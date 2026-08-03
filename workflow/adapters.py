"""Agent adapter implementations.

The graph defaults to deterministic stubs. CLI adapters are available for
explicit injection and do not run unless the caller chooses them.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contracts import AgentAdapter, AgentRequest, AgentResult


GPT56_LUNA_MODEL = "gpt-5.6-luna"
GPT56_LUNA_REASONING_EFFORT = "max"
CLAUDE_OPUS_48_MODEL = "claude-opus-4-8"
CLAUDE_OPUS_48_EFFORT = "medium"
CRITIC_OUTPUT_SCHEMA_PATH = Path(__file__).with_name("critic_output.schema.json")


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

    def run(self, request: AgentRequest) -> AgentResult:
        prompt = _format_request(request)
        cwd = request.working_directory or self.working_directory

        try:
            completed = subprocess.run(
                self.command,
                cwd=cwd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=str(error),
            )

        output = "\n".join(
            part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
        )
        if completed.returncode != 0:
            return AgentResult(
                status="failed",
                assigned_model=self.model_name,
                error=output or f"CLI exited with status {completed.returncode}",
                feedback=output,
            )

        return AgentResult(
            status="completed",
            assigned_model=self.model_name,
            feedback=output,
        )


class RalphAdapter(SubprocessAgentAdapter):
    """Adapter for the project-local Ralph runner."""

    def __init__(
        self,
        project_directory: Path,
        *,
        tool: str = "codex",
        skill_name: str = "ponytail",
        max_iterations: int = 1,
    ) -> None:
        script = project_directory / "scripts" / "ralph" / "ralph.sh"
        super().__init__(
            command=(
                "bash",
                str(script),
                "--tool",
                tool,
                "--skill",
                skill_name,
                str(max_iterations),
            ),
            model_name=f"ralph:{tool}",
            working_directory=project_directory,
        )


class CodexAdapter(SubprocessAgentAdapter):
    """Adapter for direct Codex CLI execution."""

    def __init__(self, project_directory: Path) -> None:
        super().__init__(
            command=(
                "codex",
                "exec",
                "--sandbox",
                "workspace-write",
                "--cd",
                str(project_directory),
            ),
            model_name="codex",
            working_directory=project_directory,
        )


class ClaudeAdapter(SubprocessAgentAdapter):
    """Adapter for direct Claude Code CLI execution."""

    def __init__(self, project_directory: Path) -> None:
        super().__init__(
            command=("claude", "--dangerously-skip-permissions", "--print"),
            model_name="claude",
            working_directory=project_directory,
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


def _critic_request(request: AgentRequest) -> AgentRequest:
    """Add the shared read-only audit instructions to a critic request."""

    return AgentRequest(
        task=request.task,
        item_id=request.item_id,
        item_title=request.item_title,
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
        )

    return AgentResult(
        status="critic_audited",
        assigned_model=adapter.model_name,
        approved=approved,
        feedback=feedback,
    )


def _format_request(request: AgentRequest) -> str:
    """Create a stable prompt envelope for CLI-backed adapters."""

    return "\n".join(
        [
            f"Task: {request.task}",
            f"PRD item: {request.item_id} - {request.item_title}",
            f"Instructions: {request.instructions}",
            f"Context: {request.context}",
        ]
    )


__all__ = [
    "AgentAdapter",
    "CheapCriticAdapter",
    "CLAUDE_OPUS_48_EFFORT",
    "CLAUDE_OPUS_48_MODEL",
    "ClaudeAdapter",
    "CodexAdapter",
    "ClaudeOpus48CriticAdapter",
    "GPT56LunaCriticAdapter",
    "GPT56_LUNA_MODEL",
    "GPT56_LUNA_REASONING_EFFORT",
    "RalphAdapter",
    "StubAgentAdapter",
    "StructuredCriticAdapter",
    "SubprocessAgentAdapter",
]
