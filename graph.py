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
    build_error_handler,
    create_nodes,
    default_dependencies,
    route_after_building,
    route_after_commit,
    route_after_github,
    route_after_intake,
    route_after_item_router,
    route_after_planning,
    route_after_validation,
)
from workflow.state import WorkflowState, migrate_state


DEFAULT_CHECKPOINT_DB = Path(__file__).resolve().parent / ".shanks" / "checkpoints.sqlite"


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
):
    """Build the workflow with optional adapters or a Claude/Codex choice."""

    nodes = create_nodes(
        dependencies or default_dependencies(tool=tool)
    )
    builder = StateGraph(WorkflowState)
    builder.add_node("intake", nodes["intake"])
    builder.add_node("learning", nodes["learning"])
    builder.add_node("planning", nodes["planning"])
    builder.add_node("critic_auditor", nodes["critic_auditor"])
    builder.add_node(
        "building",
        nodes["building"],
        retry_policy=RetryPolicy(),
        error_handler=build_error_handler,
    )
    builder.add_node("failed_build", nodes["failed_build"])
    # The viewer renders the validation decision node as a diamond.
    builder.add_node("validation", nodes["validation"], metadata={"kind": "decision"})
    builder.add_node("commit_item", nodes["commit_item"])
    builder.add_node("debugger", nodes["debugger"])
    builder.add_node("item_router", nodes["item_router"])
    builder.add_node("github_node", nodes["github_node"])
    builder.add_node("attempt_limit", nodes["attempt_limit"])
    builder.add_node("stop_run", nodes["stop_run"])

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        ["learning", "planning", "stop_run"],
    )
    builder.add_edge("learning", "intake")
    builder.add_conditional_edges(
        "planning",
        route_after_planning,
        ["building", "item_router", "stop_run"],
    )
    builder.add_conditional_edges(
        "building",
        route_after_building,
        [
            "critic_auditor",
            "validation",
            "attempt_limit",
            "failed_build",
            "stop_run",
        ],
    )
    builder.add_edge("critic_auditor", "building")
    builder.add_conditional_edges(
        "validation",
        route_after_validation,
        ["debugger", "commit_item", "stop_run"],
    )
    builder.add_conditional_edges(
        "commit_item",
        route_after_commit,
        ["item_router", "stop_run", END],
    )
    builder.add_edge("debugger", "planning")
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
    builder.add_edge("attempt_limit", END)
    builder.add_edge("failed_build", END)
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
