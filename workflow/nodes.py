"""Standardized LangGraph node implementations."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from langgraph.errors import GraphInterrupt, NodeError
from langgraph.types import Command, interrupt
from langchain_core.runnables import RunnableConfig

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
    PreviewRepositoryAdapter,
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
    migrate_state,
    run_manifest_event,
    validation_command_for_item,
)
from .retries import classify_failure, retry_delay, retryable_failure
from .lifecycle import (
    LeaseLostError,
    RunBusyError,
    RunLifecycleManager,
    TERMINAL_RUN_STATUSES,
)
from .mode import is_development_mode, is_dry_run
from .workspaces import (
    RunWorkspace,
    RunWorkspaceManager,
    WorkspaceError,
    current_workspace_directory,
    workspace_scope,
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
    workspace_manager: RunWorkspaceManager | None = None
    lifecycle_manager: RunLifecycleManager | None = None


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
    workspace_manager: RunWorkspaceManager | None = None,
    base_branch: str = "main",
    worktree_root: Path | None = None,
    lifecycle_manager: RunLifecycleManager | None = None,
) -> NodeDependencies:
    """Return a complete Claude- or Codex-backed workflow configuration."""

    if tool not in {"claude", "codex"}:
        raise ValueError("tool must be 'claude' or 'codex'")
    project_directory = project_directory or Path.cwd()
    workspace_manager = workspace_manager or RunWorkspaceManager(
        project_directory,
        base_branch=base_branch,
        worktree_root=worktree_root,
    )
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
        repository=GitHubAdapter(project_directory, base_branch=base_branch),
        workspace_manager=workspace_manager,
        lifecycle_manager=lifecycle_manager,
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


def _versioned_node(
    node: NodeFunction,
    workspace_manager: RunWorkspaceManager | None = None,
    lifecycle_manager: RunLifecycleManager | None = None,
) -> NodeFunction:
    """Migrate state, enforce run budgets, and stamp every checkpoint."""

    def run(
        state: WorkflowState,
        config: RunnableConfig,
    ) -> WorkflowState:
        current = migrate_state(state)
        thread_id = _thread_id(config)
        stored_run_id = current.get("run_id", "")
        if stored_run_id and thread_id and stored_run_id != thread_id:
            return {
                "status": "run_locked",
                "run_lifecycle_status": "blocked",
                "last_error": "Checkpoint run identity does not match thread_id.",
                "failure_class": "guardrail",
                "failure_node": "lease",
                "state_schema_version": CURRENT_STATE_SCHEMA_VERSION,
            }
        run_id = stored_run_id or thread_id
        lifecycle_update: WorkflowState = {}
        # Events recorded around the wrapped node. They have to travel in the
        # returned update, not in `current`: the reducer only sees what a node
        # returns, and `current` is a local read-only view.
        events: list[dict[str, Any]] = []
        recovered = False
        if lifecycle_manager is not None and run_id:
            try:
                lease = lifecycle_manager.acquire(run_id)
            except RunBusyError as error:
                failure: WorkflowState = {
                    "run_id": run_id,
                    "status": "run_locked",
                    "run_lifecycle_status": "blocked",
                    "last_error": str(error),
                    "failure_class": "guardrail",
                    "failure_node": "lease",
                    "state_schema_version": CURRENT_STATE_SCHEMA_VERSION,
                }
                failure["run_manifest"] = [
                    *events,
                    run_manifest_event(
                        "run_locked",
                        run_id=run_id,
                        status="blocked",
                        error=str(error),
                    ),
                ]
                return failure
            lifecycle_update = {
                "run_lifecycle_status": "running",
                "run_lease_expires_at": lease.expires_at,
                "run_last_heartbeat_at": lease.heartbeat_at,
                "run_recovery_count": lease.recovery_count,
            }
            recovered = lease.recovered
            if lease.recovered:
                current = {**current, **lifecycle_update}
                events.append(
                    run_manifest_event(
                        "run_recovered",
                        run_id=run_id,
                        previous_owner=lease.previous_owner,
                        recovery_count=lease.recovery_count,
                    )
                )
        workspace = None
        if workspace_manager is not None and run_id:
            try:
                workspace = workspace_manager.ensure(run_id)
            except WorkspaceError as error:
                if lifecycle_manager is not None:
                    lifecycle_manager.release(
                        run_id,
                        status="preflight_failed",
                        last_error=str(error),
                    )
                failure: WorkflowState = {
                    "run_id": run_id,
                    "status": "preflight_failed",
                    "last_error": f"Could not create isolated workspace: {error}",
                    "failure_class": "guardrail",
                    "failure_node": "workspace",
                    **lifecycle_update,
                    "state_schema_version": CURRENT_STATE_SCHEMA_VERSION,
                }
                failure["run_manifest"] = [
                    *events,
                    run_manifest_event(
                        "workspace",
                        run_id=run_id,
                        status="failed",
                        error=str(error),
                    ),
                ]
                return failure
        workspace_directory = (
            workspace.directory
            if workspace is not None
            else _state_workspace_directory(current)
        )
        workspace_update: WorkflowState = {}
        if run_id:
            workspace_update["run_id"] = run_id
        if workspace is not None:
            workspace_update.update(
                {
                    "run_branch": workspace.branch,
                    "workspace_directory": str(workspace.directory),
                }
            )
        current = {**current, **workspace_update, **lifecycle_update}
        started_at = current.get("run_started_at")
        if (
            isinstance(started_at, bool)
            or not isinstance(started_at, (int, float))
            or started_at <= 0
        ):
            started_at = time.time()
        current = {**current, "run_started_at": float(started_at)}

        try:
            with workspace_scope(workspace_directory):
                reason = _stop_reason(current)
                if reason:
                    stopped: WorkflowState = {
                        **workspace_update,
                        **lifecycle_update,
                        **_stop_update(current, reason),
                    }
                    if events:
                        stopped["run_manifest"] = events
                    return stopped
                if recovered and workspace is not None:
                    problems = _reconcile_recovered_state(current, workspace)
                    if problems:
                        events.append(
                            run_manifest_event(
                                "recovery_reconciliation_mismatch",
                                run_id=run_id,
                                problems=problems,
                            )
                        )
                        interrupt(
                            {
                                "type": "recovery_reconciliation",
                                "message": (
                                    "This recovered run's checkpoint state "
                                    "disagrees with the actual repository "
                                    "state. Review before continuing."
                                ),
                                "run_id": run_id,
                                "problems": problems,
                            }
                        )
                update = {
                    **workspace_update,
                    **lifecycle_update,
                    **dict(node(current)),
                }
        except GraphInterrupt:
            if lifecycle_manager is not None and run_id:
                lifecycle_manager.mark_interrupted(run_id)
            raise
        events.extend(update.pop("run_manifest", []))
        if lifecycle_manager is not None and run_id:
            try:
                heartbeat = lifecycle_manager.heartbeat(run_id)
            except LeaseLostError as error:
                update.update(
                    {
                        "status": "failed",
                        "run_lifecycle_status": "failed",
                        "last_error": str(error),
                        "failure_class": "guardrail",
                        "failure_node": "lease",
                    }
                )
                events.append(
                    run_manifest_event(
                        "lease_lost",
                        run_id=run_id,
                        error=str(error),
                    )
                )
            else:
                update.update(
                    {
                        "run_lease_expires_at": heartbeat.expires_at,
                        "run_last_heartbeat_at": heartbeat.heartbeat_at,
                    }
                )
        update["run_started_at"] = float(started_at)
        update.update(_usage_totals(current, update))
        merged = {**current, **update}
        reason = _stop_reason(merged)
        if reason:
            update.update(_stop_update(merged, reason))
        if lifecycle_manager is not None and run_id:
            status = update.get("status", "")
            if status in TERMINAL_RUN_STATUSES:
                update["run_lifecycle_status"] = _run_lifecycle_status(status)
        update["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
        if events:
            update["run_manifest"] = events
        return update

    return run


_RECONCILE_TIMEOUT_SECONDS = 15


def _reconcile_recovered_state(
    current: WorkflowState,
    workspace: RunWorkspace,
) -> list[str]:
    """Verify commit_sha/run_branch/pr_url still hold in a recovered run.

    Runs once, only on the first node call after a new process takes over an
    existing run (see lease.recovered in _versioned_node) - a stale checkpoint
    could otherwise let commit_item/push_node trust a commit_sha or pr_url
    that no longer reflects reality instead of surfacing it for review."""

    problems: list[str] = []
    directory = workspace.directory

    commit_sha = current.get("commit_sha", "")
    if commit_sha:
        check = _reconcile_run(
            ("git", "cat-file", "-e", f"{commit_sha}^{{commit}}"),
            cwd=directory,
        )
        if check.returncode != 0:
            problems.append(
                f"commit_sha {commit_sha!r} is no longer reachable in the "
                "workspace worktree."
            )

    pr_url = current.get("pr_url", "")
    run_branch = current.get("run_branch", "")
    if pr_url:
        if run_branch:
            remote = _reconcile_run(
                ("git", "ls-remote", "--heads", "origin", run_branch),
                cwd=directory,
            )
            if remote.returncode != 0 or not remote.stdout.strip():
                problems.append(
                    f"branch {run_branch!r} has a recorded pull request but no "
                    "matching ref on origin."
                )
        pr_check = _reconcile_run(
            ("gh", "pr", "view", pr_url, "--json", "state,url"),
            cwd=directory,
        )
        if pr_check.returncode != 0:
            detail = (pr_check.stderr or "").strip() or "gh query failed"
            problems.append(f"pull request {pr_url!r} could not be verified: {detail}.")

    return problems


def _reconcile_run(
    command: tuple[str, ...],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=_RECONCILE_TIMEOUT_SECONDS,
            check=False,
            env=GitHubAdapter._github_environment(command),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(command, 1, "", str(error))


def _thread_id(config: RunnableConfig | None) -> str:
    if not isinstance(config, dict):
        return ""
    configurable = config.get("configurable", {})
    if not isinstance(configurable, dict):
        return ""
    thread_id = configurable.get("thread_id", "")
    return thread_id.strip() if isinstance(thread_id, str) else ""


def _state_workspace_directory(state: WorkflowState) -> Path | None:
    directory = state.get("workspace_directory", "")
    if not isinstance(directory, str) or not directory.strip():
        return current_workspace_directory()
    return Path(directory)


def _run_lifecycle_status(status: str) -> str:
    if status in {"complete", "pr_created", "pull_request_preview"}:
        return "complete"
    if status in {"cancelled", "budget_exceeded"}:
        return "cancelled"
    return "failed"


_STOP_STATUSES = frozenset({"cancelled", "budget_exceeded", "run_locked"})


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
        "run_lifecycle_status": (
            "cancelled" if state.get("cancel_requested") else "failed"
        ),
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


_RETRYABLE_NODES = frozenset(
    {
        "preflight",
        "learning",
        "planning",
        "building",
        "critic_auditor",
        "validation",
        "debugger",
        "push_node",
        "pull_request_node",
    }
)


def _apply_failure_policy(
    state: WorkflowState,
    node: str,
    result: AgentResult,
    update: WorkflowState,
) -> WorkflowState:
    """Record a failure and schedule only safe transient retries."""

    if not result.failure_class:
        return update

    effective_state = {**state, **update}
    retry_counts = dict(effective_state.get("retry_counts", {}))
    retry_number = retry_counts.get(node, 0) + 1
    retry_counts[node] = retry_number
    update.update(
        {
            "failure_node": node,
            "retry_counts": retry_counts,
        }
    )
    max_attempts = effective_state.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
    attempts = effective_state.get("attempts_count", 0)
    attempts_available = (
        attempts < max_attempts if node == "building" else retry_number < max_attempts
    )
    if (
        node in _RETRYABLE_NODES
        and retryable_failure(result.failure_class)
        and attempts_available
    ):
        delay = retry_delay(retry_number)
        update.update(
            {
                "status": "retry_scheduled",
                "retry_target": node,
                "retry_delay_seconds": delay,
            }
        )
        _record_events(
            update,
            run_manifest_event(
                "retry",
                node=node,
                failure_class=result.failure_class,
                retry_number=retry_number,
                delay_seconds=delay,
            ),
        )
    return update


def _exception_failure_class(error: BaseException) -> str:
    """Classify the original exception carried by LangGraph's NodeError."""

    return classify_failure(error=error)


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
        "pre_commit_policy_gate": lambda state: pre_commit_policy_gate(state, deps),
        "commit_item": lambda state: commit_item(state, deps),
        "debugger": lambda state: debugger(state, deps),
        "item_router": item_router,
        "push_node": lambda state: push_node(state, deps),
        "pull_request_node": lambda state: pull_request_node(state, deps),
        "retry_backoff": retry_backoff,
        "attempt_limit": attempt_limit,
        "failed_build": failed_build,
        "failed_run": failed_run,
        "stop_run": stop_run,
    }
    return {
        name: _versioned_node(
            node,
            deps.workspace_manager,
            deps.lifecycle_manager,
        )
        for name, node in nodes.items()
    }


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
    _record_events(update, _audit_result("preflight", result))
    return _apply_failure_policy(state, "preflight", result, update)


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
                task = (
                    state.get("task", "").strip() or "Implement the requested feature"
                )
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
    _record_events(update, _audit_result("learning", result, request))
    update.update(
        {
            "workflow_mode": None,
            "learning_notes": result.feedback,
            "status": "learned" if result.status != "failed" else "learning_failed",
        }
    )
    return _apply_failure_policy(state, "learning", result, update)


