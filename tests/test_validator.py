"""Tests for the PDDLValidator orchestrator and Phase 2 plan structure validation."""

from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    BLOCKSWORLD_VALID_PLAN,
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    TYPED_HIERARCHY_DOMAIN,
    TYPED_HIERARCHY_PROBLEM,
    TYPED_HIERARCHY_SIBLING_PLAN,
    TYPED_HIERARCHY_SUBTYPE_PLAN,
    write_pddl_files,
)

from pyval.validator import PDDLValidator


def test_validate_syntax_domain_only(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN)
    v = PDDLValidator()
    result = v.validate_syntax(paths["domain"])
    assert result.is_valid
    assert result.status == "VALID"


def test_validate_syntax_domain_and_problem(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM)
    v = PDDLValidator()
    result = v.validate_syntax(paths["domain"], paths["problem"])
    assert result.is_valid
    assert result.status == "VALID"


def test_syntax_error_halts_pipeline(tmp_path):
    bad = "(define (domain bad) (:predicates (foo ?x))"
    paths = write_pddl_files(tmp_path, bad, None, "(noop)")
    v = PDDLValidator()
    result = v.validate_syntax(paths["domain"])
    assert not result.is_valid
    assert result.status == "SYNTAX_ERROR"


def test_undeclared_action_returns_structure_error(tmp_path):
    plan = "(nonexistent-action b1 b2)\n"
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert result.status == "STRUCTURE_ERROR"
    assert any("nonexistent-action" in e for e in result.phases["structure"]["errors"])


def test_undeclared_object_returns_structure_error(tmp_path):
    plan = "(pick-up nonexistent_object)\n"
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert result.status == "STRUCTURE_ERROR"


def test_wrong_parameter_count_returns_structure_error(tmp_path):
    plan = "(pick-up b1 b2)\n"  # pick-up takes 1 param, not 2
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert result.status == "STRUCTURE_ERROR"
    assert any("expects 1 parameters" in e for e in result.phases["structure"]["errors"])


def test_hyphen_normalization_matches_actions(tmp_path):
    """Actions with hyphens (pick-up) should match UPF's underscore names."""
    paths = write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, BLOCKSWORLD_VALID_PLAN
    )
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    # Phase 2 should pass — hyphen normalization works
    assert result.phases["structure"]["status"] == "PASS"


def test_empty_plan(tmp_path):
    """Empty plan should pass Phase 2 (goal check is Phase 3's job)."""
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, "\n")
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    # Phase 2 passes, Phase 3 determines if goals are satisfied
    assert result.phases["structure"]["status"] == "PASS"


def test_subtype_object_accepted_for_supertype_parameter(tmp_path):
    """Action parameter typed `vehicle` must accept a `truck` (subtype)."""
    paths = write_pddl_files(
        tmp_path,
        TYPED_HIERARCHY_DOMAIN,
        TYPED_HIERARCHY_PROBLEM,
        TYPED_HIERARCHY_SUBTYPE_PLAN,
    )
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert result.phases["structure"]["status"] == "PASS", (
        result.phases["structure"]["errors"]
    )


def test_sibling_type_rejected_for_parameter(tmp_path):
    """An object from a sibling branch (cargo) must NOT satisfy a vehicle parameter."""
    paths = write_pddl_files(
        tmp_path,
        TYPED_HIERARCHY_DOMAIN,
        TYPED_HIERARCHY_PROBLEM,
        TYPED_HIERARCHY_SIBLING_PLAN,
    )
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert result.status == "STRUCTURE_ERROR"
    assert any(
        "expects type 'vehicle'" in e and "box1" in e
        for e in result.phases["structure"]["errors"]
    )


def test_comment_and_cost_lines_skipped(tmp_path):
    plan = """\
; This is a comment
(pick-up b1)
; cost = 1 (general cost)
"""
    # This domain has b1 on b2, so pick-up b1 requires clear b1 (true) + ontable b1 (false)
    # Phase 2 should still pass — the plan line is structurally valid
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert result.phases["structure"]["status"] == "PASS"
