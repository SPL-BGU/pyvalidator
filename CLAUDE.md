# PyVAL — Pure Python PDDL Validator

A pure-Python PDDL plan validator that replaces compiled VAL binaries. Built on [unified-planning](https://github.com/aiplan4eu/unified-planning). Produces rich, structured diagnostics for LLM consumption.

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Project Structure

```
pyval/
├── cli.py              # CLI entry point (mirrors VAL's Validate interface)
├── validator.py        # Main orchestrator — coordinates the 3-phase pipeline
├── syntax_checker.py   # Phase 1: domain/problem syntax and semantic validation
├── plan_simulator.py   # Phase 3: step-by-step plan execution with diagnostics
├── diagnostics.py      # Diagnostic message generation (repair advice)
├── numeric_tracker.py  # Numeric fluent value tracking across plan steps
├── report_formatter.py # Output formatting (plain text, JSON, trajectory table)
└── models.py           # Dataclasses: ValidationResult, StepResult, etc.
tests/
├── domains/            # Test PDDL files (classical + numeric)
└── ...
```

## Specification

`VALIDATOR_SPEC.md` is the authoritative reference. It defines the 3-phase pipeline, output formats, data models, and diagnostic templates. Read it before making design decisions.

## Architecture

### Dependencies

- **unified-planning** — PDDL parsing (`PDDLReader`), state simulation (`SequentialSimulator`), plan validation (`PlanValidator`), expression evaluation. This is the core engine.
- **pddl-plus-parser** — Optional, for trajectory format compatibility with PlanningCopilot.

### Validation Pipeline (3 phases, halt on FATAL)

1. **Syntax & Semantic** (`syntax_checker.py`) — Parse PDDL, check types/predicates/functions/arity/duplicates.
2. **Plan Structure** (`validator.py`) — Action names exist in domain, parameters are declared objects with correct types.
3. **Plan Execution** (`plan_simulator.py`) — Simulate step-by-step via UPF `SequentialSimulator`, check preconditions, apply effects, verify goals.

### Output Modes

- **Plain text** (default) — VAL-like verbose output, optimized for LLM consumption.
- **Structured JSON** — Machine-readable, see spec for schema.
- **State trajectory** — Numeric fluent values at each plan step.

## Domain Knowledge for AI Agents

### What is PDDL?

PDDL (Planning Domain Definition Language) describes automated planning problems:
- A **domain** defines types, predicates (boolean fluents), functions (numeric fluents), and action schemas with preconditions and effects.
- A **problem** defines objects, initial state (which predicates are true, numeric values), and goal conditions.
- A **plan** is a sequence of grounded actions (action name + specific objects) that transforms the initial state into one satisfying the goals.

### Key PDDL Concepts for Validation

**Requirements** — PDDL features the domain uses:
- `:strips` — basic add/delete effects
- `:typing` — typed objects and parameters
- `:numeric-fluents` — numeric state variables with arithmetic effects (`increase`, `decrease`, `assign`, `scale-up`, `scale-down`)
- `:negative-preconditions` — `(not (pred ...))` in preconditions
- `:equality` — `(= ?x ?y)` tests
- `:conditional-effects` — `(when (condition) (effect))`
- `:action-costs` — plan cost metric using numeric fluents

**Action execution model:**
1. Check ALL preconditions against current state
2. If any fails, the action is inapplicable (plan invalid)
3. If all pass, apply ALL effects simultaneously (not sequentially)
4. Delete effects remove predicates; add effects add them; numeric effects modify function values

**Numeric expressions** — Preconditions can include `(<= (fuel ?v) 10)`, effects can include `(decrease (fuel ?v) (distance ?from ?to))`. Expressions can be nested: `(+ (cost) (* 2 (distance ?a ?b)))`.

**Grounding** — An action schema like `(drive ?truck ?from ?to)` becomes a ground action like `(drive truck1 cityA cityB)` by substituting objects for parameters. Parameters must match declared types.

### unified-planning (UPF) — The Engine

UPF is the Python library PyVAL builds on. Key classes:

```python
from unified_planning.io import PDDLReader
from unified_planning.engines import SequentialSimulator
from unified_planning.plans import SequentialPlan, ActionInstance

# Parse PDDL files
reader = PDDLReader()
problem = reader.parse_problem(domain_path, problem_path)

# Access domain info
problem.actions          # List of action schemas
problem.fluents          # All fluents (boolean + numeric)
problem.user_types       # Type hierarchy
problem.objects(type)    # Objects of a type
problem.initial_values   # Dict[FNode, FNode] — initial state

# Simulate
sim = SequentialSimulator(problem)
state = sim.get_initial_state()
action_instance = ActionInstance(action, tuple(params))
if sim.is_applicable(state, action_instance):
    new_state = sim.apply(state, action_instance)

# Read state values
state.get_value(fluent_expression)  # Returns FNode with .constant_value()
```

**Important UPF patterns:**
- `FNode` is the universal expression type — wraps constants, fluents, and complex expressions.
- `state.get_value(expr)` evaluates any expression against a state.
- `sim.is_applicable()` checks preconditions. `sim.apply()` returns new state (immutable).
- `PDDLReader` throws `UPProblemDefinitionError` on malformed PDDL.
- Plan files: one action per line, format `(action_name param1 param2 ...)`, optional `; cost = N` suffix.

**UPF plan validation (built-in, for reference):**
```python
from unified_planning.engines import PlanValidator
validator = PlanValidator(problem=problem)
result = validator.validate(plan)  # ValidationResult with .status and .log_messages
```
PyVAL wraps and extends this with richer diagnostics — the built-in validator only gives pass/fail, not per-step state changes or repair advice.

### VAL Compatibility

VAL is the C++ reference validator. PyVAL aims for output-format similarity (not exact parity). Key differences:
- VAL uses file-based I/O; PyVAL supports both files and inline strings.
- VAL's `-v` flag gives step-by-step output; PyVAL's plain text mode is similar but more structured.
- VAL's error messages are terse; PyVAL adds repair suggestions and numeric deficit reporting.

### Common Pitfalls in PDDL Validation

1. **Effects are simultaneous** — All effects of an action apply at once. `(and (not (at ?x ?from)) (at ?x ?to))` means the object is removed from `?from` and added to `?to` atomically.
2. **Closed-world assumption** — Any predicate not in the initial state is false. Any numeric function not initialized is 0.
3. **Type hierarchy** — If `truck` is a subtype of `vehicle`, a `(at ?v - vehicle ?l)` predicate accepts trucks.
4. **Numeric precision** — Floating-point comparison with `=` can be fragile. Use small epsilon tolerance.
5. **Empty plans** — A valid plan if goals are already satisfied in the initial state.
6. **Action parameter order matters** — `(drive truck1 A B)` is different from `(drive truck1 B A)`.

## Conventions

- Pure Python, zero compiled dependencies. Must stay `pip install`-able.
- Use `unified-planning` for all PDDL parsing and simulation — do not write custom parsers.
- Test against both classical and numeric domains.
- Diagnostic messages follow templates in `VALIDATOR_SPEC.md` section "Diagnostic Message Guidelines".
- CLI interface mirrors VAL's `Validate` command for familiarity.

## Testing

```bash
pytest                          # All tests
pytest tests/ -k "numeric"     # Numeric-specific tests
pytest tests/ -k "syntax"      # Syntax validation tests
```

Cross-validate results against VAL on IPC benchmark domains when possible.
