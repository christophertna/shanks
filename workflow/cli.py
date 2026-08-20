"""Command-line helpers for inspecting and managing Shanks runs."""

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
import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, Sequence

from .lifecycle import (
    RunBusyError,
    TERMINAL_LIFECYCLE_STATUSES,
)
from .mode import DEVELOPMENT_MODE, DRY_RUN_MODE, execution_mode, is_development_mode
from .state import cancel_run
from .workspaces import RunWorkspaceManager, WorkspaceError, sync_local_guardrails


class CliError(RuntimeError):
    """Raised for an operator-correctable run-management error."""


# Mirrors ``graph.build_graph``'s ``tool`` parameter; mypy flags the call sites
# if the two ever drift.
ToolName = Literal["claude", "codex"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_REQUIREMENT_FILES = ("requirements.txt", "requirements-dev.txt")
_REQUIRED_TOOLS = ("git", "gh", "bash", "jq", "gitleaks")
_AGENT_TOOLS = ("codex", "claude")
# The gitleaks floor tracks `GITLEAKS_VERSION` in .github/workflows/tests.yml:
# an older local gitleaks can miss a secret CI would catch, so the two must not
# drift apart. `test_doctor_gitleaks_floor_matches_the_ci_pin` enforces it.
_MIN_TOOL_VERSIONS = {"git": (2, 30), "gh": (2, 40), "gitleaks": (8, 18)}
RECENT_EVENT_LIMIT = 5
_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)")
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
        _check_tools(python_executable or sys.executable, runner),
        _check_dependencies(project),
        _check_authentication(project, environment, runner),
        _check_environment(environment),
        _check_checkpoint(project, environment),
        _check_hooks_path(project, runner),
        _check_claude_hooks(project, runner),
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


