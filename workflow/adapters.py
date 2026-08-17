"""Agent adapter implementations for graph nodes and external runners."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contracts import AgentAdapter, AgentRequest, AgentResult
from .mode import is_dry_run
from .workspaces import current_workspace_directory, remaining_deadline_seconds

GPT56_LUNA_MODEL = "gpt-5.6-luna"
GPT56_LUNA_REASONING_EFFORT = "max"
CLAUDE_OPUS_48_MODEL = "claude-opus-4-8"
CLAUDE_OPUS_48_EFFORT = "medium"
CRITIC_OUTPUT_SCHEMA_PATH = Path(__file__).with_name("critic_output.schema.json")
DEBUGGER_OUTPUT_SCHEMA_PATH = Path(__file__).with_name("debugger_output.schema.json")
SANDBOX_CLAUDE_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "sandbox_claude.sh"
)
CLAUDE_READ_ONLY_TOOLS = "Read,Grep,Glob"
GUARDED_PATHS_FILE = (
    Path(__file__).resolve().parent.parent / "hooks" / "guarded-paths.txt"
)
# Matches hooks/guard-dependency-files.sh's template exception, since these
# files are meant to be edited and are not the real secret.
_GUARDED_PATH_TEMPLATE_EXCEPTIONS = frozenset(
    {".env.example", ".env.sample", ".env.template", ".env.dist"}
)
SECRET_SCAN_TIMEOUT_SECONDS = 60
ITEM_BUILT_MARKER = "<promise>ITEM_BUILT</promise>"
UNCERTAINTIES_MARKER = "RALPH_UNCERTAINTIES:"
ALLOWED_AGENT_EXECUTABLES = frozenset({"bash", "claude", "codex", "python", "python3"})
# Per-item validation runs a test command, never an agent, so it gets a
# narrower policy than the shared agent allowlist above: no shell interpreter
# and no inline-code flag, both of which would re-open arbitrary execution.
VALIDATION_EXECUTABLES = frozenset({"python", "python3"})
_VERSIONED_PYTHON_EXECUTABLE = re.compile(r"python3\.\d+\Z")
AGENT_ALLOWED_ENVIRONMENT_KEYS = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SHELL",
        "TMPDIR",
        "TMP",
        "TEMP",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    }
)
GITHUB_ENVIRONMENT_KEYS = frozenset(
    {
        "GH_HOST",
        "GH_TOKEN",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
    }
)
PR_JSON_FIELDS = (
    "number,url,state,mergedAt,title,body,updatedAt,mergeStateStatus,"
    "labels,reviewRequests,latestReviews,headRefName"
)
PR_LOOKUP_LIMIT = "20"
DEFAULT_STALE_AFTER_DAYS = 30
# Quick read-only lookups. They share GitHubAdapter._run with the preflight
# test suite, quality gates, and the side-effecting `gh pr create/edit/reopen`
# calls, whose hour-long budget would let one stalled call (an unreachable
# remote during the per-item drift fetch, a hung `gh auth status` in preflight)
# hold a node for the whole hour. Keep this in sync with _validate_command's
# allowlist: every read-only command it permits belongs here, or it silently
# falls back to the hour-long budget. Matched by prefix.
PROBE_COMMANDS = (
    ("git", "branch", "--show-current"),
    ("git", "status", "--short", "--untracked-files=all"),
    ("git", "rev-parse", "HEAD"),
    ("git", "rev-list", "--count"),
    ("git", "fetch"),
    ("git", "diff"),
    ("git", "ls-files"),
    ("gh", "auth", "status"),
    ("gh", "pr", "list"),
)
_SECRET_PATTERNS = (
    re.compile(
        r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,})\b"),
    re.compile(
        r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"authorization|password|secret)\b\s*[:=]\s*)(?:bearer\s+)?"
        r"[^\s,;]+"
    ),
    re.compile(r"(?i)(\bbearer\s+)[^\s,;]+"),
)


def _load_json_schema(path: Path) -> str:
    return json.dumps(json.loads(path.read_text(encoding="utf-8")))


@dataclass(slots=True)
class StubAgentAdapter:
    """Deterministic adapter used for local graph development and tests."""

    role: str
    model_name: str

    def run(self, request: AgentRequest) -> AgentResult:
        if self.role == "planner":
            return AgentResult(
                status="planned",
                assigned_model=self.model_name,
                plan=[
                    "Understand the current PRD item",
                    "Implement the change",
                    "Run validation",
                ],
                builder_instructions=request.instructions
                or "Implement the current PRD item.",
            )
        if self.role == "builder":
            return AgentResult(
                status="built",
                assigned_model=self.model_name,
                files_touched=["example.py"],
                item_built=True,
            )
        if self.role == "critic":
            return AgentResult(
                status="critic_audited",
                assigned_model=self.model_name,
                approved=True,
                feedback="Placeholder audit completed.",
            )
        if self.role == "validator":
            return AgentResult(
                status="validated",
                assigned_model=self.model_name,
                validation_passed=True,
            )
        if self.role == "debugger":
            return AgentResult(
                status="debugged",
                assigned_model=self.model_name,
                root_cause="Placeholder debugger analysis.",
                builder_instructions="Address the reported validation failure.",
            )

        return AgentResult(
            status="completed",
            assigned_model=self.model_name,
        )


@dataclass(slots=True)
class SubprocessAgentAdapter:
    """Run a configured CLI backend through the common adapter contract."""

    command: tuple[str, ...]
    model_name: str
    working_directory: Path | None = None
    timeout_seconds: int = 3600
    allowed_directories: tuple[Path, ...] = ()

    def run(self, request: AgentRequest) -> AgentResult:
        prompt = _format_request(request)
        cwd = (
            request.working_directory
            or current_workspace_directory()
            or self.working_directory
        )
        command = self._command_for(request)
        audit_command = _audit_command(command)
        guardrail_error = self._validate_execution(command, cwd)
        if guardrail_error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=guardrail_error,
                prompt=redact_secrets(prompt),
                commands=[audit_command],
            )

        timeout: float = self.timeout_seconds
        if request.timeout_seconds is not None:
            timeout = min(timeout, request.timeout_seconds)
        if timeout <= 0:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="CLI deadline has elapsed.",
                prompt=redact_secrets(prompt),
                commands=[audit_command],
            )

        try:
            completed = _run_subprocess(
                command,
                cwd=cwd,
                input_text=prompt,
                timeout=timeout,
                env=_agent_environment(),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=redact_secrets(str(error)),
                input_tokens=_estimate_tokens(prompt),
                prompt=redact_secrets(prompt),
                commands=[audit_command],
            )

        output = "\n".join(
            part
            for part in (
                redact_secrets((completed.stdout or "").strip()),
                redact_secrets((completed.stderr or "").strip()),
            )
            if part
        )
        if completed.returncode != 0:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=output or f"CLI exited with status {completed.returncode}",
                feedback=output,
                input_tokens=_estimate_tokens(prompt),
                output_tokens=_estimate_tokens(output),
                prompt=redact_secrets(prompt),
                commands=[audit_command],
            )

        return AgentResult(
            status="completed",
            assigned_model=self.model_name,
            feedback=output,
            input_tokens=_estimate_tokens(prompt),
            output_tokens=_estimate_tokens(output),
            prompt=redact_secrets(prompt),
            commands=[audit_command],
        )

    def _command_for(self, request: AgentRequest) -> tuple[str, ...]:
        directory = request.working_directory or current_workspace_directory()
        if directory is None or "--cd" not in self.command:
            return self.command
        index = self.command.index("--cd") + 1
        if index >= len(self.command):
            return self.command
        command = list(self.command)
        command[index] = str(directory)
        return tuple(command)

    def _validate_execution(
        self,
        command: tuple[str, ...],
        cwd: Path | None,
    ) -> str | None:
        if not command:
            return "Refusing to run an empty command."
        executable = Path(command[0]).name
        if not _is_allowed_executable(executable, ALLOWED_AGENT_EXECUTABLES):
            return f"Refusing to run unapproved executable: {executable}."

        roots = self.allowed_directories or (
            (self.working_directory,) if self.working_directory else ()
        )
        if cwd is not None:
            resolved_cwd = _resolve_path(cwd)
            if not roots or not _path_within_any(resolved_cwd, roots):
                return "Refusing to run outside the configured working directories."

        for raw_path in _command_path_arguments(command):
            path = Path(raw_path)
            if not path.is_absolute() and cwd is not None:
                path = Path(cwd) / path
            if not roots or not _path_within_any(_resolve_path(path), roots):
                return (
                    "Refusing to use a command path outside the configured directories."
                )
        return None


class RalphAdapter(SubprocessAgentAdapter):
    """Adapter for the project-local Ralph runner."""

    def __init__(
        self,
        project_directory: Path,
        *,
        base_directory: Path | None = None,
        tool: str = "codex",
        skill_name: str = "ponytail",
        max_iterations: int = 1,
    ) -> None:
        if tool not in {"claude", "codex"}:
            raise ValueError("tool must be 'claude' or 'codex'")
        if skill_name and not re.fullmatch(r"[A-Za-z0-9_-]+", skill_name):
            raise ValueError("skill_name contains unsupported characters")
        if (
            isinstance(max_iterations, bool)
            or not isinstance(max_iterations, int)
            or max_iterations < 1
        ):
            raise ValueError("max_iterations must be a positive integer")
        base_directory = base_directory or project_directory
        script = base_directory / "scripts" / "ralph" / "ralph.sh"
        super().__init__(
            command=(
                "bash",
                str(script),
                "--project-dir",
                str(project_directory),
                "--tool",
                tool,
                "--skill",
                skill_name,
                str(max_iterations),
            ),
            model_name=f"ralph:{tool}",
            working_directory=base_directory,
            allowed_directories=(project_directory, base_directory),
        )

    def run(self, request: AgentRequest) -> AgentResult:
        try:
            self._sync_prd_file(request)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=f"Could not sync Ralph PRD: {error}",
            )
        result = super().run(request)
        if result.status == "failed":
            return result
        result.uncertainties = _parse_uncertainties(result.feedback)
        if ITEM_BUILT_MARKER not in result.feedback:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=f"Ralph did not emit {ITEM_BUILT_MARKER}.",
                feedback=result.feedback,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
                prompt=result.prompt,
                commands=result.commands,
            )
        result.item_built = True
        return result

    def _sync_prd_file(self, request: AgentRequest) -> None:
        """Persist the graph's full PRD before Ralph reads its next story."""

        if not request.prd_items:
            return
        if request.working_directory:
            prd_file = request.working_directory / ".shanks" / "ralph" / "prd.json"
            prd_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            prd_file = Path(self.command[1]).parent / "prd.json"
            if not prd_file.parent.is_dir():
                return

        payload: dict[str, object] = {}
        if prd_file.exists():
            payload = json.loads(prd_file.read_text(encoding="utf-8"))
        raw_stories = payload.get("userStories", [])
        if not isinstance(raw_stories, list):
            raw_stories = []
        existing_stories: dict[str, dict[str, object]] = {}
        for raw_story in raw_stories:
            if not isinstance(raw_story, dict):
                continue
            story_id = raw_story.get("id")
            if isinstance(story_id, str) and story_id:
                existing_stories[story_id] = raw_story
        stories: list[dict[str, object]] = []
        for item in request.prd_items:
            item_id = item.get("id") or ""
            story = dict(existing_stories.get(item_id, {}))
            story.update(item)
            if "acceptance_criteria" in item:
                story["acceptanceCriteria"] = item["acceptance_criteria"]
                story.pop("acceptance_criteria", None)
            if "validation_command" in item:
                story["validationCommand"] = item["validation_command"]
                story.pop("validation_command", None)
            story.setdefault("passes", False)
            story.setdefault("validation", False)
            stories.append(story)
        payload.setdefault("project", request.task)
        payload.setdefault("description", request.task)
        payload["userStories"] = stories
        temporary_file = prd_file.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_file.replace(prd_file)

    def _command_for(self, request: AgentRequest) -> tuple[str, ...]:
        directory = request.working_directory or current_workspace_directory()
        command = list(self.command)
        if directory is not None and "--project-dir" in command:
            index = command.index("--project-dir") + 1
            if index < len(command):
                command[index] = str(directory)
        if directory is not None:
            run_directory = directory / ".shanks" / "ralph"
            command.extend(("--run-dir", str(run_directory)))
        return (
            *command,
            "--graph-item-id",
            request.item_id,
            "--graph-instructions",
            _format_request(request),
        )


