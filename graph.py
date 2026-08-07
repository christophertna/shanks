"""LangGraph workflow assembled from standardized agent nodes."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from workflow.nodes import (
    NodeDependencies,
    agent_error_handler_for,
    build_error_handler,
    create_nodes,
    default_dependencies,
    route_after_building,
    route_after_commit,
    route_after_critic,
    route_after_debugger,
    route_after_github,
    route_after_intake,
    route_after_item_router,
    route_after_learning,
    route_after_planning,
    route_after_preflight,
    route_after_retry_backoff,
    route_after_validation,
)
from workflow.retries import (
    RETRY_BACKOFF_FACTOR,
    RETRY_INITIAL_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
    retry_on_exception,
)
from workflow.state import DEFAULT_MAX_ATTEMPTS, WorkflowState, migrate_state
from workflow.workspaces import RunWorkspaceManager

DEFAULT_CHECKPOINT_DB = (
    Path(__file__).resolve().parent / ".shanks" / "checkpoints.sqlite"
)
TARGETED_RETRY_POLICY = RetryPolicy(
    initial_interval=RETRY_INITIAL_DELAY_SECONDS,
    backoff_factor=RETRY_BACKOFF_FACTOR,
    max_interval=RETRY_MAX_DELAY_SECONDS,
    max_attempts=DEFAULT_MAX_ATTEMPTS,
    jitter=False,
    retry_on=retry_on_exception,
)


def _migrate_checkpoint_tuple(checkpoint_tuple):
    """Return a checkpoint tuple whose state channels use the current schema."""

    checkpoint = checkpoint_tuple.checkpoint
    channel_values = checkpoint.get("channel_values", {})
    migrated_values = migrate_state(channel_values)
    if migrated_values == channel_values:
        return checkpoint_tuple

    migrated_checkpoint = dict(checkpoint)
    migrated_checkpoint["channel_values"] = migrated_values
    return checkpoint_tuple._replace(checkpoint=migrated_checkpoint)


class VersionedSqliteSaver(SqliteSaver):
    """SqliteSaver that migrates workflow state on reads and writes."""

    def get_tuple(self, config):
        checkpoint_tuple = super().get_tuple(config)
        if checkpoint_tuple is None:
            return None
        return _migrate_checkpoint_tuple(checkpoint_tuple)

    def list(self, config=None, *, filter=None, before=None, limit=None):
        for checkpoint_tuple in super().list(
            config,
            filter=filter,
            before=before,
            limit=limit,
        ):
            yield _migrate_checkpoint_tuple(checkpoint_tuple)

    def put(self, config, checkpoint, metadata, new_versions):
        migrated_checkpoint = dict(checkpoint)
        migrated_checkpoint["channel_values"] = migrate_state(
            checkpoint.get("channel_values", {})
        )
        return super().put(
            config,
            migrated_checkpoint,
            metadata,
            new_versions,
        )


def shared_checkpointer() -> VersionedSqliteSaver:
    """Open the SQLite checkpoint store shared by workflow and viewer processes."""

    checkpoint_path = Path(
        os.environ.get("SHANKS_CHECKPOINT_DB", str(DEFAULT_CHECKPOINT_DB))
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    return VersionedSqliteSaver(connection)


def build_graph(
    dependencies: NodeDependencies | None = None,
    *,
    checkpointer=None,
    tool: Literal["claude", "codex"] = "codex",
    project_directory: Path | None = None,
    workspace_manager: RunWorkspaceManager | None = None,
    base_branch: str = "main",
    worktree_root: Path | None = None,
):
    """Build the workflow with optional adapters or a Claude/Codex choice."""

    nodes = create_nodes(
        dependencies
        or default_dependencies(
            tool=tool,
            project_directory=project_directory,
            workspace_manager=workspace_manager,
            base_branch=base_branch,
            worktree_root=worktree_root,
        )
    )
    builder = StateGraph(WorkflowState)
    builder.add_node(
        "preflight",
        nodes["preflight"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("preflight"),
    )
    builder.add_node("intake", nodes["intake"])
    builder.add_node(
        "learning",
        nodes["learning"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("learning"),
    )
    builder.add_node(
        "planning",
        nodes["planning"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("planning"),
    )
    builder.add_node(
        "critic_auditor",
        nodes["critic_auditor"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("critic_auditor"),
    )
    builder.add_node(
        "building",
        nodes["building"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=build_error_handler,
    )
    builder.add_node("failed_build", nodes["failed_build"])
    builder.add_node("failed_run", nodes["failed_run"])
    # The viewer renders the validation decision node as a diamond.
    builder.add_node(
        "validation",
        nodes["validation"],
        metadata={"kind": "decision"},
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("validation"),
    )
    builder.add_node("commit_item", nodes["commit_item"])
    builder.add_node(
        "debugger",
        nodes["debugger"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("debugger"),
    )
    builder.add_node("item_router", nodes["item_router"])
    builder.add_node("github_node", nodes["github_node"])
    builder.add_node("retry_backoff", nodes["retry_backoff"])
    builder.add_node("attempt_limit", nodes["attempt_limit"])
    builder.add_node("stop_run", nodes["stop_run"])

    builder.add_edge(START, "preflight")
    builder.add_conditional_edges(
        "preflight",
        route_after_preflight,
        ["intake", "retry_backoff", END],
    )
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        ["learning", "planning", "stop_run"],
    )
    builder.add_conditional_edges(
        "learning",
        route_after_learning,
        ["intake", "retry_backoff", "failed_run", "stop_run"],
    )
    builder.add_conditional_edges(
        "planning",
        route_after_planning,
        ["building", "item_router", "retry_backoff", "failed_run", "stop_run"],
    )
    builder.add_conditional_edges(
        "building",
        route_after_building,
        [
            "critic_auditor",
            "validation",
            "attempt_limit",
            "failed_build",
            "retry_backoff",
            "stop_run",
        ],
    )
    builder.add_conditional_edges(
        "critic_auditor",
        route_after_critic,
        ["building", "retry_backoff", "failed_run", "stop_run"],
    )
    builder.add_conditional_edges(
        "validation",
        route_after_validation,
        ["debugger", "commit_item", "retry_backoff", "failed_run", "stop_run"],
    )
    builder.add_conditional_edges(
        "commit_item",
        route_after_commit,
        ["item_router", "stop_run", END],
    )
    builder.add_conditional_edges(
        "debugger",
        route_after_debugger,
        ["planning", "retry_backoff", "failed_run", "stop_run"],
    )
    builder.add_conditional_edges(
        "item_router",
        route_after_item_router,
        ["planning", "github_node", "stop_run"],
    )
    builder.add_conditional_edges(
        "github_node",
        route_after_github,
        [END],
    )
    builder.add_conditional_edges(
        "retry_backoff",
        route_after_retry_backoff,
        [
            "preflight",
            "learning",
            "planning",
            "building",
            "critic_auditor",
            "validation",
            "debugger",
            "failed_run",
            "stop_run",
        ],
    )
    builder.add_edge("attempt_limit", END)
    builder.add_edge("failed_build", END)
    builder.add_edge("failed_run", END)
    builder.add_edge("stop_run", END)

    return builder.compile(
        checkpointer=checkpointer if checkpointer is not None else shared_checkpointer()
    )


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke(
        {"task": "Build a simple workflow"},
        config={"configurable": {"thread_id": "cli-demo"}},
    )
    print(result)
