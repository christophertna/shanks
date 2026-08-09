"""Persistent run leases and lifecycle records."""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

TERMINAL_RUN_STATUSES = frozenset(
    {
        "complete",
        "pr_created",
        "pull_request_preview",
        "failed",
        "preflight_failed",
        "cancelled",
        "budget_exceeded",
        "attempt_limit_reached",
        "approval_denied",
    }
)
TERMINAL_LIFECYCLE_STATUSES = frozenset(
    {"complete", "failed", "cancelled", "abandoned"}
)


class RunBusyError(RuntimeError):
    """Raised when another live owner holds the run lease."""


class LeaseLostError(RuntimeError):
    """Raised when a process tries to heartbeat a lease it no longer owns."""


@dataclass(frozen=True, slots=True)
class RunLease:
    """The result of acquiring or renewing a run lease."""

    run_id: str
    owner_id: str
    acquired_at: float
    heartbeat_at: float
    expires_at: float
    recovered: bool = False
    recovery_count: int = 0
    previous_owner: str = ""


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Persisted lifecycle summary for a checkpoint thread."""

    run_id: str
    status: str
    started_at: float
    updated_at: float
    finished_at: float | None
    recovery_count: int
    last_error: str


@dataclass(slots=True)
class RunLifecycleManager:
    """Coordinate one active owner and durable status for each run."""

    conn: sqlite3.Connection
    lease_ttl_seconds: float = 3600.0
    owner_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _lock: threading.RLock = field(init=False, repr=False)
    _is_setup: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        if self.lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")
        if not self.owner_id:
            raise ValueError("owner_id must not be empty")
        self._lock = threading.RLock()

    @contextmanager
    def database_lock(self):
        """Serialize checkpoint and lifecycle transactions on this connection."""

        with self._lock:
            yield

    def acquire(self, run_id: str, *, now: float | None = None) -> RunLease:
        """Acquire or renew a lease, recovering it when its owner is stale."""

        if not run_id or not isinstance(run_id, str):
            raise ValueError("run_id must be a non-empty string")
        now = time.time() if now is None else now
        expires_at = now + self.lease_ttl_seconds
        with self._lock:
            self._setup()
            # LangGraph may leave a same-connection checkpoint write open while
            # resuming an interrupt; make it durable before taking the lease.
            if self.conn.in_transaction:
                self.conn.commit()
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute(
                    """
                    SELECT owner_id, acquired_at, heartbeat_at, expires_at,
                           recovery_count
                    FROM run_leases
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchone()
                if row and row[0] != self.owner_id and row[3] > now:
                    self.conn.rollback()
                    raise RunBusyError(f"run {run_id!r} is active until {row[3]:.3f}")

                recovered = bool(row and row[0] != self.owner_id)
                previous_owner = row[0] if recovered else ""
                recovery_count = (int(row[4]) if row else 0) + int(recovered)
                acquired_at = float(row[1]) if row and not recovered else now
                self.conn.execute(
                    """
                    INSERT INTO run_leases(
                        run_id, owner_id, acquired_at, heartbeat_at, expires_at,
                        recovery_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        owner_id = excluded.owner_id,
                        acquired_at = excluded.acquired_at,
                        heartbeat_at = excluded.heartbeat_at,
                        expires_at = excluded.expires_at,
                        recovery_count = excluded.recovery_count
                    """,
                    (
                        run_id,
                        self.owner_id,
                        acquired_at,
                        now,
                        expires_at,
                        recovery_count,
                    ),
                )
                if recovered:
                    self.conn.execute(
                        """
                        UPDATE run_records
                        SET status = 'abandoned', updated_at = ?,
                            last_error = 'Lease expired before recovery.'
                        WHERE run_id = ?
                        """,
                        (now, run_id),
                    )
                self._upsert_record(
                    run_id,
                    status="running",
                    now=now,
                    recovery_count=recovery_count,
                    finished_at=None,
                    last_error=(
                        "Recovered an abandoned run lease." if recovered else ""
                    ),
                )
                self.conn.commit()
            except Exception:
                if self.conn.in_transaction:
                    self.conn.rollback()
                raise

        return RunLease(
            run_id=run_id,
            owner_id=self.owner_id,
            acquired_at=acquired_at,
            heartbeat_at=now,
            expires_at=expires_at,
            recovered=recovered,
            recovery_count=recovery_count,
            previous_owner=previous_owner,
        )

    def heartbeat(self, run_id: str, *, now: float | None = None) -> RunLease:
        """Extend the current owner's lease before another node runs."""

        now = time.time() if now is None else now
        expires_at = now + self.lease_ttl_seconds
        with self._lock:
            self._setup()
            result = self.conn.execute(
                """
                UPDATE run_leases
                SET heartbeat_at = ?, expires_at = ?
                WHERE run_id = ? AND owner_id = ?
                """,
                (now, expires_at, run_id, self.owner_id),
            )
            if result.rowcount != 1:
                raise LeaseLostError(f"lease for run {run_id!r} is no longer owned")
            self._upsert_record(
                run_id,
                status="running",
                now=now,
                recovery_count=self._recovery_count(run_id),
                finished_at=None,
                last_error="",
            )
            self.conn.commit()
            row = self.conn.execute(
                "SELECT acquired_at, recovery_count FROM run_leases WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return RunLease(
            run_id,
            self.owner_id,
            float(row[0]) if row else now,
            now,
            expires_at,
            recovery_count=int(row[1]) if row else 0,
        )

    def mark_interrupted(self, run_id: str, *, now: float | None = None) -> None:
        """Record a pause caused by a human interrupt while keeping the lease."""

        now = time.time() if now is None else now
        with self._lock:
            self._setup()
            self.conn.execute(
                """
                UPDATE run_leases
                SET heartbeat_at = ?, expires_at = ?
                WHERE run_id = ? AND owner_id = ?
                """,
                (now, now + self.lease_ttl_seconds, run_id, self.owner_id),
            )
            self._upsert_record(
                run_id,
                status="interrupted",
                now=now,
                recovery_count=self._recovery_count(run_id),
                finished_at=None,
                last_error="Run paused at an interrupt; resume before the lease expires.",
            )
            self.conn.commit()

    def release(
        self,
        run_id: str,
        *,
        status: str = "complete",
        last_error: str = "",
        now: float | None = None,
    ) -> bool:
        """Release the lease after its terminal checkpoint is persisted."""

        now = time.time() if now is None else now
        lifecycle_status = _lifecycle_status(status)
        with self._lock:
            self._setup()
            recovery_count = self._recovery_count(run_id)
            result = self.conn.execute(
                "DELETE FROM run_leases WHERE run_id = ? AND owner_id = ?",
                (run_id, self.owner_id),
            )
            if result.rowcount != 1:
                return False
            self._upsert_record(
                run_id,
                status=lifecycle_status,
                now=now,
                recovery_count=recovery_count,
                finished_at=now,
                last_error=last_error,
            )
            self.conn.commit()
            return True

    def recover_stale(self, *, now: float | None = None) -> int:
        """Mark expired leases as abandoned without taking ownership."""

        now = time.time() if now is None else now
        with self._lock:
            self._setup()
            rows = self.conn.execute(
                "SELECT run_id FROM run_leases WHERE expires_at <= ?",
                (now,),
            ).fetchall()
            for (run_id,) in rows:
                self.conn.execute(
                    """
                    UPDATE run_records
                    SET status = 'abandoned', updated_at = ?,
                        last_error = 'Lease expired; run was abandoned.'
                    WHERE run_id = ? AND status NOT IN (
                        'complete', 'failed', 'cancelled', 'blocked'
                    )
                    """,
                    (now, run_id),
                )
            self.conn.commit()
        return len(rows)

    def get_run(self, run_id: str) -> RunRecord | None:
        """Read a persisted lifecycle record."""

        with self._lock:
            self._setup()
            row = self.conn.execute(
                """
                SELECT run_id, status, started_at, updated_at, finished_at,
                       recovery_count, last_error
                FROM run_records WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return _record(row) if row else None

    def is_active(self, run_id: str, *, now: float | None = None) -> bool:
        """Return whether a live lease currently protects ``run_id``."""

        now = time.time() if now is None else now
        with self._lock:
            self._setup()
            row = self.conn.execute(
                "SELECT expires_at FROM run_leases WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return bool(row and float(row[0]) > now)

    def list_runs(self, *, now: float | None = None) -> list[RunRecord]:
        """Return lifecycle records, marking expired active runs first."""

        self.recover_stale(now=now)
        with self._lock:
            rows = self.conn.execute("""
                SELECT run_id, status, started_at, updated_at, finished_at,
                       recovery_count, last_error
                FROM run_records ORDER BY updated_at DESC
                """).fetchall()
        return [_record(row) for row in rows]

    def cleanup(
        self,
        *,
        max_age_seconds: float,
        run_id: str | None = None,
        now: float | None = None,
    ) -> int:
        """Delete old terminal or abandoned lifecycle records and leases."""

        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        now = time.time() if now is None else now
        self.recover_stale(now=now)
        cutoff = now - max_age_seconds
        with self._lock:
            query = """
                SELECT run_id FROM run_records
                WHERE updated_at < ? AND status IN (
                    'complete', 'failed', 'cancelled', 'abandoned'
                )
            """
            params: tuple[object, ...] = (cutoff,)
            if run_id is not None:
                query += " AND run_id = ?"
                params += (run_id,)
            rows = self.conn.execute(query, params).fetchall()
            for (run_id,) in rows:
                self.conn.execute("DELETE FROM run_leases WHERE run_id = ?", (run_id,))
                self.conn.execute("DELETE FROM run_records WHERE run_id = ?", (run_id,))
            self.conn.commit()
        return len(rows)

    def _setup(self) -> None:
        if self._is_setup:
            return
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS run_leases (
                run_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                acquired_at REAL NOT NULL,
                heartbeat_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                recovery_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS run_records (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                started_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                finished_at REAL,
                recovery_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT ''
            );
            """)
        self._is_setup = True

    def _recovery_count(self, run_id: str) -> int:
        row = self.conn.execute(
            "SELECT recovery_count FROM run_leases WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def _upsert_record(
        self,
        run_id: str,
        *,
        status: str,
        now: float,
        recovery_count: int,
        finished_at: float | None,
        last_error: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO run_records(
                run_id, status, started_at, updated_at, finished_at,
                recovery_count, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                finished_at = excluded.finished_at,
                recovery_count = excluded.recovery_count,
                last_error = excluded.last_error
            """,
            (
                run_id,
                status,
                now,
                now,
                finished_at,
                recovery_count,
                last_error,
            ),
        )


def _lifecycle_status(status: str) -> str:
    if status in {"complete", "pr_created", "pull_request_preview"}:
        return "complete"
    if status in {"cancelled", "budget_exceeded"}:
        return "cancelled"
    if status == "run_locked":
        return "blocked"
    return "failed"


def _record(row: tuple[object, ...]) -> RunRecord:
    return RunRecord(
        run_id=str(row[0]),
        status=str(row[1]),
        started_at=float(row[2]),
        updated_at=float(row[3]),
        finished_at=float(row[4]) if row[4] is not None else None,
        recovery_count=int(row[5]),
        last_error=str(row[6] or ""),
    )


__all__ = [
    "LeaseLostError",
    "RunBusyError",
    "RunLease",
    "RunLifecycleManager",
    "RunRecord",
    "TERMINAL_LIFECYCLE_STATUSES",
    "TERMINAL_RUN_STATUSES",
]
