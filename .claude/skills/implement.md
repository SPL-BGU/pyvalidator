---
name: implement
description: Implement a module or feature from the architecture reference. Reads CLAUDE.md and the existing pyval/ modules, then writes implementation with tests.
---

## Workflow

1. **Read the architecture reference** — `CLAUDE.md` (top-level) is the source of truth for pipeline phases, output modes, and conventions. Data-model shapes live in `pyval/models.py`; diagnostic templates live in `pyval/diagnostics.py` and `pyval/report_formatter.py`.
2. **Check existing code** — Search `pyval/` for related implementations. Don't duplicate.
3. **Check UPF API** — If the feature involves parsing, simulation, or state operations, verify the unified-planning API by reading its source or docs. Don't guess method signatures.
4. **Implement** — Follow the module structure described in `CLAUDE.md`'s "Project Structure" section. Use the data models from `pyval/models.py`.
5. **Write tests** — Every public function gets at least one classical and one numeric test case. Use inline PDDL strings, not fixture files.
6. **Run tests** — `python3 -m pytest tests/ -v`

## Rules

- The data models in `pyval/models.py` (`ValidationResult`, `StepResult`, etc.) are the contract. Don't change their shape without updating every consumer and noting it in `CHANGELOG.md`.
- All PDDL parsing goes through `unified-planning`'s `PDDLReader`. Do not write regex-based PDDL parsers.
- Diagnostic messages must follow the existing templates in `pyval/diagnostics.py` and `pyval/report_formatter.py` (precondition deficit reporting, repair-oriented messages, no leaking "Plan is VALID" when no plan was executed).
- Handle both file paths and inline PDDL strings as input.
- Numeric validation must track fluent values with float precision and report deficits.
- Phase execution halts on first FATAL error — don't continue to Phase 3 if Phase 1 has FATAL errors.
