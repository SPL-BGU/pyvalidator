# Changelog

All notable changes to PyVAL are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.5] — 2026-05-19

### Fixed
- Plain-text report no longer claims `"All goals satisfied. Plan is VALID."`
  on syntax-only calls (`validate_syntax(domain[, problem])`). The "Goal Check"
  block in `pyval/report_formatter.py` ran unconditionally whenever
  `is_valid=True`, even though no plan had been executed and no goal had been
  checked. The block is now gated on `"execution" in result.phases`; the
  syntax-only success path emits a single accurate line instead:
  `"All syntax and consistency checks passed. No plan was executed."`.
  Downstream consumers that previously string-stripped the leaked verdict
  (pddl-copilot's `pddl-validator` plugin v2.2.0) can drop that workaround.

### Added
- `tests/test_report_formatter.py::test_plain_text_syntax_only_success_domain_and_problem`
  and `::test_plain_text_syntax_only_success_domain_only` lock in the no-plan
  semantics: no `"Plan is VALID/INVALID"`, no `"Goal Check"`, and the new
  success line present.

## [0.1.4] — 2026-04-20

### Fixed
- Numeric comparison goals (`<=`, `>=`, `=`) were always reported as unsatisfied,
  even when satisfied. `_evaluate_goal` in `pyval/diagnostics.py` branched on
  `state.get_value(expr).is_bool_constant()`, which returned a non-bool FNode
  (and no exception) for comparisons — the `else` branch then set `satisfied =
  False` unconditionally. Additionally, `state.get_value` asserts on constant
  and arithmetic sub-expressions (e.g. `(+ (foo) 1)`), so even the fallback path
  could not evaluate `(<= 5 (foo))` or `(<= (+ (foo) 1) (bar))`. Replaced with
  UPF's `StateEvaluator`, which uniformly handles constants, arithmetic, NOT,
  and comparisons. Boolean-goal domains are unaffected. Numeric-goal domains
  (e.g. IPC `counters/p01`, `farmland/p01`) now validate correctly.

### Added
- `tests/test_numeric_goals.py` covering `<=`, `>=`, `=`, arithmetic LHS, and
  mixed boolean/numeric conjunctions, plus skip-guarded regression tests against
  `counters/p01` and `farmland/p01` from `pddl-copilot-experiments`.

## [0.1.3] — 2026-04-15

### Added
- `README.md` with install instructions, CLI usage, Python API, and pipeline overview
- `readme = "README.md"` in `pyproject.toml` so the README renders on PyPI

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
