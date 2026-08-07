"""Explicit execution modes for local development and normal runs."""

from __future__ import annotations

import os

RUNTIME_MODE = "runtime"
DEVELOPMENT_MODE = "development"
DRY_RUN_MODE = "dry-run"


def execution_mode() -> str:
    """Return the configured mode, failing closed for unknown values."""

    value = os.environ.get("SHANKS_MODE", RUNTIME_MODE).strip().lower()
    if value == "dry_run":
        value = DRY_RUN_MODE
    return (
        value
        if value in {RUNTIME_MODE, DEVELOPMENT_MODE, DRY_RUN_MODE}
        else RUNTIME_MODE
    )


def is_development_mode() -> bool:
    """Return whether local development side effects are explicitly enabled."""

    return execution_mode() == DEVELOPMENT_MODE


def is_dry_run() -> bool:
    """Return whether side-effecting delivery actions should be previewed."""

    return execution_mode() == DRY_RUN_MODE
