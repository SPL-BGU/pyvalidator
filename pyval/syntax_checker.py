"""Phase 1: PDDL syntax and semantic validation via UPF's PDDLReader."""

from __future__ import annotations

from unified_planning.io import PDDLReader
from unified_planning.model import Problem


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
    """Warn about numeric fluents with no explicit initial value (default 0)."""
    warnings = []
    declared_numeric_fluents = set()
    initialized_fluents = set()

    for fluent in problem.fluents:
        if fluent.type.is_int_type() or fluent.type.is_real_type():
            declared_numeric_fluents.add(fluent.name)

    for fluent_expr in problem.initial_values:
        if fluent_expr.is_fluent_exp():
            initialized_fluents.add(fluent_expr.fluent().name)

    for name in declared_numeric_fluents - initialized_fluents:
        warnings.append(
            f"Numeric function '{name}' has no initial value assigned — defaults to 0"
        )

    return warnings
