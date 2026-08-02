"""Common interfaces shared by agent adapters and graph nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .state import WorkflowState


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """Structured input passed to any agent backend."""

    task: str
    item_id: str = ""
    item_title: str = ""
    instructions: str = ""
    context: str = ""
    working_directory: Path | None = None


@dataclass(slots=True)
class AgentResult:
    """Provider-neutral output returned by an agent backend."""

    status: str
    assigned_model: str
    files_touched: list[str] = field(default_factory=list)
    error: str | None = None
    feedback: str = ""
    approved: bool | None = None
    validation_passed: bool | None = None
    validation_errors: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    builder_instructions: str = ""
    root_cause: str = ""


class AgentAdapter(Protocol):
    """Interface implemented by Ralph, model CLIs, and test doubles."""

    model_name: str

    def run(self, request: AgentRequest) -> AgentResult:
        """Run the backend for one workflow node invocation."""

        ...


NodeFunction = Callable[[WorkflowState], WorkflowState]


def state_update_from_result(result: AgentResult) -> WorkflowState:
    """Translate common agent output into shared workflow state fields."""

    update: WorkflowState = {
        "status": result.status,
        "assigned_model": result.assigned_model,
        "last_error": result.error or "",
    }

    if result.files_touched:
        update["files_touched"] = list(result.files_touched)
    if result.feedback:
        update["critic_feedback"] = result.feedback
    if result.validation_errors:
        update["validation_errors"] = list(result.validation_errors)
    if result.plan:
        update["plan"] = list(result.plan)
    if result.builder_instructions:
        update["builder_instructions"] = result.builder_instructions
    if result.root_cause:
        update["root_cause"] = result.root_cause

    return update
