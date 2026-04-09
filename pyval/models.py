"""Data models for PyVAL validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class NumericChange:
    before: float
    after: float


@dataclass
class PreconditionFailure:
    expression: str
    type: Literal["boolean", "numeric"]
    current_values: dict[str, Any]
    explanation: str
    deficit: float | None = None


@dataclass
class GoalResult:
    expression: str
    satisfied: bool
    current_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    step: int
    action: str | None
    boolean_fluents: dict[str, bool] = field(default_factory=dict)
    numeric_fluents: dict[str, float] = field(default_factory=dict)


@dataclass
class StepResult:
    index: int
    action: str
    status: Literal["OK", "FAILED"]
    boolean_changes: dict[str, bool] = field(default_factory=dict)
    numeric_changes: dict[str, NumericChange] = field(default_factory=dict)
    unsatisfied: list[PreconditionFailure] = field(default_factory=list)


@dataclass
class ValidationResult:
    status: Literal["VALID", "INVALID", "SYNTAX_ERROR", "STRUCTURE_ERROR"]
    is_valid: bool
    phases: dict = field(default_factory=dict)
    steps: list[StepResult] = field(default_factory=list)
    trajectory: list[StateSnapshot] = field(default_factory=list)
    numeric_trajectory: dict[str, list] = field(default_factory=dict)
    failed_step: int | None = None
    unsatisfied_goals: list[GoalResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metric: dict | None = None  # {"type": "minimize"/"maximize", "expression": str, "value": float}

    def report(self, verbose: bool = False) -> str:
        from pyval.report_formatter import format_plain_text
        return format_plain_text(self, verbose=verbose)

    def to_json(self) -> dict:
        from pyval.report_formatter import format_json
        return format_json(self)
