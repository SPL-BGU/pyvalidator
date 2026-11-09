"""Phase 3: Step-by-step plan execution with diagnostics."""

from __future__ import annotations

import re
import warnings

from unified_planning.engines import UPSequentialSimulator
from unified_planning.model import Problem
from unified_planning.plans import ActionInstance

from pyval.diagnostics import check_goals, decompose_preconditions
from pyval.models import GoalResult, NumericChange, StateSnapshot, StepResult
from pyval.numeric_tracker import NumericTracker
from pyval.pddl_format import as_pddl_call

# UPF raises `UPUsageError: The state {...} does not have a value for the value
# fuel(t2)` when a condition or effect reads a numeric fluent instance that
# :init never assigned. The whole state is in that message; only the fluent
# matters for the report.
_MISSING_VALUE_RE = re.compile(r"does not have a value for the value (?P<value>.+?)\s*$")


def simulate(
    problem: Problem,
    action_instances: list[ActionInstance],
    original_names: dict[str, str],
    tracked_fluents: list[str] | None = None,
) -> tuple[list[StepResult], list[StateSnapshot], list[GoalResult], dict[str, list], dict | None]:
    """Simulate plan execution step-by-step.

    Returns (steps, trajectory, goal_results, numeric_trajectory, metric).
    """
    # Suppress UPF warnings about unsupported problem kinds
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sim = UPSequentialSimulator(problem=problem, error_on_failed_checks=False)

    state = sim.get_initial_state()
    tracker = NumericTracker(problem, tracked_fluents)
    tracker.record(0, None, state)

    steps: list[StepResult] = []
    # (action instance, state it was applied in) — the pre-state is what an
    # action-cost expression must be evaluated against.
    executed: list[tuple[ActionInstance, object]] = []

    for idx, ai in enumerate(action_instances, start=1):
        action_display = _format_action(ai, original_names)

        # The simulator evaluates conditions and effects against the state, and
        # raises when the state has no value for something the plan reads (a
        # numeric fluent :init never assigned is the usual cause). That is a
        # property of the input, not a crash: report the step and stop.
        try:
            applicable = sim.is_applicable(state, ai)
        except Exception as exc:
            steps.append(_evaluation_failed_step(idx, action_display, exc))
            tracker.record(idx, action_display, state)
            break

        if not applicable:
            failures = decompose_preconditions(
                ai.action, ai.actual_parameters, state, problem
            )
            steps.append(StepResult(
                index=idx,
                action=action_display,
                status="FAILED",
                unsatisfied=failures,
            ))
            # Record snapshot at failure point too
            tracker.record(idx, action_display, state)
            break

        try:
            new_state = sim.apply(state, ai)
        except Exception as exc:
            steps.append(_evaluation_failed_step(idx, action_display, exc))
            tracker.record(idx, action_display, state)
            break

        if new_state is None:
            # apply() returned None — treat as inapplicable (per upf-gotchas.md)
            failures = decompose_preconditions(
                ai.action, ai.actual_parameters, state, problem
            )
            steps.append(StepResult(
                index=idx,
                action=action_display,
                status="FAILED",
                unsatisfied=failures,
            ))
            tracker.record(idx, action_display, state)
            break

        boolean_changes, numeric_changes = _compute_changes(
            problem, state, new_state
        )
        steps.append(StepResult(
            index=idx,
            action=action_display,
            status="OK",
            boolean_changes=boolean_changes,
            numeric_changes=numeric_changes,
        ))
        executed.append((ai, state))
        state = new_state
        tracker.record(idx, action_display, state)

    goal_results = check_goals(problem, state)
    metric = _evaluate_metric(problem, state, executed)

    return (
        steps,
        tracker._snapshots,
        goal_results,
        tracker.get_numeric_trajectory(),
        metric,
    )


def _evaluation_failed_step(idx: int, action_display: str, exc: Exception) -> StepResult:
    """Build a FAILED step that says why the step could not be evaluated."""
    return StepResult(
        index=idx,
        action=action_display,
        status="FAILED",
        evaluation_error=_describe_evaluation_error(exc),
    )