def planning(state: WorkflowState, dependencies: NodeDependencies) -> WorkflowState:
    """Plan the current incomplete item without losing retry context."""

    selected = select_next_item(state)
    if selected is None:
        return {"status": "complete"}

    # ponytail: refreshed once per item, not per node call, so a long build
    # loop can still go stale mid-item. Move it into _versioned_node if that
    # ever matters more than one git fetch per node.
    state, drift_events = _with_drift(state, dependencies)
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
    _record_events(update, *drift_events, _audit_result("planning", result, request))
    update.update(
        {
            "current_item_index": item_index,
            "current_item_id": item_id,
            "current_item_title": item.get("title", ""),
            "repo_drift": state.get("repo_drift", ""),
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
                "retry_counts": {},
                "retry_target": "",
                "retry_delay_seconds": 0.0,
            }
        )
    return _apply_failure_policy(state, "planning", result, update)


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
    _record_events(update, _audit_result("building", result, request))
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
    return _apply_failure_policy(state, "building", result, update)


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
    _record_events(update, _audit_result("critic_auditor", result, request))
    update.update(
        {
            "critic_model": result.assigned_model,
            "critic_passed": bool(result.approved),
            "critic_feedback": result.feedback,
            "status": result.status or "critic_audited",
        }
    )
    return _apply_failure_policy(state, "critic_auditor", result, update)


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
    _record_events(update, _audit_result("validation", result, request))
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
    return _apply_failure_policy(state, "validation", result, update)


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
    _record_events(update, _audit_result("debugger", result, request))
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
    return _apply_failure_policy(state, "debugger", result, update)


