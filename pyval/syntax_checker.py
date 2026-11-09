"""Phase 1: PDDL syntax and semantic validation via UPF's PDDLReader."""

from __future__ import annotations

import itertools

from unified_planning.io import PDDLReader
from unified_planning.model import Problem

from pyval.pddl_format import as_pddl_call

# Bound on how many ground instances of a numeric function we are willing to
# enumerate when cross-checking :init. Object counts multiply, so a two-argument
# function over a large domain explodes past any useful limit.
_MAX_GROUND_INSTANCES = 250
# Bound on how many missing instances one warning lists before summarising.
_MAX_LISTED_MISSING = 6


def check_syntax(
    domain_path: str, problem_path: str | None = None
) -> tuple[dict, Problem | None]:
    """Parse and validate PDDL domain (and optionally problem).

    Returns a tuple of (phase_result, parsed_problem).
    phase_result has keys: status ("PASS"|"FAIL"), errors (list[str]), warnings (list[str]).
    parsed_problem is None if parsing failed.
    """
    errors: list[str] = []
    warnings: list[str] = []

    reader = PDDLReader()
    try:
        problem = reader.parse_problem(domain_path, problem_path)
    except Exception as exc:
        errors.append(_format_parse_error(exc, domain_path, problem_path))
        return {"status": "FAIL", "errors": errors, "warnings": warnings}, None

    # Post-parse checks
    warnings.extend(_check_unsupported_requirements(problem))
    warnings.extend(_check_numeric_initialization(problem))

    return {"status": "PASS", "errors": errors, "warnings": warnings}, problem


def _check_unsupported_requirements(problem: Problem) -> list[str]:
    """Warn about PDDL features that pyvalidator cannot simulate correctly."""
    warnings = []
    kind = problem.kind

    if kind.has_time():
        warnings.append(
            "Domain uses durative/temporal actions which pyvalidator does not support. "
            "Validation results may be incorrect."
        )
    if kind.has_events() or kind.has_processes():
        warnings.append(
            "Domain uses PDDL+ features (processes/events) which pyvalidator does not support. "
            "Validation results may be incorrect."
        )

    return warnings


def _format_parse_error(
    exc: Exception, domain_path: str, problem_path: str | None
) -> str:
    """Format a UPF parse exception into a readable error message."""
    msg = str(exc).strip()
    if problem_path:
        return f"Failed to parse domain '{domain_path}' with problem '{problem_path}': {msg}"
    return f"Failed to parse domain '{domain_path}': {msg}"


def _check_numeric_initialization(problem: Problem) -> list[str]:
    """Warn about numeric fluent instances that :init never assigns a value to.

    PDDL defines no default for numeric fluents, and neither does the
    simulator: a ``state.get_value`` on an unassigned instance raises
    ``UPUsageError`` ("The state ... does not have a value for the value
    fuel(t2)"), which used to abort validation with a traceback. The check is
    per ground instance, not per declared name, because initialising
    ``(fuel t1)`` says nothing about ``(fuel t2)``.

    Only instances that matter are reported: a function an action *writes* must
    have a value for every object it ranges over (the effect raises otherwise),
    and a function with no initial value at all is reported as a whole. A static
    table such as ``(distance ?a ?b)`` is routinely specified only for the pairs
    that exist, so partial coverage there is not a defect — if a plan reads a
    missing pair, the step reports it by name.
    """
    warnings: list[str] = []
    modified = _functions_written_by_actions(problem)

    for fluent in problem.fluents:
        if not (fluent.type.is_int_type() or fluent.type.is_real_type()):
            continue

        instances = _ground_instances(problem, fluent)
        if instances is None:
            if fluent.name in modified:
                warnings.append(
                    f"Numeric function '{fluent.name}' has more than "
                    f"{_MAX_GROUND_INSTANCES} ground instances, so it was not "
                    f"cross-checked against :init. No default value is assumed: "
                    f"any instance that :init leaves out has no value in the state."
                )
            continue

        missing = [expr for expr in instances if expr not in problem.initial_values]
        if not missing:
            continue
        if fluent.name in modified or len(missing) == len(instances):
            warnings.append(_missing_init_warning(fluent.name, missing, len(instances)))

    return warnings


def _functions_written_by_actions(problem: Problem) -> set[str]:
    """Names of the functions some action effect assigns or updates."""
    names: set[str] = set()
    for action in problem.actions:
        for effect in action.effects:
            fluent_expression = getattr(effect, "fluent", None)
            if fluent_expression is not None and fluent_expression.is_fluent_exp():
                names.add(fluent_expression.fluent().name)
    return names


def _ground_instances(problem: Problem, fluent) -> list | None:
    """Enumerate the ground instances of `fluent`, or None if there are too many."""
    domains = []
    total = 1
    for parameter in fluent.signature:
        objects = list(problem.objects(parameter.type))
        if not objects:
            # A parameter type with no objects has no ground instances at all.
            return []
        domains.append(objects)
        total *= len(objects)
        if total > _MAX_GROUND_INSTANCES:
            return None

    expression_manager = problem.environment.expression_manager
    return [
        expression_manager.FluentExp(fluent, tuple(combination))
        for combination in itertools.product(*domains)
    ]


def _missing_init_warning(name: str, missing: list, total: int) -> str:
    """Build a repair-oriented message naming the unassigned instances."""
    rendered = [str(expr) for expr in missing[:_MAX_LISTED_MISSING]]
    listed = ", ".join(rendered)
    if len(missing) > _MAX_LISTED_MISSING:
        listed += f", ... ({len(missing) - _MAX_LISTED_MISSING} more)"

    if total == 1:
        subject = f"Numeric function '{name}' has no initial value"
        example = f"(= {rendered[0]} <value>)"
    else:
        subject = (
            f"Numeric function '{name}' has no initial value for "
            f"{len(missing)} of its {total} ground instances"
        )
        example = f"(= {as_pddl_call(rendered[0])} <value>)"

    return (
        f"{subject}: {listed}. PDDL assigns no default, so the simulator has no "
        f"value for them and any precondition or effect that reads one cannot be "
        f"evaluated. Add {example} to :init."
    )
