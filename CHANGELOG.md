# Changelog

All notable changes to PyVAL are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] — 2026-04-11

### Fixed
- Plan structure validation now honors PDDL type hierarchies. Objects whose
  type is a transitive subtype of an action parameter's declared type are
  accepted (e.g., an object typed `depot` satisfies a `place` parameter when
  the domain declares `depot - place`). Previously the `is_compatible` check
  was called with swapped arguments, rejecting every typed IPC benchmark
  (depots, driverlog, rovers, ...) at the structure phase.

### Added
- Regression tests (`tests/test_validator.py`) with a small `vhcl` domain
  exercising both positive (subtype accepted) and negative (sibling branch
  rejected) cases, plus matching fixtures in `tests/conftest.py`.

## [0.1.1] — 2026-04-09

### Added
- Plan quality metric evaluation (minimize/maximize expressions on final state)
- Warnings for unsupported PDDL features (durative actions, PDDL+ processes/events)
- Centralized `__version__` in `pyval/__init__.py`, used by CLI `--version`

## [0.1.0] — 2026-04-08

### Implementation
- Added `pyval/models.py` — all data models (ValidationResult, StepResult, NumericChange, PreconditionFailure, GoalResult, StateSnapshot)
- Added `pyval/syntax_checker.py` — Phase 1: PDDL syntax & semantic validation via UPF PDDLReader
- Added `pyval/validator.py` — Pipeline orchestrator (PDDLValidator class) with Phase 2 plan structure validation inline
- Added `pyval/plan_simulator.py` — Phase 3: step-by-step plan execution via UPSequentialSimulator
- Added `pyval/diagnostics.py` — Precondition decomposition and goal checking with deficit reporting
- Added `pyval/numeric_tracker.py` — Numeric fluent value tracking across plan steps
- Added `pyval/report_formatter.py` — Plain text, JSON, and trajectory table output formatters
- Added `pyval/cli.py` — CLI entry point mirroring VAL's Validate interface
- Added `pyproject.toml` — Project configuration with setuptools build system
- Added test suite: 54 tests covering all 3 pipeline phases, formatters, CLI, and integration with AMLGym benchmarks

### Project Setup
- Added `VALIDATOR_SPEC.md` — full specification for the 3-phase validation pipeline
- Added `CLAUDE.md` — project context and PDDL domain knowledge for agentic coding
- Added `.claude/skills/` — implement, test, and validate-against-val workflows