class LocalTestAdapter(SubprocessAgentAdapter):
    """Run an item's validation command or the full local suite as a fallback."""

    def __init__(self, project_directory: Path) -> None:
        super().__init__(
            command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
            model_name="local-tests",
            working_directory=project_directory,
            allowed_directories=(project_directory,),
        )

    def run(self, request: AgentRequest) -> AgentResult:
        try:
            self._command_for(request)
        except ValueError as error:
            message = f"Invalid validation command: {error}"
            return AgentResult(
                status="validation_failed",
                assigned_model=self.model_name,
                error=message,
                feedback=message,
                validation_passed=False,
                validation_errors=[message],
                test_output=message,
            )
        result = super().run(request)
        if result.status == "failed":
            output = result.error or result.feedback or "Local tests failed."
            return AgentResult(
                status="validation_failed",
                assigned_model=self.model_name,
                error=result.error,
                feedback=result.feedback,
                validation_passed=False,
                validation_errors=output.splitlines(),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
                prompt=result.prompt,
                commands=result.commands,
                test_output=output,
            )
        return AgentResult(
            status="validated",
            assigned_model=self.model_name,
            feedback=result.feedback,
            validation_passed=True,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            prompt=result.prompt,
            commands=result.commands,
            test_output=result.feedback,
        )

    def _command_for(self, request: AgentRequest) -> tuple[str, ...]:
        command = request.validation_command.strip()
        if not command:
            return self.command
        parsed = tuple(shlex.split(command))
        if not parsed:
            return self.command
        executable = Path(parsed[0]).name
        if not _is_allowed_executable(executable, VALIDATION_EXECUTABLES):
            allowed = ", ".join(sorted(VALIDATION_EXECUTABLES))
            raise ValueError(
                f"{executable!r} is not an allowed validation executable ({allowed})."
            )
        for argument in parsed[1:]:
            # Short-flag clusters, so -c, -Ic and -uc are all rejected.
            if argument.startswith("-") and not argument.startswith("--"):
                if "c" in argument[1:]:
                    raise ValueError(f"inline-code flag {argument!r} is not allowed.")
        return parsed


class DebuggerAdapter(SubprocessAgentAdapter):
    """Analyze validation failures with a read-only structured Codex run."""

    __slots__ = ()

    def __init__(
        self,
        project_directory: Path,
        *,
        tool: str = "codex",
        model_name: str | None = None,
        timeout_seconds: int = 3600,
    ) -> None:
        if tool not in {"claude", "codex"}:
            raise ValueError("tool must be 'claude' or 'codex'")
        if tool == "claude":
            schema = _load_json_schema(DEBUGGER_OUTPUT_SCHEMA_PATH)
            command: tuple[str, ...] = (
                "claude",
                "--print",
                "--permission-mode",
                "plan",
                "--tools",
                CLAUDE_READ_ONLY_TOOLS,
                "--json-schema",
                schema,
                "--no-session-persistence",
            )
        else:
            command = (
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--cd",
                str(project_directory),
                "--output-schema",
                str(DEBUGGER_OUTPUT_SCHEMA_PATH),
            )
        super().__init__(
            command=command,
            model_name=model_name or f"{tool}-debugger",
            working_directory=project_directory,
            timeout_seconds=timeout_seconds,
            allowed_directories=(project_directory, DEBUGGER_OUTPUT_SCHEMA_PATH.parent),
        )

    def run(self, request: AgentRequest) -> AgentResult:
        raw_result = super().run(_debugger_request(request))
        if raw_result.status == "failed":
            return raw_result
        return _debugger_result(self, raw_result)


