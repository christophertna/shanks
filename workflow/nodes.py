"""Standardized LangGraph node implementations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langgraph.types import interrupt

from .adapters import (
    ClaudeAdapter,
    ClaudeOpus48CriticAdapter,
    CodexAdapter,
    DebuggerAdapter,
    GPT56LunaCriticAdapter,
    GitHubAdapter,
    LocalTestAdapter,
    RalphAdapter,
)
from .contracts import (
    AgentAdapter,
    AgentRequest,
    AgentResult,
    NodeFunction,
    RepositoryAdapter,
    state_update_from_result,
)
from .state import PRDItem, WorkflowState


@dataclass(frozen=True, slots=True)
class NodeDependencies:
    """Backends injected into the standardized graph nodes."""

    planner: AgentAdapter
    builder: AgentAdapter
    critic: AgentAdapter
    validator: AgentAdapter
    debugger: AgentAdapter
    repository: RepositoryAdapter | None = None


LEARN_PROMPT = """
Use /grill-with-docs in learn mode. Read the target codebase and explain its
architecture, important workflows, conventions, and the safest places to make
changes. Do not edit files. Return the resulting codebase orientation for the
user, then stop.
""".strip()
IMPLEMENT_PROMPT = """
Use /grill-with-docs before implementation. Sharpen the requested feature
against the existing codebase, record useful terminology and decisions, then
produce an actionable implementation plan for the builder.
""".strip()


def default_dependencies(
    *,
    critic: AgentAdapter | None = None,
    project_directory: Path | None = None,
    tool: Literal["claude", "codex"] = "codex",
) -> NodeDependencies:
    """Return a complete Claude- or Codex-backed workflow configuration."""

    if tool not in {"claude", "codex"}:
        raise ValueError("tool must be 'claude' or 'codex'")
    project_directory = project_directory or Path.cwd()
    if tool == "claude":
        planner = ClaudeAdapter(project_directory)
        default_critic = ClaudeOpus48CriticAdapter(project_directory)
    else:
        planner = CodexAdapter(project_directory)
        default_critic = GPT56LunaCriticAdapter(project_directory)
    return NodeDependencies(
        planner=planner,
        builder=RalphAdapter(project_directory, tool=tool),
        critic=critic or default_critic,
        validator=LocalTestAdapter(project_directory),
        debugger=DebuggerAdapter(project_directory, tool=tool),
        repository=GitHubAdapter(project_directory),
    )


def gpt_5_6_luna_dependencies(project_directory: Path) -> NodeDependencies:
    """Use the read-only GPT-5.6 Luna subagent for critic_auditor."""

    return default_dependencies(
        critic=GPT56LunaCriticAdapter(project_directory),
        project_directory=project_directory,
        tool="codex",
    )


def claude_opus_4_8_dependencies(project_directory: Path) -> NodeDependencies:
    """Use the read-only Claude Opus 4.8 subagent for critic_auditor."""

    return default_dependencies(
        critic=ClaudeOpus48CriticAdapter(project_directory),
        project_directory=project_directory,
        tool="claude",
    )


def select_next_item(state: WorkflowState) -> tuple[int, PRDItem] | None:
    """Select the first item that is not both built and validated."""

    items = state.get("prd_items", [])
    start_index = state.get("current_item_index", 0)
    for index in range(start_index, len(items)):
        item = items[index]
        if not _item_complete(item):
            return index, item
    return None


def _item_complete(item: PRDItem) -> bool:
    """Treat legacy passes-only items as complete while honoring validation."""

    if not item.get("passes", False):
        return False
    return item.get("validation", True)


def create_nodes(
    dependencies: NodeDependencies | None = None,
) -> dict[str, NodeFunction]:
    """Create state-only node callables with injected agent backends."""

    deps = dependencies or default_dependencies()

    return {
        "intake": intake,
        "learning": lambda state: learning(state, deps),
        "planning": lambda state: planning(state, deps),
        "building": lambda state: building(state, deps),
        "critic_auditor": lambda state: critic_auditor(state, deps),
        "validation": lambda state: validation(state, deps),
        "commit_item": lambda state: commit_item(state, deps),
        "debugger": lambda state: debugger(state, deps),
        "item_router": item_router,
        "github_node": lambda state: github_node(state, deps),
        "attempt_limit": attempt_limit,
    }


def intake(state: WorkflowState) -> WorkflowState:
    """Ask for the top-level workflow mode and route the run accordingly."""

    mode = state.get("workflow_mode")
    if mode in {"learn", "implement"}:
        return {}

    prompt: dict[str, object] = {
        "type": "intake",
        "question": "What would you like to do?",
        "options": [
            {"value": "learn", "label": "Learn the codebase"},
            {"value": "implement", "label": "Implement something"},
        ],
    }
    while True:
        answer = interrupt(prompt)
        if isinstance(answer, dict):
            answer = answer.get("choice", answer.get("mode"))
        if answer in ("learn", "implement"):
            update: WorkflowState = {
                "workflow_mode": answer,
                "status": f"intake_{answer}",
            }
            if answer == "implement" and not state.get("prd_items"):
                task = state.get("task", "").strip() or "Implement the requested feature"
                update["prd_items"] = [
                    {
                        "id": "feature-1",
                        "title": task,
                        "description": task,
                        "passes": False,
                        "validation": False,
                    }
                ]
            return update
        prompt = {
            **prompt,
            "error": "Choose either learn or implement.",
        }


def learning(state: WorkflowState, dependencies: NodeDependencies) -> WorkflowState:
    """Run the documentation-oriented agent, then return to intake."""

    item = _current_item(state)
    item_id = item.get("id", "codebase")
    request = _request_for(
        state,
        item,
        item_id,
        instructions=LEARN_PROMPT,
    )
    result = dependencies.planner.run(request)
    update = state_update_from_result(result)
    update.update(
        {
            "workflow_mode": None,
            "learning_notes": result.feedback,
            "status": "learned" if result.status != "failed" else "learning_failed",
        }
    )
    return update


def planning(state: WorkflowState, dependencies: NodeDependencies) -> WorkflowState:
    """Plan the current incomplete item without losing retry context."""

    selected = select_next_item(state)
    if selected is None:
        return {"status": "complete"}

    item_index, item = selected
    item_id = item.get("id", f"item-{item_index + 1}")
    previous_item_id = state.get("current_item_id")
    item = dict(item)
    prd_items_update: list[PRDItem] | None = None
    debugger_details = _debugger_details(state, item_id, previous_item_id)
    if debugger_details:
        description = item.get("description", "").strip()
        if debugger_details not in description:
            item["description"] = "\n\n".join(
                part for part in (description, debugger_details) if part
            )
            prd_items_update = [
                dict(existing_item) for existing_item in state.get("prd_items", [])
            ]
            prd_items_update[item_index] = item
    learned_context = state.get("learning_notes", "")
    instructions = "\n\n".join(
        part
        for part in (
            IMPLEMENT_PROMPT,
            (
                "Existing codebase orientation from the previous learn pass:\n"
                + learned_context
                if learned_context
                else ""
            ),
            state.get("builder_instructions", ""),
        )
        if part
    )
    request = _request_for(state, item, item_id, instructions=instructions)
    result = dependencies.planner.run(request)
    update = state_update_from_result(result)
    update.update(
        {
            "current_item_index": item_index,
            "current_item_id": item_id,
            "current_item_title": item.get("title", ""),
            "plan": result.plan or _default_plan(),
            "builder_instructions": result.builder_instructions
            or result.feedback
            or state.get("builder_instructions", ""),
            "critic_passed": False,
            "critic_feedback": "",
            "validation_passed": False,
            "max_attempts": state.get("max_attempts", 3),
        }
    )
    if prd_items_update is not None:
        update["prd_items"] = prd_items_update
    if previous_item_id != item_id:
        update.update(
            {
                "attempts_count": 0,
                "build_completed": False,
                "validation_errors": [],
            }
        )
    return update


def building(state: WorkflowState, dependencies: NodeDependencies) -> WorkflowState:
    """Run the configured builder only when code needs to be produced/reworked."""

    # The critic routes back through this node after approval so the graph has
    # one explicit path into validation, but the code must not be rebuilt then.
    if state.get("critic_passed"):
        return {
            "status": "build_approved_for_validation",
            "build_completed": False,
        }

    max_attempts = state.get("max_attempts", 3)
    if state.get("attempts_count", 0) >= max_attempts:
        return {
            "status": "attempt_limit_reached",
            "last_error": f"Maximum build attempts reached ({max_attempts}).",
            "build_completed": False,
        }

    item = _current_item(state)
    critic_feedback = state.get("critic_feedback", "").strip()
    instructions = "\n\n".join(
        part
        for part in (
            state.get("builder_instructions", ""),
            f"Critic feedback:\n{critic_feedback}" if critic_feedback else "",
        )
        if part
    )
    request = _request_for(
        state,
        item,
        state.get("current_item_id", ""),
        instructions=instructions,
    )
    result = dependencies.builder.run(request)
    update = _merge_files(state, state_update_from_result(result))
    attempts_count = state.get("attempts_count", 0) + 1
    item_id = state.get("current_item_id", "")
    attempts_by_item = dict(state.get("attempts_by_item", {}))
    if item_id:
        attempts_by_item[item_id] = attempts_count
    files_touched_by_item = dict(state.get("files_touched_by_item", {}))
    if item_id:
        files_touched_by_item[item_id] = list(
            dict.fromkeys(
                [
                    *files_touched_by_item.get(item_id, []),
                    *result.files_touched,
                ]
            )
        )
    update.update(
        {
            "attempts_count": attempts_count,
            "attempts_by_item": attempts_by_item,
            "critic_passed": False,
            "build_completed": True,
            "status": result.status or "built",
            "files_touched_by_item": files_touched_by_item,
        }
    )
    if result.item_built is not False and result.status != "failed":
        update["prd_items"] = _mark_current_item_built(state)
    return update


def critic_auditor(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Review the current item with the configured low-cost critic."""

    item = _current_item(state)
    result = dependencies.critic.run(
        _request_for(
            state,
            item,
            state.get("current_item_id", ""),
            instructions=state.get("builder_instructions", ""),
        )
    )
    update = state_update_from_result(result)
    update.update(
        {
            "critic_model": result.assigned_model,
            "critic_passed": bool(result.approved),
            "critic_feedback": result.feedback,
            "status": result.status or "critic_audited",
        }
    )
    return update


