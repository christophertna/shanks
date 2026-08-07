"""Small command-line helpers for inspecting Shanks configuration."""

from __future__ import annotations

import argparse
from typing import Sequence

from .mode import DEVELOPMENT_MODE, DRY_RUN_MODE, execution_mode


def main(argv: Sequence[str] | None = None) -> int:
    """Print the configured execution mode when requested."""

    parser = argparse.ArgumentParser(
        prog="shanks",
        description="Inspect Shanks local configuration.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("mode",),
        help="Show the current execution mode.",
    )
    parser.add_argument(
        "--mode",
        "-mode",
        action="store_true",
        help="Show the current execution mode.",
    )
    args = parser.parse_args(argv)

    if args.mode or args.command == "mode":
        mode = execution_mode()
        if mode == DRY_RUN_MODE:
            print(
                "Shanks mode: dry-run — delivery side effects will be previewed "
                "and skipped"
            )
        elif mode == DEVELOPMENT_MODE:
            print(
                "Shanks mode: development — guarded capabilities enabled; "
                "human approval still required"
            )
        else:
            print("Shanks mode: safe/normal (runtime) — human approval required")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
