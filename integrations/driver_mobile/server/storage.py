"""Transactional SQLite storage for DebugLeaf driver mobile integration.

Corrects concurrency, idempotency, caller ownership, CAS route updates,
and atomic audit logging.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageError(Exception):
    """Base error for storage operations."""


class StaleVersionError(StorageError):
    """Raised when base_route_version does not match current state."""


class EventConflictError(StorageError):
    """Raised when an event_id or request_id is reused with conflicting parameters."""


class InvalidAckError(StorageError):
    """Raised when client acknowledgement exceeds published route version."""


class RateLimitExceededError(StorageError):
    """Raised when pairing attempts exceed configured rate limit."""


class DriverNotFoundError(StorageError):
    """Raised when driver_id is not found in driver_state."""


class RouteCandidateNotFoundError(StorageError):
    """Raised when a route_id is not found in RouteCatalog."""


class TransactionalDemoStore:
    """Thread-safe and transaction-safe SQLite store for driver demo operations."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0, isolation_level="EXCLUSIVE")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock, self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pairing_codes (
                    code TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    driver_name TEXT NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    driver_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_revoked INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS driver_state (
                    driver_id TEXT PRIMARY KEY,
                    vehicle_id TEXT NOT NULL,
                    route_id TEXT NOT NULL,
                    corridor_id TEXT NOT NULL,
                    route_version INTEGER NOT NULL DEFAULT 1,
                    manifest_revision INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'en_route',
                    last_ack_version INTEGER DEFAULT 0,
                    last_ack_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS congestion_reports (
                    event_id TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    base_route_version INTEGER NOT NULL,
                    segment_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    delay_seconds REAL NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS planning_jobs (
                    job_id TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    base_route_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    principal TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pairing_rate_limits (
                    client_ip TEXT PRIMARY KEY,
                    attempts INTEGER NOT NULL,
                    window_start REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_planning_jobs_req ON planning_jobs (request_id);
            """)

    # -------------------------------------------------------------------------
    # Pairing Codes & Sessions
    # -------------------------------------------------------------------------

    def seed_pairing_codes(self, codes: list[dict[str, str]], reset: bool = False) -> None:
        """Seed pairing codes.
        
        If reset=False, uses INSERT OR IGNORE so existing redeemed codes are NOT resurrected.
        If reset=True, uses INSERT OR REPLACE (for explicit test/demo resets).
        """
        with self._lock, self._connection() as conn:
            for item in codes:
                now = _utcnow_iso()
                if reset:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO pairing_codes (code, driver_id, vehicle_id, driver_name, is_used, created_at)
                        VALUES (?, ?, ?, ?, 0, ?)
                        """,
                        (item["code"].strip().upper(), item["driver_id"], item["vehicle_id"], item["driver_name"], now),
                    )
                else:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO pairing_codes (code, driver_id, vehicle_id, driver_name, is_used, created_at)
                        VALUES (?, ?, ?, ?, 0, ?)
                        """,
                        (item["code"].strip().upper(), item["driver_id"], item["vehicle_id"], item["driver_name"], now),
                    )

    def check_and_record_rate_limit(self, client_ip: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
        """Rate limit pairing attempts per IP. Returns True if allowed, False if exceeded."""
        now = time.time()
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT attempts, window_start FROM pairing_rate_limits WHERE client_ip = ?", (client_ip,))
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO pairing_rate_limits (client_ip, attempts, window_start) VALUES (?, 1, ?)",
                    (client_ip, now),
                )
                return True
            attempts, window_start = row["attempts"], row["window_start"]
            if now - window_start > window_seconds:
                cur.execute(
                    "UPDATE pairing_rate_limits SET attempts = 1, window_start = ? WHERE client_ip = ?",
                    (now, client_ip),
                )
                return True
            if attempts >= max_attempts:
                return False
            cur.execute(
                "UPDATE pairing_rate_limits SET attempts = attempts + 1 WHERE client_ip = ?",
                (client_ip,),
            )
            return True

    def redeem_code(self, code: str, session_token: str, expires_at: str) -> dict[str, Any] | None:
        """Atomically redeem an unused pairing code and issue a scoped session."""
        clean_code = code.strip().upper()
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM pairing_codes WHERE code = ? AND is_used = 0", (clean_code,))
            row = cur.fetchone()
            if not row:
                return None
            driver_id = row["driver_id"]
            vehicle_id = row["vehicle_id"]
            driver_name = row["driver_name"]

            # Mark code as used
            cur.execute("UPDATE pairing_codes SET is_used = 1 WHERE code = ?", (clean_code,))
            # Create session
            now = _utcnow_iso()
            cur.execute(
                """
                INSERT INTO sessions (token, driver_id, vehicle_id, driver_name, created_at, expires_at, is_revoked)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (session_token, driver_id, vehicle_id, driver_name, now, expires_at),
            )
            return {
                "driver_id": driver_id,
                "vehicle_id": vehicle_id,
                "driver_name": driver_name,
            }

    def get_session(self, token: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE token = ? AND is_revoked = 0", (token,))
            row = cur.fetchone()
            return dict(row) if row else None

    def revoke_session(self, token: str) -> bool:
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
            return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Driver State
    # -------------------------------------------------------------------------

    def init_driver_state_if_missing(
        self, driver_id: str, vehicle_id: str, route_id: str, corridor_id: str
    ) -> None:
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO driver_state (driver_id, vehicle_id, route_id, corridor_id, route_version, manifest_revision, status, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, 'en_route', ?)
                """,
                (driver_id, vehicle_id, route_id, corridor_id, _utcnow_iso()),
            )

    def get_driver_state(self, driver_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM driver_state WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_driver_states(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM driver_state ORDER BY driver_id ASC")
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------------------
    # Congestion Reports & Idempotency
    # -------------------------------------------------------------------------

    def admit_congestion_report(
        self,
        event_id: str,
        driver_id: str,
        vehicle_id: str,
        base_route_version: int,
        segment_id: str,
        severity: str,
        delay_seconds: float,
        expires_at: str,
        note: str = "",
    ) -> tuple[bool, dict[str, Any]]:
        """Admit a congestion report.
        
        Returns (is_new, report_dict).
        If event_id already exists with identical contents, returns (False, existing).
        If event_id already exists with different contents, raises EventConflictError.
        """
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM congestion_reports WHERE event_id = ?", (event_id,))
            row = cur.fetchone()
            if row:
                existing = dict(row)
                if (
                    existing["driver_id"] == driver_id
                    and existing["vehicle_id"] == vehicle_id
                    and existing["base_route_version"] == base_route_version
                    and existing["severity"] == severity
                    and (existing["note"] or "") == (note or "")
                ):
                    return False, existing
                raise EventConflictError(f"event_id '{event_id}' already exists with different parameters")

            # Check driver existence and verify base_route_version BEFORE inserting
            cur.execute("SELECT route_version FROM driver_state WHERE driver_id = ?", (driver_id,))
            drv_row = cur.fetchone()
            if not drv_row:
                raise DriverNotFoundError(f"Driver '{driver_id}' not found")
            current_v = drv_row["route_version"]
            if base_route_version != current_v:
                raise StaleVersionError(
                    f"Base route version {base_route_version} does not match current route version {current_v}"
                )

            now = _utcnow_iso()
            cur.execute(
                """
                INSERT INTO congestion_reports (event_id, driver_id, vehicle_id, base_route_version, segment_id, severity, delay_seconds, note, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, driver_id, vehicle_id, base_route_version, segment_id, severity, delay_seconds, note, now, expires_at),
            )
            return True, {
                "event_id": event_id,
                "driver_id": driver_id,
                "vehicle_id": vehicle_id,
                "base_route_version": base_route_version,
                "segment_id": segment_id,
                "severity": severity,
                "delay_seconds": delay_seconds,
                "note": note,
                "created_at": now,
                "expires_at": expires_at,
            }

    def get_active_overlays(self) -> dict[str, float]:
        """Return {segment_id: delay_seconds} for non-expired reports."""
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            now = _utcnow_iso()
            cur.execute("SELECT segment_id, delay_seconds FROM congestion_reports WHERE expires_at > ?", (now,))
            rows = cur.fetchall()
            overlays: dict[str, float] = {}
            for r in rows:
                seg = r["segment_id"]
                overlays[seg] = max(overlays.get(seg, 0.0), float(r["delay_seconds"]))
            return overlays

    def get_active_incidents(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            now = _utcnow_iso()
            cur.execute(
                "SELECT * FROM congestion_reports WHERE expires_at > ? ORDER BY created_at DESC",
                (now,),
            )
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------------------
    # Planning Jobs & Caller Ownership
    # -------------------------------------------------------------------------

    def create_or_get_planning_job(
        self, job_id: str, driver_id: str, request_id: str, base_route_version: int
    ) -> tuple[bool, dict[str, Any]]:
        """Atomically get existing or create running planning job.
        
        Returns (is_new, job_dict).
        Raises EventConflictError if request_id exists with different driver or version.
        """
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM planning_jobs WHERE request_id = ?", (request_id,))
            row = cur.fetchone()
            if row:
                existing = dict(row)
                if existing["driver_id"] == driver_id and existing["base_route_version"] == base_route_version:
                    if existing.get("result_json"):
                        try:
                            existing["result"] = json.loads(existing["result_json"])
                        except Exception:
                            existing["result"] = None
                    return False, existing
                raise EventConflictError(f"request_id '{request_id}' already exists with different parameters")

            # Check driver existence and verify base_route_version BEFORE inserting
            cur.execute("SELECT route_version FROM driver_state WHERE driver_id = ?", (driver_id,))
            drv_row = cur.fetchone()
            if not drv_row:
                raise DriverNotFoundError(f"Driver '{driver_id}' not found")
            current_v = drv_row["route_version"]
            if base_route_version != current_v:
                raise StaleVersionError(
                    f"Base route version {base_route_version} does not match current route version {current_v}"
                )

            now = _utcnow_iso()
            cur.execute(
                """
                INSERT INTO planning_jobs (job_id, driver_id, request_id, base_route_version, status, outcome, result_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', NULL, NULL, ?, ?)
                """,
                (job_id, driver_id, request_id, base_route_version, now, now),
            )
            return True, {
                "job_id": job_id,
                "driver_id": driver_id,
                "request_id": request_id,
                "base_route_version": base_route_version,
                "status": "running",
                "outcome": None,
                "result": None,
                "created_at": now,
                "updated_at": now,
            }

    def get_job(self, job_id: str, driver_id: Optional[str] = None) -> dict[str, Any] | None:
        """Retrieve job record. If driver_id is provided, enforces caller ownership."""
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM planning_jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if driver_id is not None and res["driver_id"] != driver_id:
                # Caller ownership violation: pretend not found to avoid info leakage
                return None
            if res.get("result_json"):
                try:
                    res["result"] = json.loads(res["result_json"])
                except Exception:
                    res["result"] = None
            return res

    # -------------------------------------------------------------------------
    # CAS Route Mutations & Atomic Publication
    # -------------------------------------------------------------------------

    def atomic_publish_route(
        self,
        driver_id: str,
        base_route_version: int,
        new_route_id: str,
        new_corridor_id: str,
        audit_event_type: str,
        audit_payload: Mapping[str, Any],
        job_id: Optional[str] = None,
        job_outcome: Optional[str] = None,
        job_result: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Atomically publish new route using compare-and-swap on route_version.
        
        Commits:
        1. driver_state CAS update (route_version = route_version + 1)
        2. audit_events record
        3. planning_jobs completion (if job_id supplied)
        
        Raises StaleVersionError if CAS fails.
        """
        now = _utcnow_iso()
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE driver_state
                SET route_id = ?, corridor_id = ?, route_version = route_version + 1, manifest_revision = manifest_revision + 1, updated_at = ?
                WHERE driver_id = ? AND route_version = ?
                """,
                (new_route_id, new_corridor_id, now, driver_id, base_route_version),
            )
            if cur.rowcount == 0:
                cur.execute("SELECT route_version FROM driver_state WHERE driver_id = ?", (driver_id,))
                current_row = cur.fetchone()
                current_v = current_row["route_version"] if current_row else "unknown"
                raise StaleVersionError(f"CAS conflict: expected base_route_version {base_route_version}, current is {current_v}")

            # Audit record
            cur.execute(
                """
                INSERT INTO audit_events (event_type, principal, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (audit_event_type, driver_id, json.dumps(dict(audit_payload)), now),
            )

            # Job completion
            if job_id:
                cur.execute(
                    """
                    UPDATE planning_jobs
                    SET status = 'completed', outcome = ?, result_json = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (job_outcome, json.dumps(job_result or {}), now, job_id),
                )

            cur.execute("SELECT * FROM driver_state WHERE driver_id = ?", (driver_id,))
            return dict(cur.fetchone())

    def atomic_record_decision(
        self,
        driver_id: str,
        audit_event_type: str,
        audit_payload: Mapping[str, Any],
        job_id: Optional[str] = None,
        job_outcome: Optional[str] = None,
        job_result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Atomically record non-mutating decision (e.g. KEEP) and audit log."""
        now = _utcnow_iso()
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_events (event_type, principal, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (audit_event_type, driver_id, json.dumps(dict(audit_payload)), now),
            )
            if job_id:
                cur.execute(
                    """
                    UPDATE planning_jobs
                    SET status = 'completed', outcome = ?, result_json = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (job_outcome, json.dumps(job_result or {}), now, job_id),
                )

    # -------------------------------------------------------------------------
    # Acknowledgements
    # -------------------------------------------------------------------------

    def record_acknowledgement(
        self, driver_id: str, version: int, client_timestamp: Optional[str] = None
    ) -> int:
        """Record client route version acknowledgement.
        
        Enforces:
        - version cannot exceed current published route_version (raises InvalidAckError)
        - older version acknowledgements cannot decrease stored last_ack_version
        """
        now = _utcnow_iso()
        with self._lock, self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT route_version, last_ack_version FROM driver_state WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            if not row:
                raise DriverNotFoundError(f"Driver '{driver_id}' not found")

            published_version = row["route_version"]
            current_ack = row["last_ack_version"] or 0

            if version > published_version:
                raise InvalidAckError(f"Acknowledged version {version} exceeds published version {published_version}")

            new_ack = max(current_ack, version)
            if version >= current_ack:
                cur.execute(
                    """
                    UPDATE driver_state
                    SET last_ack_version = ?, last_ack_at = ?
                    WHERE driver_id = ?
                    """,
                    (new_ack, now, driver_id),
                )

            # Audit
            cur.execute(
                """
                INSERT INTO audit_events (event_type, principal, payload_json, created_at)
                VALUES ('driver_acknowledgement', ?, ?, ?)
                """,
                (driver_id, json.dumps({"version": version, "client_timestamp": client_timestamp}), now),
            )
            return new_ack