@dataclass(slots=True)
class GitHubAdapter:
    """Commit validated items, then reconcile the branch's pull request."""

    project_directory: Path
    remote: str = "origin"
    base_branch: str = "main"
    test_command: str = ".venv/bin/python -m unittest discover -s tests"
    timeout_seconds: int = 3600
    probe_timeout_seconds: int = 60
    initial_dirty_files: tuple[str, ...] | None = None
    reviewers: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    stale_after_days: int | None = DEFAULT_STALE_AFTER_DAYS
    reopen_closed: bool = False
    protected_branches: tuple[str, ...] = ("main", "master")
    reviewer_allowlist: tuple[str, ...] | None = None
    label_allowlist: tuple[str, ...] | None = None

    model_name = "github"
    REQUIRED_TOOLS = ("git", "gh", "bash", "jq", "gitleaks")

    def __post_init__(self) -> None:
        self.project_directory = self.project_directory.resolve()
        if self.initial_dirty_files is None:
            self.initial_dirty_files = tuple(self._status_files())
        if self.stale_after_days is not None and (
            isinstance(self.stale_after_days, bool)
            or not isinstance(self.stale_after_days, int)
            or self.stale_after_days < 0
        ):
            raise ValueError("stale_after_days must be a non-negative integer or None")
        if (
            isinstance(self.probe_timeout_seconds, bool)
            or not isinstance(self.probe_timeout_seconds, int)
            or self.probe_timeout_seconds < 1
        ):
            raise ValueError("probe_timeout_seconds must be a positive integer")
        if not self._safe_ref(self.remote):
            raise ValueError("remote contains unsupported characters")
        if not self._safe_ref(self.base_branch):
            raise ValueError("base_branch contains unsupported characters")
        self.protected_branches = _branch_values(self.protected_branches)
        if self.base_branch not in self.protected_branches:
            self.protected_branches = (*self.protected_branches, self.base_branch)
        self.reviewers = _policy_values(self.reviewers)
        self.labels = _policy_values(self.labels)
        reviewer_allowlist = (
            self.reviewers
            if self.reviewer_allowlist is None
            else self.reviewer_allowlist
        )
        label_allowlist = (
            self.labels if self.label_allowlist is None else self.label_allowlist
        )
        self.reviewer_allowlist = _policy_values(reviewer_allowlist)
        self.label_allowlist = _policy_values(label_allowlist)
        _validate_policy_values("reviewers", self.reviewers)
        _validate_policy_values("labels", self.labels)
        _validate_policy_values("reviewer_allowlist", self.reviewer_allowlist)
        _validate_policy_values("label_allowlist", self.label_allowlist)
        for kind, values, allowed in (
            ("reviewers", self.reviewers, self.reviewer_allowlist),
            ("labels", self.labels, self.label_allowlist),
        ):
            missing = [
                value
                for value in values
                if value.casefold() not in {item.casefold() for item in allowed}
            ]
            if missing:
                raise ValueError(
                    f"{kind} contains values outside its configured allowlist: "
                    + ", ".join(missing)
                )

    def preflight(self) -> AgentResult:
        """Check tools, branch state, GitHub auth, and the test environment."""

        commands: list[list[str]] = []
        missing = [tool for tool in self.REQUIRED_TOOLS if shutil.which(tool) is None]
        if not Path(sys.executable).exists():
            missing.append(sys.executable)
        if missing:
            return AgentResult(
                status="preflight_failed",
                assigned_model=self.model_name,
                error=f"Missing required tools: {', '.join(missing)}.",
            )

        branch = self._run(("git", "branch", "--show-current"))
        commands.extend(branch.commands)
        if branch.status == "failed":
            return _preflight_failure(branch.error or branch.feedback, commands)
        branch_name = branch.feedback.strip()
        if not branch_name or branch_name == self.base_branch:
            return _preflight_failure(
                f"Run from a non-{self.base_branch} branch; current branch is "
                f"{branch_name or 'unknown'}.",
                commands,
            )

        status = self._run(("git", "status", "--short", "--untracked-files=all"))
        commands.extend(status.commands)
        if status.status == "failed":
            return _preflight_failure(status.error or status.feedback, commands)
        if status.feedback.strip():
            return _preflight_failure(
                "Working tree is not clean:\n" + status.feedback.strip(),
                commands,
            )

        auth = self._run(("gh", "auth", "status"))
        commands.extend(auth.commands)
        if auth.status == "failed":
            return _preflight_failure(
                "GitHub CLI authentication failed: " + (auth.error or auth.feedback),
                commands,
            )

        project_directory = self._project_directory()
        tests = LocalTestAdapter(project_directory).run(
            AgentRequest(
                task="Run the preflight test suite.",
                working_directory=project_directory,
            )
        )
        commands.extend(tests.commands)
        if tests.status != "validated":
            return _preflight_failure(
                "Preflight test suite failed: " + (tests.error or tests.feedback),
                commands,
            )
        quality = self._run(self._quality_gate_command())
        commands.extend(quality.commands)
        if quality.status == "failed":
            return _preflight_failure(
                "Preflight quality gates failed: "
                + (quality.error or quality.feedback),
                commands,
            )
        return AgentResult(
            status="preflight_passed",
            assigned_model=self.model_name,
            feedback=(
                f"branch={branch_name}; working tree clean; GitHub auth ready; "
                "test suite and quality gates passed"
            ),
            commands=commands,
            test_output=tests.feedback,
        )

    def drift_report(self) -> AgentResult:
        """Describe upstream and worktree drift for the next agent prompt."""

        # Advisory context, not a gate: an offline fetch or a detached upstream
        # records a note and lets the run continue, unlike the safety-critical
        # checks that fail closed.
        upstream = f"{self.remote}/{self.base_branch}"
        commands: list[list[str]] = []
        notes: list[str] = []

        fetch = self._run(("git", "fetch", "--quiet", self.remote, self.base_branch))
        commands.extend(fetch.commands)
        if fetch.status == "failed":
            notes.append(
                f"Could not refresh {upstream}: {fetch.error or fetch.feedback}"
            )
        else:
            behind = self._run(("git", "rev-list", "--count", f"HEAD..{upstream}"))
            commands.extend(behind.commands)
            if behind.status == "failed":
                notes.append(
                    f"Could not compare this branch against {upstream}: "
                    + (behind.error or behind.feedback)
                )
            elif behind.feedback.strip() not in {"", "0"}:
                notes.append(
                    f"This branch is {behind.feedback.strip()} commit(s) behind "
                    f"{upstream}; rebase or account for that before assuming the "
                    "working tree matches upstream."
                )

        status = self._run(("git", "status", "--short", "--untracked-files=all"))
        commands.extend(status.commands)
        if status.status == "failed":
            notes.append(
                "Could not read the working tree status: "
                + (status.error or status.feedback)
            )
        elif status.feedback.strip():
            notes.append(
                "Uncommitted changes already in the worktree:\n"
                + status.feedback.strip()
            )

        return AgentResult(
            status="drift_checked",
            assigned_model=self.model_name,
            feedback="\n".join(notes),
            commands=commands,
        )

    def policy_gate(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
        """Reject high-risk paths or leaked secrets before anything is staged."""

        # ponytail: no dependency-license allowlist exists in this repo, so
        # license policy is not enforced here. Add pip-licenses plus an
        # allowed-license list if that need ever shows up.
        commands: list[list[str]] = []
        files = self._candidate_files(files_touched, commands=commands)
        if not files:
            return AgentResult(
                status="policy_gate_passed",
                assigned_model=self.model_name,
                commands=commands,
            )

        if os.environ.get("SHANKS_ALLOW_DEPENDENCY_EDIT") != "1":
            guarded = _matching_guarded_files(files)
            if guarded:
                return AgentResult(
                    status="policy_gate_failed",
                    assigned_model=self.model_name,
                    error=(
                        "Refusing to commit high-risk file(s): "
                        + ", ".join(guarded)
                        + ". Set SHANKS_ALLOW_DEPENDENCY_EDIT=1 to override."
                    ),
                    files_touched=files,
                    commands=commands,
                )

        secret_summary = _scan_for_secrets(self._project_directory(), files)
        if secret_summary is None:
            return AgentResult(
                status="policy_gate_failed",
                assigned_model=self.model_name,
                error="Refusing to commit: could not run the gitleaks secret scan "
                "(missing gitleaks, an elapsed run deadline, or a subprocess "
                "error; see ./shanks doctor).",
                files_touched=files,
                commands=commands,
            )
        if secret_summary:
            return AgentResult(
                status="policy_gate_failed",
                assigned_model=self.model_name,
                error=f"Refusing to commit a likely secret: {secret_summary}.",
                files_touched=files,
                commands=commands,
            )

        return AgentResult(
            status="policy_gate_passed",
            assigned_model=self.model_name,
            files_touched=files,
            commands=commands,
        )

    def commit_item(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
        if is_dry_run():
            return self.preview_commit_item(item_id, item_title, files_touched)
        invalid_files = [
            file for file in files_touched if self._normalize_file(file) is None
        ]
        if invalid_files:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to commit a path outside the project directory.",
            )
        commands: list[list[str]] = []
        files = self._candidate_files(files_touched, commands=commands)
        if not files:
            return AgentResult(
                status="no_changes",
                assigned_model=self.model_name,
                commands=commands,
            )

        added = self._run(("git", "add", "--", *files))
        commands.extend(added.commands)
        if added.status == "failed":
            return _attach_commands(added, commands)

        diff_result = self._run(
            ("git", "diff", "--cached", "--no-ext-diff", "--", *files)
        )
        commands.extend(diff_result.commands)
        if diff_result.status == "failed":
            return _attach_commands(diff_result, commands)
        diff = diff_result.feedback

        quality = self._run(self._quality_gate_command(staged=True))
        commands.extend(quality.commands)
        if quality.status == "failed":
            quality.diff = diff
            return _attach_commands(quality, commands)

        message = f"feat: {item_id} - {item_title}".strip()
        committed = self._run(("git", "commit", "--only", "-m", message, "--", *files))
        commands.extend(committed.commands)
        if committed.status == "failed":
            output = (committed.error or committed.feedback).lower()
            if "nothing to commit" in output:
                return AgentResult(
                    status="no_changes",
                    assigned_model=self.model_name,
                    commands=commands,
                    diff=diff,
                )
            committed.diff = diff
            return _attach_commands(committed, commands)

        sha = self._run(("git", "rev-parse", "HEAD"))
        commands.extend(sha.commands)
        return AgentResult(
            status="committed",
            assigned_model=self.model_name,
            files_touched=files,
            feedback=committed.feedback,
            commit_sha=sha.feedback.strip() if sha.status != "failed" else "",
            commands=commands,
            diff=diff,
        )

    def preview_commit_item(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
        """Describe the commit without staging or committing anything."""

        invalid_files = [
            file for file in files_touched if self._normalize_file(file) is None
        ]
        if invalid_files:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to preview a path outside the project directory.",
            )
        commands: list[list[str]] = []
        files = self._candidate_files(files_touched, commands=commands)
        if not files:
            return AgentResult(
                status="no_changes",
                assigned_model=self.model_name,
                commands=commands,
            )

        diff_result = self._run(("git", "diff", "HEAD", "--no-ext-diff", "--", *files))
        commands.extend(diff_result.commands)
        if diff_result.status == "failed":
            return _attach_commands(diff_result, commands)
        diffs = [diff_result.feedback] if diff_result.feedback else []
        untracked = self._untracked_files(files, commands=commands)
        for file in untracked:
            untracked_diff = self._run(
                ("git", "diff", "--no-index", "--", "/dev/null", file),
                allow_exit_1=True,
            )
            commands.extend(untracked_diff.commands)
            if untracked_diff.status == "failed":
                return _attach_commands(untracked_diff, commands)
            if untracked_diff.feedback:
                diffs.append(untracked_diff.feedback)

        message = f"feat: {item_id} - {item_title}".strip()
        commands.extend(
            _audit_command(command)
            for command in (
                ("git", "add", "--", *files),
                ("git", "diff", "--cached", "--no-ext-diff", "--", *files),
                self._quality_gate_command(staged=True),
                ("git", "commit", "--only", "-m", message, "--", *files),
                ("git", "rev-parse", "HEAD"),
            )
        )
        return AgentResult(
            status="commit_preview",
            assigned_model=self.model_name,
            files_touched=files,
            feedback=f"Dry-run: would commit {message}.",
            commands=commands,
            diff="\n".join(diffs),
        )

    def push_branch(self) -> AgentResult:
        if is_dry_run():
            return self.preview_push_branch()
        commands: list[list[str]] = []
        branch_result = self._run(("git", "branch", "--show-current"))
        commands.extend(branch_result.commands)
        if branch_result.status == "failed":
            return _attach_commands(branch_result, commands)
        branch = branch_result.feedback.strip()
        if not branch or self._is_protected_branch(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to push a protected branch.",
                commands=commands,
            )

        pushed = self._run(("git", "push", "-u", self.remote, branch))
        commands.extend(pushed.commands)
        if pushed.status == "failed":
            return _attach_commands(pushed, commands)

        return AgentResult(
            status="branch_pushed",
            assigned_model=self.model_name,
            feedback=branch,
            commands=commands,
        )

    def preview_push_branch(self) -> AgentResult:
        """Describe the branch push without contacting the remote."""

        commands: list[list[str]] = []
        branch_result = self._run(("git", "branch", "--show-current"))
        commands.extend(branch_result.commands)
        if branch_result.status == "failed":
            return _attach_commands(branch_result, commands)
        branch = branch_result.feedback.strip()
        if not branch or self._is_protected_branch(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to preview a push from a protected branch.",
                commands=commands,
            )

        commands.append(_audit_command(("git", "push", "-u", self.remote, branch)))
        return AgentResult(
            status="branch_push_preview",
            assigned_model=self.model_name,
            feedback=branch,
            commands=commands,
        )

    def open_pull_request(self, task: str, *, branch: str = "") -> AgentResult:
        if is_dry_run():
            return self.preview_open_pull_request(task, branch=branch)
        commands: list[list[str]] = []
        if not branch:
            branch_result = self._run(("git", "branch", "--show-current"))
            commands.extend(branch_result.commands)
            if branch_result.status == "failed":
                return _attach_commands(branch_result, commands)
            branch = branch_result.feedback.strip()
        if not branch or self._is_protected_branch(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to open a PR from a protected branch.",
                commands=commands,
            )
        if not self._safe_ref(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to open a PR for an unsafe branch name.",
                commands=commands,
            )

        existing = self._run(self._pull_request_list_command(branch))
        commands.extend(existing.commands)
        if existing.status == "failed":
            return _attach_commands(existing, commands)
        try:
            existing_prs = json.loads(existing.feedback or "[]")
        except json.JSONDecodeError as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=f"Could not parse existing PR lookup: {error}",
                feedback=existing.feedback,
                commands=commands,
            )
        if not isinstance(existing_prs, list):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Existing PR lookup returned an invalid response.",
                feedback=existing.feedback,
                commands=commands,
            )
        if existing_prs:
            if not all(isinstance(pr, dict) for pr in existing_prs):
                return AgentResult(
                    status="failed",
                    assigned_model=self.model_name,
                    error="Existing PR lookup returned an invalid PR entry.",
                    feedback=existing.feedback,
                    commands=commands,
                )
            return self._reconcile_existing_prs(
                [pr for pr in existing_prs if isinstance(pr, dict)],
                task,
                commands,
                lookup_feedback=existing.feedback,
            )

        title, body = self._pull_request_text(task)
        create_command = [
            "gh",
            "pr",
            "create",
            "--base",
            self.base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]
        for label in self.labels:
            create_command.extend(("--label", label))
        for reviewer in self.reviewers:
            create_command.extend(("--reviewer", reviewer))
        created = self._run(tuple(create_command))
        commands.extend(created.commands)
        if created.status == "failed":
            return _attach_commands(created, commands)

        pr_url = next(
            (part for part in created.feedback.split() if part.startswith("https://")),
            "",
        )
        return AgentResult(
            status="pr_created",
            assigned_model=self.model_name,
            feedback=created.feedback,
            pr_url=pr_url,
            commands=commands,
            pr_state="open",
            pr_number=_pull_request_number(pr_url),
            pr_reviewers=list(self.reviewers),
            pr_labels=list(self.labels),
        )

    def preview_open_pull_request(
        self,
        task: str,
        branch: str = "",
    ) -> AgentResult:
        """Describe PR lookup/creation without changing GitHub."""

        commands: list[list[str]] = []
        if not branch:
            branch_result = self._run(("git", "branch", "--show-current"))
            commands.extend(branch_result.commands)
            if branch_result.status == "failed":
                return _attach_commands(branch_result, commands)
            branch = branch_result.feedback.strip()
        if not branch or self._is_protected_branch(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to preview a PR from a protected branch.",
                commands=commands,
            )
        if not self._safe_ref(branch):
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to preview a PR for an unsafe branch name.",
                commands=commands,
            )

        title, body = self._pull_request_text(task)
        create_command = [
            "gh",
            "pr",
            "create",
            "--base",
            self.base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]
        for label in self.labels:
            create_command.extend(("--label", label))
        for reviewer in self.reviewers:
            create_command.extend(("--reviewer", reviewer))
        commands.extend(
            [
                _audit_command(self._pull_request_list_command(branch)),
                _audit_command(tuple(create_command)),
            ]
        )
        return AgentResult(
            status="pull_request_preview",
            assigned_model=self.model_name,
            feedback=(
                "Dry-run: would inspect the branch pull request and create or "
                "reconcile it."
            ),
            commands=commands,
            pr_state="preview",
            pr_reviewers=list(self.reviewers),
            pr_labels=list(self.labels),
        )

    def publish_pr(self, task: str) -> AgentResult:
        """Push and open a PR for callers that do not need approval boundaries."""

        pushed = self.push_branch()
        if pushed.status not in {"branch_pushed", "branch_push_preview"}:
            return pushed
        opened = self.open_pull_request(task, branch=pushed.feedback.strip())
        return _attach_commands(opened, [*pushed.commands, *opened.commands])

    def _reconcile_existing_prs(
        self,
        pull_requests: list[dict[str, object]],
        task: str,
        commands: list[list[str]],
        *,
        lookup_feedback: str,
    ) -> AgentResult:
        selected: dict[str, object] | None = None
        selected_state = ""
        for state in ("open", "closed", "merged"):
            for pull_request in pull_requests:
                current_state = self._pull_request_state(pull_request)
                if current_state is None:
                    return AgentResult(
                        status="failed",
                        assigned_model=self.model_name,
                        error="Existing PR lookup returned an invalid PR state.",
                        feedback=lookup_feedback,
                        commands=commands,
                    )
                if current_state == state:
                    selected = pull_request
                    selected_state = current_state
                    break
            if selected is not None:
                break

        if selected is None:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Existing PR lookup returned no recognized PR state.",
                feedback=lookup_feedback,
                commands=commands,
            )

        pr_url = self._pull_request_url(selected)
        target = self._pull_request_target(selected)
        if not pr_url or not target:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Existing PR lookup returned no usable URL or number.",
                feedback=lookup_feedback,
                commands=commands,
            )

        if selected_state == "merged":
            return AgentResult(
                status="pr_merged",
                assigned_model=self.model_name,
                feedback=lookup_feedback,
                pr_url=pr_url,
                commands=commands,
                pr_state="merged",
                pr_number=_pull_request_number(pr_url)
                or str(selected.get("number", "")),
            )

        if selected_state == "closed":
            if not self.reopen_closed:
                return AgentResult(
                    status="pr_closed",
                    assigned_model=self.model_name,
                    feedback=lookup_feedback,
                    pr_url=pr_url,
                    commands=commands,
                    pr_state="closed",
                    pr_number=_pull_request_number(pr_url)
                    or str(selected.get("number", "")),
                )
            reopened = self._run(("gh", "pr", "reopen", target))
            commands.extend(reopened.commands)
            if reopened.status == "failed":
                return _attach_commands(reopened, commands)
            return self._reconcile_open_pr(
                selected,
                task,
                commands,
                lookup_feedback=lookup_feedback,
                reopened=True,
            )

        return self._reconcile_open_pr(
            selected,
            task,
            commands,
            lookup_feedback=lookup_feedback,
        )

    def _reconcile_open_pr(
        self,
        pull_request: dict[str, object],
        task: str,
        commands: list[list[str]],
        *,
        lookup_feedback: str,
        reopened: bool = False,
    ) -> AgentResult:
        pr_url = self._pull_request_url(pull_request)
        target = self._pull_request_target(pull_request)
        title, body = self._pull_request_text(task)
        edit_args: list[str] = []
        if self._pr_text_needs_update(pull_request, title, body):
            edit_args.extend(("--title", title, "--body", body))

        current_labels = _pull_request_names(pull_request.get("labels"), "name")
        current_reviewers = _pull_request_names(
            pull_request.get("reviewRequests"), "login"
        )
        current_reviewers.update(
            _pull_request_names(pull_request.get("latestReviews"), "login")
        )
        for label in self.labels:
            if label.casefold() not in current_labels:
                edit_args.extend(("--add-label", label))
        for reviewer in self.reviewers:
            if reviewer.casefold() not in current_reviewers:
                edit_args.extend(("--add-reviewer", reviewer))

        feedback = [lookup_feedback]
        if edit_args:
            edited = self._run(tuple(("gh", "pr", "edit", target, *edit_args)))
            commands.extend(edited.commands)
            if edited.status == "failed":
                return _attach_commands(edited, commands)
            if edited.feedback:
                feedback.append(edited.feedback)

        stale = self._is_stale_pull_request(pull_request)
        status = "pr_stale" if stale else "pr_created"
        if reopened and not stale:
            status = "pr_reopened"
        return AgentResult(
            status=status,
            assigned_model=self.model_name,
            feedback="\n".join(part for part in feedback if part),
            pr_url=pr_url,
            commands=commands,
            pr_state="open",
            pr_stale=stale,
            pr_number=_pull_request_number(pr_url)
            or str(pull_request.get("number", "")),
            pr_reviewers=list(self.reviewers),
            pr_labels=list(self.labels),
        )

    def _pull_request_list_command(self, branch: str) -> tuple[str, ...]:
        return (
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            PR_JSON_FIELDS,
            "--limit",
            PR_LOOKUP_LIMIT,
        )

    def _pull_request_text(self, task: str) -> tuple[str, str]:
        summary = redact_secrets(" ".join(task.split())) or (
            "Implement the planned PRD items"
        )
        title = f"feat: {summary}"
        if len(title) > 50:
            title = f"{title[:47].rstrip()}..."
        body = "\n".join(
            (
                "## Why",
                f"- {summary}",
                "",
                "## Tested",
                f"- `{redact_secrets(self.test_command)}`",
            )
        )
        return title, body

    def _pr_text_needs_update(
        self,
        pull_request: dict[str, object],
        title: str,
        body: str,
    ) -> bool:
        return any(
            field in pull_request and pull_request[field] != expected
            for field, expected in (("title", title), ("body", body))
        )

    @staticmethod
    def _pull_request_state(pull_request: dict[str, object]) -> str | None:
        if pull_request.get("mergedAt") or pull_request.get("merged") is True:
            return "merged"
        raw_state = pull_request.get("state")
        if raw_state is None:
            return "open"
        state = str(raw_state).strip().lower()
        if state in {"open", "closed", "merged"}:
            return state
        return None

    @staticmethod
    def _pull_request_url(pull_request: dict[str, object]) -> str:
        url = pull_request.get("url", "")
        return url.strip() if isinstance(url, str) else ""

    @staticmethod
    def _pull_request_target(pull_request: dict[str, object]) -> str:
        number = pull_request.get("number")
        if isinstance(number, int) and not isinstance(number, bool):
            return str(number)
        if isinstance(number, str) and number.strip().isdigit():
            return number.strip()
        return GitHubAdapter._pull_request_url(pull_request)

    def _is_stale_pull_request(self, pull_request: dict[str, object]) -> bool:
        if "headRefName" in pull_request and not pull_request.get("headRefName"):
            return True
        if str(pull_request.get("mergeStateStatus", "")).upper() == "BEHIND":
            return True
        if self.stale_after_days is None or self.stale_after_days == 0:
            return False
        updated_at = pull_request.get("updatedAt")
        if not isinstance(updated_at, str) or not updated_at.strip():
            return False
        try:
            timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - timestamp
        return age.total_seconds() >= self.stale_after_days * 86400

    def _candidate_files(
        self,
        files_touched: list[str],
        *,
        commands: list[list[str]] | None = None,
    ) -> list[str]:
        current = self._status_files(commands=commands)
        baseline = {
            normalized
            for file in (self.initial_dirty_files or ())
            if (normalized := self._normalize_file(file)) is not None
        }
        fresh = [
            normalized
            for path in current
            if (normalized := self._normalize_file(path)) is not None
            and normalized not in baseline
        ]
        requested = {
            normalized
            for file in files_touched
            if (normalized := self._normalize_file(file)) is not None
        }
        return [path for path in fresh if not requested or path in requested]

    def _status_files(self, *, commands: list[list[str]] | None = None) -> list[str]:
        result = self._run(("git", "status", "--short", "--untracked-files=all"))
        if commands is not None:
            commands.extend(result.commands)
        if result.status == "failed":
            return []
        files = []
        for line in result.feedback.splitlines():
            path = line[3:] if len(line) >= 3 else line
            if " -> " in path:
                path = path.rsplit(" -> ", 1)[-1]
            if path:
                files.append(path)
        return files

    def _untracked_files(
        self,
        files: list[str],
        *,
        commands: list[list[str]] | None = None,
    ) -> list[str]:
        result = self._run(
            ("git", "ls-files", "--others", "--exclude-standard", "--", *files)
        )
        if commands is not None:
            commands.extend(result.commands)
        if result.status == "failed":
            return []
        return [path for path in result.feedback.splitlines() if path]

    def _project_directory(self) -> Path:
        return current_workspace_directory() or self.project_directory

    def _is_protected_branch(self, branch: str) -> bool:
        return branch in self.protected_branches

    def _normalize_file(self, file: str) -> str | None:
        if not isinstance(file, str) or not file.strip():
            return None
        root = self._project_directory().resolve()
        path = Path(file)
        candidate = _resolve_path(path if path.is_absolute() else root / path)
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            return None
        if not relative.parts:
            return None
        return relative.as_posix()

    def _run(
        self,
        command: tuple[str, ...],
        *,
        allow_exit_1: bool = False,
    ) -> AgentResult:
        guardrail_error = self._validate_command(command)
        if guardrail_error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=guardrail_error,
                commands=[_audit_command(command)],
            )
        timeout = self._timeout_for(command)
        if timeout <= 0:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Repository deadline has elapsed.",
                commands=[_audit_command(command)],
            )
        try:
            completed = _run_subprocess(
                command,
                cwd=self._project_directory(),
                timeout=timeout,
                env=self._github_environment(command),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=redact_secrets(str(error)),
                commands=[_audit_command(command)],
            )

        raw_stdout = redact_secrets(completed.stdout or "")
        stdout = (
            raw_stdout
            if command == ("git", "status", "--short", "--untracked-files=all")
            else raw_stdout.strip()
        )
        stderr = redact_secrets((completed.stderr or "").strip())
        if completed.returncode == 0 and command in {
            ("git", "status", "--short", "--untracked-files=all"),
            ("git", "branch", "--show-current"),
            ("git", "rev-parse", "HEAD"),
        }:
            output = stdout
        else:
            output = "\n".join(part for part in (stdout, stderr) if part)
        expected_difference = allow_exit_1 and completed.returncode == 1
        if completed.returncode != 0 and not expected_difference:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=output or f"Command exited with status {completed.returncode}",
                feedback=output,
                commands=[_audit_command(command)],
            )
        return AgentResult(
            status="completed",
            assigned_model=self.model_name,
            feedback=output,
            commands=[_audit_command(command)],
        )

    def _timeout_for(self, command: tuple[str, ...]) -> float:
        """Cap quick read-only lookups so a stall cannot hold a node for an hour.

        Clamped again by whatever is left of the run's wall-clock budget, so a
        repository subprocess cannot outlive `max_runtime_seconds` the way an
        agent subprocess already cannot."""

        if any(command[: len(probe)] == probe for probe in PROBE_COMMANDS):
            timeout = float(min(self.probe_timeout_seconds, self.timeout_seconds))
        else:
            timeout = float(self.timeout_seconds)
        return _clamped_to_run_budget(timeout)

    def _quality_gate_command(self, *, staged: bool = False) -> tuple[str, ...]:
        command = (
            sys.executable,
            "scripts/quality_gates.py",
            "--diff-base",
            f"{self.remote}/{self.base_branch}",
        )
        return (*command, "--staged") if staged else command

    def _validate_command(self, command: tuple[str, ...]) -> str | None:
        if command == ("git", "status", "--short", "--untracked-files=all"):
            return None
        if command == ("git", "branch", "--show-current"):
            return None
        if command == ("git", "rev-parse", "HEAD"):
            return None
        if command == ("git", "fetch", "--quiet", self.remote, self.base_branch):
            return None
        if command == (
            "git",
            "rev-list",
            "--count",
            f"HEAD..{self.remote}/{self.base_branch}",
        ):
            return None
        if (
            len(command) >= 6
            and command[:5] == ("git", "diff", "--cached", "--no-ext-diff", "--")
            and self._safe_files(command[5:])
        ):
            return None
        if (
            len(command) >= 6
            and command[:5] == ("git", "diff", "HEAD", "--no-ext-diff", "--")
            and self._safe_files(command[5:])
        ):
            return None
        if (
            len(command) >= 6
            and command[:4] == ("git", "ls-files", "--others", "--exclude-standard")
            and command[4] == "--"
            and self._safe_files(command[5:])
        ):
            return None
        if (
            len(command) == 6
            and command[:4] == ("git", "diff", "--no-index", "--")
            and command[4] == "/dev/null"
            and self._safe_files((command[5],))
        ):
            return None
        if command == ("gh", "auth", "status"):
            return None
        if (
            len(command) in {4, 5}
            and command[:3]
            == (sys.executable, "scripts/quality_gates.py", "--diff-base")
            and self._safe_ref(command[3])
            and (len(command) == 4 or command[4] == "--staged")
        ):
            return None
        if command[:3] == ("git", "add", "--") and self._safe_files(command[3:]):
            return None
        if (
            len(command) >= 7
            and command[:4] == ("git", "commit", "--only", "-m")
            and command[4]
            and command[5] == "--"
            and self._safe_files(command[6:])
        ):
            return None
        if (
            len(command) == 5
            and command[:3] == ("git", "push", "-u")
            and command[3] == self.remote
            and self._safe_ref(command[4])
            and not self._is_protected_branch(command[4])
        ):
            return None
        if (
            len(command) == 11
            and command[:4] == ("gh", "pr", "list", "--head")
            and self._safe_ref(command[4])
            and not self._is_protected_branch(command[4])
            and command[5:7] == ("--state", "all")
            and command[7] == "--json"
            and command[8] in {"url", PR_JSON_FIELDS}
            and command[9] == "--limit"
            and command[10] in {"1", PR_LOOKUP_LIMIT}
        ):
            return None
        if (
            len(command) >= 11
            and command[:4] == ("gh", "pr", "create", "--base")
            and command[4] == self.base_branch
            and command[5] == "--head"
            and self._safe_ref(command[6])
            and not self._is_protected_branch(command[6])
            and command[7] == "--title"
            and self._safe_text(command[8])
            and command[9] == "--body"
            and self._safe_text(command[10])
            and self._safe_policy_arguments(command[11:], create=True)
        ):
            return None
        if (
            len(command) >= 4
            and command[:3] == ("gh", "pr", "reopen")
            and self.reopen_closed
            and self._safe_pr_target(command[3])
        ):
            return None
        if (
            len(command) >= 5
            and command[:3] == ("gh", "pr", "edit")
            and self._safe_pr_target(command[3])
            and self._safe_policy_arguments(command[4:], create=False)
        ):
            return None
        return "Refusing to run an unapproved Git or GitHub command."

    def _safe_files(self, files: tuple[str, ...]) -> bool:
        return bool(files) and all(
            self._normalize_file(file) is not None for file in files
        )

    @staticmethod
    def _safe_ref(value: str) -> bool:
        return bool(
            value
            and not value.startswith("-")
            and ".." not in value
            and "@{" not in value
            and re.fullmatch(r"[A-Za-z0-9._/-]+", value)
        )

    @staticmethod
    def _safe_text(value: str) -> bool:
        return isinstance(value, str) and "\x00" not in value

    def _safe_policy_arguments(
        self,
        arguments: tuple[str, ...],
        *,
        create: bool,
    ) -> bool:
        allowed = {
            "--label" if create else "--add-label",
            "--reviewer" if create else "--add-reviewer",
        }
        index = 0
        while index < len(arguments):
            flag = arguments[index]
            if flag not in allowed or index + 1 >= len(arguments):
                if not create and flag in {"--title", "--body"}:
                    if index + 1 >= len(arguments) or not self._safe_text(
                        arguments[index + 1]
                    ):
                        return False
                    index += 2
                    continue
                return False
            value = arguments[index + 1]
            policy = (
                self.label_allowlist
                if flag.endswith("label")
                else self.reviewer_allowlist
            ) or ()
            if not self._safe_policy_value(value) or value.casefold() not in {
                item.casefold() for item in policy
            }:
                return False
            index += 2
        return True

    @staticmethod
    def _safe_policy_value(value: str) -> bool:
        return bool(
            isinstance(value, str)
            and value
            and not value.startswith("-")
            and "\x00" not in value
            and "\r" not in value
            and "\n" not in value
        )

    @staticmethod
    def _safe_pr_target(value: str) -> bool:
        return bool(
            re.fullmatch(r"[0-9]+", value)
            or re.fullmatch(
                r"https://[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*/pull/[0-9]+",
                value,
            )
        )

    @staticmethod
    def _github_environment(command: tuple[str, ...]) -> dict[str, str]:
        keys = {"HOME", "LANG", "LC_ALL", "PATH"}
        if command and command[0] == "gh":
            keys.add("GH_HOST")
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in keys and key in GITHUB_ENVIRONMENT_KEYS
        }
        environment["GIT_TERMINAL_PROMPT"] = "0"
        if command and command[0] == "gh":
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if token:
                environment["GH_TOKEN"] = token
            environment["GH_PROMPT_DISABLED"] = "1"
        return environment


