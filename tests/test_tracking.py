"""`--track` must accept the spellings people actually type.

The README documents `pyval ... --trajectory --track fuel`, and that command
printed "No numeric fluents to display." for every domain whose fluent has
arguments: the tracker compared a display name ("fuel truck1") against a
snapshot key ("fuel(truck1)"), and the formatter compared the raw reference
against the same key, so nothing ever matched.
"""

import subprocess
import sys

from pyval import PDDLValidator
from pyval.numeric_tracker import (
    fluent_reference_matches,
    parse_fluent_reference,
)
from pyval.report_formatter import format_json, format_plain_text, format_trajectory
from tests.conftest import (
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    LOGISTICS_FUEL_VALID_PLAN,
    write_pddl_files,
)


def _files(tmp_path):
    return write_pddl_files(
        tmp_path, LOGISTICS_FUEL_DOMAIN, LOGISTICS_FUEL_PROBLEM, LOGISTICS_FUEL_VALID_PLAN
    )


def _validate(files, tracked):
    return PDDLValidator().validate(
        files["domain"], files["problem"], files["plan"], tracked_fluents=tracked
    )


def test_parse_reference_spellings():
    assert parse_fluent_reference("fuel") == ("fuel", None)
    assert parse_fluent_reference("fuel truck1") == ("fuel", ("truck1",))
    assert parse_fluent_reference("fuel(truck1)") == ("fuel", ("truck1",))
    assert parse_fluent_reference("distance(loc1, loc2)") == ("distance", ("loc1", "loc2"))


def test_matching_bare_name_covers_every_instance():
    assert fluent_reference_matches("fuel", "fuel(truck1)")
    assert fluent_reference_matches("fuel", "fuel(truck2)")
    assert not fluent_reference_matches("fuel", "distance(loc1, loc2)")


def test_matching_single_instance():
    assert fluent_reference_matches("fuel truck1", "fuel(truck1)")
    assert fluent_reference_matches("fuel(truck1)", "fuel(truck1)")
    assert not fluent_reference_matches("fuel truck2", "fuel(truck1)")
    assert fluent_reference_matches("distance loc1 loc2", "distance(loc1, loc2)")


def test_bare_function_name_tracks_all_instances(tmp_path):
    result = _validate(_files(tmp_path), ["fuel"])
    assert list(result.numeric_trajectory) == ["fuel(truck1)"]
    assert result.numeric_trajectory["fuel(truck1)"][:2] == [100.0, 90.0]


def test_instance_name_tracks_one_fluent(tmp_path):
    result = _validate(_files(tmp_path), ["distance loc1 loc2", "fuel truck1"])
    assert set(result.numeric_trajectory) == {"fuel(truck1)", "distance(loc1, loc2)"}


def test_trajectory_tables_the_tracked_fluent(tmp_path):
    files = _files(tmp_path)
    result = _validate(files, ["fuel"])
    table = format_trajectory(result, tracked=["fuel"])

    assert "fuel(truck1)" in table
    assert "distance" not in table
    assert "100" in table


def test_unknown_track_reference_is_reported(tmp_path):
    files = _files(tmp_path)
    result = _validate(files, ["fuell"])

    assert result.numeric_trajectory == {}
    assert any("'fuell' matches no numeric fluent" in w for w in result.warnings)
    assert any("fuel(truck1)" in w for w in result.warnings if "'fuell'" in w)

    text = format_plain_text(result)
    assert "=== Warnings ===" in text
    assert "'fuell' matches no numeric fluent" in text
    assert format_json(result)["warnings"]


def test_no_warning_when_every_reference_matches(tmp_path):
    result = _validate(_files(tmp_path), ["fuel", "distance"])
    assert not [w for w in result.warnings if "matches no numeric fluent" in w]


def test_cli_readme_command_tracks_fuel(tmp_path):
    """The exact command from the README: --trajectory --track fuel."""
    files = _files(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyval.cli",
            files["domain"],
            files["problem"],
            files["plan"],
            "--trajectory",
            "--track",
            "fuel",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "fuel(truck1)" in completed.stdout
    assert "No numeric fluents" not in completed.stdout
