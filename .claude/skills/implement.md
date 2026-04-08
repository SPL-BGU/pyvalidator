---
name: implement
description: Implement a module or feature from the spec. Reads VALIDATOR_SPEC.md, checks existing code, writes implementation with tests.
---

## Workflow

1. **Read the spec** — `VALIDATOR_SPEC.md` is the source of truth. Find the section relevant to the module/feature.
2. **Check existing code** — Search `pyval/` for related implementations. Don't duplicate.
3. **Check UPF API** — If the feature involves parsing, simulation, or state operations, verify the unified-planning API by reading its source or docs. Don't guess method signatures.
4. **Implement** — Follow the module structure from the spec. Use the data models from `models.py`.
5. **Write tests** — Every public function gets at least one classical and one numeric test case. Use inline PDDL strings, not fixture files.
6. **Run tests** — `python3 -m pytest tests/ -v`

## Rules

- The spec's data models (`ValidationResult`, `StepResult`, etc.) are the contract. Don't change their shape without updating the spec.
- All PDDL parsing goes through `unified-planning`'s `PDDLReader`. Do not write regex-based PDDL parsers.
- Diagnostic messages must follow the templates in the spec's "Diagnostic Message Guidelines" section.
- Handle both file paths and inline PDDL strings as input.
- Numeric validation must track fluent values with float precision and report deficits.
- Phase execution halts on first FATAL error — don't continue to Phase 3 if Phase 1 has FATAL errors.
