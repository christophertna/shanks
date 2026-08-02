"""Standardized LangGraph node implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .adapters import CheapCriticAdapter, StubAgentAdapter
from .contracts import (
    AgentAdapter,
    AgentRequest,
    AgentResult,
    NodeFunction,
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


def default_dependencies() -> NodeDependencies:
    """Return side-effect-free adapters for local graph development."""

    return NodeDependencies(
        planner=StubAgentAdapter("planner", "planner-stub"),
        builder=StubAgentAdapter("builder", "builder-stub"),
        critic=CheapCriticAdapter(),
        validator=StubAgentAdapter("validator", "validator-stub"),
        debugger=StubAgentAdapter("debugger", "debugger-stub"),
    )


def select_next_item(state: WorkflowState) -> tuple[int, PRDItem] | None:
    """Select the first incomplete item at or after the current index."""

    items = state.get("prd_items", [])
    start_index = state.get("current_item_index", 0)
    for index in range(start_index, len(items)):
        item = items[index]
        if not item.get("passes", False):
            return index, item
    return None


def create_nodes(
    dependencies: NodeDependencies | None = None,
) -> dict[str, NodeFunction]:
    """Create state-only node callables with injected agent backends."""

    deps = dependencies or default_dependencies()

    return {
        "planning": lambda state: planning(state, deps),
        "building": lambda state: building(state, deps),
        "critic_auditor": lambda state: critic_auditor(state, deps),
        "validation": lambda state: validation(state, deps),
        "debugger": lambda state: debugger(state, deps),
        "item_router": item_router,
        "attempt_limit": attempt_limit,
    }


def planning(state: WorkflowState, dependencies: NodeDependencies) -> WorkflowState:
    """Plan the current incomplete item without losing retry context."""

    selected = select_next_item(state)
    if selected is None:
        return {"status": "complete"}

    item_index, item = selected
    item_id = item.get("id", f"item-{item_index + 1}")
    previous_item_id = state.get("current_item_id")
    request = _request_for(state, item, item_id)
    result = dependencies.planner.run(request)
    update = state_update_from_result(result)
    update.update(
        {
            "current_item_index": item_index,
            "current_item_id": item_id,
            "current_item_title": item.get("title", ""),
            "plan": result.plan or _default_plan(),
            "builder_instructions": result.builder_instructions
            or state.get("builder_instructions", ""),
            "critic_passed": False,
            "validation_passed": False,
            "max_attempts": state.get("max_attempts", 3),
        }
    )
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
    request = _request_for(state, item, state.get("current_item_id", ""))
    result = dependencies.builder.run(request)
    update = _merge_files(state, state_update_from_result(result))
    attempts_count = state.get("attempts_count", 0) + 1
    item_id = state.get("current_item_id", "")
    attempts_by_item = dict(state.get("attempts_by_item", {}))
    if item_id:
        attempts_by_item[item_id] = attempts_count
    update.update(
        {
            "attempts_count": attempts_count,
            "attempts_by_item": attempts_by_item,
            "critic_passed": False,
            "build_completed": True,
            "status": result.status or "built",
        }
    )
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
        }
    )
    if passed:
        update["prd_items"] = _mark_current_item_passed(state)
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
    result = dependencies.debugger.run(
        _request_for(
            state,
            item,
            state.get("current_item_id", ""),
            instructions="\n".join(state.get("validation_errors", [])),
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


def route_after_validation(
    state: WorkflowState,
) -> Literal["debugger", "item_router"]:
    """Send failures to debugging and successes to the item router."""

    if not state.get("validation_passed"):
        return "debugger"
    return "item_router"


def route_after_item_router(
    state: WorkflowState,
) -> Literal["planning", "__end__"]:
    """Start the next incomplete item or finish the workflow."""

    return "planning" if select_next_item(state) is not None else "__end__"


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


def _mark_current_item_passed(state: WorkflowState) -> list[PRDItem]:
    items = [dict(item) for item in state.get("prd_items", [])]
    index = state.get("current_item_index", 0)
    if 0 <= index < len(items):
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
    "create_nodes",
    "debugger",
    "default_dependencies",
    "item_router",
    "attempt_limit",
    "planning",
    "route_after_building",
    "route_after_item_router",
    "route_after_validation",
    "select_next_item",
    "validation",
]
