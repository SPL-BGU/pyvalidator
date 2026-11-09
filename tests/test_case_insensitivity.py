"""PDDL names are case-insensitive: plan steps must resolve regardless of case.

UPF's PDDLReader lower-cases domain and problem text on read, but plan tokens
are kept as written. Plan-name lookup must therefore case-fold, while error
messages and step display keep the name exactly as the user wrote it.
"""

from pathlib import Path

from tests.conftest import write_pddl_files

from pyval.validator import PDDLValidator

FIXTURES = Path(__file__).parent / "fixtures"

# Upper-case action names and objects, plus one hyphenated action.
CASE_DOMAIN = """\
(define (domain caseworld)
  (:requirements :strips :typing)
  (:types loc)
  (:predicates (at ?l - loc) (visited ?l - loc))
  (:action MOVE_TO
    :parameters (?from - loc ?to - loc)
    :precondition (at ?from)
    :effect (and (not (at ?from)) (at ?to) (visited ?to)))
  (:action go-back
    :parameters (?from - loc ?to - loc)
    :precondition (at ?from)
    :effect (and (not (at ?from)) (at ?to)))
)
"""

CASE_PROBLEM = """\
(define (problem case1)
  (:domain caseworld)
  (:objects Home Store - loc)
  (:init (at Home))
  (:goal (and (visited Store) (at Home)))
)
"""


def _validate(tmp_path, plan):
    paths = write_pddl_files(tmp_path, CASE_DOMAIN, CASE_PROBLEM, plan)
    return PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])


def test_upper_case_object_in_plan(tmp_path):
    result = _validate(tmp_path, "(move_to Home Store)\n(go-back Store Home)\n")
    assert result.is_valid, result.report()


def test_upper_case_action_name_in_plan(tmp_path):
    result = _validate(tmp_path, "(MOVE_TO home store)\n(go-back store home)\n")
    assert result.is_valid, result.report()


def test_mixed_case_names_in_plan(tmp_path):
    result = _validate(tmp_path, "(Move_To hOmE STORE)\n(Go-Back Store home)\n")
    assert result.is_valid, result.report()


# Lookup retries "-" as "_" (plan `move-to` for domain `move_to`). The reverse
# direction was never supported and is intentionally left unchanged.
def test_hyphen_underscore_still_resolves(tmp_path):
    result = _validate(tmp_path, "(move-to home store)\n(go-back store home)\n")
    assert result.is_valid, result.report()


def test_hyphen_underscore_with_upper_case(tmp_path):
    result = _validate(tmp_path, "(MOVE-TO Home Store)\n(GO-BACK Store Home)\n")
    assert result.is_valid, result.report()


def test_step_display_keeps_written_case(tmp_path):
    result = _validate(tmp_path, "(MOVE_TO Home Store)\n(go-back Store Home)\n")
    assert result.is_valid
    assert result.steps[0].action == "(MOVE_TO Home Store)"


def test_unknown_object_error_keeps_written_case(tmp_path):
    result = _validate(tmp_path, "(MOVE_TO Home Nowhere)\n")
    assert result.status == "STRUCTURE_ERROR"
    errors = result.phases["structure"]["errors"]
    assert any("'Nowhere'" in e for e in errors), errors
    assert any("'MOVE_TO'" in e for e in errors), errors


def test_unknown_action_error_keeps_written_case(tmp_path):
    result = _validate(tmp_path, "(FLY_TO Home Store)\n")
    assert result.status == "STRUCTURE_ERROR"
    errors = result.phases["structure"]["errors"]
    assert any("'FLY_TO'" in e for e in errors), errors


# Real IPC input: satellite p02 declares GroundStation1, Star0, Phenomenon2,
# Star3. A plan using the declared capitalisation must validate (VAL accepts).
SATELLITE_P02_PLAN = """\
(switch_on instrument2 satellite1)
(turn_to satellite1 Phenomenon2 GroundStation1)
(turn_to satellite1 Star0 Phenomenon2)
(calibrate satellite1 instrument2 Star0)
(turn_to satellite1 Phenomenon2 Star0)
(take_image satellite1 Phenomenon2 instrument2 thermograph0)
(turn_to satellite1 Star3 Phenomenon2)
(take_image satellite1 Star3 instrument2 thermograph0)
(turn_to satellite0 GroundStation1 Star0)
"""


def test_satellite_p02_declared_case_plan(tmp_path):
    plan = tmp_path / "p02.plan"
    plan.write_text(SATELLITE_P02_PLAN)
    sat = FIXTURES / "satellite"
    result = PDDLValidator().validate(
        str(sat / "domain.pddl"), str(sat / "p02.pddl"), str(plan)
    )
    assert result.is_valid, result.report()
