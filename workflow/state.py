"""Shared state types for the graph-engineering workflow."""

from __future__ import annotations

from typing import Literal, TypedDict


class PRDItem(TypedDict, total=False):
    """A single item that the workflow can build and validate."""

    id: str
    title: str
    description: str
    priority: int
    passes: bool


class WorkflowState(TypedDict, total=False):
    """State shared by every graph node and persisted between retries."""

    task: str
    workflow_mode: Literal["learn", "implement"] | None
    plan: list[str]
    prd_items: list[PRDItem]
    current_item_index: int
    current_item_id: str
    current_item_title: str
    builder_instructions: str
    files_touched: list[str]
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
    completed_items: list[str]
    learning_notes: str
    status: str
