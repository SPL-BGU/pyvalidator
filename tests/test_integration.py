"""End-to-end integration tests with real PDDL files and full API cycle."""

import os

import pytest

from pyval import PDDLValidator, ValidationResult

# AMLGym benchmark paths
BENCHMARK_DIR = "/Users/omereliyahu/personal/AMLGym/amlgym/benchmarks"
DOMAINS_DIR = os.path.join(BENCHMARK_DIR, "domains")
PROBLEMS_DIR = os.path.join(BENCHMARK_DIR, "problems", "solving")

has_benchmarks = os.path.isdir(DOMAINS_DIR)


# ---------------------------------------------------------------------------
# Integration tests with inline PDDL (always run)
# ---------------------------------------------------------------------------


def test_full_api_cycle_valid(classical_files):
    """Full cycle: validate -> report -> to_json."""
    v = PDDLValidator()
    result = v.validate(
        classical_files["domain"], classical_files["problem"], classical_files["plan"]
    )
    assert isinstance(result, ValidationResult)
    assert result.is_valid
    assert result.status == "VALID"

    # report() produces a string
    text = result.report()
    assert isinstance(text, str)
    assert "VALID" in text

    # to_json() produces a dict
    j = result.to_json()
    assert isinstance(j, dict)
    assert j["status"] == "VALID"


def test_full_api_cycle_invalid(classical_invalid_files):
    """Full cycle with invalid plan."""
    v = PDDLValidator()
    result = v.validate(
        classical_invalid_files["domain"],
        classical_invalid_files["problem"],
        classical_invalid_files["plan"],
    )
    assert not result.is_valid

    text = result.report()
    assert "INVALID" in text

    j = result.to_json()
    assert j["status"] == "INVALID"


def test_full_api_cycle_numeric(numeric_files):
    """Full cycle with numeric domain."""
    v = PDDLValidator()
    result = v.validate(
        numeric_files["domain"], numeric_files["problem"], numeric_files["plan"]
    )
    assert result.is_valid

    text = result.report()
    assert "VALID" in text

    j = result.to_json()
    assert j["status"] == "VALID"

    # Numeric trajectory available
    assert "fuel" in str(result.numeric_trajectory)


def test_import_public_api():
    """All public types are importable from pyval."""
    from pyval import (
        PDDLValidator,
        ValidationResult,
        StepResult,
        NumericChange,
        PreconditionFailure,
        GoalResult,
        StateSnapshot,
    )
    assert PDDLValidator is not None


# ---------------------------------------------------------------------------
# Integration tests with AMLGym benchmarks (skip if not available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not has_benchmarks, reason="AMLGym benchmarks not found")
class TestBenchmarkDomains:
    """Validate syntax of real IPC benchmark domains."""

    def test_blocksworld_syntax(self):
        v = PDDLValidator()
        domain = os.path.join(DOMAINS_DIR, "blocksworld.pddl")
        problem = os.path.join(PROBLEMS_DIR, "blocksworld", "0_blocksworld_prob.pddl")
        result = v.validate_syntax(domain, problem)
        assert result.is_valid, result.report()

    @pytest.mark.parametrize("domain_name", ["driverlog", "rovers", "satellite", "depots", "ferry"])
    def test_benchmark_domain_syntax(self, domain_name):
        domain = os.path.join(DOMAINS_DIR, f"{domain_name}.pddl")
        problem_dir = os.path.join(PROBLEMS_DIR, domain_name)
        if not os.path.isfile(domain):
            pytest.skip(f"Domain file not found: {domain}")
        if not os.path.isdir(problem_dir):
            pytest.skip(f"Problem dir not found: {problem_dir}")
        # Find first problem file
        problems = sorted(f for f in os.listdir(problem_dir) if f.endswith(".pddl"))
        if not problems:
            pytest.skip(f"No problem files in {problem_dir}")
        problem = os.path.join(problem_dir, problems[0])

        v = PDDLValidator()
        result = v.validate_syntax(domain, problem)
        assert result.is_valid, result.report()
