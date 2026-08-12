"""LangGraph workflow assembled from standardized agent nodes."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
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
    route_after_pull_request,
    route_after_retry_backoff,
    route_after_validation,
)
from workflow.retries import (
    RETRY_BACKOFF_FACTOR,
    RETRY_INITIAL_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
    retry_on_exception,
)
from workflow.lifecycle import (
    RunLifecycleManager,
    TERMINAL_RUN_STATUSES,
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
DEFAULT_CHECKPOINT_RETENTION = 100


@dataclass(frozen=True, slots=True)
class CheckpointCleanup:
    """Counts returned by checkpoint retention cleanup."""

    threads_scanned: int
    checkpoints_deleted: int
    writes_deleted: int


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

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        lifecycle_manager: RunLifecycleManager | None = None,
        retention_limit: int = DEFAULT_CHECKPOINT_RETENTION,
        retention_seconds: float | None = None,
    ) -> None:
        super().__init__(conn)
        if retention_limit < 1:
            raise ValueError("retention_limit must be at least one")
        if retention_seconds is not None and retention_seconds < 0:
            raise ValueError("retention_seconds cannot be negative")
        self.lifecycle_manager = lifecycle_manager or RunLifecycleManager(conn)
        self.retention_limit = retention_limit
        self.retention_seconds = retention_seconds

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
        with self.lifecycle_manager.database_lock():
            saved_config = super().put(
                config,
                migrated_checkpoint,
                metadata,
                new_versions,
            )
            thread_id = str(config["configurable"]["thread_id"])
            values = migrated_checkpoint["channel_values"]
            status = values.get("status", "")
            if status in TERMINAL_RUN_STATUSES:
                self.lifecycle_manager.release(
                    thread_id,
                    status=status,
                    last_error=str(values.get("last_error", "")),
                )
                self.cleanup(
                    thread_id=thread_id,
                    max_age_seconds=self.retention_seconds,
                )
        return saved_config

    def put_writes(self, config, writes, task_id, task_path=""):
        with self.lifecycle_manager.database_lock():
            return super().put_writes(config, writes, task_id, task_path)

    def cleanup(
        self,
        *,
        keep_latest: int | None = None,
        max_age_seconds: float | None = None,
        terminal_only: bool = True,
        thread_id: str | None = None,
        now: float | None = None,
    ) -> CheckpointCleanup:
        with self.lifecycle_manager.database_lock():
            return self._cleanup(
                keep_latest=keep_latest,
                max_age_seconds=max_age_seconds,
                terminal_only=terminal_only,
                thread_id=thread_id,
                now=now,
            )

    def _cleanup(
        self,
        *,
        keep_latest: int | None = None,
        max_age_seconds: float | None = None,
        terminal_only: bool = True,
        thread_id: str | None = None,
        now: float | None = None,
    ) -> CheckpointCleanup:
        """Retain recent checkpoints and delete their associated writes."""

        keep_latest = self.retention_limit if keep_latest is None else keep_latest
        if isinstance(keep_latest, bool) or keep_latest < 1:
            raise ValueError("keep_latest must be at least one")
        if max_age_seconds is not None and max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        now = _now() if now is None else now
        cutoff = now - max_age_seconds if max_age_seconds is not None else None

        groups = self._checkpoint_groups(thread_id)
        deleted_checkpoints = 0
        deleted_writes = 0
        for current_thread_id, checkpoint_ns in groups:
            config = {
                "configurable": {
                    "thread_id": current_thread_id,
                    "checkpoint_ns": checkpoint_ns,
                }
            }
            checkpoints = sorted(
                list(self.list(config)),
                key=lambda item: _checkpoint_timestamp(item.checkpoint),
                reverse=True,
            )
            if not checkpoints:
                continue
            latest_values = checkpoints[0].checkpoint.get("channel_values", {})
            if (
                terminal_only
                and latest_values.get("status") not in TERMINAL_RUN_STATUSES
            ):
                continue

            remove = []
            for checkpoint in checkpoints[keep_latest:]:
                timestamp = _checkpoint_timestamp(checkpoint.checkpoint)
                if cutoff is None or (timestamp is not None and timestamp < cutoff):
                    remove.append(checkpoint.config["configurable"]["checkpoint_id"])
            if not remove:
                continue
            with self.cursor() as cursor:
                placeholders = ",".join("?" for _ in remove)
                params = (current_thread_id, checkpoint_ns, *remove)
                cursor.execute(
                    f"DELETE FROM writes WHERE thread_id = ? AND checkpoint_ns = ? "
                    f"AND checkpoint_id IN ({placeholders})",
                    params,
                )
                deleted_writes += cursor.rowcount
                cursor.execute(
                    f"DELETE FROM checkpoints WHERE thread_id = ? "
                    f"AND checkpoint_ns = ? AND checkpoint_id IN ({placeholders})",
                    params,
                )
                deleted_checkpoints += cursor.rowcount

        return CheckpointCleanup(
            threads_scanned=len(groups),
            checkpoints_deleted=deleted_checkpoints,
            writes_deleted=deleted_writes,
        )

    cleanup_checkpoints = cleanup

    def _checkpoint_groups(self, thread_id: str | None) -> list[tuple[str, str]]:
        with self.cursor(transaction=False) as cursor:
            try:
                if thread_id is None:
                    cursor.execute(
                        "SELECT DISTINCT thread_id, checkpoint_ns FROM checkpoints"
                    )
                else:
                    cursor.execute(
                        """
                        SELECT DISTINCT thread_id, checkpoint_ns FROM checkpoints
                        WHERE thread_id = ?
                        """,
                        (thread_id,),
                    )
            except sqlite3.OperationalError as error:
                if "no such table: checkpoints" not in str(error):
                    raise
                return []
            return [(str(row[0]), str(row[1])) for row in cursor.fetchall()]


def shared_checkpointer() -> VersionedSqliteSaver:
    """Open the SQLite checkpoint store shared by workflow and viewer processes."""

    checkpoint_path = Path(
        os.environ.get("SHANKS_CHECKPOINT_DB", str(DEFAULT_CHECKPOINT_DB))
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
    lifecycle = RunLifecycleManager(
        connection,
        lease_ttl_seconds=_env_float("SHANKS_RUN_LEASE_SECONDS", 3600.0),
    )
    return VersionedSqliteSaver(
        connection,
        lifecycle_manager=lifecycle,
        retention_limit=_env_int(
            "SHANKS_CHECKPOINT_RETENTION",
            DEFAULT_CHECKPOINT_RETENTION,
        ),
    )


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

    if checkpointer is None:
        checkpointer = shared_checkpointer()
    lifecycle_manager = getattr(checkpointer, "lifecycle_manager", None)
    nodes = create_nodes(
        dependencies
        or default_dependencies(
            tool=tool,
            project_directory=project_directory,
            workspace_manager=workspace_manager,
            base_branch=base_branch,
            worktree_root=worktree_root,
            lifecycle_manager=lifecycle_manager,
        )
    )
    builder = StateGraph(WorkflowState)
    builder.add_node(
        "preflight",
        nodes["preflight"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("preflight"),
    )
    builder.add_node(
        "intake",
        nodes["intake"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("intake"),
    )
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
    builder.add_node(
        "failed_build",
        nodes["failed_build"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("failed_build"),
    )
    builder.add_node(
        "failed_run",
        nodes["failed_run"],
        retry_policy=TARGETED_RETRY_POLICY,
        # No error_handler: agent_error_handler always routes exhausted
        # retries to "failed_run", which would self-loop this node forever.
    )
    # The viewer renders the validation decision node as a diamond.
    builder.add_node(
        "validation",
        nodes["validation"],
        metadata={"kind": "decision"},
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("validation"),
    )
    builder.add_node(
        "commit_item",
        nodes["commit_item"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("commit_item"),
    )
    builder.add_node(
        "debugger",
        nodes["debugger"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("debugger"),
    )
    builder.add_node(
        "item_router",
        nodes["item_router"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("item_router"),
    )
    builder.add_node(
        "github_node",
        nodes["github_node"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("github_node"),
    )
    builder.add_node(
        "pull_request_node",
        nodes["pull_request_node"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("pull_request_node"),
    )
    builder.add_node(
        "retry_backoff",
        nodes["retry_backoff"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("retry_backoff"),
    )
    builder.add_node(
        "attempt_limit",
        nodes["attempt_limit"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("attempt_limit"),
    )
    builder.add_node(
        "stop_run",
        nodes["stop_run"],
        retry_policy=TARGETED_RETRY_POLICY,
        error_handler=agent_error_handler_for("stop_run"),
    )

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
        ["pull_request_node", "retry_backoff", END],
    )
    builder.add_conditional_edges(
        "pull_request_node",
        route_after_pull_request,
        ["retry_backoff", END],
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
            "github_node",
            "pull_request_node",
            "failed_run",
            "stop_run",
        ],
    )
    builder.add_edge("attempt_limit", END)
    builder.add_edge("failed_build", END)
    builder.add_edge("failed_run", END)
    builder.add_edge("stop_run", END)

    return builder.compile(checkpointer=checkpointer)


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _checkpoint_timestamp(checkpoint: dict) -> float:
    raw = checkpoint.get("ts")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return 0.0


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value >= 1 else default


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke(
        {"task": "Build a simple workflow"},
        config={"configurable": {"thread_id": "cli-demo"}},
    )
    print(result)
