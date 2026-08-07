#!/usr/bin/env python3
"""Run the repository's repeatable pre-commit and CI quality gates."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PATHS = ("graph.py", "serve_graph.py", "workflow", "tests", "scripts")
DEFAULT_MAX_FILES = 50
DEFAULT_MAX_LINES = 2000
IGNORED_DIFF_PREFIXES = ("graphify-out/",)
_SAFE_REF = re.compile(r"[A-Za-z0-9._/@:+-]+")
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class DiffStats:
    """The files and changed lines reported by ``git diff --numstat``."""

    files: int = 0
    lines: int = 0
    binary_files: int = 0


def quality_commands(
    python_executable: str | None = None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return the external commands used by every quality-gate invocation."""

    executable = python_executable or sys.executable
    paths = (*PYTHON_PATHS,)
    return (
        (
            "formatting",
            (executable, "-m", "black", "--check", *paths),
        ),
        (
            "linting",
            (executable, "-m", "ruff", "check", *paths),
        ),
        (
            "typing",
            (
                executable,
                "-m",
                "mypy",
                "scripts/quality_gates.py",
                "workflow/adapters.py",
                "workflow/contracts.py",
                "workflow/retries.py",
                "workflow/state.py",
            ),
        ),
        (
            "dependency/security audit",
            (
                executable,
                "-m",
                "pip_audit",
                "-r",
                "requirements.txt",
                "-r",
                "requirements-dev.txt",
                "--cache-dir",
                ".shanks/pip-audit",
                "--progress-spinner",
                "off",
            ),
        ),
    )


def validate_diff_base(value: str) -> str:
    """Validate a git ref before placing it in a subprocess argument list."""

    if (
        not value
        or value.startswith("-")
        or ".." in value
        or _SAFE_REF.fullmatch(value) is None
    ):
        raise ValueError(f"Unsupported diff base ref: {value!r}")
    return value


def diff_command(base: str, *, staged: bool = False) -> tuple[str, ...]:
    """Build the read-only git command used for the diff-size gate."""

    safe_base = validate_diff_base(base)
    if staged:
        return ("git", "diff", "--cached", "--numstat", safe_base)
    return ("git", "diff", "--numstat", f"{safe_base}...HEAD")


def parse_numstat(output: str) -> DiffStats:
    """Parse git's tab-separated numstat output, including binary files."""

    files = 0
    lines = 0
    binary_files = 0
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t", 2)
        if len(fields) != 3:
            raise ValueError(f"Malformed git numstat line: {raw_line!r}")
        added, deleted, path = fields
        if path.startswith(IGNORED_DIFF_PREFIXES):
            continue
        files += 1
        if added == "-" or deleted == "-":
            binary_files += 1
            continue
        try:
            lines += int(added) + int(deleted)
        except ValueError as error:
            raise ValueError(f"Malformed git numstat counts: {raw_line!r}") from error
    return DiffStats(files=files, lines=lines, binary_files=binary_files)


def diff_size_errors(
    stats: DiffStats,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_lines: int = DEFAULT_MAX_LINES,
) -> list[str]:
    """Return actionable failures for a changed-file or changed-line limit."""

    if max_files < 1 or max_lines < 1:
        raise ValueError("diff-size limits must be positive")
    errors = []
    if stats.files > max_files:
        errors.append(f"diff changes {stats.files} files; limit is {max_files} files")
    if stats.lines > max_lines:
        errors.append(f"diff changes {stats.lines} lines; limit is {max_lines} lines")
    return errors


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part.strip()
        for part in (result.stdout or "", result.stderr or "")
        if part and part.strip()
    )


def run_quality_gates(
    project_directory: Path = PROJECT_ROOT,
    *,
    diff_base: str | None = None,
    staged: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    max_lines: int = DEFAULT_MAX_LINES,
    runner: Runner = subprocess.run,
) -> list[str]:
    """Run all configured gates and return human-readable failures."""

    failures: list[str] = []
    for label, command in quality_commands():
        result = runner(
            command,
            cwd=project_directory,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            output = _command_output(result) or "no output"
            failures.append(f"{label} gate failed:\n{output}")

    if diff_base is not None:
        command = diff_command(diff_base, staged=staged)
        result = runner(
            command,
            cwd=project_directory,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            output = _command_output(result) or "no output"
            failures.append(f"diff-size gate could not inspect the diff:\n{output}")
        else:
            try:
                stats = parse_numstat(result.stdout or "")
                failures.extend(
                    diff_size_errors(
                        stats,
                        max_files=max_files,
                        max_lines=max_lines,
                    )
                )
            except ValueError as error:
                failures.append(f"diff-size gate returned invalid output: {error}")

    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff-base",
        help="git ref to compare for the diff-size gate, e.g. origin/main",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="measure the staged diff against --diff-base",
    )
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.staged and args.diff_base is None:
        print("--staged requires --diff-base", file=sys.stderr)
        return 2
    try:
        failures = run_quality_gates(
            diff_base=args.diff_base,
            staged=args.staged,
            max_files=args.max_files,
            max_lines=args.max_lines,
        )
    except (OSError, ValueError) as error:
        print(f"Quality gates could not run: {error}", file=sys.stderr)
        return 2
    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1
    print("Quality gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
