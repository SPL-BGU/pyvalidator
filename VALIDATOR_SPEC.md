# PyVAL — Python PDDL Validator Specification

## Overview

PyVAL is a pure-Python PDDL plan validator designed to replace compiled VAL binaries in LLM-augmented planning pipelines. It produces rich, structured diagnostic output suitable for consumption by Large Language Models (LLMs) operating as planning copilots.

Built on top of the [Unified Planning Framework (UPF)](https://github.com/aiplan4eu/unified-planning), PyVAL supports both classical and numeric PDDL domains and requires zero compiled dependencies — it is fully pip-installable.

---

## Goals

1. **Drop-in replacement** for VAL's `validate` binary in MCP-based planning tool servers (e.g., SPL-BGU/PlanningCopilot).
2. **Rich diagnostic output** — match or exceed VAL's verbose mode (`-v`) and error reporting (`-e`) quality, with output structured for LLM parsing.
3. **Classical + Numeric PDDL support** — handle `:strips`, `:typing`, `:numeric-fluents`, `:negative-preconditions`, `:equality`, `:conditional-effects`, and `:action-costs`.
4. **Zero compiled dependencies** — pure Python, pip-installable, no Docker, no platform-specific binaries.
5. **Programmatic API** — usable both as a CLI tool and as an importable Python library.

---

## Scope

### In Scope

- PDDL domain syntax validation (type checking, predicate/function declarations, action schema well-formedness).
- PDDL problem validation against a domain (object types, initial state consistency, goal well-formedness).
- Sequential plan validation (precondition checking, effect application, goal verification).
- Numeric fluent tracking throughout plan execution (increase, decrease, assign, scale-up, scale-down effects).
- Numeric precondition evaluation (comparisons: `<`, `<=`, `=`, `>=`, `>` over arithmetic expressions).
- Detailed per-step diagnostic reports when validation fails.
- Repair advice generation (identifying unsatisfied preconditions and suggesting fixes).
- State trajectory extraction (fluent values at each step of the plan).
- Goal achievement analysis (which goals are met/unmet after plan execution).

### Out of Scope (v1)

- Temporal plan validation (durative actions, `at start`/`at end`/`over all` conditions).
- PDDL+ features (processes, events, continuous change).
- Derived predicates / axioms.
- Multi-agent plan validation.
- LaTeX report generation.
- Plan optimization metric evaluation (may be added in a future version).

---

## Architecture

### Dependencies

| Package | Purpose |
|---|---|
| `unified-planning` | PDDL parsing (`PDDLReader`), state simulation (`SequentialSimulator`), plan validation (`PlanValidator`), expression evaluation |
| `pddl-plus-parser` | Trajectory I/O format compatibility with PlanningCopilot's `get_state_transition` tool (optional integration layer) |

### Core Modules

```
pyval/
├── __init__.py
├── cli.py                  # CLI entry point (mirrors VAL's Validate interface)
├── validator.py            # Main validation orchestrator
├── syntax_checker.py       # Domain/problem syntax and semantic validation
├── plan_simulator.py       # Step-by-step plan simulation with diagnostics
├── diagnostics.py          # Diagnostic message generation (RepairAdvice equivalent)
├── numeric_tracker.py      # Numeric fluent value tracking across plan steps
├── report_formatter.py     # Output formatting (plain text, structured JSON)
└── models.py               # Data classes for validation results
```

---

## Validation Pipeline

The validator operates in three sequential phases. Execution halts at the first phase that produces errors of severity `FATAL`.

### Phase 1 — Syntax & Semantic Validation

Validates domain and problem files independently and against each other.

**Checks performed:**

- PDDL parse success (well-formed S-expressions, valid keywords).
- All types referenced in predicates, functions, actions, and objects are declared.
- All predicates and functions used in preconditions and effects are declared with correct arity.
- Action parameters have declared types.
- No duplicate predicate, function, type, action, or object names.
- Problem domain name matches the provided domain.
- All objects in the problem have types declared in the domain.
- Initial state only references declared predicates/functions with correct arity and types.
- Goal formula only references declared predicates/functions with correct arity and types.
- Numeric function initial values are assigned where expected.

**Output on failure:**

```
=== Syntax & Semantic Validation ===
[ERROR] Domain: Action 'move' references undeclared predicate 'at_robot' (did you mean 'robot_at'?)
[ERROR] Domain: Function '(distance ?from ?to)' declared with types (city, city) but used in action 'drive' with types (location, location)
[WARNING] Problem: Numeric function '(fuel truck1)' has no initial value assigned — defaults to 0
```

### Phase 2 — Plan Structure Validation

Validates the plan file against the domain and problem.

**Checks performed:**

- Plan file parses correctly (action names and parameters per line).
- Every action name in the plan corresponds to a declared action in the domain.
- Every action parameter in the plan corresponds to a declared object in the problem.
- Parameter types match action schema parameter types.
- No empty plan when goals are not satisfied in the initial state.

**Output on failure:**

```
=== Plan Structure Validation ===
[ERROR] Step 3: Action 'pick_up' is not declared in domain 'logistics'
[ERROR] Step 7: Action 'drive(truck1, depot, city3)' — object 'city3' is not declared in problem
[ERROR] Step 7: Action 'drive(truck1, depot, city3)' — parameter 3 expects type 'location', got undeclared object
```

### Phase 3 — Plan Execution Simulation

Simulates the plan step-by-step using UPF's `SequentialSimulator`, checking preconditions and applying effects at each step.

**For each action in the plan:**

1. Evaluate all preconditions against the current state.
2. If any precondition is unsatisfied, report:
   - Which precondition failed.
   - The current values of all fluents involved in the failed precondition.
   - A human-readable explanation of what would need to change.
3. If all preconditions are met, apply the action's effects and advance the state.
4. Record all fluent values that changed (boolean and numeric).

**After all actions:**

5. Evaluate goal satisfaction against the final state.
6. Report which goals are met and which are unmet (with current values for numeric goals).

**Output on success:**

```
=== Plan Execution ===
Step 1: (drive truck1 depot loc1) ✓
  Changed: (at truck1 depot) = false, (at truck1 loc1) = true, (fuel truck1) = 92 (was 100)
Step 2: (load pkg1 truck1 loc1) ✓
  Changed: (in pkg1 truck1) = true, (at_pkg pkg1 loc1) = false
Step 3: (drive truck1 loc1 loc2) ✓
  Changed: (at truck1 loc1) = false, (at truck1 loc2) = true, (fuel truck1) = 84 (was 92)

=== Goal Check ===
All goals satisfied. Plan is VALID.
Plan length: 3 actions
Final state numeric values: (fuel truck1) = 84
```

**Output on failure:**

```
=== Plan Execution ===
Step 1: (drive truck1 depot loc1) ✓
  Changed: (at truck1 depot) = false, (at truck1 loc1) = true, (fuel truck1) = 92 (was 100)
Step 2: (drive truck1 loc1 loc3) ✗ PRECONDITION FAILURE
  Unsatisfied: (>= (fuel truck1) 20)
    Current value: (fuel truck1) = 8
    Required: (fuel truck1) >= 20
    Deficit: 12 units
  Unsatisfied: (connected loc1 loc3)
    Current value: false
    Explanation: No direct connection exists between loc1 and loc3

Plan is INVALID. Failed at step 2 of 5.
Remaining actions not executed: 3
```

---

## Output Modes

### Plain Text (default)

Human-readable output matching VAL's verbose style. This is the primary mode for LLM consumption via MCP tools.

### Structured JSON

Machine-readable output for programmatic integration.

```json
{
  "status": "INVALID",
  "phases": {
    "syntax": {"status": "PASS", "errors": [], "warnings": []},
    "structure": {"status": "PASS", "errors": [], "warnings": []},
    "execution": {
      "status": "FAIL",
      "failed_step": 2,
      "total_steps": 5,
      "steps": [
        {
          "index": 1,
          "action": "(drive truck1 depot loc1)",
          "status": "OK",
          "changes": {
            "boolean": {"(at truck1 depot)": false, "(at truck1 loc1)": true},
            "numeric": {"(fuel truck1)": {"before": 100, "after": 92}}
          }
        },
        {
          "index": 2,
          "action": "(drive truck1 loc1 loc3)",
          "status": "FAILED",
          "unsatisfied_preconditions": [
            {
              "expression": "(>= (fuel truck1) 20)",
              "type": "numeric",
              "current_values": {"(fuel truck1)": 8},
              "required": ">= 20",
              "deficit": 12
            },
            {
              "expression": "(connected loc1 loc3)",
              "type": "boolean",
              "current_value": false
            }
          ]
        }
      ]
    },
    "goals": null
  }
}
```

### State Trajectory (ValueSeq equivalent)

Numeric fluent values tracked across the entire plan execution.

```
=== Numeric Fluent Trajectory ===
Step | Action                      | (fuel truck1) | (packages_delivered)
-----|-----------------------------|--------------:|--------------------:
  0  | [initial state]             |           100 |                   0
  1  | (drive truck1 depot loc1)   |            92 |                   0
  2  | (load pkg1 truck1 loc1)     |            92 |                   0
  3  | (drive truck1 loc1 loc2)    |            84 |                   0
  4  | (unload pkg1 truck1 loc2)   |            84 |                   1
```

---

## API Interface

### Python API

```python
from pyval import PDDLValidator, ValidationResult

# Initialize validator
validator = PDDLValidator()

# Validate domain only (syntax check)
result: ValidationResult = validator.validate_syntax(domain_path="domain.pddl")

# Validate domain + problem (syntax + consistency check)
result: ValidationResult = validator.validate_syntax(
    domain_path="domain.pddl",
    problem_path="problem.pddl"
)

# Validate domain + problem + plan (full validation)
result: ValidationResult = validator.validate(
    domain_path="domain.pddl",
    problem_path="problem.pddl",
    plan_path="plan.txt"
)

# Access results
print(result.is_valid)              # bool
print(result.status)                # "VALID" | "INVALID" | "SYNTAX_ERROR" | "STRUCTURE_ERROR"
print(result.report())              # Plain text report (for LLM consumption)
print(result.to_json())             # Structured JSON
print(result.trajectory)            # List of state snapshots
print(result.failed_step)           # Step index where failure occurred (or None)
print(result.unsatisfied_goals)     # List of unmet goals in final state
print(result.numeric_trajectory)    # Dict of numeric fluent values per step

# Get specific step diagnostics
step = result.steps[1]
print(step.action)                  # "(drive truck1 loc1 loc3)"
print(step.status)                  # "FAILED"
print(step.unsatisfied)             # List of unsatisfied precondition diagnostics
```

### CLI Interface

```bash
# Syntax validation only
pyval domain.pddl

# Domain + problem validation
pyval domain.pddl problem.pddl

# Full plan validation (verbose)
pyval -v domain.pddl problem.pddl plan.txt

# JSON output
pyval --json domain.pddl problem.pddl plan.txt

# Numeric trajectory output
pyval --trajectory domain.pddl problem.pddl plan.txt

# Specific numeric fluent tracking (ValueSeq equivalent)
pyval --track "fuel truck1" --track "packages_delivered" domain.pddl problem.pddl plan.txt
```

### MCP Tool Interface

Drop-in replacement for PlanningCopilot's `validate_pddl_syntax` tool:

```python
@mcp.tool()
def validate_pddl_syntax(domain: str, problem: str = None, plan: str = None) -> str:
    """Validates PDDL domain/problem/plan using PyVAL."""
    validator = PDDLValidator()

    if plan is not None:
        result = validator.validate(
            domain_path=domain,
            problem_path=problem,
            plan_path=plan
        )
    elif problem is not None:
        result = validator.validate_syntax(
            domain_path=domain,
            problem_path=problem
        )
    else:
        result = validator.validate_syntax(domain_path=domain)

    return result.report()
```

---

## Data Models

```python
@dataclass
class ValidationResult:
    status: Literal["VALID", "INVALID", "SYNTAX_ERROR", "STRUCTURE_ERROR"]
    is_valid: bool
    phases: dict                          # Phase-level results
    steps: list[StepResult]               # Per-action results
    trajectory: list[StateSnapshot]       # Full state at each step
    numeric_trajectory: dict[str, list]   # Fluent name -> values per step
    failed_step: int | None               # First failure index
    unsatisfied_goals: list[GoalResult]   # Unmet goals after execution
    warnings: list[str]                   # Non-fatal warnings

@dataclass
class StepResult:
    index: int
    action: str
    status: Literal["OK", "FAILED"]
    boolean_changes: dict[str, bool]
    numeric_changes: dict[str, NumericChange]
    unsatisfied: list[PreconditionFailure]

@dataclass
class NumericChange:
    before: float
    after: float

@dataclass
class PreconditionFailure:
    expression: str                       # The precondition as PDDL string
    type: Literal["boolean", "numeric"]
    current_values: dict[str, Any]        # Current values of involved fluents
    explanation: str                       # Human-readable explanation
    deficit: float | None                 # For numeric: how far from satisfaction

@dataclass
class GoalResult:
    expression: str
    satisfied: bool
    current_values: dict[str, Any]

@dataclass
class StateSnapshot:
    step: int
    action: str | None                    # None for initial state
    boolean_fluents: dict[str, bool]
    numeric_fluents: dict[str, float]
```

---

## Diagnostic Message Guidelines

Diagnostic messages are the primary interface between PyVAL and the LLM. They must be:

1. **Specific** — always name the exact precondition, fluent, action, and step involved.
2. **Quantitative** — for numeric failures, always report current value, required threshold, and deficit.
3. **Actionable** — suggest what would need to change for the precondition to be satisfied.
4. **Consistent** — use the same PDDL notation the LLM sees in the domain/problem files.
5. **Concise** — avoid boilerplate; every line should carry information.

### Diagnostic Templates

**Boolean precondition failure:**
```
Unsatisfied: ({predicate} {args})
  Current value: false
  Explanation: {predicate}({args}) is not true in the current state.
  Last made true at: Step {n} by action ({action})  [if applicable]
  Last made false at: Step {n} by action ({action}) [if applicable]
```

**Numeric precondition failure:**
```
Unsatisfied: ({comparator} ({expression}) {threshold})
  Current value: ({fluent}) = {value}
  Required: ({fluent}) {comparator} {threshold}
  Deficit: {abs(threshold - value)} units
```

**Goal not achieved:**
```
Unmet goal: ({goal_expression})
  Current value: {value}
  Required: {description}
  Nearest achieving action: {action_name} (sets this to true / modifies this fluent)
```

---

## Compatibility Notes

- **VAL output parity**: PyVAL's plain-text output should be parseable by any system that currently parses VAL's verbose output. The format is intentionally similar but not identical — it is optimized for LLM consumption rather than strict backward compatibility.
- **PlanningCopilot integration**: The MCP tool function signature matches the existing `validate_pddl_syntax` tool in `solvers_server.py`, allowing a one-line swap.
- **Plan file format**: Accepts IPC-standard plan format (one grounded action per line, optional cost comments).

---

## Implementation Reference

The validation logic is informed by studying the following VAL source files (BSD 3-Clause licensed):

| VAL Source File | PyVAL Equivalent | Purpose |
|---|---|---|
| `Validator.cpp` | `plan_simulator.py` | Main simulation loop: precondition check → effect apply → advance |
| `RepairAdvice.cpp` | `diagnostics.py` | Diagnostic message generation for failed preconditions |
| `State.cpp` | UPF `SequentialSimulator` | State representation and update semantics |
| `FuncExp.cpp` | UPF expression evaluation | Numeric expression evaluation |
| `typecheck.cpp` | `syntax_checker.py` | Type hierarchy and arity checking |
| `Plan.cpp` | `validator.py` | Plan parsing and action-to-schema matching |

---

## Testing Strategy

- **Unit tests** for each validation phase independently.
- **Cross-validation against VAL** on IPC benchmark domains (classical + numeric) to verify agreement on valid/invalid verdicts.
- **Diagnostic quality tests** — for known-invalid plans, assert that the diagnostic output contains the specific precondition, current value, and step number.
- **Numeric precision tests** — validate correct handling of floating-point arithmetic in numeric fluent tracking.
- **Regression suite** from VAL's known bug cases (plans that VAL incorrectly accepts/rejects).
