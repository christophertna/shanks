"""Standardized LangGraph node implementations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langgraph.errors import NodeError
from langgraph.types import Command, interrupt

from .adapters import (
    ClaudeAdapter,
    ClaudeOpus48CriticAdapter,
    CodexAdapter,
    DebuggerAdapter,
    GPT56LunaCriticAdapter,
    GitHubAdapter,
    LocalTestAdapter,
    RalphAdapter,
    redact_secrets,
)
from .contracts import (
    AgentAdapter,
    AgentRequest,
    AgentResult,
    NodeFunction,
    RepositoryAdapter,
    state_update_from_result,
)
from .state import (
    CURRENT_STATE_SCHEMA_VERSION,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_COST_USD,
    DEFAULT_MAX_RUNTIME_SECONDS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOTAL_ATTEMPTS,
    PRDItem,
    WorkflowState,
    acceptance_criteria_for_item,
    append_run_manifest,
    migrate_state,
    validation_command_for_item,
)


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


def _versioned_node(node: NodeFunction) -> NodeFunction:
    """Migrate state, enforce run budgets, and stamp every checkpoint."""

    def run(state: WorkflowState) -> WorkflowState:
        current = migrate_state(state)
        started_at = current.get("run_started_at")
        if (
            isinstance(started_at, bool)
            or not isinstance(started_at, (int, float))
            or started_at <= 0
        ):
            started_at = time.time()
        current = {**current, "run_started_at": float(started_at)}

        reason = _stop_reason(current)
        if reason:
            return _stop_update(current, reason)

        update = dict(node(current))
        update["run_started_at"] = float(started_at)
        update.update(_usage_totals(current, update))
        merged = {**current, **update}
        reason = _stop_reason(merged)
        if reason:
            update.update(_stop_update(merged, reason))
        update["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
        return update

    return run


_STOP_STATUSES = frozenset({"cancelled", "budget_exceeded"})


def _stop_reason(state: WorkflowState) -> str | None:
    """Return the first configured cancellation or budget stop reason."""

    if state.get("cancel_requested"):
        return state.get("cancel_reason", "").strip() or "Cancelled by user."

    invalid = _invalid_budget(state)
    if invalid:
        return invalid

    started_at = state.get("run_started_at")
    runtime_limit = state.get("max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS)
    if isinstance(started_at, (int, float)) and not isinstance(started_at, bool):
        if time.time() - started_at >= runtime_limit:
            return f"Maximum runtime exceeded ({runtime_limit:g} seconds)."

    total_attempts = _nonnegative_int(state.get("total_attempts", 0))
    attempt_limit = state.get(
        "max_total_attempts",
        DEFAULT_MAX_TOTAL_ATTEMPTS,
    )
    if total_attempts >= attempt_limit:
        return f"Maximum total attempts reached ({attempt_limit})."

    total_tokens = _nonnegative_int(state.get("total_tokens", 0))
    token_limit = state.get("max_tokens", DEFAULT_MAX_TOKENS)
    if total_tokens >= token_limit:
        return f"Maximum token budget reached ({token_limit})."

    total_cost = _nonnegative_float(state.get("total_cost_usd", 0.0))
    cost_limit = state.get("max_cost_usd", DEFAULT_MAX_COST_USD)
    if cost_limit > 0 and total_cost >= cost_limit:
        return f"Maximum cost budget reached (${cost_limit:.2f})."
    return None


def _invalid_budget(state: WorkflowState) -> str | None:
    """Reject malformed limits instead of silently running without guardrails."""

    for key in (
        "max_runtime_seconds",
        "max_total_attempts",
        "max_tokens",
        "max_cost_usd",
    ):
        value = state.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"Invalid budget value for {key}."
        if value < 0:
            return f"Budget value for {key} cannot be negative."
    return None


def _stop_update(state: WorkflowState, reason: str) -> WorkflowState:
    """Return a terminal state update without invoking another backend."""

    return {
        "status": "cancelled" if state.get("cancel_requested") else "budget_exceeded",
        "last_error": reason,
        "run_started_at": state.get("run_started_at", time.time()),
        "state_schema_version": CURRENT_STATE_SCHEMA_VERSION,
    }


def _usage_totals(
    state: WorkflowState,
    update: WorkflowState,
) -> WorkflowState:
    """Accumulate usage deltas reported by one adapter invocation."""

    input_tokens = _nonnegative_int(update.get("last_input_tokens", 0))
    output_tokens = _nonnegative_int(update.get("last_output_tokens", 0))
    cost_usd = _nonnegative_float(update.get("last_cost_usd", 0.0))
    total_input = _nonnegative_int(state.get("total_input_tokens", 0)) + input_tokens
    total_output = _nonnegative_int(state.get("total_output_tokens", 0)) + output_tokens
    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_usd": _nonnegative_float(state.get("total_cost_usd", 0.0))
        + cost_usd,
    }


def _nonnegative_int(value: object) -> int:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else 0
    )


def _nonnegative_float(value: object) -> float:
    return (
        value
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
        else 0.0
    )


def _run_stopped(state: WorkflowState) -> bool:
    return state.get("status") in _STOP_STATUSES or _stop_reason(state) is not None


def remaining_runtime_seconds(state: WorkflowState) -> float | None:
    """Return the current run's remaining wall-clock budget for adapters."""

    started_at = state.get("run_started_at")
    limit = state.get("max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS)
    if (
        isinstance(started_at, (int, float))
        and not isinstance(started_at, bool)
        and isinstance(limit, (int, float))
        and not isinstance(limit, bool)
    ):
        return max(0.0, limit - (time.time() - started_at))
    return None


def create_nodes(
    dependencies: NodeDependencies | None = None,
) -> dict[str, NodeFunction]:
    """Create state-only node callables with injected agent backends."""

    deps = dependencies or default_dependencies()

    nodes = {
        "preflight": lambda state: preflight(state, deps),
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
        "failed_build": failed_build,
        "stop_run": stop_run,
    }
    return {name: _versioned_node(node) for name, node in nodes.items()}


def preflight(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Run repository preflight checks before asking for workflow mode."""

    repository = dependencies.repository
    check = getattr(repository, "preflight", None)
    if check is None:
        return {"status": "preflight_skipped"}
    result = check()
    update = state_update_from_result(result)
    update.update(_audit_result(state, "preflight", result))
    return update


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
    update.update(_audit_result(state, "learning", result, request))
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
    update.update(_audit_result(state, "planning", result, request))
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
            "max_attempts": state.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
            "max_total_attempts": state.get(
                "max_total_attempts",
                DEFAULT_MAX_TOTAL_ATTEMPTS,
            ),
            "max_runtime_seconds": state.get(
                "max_runtime_seconds",
                DEFAULT_MAX_RUNTIME_SECONDS,
            ),
            "max_tokens": state.get("max_tokens", DEFAULT_MAX_TOKENS),
            "max_cost_usd": state.get("max_cost_usd", DEFAULT_MAX_COST_USD),
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
                "commit_sha": "",
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
    update.update(_audit_result(state, "building", result, request))
    attempts_count = state.get("attempts_count", 0) + 1
    total_attempts = state.get("total_attempts", 0) + 1
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
    uncertainties_by_item = dict(state.get("uncertainties_by_item", {}))
    if item_id and (item_id in uncertainties_by_item or result.uncertainties):
        uncertainties_by_item[item_id] = list(
            dict.fromkeys(
                [
                    *uncertainties_by_item.get(item_id, []),
                    *result.uncertainties,
                ]
            )
        )
    update.update(
        {
            "attempts_count": attempts_count,
            "total_attempts": total_attempts,
            "attempts_by_item": attempts_by_item,
            "critic_passed": False,
            "build_completed": result.status != "failed",
            "status": result.status or "built",
            "files_touched_by_item": files_touched_by_item,
            "uncertainties_by_item": uncertainties_by_item,
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
    request = _request_for(
        state,
        item,
        state.get("current_item_id", ""),
        instructions=state.get("builder_instructions", ""),
    )
    result = dependencies.critic.run(request)
    update = state_update_from_result(result)
    update.update(_audit_result(state, "critic_auditor", result, request))
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
    request = _request_for(
        state,
        item,
        state.get("current_item_id", ""),
        instructions=state.get("builder_instructions", ""),
    )
    result = dependencies.validator.run(request)
    passed = bool(result.validation_passed)
    update = state_update_from_result(result)
    update.update(_audit_result(state, "validation", result, request))
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
    request = _request_for(
        state,
        item,
        state.get("current_item_id", ""),
        instructions=f"Validation failure:\n{failure_message}",
    )
    result = dependencies.debugger.run(request)
    update = state_update_from_result(result)
    update.update(_audit_result(state, "debugger", result, request))
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
    if state.get("commit_sha"):
        return {
            "status": "committed",
            "commit_sha": state["commit_sha"],
        }
    if repository is None:
        return {"status": "commit_skipped"}

    item_id = state.get("current_item_id", "")
    if not _request_approval(
        action="commit",
        question="Approve committing this validated item?",
        details={
            "item_id": item_id,
            "item_title": state.get("current_item_title", ""),
            "files": list(state.get("files_touched_by_item", {}).get(item_id, [])),
        },
    ):
        return _approval_denied("commit")

    result = repository.commit_item(
        item_id,
        state.get("current_item_title", ""),
        list(state.get("files_touched_by_item", {}).get(item_id, [])),
    )
    update = state_update_from_result(result)
    update.update(_audit_result(state, "commit_item", result))
    return update


def github_node(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Push the completed branch and create its pull request."""

    repository = dependencies.repository
    if state.get("pr_url"):
        return {
            "status": "pr_created",
            "pr_url": state["pr_url"],
        }
    if repository is None:
        return {"status": "complete"}

    if not _request_approval(
        action="publish_pr",
        question="Approve pushing the branch and opening a pull request?",
        details={
            "operations": ["push", "open_pull_request"],
            "task": redact_secrets(state.get("task", "")),
        },
    ):
        return _approval_denied("push or open a pull request")

    result = repository.publish_pr(state.get("task", ""))
    update = state_update_from_result(result)
    update.update(_audit_result(state, "github_node", result))
    return update


def attempt_limit(state: WorkflowState) -> WorkflowState:
    """Stop safely when an item needs more build attempts than allowed."""

    return {
        "status": "attempt_limit_reached",
        "last_error": state.get(
            "last_error",
            f"Maximum build attempts reached ({state.get('max_attempts', 3)}).",
        ),
    }


def failed_build(state: WorkflowState) -> WorkflowState:
    """Stop safely when the builder fails after its retries are exhausted."""

    return {
        "status": "failed",
        "last_error": state.get("last_error") or "Build failed.",
        "build_completed": False,
    }


def stop_run(state: WorkflowState) -> WorkflowState:
    """Finish a cancelled or budget-exhausted run without side effects."""

    return {
        "status": state.get("status", "cancelled"),
        "last_error": state.get("last_error", "Run stopped."),
    }


def build_error_handler(
    state: WorkflowState,
    error: NodeError,
) -> Command:
    """Route an exhausted native build-node failure to the terminal path."""

    return Command(
        update={
            "status": "failed",
            "last_error": str(error.error),
            "build_completed": False,
        },
        goto="failed_build",
    )


def route_after_building(
    state: WorkflowState,
) -> Literal[
    "critic_auditor",
    "validation",
    "attempt_limit",
    "failed_build",
    "stop_run",
]:
    """Route code to review, validation, retry limiting, or failed-build stop."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "failed":
        return "failed_build"
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
) -> Literal["building", "item_router", "stop_run"]:
    """Start the next item or send an already-complete run to the router."""

    if _run_stopped(state):
        return "stop_run"
    if select_next_item(state) is None:
        return "item_router"
    return "building"


def route_after_intake(
    state: WorkflowState,
) -> Literal["learning", "planning", "stop_run"]:
    """Route the selected top-level mode into its focused workflow."""

    if _run_stopped(state):
        return "stop_run"
    return "learning" if state.get("workflow_mode") == "learn" else "planning"


def route_after_preflight(
    state: WorkflowState,
) -> Literal["intake", "__end__"]:
    """Enter intake only after preflight succeeds or is explicitly skipped."""

    if _run_stopped(state) or state.get("status") == "preflight_failed":
        return "__end__"
    return "intake"


def route_after_validation(
    state: WorkflowState,
) -> Literal["debugger", "commit_item", "stop_run"]:
    """Send failures to debugging and successes to the commit checkpoint."""

    if _run_stopped(state):
        return "stop_run"
    if not state.get("validation_passed"):
        return "debugger"
    return "commit_item"


def route_after_commit(
    state: WorkflowState,
) -> Literal["item_router", "stop_run", "__end__"]:
    """Continue only when the validated item was committed or had no changes."""

    if _run_stopped(state):
        return "stop_run"
    return (
        "item_router"
        if state.get("status") in {"committed", "no_changes", "commit_skipped"}
        else "__end__"
    )


def route_after_item_router(
    state: WorkflowState,
) -> Literal["planning", "github_node", "stop_run"]:
    """Start the next incomplete item or finish the workflow."""

    if _run_stopped(state):
        return "stop_run"
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


def _request_approval(
    *,
    action: str,
    question: str,
    details: dict[str, object],
) -> bool:
    """Pause until a human explicitly approves or rejects a side effect."""

    prompt: dict[str, object] = {
        "type": "approval",
        "action": action,
        "question": question,
        "options": [
            {"value": "approve", "label": "Approve"},
            {"value": "reject", "label": "Reject"},
        ],
        **details,
    }
    while True:
        answer = interrupt(prompt)
        if isinstance(answer, dict):
            answer = next(
                (
                    answer[key]
                    for key in ("choice", "approval", "decision", "approved")
                    if key in answer
                ),
                None,
            )
        if answer is True:
            return True
        if answer is False:
            return False
        if isinstance(answer, str):
            answer = answer.strip().lower()
            if answer in {"approve", "approved", "yes", "y"}:
                return True
            if answer in {"reject", "rejected", "deny", "denied", "no", "n"}:
                return False
        prompt = {**prompt, "error": "Choose approve or reject."}


def _approval_denied(action: str) -> WorkflowState:
    return {
        "status": "approval_denied",
        "last_error": f"Human approval denied before {action}.",
    }


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
        acceptance_criteria=acceptance_criteria_for_item(item),
        validation_command=validation_command_for_item(item),
        prd_items=[dict(prd_item) for prd_item in state.get("prd_items", [])],
        instructions=(
            instructions
            if instructions is not None
            else state.get("builder_instructions", "")
        ),
        context=state.get("root_cause", ""),
        timeout_seconds=remaining_runtime_seconds(state),
    )


def _audit_result(
    state: WorkflowState,
    node: str,
    result: AgentResult,
    request: AgentRequest | None = None,
) -> WorkflowState:
    """Capture one redacted agent or repository operation in the run manifest."""

    details: dict[str, object] = {
        "node": node,
        "status": result.status,
        "model": result.assigned_model,
    }
    if request is not None:
        details["prompt"] = (
            redact_secrets(result.prompt)
            if result.prompt
            else _redact_manifest_value(
                {
                    "task": request.task,
                    "item_id": request.item_id,
                    "item_title": request.item_title,
                    "item_description": request.item_description,
                    "acceptance_criteria": request.acceptance_criteria,
                    "validation_command": request.validation_command,
                    "prd_items": request.prd_items,
                    "instructions": request.instructions,
                    "context": request.context,
                    "timeout_seconds": request.timeout_seconds,
                }
            )
        )
    if result.commands:
        details["commands"] = _redact_manifest_value(result.commands)
    if result.feedback:
        output = redact_secrets(result.feedback)
        details["output"] = output
        if node in {"preflight", "validation"}:
            details["test_output"] = output
    if result.test_output:
        details["test_output"] = redact_secrets(result.test_output)
    if result.error:
        details["error"] = redact_secrets(result.error)
    if result.validation_errors:
        details["validation_errors"] = [
            redact_secrets(error) for error in result.validation_errors
        ]
    if result.files_touched:
        details["files_touched"] = list(result.files_touched)
    if result.diff:
        details["diff"] = redact_secrets(result.diff)
    if result.commit_sha:
        details["commit_sha"] = result.commit_sha
    if result.pr_url:
        details["pull_request_url"] = redact_secrets(result.pr_url)
        details["pull_request_id"] = _pull_request_id(result.pr_url)
    return append_run_manifest(state, "agent" if request else "repository", **details)


def _pull_request_id(url: str) -> str:
    """Extract the numeric or opaque ID at the end of a pull-request URL."""

    return url.rstrip("/").rsplit("/", 1)[-1] if "/pull/" in url else ""


def _redact_manifest_value(value: object) -> object:
    """Redact strings recursively before they enter persisted state."""

    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {
            str(key): _redact_manifest_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_manifest_value(item) for item in value]
    return value


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
    "failed_build",
    "default_dependencies",
    "claude_opus_4_8_dependencies",
    "gpt_5_6_luna_dependencies",
    "github_node",
    "intake",
    "learning",
    "item_router",
    "attempt_limit",
    "build_error_handler",
    "planning",
    "preflight",
    "route_after_preflight",
    "route_after_intake",
    "route_after_building",
    "route_after_commit",
    "route_after_github",
    "stop_run",
    "route_after_item_router",
    "route_after_validation",
    "select_next_item",
    "validation",
]
