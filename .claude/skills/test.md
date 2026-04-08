---
name: test
description: Run tests, analyze failures, and fix issues. Use after implementing or modifying code.
---

## Workflow

1. **Run the full suite**: `python3 -m pytest tests/ -v`
2. **On failure**: Read the traceback carefully. Check if it's a test bug or implementation bug.
3. **Fix the root cause** — Don't patch symptoms. If a UPF API call fails, check the API docs.
4. **Re-run** — Confirm the fix doesn't break other tests.

## Writing New Tests

- Use inline PDDL strings for test data (no external fixture files for simple cases).
- Test domains go in `tests/domains/` only when they're reused across multiple test files.
- Every validation phase needs positive (valid) and negative (invalid) test cases.
- Numeric tests must verify exact fluent values at each step, not just pass/fail.
- Name tests descriptively: `test_numeric_precondition_deficit_reported`, not `test_case_3`.

## Quick Commands

```bash
python3 -m pytest tests/ -v                    # Full suite
python3 -m pytest tests/ -v -k "numeric"       # Numeric tests only
python3 -m pytest tests/ -v -k "syntax"        # Syntax phase only
python3 -m pytest tests/ -v -x                 # Stop on first failure
python3 -m pytest tests/ -v --tb=long          # Verbose tracebacks
```
