"""Tests for Phase 3: Plan Execution Simulation."""

from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    BLOCKSWORLD_VALID_PLAN,
    BLOCKSWORLD_INVALID_PLAN,
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    LOGISTICS_FUEL_VALID_PLAN,
    LOGISTICS_FUEL_INVALID_PLAN,
    write_pddl_files,
)

from pyval.validator import PDDLValidator


def test_valid_classical_plan_executes_all_steps(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    assert result.is_valid
    assert result.status == "VALID"
    assert len(result.steps) == 8  # 8 actions in the valid plan
    assert all(s.status == "OK" for s in result.steps)


def test_invalid_classical_plan_fails(classical_invalid_files):
    v = PDDLValidator()
    result = v.validate(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    assert not result.is_valid
    assert result.status == "INVALID"
    assert result.failed_step is not None


def test_boolean_precondition_failure_detected(classical_invalid_files):
    v = PDDLValidator()
    result = v.validate(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    failed = [s for s in result.steps if s.status == "FAILED"]
    assert len(failed) == 1
    assert len(failed[0].unsatisfied) > 0


def test_valid_numeric_plan(numeric_files):
    v = PDDLValidator()
    result = v.validate(
        numeric_files["domain"], numeric_files["problem"], numeric_files["plan"]
    )
    assert result.is_valid
    assert result.status == "VALID"
    assert len(result.steps) == 4


def test_numeric_changes_recorded(numeric_files):
    v = PDDLValidator()
    result = v.validate(
        numeric_files["domain"], numeric_files["problem"], numeric_files["plan"]
    )
    # First step is drive — should have numeric changes for fuel
    drive_step = result.steps[0]
    assert len(drive_step.numeric_changes) > 0
    fuel_key = [k for k in drive_step.numeric_changes if "fuel" in k]
    assert len(fuel_key) > 0
    change = drive_step.numeric_changes[fuel_key[0]]
    assert change.before == 100
    assert change.after == 90  # 100 - distance(loc1, loc2) = 100 - 10


def test_numeric_plan_invalid_no_goal(numeric_invalid_files):
    """Plan executes but doesn't achieve goals (never loads/delivers package)."""
    v = PDDLValidator()
    result = v.validate(
        numeric_invalid_files["domain"],
        numeric_invalid_files["problem"],
        numeric_invalid_files["plan"],
    )
    assert not result.is_valid
    assert len(result.unsatisfied_goals) > 0


def test_numeric_precondition_failure(tmp_path):
    """Plan fails due to insufficient fuel (numeric precondition)."""
    plan = """\
(drive truck1 loc1 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
(drive truck1 loc2 loc3)
"""
    paths = write_pddl_files(
        tmp_path, LOGISTICS_FUEL_DOMAIN, LOGISTICS_FUEL_PROBLEM, plan
    )
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert result.failed_step is not None
    failed = [s for s in result.steps if s.status == "FAILED"]
    assert len(failed) == 1
    assert any(f.type == "numeric" for f in failed[0].unsatisfied)


def test_state_changes_recorded(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    # First step is unstack b1 b2 — should have boolean changes
    first = result.steps[0]
    assert len(first.boolean_changes) > 0


def test_trajectory_recorded(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    # Should have initial + N steps snapshots
    assert len(result.trajectory) >= 2


def test_goals_checked(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    # Valid plan — all goals should be satisfied
    assert all(g.satisfied for g in result.unsatisfied_goals) or len(result.unsatisfied_goals) == 0


def test_unsatisfied_goals_reported(tmp_path):
    """A plan that executes but doesn't achieve all goals."""
    plan = "(unstack b1 b2)\n(put-down b1)\n"  # Doesn't achieve goal
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert not result.is_valid
    assert len(result.unsatisfied_goals) > 0


def test_empty_plan_valid_when_goals_satisfied(tmp_path):
    """Empty plan should be valid if goals are already true in initial state."""
    domain = """\
(define (domain trivial)
  (:requirements :strips)
  (:predicates (done))
  (:action noop
    :parameters ()
    :precondition (done)
    :effect (done)
  )
)
"""
    problem = """\
(define (problem trivial-p)
  (:domain trivial)
  (:init (done))
  (:goal (done))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem, "\n")
    v = PDDLValidator()
    result = v.validate(paths["domain"], paths["problem"], paths["plan"])
    assert result.is_valid
    assert result.status == "VALID"
