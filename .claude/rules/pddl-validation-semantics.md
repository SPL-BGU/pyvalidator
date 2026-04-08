---
description: PDDL plan validation correctness rules — action parsing, grounding, precondition checking, goal evaluation
paths:
  - "pyval/plan_simulator.py"
  - "pyval/syntax_checker.py"
  - "pyval/validator.py"
  - "pyval/diagnostics.py"
  - "pyval/numeric_tracker.py"
---

## Action String Parsing (Plan Files)

Plan file format: one action per line as `(action_name param1 param2)`.
- Strip outer parentheses, split on whitespace
- First token is action name, rest are parameter object names
- Handle optional `; cost = N` suffix (IPC format) — strip everything after `;`
- Handle both formats: `(pick-up b1)` and `pick-up b1` (with and without parens)
- Empty lines and lines starting with `;` are comments — skip them

Production pattern from AMLGym `UPEnv._str_to_action()`:
```python
action_split = action_label.strip()[1:-1].split()  # strip parens, split
op_name = action_split[0]
obj_names = [o.strip() for o in action_split[1:]]
up_op = problem.action(op_name)
up_objs = [problem.object(o) for o in obj_names]
action_instance = ActionInstance(up_op, up_objs)
```

## State Representation for Validation

Use UP's state objects directly — do NOT convert to `Set[str]`.
- The Set[str] pattern (e.g., `{"(on b1 b2)", "(clear b3)"}`) is used in AMLGym/online_model_learning for learning algorithms, but adds unnecessary conversion overhead for validation.
- UP's `state.get_value(expr)` evaluates any expression against the state — use this for precondition checking and diagnostic reporting.
- Boolean fluents: absent from state means false (closed-world assumption).
- Numeric fluents: default to 0 if not in initial state (PDDL convention).

## Grounding Plan Actions for Validation

To validate a plan action line against a domain:
1. Parse action name + parameter names from plan line
2. Look up action schema: `problem.action(name)` — handle hyphen normalization (see upf-gotchas.md)
3. Look up each parameter object: `problem.object(obj_name)` — report clear error if not found
4. Verify parameter count matches action schema parameter count
5. Verify each object's type is compatible with the corresponding parameter's type (including subtypes)
6. Create: `ActionInstance(action_schema, tuple(up_objects))`

Report specific errors:
- "Action 'xyz' not found in domain" (after normalization attempt)
- "Object 'abc' not declared in problem"
- "Parameter 2 of 'drive': expected type 'location', got 'truck' (object 'truck1')"
- "Action 'drive' expects 3 parameters, got 2"

## Precondition Decomposition for Diagnostics

When `is_applicable()` returns False, decompose preconditions for diagnostic reporting:
- **AND**: evaluate each conjunct separately against the state, report which specific ones fail
- **NOT**: evaluate inner expression, invert
- **Comparison** (`<=`, `>=`, `<`, `>`, `=`): evaluate both sides numerically, report current values and deficit (e.g., "fuel(truck1) = 3, need >= 10, deficit = 7")
- **Fluent expression**: evaluate against state, report current value
- **OR**: evaluate each disjunct, report that none were satisfied

## Goal Checking After Plan Execution

After executing all plan actions, evaluate goals against the final state:
- Goals are typically conjunctions — decompose and check each sub-goal independently
- For boolean goals: report whether predicate is true/false in final state
- For numeric goals: report current value vs. required threshold
- Report which goals are satisfied and which are not
- If goals are already satisfied in the initial state, an empty plan is valid
