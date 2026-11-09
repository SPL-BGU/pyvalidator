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

        # Filter numeric fluents if tracking specific ones. A reference may be
        # the bare function name (`fuel`, every instance), or one instance in
        # either spelling (`fuel truck1`, `fuel(truck1)`).
        self.tracked_unknown: list[str] = []
        if tracked_fluents is not None:
            kept = [
                expr
                for expr in self._numeric_exprs
                if _matches_any(tracked_fluents, str(expr))
            ]
            self.tracked_unknown = [
                reference
                for reference in tracked_fluents
                if not _matches_any([reference], *(str(e) for e in self._numeric_exprs))
            ]
            self._numeric_exprs = kept

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


def available_numeric_fluents(problem: Problem) -> list[str]:
    """Names of the tracked-able numeric fluent instances, as `str(expr)`."""
    return [
        str(expr)
        for expr, value in problem.initial_values.items()
        if not value.is_bool_constant()
    ]


def fluent_reference_matches(reference: str, fluent_name: str) -> bool:
    """Whether a user-supplied --track reference selects `fluent_name`.

    Accepts the PDDL spelling, UPF's rendering and the bare function name:
    ``fuel`` (all instances of `fuel`), ``fuel truck1``, ``fuel(truck1)`` and
    ``fuel(truck1, ...)`` all select ``fuel(truck1)``. Before this, `--track`
    compared the display name (`fuel truck1`) with the snapshot key
    (`fuel(truck1)`), so no value ever matched and the table came back empty.
    """
    name, arguments = parse_fluent_reference(reference)
    fluent, fluent_arguments = parse_fluent_reference(fluent_name)
    if name != fluent:
        return False
    if arguments is None:
        return True
    return arguments == fluent_arguments


def parse_fluent_reference(reference: str) -> tuple[str, tuple[str, ...] | None]:
    """Split a fluent reference into (name, arguments or None).

    ``None`` for the arguments means "every instance of this function".
    """
    text = reference.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()

    head, separator, rest = text.partition("(")
    if separator and rest.endswith(")"):
        arguments = tuple(
            argument.strip() for argument in rest[:-1].split(",") if argument.strip()
        )
        return head.strip(), arguments

    parts = text.split()
    if not parts:
        return text, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], tuple(parts[1:])


def _matches_any(references, *fluent_names: str) -> bool:
    return any(
        fluent_reference_matches(reference, fluent_name)
        for reference in references
        for fluent_name in fluent_names
    )
