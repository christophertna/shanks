"""Shared state types for the graph-engineering workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict, cast


CURRENT_STATE_SCHEMA_VERSION = 1


class PRDItem(TypedDict, total=False):
    """A single item that the workflow can build and validate."""

    id: str
    title: str
    description: str
    priority: int
    passes: bool
    validation: bool


class WorkflowState(TypedDict, total=False):
    """State shared by every graph node and persisted between retries."""

    state_schema_version: int
    task: str
    workflow_mode: Literal["learn", "implement"] | None
    plan: list[str]
    prd_items: list[PRDItem]
    current_item_index: int
    current_item_id: str
    current_item_title: str
    builder_instructions: str
    files_touched: list[str]
    files_touched_by_item: dict[str, list[str]]
    uncertainties_by_item: dict[str, list[str]]
    attempts_count: int
    attempts_by_item: dict[str, int]
    max_attempts: int
    build_completed: bool
    last_error: str
    assigned_model: str
    critic_model: str
    critic_passed: bool
    critic_feedback: str
    validation_passed: bool
    validation_errors: list[str]
    debugger_model: str
    root_cause: str
    item_built: bool
    completed_items: list[str]
    learning_notes: str
    status: str
    commit_sha: str
    pr_url: str


class StateSchemaError(ValueError):
    """Raised when persisted state cannot be migrated safely."""


StateMigration = Callable[[dict[str, Any]], dict[str, Any]]


def _migrate_v0_to_v1(state: dict[str, Any]) -> dict[str, Any]:
    """Mark an unversioned legacy state as the first supported schema."""

    state["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
    return state


_STATE_MIGRATIONS: dict[int, StateMigration] = {
    0: _migrate_v0_to_v1,
}


def migrate_state(state: Mapping[str, Any]) -> WorkflowState:
    """Upgrade persisted state to the current schema without mutating it."""

    migrated = dict(state)
    raw_version = migrated.get("state_schema_version", 0)
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise StateSchemaError(
            "state_schema_version must be an integer; "
            f"got {raw_version!r}"
        )
    if raw_version < 0:
        raise StateSchemaError(
            f"state_schema_version cannot be negative: {raw_version}"
        )
    if raw_version > CURRENT_STATE_SCHEMA_VERSION:
        raise StateSchemaError(
            "state was written by a newer workflow version: "
            f"{raw_version} > {CURRENT_STATE_SCHEMA_VERSION}"
        )

    version = raw_version
    while version < CURRENT_STATE_SCHEMA_VERSION:
        migration = _STATE_MIGRATIONS.get(version)
        if migration is None:
            raise StateSchemaError(f"no migration registered for state v{version}")
        migrated = migration(migrated)
        next_version = migrated.get("state_schema_version")
        if not isinstance(next_version, int) or next_version <= version:
            raise StateSchemaError(
                f"migration from state v{version} did not advance the schema"
            )
        version = next_version

    return cast(WorkflowState, migrated)
