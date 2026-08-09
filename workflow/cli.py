"""Small command-line helpers for inspecting Shanks configuration."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .mode import DEVELOPMENT_MODE, DRY_RUN_MODE, execution_mode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_REQUIREMENT_FILES = ("requirements.txt", "requirements-dev.txt")
_REQUIRED_TOOLS = ("git", "gh", "bash")
_AGENT_TOOLS = ("codex", "claude")
_VALID_MODES = {"runtime", DEVELOPMENT_MODE, DRY_RUN_MODE, "dry_run"}
_ENVIRONMENT_KEYS = (
    "SHANKS_MODE",
    "SHANKS_CHECKPOINT_DB",
    "SHANKS_RUN_LEASE_SECONDS",
    "SHANKS_CHECKPOINT_RETENTION",
)
_REQUIREMENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    """One human-readable configuration diagnostic."""

    name: str
    passed: bool
    detail: str


def doctor_checks(
    project_directory: Path | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    python_executable: str | None = None,
) -> list[DoctorCheck]:
    """Collect diagnostics without changing project or checkpoint state."""

    project = (project_directory or PROJECT_ROOT).expanduser().resolve()
    environment = dict(os.environ if environment is None else environment)
    runner = subprocess.run if runner is None else runner
    return [
        _check_mode(environment),
        _check_tools(python_executable or sys.executable),
        _check_dependencies(project),
        _check_authentication(project, environment, runner),
        _check_environment(environment),
        _check_checkpoint(project, environment),
    ]


def run_doctor(
    project_directory: Path | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    python_executable: str | None = None,
) -> int:
    """Print diagnostics and return a failing status when any check fails."""

    checks = doctor_checks(
        project_directory,
        environment=environment,
        runner=runner,
        python_executable=python_executable,
    )
    print("Shanks doctor")
    for check in checks:
        status = "OK" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
    passed = sum(check.passed for check in checks)
    result = "PASS" if passed == len(checks) else "FAIL"
    print(f"Doctor: {result} ({passed}/{len(checks)} checks passed)")
    return 0 if result == "PASS" else 1


def _check_mode(environment: Mapping[str, str]) -> DoctorCheck:
    raw = environment.get("SHANKS_MODE")
    if raw is None:
        return DoctorCheck("mode", True, "runtime (default; SHANKS_MODE is unset)")
    value = raw.strip().lower()
    if value not in _VALID_MODES:
        return DoctorCheck(
            "mode",
            False,
            f"invalid SHANKS_MODE={raw!r}; use runtime, development, or dry-run",
        )
    effective = DRY_RUN_MODE if value == "dry_run" else value
    return DoctorCheck("mode", True, f"{effective} (SHANKS_MODE={raw})")


def _check_tools(python_executable: str) -> DoctorCheck:
    missing = [tool for tool in _REQUIRED_TOOLS if shutil.which(tool) is None]
    available_agents = [tool for tool in _AGENT_TOOLS if shutil.which(tool)]
    if not available_agents:
        missing.append("codex or claude")
    interpreter = Path(python_executable)
    if not interpreter.exists():
        missing.append(f"Python interpreter ({python_executable})")
    version = sys.version_info
    if (version.major, version.minor) < (3, 11):
        missing.append("Python 3.11 or newer")
    if missing:
        return DoctorCheck("tools", False, "missing: " + ", ".join(missing))
    tools = ", ".join((*_REQUIRED_TOOLS, f"agent={available_agents[0]}"))
    return DoctorCheck(
        "tools", True, f"{tools}; Python {version.major}.{version.minor}"
    )


def _check_dependencies(project: Path) -> DoctorCheck:
    requirements: list[tuple[str, str]] = []
    missing_files: list[str] = []
    for filename in _REQUIREMENT_FILES:
        path = project / filename
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            missing_files.append(filename)
            continue
        for raw_line in lines:
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            match = _REQUIREMENT_NAME.match(line)
            if match:
                expected = ""
                if "==" in line:
                    expected = line.split("==", 1)[1].split(";", 1)[0].strip()
                requirements.append((match.group(0), expected))

    errors = [f"missing requirement file: {filename}" for filename in missing_files]
    for name, expected in requirements:
        try:
            installed = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            errors.append(f"{name} is not installed")
            continue
        if expected and installed != expected:
            errors.append(f"{name} is {installed}; expected {expected}")
    if errors:
        return DoctorCheck("dependencies", False, "; ".join(errors))
    return DoctorCheck(
        "dependencies",
        True,
        f"{len(requirements)} pinned dependencies are installed",
    )


def _check_authentication(
    project: Path,
    environment: Mapping[str, str],
    runner: Runner,
) -> DoctorCheck:
    if shutil.which("gh") is None:
        return DoctorCheck(
            "authentication", False, "gh is unavailable; cannot check login"
        )
    try:
        result = runner(
            ("gh", "auth", "status"),
            cwd=project,
            env=_github_environment(environment),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return DoctorCheck("authentication", False, f"gh auth status failed: {error}")
    if result.returncode:
        return DoctorCheck(
            "authentication",
            False,
            f"GitHub CLI is not authenticated (exit {result.returncode}); run gh auth login",
        )
    return DoctorCheck("authentication", True, "GitHub CLI authentication is available")


def _check_environment(environment: Mapping[str, str]) -> DoctorCheck:
    errors: list[str] = []
    mode = environment.get("SHANKS_MODE")
    if mode is not None and mode.strip().lower() not in _VALID_MODES:
        errors.append("SHANKS_MODE is invalid")

    lease = environment.get("SHANKS_RUN_LEASE_SECONDS")
    if lease is not None:
        try:
            parsed_lease = float(lease)
        except ValueError:
            parsed_lease = 0.0
        if not math.isfinite(parsed_lease) or parsed_lease <= 0:
            errors.append("SHANKS_RUN_LEASE_SECONDS must be a positive number")

    retention = environment.get("SHANKS_CHECKPOINT_RETENTION")
    if retention is not None:
        try:
            parsed_retention = int(retention)
        except ValueError:
            parsed_retention = 0
        if parsed_retention < 1:
            errors.append("SHANKS_CHECKPOINT_RETENTION must be a positive integer")

    checkpoint_db = environment.get("SHANKS_CHECKPOINT_DB")
    if checkpoint_db is not None and not checkpoint_db.strip():
        errors.append("SHANKS_CHECKPOINT_DB must not be empty")

    if errors:
        return DoctorCheck("environment", False, "; ".join(errors))
    configured = [key for key in _ENVIRONMENT_KEYS if key in environment]
    detail = ", ".join(configured) if configured else "no overrides; defaults are valid"
    return DoctorCheck("environment", True, detail)


def _check_checkpoint(
    project: Path,
    environment: Mapping[str, str],
) -> DoctorCheck:
    raw_path = environment.get("SHANKS_CHECKPOINT_DB")
    if raw_path is not None and not raw_path.strip():
        return DoctorCheck("checkpoint", False, "SHANKS_CHECKPOINT_DB is empty")
    path = (
        Path(raw_path).expanduser()
        if raw_path
        else project / ".shanks" / "checkpoints.sqlite"
    )
    if not path.is_absolute():
        path = project / path
    path = path.resolve(strict=False)
    if path.exists() and not path.is_file():
        return DoctorCheck(
            "checkpoint", False, f"checkpoint path is not a file: {path}"
        )

    parent = path.parent
    writable_parent = parent
    while not writable_parent.exists() and writable_parent != writable_parent.parent:
        writable_parent = writable_parent.parent
    if not writable_parent.is_dir() or not os.access(writable_parent, os.W_OK):
        return DoctorCheck(
            "checkpoint",
            False,
            f"checkpoint directory is not writable: {parent}",
        )

    if not path.exists():
        return DoctorCheck(
            "checkpoint",
            True,
            f"{path} is ready to be created",
        )
    try:
        connection = sqlite3.connect(str(path), timeout=1)
        connection.execute("PRAGMA schema_version").fetchone()
        connection.close()
    except (OSError, sqlite3.Error) as error:
        return DoctorCheck(
            "checkpoint", False, f"SQLite database is not usable: {error}"
        )
    return DoctorCheck("checkpoint", True, f"SQLite database is ready: {path}")


def _github_environment(environment: Mapping[str, str]) -> dict[str, str]:
    keys = {
        "GH_HOST",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
    }
    result = {key: environment[key] for key in keys if key in environment}
    result["GIT_TERMINAL_PROMPT"] = "0"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Print the configured execution mode when requested."""

    parser = argparse.ArgumentParser(
        prog="shanks",
        description="Inspect Shanks local configuration.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("mode", "doctor"),
        help="Show the current execution mode or diagnose the environment.",
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

    if args.command == "doctor":
        return run_doctor()

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
