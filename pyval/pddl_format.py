"""Small formatting helpers shared by the diagnostics paths.

UPF renders fluent instances the way the API spells them — ``fuel(t2)``,
``distance(l1, l2)`` — while the messages we emit are read by people editing
PDDL source files, where the same term is ``(fuel t2)``. Converting once here
keeps every repair hint valid PDDL.
"""

from __future__ import annotations


def as_pddl_call(rendered: str) -> str:
    """Turn a UPF name rendering into the PDDL source spelling.

    ``fuel(t2)`` -> ``(fuel t2)``; ``total-cost`` -> ``(total-cost)``.
    """
    head, separator, rest = rendered.partition("(")
    if not separator or not rest.endswith(")"):
        return f"({rendered.strip()})"
    arguments = " ".join(
        argument.strip() for argument in rest[:-1].split(",") if argument.strip()
    )
    name = head.strip()
    return f"({name} {arguments})" if arguments else f"({name})"