def _describe_evaluation_error(exc: Exception) -> str:
    """Turn a simulator exception into a repair-oriented one-line explanation."""
    message = str(exc).strip()
    missing = _MISSING_VALUE_RE.search(message)
    if missing:
        value = missing.group("value").strip()
        return (
            f"No value in the current state for {value}: this problem's :init never "
            f"assigns it, and PDDL defines no default. The step cannot be evaluated "
            f"until it is initialised. Add (= {as_pddl_call(value)} <value>) to :init."
        )
    first_line = message.splitlines()[0] if message else "no message"
    return f"{type(exc).__name__}: {first_line}"[:400]


def _evaluate_metric(
    problem: Problem, final_state, executed: list[tuple[ActionInstance, object]] | None = None
) -> dict | None:
    """Evaluate plan quality metric against the final state.

    Goes through UPF's ``StateEvaluator``: ``state.get_value`` asserts on
    arithmetic sub-expressions, so a metric like
    ``(:metric minimize (+ (* 2 (fuel)) 5))`` used to come back as ``None`` —
    indistinguishable from a problem that declares no metric at all.

    ``:action-costs`` domains carry ``MinimizeActionCosts``, which has no
    single expression: the plan's cost is the sum of the per-action cost
    expressions for the actions that actually executed, each evaluated in the
    state it was applied in.
    """
    from unified_planning.model.metrics import (
        MaximizeExpressionOnFinalState,
        MinimizeActionCosts,
        MinimizeExpressionOnFinalState,
    )
    from unified_planning.model.walkers import StateEvaluator

    for metric in problem.quality_metrics:
        if isinstance(metric, MinimizeActionCosts):
            return _evaluate_action_costs(problem, metric, executed or [])
        if isinstance(metric, (MinimizeExpressionOnFinalState, MaximizeExpressionOnFinalState)):
            kind = "minimize" if isinstance(metric, MinimizeExpressionOnFinalState) else "maximize"
            entry: dict = {
                "type": kind,
                "expression": str(metric.expression),
                "value": None,
            }
            try:
                value = StateEvaluator(problem).evaluate(metric.expression, final_state)
                entry["value"] = float(value.constant_value())
            except Exception as exc:
                entry["unavailable"] = _describe_metric_error(exc)
            return entry
    return None


def _evaluate_action_costs(
    problem: Problem, metric, executed: list[tuple[ActionInstance, object]]
) -> dict:
    """Sum the declared cost of every action that executed."""
    from unified_planning.model.walkers import StateEvaluator

    entry: dict = {"type": "minimize", "expression": "action-costs", "value": None}
    evaluator = StateEvaluator(problem)
    total = 0.0

    for instance, state_before in executed:
        cost_expression = metric.get_action_cost(instance.action)
        if cost_expression is None:
            entry["unavailable"] = (
                f"No cost is declared for action '{instance.action.name}', so the "
                f"plan cost is incomplete"
            )
            return entry
        substitutions = dict(zip(instance.action.parameters, instance.actual_parameters))
        try:
            grounded = (
                cost_expression.substitute(substitutions) if substitutions else cost_expression
            )
            total += float(evaluator.evaluate(grounded, state_before).constant_value())
        except Exception as exc:
            entry["unavailable"] = _describe_metric_error(exc)
            return entry

    entry["value"] = total
    return entry


def _describe_metric_error(exc: Exception) -> str:
    """One-line reason a metric expression could not be evaluated."""
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else "no message"
    return f"{type(exc).__name__}: {message}"[:300]


def _compute_changes(
    problem: Problem, old_state, new_state
) -> tuple[dict[str, bool], dict[str, NumericChange]]:
    """Compute fluent changes between two states."""
    boolean_changes: dict[str, bool] = {}
    numeric_changes: dict[str, NumericChange] = {}

    for fluent_expr in problem.initial_values:
        old_val = old_state.get_value(fluent_expr)
        new_val = new_state.get_value(fluent_expr)

        if str(old_val) != str(new_val):
            name = str(fluent_expr)
            if old_val.is_bool_constant():
                boolean_changes[name] = new_val.is_true()
            else:
                numeric_changes[name] = NumericChange(
                    before=float(old_val.constant_value()),
                    after=float(new_val.constant_value()),
                )

    return boolean_changes, numeric_changes


def _format_action(ai: ActionInstance, original_names: dict[str, str]) -> str:
    """Format an ActionInstance as a PDDL plan line using original names."""
    action_name = original_names.get(ai.action.name, ai.action.name)
    params = " ".join(
        original_names.get(str(p), str(p)) for p in ai.actual_parameters
    )
    return f"({action_name} {params})" if params else f"({action_name})"
