"""Diagnostic message generation — precondition decomposition and goal checking."""

from __future__ import annotations

from unified_planning.model import FNode, OperatorKind
from unified_planning.model.walkers import StateEvaluator

from pyval.models import GoalResult, PreconditionFailure


def decompose_preconditions(
    action, parameters: tuple, state, problem
) -> list[PreconditionFailure]:
    """Walk action preconditions, evaluate each against state, return failures.

    Parameters are the grounded objects substituted into the action schema.
    """
    failures: list[PreconditionFailure] = []
    param_map = dict(zip(action.parameters, parameters))
    evaluator = StateEvaluator(problem)

    for prec in action.preconditions:
        _evaluate_expr(prec, state, param_map, failures, evaluator)

    return failures


def check_goals(problem, state) -> list[GoalResult]:
    """Evaluate all goals against a state, return results for each."""
    results: list[GoalResult] = []
    evaluator = StateEvaluator(problem)
    for goal in problem.goals:
        _evaluate_goal(goal, state, results, evaluator)
    return results


def _evaluate_expr(
    expr: FNode,
    state,
    param_map: dict,
    failures: list[PreconditionFailure],
    evaluator,
) -> None:
    """Recursively evaluate a precondition expression, collecting failures."""
    node_type = expr.node_type

    if node_type == OperatorKind.AND:
        for arg in expr.args:
            _evaluate_expr(arg, state, param_map, failures, evaluator)
        return

    if node_type == OperatorKind.OR:
        _evaluate_disjunction(expr, state, param_map, failures, evaluator)
        return

    if node_type == OperatorKind.NOT:
        inner = expr.args[0]
        verdict = _holds(expr, state, param_map, evaluator)
        if verdict is False:
            failures.append(PreconditionFailure(
                expression=_expr_to_pddl(expr, param_map),
                type="boolean",
                current_values={_expr_to_pddl(inner, param_map): True},
                explanation=f"{_expr_to_pddl(inner, param_map)} is true but should be false",
            ))
        elif verdict is None:
            failures.append(_unevaluable_failure(expr, param_map))
        return

    # Comparison operators: LE, LT, EQUALS (UPF normalizes >= to <= with swapped args).
    # EQUALS is also how `:equality` compares *objects*, which carries no numeric
    # deficit and must not be reported as an unreadable numeric comparison.
    if node_type in (OperatorKind.LE, OperatorKind.LT, OperatorKind.EQUALS):
        if _is_numeric(expr.args[0]) and _is_numeric(expr.args[1]):
            _evaluate_comparison(expr, state, param_map, failures)
        else:
            _evaluate_boolean(
                expr,
                state,
                param_map,
                failures,
                evaluator,
                unsatisfied="is not satisfied in the current state",
            )
        return

    # Fluent expression (boolean)
    if expr.is_fluent_exp():
        _evaluate_boolean(
            expr,
            state,
            param_map,
            failures,
            evaluator,
            unsatisfied="is not true in the current state",
        )
        return

    # Everything else — quantifiers, implication, equivalence, object equality —
    # used to fall through this function silently, so a failing quantified
    # precondition produced a FAILED step with an empty explanation.
    _evaluate_boolean(
        expr,
        state,
        param_map,
        failures,
        evaluator,
        unsatisfied="is not satisfied in the current state",
    )


def _evaluate_disjunction(
    expr: FNode,
    state,
    param_map: dict,
    failures: list[PreconditionFailure],
    evaluator,
) -> None:
    """Report a disjunction only when no disjunct holds.

    Counting sub-failures is not the same as evaluating the disjuncts: an
    ``(and ...)`` disjunct contributes one failure per failing conjunct, so
    ``(or (and (p) (q) (s)) (r))`` produced more "failures" than there were
    disjuncts and the OR reported nothing at all — the failing step then showed
    no unsatisfied precondition.
    """
    verdicts = [_holds(arg, state, param_map, evaluator) for arg in expr.args]
    if any(verdict is True for verdict in verdicts):
        return

    rendered = _expr_to_pddl(expr, param_map)
    disjuncts = [_expr_to_pddl(arg, param_map) for arg in expr.args]

    if all(verdict is False for verdict in verdicts):
        explanation = (
            f"None of the {len(disjuncts)} disjuncts holds: " + "; ".join(disjuncts)
        )
    else:
        unevaluable = [
            disjunct
            for disjunct, verdict in zip(disjuncts, verdicts)
            if verdict is None
        ]
        explanation = (
            "No disjunct could be shown to hold; the simulator raised on: "
            + "; ".join(unevaluable)
        )

    failures.append(PreconditionFailure(
        expression=rendered,
        type="boolean",
        current_values={},
        explanation=explanation,
    ))


def _evaluate_boolean(
    expr: FNode,
    state,
    param_map: dict,
    failures: list[PreconditionFailure],
    evaluator,
    unsatisfied: str,
) -> None:
    """Report a boolean condition that does not hold, using UPF's evaluator."""
    verdict = _holds(expr, state, param_map, evaluator)
    if verdict is True:
        return
    if verdict is None:
        failures.append(_unevaluable_failure(expr, param_map))
        return

    rendered = _expr_to_pddl(expr, param_map)
    failures.append(PreconditionFailure(
        expression=rendered,
        type="boolean",
        current_values={rendered: False},
        explanation=f"{rendered} {unsatisfied}",
    ))


def _unevaluable_failure(expr: FNode, param_map: dict) -> PreconditionFailure:
    """Build a failure for a condition the simulator could not evaluate."""
    rendered = _expr_to_pddl(expr, param_map)
    return PreconditionFailure(
        expression=rendered,
        type="boolean",
        current_values={},
        explanation=f"Could not evaluate {rendered}",
    )


