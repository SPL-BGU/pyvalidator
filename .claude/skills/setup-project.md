---
name: setup-project
description: Bootstrap the pyvalidator project structure. Creates pyproject.toml, package directories, and test infrastructure.
---

## Workflow

1. **Create `pyproject.toml`**:
   - Build backend: `hatchling` or `setuptools`
   - Name: `pyval`
   - Python: `>= 3.10`
   - Dependencies: `unified-planning`
   - Optional deps `[dev]`: `pytest`
   - Optional deps `[copilot]`: `pddl-plus-parser` (trajectory compatibility)
   - Entry point: `[project.scripts] pyval = "pyval.cli:main"`
   - Include license, description, author metadata

2. **Create `pyval/` package** (all modules from VALIDATOR_SPEC.md):
   ```
   pyval/__init__.py          # Public API: PDDLValidator, ValidationResult
   pyval/cli.py               # CLI entry point
   pyval/validator.py          # Main orchestrator (3-phase pipeline)
   pyval/syntax_checker.py     # Phase 1: domain/problem syntax validation
   pyval/plan_simulator.py     # Phase 3: step-by-step plan execution
   pyval/diagnostics.py        # Diagnostic message generation
   pyval/numeric_tracker.py    # Numeric fluent tracking
   pyval/report_formatter.py   # Output formatting (text, JSON, trajectory)
   pyval/models.py             # Dataclasses: ValidationResult, StepResult, etc.
   ```
   Start each module with a docstring describing its role, then stub the public API.

3. **Create `tests/` structure**:
   ```
   tests/__init__.py
   tests/conftest.py           # Shared fixtures (inline PDDL strings for classical + numeric domains)
   tests/domains/              # Reusable test PDDL files (only for complex multi-file test cases)
   ```

4. **Create `.gitignore`** additions (if not present):
   ```
   __pycache__/
   *.egg-info/
   dist/
   build/
   .venv/
   .pytest_cache/
   ```

5. **Install and verify**:
   ```bash
   pip install -e ".[dev]"
   python3 -c "import pyval"
   python3 -m pytest --collect-only
   ```

## Rules

- Follow VALIDATOR_SPEC.md for all module names and data model shapes
- Python >= 3.10 (for `match` statements and `X | Y` type union syntax)
- `models.py` should be implemented first — other modules depend on its dataclasses
- All `__init__.py` files should export public API names
- Do NOT install pddl-plus-parser by default — it's optional
