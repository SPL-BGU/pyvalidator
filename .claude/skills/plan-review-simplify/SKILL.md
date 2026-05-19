---
name: plan-review-simplify
description: Create an execution plan with built-in review for correctness and simplification. Use for multi-file changes, new pipeline modules, refactoring, or any change spanning multiple files.
disable-model-invocation: true
argument-hint: [task description]
---

## Planning Workflow with Review and Simplification

For the task described in $ARGUMENTS:

### Phase 1: Explore
1. Read all relevant existing code using Grep and Glob
2. Identify existing patterns that can be reused — especially:
   - `pyval/models.py` for data model contracts (and `to_json()` for the JSON output schema)
   - `pyval/validator.py` for pipeline orchestration patterns
   - `pyval/report_formatter.py` and `pyval/diagnostics.py` for output format and diagnostic templates
   - `CLAUDE.md` for the architectural overview and conventions
3. Check all modules under `pyval/` to understand cross-module impact
4. Review `.claude/rules/` for validation semantics and UPF gotchas
5. **Run `python3 -m pytest tests/ -v`** to verify baseline test state before planning changes

### Phase 2: Plan
Design the implementation approach covering:
- **Objective**: One sentence describing the goal
- **Analysis**: Current state, what needs to change, existing code to reuse
- **Reference alignment**: Which sections of `CLAUDE.md` (or which `pyval/` modules) are affected? Do output formats or diagnostic templates need updates in `report_formatter.py` / `diagnostics.py`?
- **Pipeline phase**: Which phase does this change belong to? (Phase 1: syntax_checker, Phase 2: validator, Phase 3: plan_simulator, or cross-cutting: models/diagnostics/report_formatter)
- **Models impact**: Does this change the models.py dataclass shapes? If so, which downstream modules break?
- **Files to modify**: Table of file | action (create/modify/delete) | description
- **Execution steps**: Numbered checklist
- **Validation strategy**: `python3 -m pytest tests/ -v` at minimum. Numeric changes also need `-k "numeric"`.

### Phase 3: Review
Before presenting the plan, review it for simplification and correctness:

**Simplification:**
- Can any proposed new file be merged into an existing module?
- Can any proposed new class be a method on an existing class?
- Are there existing utilities in `pyval/` that eliminate proposed helpers?
- Would a senior engineer say "this is more code than necessary"?

**Pipeline integrity:**
- Does each module stay within its pipeline phase responsibility?
- Does the change keep the halt-on-FATAL phase sequencing intact?
- Does `models.py` remain the single source of truth for data shapes?
- Does the change avoid duplicating logic across pipeline phases?

**Reference conformance:**
- Do output formats match the existing templates in `pyval/report_formatter.py`?
- Do diagnostic messages follow the existing patterns in `pyval/diagnostics.py` (precondition deficits, repair advice, no leaking "Plan is VALID" when no plan was executed)?
- Do data models match the dataclass definitions in `pyval/models.py`?
- Does the CLI interface stay compatible with VAL's `Validate` command?

**UPF correctness:**
- Is all PDDL parsing delegated to `PDDLReader`? (No regex-based PDDL parsers)
- Does the change handle UPF's hyphen-to-underscore normalization?
- Does the change call `is_applicable()` before `apply()`?
- Does the change handle `FNode` expressions correctly? (see `.claude/rules/upf-gotchas.md`)

If concerns found: revise the plan. Note what changed and why.

### Phase 4: Present for Approval
Present plan to user, noting:
- Open decisions requiring user input
- Any models.py contract changes and their downstream impact
- Spec sections that may need updating alongside the code change

Do NOT proceed until approved.

### Phase 5: Execute
Execute steps in order. After completion:
1. Run `python3 -m pytest tests/ -v`
2. If numeric changes: also run `python3 -m pytest tests/ -v -k "numeric"`
3. Verify `python3 -c "import pyval"` succeeds
4. Update `CHANGELOG.md` under `[Unreleased]`
5. Summarize changes, key decisions, validation results

## Fast Mode
If user says "fast mode", "just do it", or "skip planning" — execute immediately without the planning workflow.

## Simple Tasks (No Planning Required)
Skip planning for:
- Single-file edits under 50 lines
- Answering questions or explaining code
- Running tests without modification
- Git operations
- Documentation-only changes to a single file
- Adding a single test case