def _holds(expr: FNode, state, param_map: dict, evaluator) -> bool | None:
    """Return whether `expr` holds in `state`, or None when it cannot be evaluated.

    Uses UPF's StateEvaluator so constants, arithmetic, quantifiers and object
    equality evaluate the same way the simulator evaluates them.
    """
    grounded = _substitute(expr, param_map)
    try:
        value = evaluator.evaluate(grounded, state)
    except Exception:
        return None
    if value.is_bool_constant():
        return value.is_true()
    return None


def _is_numeric(expr: FNode) -> bool:
    """Whether an expression denotes a number (as opposed to an object or bool)."""
    try:
        expr_type = expr.type
    except Exception:
        return False
    return expr_type.is_int_type() or expr_type.is_real_type()


def _evaluate_comparison(
    expr: FNode,
    state,
    param_map: dict,
    failures: list[PreconditionFailure],
) -> None:
    """Evaluate a numeric comparison, report failure with deficit."""
    left_expr, right_expr = expr.args[0], expr.args[1]
    left_grounded = _substitute(left_expr, param_map)
    right_grounded = _substitute(right_expr, param_map)

    try:
        left_val = state.get_value(left_grounded).constant_value()
        right_val = state.get_value(right_grounded).constant_value()
    except Exception:
        failures.append(PreconditionFailure(
            expression=_expr_to_pddl(expr, param_map),
            type="numeric",
            current_values={},
            explanation="Could not evaluate numeric comparison",
        ))
        return

    op = expr.node_type
    satisfied = _check_comparison(op, left_val, right_val)

    if not satisfied:
        current_values = {}
        if left_expr.is_fluent_exp():
            current_values[_expr_to_pddl(left_expr, param_map)] = left_val
        if right_expr.is_fluent_exp():
            current_values[_expr_to_pddl(right_expr, param_map)] = right_val

        deficit = _compute_deficit(op, left_val, right_val)
        op_symbol = _op_symbol(op)

        failures.append(PreconditionFailure(
            expression=_expr_to_pddl(expr, param_map),
            type="numeric",
            current_values=current_values,
            explanation=(
                f"Required: {_expr_to_pddl(left_expr, param_map)} "
                f"{op_symbol} {_expr_to_pddl(right_expr, param_map)}"
            ),
            deficit=deficit,
        ))


def _check_comparison(op: OperatorKind, left: float, right: float) -> bool:
    eps = 1e-6
    if op == OperatorKind.LE:
        return left <= right + eps
    if op == OperatorKind.LT:
        return left < right
    if op == OperatorKind.EQUALS:
        return abs(left - right) < eps
    return False


def _compute_deficit(op: OperatorKind, left: float, right: float) -> float:
    if op == OperatorKind.LE:
        return left - right
    if op == OperatorKind.LT:
        return left - right
    if op == OperatorKind.EQUALS:
        return abs(left - right)
    return 0.0


def _op_symbol(op: OperatorKind) -> str:
    return {
        OperatorKind.LE: "<=",
        OperatorKind.LT: "<",
        OperatorKind.EQUALS: "=",
    }.get(op, "?")


def _evaluate_goal(expr: FNode, state, results: list[GoalResult], evaluator) -> None:
    """Evaluate a single goal expression, decomposing ANDs.

    Uses UPF's StateEvaluator — unlike `state.get_value`, it handles constants,
    arithmetic sub-expressions, NOT, and comparisons uniformly.
    """
    if expr.node_type == OperatorKind.AND:
        for arg in expr.args:
            _evaluate_goal(arg, state, results, evaluator)
        return

    if expr.node_type in (OperatorKind.LE, OperatorKind.LT, OperatorKind.EQUALS):
        if _is_numeric(expr.args[0]) and _is_numeric(expr.args[1]):
            satisfied, current_values = _evaluate_comparison_goal(expr, state, evaluator)
        else:
            satisfied, current_values = _evaluate_boolean_goal(expr, state, evaluator)
    else:
        satisfied, current_values = _evaluate_boolean_goal(expr, state, evaluator)

    results.append(GoalResult(
        expression=str(expr),
        satisfied=satisfied,
        current_values=current_values,
    ))


def _evaluate_boolean_goal(expr: FNode, state, evaluator) -> tuple[bool, dict]:
    """Evaluate a non-numeric goal (fluent, NOT, quantified, object equality)."""
    try:
        value = evaluator.evaluate(expr, state)
    except Exception:
        return (False, {})
    if value.is_bool_constant():
        return (value.is_true(), {str(expr): value.is_true()})
    return (False, {})


def _evaluate_comparison_goal(expr: FNode, state, evaluator) -> tuple[bool, dict]:
    try:
        left_val = float(evaluator.evaluate(expr.args[0], state).constant_value())
        right_val = float(evaluator.evaluate(expr.args[1], state).constant_value())
    except Exception:
        return (False, {})
    satisfied = _check_comparison(expr.node_type, left_val, right_val)
    current_values: dict = {}
    if expr.args[0].is_fluent_exp():
        current_values[str(expr.args[0])] = left_val
    if expr.args[1].is_fluent_exp():
        current_values[str(expr.args[1])] = right_val
    return (satisfied, current_values)


def _substitute(expr: FNode, param_map: dict) -> FNode:
    """Substitute action parameters with grounded objects in an expression."""
    if not param_map:
        return expr
    return expr.substitute(param_map)


def _expr_to_pddl(expr: FNode, param_map: dict | None = None) -> str:
    """Convert an FNode expression to a PDDL-like string."""
    if param_map:
        expr = _substitute(expr, param_map)
    return str(expr).replace(" == ", " = ")
