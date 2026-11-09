# PyVAL — Pure Python PDDL Plan Validator

[![PyPI](https://img.shields.io/pypi/v/pddl-pyvalidator.svg)](https://pypi.org/project/pddl-pyvalidator/)
[![Python](https://img.shields.io/pypi/pyversions/pddl-pyvalidator.svg)](https://pypi.org/project/pddl-pyvalidator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A pure-Python PDDL plan validator — a drop-in alternative to the compiled [VAL](https://github.com/KCL-Planning/VAL) binary. Built on [unified-planning](https://github.com/aiplan4eu/unified-planning), zero compiled dependencies, `pip install`-able everywhere.

PyVAL produces rich, structured diagnostics designed for both humans and LLM consumption: per-step state changes, precondition deficit reporting, and repair-oriented messages.

## Install

```bash
pip install pddl-pyvalidator
```

## Quick Start

```bash
# Validate a plan against a domain and problem
pyval domain.pddl problem.pddl plan.txt

# JSON output for tool integration
pyval domain.pddl problem.pddl plan.txt --json

# Numeric fluent trajectory (one row per step)
pyval domain.pddl problem.pddl plan.txt --trajectory --track fuel --track cost

# Syntax check only (domain, or domain + problem)
pyval domain.pddl
pyval domain.pddl problem.pddl
```

Exit code is `0` on a valid plan, `1` otherwise.

## Python API

```python
from pyval import PDDLValidator

validator = PDDLValidator()
result = validator.validate(
    domain_path="domain.pddl",
    problem_path="problem.pddl",
    plan_path="plan.txt",
)

if result.is_valid:
    print("Plan is valid")
else:
    for err in result.errors:
        print(err)
```

## What Gets Validated

PyVAL runs a three-phase pipeline and halts on the first fatal error:

1. **Syntax & semantic** — PDDL parses, types/predicates/functions are well-formed, no duplicates or arity mismatches.
2. **Plan structure** — every action name exists in the domain, parameters are declared objects with type-compatible (subtype-aware) bindings.
3. **Plan execution** — each step's preconditions hold, effects apply, and goals are satisfied in the final state. Numeric fluents are tracked across steps; quality metrics (`minimize` / `maximize`) are evaluated on the final state.

Unsupported PDDL features (durative actions, PDDL+ processes/events) are reported as warnings rather than silent failures.

Numeric fluents have no default value in PDDL, so `:init` must assign every
instance an action reads or writes. Phase 1 warns about the instances a written
function leaves out; if the simulator still cannot evaluate a step at execution
time, validation stops there and reports `EVALUATION ERROR` naming the fluent and
the repair, instead of claiming the plan is invalid — an unevaluable step proves
nothing about the plan.

## Output Modes

- **Plain text** (default, VAL-like, optionally `-v` for per-step detail)
- **JSON** (`--json`) — structured for programmatic consumption
- **Trajectory** (`--trajectory`) — numeric fluent values per step, optionally filtered via `--track`

`--track` accepts the bare function name (`--track fuel`, every instance of `fuel`),
one instance in PDDL spelling (`--track "fuel truck1"`), or UPF's rendering
(`--track "fuel(truck1)"`). A reference that matches no numeric fluent is reported
as a warning listing the fluents that exist, rather than printing an empty table.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

See `CLAUDE.md` for architecture notes and the validation pipeline overview.

## License

MIT — see [LICENSE](LICENSE).
