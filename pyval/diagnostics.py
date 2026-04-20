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

    for prec in action.preconditions:
        _evaluate_expr(prec, state, param_map, failures)

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
) -> None:
    """Recursively evaluate a precondition expression, collecting failures."""
    node_type = expr.node_type

    if node_type == OperatorKind.AND:
        for arg in expr.args:
            _evaluate_expr(arg, state, param_map, failures)
        return

    if node_type == OperatorKind.OR:
        # Check if any disjunct is satisfied
        sub_failures: list[PreconditionFailure] = []
        for arg in expr.args:
            _evaluate_expr(arg, state, param_map, sub_failures)
        if len(sub_failures) == len(expr.args):
            # None satisfied — report the OR as failed
            failures.append(PreconditionFailure(
                expression=_expr_to_pddl(expr, param_map),
                type="boolean",
                current_values={},
                explanation="None of the disjuncts are satisfied",
            ))
        return

    if node_type == OperatorKind.NOT:
        inner = expr.args[0]
        grounded = _substitute(inner, param_map)
        try:
            val = state.get_value(grounded)
            if val.is_true():
                failures.append(PreconditionFailure(
                    expression=_expr_to_pddl(expr, param_map),
                    type="boolean",
                    current_values={_expr_to_pddl(inner, param_map): True},
                    explanation=f"{_expr_to_pddl(inner, param_map)} is true but should be false",
                ))
        except Exception:
            pass
        return

    # Comparison operators: LE, LT, EQUALS (UPF normalizes >= to <= with swapped args)
    if node_type in (OperatorKind.LE, OperatorKind.LT, OperatorKind.EQUALS):
        _evaluate_comparison(expr, state, param_map, failures)
        return

    # Fluent expression (boolean)
    if expr.is_fluent_exp():
        grounded = _substitute(expr, param_map)
        try:
            val = state.get_value(grounded)
            if val.is_false():
                failures.append(PreconditionFailure(
                    expression=_expr_to_pddl(expr, param_map),
                    type="boolean",
                    current_values={_expr_to_pddl(expr, param_map): False},
                    explanation=f"{_expr_to_pddl(expr, param_map)} is not true in the current state",
                ))
        except Exception:
            failures.append(PreconditionFailure(
                expression=_expr_to_pddl(expr, param_map),
                type="boolean",
                current_values={},
                explanation=f"Could not evaluate {_expr_to_pddl(expr, param_map)}",
            ))
        return


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
            explanation=f"Could not evaluate numeric comparison",
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
        satisfied, current_values = _evaluate_comparison_goal(expr, state, evaluator)
    else:
        satisfied = False
        try:
            val = evaluator.evaluate(expr, state)
            if val.is_bool_constant():
                satisfied = val.is_true()
        except Exception:
            pass
        current_values = {str(expr): satisfied}

    results.append(GoalResult(
        expression=str(expr),
        satisfied=satisfied,
        current_values=current_values,
    ))


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
    return str(expr)
