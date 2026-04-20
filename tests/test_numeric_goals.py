"""Tests for numeric comparison goals (<=, >=, =) in :goal.

Regression tests for the bug where `_evaluate_goal` always reported
numeric comparison goals as unsatisfied. A `noop`-only mini domain
isolates the goal check from simulator mechanics — the plan is just
`(noop)`, so any failure is in goal evaluation.
"""

import os

import pytest

from pyval import PDDLValidator
from tests.conftest import write_pddl_files


def _build(tmp_path, predicates: str, functions: str, init: str, goal: str):
    """Construct a noop-domain problem with the given init state and goal."""
    domain = f"""\
(define (domain goal-test)
  (:requirements :strips :typing :numeric-fluents)
  (:predicates
    {predicates}
  )
  (:functions
    {functions}
  )
  (:action noop
    :parameters ()
    :precondition (and)
    :effect (and)
  )
)
"""
    problem = f"""\
(define (problem goal-test-p1)
  (:domain goal-test)
  (:init
    {init}
  )
  (:goal {goal})
)
"""
    plan = "(noop)\n"
    return write_pddl_files(tmp_path, domain, problem, plan)


def test_le_goal_satisfied(tmp_path):
    """(<= 5 (foo)) with foo=10 → VALID."""
    files = _build(tmp_path, "(pred)", "(foo)", "(= (foo) 10)", "(<= 5 (foo))")
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert result.is_valid, result.report()


def test_le_goal_unsatisfied(tmp_path):
    """(<= 5 (foo)) with foo=3 → INVALID."""
    files = _build(tmp_path, "(pred)", "(foo)", "(= (foo) 3)", "(<= 5 (foo))")
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert not result.is_valid


def test_ge_goal_normalization(tmp_path):
    """(>= (foo) 5) with foo=10 → VALID. Confirms UPF >= → LE normalization."""
    files = _build(tmp_path, "(pred)", "(foo)", "(= (foo) 10)", "(>= (foo) 5)")
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert result.is_valid, result.report()


def test_equals_goal_satisfied(tmp_path):
    """(= (foo) 7) with foo=7 → VALID (tolerance path)."""
    files = _build(tmp_path, "(pred)", "(foo)", "(= (foo) 7)", "(= (foo) 7)")
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert result.is_valid, result.report()


def test_arithmetic_lhs(tmp_path):
    """(<= (+ (foo) 1) (bar)) with foo=5, bar=10 → VALID (counters-style)."""
    files = _build(
        tmp_path,
        "(pred)",
        "(foo) (bar)",
        "(= (foo) 5) (= (bar) 10)",
        "(<= (+ (foo) 1) (bar))",
    )
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert result.is_valid, result.report()


def test_mixed_conjunction(tmp_path):
    """(and (pred) (<= 5 (foo))) with pred=T, foo=10 → VALID."""
    files = _build(
        tmp_path,
        "(pred)",
        "(foo)",
        "(pred) (= (foo) 10)",
        "(and (pred) (<= 5 (foo)))",
    )
    result = PDDLValidator().validate(files["domain"], files["problem"], files["plan"])
    assert result.is_valid, result.report()


# ---------------------------------------------------------------------------
# Cross-repo regression tests — skipped if pddl-copilot-experiments absent
# ---------------------------------------------------------------------------

_EXPERIMENTS = "/Users/omereliyahu/personal/pddl-copilot-experiments/domains/numeric"
_COUNTERS = f"{_EXPERIMENTS}/counters"
_FARMLAND = f"{_EXPERIMENTS}/farmland"


@pytest.mark.skipif(
    not os.path.isfile(f"{_COUNTERS}/p01.plan"),
    reason="pddl-copilot-experiments counters fixture absent",
)
def test_counters_p01_reference_plan():
    result = PDDLValidator().validate(
        f"{_COUNTERS}/domain.pddl",
        f"{_COUNTERS}/p01.pddl",
        f"{_COUNTERS}/p01.plan",
    )
    assert result.is_valid, result.report()


@pytest.mark.skipif(
    not os.path.isfile(f"{_FARMLAND}/p01.plan"),
    reason="pddl-copilot-experiments farmland fixture absent",
)
def test_farmland_p01_reference_plan():
    result = PDDLValidator().validate(
        f"{_FARMLAND}/domain.pddl",
        f"{_FARMLAND}/p01.pddl",
        f"{_FARMLAND}/p01.plan",
    )
    assert result.is_valid, result.report()