def validation(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Run authoritative validation and mark the current item when it passes."""

    item = _current_item(state)
    result = dependencies.validator.run(
        _request_for(
            state,
            item,
            state.get("current_item_id", ""),
            instructions=state.get("builder_instructions", ""),
        )
    )
    passed = bool(result.validation_passed)
    update = state_update_from_result(result)
    update.update(
        {
            "validation_passed": passed,
            "validation_errors": list(result.validation_errors),
            "status": result.status or "validated",
            "prd_items": _mark_current_item_validated(state, passed),
        }
    )
    if passed:
        completed = list(state.get("completed_items", []))
        item_id = state.get("current_item_id", "")
        if item_id and item_id not in completed:
            completed.append(item_id)
        update["completed_items"] = completed
    return update


def debugger(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Analyze validation failure and prepare same-item rework instructions."""

    item = _current_item(state)
    failure_message = "\n".join(state.get("validation_errors", [])).strip()
    if not failure_message:
        failure_message = state.get("last_error", "").strip()
    if not failure_message:
        failure_message = "Validation failed without a reported message."
    result = dependencies.debugger.run(
        _request_for(
            state,
            item,
            state.get("current_item_id", ""),
            instructions=f"Validation failure:\n{failure_message}",
        )
    )
    update = state_update_from_result(result)
    update.update(
        {
            "debugger_model": result.assigned_model,
            "root_cause": result.root_cause or result.feedback,
            "builder_instructions": result.builder_instructions
            or state.get("builder_instructions", ""),
            "critic_passed": False,
            "validation_passed": False,
            "status": result.status or "debugged",
        }
    )
    return update


def item_router(state: WorkflowState) -> WorkflowState:
    """Prepare the decision to start another item or finish the workflow."""

    return {
        "status": "next_item_ready"
        if select_next_item(state) is not None
        else "complete"
    }


def commit_item(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Commit the validated current item before selecting the next one."""

    repository = dependencies.repository
    if repository is None:
        return {"status": "commit_skipped"}

    item_id = state.get("current_item_id", "")
    result = repository.commit_item(
        item_id,
        state.get("current_item_title", ""),
        list(state.get("files_touched_by_item", {}).get(item_id, [])),
    )
    return state_update_from_result(result)


def github_node(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Push the completed branch and create its pull request."""

    repository = dependencies.repository
    if repository is None:
        return {"status": "complete"}

    return state_update_from_result(repository.publish_pr(state.get("task", "")))


def attempt_limit(state: WorkflowState) -> WorkflowState:
    """Stop safely when an item needs more build attempts than allowed."""

    return {
        "status": "attempt_limit_reached",
        "last_error": state.get(
            "last_error",
            f"Maximum build attempts reached ({state.get('max_attempts', 3)}).",
        ),
    }


def route_after_building(
    state: WorkflowState,
) -> Literal["critic_auditor", "validation", "attempt_limit"]:
    """Route code to the critic, validation, or a safe attempt-limit stop."""

    if state.get("critic_passed"):
        return "validation"
    if (
        not state.get("build_completed")
        and state.get("attempts_count", 0) >= state.get("max_attempts", 3)
    ):
        return "attempt_limit"
    return "critic_auditor"


def route_after_planning(
    state: WorkflowState,
) -> Literal["building", "item_router"]:
    """Start the next item or send an already-complete run to the router."""

    if select_next_item(state) is None:
        return "item_router"
    return "building"


def route_after_intake(
    state: WorkflowState,
) -> Literal["learning", "planning"]:
    """Route the selected top-level mode into its focused workflow."""

    return "learning" if state.get("workflow_mode") == "learn" else "planning"


def route_after_validation(
    state: WorkflowState,
) -> Literal["debugger", "commit_item"]:
    """Send failures to debugging and successes to the commit checkpoint."""

    if not state.get("validation_passed"):
        return "debugger"
    return "commit_item"


def route_after_commit(
    state: WorkflowState,
) -> Literal["item_router", "__end__"]:
    """Continue only when the validated item was committed or had no changes."""

    return "__end__" if state.get("status") == "failed" else "item_router"


def route_after_item_router(
    state: WorkflowState,
) -> Literal["planning", "github_node"]:
    """Start the next incomplete item or finish the workflow."""

    return "planning" if select_next_item(state) is not None else "github_node"


def route_after_github(
    state: WorkflowState,
) -> Literal["__end__"]:
    """Stop after the handoff; debugger is reserved for validation failures."""

    return "__end__"


def _debugger_details(
    state: WorkflowState,
    item_id: str,
    previous_item_id: str | None,
) -> str:
    """Format new debugger findings for the current PRD requirement."""

    if previous_item_id != item_id:
        return ""

    root_cause = state.get("root_cause", "").strip()
    builder_instructions = state.get("builder_instructions", "").strip()
    failure_message = "\n".join(state.get("validation_errors", [])).strip()
    if not root_cause and not builder_instructions:
        return ""

    details = ["Debugger findings:"]
    if failure_message:
        details.append(f"Validation failure: {failure_message}")
    if root_cause:
        details.append(f"Root cause: {root_cause}")
    if builder_instructions:
        details.append(f"Repair instructions: {builder_instructions}")
    return "\n".join(details)


def _request_for(
    state: WorkflowState,
    item: PRDItem,
    item_id: str,
    *,
    instructions: str | None = None,
) -> AgentRequest:
    return AgentRequest(
        task=state.get("task", ""),
        item_id=item_id,
        item_title=item.get("title", ""),
        item_description=item.get("description", ""),
        prd_items=[dict(prd_item) for prd_item in state.get("prd_items", [])],
        instructions=(
            instructions
            if instructions is not None
            else state.get("builder_instructions", "")
        ),
        context=state.get("root_cause", ""),
    )


def _current_item(state: WorkflowState) -> PRDItem:
    selected = select_next_item(state)
    if selected is not None:
        return selected[1]
    return {
        "id": state.get("current_item_id", "starter-item"),
        "title": state.get("current_item_title", state.get("task", "Starter task")),
        "passes": False,
    }


def _merge_files(
    state: WorkflowState,
    update: WorkflowState,
) -> WorkflowState:
    previous = state.get("files_touched", [])
    current = update.get("files_touched", [])
    update["files_touched"] = list(dict.fromkeys([*previous, *current]))
    return update


def _mark_current_item_built(state: WorkflowState) -> list[PRDItem]:
    items = [dict(item) for item in state.get("prd_items", [])]
    index = state.get("current_item_index", 0)
    if 0 <= index < len(items):
        items[index]["passes"] = True
        items[index]["validation"] = False
    return items


def _mark_current_item_validated(
    state: WorkflowState,
    passed: bool,
) -> list[PRDItem]:
    items = [dict(item) for item in state.get("prd_items", [])]
    index = state.get("current_item_index", 0)
    if 0 <= index < len(items):
        items[index]["validation"] = passed
        if passed:
            items[index]["passes"] = True
    return items


def _default_plan() -> list[str]:
    return [
        "Understand the current PRD item",
        "Implement the change",
        "Run validation",
    ]


__all__ = [
    "NodeDependencies",
    "building",
    "critic_auditor",
    "commit_item",
    "create_nodes",
    "debugger",
    "default_dependencies",
    "claude_opus_4_8_dependencies",
    "gpt_5_6_luna_dependencies",
    "github_node",
    "intake",
    "learning",
    "item_router",
    "attempt_limit",
    "planning",
    "route_after_intake",
    "route_after_building",
    "route_after_commit",
    "route_after_github",
    "route_after_item_router",
    "route_after_validation",
    "select_next_item",
    "validation",
]
