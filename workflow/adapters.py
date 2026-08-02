"""Agent adapter implementations.

The graph defaults to deterministic stubs. CLI adapters are available for
explicit injection and do not run unless the caller chooses them.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contracts import AgentAdapter, AgentRequest, AgentResult


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
        max_iterations: int = 1,
    ) -> None:
        script = project_directory / "scripts" / "ralph" / "ralph.sh"
        super().__init__(
            command=("bash", str(script), "--tool", tool, str(max_iterations)),
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


class CheapCriticAdapter(StubAgentAdapter):
    """Low-cost critic default; replace with a real model adapter later."""

    def __init__(self, model_name: str = "cheap-critic-model") -> None:
        super().__init__(role="critic", model_name=model_name)


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
    "ClaudeAdapter",
    "CodexAdapter",
    "RalphAdapter",
    "StubAgentAdapter",
    "SubprocessAgentAdapter",
]
