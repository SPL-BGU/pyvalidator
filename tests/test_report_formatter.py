"""Tests for report formatting: plain text, JSON, trajectory."""

from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    BLOCKSWORLD_VALID_PLAN,
    BLOCKSWORLD_INVALID_PLAN,
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    LOGISTICS_FUEL_VALID_PLAN,
    write_pddl_files,
)

from pyval.validator import PDDLValidator
from pyval.report_formatter import format_plain_text, format_json, format_trajectory


def test_plain_text_valid_plan(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    text = format_plain_text(result)
    assert "Plan is VALID" in text
    assert "Step 1:" in text
    assert "\u2713" in text  # checkmark


def test_plain_text_failed_plan(classical_invalid_files):
    v = PDDLValidator()
    result = v.validate(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    text = format_plain_text(result)
    assert "INVALID" in text
    assert "PRECONDITION FAILURE" in text


def test_plain_text_via_report_method(classical_files):
    """Test that ValidationResult.report() delegates to format_plain_text."""
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    text = result.report()
    assert "Plan is VALID" in text


def test_json_output_schema(classical_files):
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    j = format_json(result)
    assert j["status"] == "VALID"
    assert "syntax" in j["phases"]
    assert "structure" in j["phases"]
    assert "execution" in j["phases"]
    assert j["phases"]["execution"]["status"] == "PASS"
    assert len(j["phases"]["execution"]["steps"]) == 8


def test_json_via_to_json_method(classical_files):
    """Test that ValidationResult.to_json() delegates to format_json."""
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    j = result.to_json()
    assert j["status"] == "VALID"


def test_json_failed_plan(classical_invalid_files):
    v = PDDLValidator()
    result = v.validate(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    j = format_json(result)
    assert j["status"] == "INVALID"
    failed_steps = [s for s in j["phases"]["execution"]["steps"] if s["status"] == "FAILED"]
    assert len(failed_steps) > 0
    assert "unsatisfied_preconditions" in failed_steps[0]


def test_trajectory_table(numeric_files):
    v = PDDLValidator()
    result = v.validate(
        numeric_files["domain"], numeric_files["problem"], numeric_files["plan"]
    )
    table = format_trajectory(result)
    assert "Numeric Fluent Trajectory" in table
    assert "fuel" in table
    assert "[initial state]" in table


def test_trajectory_empty_for_classical(classical_files):
    """Classical domains have no numeric fluents — trajectory should say so."""
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    table = format_trajectory(result)
    assert "No numeric fluents" in table


def test_plain_text_syntax_error(tmp_path):
    bad = "(define (domain bad) (:predicates (foo ?x))"
    paths = write_pddl_files(tmp_path, bad)
    v = PDDLValidator()
    result = v.validate_syntax(paths["domain"])
    text = format_plain_text(result)
    assert "SYNTAX_ERROR" in text
    assert "[ERROR]" in text
