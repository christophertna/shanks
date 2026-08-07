"""Shared state types for the graph-engineering workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict, cast

CURRENT_STATE_SCHEMA_VERSION = 6
DEFAULT_MAX_RUNTIME_SECONDS = 3600.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MAX_TOTAL_ATTEMPTS = 20
DEFAULT_MAX_TOKENS = 100_000
DEFAULT_MAX_COST_USD = 0.0


class PRDItem(TypedDict, total=False):
    """A single item that the workflow can build and validate."""

    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    validation_command: str
    # These aliases are accepted when loading the Ralph JSON representation.
    acceptanceCriteria: list[str]
    validationCommand: str
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
    total_attempts: int
    max_total_attempts: int
    run_started_at: float
    max_runtime_seconds: float
    last_input_tokens: int
    last_output_tokens: int
    last_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    max_tokens: int
    total_cost_usd: float
    max_cost_usd: float
    cancel_requested: bool
    cancel_reason: str
    run_manifest: list[dict[str, Any]]
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
    failure_class: str
    failure_node: str
    retry_counts: dict[str, int]
    retry_target: str
    retry_delay_seconds: float
    commit_sha: str
    pr_url: str
    run_id: str
    run_branch: str
    workspace_directory: str
    run_lifecycle_status: str
    run_lease_expires_at: float
    run_last_heartbeat_at: float
    run_recovery_count: int


class StateSchemaError(ValueError):
    """Raised when persisted state cannot be migrated safely."""


StateMigration = Callable[[dict[str, Any]], dict[str, Any]]


def acceptance_criteria_for_item(item: Mapping[str, Any]) -> list[str]:
    """Read acceptance criteria from either Python or Ralph PRD field names."""

    criteria = item.get("acceptance_criteria")
    if criteria is None:
        criteria = item.get("acceptanceCriteria", [])
    if not isinstance(criteria, (list, tuple)):
        return []
    return [
        value.strip() for value in criteria if isinstance(value, str) and value.strip()
    ]


def validation_command_for_item(item: Mapping[str, Any]) -> str:
    """Read an optional per-item validation command from a PRD item."""

    command = item.get("validation_command")
    if command is None:
        command = item.get("validationCommand", "")
    return command.strip() if isinstance(command, str) else ""


def _migrate_v0_to_v1(state: dict[str, Any]) -> dict[str, Any]:
    """Mark an unversioned legacy state as the first supported schema."""

    state["state_schema_version"] = 1
    return state


def _migrate_v1_to_v2(state: dict[str, Any]) -> dict[str, Any]:
    """Add run budgets and clean-cancellation fields to persisted state."""

    state.setdefault("max_attempts", DEFAULT_MAX_ATTEMPTS)
    state.setdefault("max_total_attempts", DEFAULT_MAX_TOTAL_ATTEMPTS)
    state.setdefault("max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS)
    state.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
    state.setdefault("max_cost_usd", DEFAULT_MAX_COST_USD)
    state.setdefault("total_attempts", 0)
    state.setdefault("last_input_tokens", 0)
    state.setdefault("last_output_tokens", 0)
    state.setdefault("last_cost_usd", 0.0)
    state.setdefault("total_input_tokens", 0)
    state.setdefault("total_output_tokens", 0)
    state.setdefault("total_tokens", 0)
    state.setdefault("total_cost_usd", 0.0)
    state.setdefault("cancel_requested", False)
    state.setdefault("cancel_reason", "")
    state["state_schema_version"] = 2
    return state


def _migrate_v2_to_v3(state: dict[str, Any]) -> dict[str, Any]:
    """Add the persisted run manifest and audit history."""

    state.setdefault("run_manifest", [])
    state["state_schema_version"] = 3
    return state


def _migrate_v3_to_v4(state: dict[str, Any]) -> dict[str, Any]:
    """Add failure classification and targeted retry fields."""

    state.setdefault("failure_class", "")
    state.setdefault("failure_node", "")
    state.setdefault("retry_counts", {})
    state.setdefault("retry_target", "")
    state.setdefault("retry_delay_seconds", 0.0)
    state["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
    return state


def _migrate_v4_to_v5(state: dict[str, Any]) -> dict[str, Any]:
    """Add the persisted run identity and isolated workspace fields."""

    state.setdefault("run_id", "")
    state.setdefault("run_branch", "")
    state.setdefault("workspace_directory", "")
    state["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
    return state


def _migrate_v5_to_v6(state: dict[str, Any]) -> dict[str, Any]:
    """Add persisted run lease and recovery metadata."""

    state.setdefault("run_lifecycle_status", "")
    state.setdefault("run_lease_expires_at", 0.0)
    state.setdefault("run_last_heartbeat_at", 0.0)
    state.setdefault("run_recovery_count", 0)
    state["state_schema_version"] = CURRENT_STATE_SCHEMA_VERSION
    return state


_STATE_MIGRATIONS: dict[int, StateMigration] = {
    0: _migrate_v0_to_v1,
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
    4: _migrate_v4_to_v5,
    5: _migrate_v5_to_v6,
}


def append_run_manifest(
    state: WorkflowState,
    event_type: str,
    **details: Any,
) -> WorkflowState:
    """Append one timestamped, persisted audit event to the current run."""

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **details,
    }
    return {
        "run_manifest": [
            *state.get("run_manifest", []),
            event,
        ]
    }


def cancel_run(reason: str = "Cancelled by user.") -> WorkflowState:
    """Return a state update that asks the workflow to stop cleanly."""

    message = reason.strip() or "Cancelled by user."
    return {
        "cancel_requested": True,
        "cancel_reason": message,
        "status": "cancelled",
        "run_lifecycle_status": "cancelled",
        "last_error": message,
    }


def migrate_state(state: Mapping[str, Any]) -> WorkflowState:
    """Upgrade persisted state to the current schema without mutating it."""

    migrated = dict(state)
    raw_version = migrated.get("state_schema_version", 0)
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise StateSchemaError(
            "state_schema_version must be an integer; " f"got {raw_version!r}"
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

    migrated.setdefault("run_manifest", [])
    migrated.setdefault("failure_class", "")
    migrated.setdefault("failure_node", "")
    migrated.setdefault("retry_counts", {})
    migrated.setdefault("retry_target", "")
    migrated.setdefault("retry_delay_seconds", 0.0)
    migrated.setdefault("run_id", "")
    migrated.setdefault("run_branch", "")
    migrated.setdefault("workspace_directory", "")
    migrated.setdefault("run_lifecycle_status", "")
    migrated.setdefault("run_lease_expires_at", 0.0)
    migrated.setdefault("run_last_heartbeat_at", 0.0)
    migrated.setdefault("run_recovery_count", 0)
    return cast(WorkflowState, migrated)
