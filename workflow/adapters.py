"""Agent adapter implementations for graph nodes and external runners."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .contracts import AgentAdapter, AgentRequest, AgentResult


GPT56_LUNA_MODEL = "gpt-5.6-luna"
GPT56_LUNA_REASONING_EFFORT = "max"
CLAUDE_OPUS_48_MODEL = "claude-opus-4-8"
CLAUDE_OPUS_48_EFFORT = "medium"
CRITIC_OUTPUT_SCHEMA_PATH = Path(__file__).with_name("critic_output.schema.json")
DEBUGGER_OUTPUT_SCHEMA_PATH = Path(__file__).with_name("debugger_output.schema.json")
ITEM_BUILT_MARKER = "<promise>ITEM_BUILT</promise>"
UNCERTAINTIES_MARKER = "RALPH_UNCERTAINTIES:"
ALLOWED_AGENT_EXECUTABLES = frozenset(
    {"bash", "claude", "codex", "python", "python3"}
)
GITHUB_ENVIRONMENT_KEYS = frozenset(
    {
        "GH_HOST",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
    }
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
        cwd = request.working_directory or self.working_directory
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

        timeout = self.timeout_seconds
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
            completed = subprocess.run(
                command,
                cwd=cwd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
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
        return self.command

    def _validate_execution(
        self,
        command: tuple[str, ...],
        cwd: Path | None,
    ) -> str | None:
        if not command:
            return "Refusing to run an empty command."
        executable = Path(command[0]).name
        if executable not in ALLOWED_AGENT_EXECUTABLES:
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
                return "Refusing to use a command path outside the configured directories."
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
        prd_file = Path(self.command[1]).parent / "prd.json"
        if not prd_file.parent.is_dir():
            return

        payload: dict[str, object] = {}
        if prd_file.exists():
            payload = json.loads(prd_file.read_text(encoding="utf-8"))
        existing_stories = {
            story.get("id"): story
            for story in payload.get("userStories", [])
            if isinstance(story, dict) and story.get("id")
        }
        stories = []
        for item in request.prd_items:
            story = dict(existing_stories.get(item.get("id"), {}))
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
        return (
            *self.command,
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
        return parsed or self.command


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
            schema = json.dumps(
                json.loads(DEBUGGER_OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
            )
            command = (
                "claude",
                "--print",
                "--permission-mode",
                "plan",
                "--tools",
                "Read",
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
    """Commit validated items, then push the branch and open its PR."""

    project_directory: Path
    remote: str = "origin"
    base_branch: str = "main"
    test_command: str = ".venv/bin/python -m unittest discover -s tests"
    timeout_seconds: int = 3600
    initial_dirty_files: tuple[str, ...] | None = None

    model_name = "github"

    def __post_init__(self) -> None:
        self.project_directory = self.project_directory.resolve()
        if self.initial_dirty_files is None:
            self.initial_dirty_files = tuple(self._status_files())

    def preflight(self) -> AgentResult:
        """Check tools, branch state, GitHub auth, and the test environment."""

        commands: list[list[str]] = []
        required_tools = ("git", "gh", "bash")
        missing = [tool for tool in required_tools if shutil.which(tool) is None]
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
                "GitHub CLI authentication failed: "
                + (auth.error or auth.feedback),
                commands,
            )

        tests = LocalTestAdapter(self.project_directory).run(
            AgentRequest(task="Run the preflight test suite.")
        )
        commands.extend(tests.commands)
        if tests.status != "validated":
            return _preflight_failure(
                "Preflight test suite failed: "
                + (tests.error or tests.feedback),
                commands,
            )
        return AgentResult(
            status="preflight_passed",
            assigned_model=self.model_name,
            feedback=(
                f"branch={branch_name}; working tree clean; GitHub auth ready; "
                "test suite passed"
            ),
            commands=commands,
            test_output=tests.feedback,
        )

    def commit_item(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
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

        message = f"feat: {item_id} - {item_title}".strip()
        committed = self._run(
            ("git", "commit", "--only", "-m", message, "--", *files)
        )
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

    def publish_pr(self, task: str) -> AgentResult:
        commands: list[list[str]] = []
        branch_result = self._run(("git", "branch", "--show-current"))
        commands.extend(branch_result.commands)
        if branch_result.status == "failed":
            return _attach_commands(branch_result, commands)
        branch = branch_result.feedback.strip()
        if not branch or branch == self.base_branch:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error="Refusing to push or open a PR from the base branch.",
                commands=commands,
            )

        pushed = self._run(("git", "push", "-u", self.remote, branch))
        commands.extend(pushed.commands)
        if pushed.status == "failed":
            return _attach_commands(pushed, commands)

        existing = self._run(
            (
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "url",
                "--limit",
                "1",
            )
        )
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
            first_pr = existing_prs[0]
            pr_url = (
                first_pr.get("url", "")
                if isinstance(first_pr, dict)
                else ""
            )
            if not isinstance(pr_url, str) or not pr_url:
                return AgentResult(
                    status="failed",
                    assigned_model=self.model_name,
                    error="Existing PR lookup returned no URL.",
                    feedback=existing.feedback,
                    commands=commands,
                )
            return AgentResult(
                status="pr_created",
                assigned_model=self.model_name,
                feedback=existing.feedback,
                pr_url=pr_url,
                commands=commands,
            )

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
                f"- `{self.test_command}`",
            )
        )
        created = self._run(
            (
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
            )
        )
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
        )

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

    def _normalize_file(self, file: str) -> str | None:
        if not isinstance(file, str) or not file.strip():
            return None
        root = self.project_directory.resolve()
        path = Path(file)
        candidate = _resolve_path(path if path.is_absolute() else root / path)
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            return None
        if not relative.parts:
            return None
        return relative.as_posix()

    def _run(self, command: tuple[str, ...]) -> AgentResult:
        guardrail_error = self._validate_command(command)
        if guardrail_error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=guardrail_error,
                commands=[_audit_command(command)],
            )
        try:
            completed = subprocess.run(
                command,
                cwd=self.project_directory,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env=self._github_environment(command),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=redact_secrets(str(error)),
                commands=[_audit_command(command)],
            )

        stdout = redact_secrets((completed.stdout or "").strip())
        stderr = redact_secrets((completed.stderr or "").strip())
        if completed.returncode == 0 and command in {
            ("git", "status", "--short", "--untracked-files=all"),
            ("git", "branch", "--show-current"),
            ("git", "rev-parse", "HEAD"),
        }:
            output = stdout
        else:
            output = "\n".join(part for part in (stdout, stderr) if part)
        if completed.returncode != 0:
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

    def _validate_command(self, command: tuple[str, ...]) -> str | None:
        if command == ("git", "status", "--short", "--untracked-files=all"):
            return None
        if command == ("git", "branch", "--show-current"):
            return None
        if command == ("git", "rev-parse", "HEAD"):
            return None
        if (
            len(command) >= 6
            and command[:5] == ("git", "diff", "--cached", "--no-ext-diff", "--")
            and self._safe_files(command[5:])
        ):
            return None
        if command == ("gh", "auth", "status"):
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
            and self._safe_ref(command[3])
            and self._safe_ref(command[4])
        ):
            return None
        if (
            len(command) == 11
            and command[:4] == ("gh", "pr", "list", "--head")
            and self._safe_ref(command[4])
            and command[5:] == (
                "--state",
                "all",
                "--json",
                "url",
                "--limit",
                "1",
            )
        ):
            return None
        if (
            len(command) == 11
            and command[:4] == ("gh", "pr", "create", "--base")
            and self._safe_ref(command[4])
            and command[5] == "--head"
            and self._safe_ref(command[6])
            and command[7] == "--title"
            and isinstance(command[8], str)
            and command[9] == "--body"
            and isinstance(command[10], str)
        ):
            return None
        return "Refusing to run an unapproved Git or GitHub command."

    def _safe_files(self, files: tuple[str, ...]) -> bool:
        return bool(files) and all(self._normalize_file(file) is not None for file in files)

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
    def _github_environment(command: tuple[str, ...]) -> dict[str, str]:
        keys = {"HOME", "LANG", "LC_ALL", "PATH"}
        if command and command[0] == "gh":
            keys.update({"GH_HOST", "GH_TOKEN", "GITHUB_TOKEN"})
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in keys and key in GITHUB_ENVIRONMENT_KEYS
        }
        environment["GIT_TERMINAL_PROMPT"] = "0"
        return environment


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


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
    for flag in ("--cd", "--project-dir", "--output-schema"):
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
            redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _audit_command(command: tuple[str, ...]) -> list[str]:
    """Return a redacted command suitable for the persisted run manifest."""

    return [redact_secrets(part) for part in command]


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
        command = (
            (
                "claude",
                "--print",
                "--permission-mode",
                "plan",
                "--tools",
                "Read",
                "--no-session-persistence",
            )
            if read_only
            else ("claude", "--dangerously-skip-permissions", "--print")
        )
        super().__init__(
            command=command,
            model_name="claude",
            working_directory=project_directory,
            allowed_directories=(project_directory,),
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
        schema = json.dumps(
            json.loads(CRITIC_OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        )
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
                "Read",
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
