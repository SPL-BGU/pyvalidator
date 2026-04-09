"""Output formatting: plain text, structured JSON, and trajectory table."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyval.models import ValidationResult


def format_plain_text(result: ValidationResult, verbose: bool = False) -> str:
    """Format validation result as human-readable plain text."""
    lines: list[str] = []

    # Phase 1: Syntax
    if "syntax" in result.phases:
        phase = result.phases["syntax"]
        if phase["errors"] or phase["warnings"] or verbose:
            lines.append("=== Syntax & Semantic Validation ===")
            for err in phase["errors"]:
                lines.append(f"[ERROR] {err}")
            for warn in phase["warnings"]:
                lines.append(f"[WARNING] {warn}")
            if not phase["errors"] and not phase["warnings"]:
                lines.append("All checks passed.")
            lines.append("")

    if result.status == "SYNTAX_ERROR":
        lines.append(f"Validation halted: {result.status}")
        return "\n".join(lines)

    # Phase 2: Structure
    if "structure" in result.phases:
        phase = result.phases["structure"]
        if phase["errors"] or phase["warnings"] or verbose:
            lines.append("=== Plan Structure Validation ===")
            for err in phase["errors"]:
                lines.append(f"[ERROR] {err}")
            for warn in phase["warnings"]:
                lines.append(f"[WARNING] {warn}")
            if not phase["errors"] and not phase["warnings"]:
                lines.append("All checks passed.")
            lines.append("")

    if result.status == "STRUCTURE_ERROR":
        lines.append(f"Validation halted: {result.status}")
        return "\n".join(lines)

    # Phase 3: Execution
    if result.steps:
        lines.append("=== Plan Execution ===")
        for step in result.steps:
            if step.status == "OK":
                lines.append(f"Step {step.index}: {step.action} \u2713")
                changes = _format_changes(step)
                if changes:
                    lines.append(f"  Changed: {changes}")
            else:
                lines.append(f"Step {step.index}: {step.action} \u2717 PRECONDITION FAILURE")
                for failure in step.unsatisfied:
                    lines.append(f"  Unsatisfied: {failure.expression}")
                    for k, v in failure.current_values.items():
                        lines.append(f"    Current value: {k} = {v}")
                    if failure.explanation:
                        lines.append(f"    {failure.explanation}")
                    if failure.deficit is not None and failure.deficit > 0:
                        lines.append(f"    Deficit: {failure.deficit} units")
        lines.append("")

    # Goal check
    lines.append("=== Goal Check ===")
    if result.is_valid:
        lines.append("All goals satisfied. Plan is VALID.")
    else:
        if result.failed_step is not None:
            total = result.phases.get("execution", {}).get("total_steps", "?")
            lines.append(
                f"Plan is INVALID. Failed at step {result.failed_step} of {total}."
            )
            remaining = int(total) - result.failed_step if isinstance(total, int) else "?"
            lines.append(f"Remaining actions not executed: {remaining}")
        elif result.unsatisfied_goals:
            lines.append("Plan executed but goals are NOT satisfied.")
            for goal in result.unsatisfied_goals:
                lines.append(f"  Unmet goal: {goal.expression}")
                for k, v in goal.current_values.items():
                    lines.append(f"    Current value: {v}")
        else:
            lines.append(f"Plan is {result.status}.")

    # Summary
    if result.steps:
        lines.append(f"Plan length: {len(result.steps)} actions")

    # Metric
    if result.metric:
        lines.append(
            f"Plan metric: {result.metric['type']} {result.metric['expression']} "
            f"= {result.metric['value']}"
        )

    # Numeric summary
    if result.numeric_trajectory:
        numeric_finals = {}
        for fluent, values in result.numeric_trajectory.items():
            if values:
                numeric_finals[fluent] = values[-1]
        if numeric_finals:
            parts = [f"{k} = {v}" for k, v in numeric_finals.items()]
            lines.append(f"Final state numeric values: {', '.join(parts)}")

    return "\n".join(lines)


def format_json(result: ValidationResult) -> dict:
    """Format validation result as structured JSON dict."""
    output: dict = {
        "status": result.status,
        "phases": {},
    }

    # Syntax phase
    if "syntax" in result.phases:
        output["phases"]["syntax"] = result.phases["syntax"]

    # Structure phase
    if "structure" in result.phases:
        output["phases"]["structure"] = result.phases["structure"]

    # Execution phase
    if "execution" in result.phases:
        exec_phase: dict = {
            "status": result.phases["execution"]["status"],
            "failed_step": result.failed_step,
            "total_steps": result.phases["execution"].get("total_steps"),
            "steps": [],
        }

        for step in result.steps:
            step_dict: dict = {
                "index": step.index,
                "action": step.action,
                "status": step.status,
            }

            if step.status == "OK":
                step_dict["changes"] = {
                    "boolean": step.boolean_changes,
                    "numeric": {
                        k: {"before": v.before, "after": v.after}
                        for k, v in step.numeric_changes.items()
                    },
                }
            else:
                step_dict["unsatisfied_preconditions"] = [
                    {
                        "expression": f.expression,
                        "type": f.type,
                        "current_values": f.current_values,
                        "explanation": f.explanation,
                        **({"deficit": f.deficit} if f.deficit is not None else {}),
                    }
                    for f in step.unsatisfied
                ]

            exec_phase["steps"].append(step_dict)
        output["phases"]["execution"] = exec_phase

    # Goals
    if result.unsatisfied_goals is not None:
        goals = [
            {
                "expression": g.expression,
                "satisfied": g.satisfied,
                "current_values": g.current_values,
            }
            for g in result.unsatisfied_goals
        ]
        output["phases"]["goals"] = goals if goals else None
    else:
        output["phases"]["goals"] = None

    # Metric
    if result.metric:
        output["metric"] = result.metric

    return output


def _format_changes(step) -> str:
    """Format boolean and numeric changes for a step as a compact string."""
    parts: list[str] = []
    for name, val in step.boolean_changes.items():
        parts.append(f"{name} = {str(val).lower()}")
    for name, change in step.numeric_changes.items():
        parts.append(f"{name} = {change.after} (was {change.before})")
    return ", ".join(parts)


def format_trajectory(
    result: ValidationResult, tracked: list[str] | None = None
) -> str:
    """Format numeric fluent trajectory as a table."""
    traj = result.numeric_trajectory
    if not traj:
        return "No numeric fluents to display."

    # Filter if specific fluents requested
    if tracked:
        tracked_set = set(tracked)
        traj = {k: v for k, v in traj.items() if k in tracked_set}
        if not traj:
            return "No matching numeric fluents found."

    fluent_names = list(traj.keys())
    num_steps = max(len(v) for v in traj.values()) if traj else 0

    # Build action labels from trajectory snapshots
    action_labels = []
    for snap in result.trajectory:
        action_labels.append(snap.action or "[initial state]")

    # Column widths
    step_width = max(4, len(str(num_steps)))
    action_width = max(6, max((len(a) for a in action_labels), default=6))
    col_widths = {
        name: max(len(name), max((len(str(v)) for v in vals), default=1))
        for name, vals in traj.items()
    }

    lines: list[str] = []
    lines.append("=== Numeric Fluent Trajectory ===")

    # Header
    header = (
        f"{'Step':>{step_width}} | {'Action':<{action_width}}"
    )
    for name in fluent_names:
        header += f" | {name:>{col_widths[name]}}"
    lines.append(header)

    # Separator
    sep = "-" * (step_width + 1) + "|" + "-" * (action_width + 2)
    for name in fluent_names:
        sep += "|" + "-" * (col_widths[name] + 1) + ":"
    lines.append(sep)

    # Data rows
    for i in range(num_steps):
        action = action_labels[i] if i < len(action_labels) else ""
        row = f"{i:>{step_width}} | {action:<{action_width}}"
        for name in fluent_names:
            vals = traj[name]
            val = vals[i] if i < len(vals) else ""
            val_str = str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
            row += f" | {val_str:>{col_widths[name]}}"
        lines.append(row)

    return "\n".join(lines)
