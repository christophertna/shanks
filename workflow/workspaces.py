"""Run-scoped Git worktree management and workspace context."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .mode import is_development_mode

_CURRENT_WORKSPACE: ContextVar[Path | None] = ContextVar(
    "shanks_current_workspace",
    default=None,
)
_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


class WorkspaceError(RuntimeError):
    """Raised when a run cannot be assigned a safe isolated workspace."""


@dataclass(frozen=True, slots=True)
class RunWorkspace:
    """The branch and worktree assigned to one workflow run."""

    run_id: str
    branch: str
    directory: Path
    base_branch: str


@dataclass(slots=True)
class RunWorkspaceManager:
    """Create one reusable Git worktree for each checkpointed run."""

    project_directory: Path
    base_branch: str = "main"
    worktree_root: Path | None = None
    branch_prefix: str = "shanks/run"
    timeout_seconds: int = 30
    _lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.project_directory = self.project_directory.expanduser().resolve()
        root = self.worktree_root or self.project_directory / ".shanks" / "worktrees"
        self.worktree_root = root.expanduser().resolve()
        try:
            self.worktree_root.relative_to(self.project_directory)
        except ValueError as error:
            raise ValueError(
                "worktree_root must be inside project_directory"
            ) from error
        if not _safe_ref(self.base_branch):
            raise ValueError("base_branch contains unsupported characters")
        if not _safe_ref(self.branch_prefix):
            raise ValueError("branch_prefix contains unsupported characters")
        self._lock = threading.Lock()

    def ensure(self, run_id: str) -> RunWorkspace:
        """Create or reuse the workspace assigned to ``run_id``."""

        normalized_id = _normalize_component(run_id)
        if not normalized_id:
            raise WorkspaceError("run_id must contain at least one safe character")
        branch = f"{self.branch_prefix}/{normalized_id}"
        directory = self.worktree_root / normalized_id

        with self._lock:
            if directory.exists():
                return self._validate_existing(run_id, branch, directory)

            self.worktree_root.mkdir(parents=True, exist_ok=True)
            branch_exists = self._branch_exists(branch)
            if branch_exists:
                command = ("git", "worktree", "add", str(directory), branch)
            else:
                command = (
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    branch,
                    str(directory),
                    self.base_branch,
                )
            self._run(command, cwd=self.project_directory)

        return RunWorkspace(run_id, branch, directory, self.base_branch)

    def remove(self, run_id: str, *, force: bool = False) -> None:
        """Remove a run worktree; branch deletion is intentionally separate."""

        normalized_id = _normalize_component(run_id)
        if not normalized_id:
            return
        directory = self.worktree_root / normalized_id
        if not directory.exists():
            return
        parts = ["git", "worktree", "remove"]
        if force:
            parts.append("--force")
        parts.append(str(directory))
        with self._lock:
            self._run(tuple(parts), cwd=self.project_directory)

    def delete_branch(self, run_id: str, *, force: bool = False) -> None:
        """Delete this run's local branch only in explicit development mode."""

        if not is_development_mode():
            raise WorkspaceError(
                "I don't have permission to delete branches because Shanks is "
                "not in development mode; set SHANKS_MODE=development."
            )

        normalized_id = _normalize_component(run_id)
        if not normalized_id:
            return
        branch = f"{self.branch_prefix}/{normalized_id}"
        if branch == self.base_branch:
            raise WorkspaceError("Refusing to delete the base branch.")

        directory = self.worktree_root / normalized_id
        with self._lock:
            if directory.exists():
                raise WorkspaceError(
                    f"Remove worktree {directory} before deleting its branch."
                )
            if not self._branch_exists(branch):
                return
            command = ["git", "branch", "--delete"]
            if force:
                command.append("--force")
            command.append(branch)
            self._run(tuple(command), cwd=self.project_directory)

    def _validate_existing(
        self,
        run_id: str,
        branch: str,
        directory: Path,
    ) -> RunWorkspace:
        if not directory.is_dir() or not (directory / ".git").exists():
            raise WorkspaceError(f"workspace path is not a Git worktree: {directory}")
        current_branch = self._run(
            ("git", "branch", "--show-current"),
            cwd=directory,
        )
        if current_branch != branch:
            raise WorkspaceError(
                f"workspace {directory} belongs to branch {current_branch!r}, "
                f"expected {branch!r}"
            )
        return RunWorkspace(run_id, branch, directory, self.base_branch)

    def _branch_exists(self, branch: str) -> bool:
        result = self._run_result(
            ("git", "branch", "--list", branch),
            cwd=self.project_directory,
        )
        if result.returncode != 0:
            raise WorkspaceError(
                _command_error(result, "Could not inspect Git branches")
            )
        return any(
            line.lstrip("* ").strip() == branch for line in result.stdout.splitlines()
        )

    def _run(self, command: tuple[str, ...], *, cwd: Path) -> str:
        result = self._run_result(command, cwd=cwd)
        if result.returncode != 0:
            raise WorkspaceError(
                _command_error(result, "Git worktree operation failed")
            )
        return result.stdout.strip()

    def _run_result(self, command: tuple[str, ...], *, cwd: Path):
        try:
            return subprocess.run(
                command,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env={**_git_environment(), "GIT_TERMINAL_PROMPT": "0"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorkspaceError(str(error)) from error


@contextmanager
def workspace_scope(directory: Path | None) -> Iterator[None]:
    """Make a run workspace available to adapters without shared mutation."""

    token = _CURRENT_WORKSPACE.set(directory.resolve() if directory else None)
    try:
        yield
    finally:
        _CURRENT_WORKSPACE.reset(token)


def current_workspace_directory() -> Path | None:
    """Return the workspace for the current graph invocation, if any."""

    return _CURRENT_WORKSPACE.get()


def _normalize_component(value: str) -> str:
    if not isinstance(value, str):
        return ""
    raw = value.strip()
    component = _SAFE_COMPONENT.sub("-", raw).strip(".-")
    if component != raw:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        component = f"{component}-{digest}" if component else digest
    return component[:80]


def _safe_ref(value: str) -> bool:
    return bool(
        value
        and not value.startswith("-")
        and ".." not in value
        and "@{" not in value
        and re.fullmatch(r"[A-Za-z0-9._/-]+", value)
    )


def _git_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key in {"HOME", "LANG", "LC_ALL", "PATH"}
    }


def _command_error(result: subprocess.CompletedProcess, prefix: str) -> str:
    output = "\n".join(
        part.strip()
        for part in (result.stdout or "", result.stderr or "")
        if part and part.strip()
    )
    return f"{prefix}: {output or f'command exited with status {result.returncode}'}"


__all__ = [
    "RunWorkspace",
    "RunWorkspaceManager",
    "WorkspaceError",
    "current_workspace_directory",
    "workspace_scope",
]
