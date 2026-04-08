"""Main validation orchestrator — coordinates the 3-phase pipeline."""

from __future__ import annotations

from unified_planning.model import Problem
from unified_planning.plans import ActionInstance

from pyval.models import ValidationResult
from pyval.syntax_checker import check_syntax


class PDDLValidator:
    """Pure-Python PDDL plan validator."""

    def validate_syntax(
        self, domain_path: str, problem_path: str | None = None
    ) -> ValidationResult:
        """Run Phase 1 only: syntax and semantic validation."""
        phase_result, problem = check_syntax(domain_path, problem_path)

        if phase_result["status"] == "FAIL":
            return ValidationResult(
                status="SYNTAX_ERROR",
                is_valid=False,
                phases={"syntax": phase_result},
                warnings=phase_result["warnings"],
            )

        return ValidationResult(
            status="VALID",
            is_valid=True,
            phases={"syntax": phase_result},
            warnings=phase_result["warnings"],
        )

    def validate(
        self,
        domain_path: str,
        problem_path: str,
        plan_path: str,
        tracked_fluents: list[str] | None = None,
    ) -> ValidationResult:
        """Run full 3-phase validation pipeline."""
        # Phase 1: Syntax & Semantic
        phase1_result, problem = check_syntax(domain_path, problem_path)
        phases: dict = {"syntax": phase1_result}

        if phase1_result["status"] == "FAIL":
            return ValidationResult(
                status="SYNTAX_ERROR",
                is_valid=False,
                phases=phases,
                warnings=phase1_result["warnings"],
            )

        assert problem is not None

        # Phase 2: Plan Structure
        phase2_result, action_instances, original_names = _validate_plan_structure(
            problem, plan_path
        )
        phases["structure"] = phase2_result

        if phase2_result["status"] == "FAIL":
            return ValidationResult(
                status="STRUCTURE_ERROR",
                is_valid=False,
                phases=phases,
                warnings=phase1_result["warnings"] + phase2_result["warnings"],
            )

        # Phase 3: Plan Execution
        from pyval.plan_simulator import simulate

        steps, trajectory, goal_results, numeric_traj = simulate(
            problem, action_instances, original_names, tracked_fluents
        )

        failed_step = next(
            (s.index for s in steps if s.status == "FAILED"), None
        )
        unsatisfied_goals = [g for g in goal_results if not g.satisfied]
        is_valid = failed_step is None and len(unsatisfied_goals) == 0

        exec_status = "PASS" if is_valid else "FAIL"
        phases["execution"] = {
            "status": exec_status,
            "failed_step": failed_step,
            "total_steps": len(action_instances),
        }

        all_warnings = phase1_result["warnings"] + phase2_result["warnings"]

        return ValidationResult(
            status="VALID" if is_valid else "INVALID",
            is_valid=is_valid,
            phases=phases,
            steps=steps,
            trajectory=trajectory,
            numeric_trajectory=numeric_traj,
            failed_step=failed_step,
            unsatisfied_goals=unsatisfied_goals,
            warnings=all_warnings,
        )


def _validate_plan_structure(
    problem: Problem, plan_path: str
) -> tuple[dict, list[ActionInstance], dict[str, str]]:
    """Phase 2: parse plan file and validate action/object/type references.

    Returns (phase_result, action_instances, original_names).
    original_names maps normalized (underscore) names to original PDDL names.
    """
    errors: list[str] = []
    warnings: list[str] = []
    action_instances: list[ActionInstance] = []
    original_names: dict[str, str] = {}

    lines = _read_plan_lines(plan_path)

    if not lines:
        # Empty plan — valid only if goals already satisfied
        # (goal checking is Phase 3's job, so we pass it through)
        return (
            {"status": "PASS", "errors": errors, "warnings": warnings},
            action_instances,
            original_names,
        )

    for step_idx, line in enumerate(lines, start=1):
        tokens = _parse_plan_line(line)
        if tokens is None:
            continue

        action_name_raw = tokens[0]
        param_names_raw = tokens[1:]

        # Look up action schema — try original name, then normalized
        action_schema = _lookup_action(problem, action_name_raw)
        if action_schema is None:
            errors.append(
                f"Step {step_idx}: Action '{action_name_raw}' is not declared in domain"
            )
            continue
        original_names[action_schema.name] = action_name_raw

        # Check parameter count
        expected_count = len(action_schema.parameters)
        if len(param_names_raw) != expected_count:
            errors.append(
                f"Step {step_idx}: Action '{action_name_raw}' expects "
                f"{expected_count} parameters, got {len(param_names_raw)}"
            )
            continue

        # Look up each parameter object and check types
        objects = []
        step_ok = True
        for i, param_name_raw in enumerate(param_names_raw):
            obj = _lookup_object(problem, param_name_raw)
            if obj is None:
                errors.append(
                    f"Step {step_idx}: Action '{action_name_raw}' — "
                    f"object '{param_name_raw}' is not declared in problem"
                )
                step_ok = False
                continue
            original_names[obj.name] = param_name_raw

            expected_type = action_schema.parameters[i].type
            if not obj.type.is_compatible(expected_type):
                errors.append(
                    f"Step {step_idx}: Action '{action_name_raw}' — "
                    f"parameter {i + 1} expects type '{expected_type}', "
                    f"got '{obj.type}' (object '{param_name_raw}')"
                )
                step_ok = False
                continue

            objects.append(obj)

        if step_ok:
            action_instances.append(ActionInstance(action_schema, tuple(objects)))

    status = "FAIL" if errors else "PASS"
    return (
        {"status": status, "errors": errors, "warnings": warnings},
        action_instances,
        original_names,
    )


def _read_plan_lines(plan_path: str) -> list[str]:
    """Read plan file, strip comments and blank lines."""
    with open(plan_path) as f:
        lines = []
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            # Strip inline cost comments
            if ";" in line:
                line = line[: line.index(";")].strip()
            if line:
                lines.append(line)
        return lines


def _parse_plan_line(line: str) -> list[str] | None:
    """Parse a plan line into [action_name, param1, param2, ...].

    Handles both `(action p1 p2)` and `action p1 p2` formats.
    """
    line = line.strip()
    if line.startswith("(") and line.endswith(")"):
        line = line[1:-1]
    tokens = line.split()
    if not tokens:
        return None
    return tokens


def _lookup_action(problem: Problem, raw_name: str):
    """Look up an action schema, trying original name then hyphen-normalized."""
    for candidate in _name_candidates(raw_name):
        try:
            return problem.action(candidate)
        except Exception:
            continue
    return None


def _lookup_object(problem: Problem, raw_name: str):
    """Look up a problem object, trying original name then hyphen-normalized."""
    for candidate in _name_candidates(raw_name):
        try:
            return problem.object(candidate)
        except Exception:
            continue
    return None


def _name_candidates(name: str) -> list[str]:
    """Return lookup candidates: original, then normalized (if different)."""
    candidates = [name]
    normalized = name.replace("-", "_")
    if normalized != name:
        candidates.append(normalized)
    return candidates
