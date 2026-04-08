"""Phase 3: Step-by-step plan execution with diagnostics."""

from __future__ import annotations

import warnings

from unified_planning.engines import UPSequentialSimulator
from unified_planning.model import Problem
from unified_planning.plans import ActionInstance

from pyval.diagnostics import check_goals, decompose_preconditions
from pyval.models import GoalResult, NumericChange, StateSnapshot, StepResult
from pyval.numeric_tracker import NumericTracker


def simulate(
    problem: Problem,
    action_instances: list[ActionInstance],
    original_names: dict[str, str],
    tracked_fluents: list[str] | None = None,
) -> tuple[list[StepResult], list[StateSnapshot], list[GoalResult], dict[str, list]]:
    """Simulate plan execution step-by-step.

    Returns (steps, trajectory, goal_results, numeric_trajectory).
    """
    # Suppress UPF warnings about unsupported problem kinds
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sim = UPSequentialSimulator(problem=problem, error_on_failed_checks=False)

    state = sim.get_initial_state()
    tracker = NumericTracker(problem, tracked_fluents)
    tracker.record(0, None, state)

    steps: list[StepResult] = []

    for idx, ai in enumerate(action_instances, start=1):
        action_display = _format_action(ai, original_names)

        if sim.is_applicable(state, ai):
            new_state = sim.apply(state, ai)
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
            state = new_state
            tracker.record(idx, action_display, state)
        else:
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

    goal_results = check_goals(problem, state)

    return (
        steps,
        tracker._snapshots,
        goal_results,
        tracker.get_numeric_trajectory(),
    )


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
