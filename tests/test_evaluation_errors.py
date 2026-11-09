"""A plan step the simulator cannot evaluate must be reported, not raised.

Both crash paths are covered: a precondition reading a numeric fluent instance
that ``:init`` never assigns (``sim.is_applicable`` raises ``UPUsageError``) and
an effect that writes one (``sim.apply`` raises). Before this, ``validate()``
propagated the UPF exception, so the CLI died with a traceback instead of
producing a report.
"""

from pyval import PDDLValidator
from pyval.report_formatter import format_json, format_plain_text
from tests.conftest import write_pddl_files


PARTIAL_DOMAIN = """\
(define (domain partial)
  (:requirements :strips :typing :numeric-fluents)
  (:types truck loc)
  (:predicates (at ?t - truck ?l - loc) (link ?a - loc ?b - loc))
  (:functions (fuel ?t - truck) (distance ?a - loc ?b - loc))
  (:action drive
    :parameters (?t - truck ?from - loc ?to - loc)
    :precondition (and (at ?t ?from) (link ?from ?to)
                       (>= (fuel ?t) (distance ?from ?to)))
    :effect (and (not (at ?t ?from)) (at ?t ?to)
                 (decrease (fuel ?t) (distance ?from ?to))))
)
"""


def _partial_problem(init: str) -> str:
    return f"""\
(define (problem partial-p1)
  (:domain partial)
  (:objects t1 t2 - truck l1 l2 - loc)
  (:init (at t1 l1) (at t2 l1) (link l1 l2) (= (distance l1 l2) 10)
    {init}
  )
  (:goal (at t1 l2))
)
"""


def test_uninitialised_precondition_fluent_is_reported(tmp_path):
    """The second truck's fuel has no value: precondition evaluation raises."""
    paths = write_pddl_files(
        tmp_path,
        PARTIAL_DOMAIN,
        _partial_problem("(= (fuel t1) 50)"),
        "(drive t1 l1 l2)\n(drive t2 l1 l2)\n",
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert not result.is_valid
    assert result.failed_step == 2
    failed = result.steps[1]
    assert failed.status == "FAILED"
    assert failed.unsatisfied == []
    assert failed.evaluation_error is not None
    assert "fuel(t2)" in failed.evaluation_error
    assert "Add (= (fuel t2) <value>) to :init." in failed.evaluation_error


def test_uninitialised_effect_fluent_is_reported(tmp_path):
    """An effect that increases a fluent with no value raises in sim.apply."""
    domain = """\
(define (domain apperr)
  (:requirements :strips :typing :numeric-fluents)
  (:types thing)
  (:predicates (done ?x - thing))
  (:functions (cost ?x - thing))
  (:action bump
    :parameters (?x - thing)
    :precondition (and)
    :effect (and (done ?x) (increase (cost ?x) 1)))
)
"""
    problem = """\
(define (problem apperr-p1)
  (:domain apperr)
  (:objects a b - thing)
  (:init (= (cost a) 0))
  (:goal (done b))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem, "(bump a)\n(bump b)\n")
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert not result.is_valid
    assert result.failed_step == 2
    assert "cost(b)" in result.steps[1].evaluation_error
    assert result.steps[0].status == "OK"


def test_report_does_not_claim_the_plan_is_invalid(tmp_path):
    """An unevaluable step means "unknown", not "invalid"."""
    paths = write_pddl_files(
        tmp_path, PARTIAL_DOMAIN, _partial_problem("(= (fuel t1) 50)"), "(drive t2 l1 l2)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    text = format_plain_text(result)

    assert "EVALUATION ERROR" in text
    assert "No value in the current state for fuel(t2)" in text
    assert "Plan could not be validated" in text
    assert "Plan is INVALID" not in text


def test_json_carries_the_evaluation_error(tmp_path):
    paths = write_pddl_files(
        tmp_path, PARTIAL_DOMAIN, _partial_problem("(= (fuel t1) 50)"), "(drive t2 l1 l2)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    payload = format_json(result)
    step = payload["phases"]["execution"]["steps"][0]

    assert step["status"] == "FAILED"
    assert step["unsatisfied_preconditions"] == []
    assert "fuel(t2)" in step["evaluation_error"]


def test_cli_survives_the_unevaluable_step(tmp_path):
    """The CLI printed a traceback and exited non-zero before; now it reports."""
    import subprocess
    import sys

    paths = write_pddl_files(
        tmp_path, PARTIAL_DOMAIN, _partial_problem("(= (fuel t1) 50)"), "(drive t2 l1 l2)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-m", "pyval.cli", paths["domain"], paths["problem"], paths["plan"]],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    assert "EVALUATION ERROR" in completed.stdout


def test_message_names_only_the_missing_fluent(tmp_path):
    """The UPF message embeds the whole state; only the fluent name survives."""
    paths = write_pddl_files(
        tmp_path, PARTIAL_DOMAIN, _partial_problem("(= (fuel t1) 50)"), "(drive t2 l1 l2)\n"
    )
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    message = result.steps[0].evaluation_error
    assert "{" not in message and "at(t1, l1)" not in message