def _run_subprocess(
    command: tuple[str, ...],
    *,
    cwd: Path | None,
    env: dict[str, str],
    timeout: float,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command in its own process group so a timeout kills its whole
    process tree, not just the direct child - a wrapper like sandbox-exec or
    a shell can otherwise leave grandchildren running past the deadline."""

    with subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(input_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _agent_environment() -> dict[str, str]:
    """Give agent subprocesses only the environment keys they need to run."""

    return {
        key: value
        for key, value in os.environ.items()
        if key in AGENT_ALLOWED_ENVIRONMENT_KEYS
    }


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_allowed_executable(executable: str, allowed: frozenset[str]) -> bool:
    """Allow configured executables and versioned Python 3 interpreters."""

    return executable in allowed or (
        "python3" in allowed
        and _VERSIONED_PYTHON_EXECUTABLE.fullmatch(executable) is not None
    )


def _branch_values(values: object) -> tuple[str, ...]:
    """Normalize protected branch names and reject unsafe refs early."""

    if isinstance(values, str):
        values = (values,)
    if not isinstance(values, (list, tuple)):
        raise ValueError("protected_branches must be sequences of strings")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not GitHubAdapter._safe_ref(value.strip()):
            raise ValueError("protected_branches must contain safe branch names")
        value = value.strip()
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _policy_values(values: object) -> tuple[str, ...]:
    """Normalize and deduplicate configured reviewer or label names."""

    if isinstance(values, str):
        values = (values,)
    if not isinstance(values, (list, tuple)):
        raise ValueError("reviewers and labels must be sequences of strings")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("reviewers and labels must contain only strings")
        value = value.strip()
        if value and value.casefold() not in {item.casefold() for item in normalized}:
            normalized.append(value)
    return tuple(normalized)


def _validate_policy_values(kind: str, values: tuple[str, ...]) -> None:
    if any(not GitHubAdapter._safe_policy_value(value) for value in values):
        raise ValueError(f"{kind} contains an unsafe reviewer or label value")


def _pull_request_names(values: object, field: str) -> set[str]:
    """Extract case-insensitive label or reviewer names from gh JSON."""

    if not isinstance(values, list):
        return set()
    names: set[str] = set()
    for value in values:
        if isinstance(value, str):
            names.add(value.casefold())
            continue
        if not isinstance(value, dict):
            continue
        name = value.get(field) or value.get("login") or value.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip().casefold())
            continue
        for nested_key in ("requestedReviewer", "author"):
            nested = value.get(nested_key)
            if not isinstance(nested, dict):
                continue
            name = nested.get(field) or nested.get("login") or nested.get("name")
            if isinstance(name, str) and name.strip():
                names.add(name.strip().casefold())
                break
    return names


def _pull_request_number(url: str) -> str:
    """Extract the number from a GitHub pull-request URL."""

    return url.rstrip("/").rsplit("/", 1)[-1] if "/pull/" in url else ""


def _path_within_any(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(_resolve_path(root))
        except ValueError:
            continue
        return True
    return False


def _command_path_arguments(command: tuple[str, ...]) -> tuple[str, ...]:
    paths: list[str] = []
    if Path(command[0]).name == "bash" and len(command) > 1:
        if not command[1].startswith("-"):
            paths.append(command[1])
    for flag in ("--cd", "--project-dir", "--run-dir", "--output-schema"):
        if flag in command:
            index = command.index(flag) + 1
            if index < len(command):
                paths.append(command[index])
    return tuple(paths)


def redact_secrets(value: str) -> str:
    """Remove common credentials before command output enters workflow state."""

    redacted = value
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(
                lambda match: f"{match.group(1)}[REDACTED]", redacted
            )
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _audit_command(command: tuple[str, ...]) -> list[str]:
    """Return a redacted command suitable for the persisted run manifest."""

    return [redact_secrets(part) for part in command]


def _guarded_path_patterns(patterns_file: Path) -> list[re.Pattern[str]]:
    """Parse hooks/guard-dependency-files.sh's basename pattern file."""

    if not patterns_file.is_file():
        return []
    patterns = []
    for line in patterns_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line))
        except re.error:
            continue
    return patterns


