"""Explicit execution modes for local development and normal runs."""

from __future__ import annotations

import os

RUNTIME_MODE = "runtime"
DEVELOPMENT_MODE = "development"


def execution_mode() -> str:
    """Return the configured mode, failing closed for unknown values."""

    value = os.environ.get("SHANKS_MODE", RUNTIME_MODE).strip().lower()
    return value if value in {RUNTIME_MODE, DEVELOPMENT_MODE} else RUNTIME_MODE


def is_development_mode() -> bool:
    """Return whether local development side effects are explicitly enabled."""

    return execution_mode() == DEVELOPMENT_MODE