def item_router(state: WorkflowState) -> WorkflowState:
    """Prepare the decision to start another item or finish the workflow."""

    return {
        "status": (
            "next_item_ready"
            if select_next_item(state) is not None
            else "github_handoff_ready"
        )
    }


def pre_commit_policy_gate(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Read-only check for high-risk paths or leaked secrets before commit."""

    repository = dependencies.repository
    if state.get("commit_sha"):
        return {"status": "policy_gate_passed", "policy_gate_passed": True}
    if repository is None:
        return {"status": "policy_gate_skipped", "policy_gate_passed": True}

    item_id = state.get("current_item_id", "")
    item_title = state.get("current_item_title", "")
    files_touched = list(state.get("files_touched_by_item", {}).get(item_id, []))
    result = repository.policy_gate(item_id, item_title, files_touched)
    update = state_update_from_result(result)
    _record_events(update, _audit_result("pre_commit_policy_gate", result))
    update["policy_gate_passed"] = result.status == "policy_gate_passed"
    return _apply_failure_policy(state, "pre_commit_policy_gate", result, update)


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

    item_title = state.get("current_item_title", "")
    files_touched = list(state.get("files_touched_by_item", {}).get(item_id, []))
    if is_dry_run():
        message = f"feat: {item_id} - {item_title}".strip()
        if isinstance(repository, PreviewRepositoryAdapter):
            result = repository.preview_commit_item(item_id, item_title, files_touched)
        else:
            result = AgentResult(
                status="commit_preview",
                assigned_model=str(getattr(repository, "model_name", "repository")),
                files_touched=files_touched,
                feedback=f"Dry-run: would commit {message}.",
                commands=[
                    ["git", "add", "--", *files_touched],
                    ["git", "commit", "--only", "-m", message, "--", *files_touched],
                ],
            )
    else:
        result = repository.commit_item(item_id, item_title, files_touched)
    update = state_update_from_result(result)
    _record_events(update, _audit_result("commit_item", result))
    if result.failure_class:
        update["failure_node"] = "commit_item"
    return update


def push_node(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Request approval, then push the completed branch."""

    repository = dependencies.repository
    if state.get("pr_url"):
        return {
            "status": "pr_created",
            "pr_url": state["pr_url"],
        }
    if repository is None:
        return {"status": "complete"}

    if not _request_approval(
        action="push",
        question="Approve pushing the branch?",
        details={
            "operations": ["push"],
            "task": redact_secrets(state.get("task", "")),
        },
    ):
        return _approval_denied("push")

    if is_dry_run():
        branch = state.get("run_branch", "") or "<current branch>"
        if isinstance(repository, PreviewRepositoryAdapter):
            result = repository.preview_push_branch()
        else:
            result = AgentResult(
                status="branch_push_preview",
                assigned_model=str(getattr(repository, "model_name", "repository")),
                feedback=f"Dry-run: would push branch {branch}.",
                commands=[["git", "push", "-u", "origin", branch]],
            )
    else:
        result = repository.push_branch()
    update = state_update_from_result(result)
    _record_events(update, _audit_result("push_node", result))
    return _apply_failure_policy(state, "push_node", result, update)


def pull_request_node(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> WorkflowState:
    """Request approval, then open or reuse the pull request."""

    repository = dependencies.repository
    if state.get("pr_url"):
        return {
            "status": "pr_created",
            "pr_url": state["pr_url"],
        }
    if repository is None:
        return {"status": "complete"}

    if not _request_approval(
        action="open_pull_request",
        question="Approve opening the pull request?",
        details={
            "operations": ["open_pull_request"],
            "task": redact_secrets(state.get("task", "")),
        },
    ):
        return _approval_denied("opening a pull request")

    task = state.get("task", "")
    branch = state.get("run_branch", "")
    if is_dry_run():
        title = f"feat: {redact_secrets(' '.join(task.split()))}".strip()
        if isinstance(repository, PreviewRepositoryAdapter):
            result = repository.preview_open_pull_request(task, branch=branch)
        else:
            result = AgentResult(
                status="pull_request_preview",
                assigned_model=str(getattr(repository, "model_name", "repository")),
                feedback=(
                    "Dry-run: would inspect the branch pull request and create or "
                    "reconcile it."
                ),
                commands=[
                    [
                        "gh",
                        "pr",
                        "create",
                        "--base",
                        "main",
                        "--head",
                        branch or "<current branch>",
                        "--title",
                        title,
                    ]
                ],
                pr_state="preview",
            )
    else:
        result = repository.open_pull_request(task, branch=branch)
    update = state_update_from_result(result)
    _record_events(update, _audit_result("pull_request_node", result))
    return _apply_failure_policy(state, "pull_request_node", result, update)


def attempt_limit(state: WorkflowState) -> WorkflowState:
    """Stop safely when an item needs more build attempts than allowed."""

    return {
        "status": "attempt_limit_reached",
        "last_error": state.get(
            "last_error",
            f"Maximum build attempts reached ({state.get('max_attempts', 3)}).",
        ),
    }


def retry_backoff(state: WorkflowState) -> WorkflowState:
    """Wait between safe retries without retrying side-effecting operations."""

    delay = state.get("retry_delay_seconds", 0.0)
    if isinstance(delay, (int, float)) and not isinstance(delay, bool) and delay > 0:
        time.sleep(delay)
    return {
        "status": "retrying",
        "retry_delay_seconds": 0.0,
    }


def failed_build(state: WorkflowState) -> WorkflowState:
    """Stop safely when the builder fails after its retries are exhausted."""

    return {
        "status": "failed",
        "last_error": state.get("last_error") or "Build failed.",
        "build_completed": False,
    }


def failed_run(state: WorkflowState) -> WorkflowState:
    """Stop safely after a non-build agent failure cannot be retried."""

    return {
        "status": "failed",
        "last_error": state.get("last_error") or "Workflow step failed.",
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

    failure_class = _exception_failure_class(error.error)
    update: WorkflowState = {
        "status": "failed",
        "last_error": str(error.error),
        "failure_class": failure_class,
        "failure_node": "building",
        "build_completed": False,
    }
    _record_events(
        update,
        run_manifest_event(
            "agent_error",
            node="building",
            failure_class=failure_class,
            error=str(error.error),
        ),
    )
    return Command(
        update=update,
        goto="failed_build",
    )


def agent_error_handler(
    state: WorkflowState,
    error: NodeError,
    node: str = "agent",
) -> Command:
    """Classify an exhausted non-build node exception and stop safely."""

    failure_class = _exception_failure_class(error.error)
    update: WorkflowState = {
        "status": "failed",
        "last_error": str(error.error),
        "failure_class": failure_class,
        "failure_node": node,
    }
    _record_events(
        update,
        run_manifest_event(
            "agent_error",
            node=node,
            failure_class=failure_class,
            error=str(error.error),
        ),
    )
    return Command(update=update, goto="failed_run")


def agent_error_handler_for(node: str):
    """Bind a graph node name while preserving LangGraph error injection."""

    def handle(state: WorkflowState, error: NodeError) -> Command:
        return agent_error_handler(state, error, node)

    return handle


def route_after_building(
    state: WorkflowState,
) -> Literal[
    "critic_auditor",
    "validation",
    "attempt_limit",
    "failed_build",
    "retry_backoff",
    "stop_run",
]:
    """Route code to review, validation, retry limiting, or failed-build stop."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if state.get("status") == "failed":
        if retryable_failure(state.get("failure_class")) and state.get(
            "attempts_count", 0
        ) >= state.get("max_attempts", 3):
            return "attempt_limit"
        return "failed_build"
    if state.get("critic_passed"):
        return "validation"
    if not state.get("build_completed") and state.get("attempts_count", 0) >= state.get(
        "max_attempts", 3
    ):
        return "attempt_limit"
    return "critic_auditor"


def route_after_planning(
    state: WorkflowState,
) -> Literal["building", "item_router", "retry_backoff", "failed_run", "stop_run"]:
    """Start the next item or send an already-complete run to the router."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if state.get("status") == "failed":
        return "failed_run"
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


def route_after_learning(
    state: WorkflowState,
) -> Literal["intake", "retry_backoff", "failed_run", "stop_run"]:
    """Retry transient learn failures without asking for a new mode."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if state.get("status") == "learning_failed":
        return "failed_run"
    return "intake"


def route_after_preflight(
    state: WorkflowState,
) -> Literal["intake", "retry_backoff", "__end__"]:
    """Enter intake only after preflight succeeds or is explicitly skipped."""

    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if _run_stopped(state) or state.get("status") == "preflight_failed":
        return "__end__"
    return "intake"


def route_after_critic(
    state: WorkflowState,
) -> Literal["building", "retry_backoff", "failed_run", "stop_run"]:
    """Retry transient review failures but never turn them into rebuilds."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if state.get("status") == "failed":
        return "failed_run"
    return "building"


def route_after_validation(
    state: WorkflowState,
) -> Literal[
    "debugger", "pre_commit_policy_gate", "retry_backoff", "failed_run", "stop_run"
]:
    """Send failures to debugging and successes to the pre-commit policy gate."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if not state.get("validation_passed"):
        if (
            state.get("status") == "failed"
            and state.get("failure_class") != "validation"
        ):
            return "failed_run"
        return "debugger"
    return "pre_commit_policy_gate"


def route_after_policy_gate(
    state: WorkflowState,
) -> Literal["commit_item", "failed_run", "stop_run"]:
    """Only let a commit proceed once the policy gate reports a clean pass."""

    if _run_stopped(state):
        return "stop_run"
    return "commit_item" if state.get("policy_gate_passed") else "failed_run"


def route_after_debugger(
    state: WorkflowState,
) -> Literal["planning", "retry_backoff", "failed_run", "stop_run"]:
    """Retry transient debugger failures without hiding permanent failures."""

    if _run_stopped(state):
        return "stop_run"
    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    if state.get("status") == "failed":
        return "failed_run"
    return "planning"


def route_after_retry_backoff(
    state: WorkflowState,
) -> Literal[
    "preflight",
    "learning",
    "planning",
    "building",
    "critic_auditor",
    "validation",
    "debugger",
    "push_node",
    "pull_request_node",
    "failed_run",
    "stop_run",
]:
    """Return to the exact safe node that classified the transient failure."""

    if _run_stopped(state):
        return "stop_run"
    target = state.get("retry_target")
    if target in _RETRYABLE_NODES:
        return target
    return "failed_run"


def route_after_commit(
    state: WorkflowState,
) -> Literal["item_router", "stop_run", "__end__"]:
    """Continue only when the validated item was committed or had no changes."""

    if _run_stopped(state):
        return "stop_run"
    return (
        "item_router"
        if state.get("status")
        in {"committed", "no_changes", "commit_skipped", "commit_preview"}
        else "__end__"
    )


def route_after_item_router(
    state: WorkflowState,
) -> Literal["planning", "push_node", "stop_run"]:
    """Start the next incomplete item or finish the workflow."""

    if _run_stopped(state):
        return "stop_run"
    return "planning" if select_next_item(state) is not None else "push_node"


def route_after_push(
    state: WorkflowState,
) -> Literal["pull_request_node", "retry_backoff", "__end__"]:
    """Route a successful push to its separately approved PR handoff."""

    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
    return (
        "pull_request_node"
        if state.get("status") in {"branch_pushed", "branch_push_preview"}
        else "__end__"
    )


def route_after_pull_request(
    state: WorkflowState,
) -> Literal["retry_backoff", "__end__"]:
    """Retry a transient pull-request failure instead of ending the run."""

    if state.get("status") == "retry_scheduled":
        return "retry_backoff"
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
    """Pause for human approval before every side effect."""

    if is_dry_run():
        return True
    if is_development_mode():
        message = (
            "Development mode is enabled, but human approval is still required "
            "before this side effect."
        )
    else:
        message = (
            "I don't have automatic permission because Shanks is not in "
            "development mode; explicit approval is required for this side "
            "effect."
        )

    prompt: dict[str, object] = {
        "type": "approval",
        "message": message,
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


def _with_drift(
    state: WorkflowState,
    dependencies: NodeDependencies,
) -> tuple[WorkflowState, list[dict[str, Any]]]:
    """Refresh the drift note, returning it plus its audit event to record."""

    check = getattr(dependencies.repository, "drift_report", None)
    if check is None:
        return state, []
    result = check()
    return {**state, "repo_drift": result.feedback}, [
        _audit_result("drift_check", result)
    ]


def _request_for(
    state: WorkflowState,
    item: PRDItem,
    item_id: str,
    *,
    instructions: str | None = None,
) -> AgentRequest:
    drift = state.get("repo_drift", "")
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
        context="\n\n".join(
            part
            for part in (
                f"Repository drift since this run started:\n{drift}" if drift else "",
                state.get("root_cause", ""),
            )
            if part
        ),
        working_directory=_state_workspace_directory(state),
        timeout_seconds=remaining_runtime_seconds(state),
    )


def _record_events(update: WorkflowState, *events: dict[str, Any]) -> WorkflowState:
    """Add audit events to a node update without dropping the earlier ones.

    `run_manifest` is an append-only channel, so a node returns only its own
    new events. Always go through here rather than assigning `run_manifest`
    directly: a plain `update["run_manifest"] = [...]` silently discards
    whatever the same node recorded before it.
    """

    if events:
        update["run_manifest"] = [*update.get("run_manifest", []), *events]
    return update


def _audit_result(
    node: str,
    result: AgentResult,
    request: AgentRequest | None = None,
) -> dict[str, Any]:
    """Capture one redacted agent or repository operation as an audit event."""

    details: dict[str, object] = {
        "node": node,
        "status": result.status,
        "model": result.assigned_model,
    }
    if result.failure_class:
        details["failure_class"] = result.failure_class
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
    if result.pr_state:
        details["pull_request_state"] = result.pr_state
        details["pull_request_stale"] = result.pr_stale
    if result.pr_reviewers:
        details["pull_request_reviewers"] = list(result.pr_reviewers)
    if result.pr_labels:
        details["pull_request_labels"] = list(result.pr_labels)
    return run_manifest_event("agent" if request else "repository", **details)


def _pull_request_id(url: str) -> str:
    """Extract the numeric or opaque ID at the end of a pull-request URL."""

    return url.rstrip("/").rsplit("/", 1)[-1] if "/pull/" in url else ""


def _redact_manifest_value(value: object) -> object:
    """Redact strings recursively before they enter persisted state."""

    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {str(key): _redact_manifest_value(item) for key, item in value.items()}
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
    "failed_run",
    "default_dependencies",
    "claude_opus_4_8_dependencies",
    "gpt_5_6_luna_dependencies",
    "push_node",
    "pull_request_node",
    "intake",
    "learning",
    "item_router",
    "attempt_limit",
    "agent_error_handler",
    "agent_error_handler_for",
    "build_error_handler",
    "planning",
    "preflight",
    "route_after_preflight",
    "route_after_intake",
    "route_after_learning",
    "route_after_building",
    "route_after_commit",
    "route_after_critic",
    "route_after_debugger",
    "route_after_push",
    "route_after_pull_request",
    "stop_run",
    "route_after_item_router",
    "route_after_retry_backoff",
    "route_after_validation",
    "retry_backoff",
    "select_next_item",
    "validation",
]
