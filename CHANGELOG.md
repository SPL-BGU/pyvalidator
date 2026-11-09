# Changelog

All notable changes to PyVAL are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- A plan step the simulator cannot evaluate no longer aborts validation with a
  traceback. Reading (or writing) a numeric fluent instance that `:init` never
  assigns makes UPF raise `UPUsageError` from `is_applicable`/`apply`, and
  `PDDLValidator.validate` propagated it out to the CLI. `simulate` in
  `pyval/plan_simulator.py` now catches the evaluation failure, stops the plan
  there and records it on the step (`StepResult.evaluation_error`), naming the
  fluent and the PDDL repair (`Add (= (fuel t2) <value>) to :init.`). The report
  prints `✗ EVALUATION ERROR` and states that the plan could not be validated
  rather than claiming it is invalid — the plan is not proven wrong, it simply
  cannot be checked past that step. The JSON step carries `evaluation_error`.
- The Phase-1 "numeric function has no initial value" warning was decided per
  declared function *name*, so initialising `(fuel t1)` silenced it for
  `(fuel t2)` entirely, and the message claimed the missing value "defaults to
  0". Neither is true: PDDL defines no default for numeric fluents and the
  simulator raises `UPUsageError: The state ... does not have a value for the
  value fuel(t2)` when a precondition or effect reads an unassigned instance
  (validation aborted with a traceback). `_check_numeric_initialization` in
  `pyval/syntax_checker.py` now enumerates the ground instances of every
  numeric function and names the ones `:init` leaves out, with a valid PDDL
  repair hint (`Add (= (fuel t2) <value>) to :init.`). The warning stays a
  warning: a plan that never reads the instance is still valid. Functions with
  more than 250 ground instances are not enumerated and get a summary message
  instead.

### Added
- `tests/test_numeric_init.py`: partial initialisation, fully initialised
  functions, zero-arity functions, summarised long lists, the enumeration bound,
  and a guard against the "defaults to 0" claim coming back.
- `tests/test_evaluation_errors.py`: the precondition and effect crash paths, the
  report wording, the JSON field, and a CLI run that must not print a traceback.

## [0.1.6] — 2026-11-09

### Fixed
- Plan steps whose action or object names differ in case from the parsed
  domain/problem are no longer rejected. PDDL names are case-insensitive and
  UPF's `PDDLReader` lower-cases domain and problem text, but plan tokens were
  looked up exactly as written, so a plan using the declared capitalisation
  (e.g. `(turn_to satellite0 Star0 GroundStation1)` against IPC satellite
  p02–p05, or `(CRAFT_PLANK ...)` against `pogo_stick`) failed with
  `"Action ... is not declared in domain"` / `"object ... is not declared in
  problem"`. VAL accepts these plans. `_name_candidates` in
  `pyval/validator.py` now also tries the lower-case form (and lower-case plus
  `-`→`_`) after the existing candidates, so plans that already resolved pick
  the same name as before. Error messages and step display still show the
  name as written in the plan. Reported as ISS-027 in pddl-copilot-experiments.

### Added
- `tests/test_case_insensitivity.py`: upper-case object, upper-case action,
  mixed case, `-`/`_` with and without upper case, written-case error
  messages and step display, and a regression test on IPC satellite p02 with
  its declared capitalisation (`tests/fixtures/satellite/`).

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

### Removed
- `VALIDATOR_SPEC.md` — content was redundant with `CLAUDE.md` and the inline
  module docs/diagnostic templates in `pyval/`. `CLAUDE.md` is now the single
  authoritative architecture reference; data-model shapes are documented by
  `pyval/models.py` and the JSON schema by `ValidationResult.to_json()`.

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
