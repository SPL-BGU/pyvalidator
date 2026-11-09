"""Precondition diagnostics must explain every step they call FAILED.

`decompose_preconditions` walked AND/OR/NOT/comparisons and silently ignored
everything else, and its OR branch counted sub-failures instead of evaluating
the disjuncts. Both produced a FAILED step with an empty
`unsatisfied_preconditions` list, which is the one thing a repair-oriented
validator must never do.
"""

from pyval import PDDLValidator
from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    write_pddl_files,
)

DISJUNCT_DOMAIN = """\
(define (domain disjuncts)
  (:requirements :strips :typing)
  (:types thing)
  (:predicates (p ?x - thing) (q ?x - thing) (s ?x - thing) (r ?x - thing)
               (done ?x - thing))
  (:action go
    :parameters (?x - thing)
    :precondition (or (and (p ?x) (q ?x) (s ?x)) (r ?x))
    :effect (done ?x))
)
"""


def _disjunct_problem(init: str) -> str:
    return f"""\
(define (problem disjuncts-p1)
  (:domain disjuncts)
  (:objects a - thing)
  (:init {init})
  (:goal (done a))
)
"""


def test_or_with_multi_conjunct_disjunct_still_reports(tmp_path):
    """`(and p q s)` fails 3 times and `r` fails once — the OR must still speak."""
    paths = write_pddl_files(
        tmp_path, DISJUNCT_DOMAIN, _disjunct_problem(""), "(go a)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.status == "INVALID"
    failures = result.steps[0].unsatisfied
    assert len(failures) == 1, failures
    assert "or" in failures[0].expression
    assert "None of the 2 disjuncts holds" in failures[0].explanation
    assert "p(a)" in failures[0].explanation
    assert "r(a)" in failures[0].explanation


def test_or_with_satisfied_disjunct_does_not_report(tmp_path):
    paths = write_pddl_files(
        tmp_path, DISJUNCT_DOMAIN, _disjunct_problem("(r a)"), "(go a)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    assert result.is_valid, result.report()


QUANTIFIED_DOMAIN = """\
(define (domain quantified)
  (:requirements :strips :typing :quantified-preconditions)
  (:types thing)
  (:predicates (p ?x - thing) (done ?x - thing))
  (:action mark
    :parameters (?x - thing)
    :precondition (forall (?y - thing) (p ?y))
    :effect (done ?x))
)
"""


def test_universal_precondition_failure_is_reported(tmp_path):
    problem = """\
(define (problem quantified-p1)
  (:domain quantified)
  (:objects a b c - thing)
  (:init (p a) (p b))
  (:goal (done a))
)
"""
    paths = write_pddl_files(tmp_path, QUANTIFIED_DOMAIN, problem, "(mark a)\n")
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.status == "INVALID"
    failures = result.steps[0].unsatisfied
    assert len(failures) == 1
    assert failures[0].type == "boolean"
    assert "Forall" in failures[0].expression
    assert "is not satisfied in the current state" in failures[0].explanation


EQUALITY_DOMAIN = """\
(define (domain equality)
  (:requirements :strips :typing :equality)
  (:types thing)
  (:predicates (at ?x - thing ?loc - thing))
  (:action move
    :parameters (?x - thing ?from - thing ?to - thing)
    :precondition (and (at ?x ?from) (= ?from ?to))
    :effect (and (not (at ?x ?from)) (at ?x ?to)))
)
"""

EQUALITY_PROBLEM = """\
(define (problem equality-p1)
  (:domain equality)
  (:objects a b c - thing)
  (:init (at a a))
  (:goal (at a c))
)
"""


def test_object_equality_failure_is_not_reported_as_numeric(tmp_path):
    """`:equality` compares objects; the old path said "numeric comparison"."""
    paths = write_pddl_files(
        tmp_path, EQUALITY_DOMAIN, EQUALITY_PROBLEM, "(move a a c)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.status == "INVALID"
    failure = result.steps[0].unsatisfied[0]
    assert failure.type == "boolean"
    assert "numeric comparison" not in failure.explanation
    assert failure.deficit is None
    assert "= c" in failure.expression  # rendered as PDDL equality, not "=="


def test_object_equality_that_holds_does_not_report(tmp_path):
    paths = write_pddl_files(
        tmp_path, EQUALITY_DOMAIN, EQUALITY_PROBLEM, "(move a a a)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.steps[0].status == "OK"
    assert result.steps[0].unsatisfied == []
    # The plan is still invalid: it never reaches (at a c). That is a goal
    # failure, not a precondition failure.
    assert result.status == "INVALID"
    assert result.failed_step is None
    assert [g.expression for g in result.unsatisfied_goals] == ["at(a, c)"]


def test_conjunction_reports_every_failing_conjunct(tmp_path):
    """(on b2 b1) and (clear b2) both fail for `unstack b2 b1`."""
    paths = write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, "(unstack b2 b1)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    expressions = sorted(failure.expression for failure in result.steps[0].unsatisfied)
    assert expressions == ["clear(b2)", "on(b2, b1)"], expressions


def test_failed_steps_always_explain_themselves(tmp_path):
    """Invariant: a FAILED step without an evaluation error has diagnostics."""
    numeric_paths = write_pddl_files(
        tmp_path,
        LOGISTICS_FUEL_DOMAIN,
        LOGISTICS_FUEL_PROBLEM,
        "(drive truck1 loc1 loc2)\n"
        "(drive truck1 loc2 loc3)\n"
        "(drive truck1 loc3 loc2)\n"
        "(drive truck1 loc2 loc3)\n"
        "(drive truck1 loc3 loc2)\n"
        "(drive truck1 loc2 loc3)\n"
        "(drive truck1 loc3 loc2)\n"
        "(drive truck1 loc2 loc3)\n",
    )
    bw_dir = tmp_path / "bw"
    bw_dir.mkdir()
    classical_paths = write_pddl_files(
        bw_dir, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, "(unstack b1 b2)\n(stack b1 b3)\n"
    )

    for paths in (numeric_paths, classical_paths):
        result = PDDLValidator().validate(
            paths["domain"], paths["problem"], paths["plan"]
        )
        failed = [step for step in result.steps if step.status == "FAILED"]
        assert failed, result.report()
        for step in failed:
            assert step.unsatisfied or step.evaluation_error, step
