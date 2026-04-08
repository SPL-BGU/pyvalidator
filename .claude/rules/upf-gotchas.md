---
description: Critical unified-planning pitfalls from production usage in online_model_learning and AMLGym
paths:
  - "pyval/**/*.py"
  - "tests/**/*.py"
---

## Hyphen-to-Underscore Normalization

UP's PDDLReader silently converts hyphens in PDDL identifiers to underscores during parsing.
- PDDL `pick-up` becomes UP action name `pick_up`
- PDDL `(at-robot ?r ?l)` becomes UP fluent `at_robot`
- When matching plan actions to domain actions, normalize hyphens to underscores
- When displaying results back to the user, use the ORIGINAL PDDL names (with hyphens)
- Production workaround: AMLGym pre-normalizes domains with `re.sub(r'(?<=\w)-(?=\w)', '_', data)`. PyVAL should handle this at runtime instead.

## simulator.apply() May Return None

`SequentialSimulator.apply()` behavior varies by UP version:
- Some versions return `None` for inapplicable actions (no exception)
- Other versions raise `UPInvalidActionError`
- **Always call `is_applicable()` BEFORE `apply()`** — this is the safe pattern used in `online_model_learning/active_environment.py`
- If you must call `apply()` without pre-checking, wrap in try/except AND check for None:
  ```python
  try:
      next_state = simulator.apply(state, action)
  except UPInvalidActionError:
      next_state = None
  if next_state is None:
      # action was inapplicable
  ```

## FNode Expression Handling

FNode is the universal expression wrapper. Access patterns:
- **Numeric value**: `state.get_value(expr).constant_value()` → float/int
- **Boolean value**: `value_fnode.is_true()` / `value_fnode.is_false()`
- **Fluent name**: `fluent_expr.fluent().name` → str
- **Fluent arguments**: `fluent_expr.args` → tuple of FNode (use `str(arg)` for object name)
- **Expression type checks**: `.is_and()`, `.is_or()`, `.is_not()`, `.is_fluent_exp()`
- When iterating state values: `state._values.items()` gives `{fluent_expr: value_fnode}` (internal but used in production AMLGym code)

## PDDLReader Patterns

```python
reader = PDDLReader()
problem = reader.parse_problem(domain_path, problem_path)  # both files
plan = reader.parse_plan(problem, plan_path)                # IPC-format plan → SequentialPlan
```
- On malformed PDDL: raises `UPProblemDefinitionError` or `SyntaxError`
- `parse_plan` expects IPC format: one `(action param1 param2)` per line

## Object and Type Resolution

```python
action_schema = problem.action(name)      # raises if not found
obj = problem.object(name)                # raises if not found
fluent = problem.fluent(name)             # raises if not found
```
- `problem.all_objects` — includes objects from type declarations
- `problem.objects(type)` — objects of a specific type only
- Type compatibility: `obj.type.is_compatible(param.type)` for subtype checking
- Action parameters: `action.parameters` → list of `Parameter` with `.name` and `.type`

## Domain Name Mismatch

UP may append "-domain" to domain names during parsing. When comparing `problem.domain_name` against PDDL source, handle this suffix. Production code normalizes with:
```python
domain_str.replace(f"(domain {name}-domain)", f"(domain {name})")
```