def _matching_guarded_files(files: list[str]) -> list[str]:
    """Return files whose basename matches a guarded dependency/secret pattern."""

    patterns_file = Path(
        os.environ.get("SHANKS_GUARDED_PATTERNS") or GUARDED_PATHS_FILE
    )
    patterns = _guarded_path_patterns(patterns_file)
    if not patterns:
        return []
    matched = []
    for file in files:
        basename = Path(file).name
        if basename in _GUARDED_PATH_TEMPLATE_EXCEPTIONS:
            continue
        if any(pattern.search(basename) for pattern in patterns):
            matched.append(file)
    return matched


def _clamped_to_run_budget(timeout: float) -> float:
    """Trim a fixed subprocess timeout to the run's remaining wall-clock budget."""

    remaining = remaining_deadline_seconds()
    return timeout if remaining is None else min(timeout, remaining)


def _scan_for_secrets(project_directory: Path, files: list[str]) -> str | None:
    """Run hooks/secret-scan.sh's gitleaks invocation over dirty files at once.

    Returns "" when clean, a finding summary when secrets are flagged, and
    None when the scan itself could not run - a missing tool or subprocess
    error is not the same as a clean scan, so the caller fails closed on
    None, matching hooks/secret-scan.sh's fail-closed stance on missing jq/
    gitleaks."""

    if shutil.which("gitleaks") is None:
        return None
    scan_timeout = _clamped_to_run_budget(SECRET_SCAN_TIMEOUT_SECONDS)
    if scan_timeout <= 0:
        return None
    with tempfile.TemporaryDirectory(prefix="shanks-policy-gate-") as scan_dir:
        scan_root = Path(scan_dir)
        found_any = False
        for relative in files:
            source = project_directory / relative
            if not source.is_file():
                continue
            destination = scan_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            found_any = True
        if not found_any:
            return ""
        try:
            completed = _run_subprocess(
                (
                    "gitleaks",
                    "detect",
                    "--source",
                    str(scan_root),
                    "--no-git",
                    "--no-banner",
                    "-f",
                    "json",
                    "-r",
                    "-",
                ),
                cwd=project_directory,
                env=_agent_environment(),
                timeout=scan_timeout,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode == 0:
            return ""
        try:
            findings = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError:
            return "gitleaks flagged a potential secret"
        summary = ", ".join(
            f"{item.get('RuleID', 'secret')} in {Path(item.get('File', '')).name}"
            for item in findings
            if isinstance(item, dict)
        )
        return summary or "gitleaks flagged a potential secret"


def _attach_commands(
    result: AgentResult,
    commands: list[list[str]],
) -> AgentResult:
    """Keep the full command trail when a multi-command operation fails."""

    result.commands = list(commands)
    return result


class CodexAdapter(SubprocessAgentAdapter):
    """Adapter for direct Codex CLI execution."""

    def __init__(
        self,
        project_directory: Path,
        *,
        read_only: bool = True,
    ) -> None:
        super().__init__(
            command=(
                "codex",
                "exec",
                "--sandbox",
                "read-only" if read_only else "workspace-write",
                "--cd",
                str(project_directory),
            ),
            model_name="codex",
            working_directory=project_directory,
            allowed_directories=(project_directory,),
        )


class ClaudeAdapter(SubprocessAgentAdapter):
    """Adapter for direct Claude Code CLI execution."""

    def __init__(
        self,
        project_directory: Path,
        *,
        read_only: bool = True,
    ) -> None:
        claude_command = (
            "claude",
            "--print",
            "--permission-mode",
            "plan" if read_only else "acceptEdits",
            "--tools",
            CLAUDE_READ_ONLY_TOOLS if read_only else "Read,Write,Edit,Bash,Grep,Glob",
            "--no-session-persistence",
        )
        command = (
            claude_command
            if read_only
            else (
                "bash",
                str(SANDBOX_CLAUDE_SCRIPT_PATH),
                str(project_directory),
                *claude_command,
            )
        )
        super().__init__(
            command=command,
            model_name="claude",
            working_directory=project_directory,
            allowed_directories=(project_directory, SANDBOX_CLAUDE_SCRIPT_PATH.parent),
        )


class StructuredCriticAdapter(SubprocessAgentAdapter):
    """Normalize a read-only CLI critic into the common agent result shape."""

    __slots__ = ()

    def run(self, request: AgentRequest) -> AgentResult:
        raw_result = super().run(_critic_request(request))
        if raw_result.status == "failed":
            return raw_result
        return _critic_result(self, raw_result)


class GPT56LunaCriticAdapter(StructuredCriticAdapter):
    """Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent."""

    __slots__ = ("reasoning_effort",)

    def __init__(
        self,
        project_directory: Path,
        *,
        model_name: str = GPT56_LUNA_MODEL,
        reasoning_effort: str = GPT56_LUNA_REASONING_EFFORT,
        timeout_seconds: int = 3600,
    ) -> None:
        super().__init__(
            command=(
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--cd",
                str(project_directory),
                "--model",
                model_name,
                "--config",
                f'model_reasoning_effort="{reasoning_effort}"',
                "--output-schema",
                str(CRITIC_OUTPUT_SCHEMA_PATH),
            ),
            model_name=model_name,
            working_directory=project_directory,
            timeout_seconds=timeout_seconds,
            allowed_directories=(project_directory, CRITIC_OUTPUT_SCHEMA_PATH.parent),
        )
        self.reasoning_effort = reasoning_effort


class ClaudeOpus48CriticAdapter(StructuredCriticAdapter):
    """Run the critic_auditor as a read-only Claude Opus 4.8 subagent."""

    __slots__ = ("effort",)

    def __init__(
        self,
        project_directory: Path,
        *,
        model_name: str = CLAUDE_OPUS_48_MODEL,
        effort: str = CLAUDE_OPUS_48_EFFORT,
        timeout_seconds: int = 3600,
    ) -> None:
        schema = _load_json_schema(CRITIC_OUTPUT_SCHEMA_PATH)
        super().__init__(
            command=(
                "claude",
                "--print",
                "--model",
                model_name,
                "--effort",
                effort,
                "--permission-mode",
                "plan",
                "--tools",
                CLAUDE_READ_ONLY_TOOLS,
                "--json-schema",
                schema,
                "--no-session-persistence",
            ),
            model_name=model_name,
            working_directory=project_directory,
            timeout_seconds=timeout_seconds,
            allowed_directories=(project_directory,),
        )
        self.effort = effort


class CheapCriticAdapter(StubAgentAdapter):
    """Deterministic low-cost critic used by the default graph."""

    def __init__(self, model_name: str = "cheap-critic-model") -> None:
        super().__init__(role="critic", model_name=model_name)


def _parse_json_object(output: str) -> dict[str, object]:
    """Parse a JSON object even when the CLI adds non-JSON log lines."""

    decoder = json.JSONDecoder()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        for index, character in enumerate(output):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(output[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise

    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload


def _parse_uncertainties(output: str) -> list[str]:
    """Extract the builder's concise uncertainty bullets from Ralph output."""

    lines = output.splitlines()
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line.startswith(UNCERTAINTIES_MARKER):
            continue

        inline = line[len(UNCERTAINTIES_MARKER) :].strip()
        if inline:
            return [] if inline.lower() == "none" else [inline]

        entries: list[str] = []
        for raw_entry in lines[index + 1 :]:
            entry = raw_entry.strip()
            if not entry:
                continue
            if entry.startswith("RALPH_") or entry.startswith("<promise>"):
                break
            if entry.startswith(("- ", "* ")):
                entry = entry[2:].strip()
            else:
                continue
            if entry and entry.lower() != "none":
                entries.append(entry)
        return list(dict.fromkeys(entries))

    return []


def _critic_request(request: AgentRequest) -> AgentRequest:
    """Add the shared read-only audit instructions to a critic request."""

    return AgentRequest(
        task=request.task,
        item_id=request.item_id,
        item_title=request.item_title,
        item_description=request.item_description,
        acceptance_criteria=request.acceptance_criteria,
        validation_command=request.validation_command,
        prd_items=request.prd_items,
        instructions="\n".join(
            part
            for part in (
                (
                    "You are the critic_auditor subagent. Inspect the current "
                    "repository and relevant tests in read-only mode. Do not "
                    "edit files. Approve only when the requested item is "
                    "implemented correctly and has no obvious regressions. "
                    "Return only the structured audit object required by the "
                    "output schema."
                ),
                request.instructions,
            )
            if part
        ),
        context=request.context,
        working_directory=request.working_directory,
        timeout_seconds=request.timeout_seconds,
    )


def _debugger_request(request: AgentRequest) -> AgentRequest:
    """Give the debugger failure evidence and a read-only analysis mandate."""

    return AgentRequest(
        task=request.task,
        item_id=request.item_id,
        item_title=request.item_title,
        item_description=request.item_description,
        acceptance_criteria=request.acceptance_criteria,
        validation_command=request.validation_command,
        prd_items=request.prd_items,
        instructions="\n".join(
            part
            for part in (
                (
                    "You are the debugger subagent. Inspect the current "
                    "repository, the PRD requirement, and relevant tests in "
                    "read-only mode. Do not edit files. Analyze the supplied "
                    "validation failure, trace it to the most likely root "
                    "cause, and give precise repair instructions for Ralph. "
                    "Return only the structured debugger object required by "
                    "the output schema."
                ),
                request.instructions,
            )
            if part
        ),
        context=request.context,
        working_directory=request.working_directory,
        timeout_seconds=request.timeout_seconds,
    )


def _critic_result(
    adapter: SubprocessAgentAdapter,
    raw_result: AgentResult,
) -> AgentResult:
    """Translate a structured CLI response into an AgentResult."""

    try:
        payload = _parse_json_object(raw_result.feedback)
        approved = payload["approved"]
        feedback = payload["feedback"]
        if not isinstance(approved, bool) or not isinstance(feedback, str):
            raise ValueError("approved must be a boolean and feedback a string")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return AgentResult(
            status="failed",
            assigned_model=adapter.model_name,
            error=f"Critic returned invalid structured output: {error}",
            feedback=raw_result.feedback,
            input_tokens=raw_result.input_tokens,
            output_tokens=raw_result.output_tokens,
            cost_usd=raw_result.cost_usd,
            prompt=raw_result.prompt,
            commands=raw_result.commands,
        )

    return AgentResult(
        status="critic_audited",
        assigned_model=adapter.model_name,
        approved=approved,
        feedback=feedback,
        input_tokens=raw_result.input_tokens,
        output_tokens=raw_result.output_tokens,
        cost_usd=raw_result.cost_usd,
        prompt=raw_result.prompt,
        commands=raw_result.commands,
    )


def _debugger_result(
    adapter: SubprocessAgentAdapter,
    raw_result: AgentResult,
) -> AgentResult:
    """Translate structured debugger output into the shared result shape."""

    try:
        payload = _parse_json_object(raw_result.feedback)
        root_cause = payload["root_cause"]
        builder_instructions = payload["builder_instructions"]
        feedback = payload.get("feedback", "")
        if (
            not isinstance(root_cause, str)
            or not root_cause.strip()
            or not isinstance(builder_instructions, str)
            or not builder_instructions.strip()
            or not isinstance(feedback, str)
        ):
            raise ValueError(
                "root_cause and builder_instructions must be non-empty strings"
            )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return AgentResult(
            status="failed",
            assigned_model=adapter.model_name,
            error=f"Debugger returned invalid structured output: {error}",
            feedback=raw_result.feedback,
            input_tokens=raw_result.input_tokens,
            output_tokens=raw_result.output_tokens,
            cost_usd=raw_result.cost_usd,
            prompt=raw_result.prompt,
            commands=raw_result.commands,
        )

    return AgentResult(
        status="debugged",
        assigned_model=adapter.model_name,
        root_cause=root_cause,
        builder_instructions=builder_instructions,
        feedback=feedback,
        input_tokens=raw_result.input_tokens,
        output_tokens=raw_result.output_tokens,
        cost_usd=raw_result.cost_usd,
        prompt=raw_result.prompt,
        commands=raw_result.commands,
    )


def _format_request(request: AgentRequest) -> str:
    """Create a stable prompt envelope for CLI-backed adapters."""

    return "\n".join(
        [
            f"Task: {request.task}",
            f"PRD item: {request.item_id} - {request.item_title}",
            f"PRD requirement: {request.item_description}",
            f"Acceptance criteria: {json.dumps(request.acceptance_criteria)}",
            "Validation command: "
            + (request.validation_command or "<full test suite fallback>"),
            f"PRD list: {json.dumps(request.prd_items, sort_keys=True)}",
            f"Instructions: {request.instructions}",
            f"Context: {request.context}",
        ]
    )


def _estimate_tokens(value: str) -> int:
    """Use a conservative four-characters-per-token estimate for CLI text."""

    return (len(value) + 3) // 4


def _preflight_failure(
    message: str,
    commands: list[list[str]] | None = None,
) -> AgentResult:
    return AgentResult(
        status="preflight_failed",
        assigned_model="github",
        error=message or "Preflight check failed.",
        commands=commands or [],
    )


__all__ = [
    "AgentAdapter",
    "CheapCriticAdapter",
    "CLAUDE_OPUS_48_EFFORT",
    "CLAUDE_OPUS_48_MODEL",
    "ClaudeAdapter",
    "CodexAdapter",
    "ClaudeOpus48CriticAdapter",
    "DebuggerAdapter",
    "DEBUGGER_OUTPUT_SCHEMA_PATH",
    "GPT56LunaCriticAdapter",
    "GPT56_LUNA_MODEL",
    "GPT56_LUNA_REASONING_EFFORT",
    "GitHubAdapter",
    "ITEM_BUILT_MARKER",
    "LocalTestAdapter",
    "RalphAdapter",
    "redact_secrets",
    "StubAgentAdapter",
    "StructuredCriticAdapter",
    "SubprocessAgentAdapter",
]