def _tool_version(tool: str, runner: Runner) -> tuple[int, int] | None:
    """Best-effort `<tool> --version` parse; None if unavailable or unparsable."""

    try:
        result = runner(
            (tool, "--version"), capture_output=True, text=True, check=False, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = _VERSION_PATTERN.search(result.stdout)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _check_tools(python_executable: str, runner: Runner) -> DoctorCheck:
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
    for tool, minimum in _MIN_TOOL_VERSIONS.items():
        if tool in missing:
            continue
        found = _tool_version(tool, runner)
        if found is not None and found < minimum:
            missing.append(
                f"{tool} {minimum[0]}.{minimum[1]}+ (found {found[0]}.{found[1]})"
            )
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


def _check_hooks_path(project: Path, runner: Runner) -> DoctorCheck:
    try:
        result = runner(
            ("git", "config", "--get", "core.hooksPath"),
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return DoctorCheck("hooks", False, f"git config check failed: {error}")
    configured = result.stdout.strip()
    if configured != "hooks":
        return DoctorCheck(
            "hooks",
            False,
            "core.hooksPath is not 'hooks'; run: git config core.hooksPath hooks"
            + (f" (currently {configured!r})" if configured else ""),
        )
    return DoctorCheck("hooks", True, "core.hooksPath=hooks")


def _main_checkout(project: Path, runner: Runner) -> Path | None:
    """Return the main working tree for `project`, or None if undeterminable.

    `git rev-parse --git-common-dir` resolves to `<main checkout>/.git` from
    any linked worktree (and from the main checkout itself), without needing
    `--path-format` (Git 2.31+, newer than this repo's 2.30 floor).
    """

    try:
        result = runner(
            ("git", "rev-parse", "--git-common-dir"),
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    common_dir = (project / result.stdout.strip()).resolve()
    if common_dir.name != ".git":
        return None
    return common_dir.parent


def _stale_worktree_detail(project: Path, settings: Path, runner: Runner) -> str | None:
    """Return a failure detail when `settings` lags the main checkout's copy."""

    main = _main_checkout(project, runner)
    if main is None or main == project.resolve():
        return None
    canonical = main / ".claude" / "settings.json"
    if not canonical.is_file() or canonical.read_bytes() == settings.read_bytes():
        return None
    return f"stale relative to {main}; run: ./shanks dev sync {project}"


def _check_claude_hooks(project: Path, runner: Runner | None = None) -> DoctorCheck:
    """Report `hooks/*.sh` scripts the gitignored hook wiring never references.

    `hooks/` is tracked but `.claude/settings.json` is not, so a hook can be
    committed, documented, and CI-tested while firing nowhere. Only `*.sh` is
    checked: `post-merge`/`post-checkout`/`pre-push` are real Git hooks, wired
    by `core.hooksPath` above rather than by this file.

    Also flags a worktree whose `.claude/settings.json` has fallen behind the
    main checkout's - `./shanks dev sync` only runs on demand, so nothing else
    notices a hook change that never made it into an existing worktree.
    """

    runner = subprocess.run if runner is None else runner
    settings = project / ".claude" / "settings.json"
    scripts = sorted(path.name for path in (project / "hooks").glob("*.sh"))
    if not settings.is_file():
        # A fresh clone and CI both legitimately lack it (it is gitignored),
        # and without it there is no wiring to compare against - so this is a
        # warning, while a script the existing wiring forgot is a failure.
        return DoctorCheck(
            "claude-hooks",
            True,
            "no .claude/settings.json; no Claude Code hooks are active here",
        )
    try:
        wiring = settings.read_text(encoding="utf-8")
        json.loads(wiring)
    except (OSError, ValueError) as error:
        return DoctorCheck(
            "claude-hooks", False, f".claude/settings.json is unusable: {error}"
        )
    unwired = [name for name in scripts if name not in wiring]
    if unwired:
        return DoctorCheck(
            "claude-hooks",
            False,
            "never referenced by .claude/settings.json: " + ", ".join(unwired),
        )
    stale = _stale_worktree_detail(project, settings, runner)
    if stale:
        return DoctorCheck("claude-hooks", False, stale)
    return DoctorCheck(
        "claude-hooks", True, f"{len(scripts)} hook scripts wired: {', '.join(scripts)}"
    )


def _github_environment(environment: Mapping[str, str]) -> dict[str, str]:
    keys = {
        "GH_HOST",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
    }
    result = {key: environment[key] for key in keys if key in environment}
    result["GIT_TERMINAL_PROMPT"] = "0"
    token = environment.get("GH_TOKEN") or environment.get("GITHUB_TOKEN")
    if token:
        result["GH_TOKEN"] = token
    result["GH_PROMPT_DISABLED"] = "1"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Shanks configuration or run-management command."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.show_mode or args.command == "mode":
        _print_mode()
        return 0
    if args.command in {"run", "runs"}:
        try:
            return _run_command(args)
        except (CliError, RunBusyError, WorkspaceError, ValueError, OSError) as error:
            print(f"shanks: {error}", file=sys.stderr)
            return 1
        except sqlite3.Error as error:
            print(f"shanks: checkpoint database error: {error}", file=sys.stderr)
            return 1

    if args.command == "doctor":
        return run_doctor()

    if args.command == "dev":
        try:
            if args.dev_command == "sync":
                dev_sync(
                    args.directories,
                    project_directory=args.project_directory,
                )
            else:
                dev_worktree(
                    args.branch,
                    project_directory=args.project_directory,
                    directory=args.directory,
                )
        except (CliError, OSError) as error:
            print(f"shanks: {error}", file=sys.stderr)
            return 1
        return 0

    parser.print_help()
    return 0


def dev_worktree(
    branch: str,
    *,
    project_directory: Path | None = None,
    directory: Path | None = None,
) -> Path:
    """Create an isolated dev worktree for one agent and return its path.

    A bare `git worktree add` leaves out everything gitignored - notably
    `.claude/settings.json` (so no hooks fire at all) and `.venv/` (so the test
    commands do not exist). Doing that by hand silently produces a *less*
    guarded worktree than the main checkout, which is the failure this wraps.
    """

    project = (project_directory or PROJECT_ROOT).expanduser().resolve()
    branch = branch.strip()
    if not branch:
        raise CliError("branch name cannot be empty")

    if directory is None:
        directory = project.parent / f"{project.name}-{branch.replace('/', '-')}"
    directory = directory.expanduser().resolve()
    if directory.exists():
        raise CliError(f"{directory} already exists")

    existing = subprocess.run(
        ("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"),
        cwd=project,
        capture_output=True,
        text=True,
    )
    add: tuple[str, ...] = ("git", "worktree", "add", str(directory))
    add += (branch,) if existing.returncode == 0 else ("-b", branch)
    created = subprocess.run(add, cwd=project, capture_output=True, text=True)
    if created.returncode != 0:
        raise CliError(f"git worktree add failed: {created.stderr.strip()}")

    hooks_synced = sync_local_guardrails(project, directory)
    venv_linked = (directory / ".venv").is_symlink()

    print(f"Created {directory} on branch {branch}")
    print(
        f"  hooks   {'.claude/settings.json copied' if hooks_synced else 'NOT SYNCED'}"
    )
    print(f"  venv    {'symlinked' if venv_linked else 'not linked'}")
    if not hooks_synced:
        print(
            "  warning: no .claude/settings.json in the project, so this "
            "worktree runs with no hooks (no dangerous-command or secret "
            "scanning). Create it before pointing an agent here.",
            file=sys.stderr,
        )
    print(f"\nPoint one agent at it with:\n  cd {directory}")
    return directory


def _worktree_directories(project: Path) -> list[Path]:
    listed = subprocess.run(
        ("git", "worktree", "list", "--porcelain"),
        cwd=project,
        capture_output=True,
        text=True,
    )
    if listed.returncode != 0:
        raise CliError(f"git worktree list failed: {listed.stderr.strip()}")
    return [
        Path(line[len("worktree ") :]).resolve()
        for line in listed.stdout.splitlines()
        if line.startswith("worktree ")
    ]


def dev_sync(
    directories: Sequence[Path] | None = None,
    *,
    project_directory: Path | None = None,
) -> list[Path]:
    """Re-copy the gitignored guardrails into worktrees that already exist.

    `sync_local_guardrails` otherwise runs exactly once, at `git worktree add`
    time, so every hook change strands every existing worktree until someone
    copies `.claude/settings.json` by hand. Defaults to every worktree this
    checkout knows about; the project checkout itself is the source, so it is
    always skipped.
    """

    project = (project_directory or PROJECT_ROOT).expanduser().resolve()
    if not (project / ".claude" / "settings.json").is_file():
        raise CliError(
            f"{project} has no .claude/settings.json to sync; create it first"
        )

    targets = (
        [directory.expanduser().resolve() for directory in directories]
        if directories
        else _worktree_directories(project)
    )
    synced: list[Path] = []
    for target in targets:
        if target == project:
            continue
        if not target.is_dir():
            print(f"  skipped {target} (does not exist)", file=sys.stderr)
            continue
        sync_local_guardrails(project, target)
        synced.append(target)
        venv = "venv linked" if (target / ".venv").is_symlink() else "no venv"
        print(f"  synced  {target} (settings copied, {venv})")

    print(f"Synced {len(synced)} worktree(s) from {project}")
    return synced


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shanks",
        description="Inspect and manage Shanks workflow runs.",
    )
    parser.add_argument(
        "--mode",
        "-mode",
        dest="show_mode",
        action="store_true",
        help="Show the current execution mode.",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("mode", help="Show the current execution mode.")
    commands.add_parser("doctor", help="Diagnose the local Shanks environment.")

    dev = commands.add_parser(
        "dev",
        help="Developer helpers for working on Shanks itself.",
    )
    dev_actions = dev.add_subparsers(dest="dev_command", required=True)
    worktree = dev_actions.add_parser(
        "worktree",
        help="Create an isolated worktree so a second agent has its own tree.",
    )
    worktree.add_argument("branch", help="Branch to create or check out there.")
    worktree.add_argument(
        "--directory",
        type=Path,
        default=None,
        help="Worktree path; defaults to ../<project>-<branch> beside the project.",
    )
    worktree.add_argument(
        "--project-dir",
        dest="project_directory",
        type=Path,
        default=None,
        help="Project to branch from; defaults to this checkout.",
    )

    sync = dev_actions.add_parser(
        "sync",
        help="Re-copy .claude/settings.json (and link .venv) into worktrees.",
    )
    sync.add_argument(
        "directories",
        nargs="*",
        type=Path,
        help="Worktrees to refresh; defaults to every worktree of this checkout.",
    )
    sync.add_argument(
        "--project-dir",
        dest="project_directory",
        type=Path,
        default=None,
        help="Project to copy from; defaults to this checkout.",
    )

    runs = commands.add_parser(
        "runs",
        aliases=("run",),
        help="List, inspect, resume, cancel, and clean up runs.",
    )
    runs.add_argument("--json", dest="json_output", action="store_true")
    _add_runtime_options(runs)
    actions = runs.add_subparsers(dest="runs_command", required=True)

    list_runs = actions.add_parser("list", help="List persisted runs.")
    _add_action_options(list_runs)

    status = actions.add_parser("status", help="Inspect one run and its checkpoint.")
    status.add_argument("run_id")
    _add_action_options(status)

    resume = actions.add_parser("resume", help="Resume an interrupted or stale run.")
    resume.add_argument("run_id")
    resume.add_argument("response", nargs="?")
    resume.add_argument(
        "--response",
        dest="response_option",
        help="The interrupt response, such as implement, learn, approve, or reject.",
    )
    resume.add_argument("--tool", choices=("claude", "codex"))
    _add_action_options(resume)

    cancel = actions.add_parser("cancel", help="Request a safe-boundary stop.")
    cancel.add_argument("run_id")
    cancel.add_argument(
        "--reason",
        default="Cancelled by user.",
        help="Reason persisted with the cancellation request.",
    )
    _add_action_options(cancel)

    recover = actions.add_parser("recover", help="Mark expired leases as abandoned.")
    _add_action_options(recover)

    cleanup = actions.add_parser(
        "cleanup",
        help="Delete old terminal checkpoint history.",
    )
    cleanup.add_argument("--keep-latest", type=_positive_int)
    cleanup.add_argument("--max-age", type=_nonnegative_float)
    cleanup.add_argument("--run-id")
    cleanup.add_argument(
        "--include-active",
        action="store_true",
        help="Allow cleanup of active checkpoint threads; terminal-only is safer.",
    )
    cleanup.add_argument(
        "--delete-records",
        action="store_true",
        help="Also delete lifecycle records older than --max-age.",
    )
    _add_action_options(cleanup)

    remove = actions.add_parser(
        "remove",
        help="Remove a completed run worktree and optionally its local branch.",
    )
    remove.add_argument("run_id")
    remove.add_argument(
        "--delete-branch",
        action="store_true",
        help="Also delete the run branch; requires development mode.",
    )
    remove.add_argument(
        "--force",
        action="store_true",
        help="Force worktree or unmerged-branch removal.",
    )
    _add_action_options(remove)

    prune = actions.add_parser(
        "prune",
        help="Report, and optionally remove, orphaned run worktrees and branches.",
    )
    prune.add_argument(
        "--apply",
        action="store_true",
        help="Remove orphans instead of only reporting them.",
    )
    prune.add_argument(
        "--delete-branches",
        action="store_true",
        help="Also remove orphaned local branches; requires development mode.",
    )
    prune.add_argument(
        "--include-remote",
        action="store_true",
        help="Also scan and remove orphaned branches on the remote.",
    )
    prune.add_argument(
        "--remote",
        default="origin",
        help="Remote name to scan for orphaned branches.",
    )
    prune.add_argument(
        "--force",
        action="store_true",
        help="Force worktree or unmerged-branch removal.",
    )
    _add_action_options(prune)
    return parser


def _add_action_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Print machine-readable JSON.",
    )
    _add_runtime_options(parser, suppress_defaults=True)


def _add_runtime_options(
    parser: argparse.ArgumentParser,
    *,
    suppress_defaults: bool = False,
) -> None:
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument(
        "--checkpoint-db",
        type=Path,
        default=default,
        help="Use this SQLite checkpoint database instead of the environment default.",
    )
    parser.add_argument(
        "--project-dir",
        dest="project_directory",
        type=Path,
        default=default,
        help="Project directory containing run worktrees.",
    )
    parser.add_argument(
        "--base-branch",
        default="main" if not suppress_defaults else default,
        help="Base branch used for workspace safety checks.",
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=default,
        help="Override the run worktree root.",
    )


def _run_command(args: argparse.Namespace) -> int:
    json_output = bool(getattr(args, "json_output", False))
    command = args.runs_command
    if command == "list":
        return _list_runs(args, json_output)
    if command == "status":
        return _status(args, json_output)
    if command == "resume":
        return _resume(args, json_output)
    if command == "cancel":
        return _cancel(args, json_output)
    if command == "recover":
        return _recover(args, json_output)
    if command == "cleanup":
        return _cleanup(args, json_output)
    if command == "remove":
        return _remove(args, json_output)
    if command == "prune":
        return _prune(args, json_output)
    raise CliError(f"unknown runs command: {command}")


@contextmanager
def _open_checkpointer(args: argparse.Namespace) -> Iterator[Any]:
    from graph import shared_checkpointer

    previous = os.environ.get("SHANKS_CHECKPOINT_DB")
    checkpointer = None
    if args.checkpoint_db is not None:
        os.environ["SHANKS_CHECKPOINT_DB"] = str(args.checkpoint_db)
    try:
        checkpointer = shared_checkpointer()
        yield checkpointer
    finally:
        if checkpointer is not None:
            checkpointer.conn.close()
        if previous is None:
            os.environ.pop("SHANKS_CHECKPOINT_DB", None)
        else:
            os.environ["SHANKS_CHECKPOINT_DB"] = previous


def _project_directory(args: argparse.Namespace) -> Path:
    project = Path(args.project_directory or Path.cwd()).expanduser().resolve()
    if not project.is_dir():
        raise CliError(f"project directory does not exist: {project}")
    return project


def _build_graph(
    args: argparse.Namespace, checkpointer: Any, *, tool: ToolName = "codex"
):
    from graph import build_graph

    return build_graph(
        checkpointer=checkpointer,
        tool=tool,
        project_directory=_project_directory(args),
        base_branch=args.base_branch,
        worktree_root=args.worktree_root,
    )


def _latest_checkpoint(checkpointer: Any, run_id: str) -> dict[str, Any] | None:
    checkpoint_tuple = checkpointer.get_tuple({"configurable": {"thread_id": run_id}})
    if checkpoint_tuple is None:
        return None
    checkpoint = checkpoint_tuple.checkpoint
    values = checkpoint.get("channel_values", {})
    config = checkpoint_tuple.config or {}
    configurable = config.get("configurable", {})
    return {
        "checkpoint_id": configurable.get("checkpoint_id"),
        "timestamp": checkpoint.get("ts"),
        "values": dict(values) if isinstance(values, dict) else {},
        "interrupts": _interrupt_payloads(
            pending
            for _, channel, pending in (checkpoint_tuple.pending_writes or ())
            if channel == "__interrupt__"
        ),
    }


def _interrupt_payloads(pending: Iterable[Any]) -> list[dict[str, Any]]:
    """Flatten pending LangGraph interrupts into printable prompt payloads."""

    return [
        {"id": getattr(item, "id", ""), "value": getattr(item, "value", item)}
        for group in pending
        for item in (group if isinstance(group, (list, tuple)) else (group,))
    ]


def _status_payload(
    run_id: str,
    record: Any,
    latest: dict[str, Any] | None,
) -> dict[str, Any]:
    values = latest["values"] if latest else {}
    checkpoint = None
    if latest is not None:
        checkpoint = {
            "id": latest["checkpoint_id"],
            "timestamp": latest["timestamp"],
            "status": values.get("status", ""),
            "run_lifecycle_status": values.get("run_lifecycle_status", ""),
            "cancel_requested": values.get("cancel_requested", False),
            "last_error": values.get("last_error", ""),
            "run_branch": values.get("run_branch", ""),
            "workspace_directory": values.get("workspace_directory", ""),
            "current_item_id": values.get("current_item_id", ""),
            "current_item_title": values.get("current_item_title", ""),
            "state_schema_version": values.get("state_schema_version", 0),
            "run_lease_expires_at": values.get("run_lease_expires_at", 0.0),
            "run_recovery_count": values.get("run_recovery_count", 0),
            "repo_drift": values.get("repo_drift", ""),
        }
    return {
        "run_id": run_id,
        "lifecycle": asdict(record) if record is not None else None,
        "checkpoint": checkpoint,
        "interrupts": latest["interrupts"] if latest else [],
        "recent_events": _recent_events(values.get("run_manifest", [])),
    }


def _recent_events(manifest: Any) -> list[dict[str, Any]]:
    """Summarize the newest run-manifest events without their bulky payloads."""

    if not isinstance(manifest, list):
        return []
    return [
        {
            key: event.get(key)
            for key in ("timestamp", "type", "node", "status", "error")
            if event.get(key)
        }
        for event in manifest[-RECENT_EVENT_LIMIT:]
        if isinstance(event, dict)
    ]


def _list_runs(args: argparse.Namespace, json_output: bool) -> int:
    with _open_checkpointer(args) as checkpointer:
        records = checkpointer.lifecycle_manager.list_runs()
        rows = []
        for record in records:
            latest = _latest_checkpoint(checkpointer, record.run_id)
            values = latest["values"] if latest else {}
            rows.append(
                {
                    **asdict(record),
                    "run_branch": values.get("run_branch", ""),
                    "workspace_directory": values.get("workspace_directory", ""),
                    "checkpoint_id": latest["checkpoint_id"] if latest else None,
                }
            )

    if json_output:
        _print_json(rows)
    elif not rows:
        print("No runs found.")
    else:
        print("RUN_ID\tSTATUS\tUPDATED\tRECOVERIES")
        for row in rows:
            print(
                f"{row['run_id']}\t{row['status']}\t"
                f"{_format_time(row['updated_at'])}\t{row['recovery_count']}"
            )
    return 0


def _status(args: argparse.Namespace, json_output: bool) -> int:
    with _open_checkpointer(args) as checkpointer:
        lifecycle = checkpointer.lifecycle_manager
        lifecycle.recover_stale()
        record = lifecycle.get_run(args.run_id)
        latest = _latest_checkpoint(checkpointer, args.run_id)
        if record is None and latest is None:
            raise CliError(f"run not found: {args.run_id}")
        payload = _status_payload(args.run_id, record, latest)

    if json_output:
        _print_json(payload)
    else:
        _print_human_status(payload)
    return 0


def _resume(args: argparse.Namespace, json_output: bool) -> int:
    response = args.response_option or args.response
    if not response:
        raise CliError("resume requires a response value")
    response_value: Any = response
    if response[:1] in {"{", "["}:
        try:
            response_value = json.loads(response)
        except json.JSONDecodeError:
            pass

    with _open_checkpointer(args) as checkpointer:
        latest = _latest_checkpoint(checkpointer, args.run_id)
        if latest is None:
            raise CliError(f"run not found: {args.run_id}")
        tool = args.tool or _tool_for_values(latest["values"])
        from langgraph.types import Command

        graph = _build_graph(args, checkpointer, tool=tool)
        result = graph.invoke(
            Command(resume=response_value),
            {"configurable": {"thread_id": args.run_id}},
        )
        payload = {
            "run_id": args.run_id,
            "status": result.get("status", "") if isinstance(result, dict) else "",
            "last_error": (
                result.get("last_error", "") if isinstance(result, dict) else ""
            ),
            "interrupted": isinstance(result, dict) and "__interrupt__" in result,
            "interrupts": _interrupt_payloads(
                [result["__interrupt__"]]
                if isinstance(result, dict) and "__interrupt__" in result
                else ()
            ),
        }

    if json_output:
        _print_json(payload)
    else:
        print(f"Run {args.run_id}: {payload['status'] or 'resumed'}")
        if payload["last_error"]:
            print(payload["last_error"])
        for interrupt in payload["interrupts"]:
            print("Waiting for a response:")
            for line in _interrupt_lines(interrupt["value"]):
                print(f"  {line}")
    return 0


def _cancel(args: argparse.Namespace, json_output: bool) -> int:
    with _open_checkpointer(args) as checkpointer:
        lifecycle = checkpointer.lifecycle_manager
        record = lifecycle.get_run(args.run_id)
        latest = _latest_checkpoint(checkpointer, args.run_id)
        if record is None and latest is None:
            raise CliError(f"run not found: {args.run_id}")
        if record is not None and record.status in {"complete", "failed", "cancelled"}:
            raise CliError(f"run {args.run_id!r} is already {record.status}")

        from graph import build_graph

        tool = _tool_for_values(latest["values"] if latest else {})
        graph = build_graph(
            checkpointer=checkpointer,
            tool=tool,
            project_directory=_project_directory(args),
            base_branch=args.base_branch,
            worktree_root=args.worktree_root,
        )
        config = {"configurable": {"thread_id": args.run_id}}
        active = lifecycle.is_active(args.run_id)
        graph.update_state(config, cancel_run(args.reason))
        result = None
        if not active:
            result = graph.invoke(None, config)
        payload = {
            "run_id": args.run_id,
            "status": (
                result.get("status", "cancelled")
                if isinstance(result, dict)
                else "cancellation_requested"
            ),
            "reason": args.reason.strip() or "Cancelled by user.",
            "active_owner_notified": active,
        }

    if json_output:
        _print_json(payload)
    else:
        if active:
            print(f"Cancellation requested for active run {args.run_id}.")
        else:
            print(f"Run {args.run_id}: {payload['status']}")
    return 0


def _recover(args: argparse.Namespace, json_output: bool) -> int:
    with _open_checkpointer(args) as checkpointer:
        recovered = checkpointer.lifecycle_manager.recover_stale()
    payload = {"runs_marked_abandoned": recovered}
    if json_output:
        _print_json(payload)
    else:
        print(f"Marked {recovered} stale run(s) as abandoned.")
    return 0


def _cleanup(args: argparse.Namespace, json_output: bool) -> int:
    if args.delete_records and args.max_age is None:
        raise CliError("--delete-records requires --max-age")
    with _open_checkpointer(args) as checkpointer:
        result = checkpointer.cleanup(
            keep_latest=args.keep_latest,
            max_age_seconds=args.max_age,
            terminal_only=not args.include_active,
            thread_id=args.run_id,
        )
        records_deleted = 0
        if args.delete_records:
            records_deleted = checkpointer.lifecycle_manager.cleanup(
                max_age_seconds=args.max_age,
                run_id=args.run_id,
            )
    payload = {**asdict(result), "records_deleted": records_deleted}
    if json_output:
        _print_json(payload)
    else:
        print(
            f"Scanned {payload['threads_scanned']} thread(s); deleted "
            f"{payload['checkpoints_deleted']} checkpoint(s), "
            f"{payload['writes_deleted']} write(s), and "
            f"{payload['records_deleted']} lifecycle record(s)."
        )
    return 0


def _remove(args: argparse.Namespace, json_output: bool) -> int:
    with _open_checkpointer(args) as checkpointer:
        lifecycle = checkpointer.lifecycle_manager
        record = lifecycle.get_run(args.run_id)
        latest = _latest_checkpoint(checkpointer, args.run_id)
        if record is None or latest is None:
            raise CliError(f"run {args.run_id!r} has no removable completed checkpoint")
        if record.status not in TERMINAL_LIFECYCLE_STATUSES:
            raise CliError(
                f"run {args.run_id!r} is {record.status}; only terminal runs can be removed"
            )
        if record.finished_at is None:
            raise CliError(f"run {args.run_id!r} has not finished")
        if record.status != "complete" and not args.force:
            raise CliError(
                "refusing to remove a failed or cancelled worktree without --force"
            )
        if lifecycle.is_active(args.run_id):
            raise CliError(f"run {args.run_id!r} still has an active lease")
        if args.delete_branch and not is_development_mode():
            raise CliError(
                "branch deletion requires SHANKS_MODE=development; worktree was not removed"
            )

        values = latest["values"]
        workspace_manager = RunWorkspaceManager(
            _project_directory(args),
            base_branch=args.base_branch,
            worktree_root=args.worktree_root,
        )
        expected = workspace_manager.workspace_for(args.run_id)
        directory = Path(values.get("workspace_directory") or expected.directory)
        branch = str(values.get("run_branch") or expected.branch)
        if directory.expanduser().resolve() != expected.directory.resolve():
            raise CliError(
                f"checkpoint worktree does not match the configured run path: {directory}"
            )
        if branch != expected.branch:
            raise CliError(
                f"checkpoint branch does not match the configured run branch: {branch}"
            )
        workspace_manager.remove(args.run_id, force=args.force, directory=directory)
        if args.delete_branch:
            workspace_manager.delete_branch(
                args.run_id,
                force=args.force,
                branch=branch,
                directory=directory,
            )
        payload = {
            "run_id": args.run_id,
            "worktree_removed": str(directory),
            "branch_deleted": branch if args.delete_branch else None,
        }

    if json_output:
        _print_json(payload)
    else:
        print(f"Removed worktree for run {args.run_id}: {directory}")
        if args.delete_branch:
            print(f"Deleted local branch: {branch}")
    return 0


def _prune(args: argparse.Namespace, json_output: bool) -> int:
    if args.apply and args.delete_branches and not is_development_mode():
        raise CliError("--delete-branches requires SHANKS_MODE=development")
    if args.apply and args.include_remote and not is_development_mode():
        raise CliError("--include-remote --apply requires SHANKS_MODE=development")

    with _open_checkpointer(args) as checkpointer:
        lifecycle = checkpointer.lifecycle_manager
        live_ids = {
            record.run_id
            for record in lifecycle.list_runs()
            if record.status not in TERMINAL_LIFECYCLE_STATUSES
            or lifecycle.is_active(record.run_id)
        }
        workspace_manager = RunWorkspaceManager(
            _project_directory(args),
            base_branch=args.base_branch,
            worktree_root=args.worktree_root,
        )
        # Ownership check: only ids belonging to a run this project still
        # considers live are protected from removal.
        live_run_ids = {
            workspace_manager.workspace_for(run_id).directory.name
            for run_id in live_ids
        }

        worktrees = _prune_targets(workspace_manager.list_worktrees(), live_run_ids)
        branches = _prune_targets(workspace_manager.list_branches(), live_run_ids)
        remote_branches = (
            _prune_targets(
                workspace_manager.list_remote_branches(args.remote), live_run_ids
            )
            if args.include_remote
            else []
        )

        if args.apply:
            for target in worktrees:
                if target["orphan"]:
                    target["action"] = _apply(
                        partial(
                            workspace_manager.remove, target["id"], force=args.force
                        )
                    )
            if args.delete_branches:
                for target in branches:
                    if target["orphan"]:
                        target["action"] = _apply(
                            partial(
                                workspace_manager.delete_branch,
                                target["id"],
                                force=args.force,
                            )
                        )
            if args.include_remote:
                for target in remote_branches:
                    if target["orphan"]:
                        target["action"] = _apply(
                            partial(
                                workspace_manager.delete_remote_branch,
                                target["id"],
                                remote=args.remote,
                            )
                        )

    payload = {
        "applied": bool(args.apply),
        "worktrees": worktrees,
        "branches": branches,
        "remote_branches": remote_branches,
    }
    if json_output:
        _print_json(payload)
    else:
        _print_prune_report(payload)
    return 0


def _prune_targets(ids: Sequence[str], live_run_ids: set[str]) -> list[dict[str, Any]]:
    targets = []
    for identifier in ids:
        orphan = identifier not in live_run_ids
        targets.append(
            {
                "id": identifier,
                "orphan": orphan,
                "action": "orphan" if orphan else "skipped: active run",
            }
        )
    return targets


def _apply(action: Callable[[], None]) -> str:
    try:
        action()
        return "removed"
    except WorkspaceError as error:
        return f"error: {error}"


def _print_prune_report(payload: dict[str, Any]) -> None:
    mode = "apply" if payload["applied"] else "dry-run"
    print(f"Prune report ({mode}):")
    sections = (
        ("Worktrees", payload["worktrees"]),
        ("Local branches", payload["branches"]),
        ("Remote branches", payload["remote_branches"]),
    )
    reported = False
    for label, targets in sections:
        if not targets:
            continue
        reported = True
        print(f"{label}:")
        for target in targets:
            print(f"  {target['id']}: {target['action']}")
    if not reported:
        print("Nothing to report.")


def _tool_for_values(values: dict[str, Any]) -> ToolName:
    model = str(values.get("assigned_model", "")).lower()
    return "claude" if "claude" in model else "codex"


def _print_mode() -> None:
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


def _print_human_status(payload: dict[str, Any]) -> None:
    print(f"Run: {payload['run_id']}")
    lifecycle = payload.get("lifecycle")
    if lifecycle:
        print(f"Lifecycle: {lifecycle['status']}")
        print(f"Updated: {_format_time(lifecycle['updated_at'])}")
        print(f"Recoveries: {lifecycle['recovery_count']}")
        if lifecycle["last_error"]:
            print(f"Lifecycle error: {lifecycle['last_error']}")
    checkpoint = payload.get("checkpoint")
    if checkpoint:
        print(f"Checkpoint: {checkpoint['id']}")
        print(f"Status: {checkpoint['status'] or 'unknown'}")
        if checkpoint["run_branch"]:
            print(f"Branch: {checkpoint['run_branch']}")
        if checkpoint["workspace_directory"]:
            print(f"Worktree: {checkpoint['workspace_directory']}")
        if checkpoint["last_error"]:
            print(f"Error: {checkpoint['last_error']}")
        if checkpoint["repo_drift"]:
            print(f"Repository drift: {checkpoint['repo_drift']}")
    for interrupt in payload.get("interrupts", []):
        print("Waiting for a response:")
        for line in _interrupt_lines(interrupt["value"]):
            print(f"  {line}")
    events = payload.get("recent_events", [])
    if events:
        print("Recent events:")
        for event in events:
            summary = " ".join(
                str(event[key]) for key in ("node", "type", "status") if event.get(key)
            )
            print(f"  {_format_time(event.get('timestamp', ''))} {summary}")


def _interrupt_lines(value: Any) -> list[str]:
    """Render one interrupt prompt as operator-readable lines."""

    if not isinstance(value, Mapping):
        return [str(value)]
    lines = [
        str(value[key])
        for key in ("message", "question", "error")
        if value.get(key) is not None
    ]
    options = value.get("options")
    if isinstance(options, list):
        lines.extend(
            (
                f"- {option.get('value', '')}: {option.get('label', '')}"
                if isinstance(option, Mapping)
                else f"- {option}"
            )
            for option in options
        )
    details = {
        key: item
        for key, item in value.items()
        if key not in {"message", "question", "error", "options", "type"}
    }
    if details:
        lines.append(json.dumps(details, default=str, sort_keys=True))
    return lines or [json.dumps(value, default=str, sort_keys=True)]


def _print_json(value: Any) -> None:
    print(json.dumps(value, default=str, sort_keys=True))


def _format_time(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat(
            timespec="seconds"
        )
    except (TypeError, ValueError, OSError):
        return str(value or "-")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least one")
    return parsed


def _nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
