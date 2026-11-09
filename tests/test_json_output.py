"""The JSON output must say whether a goal check happened, and what it found.

`phases["goals"]` only ever carried the *unsatisfied* goals and was `null` both
for a syntax-only run and for a VALID plan, so a consumer could not tell "goals
were checked and passed" from "no plan was executed" — and `is_valid` was not in
the payload at all.
"""

import json

from pyval import PDDLValidator
from pyval.report_formatter import format_json
from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    BLOCKSWORLD_VALID_PLAN,
    write_pddl_files,
)


def test_is_valid_is_present_for_every_status(tmp_path):
    paths = write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, BLOCKSWORLD_VALID_PLAN
    )
    valid = format_json(
        PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    )
    assert valid["is_valid"] is True

    syntax_only = format_json(PDDLValidator().validate_syntax(paths["domain"]))
    assert syntax_only["is_valid"] is True
    assert syntax_only["status"] == "VALID"


def test_valid_plan_exposes_every_goal(tmp_path):
    paths = write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, BLOCKSWORLD_VALID_PLAN
    )
    payload = format_json(
        PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    )

    goal_check = payload["phases"]["goal_check"]
    assert [g["expression"] for g in goal_check] == ["on(b3, b2)", "on(b2, b1)", "ontable(b1)"]
    assert all(g["satisfied"] for g in goal_check)
    # Backwards compatibility: the unsatisfied-only key still reads as before.
    assert payload["phases"]["goals"] is None


def test_unevaluable_goals_are_still_listed(tmp_path):
    plan = "(unstack b1 b2)\n(put-down b1)\n"
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, plan)
    payload = format_json(
        PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])
    )

    goal_check = payload["phases"]["goal_check"]
    assert len(goal_check) == 3
    unmet = [g["expression"] for g in goal_check if not g["satisfied"]]
    assert unmet == ["on(b3, b2)", "on(b2, b1)"]
    assert payload["is_valid"] is False


def test_syntax_only_has_no_goal_check(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM)
    payload = format_json(PDDLValidator().validate_syntax(paths["domain"], paths["problem"]))

    assert "goal_check" not in payload["phases"]
    assert payload["phases"]["goals"] is None
    # And it must still be valid JSON when printed, as the CLI does.
    assert json.loads(json.dumps(payload))["status"] == "VALID"
