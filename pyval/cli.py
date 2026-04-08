"""CLI entry point — mirrors VAL's Validate interface."""

from __future__ import annotations

import argparse
import sys

from pyval.report_formatter import format_json, format_plain_text, format_trajectory
from pyval.validator import PDDLValidator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyval",
        description="PyVAL — Pure Python PDDL plan validator",
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="PDDL files: domain [problem [plan]]",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as structured JSON"
    )
    parser.add_argument(
        "--trajectory", action="store_true", help="Output numeric fluent trajectory"
    )
    parser.add_argument(
        "--track",
        action="append",
        metavar="FLUENT",
        help="Track specific numeric fluent (repeatable)",
    )
    parser.add_argument(
        "--version", action="version", version="pyval 0.1.0"
    )

    args = parser.parse_args()
    files = args.files

    if len(files) > 3:
        parser.error("Expected 1-3 files: domain [problem [plan]]")

    validator = PDDLValidator()

    if len(files) == 1:
        result = validator.validate_syntax(domain_path=files[0])
    elif len(files) == 2:
        result = validator.validate_syntax(
            domain_path=files[0], problem_path=files[1]
        )
    else:
        result = validator.validate(
            domain_path=files[0],
            problem_path=files[1],
            plan_path=files[2],
            tracked_fluents=args.track,
        )

    # Output
    import json

    if args.json:
        print(json.dumps(format_json(result), indent=2))
    elif args.trajectory:
        print(format_trajectory(result, tracked=args.track))
    else:
        print(format_plain_text(result, verbose=args.verbose))

    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
