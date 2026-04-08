"""Tests for CLI entry point."""

import json
import subprocess
import sys

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


def _run_pyval(*args):
    """Run pyval CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "pyval.cli", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_domain_only_syntax_check(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN)
    code, out, err = _run_pyval(paths["domain"])
    assert code == 0


def test_full_validation_valid_plan(classical_files):
    code, out, err = _run_pyval(
        classical_files["domain"],
        classical_files["problem"],
        classical_files["plan"],
    )
    assert code == 0
    assert "VALID" in out


def test_full_validation_invalid_plan(classical_invalid_files):
    code, out, err = _run_pyval(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    assert code == 1
    assert "INVALID" in out


def test_json_output_flag(classical_files):
    code, out, err = _run_pyval(
        "--json",
        classical_files["domain"],
        classical_files["problem"],
        classical_files["plan"],
    )
    assert code == 0
    data = json.loads(out)
    assert data["status"] == "VALID"


def test_trajectory_flag(numeric_files):
    code, out, err = _run_pyval(
        "--trajectory",
        numeric_files["domain"],
        numeric_files["problem"],
        numeric_files["plan"],
    )
    assert code == 0
    assert "Trajectory" in out
    assert "fuel" in out


def test_exit_code_valid(classical_files):
    code, _, _ = _run_pyval(
        classical_files["domain"],
        classical_files["problem"],
        classical_files["plan"],
    )
    assert code == 0


def test_exit_code_invalid(classical_invalid_files):
    code, _, _ = _run_pyval(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    assert code == 1
