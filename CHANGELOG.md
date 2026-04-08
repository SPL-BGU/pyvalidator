# Changelog

All notable changes to PyVAL are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
