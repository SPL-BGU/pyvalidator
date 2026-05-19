---
name: simplify
description: Review current plan or code changes for unnecessary complexity, pipeline violations, and spec deviations. Flags over-engineering, UPF misuse, models contract breaks, and diagnostic quality issues.
context: fork
agent: simplifier
argument-hint: [description of what to review]
---

Review the current work for unnecessary complexity and correctness.

$ARGUMENTS

If no specific target is given, review the most recent changes (check git diff or the current plan).

Key reference files for correctness and convention review:
- CLAUDE.md — Authoritative architecture reference (pipeline phases, output modes, conventions)
- pyval/models.py — Data model contract (ValidationResult, StepResult, etc.) and JSON schema via `to_json()`
- pyval/diagnostics.py, pyval/report_formatter.py — Diagnostic message templates and output formats
- .claude/rules/pddl-validation-semantics.md — Validation correctness rules
- .claude/rules/upf-gotchas.md — UPF API pitfalls
