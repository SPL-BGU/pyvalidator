---
name: validate-against-val
description: Cross-validate PyVAL output against compiled VAL on benchmark domains. Use for correctness verification.
---

## Purpose

Compare PyVAL's verdicts (VALID/INVALID) against the reference VAL binary on IPC benchmark domains to ensure correctness.

## Workflow

1. **Collect test cases** — Use domains from `tests/domains/` or IPC benchmark repositories.
2. **Run PyVAL** — `python3 -m pyval.cli domain.pddl problem.pddl plan.txt`
3. **Run VAL** (if available) — `Validate -v domain.pddl problem.pddl plan.txt`
4. **Compare verdicts** — Both must agree on VALID/INVALID. Diagnostic details may differ (PyVAL is richer).
5. **Document discrepancies** — If PyVAL disagrees with VAL, determine which is correct and file accordingly.

## What to Compare

- **Verdict agreement** — VALID/INVALID must match on all test cases.
- **Failure step** — If both say INVALID, they should identify the same failing step.
- **Precondition identification** — Both should flag the same unsatisfied precondition.
- **Numeric values** — Fluent values at failure point should agree (within float epsilon).

## Known VAL Limitations

- VAL has known bugs with some numeric domains (documented in VAL's issue tracker).
- VAL's error messages are less specific than PyVAL's — PyVAL may report more detail.
- VAL doesn't report numeric deficits or repair advice.
