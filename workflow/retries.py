"""Failure classification and bounded retry helpers."""

from __future__ import annotations

import subprocess
from typing import Literal

FailureClass = Literal[
    "transient",
    "validation",
    "guardrail",
    "budget",
    "cancelled",
    "permanent",
]

RETRY_INITIAL_DELAY_SECONDS = 0.5
RETRY_BACKOFF_FACTOR = 2.0
RETRY_MAX_DELAY_SECONDS = 8.0

_GUARDRAIL_MARKERS = (
    "refusing to",
    "unapproved executable",
    "outside the configured",
    "outside the project",
    "path outside",
    "unsupported characters",
)
_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "temporarily unavailable",
    "service unavailable",
    "connection reset",
    "connection refused",
    "connection aborted",
    "network is unreachable",
    "rate limit",
    "too many requests",
    "try again",
    "server error",
    "database is locked",
    "status 429",
    "status 502",
    "status 503",
    "status 504",
)


def classify_failure(
    message: str | None = None,
    *,
    status: str = "",
    error: BaseException | None = None,
) -> FailureClass:
    """Classify a failure before deciding whether it is safe to retry."""

    normalized_status = status.strip().lower()
    normalized_message = (message or str(error or "")).strip().lower()

    if (
        normalized_status in {"cancelled", "canceled"}
        or "cancelled" in normalized_message
    ):
        return "cancelled"
    if normalized_status == "budget_exceeded" or "budget" in normalized_message:
        return "budget"
    if any(marker in normalized_message for marker in _GUARDRAIL_MARKERS):
        return "guardrail"
    if isinstance(
        error,
        (
            TimeoutError,
            ConnectionError,
            subprocess.TimeoutExpired,
        ),
    ):
        return "transient"
    if any(marker in normalized_message for marker in _TRANSIENT_MARKERS):
        return "transient"
    if normalized_status.startswith("validation") or normalized_status == "validation":
        return "validation"
    return "permanent"


def retryable_failure(failure_class: str | None) -> bool:
    """Return whether a classified failure is safe for an automatic retry."""

    return failure_class == "transient"


def retry_delay(retry_number: int) -> float:
    """Return a deterministic exponential delay for the next retry."""

    if retry_number <= 0:
        return 0.0
    return min(
        RETRY_MAX_DELAY_SECONDS,
        RETRY_INITIAL_DELAY_SECONDS * RETRY_BACKOFF_FACTOR ** (retry_number - 1),
    )


def retry_on_exception(error: Exception) -> bool:
    """Use the same classifier for LangGraph's native node retry policy."""

    return retryable_failure(classify_failure(error=error))


__all__ = [
    "FailureClass",
    "RETRY_BACKOFF_FACTOR",
    "RETRY_INITIAL_DELAY_SECONDS",
    "RETRY_MAX_DELAY_SECONDS",
    "classify_failure",
    "retry_delay",
    "retry_on_exception",
    "retryable_failure",
]
