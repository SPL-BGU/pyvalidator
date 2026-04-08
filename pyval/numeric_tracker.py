"""Numeric fluent value tracking across plan steps."""

from __future__ import annotations

from unified_planning.model import Problem

from pyval.models import StateSnapshot


class NumericTracker:
    """Tracks numeric (and boolean) fluent values across plan execution steps."""

    def __init__(
        self, problem: Problem, tracked_fluents: list[str] | None = None
    ):
        self._problem = problem
        self._snapshots: list[StateSnapshot] = []

        # Identify all fluent expressions from initial values
        self._boolean_exprs = []
        self._numeric_exprs = []
        for fluent_expr, val in problem.initial_values.items():
            if val.is_bool_constant():
                self._boolean_exprs.append(fluent_expr)
            else:
                self._numeric_exprs.append(fluent_expr)

        # Filter numeric fluents if tracking specific ones
        if tracked_fluents is not None:
            tracked_set = set(tracked_fluents)
            self._numeric_exprs = [
                e for e in self._numeric_exprs
                if _fluent_display_name(e) in tracked_set
            ]

    def record(self, step: int, action: str | None, state) -> StateSnapshot:
        """Record a state snapshot at a given step."""
        boolean_fluents = {}
        for expr in self._boolean_exprs:
            val = state.get_value(expr)
            boolean_fluents[str(expr)] = val.is_true()

        numeric_fluents = {}
        for expr in self._numeric_exprs:
            val = state.get_value(expr)
            numeric_fluents[str(expr)] = float(val.constant_value())

        snapshot = StateSnapshot(
            step=step,
            action=action,
            boolean_fluents=boolean_fluents,
            numeric_fluents=numeric_fluents,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_numeric_trajectory(self) -> dict[str, list[float]]:
        """Return {fluent_name: [val_step0, val_step1, ...]}."""
        if not self._snapshots:
            return {}

        # Use the first snapshot's numeric keys as the canonical set
        keys = list(self._snapshots[0].numeric_fluents.keys())
        trajectory: dict[str, list[float]] = {k: [] for k in keys}
        for snap in self._snapshots:
            for k in keys:
                trajectory[k].append(snap.numeric_fluents.get(k, 0.0))
        return trajectory


def _fluent_display_name(expr) -> str:
    """Extract a display name like 'fuel truck1' from a fluent expression."""
    if expr.is_fluent_exp():
        name = expr.fluent().name
        args = " ".join(str(a) for a in expr.args)
        return f"{name} {args}".strip() if args else name
    return str(expr)
