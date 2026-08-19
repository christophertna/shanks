"""Recompute `tests/tests.md`'s counts from the suites they describe.

The same numbers live in two places - a per-file row and the headline total -
and hand-editing both is what left `main` red for twenty minutes (#91) and
produced the only merge conflict between two parallel branches (#92/#93).
`--fix` rewrites every documented count from the real suite, so no one has to
type one again; the default check mode is what `tests/test_cli.py`'s guards
call, so the checker and the fixer can never disagree about a number.

Rows are only ever rewritten, never added: a new test module still needs a
human-written "Main areas" description, and the headline is the sum of the
documented rows (not of every file on disk) so it keeps agreeing with the
table it summarizes.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

# Shared with `tests/test_cli.py`, so "documented" means the same thing to the
# guards, to the harness runner, and to the fixer below.
PYTHON_ROW = re.compile(
    r"\[`(?P<path>test_\w+\.py)`\]\((?P=path)\) \| (?P<count>\d+) \|"
)
HARNESS_ROW = re.compile(
    r"\[`(?P<path>\.\./hooks/test\.hooks/[\w.-]+\.sh)`\]\((?P=path)\) \| "
    r"(?P<count>\d+) shell checks \|"
)
HEADLINE = re.compile(r"\*\*(?P<count>\d+) unittest methods\*\*")
TEST_METHOD = re.compile(r"^\s*def test_", re.MULTILINE)
HARNESS_RESULT = re.compile(r"passed: (\d+), failed: 0")


class HarnessError(RuntimeError):
    """A harness failed, so its check count cannot be trusted or written."""


def python_counts(text: str, repo: Path) -> dict[str, int]:
    """Count the test methods in every Python module `text` documents."""

    counts = {}
    for name, _ in PYTHON_ROW.findall(text):
        source = (repo / "tests" / name).read_text(encoding="utf-8")
        counts[name] = len(TEST_METHOD.findall(source))
    return counts


def harness_counts(text: str, repo: Path) -> dict[str, int]:
    """Run every shell harness `text` documents and report its check count.

    Raises rather than returning a number for a harness that did not pass -
    a failing harness reports whatever it reached, which is not the count.
    """

    counts = {}
    for relative, _ in HARNESS_ROW.findall(text):
        harness = (repo / "tests" / relative).resolve()
        result = subprocess.run(
            ["bash", str(harness)],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        summary = result.stdout.strip().splitlines()[-1:] or [""]
        matched = HARNESS_RESULT.fullmatch(summary[0])
        if result.returncode != 0 or matched is None:
            raise HarnessError(
                f"{harness.name} failed:\n{result.stdout}{result.stderr}"
            )
        counts[relative] = int(matched.group(1))
    return counts


def apply_python_counts(text: str, repo: Path) -> str:
    """Return `text` with its Python rows and headline total recomputed."""

    counts = python_counts(text, repo)
    updated = PYTHON_ROW.sub(
        lambda row: f"[`{row['path']}`]({row['path']}) | {counts[row['path']]} |",
        text,
    )
    return HEADLINE.sub(f"**{sum(counts.values())} unittest methods**", updated)


def apply_harness_counts(text: str, repo: Path) -> str:
    """Return `text` with its shell-harness check counts recomputed."""

    counts = harness_counts(text, repo)
    return HARNESS_ROW.sub(
        lambda row: (
            f"[`{row['path']}`]({row['path']}) | "
            f"{counts[row['path']]} shell checks |"
        ),
        text,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite tests/tests.md in place instead of reporting the drift",
    )
    arguments = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    document = repo / "tests" / "tests.md"
    current = document.read_text(encoding="utf-8")
    updated = apply_harness_counts(apply_python_counts(current, repo), repo)

    if current == updated:
        print("tests/tests.md counts match the suites.")
        return 0
    if arguments.fix:
        document.write_text(updated, encoding="utf-8")
        print("tests/tests.md counts updated.")
        return 0

    print(
        "".join(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile="tests/tests.md",
                tofile="tests/tests.md (derived)",
                n=0,
            )
        ),
        end="",
    )
    print("Run `.venv/bin/python scripts/sync_tests_md.py --fix` to update them.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
