"""Common interfaces shared by agent adapters and graph nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .state import PRDItem, WorkflowState


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """Structured input passed to any agent backend."""

    task: str
    item_id: str = ""
    item_title: str = ""
    item_description: str = ""
    prd_items: list[PRDItem] = field(default_factory=list)
    instructions: str = ""
    context: str = ""
    working_directory: Path | None = None
    timeout_seconds: float | None = None


@dataclass(slots=True)
class AgentResult:
    """Provider-neutral output returned by an agent backend."""

    status: str
    assigned_model: str
    files_touched: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    error: str | None = None
    feedback: str = ""
    approved: bool | None = None
    validation_passed: bool | None = None
    validation_errors: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    builder_instructions: str = ""
    root_cause: str = ""
    item_built: bool | None = None
    commit_sha: str = ""
    pr_url: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class AgentAdapter(Protocol):
    """Interface implemented by Ralph, model CLIs, and test doubles."""

    model_name: str

    def run(self, request: AgentRequest) -> AgentResult:
        """Run the backend for one workflow node invocation."""

        ...


class RepositoryAdapter(Protocol):
    """Interface for local commits and the final GitHub handoff."""

    def commit_item(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
        """Commit one validated item's intended files."""

        ...

    def publish_pr(self, task: str) -> AgentResult:
        """Push the branch and create its pull request."""

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
    if result.item_built is not None:
        update["item_built"] = result.item_built
    if result.commit_sha:
        update["commit_sha"] = result.commit_sha
    if result.pr_url:
        update["pr_url"] = result.pr_url
    if result.input_tokens:
        update["last_input_tokens"] = result.input_tokens
    if result.output_tokens:
        update["last_output_tokens"] = result.output_tokens
    if result.cost_usd:
        update["last_cost_usd"] = result.cost_usd

    return update
