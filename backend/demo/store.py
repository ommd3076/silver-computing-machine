"""Thread-safe SQLite storage for hackathon phone demo.

Manages:
  - Pairing codes & driver sessions
  - Driver route states & active manifest versions
  - Congestion reports & active delay overlays
  - Durable planning jobs
  - Client acknowledgements & decision audit log
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemoStore:
    """SQLite-backed store for demo state isolation."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            configured = os.environ.get("DEBUGLEAF_DEMO_DB_PATH")
            if configured:
                self.db_path = configured
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            else:
                db_dir = Path(".runtime")
                db_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = str(db_dir / "demo_store.sqlite3")
        else:
            self.db_path = str(db_path)
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._init_db()

    from contextlib import contextmanager

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=FULL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
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
                    last_ack_manifest_revision INTEGER DEFAULT 0,
                    last_ack_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS congestion_reports (
                    event_id TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    segment_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    delay_seconds REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    note TEXT
                );

                CREATE TABLE IF NOT EXISTS planning_jobs (
                    job_id TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
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

                CREATE TABLE IF NOT EXISTS demo_events (
                    event_id TEXT PRIMARY KEY, driver_id TEXT NOT NULL, request_hash TEXT NOT NULL,
                    proposal_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS demo_proposals (
                    proposal_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, driver_id TEXT NOT NULL,
                    status TEXT NOT NULL, base_route_version INTEGER NOT NULL, route_id TEXT,
                    corridor_id TEXT, proposal_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    decided_at TEXT, decided_by TEXT, published_manifest_json TEXT
                );
                CREATE TABLE IF NOT EXISTS demo_manifests (
                    vehicle_id TEXT NOT NULL, version INTEGER NOT NULL, driver_id TEXT NOT NULL,
                    manifest_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY(vehicle_id, version)
                );
            """)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(driver_state)").fetchall()}
            if "last_ack_manifest_revision" not in columns:
                conn.execute("ALTER TABLE driver_state ADD COLUMN last_ack_manifest_revision INTEGER DEFAULT 0")
            proposal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(demo_proposals)").fetchall()}
            if "published_manifest_json" not in proposal_columns:
                conn.execute("ALTER TABLE demo_proposals ADD COLUMN published_manifest_json TEXT")

    # -------------------------------------------------------------------------
    # Pairing & Sessions
    # -------------------------------------------------------------------------

    def seed_pairing_codes(self, codes: list[dict[str, str]]) -> None:
        with self._lock, self._get_connection() as conn:
            for item in codes:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pairing_codes (code, driver_id, vehicle_id, driver_name, is_used, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (item["code"], item["driver_id"], item["vehicle_id"], item["driver_name"], _utcnow_iso()),
                )

    def redeem_code(self, code: str, session_token: str, expires_at: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM pairing_codes WHERE code = ? AND is_used = 0", (code,))
            row = cur.fetchone()
            if not row:
                return None
            driver_id = row["driver_id"]
            vehicle_id = row["vehicle_id"]
            driver_name = row["driver_name"]

            # Mark code as used
            cur.execute("UPDATE pairing_codes SET is_used = 1 WHERE code = ?", (code,))
            # Insert session
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
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE token = ? AND is_revoked = 0", (token,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def revoke_session(self, token: str) -> bool:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
            return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Driver State
    # -------------------------------------------------------------------------

    def init_driver_state_if_missing(
        self, driver_id: str, vehicle_id: str, route_id: str, corridor_id: str
    ) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO driver_state (driver_id, vehicle_id, route_id, corridor_id, route_version, manifest_revision, status, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, 'en_route', ?)
                """,
                (driver_id, vehicle_id, route_id, corridor_id, _utcnow_iso()),
            )
            # Keep a durable initial manifest aligned with the authoritative
            # driver row (including pre-existing rows with advanced versions).
            state = conn.execute("SELECT * FROM driver_state WHERE driver_id=?", (driver_id,)).fetchone()
            if state:
                existing = conn.execute(
                    "SELECT 1 FROM demo_manifests WHERE vehicle_id=? AND driver_id=? LIMIT 1",
                    (state["vehicle_id"], driver_id),
                ).fetchone()
            else:
                existing = True
            if state and not existing:
                manifest = self._manifest_from_state(conn, driver_id)
                conn.execute(
                    "INSERT OR IGNORE INTO demo_manifests (vehicle_id,version,driver_id,manifest_json,created_at) VALUES(?,?,?,?,?)",
                    (state["vehicle_id"], state["manifest_revision"], driver_id,
                     json.dumps(manifest, sort_keys=True), _utcnow_iso()),
                )

    def get_driver_state(self, driver_id: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM driver_state WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_driver_route(
        self, driver_id: str, route_id: str, corridor_id: str
    ) -> dict[str, Any]:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            now = _utcnow_iso()
            cur.execute(
                """
                UPDATE driver_state
                SET route_id = ?, corridor_id = ?, route_version = route_version + 1, manifest_revision = manifest_revision + 1, updated_at = ?
                WHERE driver_id = ?
                """,
                (route_id, corridor_id, now, driver_id),
            )
            cur.execute("SELECT * FROM driver_state WHERE driver_id = ?", (driver_id,))
            return dict(cur.fetchone())

    def record_acknowledgement(self, driver_id: str, version: int, manifest_revision: int) -> str:
        now = _utcnow_iso()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                UPDATE driver_state
                SET last_ack_version = ?, last_ack_manifest_revision = ?, last_ack_at = ?
                WHERE driver_id = ?
                """,
                (version, manifest_revision, now, driver_id),
            )
        return now

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT * FROM demo_events WHERE event_id=?", (event_id,)).fetchone()
            return dict(row) if row else None

    def create_event_proposal(self, event_id: str, driver_id: str, request_hash: str,
                              proposal_id: str, base_version: int, route_id: str | None,
                              corridor_id: str | None, proposal: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute("SELECT * FROM demo_events WHERE event_id=?", (event_id,)).fetchone()
            if prior:
                if prior["driver_id"] != driver_id or prior["request_hash"] != request_hash:
                    raise ValueError("event_conflict")
                return json.loads(prior["proposal_json"])
            now = _utcnow_iso()
            body = json.dumps(proposal, sort_keys=True)
            conn.execute("INSERT INTO demo_events VALUES(?,?,?,?,?)", (event_id, driver_id, request_hash, body, now))
            conn.execute("INSERT INTO demo_proposals (proposal_id,event_id,driver_id,status,base_route_version,route_id,corridor_id,proposal_json,created_at,decided_at,decided_by) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (proposal_id, event_id, driver_id, "pending", base_version,
                          route_id, corridor_id, body, now, None, None))
            return proposal

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT * FROM demo_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                return None
            out = dict(row)
            out["proposal"] = json.loads(out.pop("proposal_json"))
            return out

    def publish_proposal(self, proposal_id: str, actor: str, validation: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            # Acquire the SQLite writer lock before checking the base version. Store
            # instances have separate Python locks, so this is the cross-instance CAS.
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM demo_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                return None
            if row["status"] == "published":
                if row["published_manifest_json"]:
                    return json.loads(row["published_manifest_json"])
                # Backward compatibility for previously published rows predating
                # the exact-result column. Restrict lookup to the proposal owner.
                state_row = conn.execute("SELECT vehicle_id FROM driver_state WHERE driver_id=?", (row["driver_id"],)).fetchone()
                if not state_row:
                    return None
                saved = conn.execute("SELECT manifest_json FROM demo_manifests WHERE vehicle_id=? AND driver_id=? ORDER BY version DESC LIMIT 1",
                                     (state_row["vehicle_id"], row["driver_id"])).fetchone()
                return json.loads(saved["manifest_json"]) if saved else self._manifest_from_state(conn, row["driver_id"])
            if row["status"] != "pending":
                raise ValueError("proposal_not_pending")
            if not validation.get("valid"):
                raise ValueError("validation_failed")
            state = conn.execute("SELECT * FROM driver_state WHERE driver_id=?", (row["driver_id"],)).fetchone()
            if not state or state["route_version"] != row["base_route_version"]:
                raise ValueError("stale_proposal")
            if row["route_id"]:
                latest = conn.execute("SELECT MAX(version) AS version FROM demo_manifests WHERE vehicle_id=?",
                                      (state["vehicle_id"],)).fetchone()["version"]
                version = max(state["manifest_revision"], latest or 0) + 1
                conn.execute("UPDATE driver_state SET route_id=?,corridor_id=?,route_version=?,manifest_revision=?,updated_at=? WHERE driver_id=?",
                             (row["route_id"], row["corridor_id"], state["route_version"] + 1,
                              version, _utcnow_iso(), row["driver_id"]))
                manifest = {"driver_id": row["driver_id"], "vehicle_id": state["vehicle_id"],
                            "version": version, "route_version": state["route_version"] + 1,
                            "route_id": row["route_id"], "corridor_id": row["corridor_id"],
                            "proposal_id": proposal_id, "status": "published", "validation": validation}
                conn.execute("INSERT INTO demo_manifests VALUES(?,?,?,?,?)",
                             (state["vehicle_id"], version, row["driver_id"], json.dumps(manifest), _utcnow_iso()))
            else:
                manifest = self._manifest_from_state(conn, row["driver_id"])
            if manifest is None:
                raise ValueError("driver_state_missing")
            proposal = json.loads(row["proposal_json"])
            proposal["validation"] = validation
            conn.execute("UPDATE demo_proposals SET status='published',proposal_json=?,decided_at=?,decided_by=?,published_manifest_json=? WHERE proposal_id=?",
                         (json.dumps(proposal, sort_keys=True), _utcnow_iso(), actor,
                          json.dumps(manifest, sort_keys=True), proposal_id))
            return manifest

    @staticmethod
    def _manifest_from_state(conn, driver_id: str) -> dict[str, Any] | None:
        state = conn.execute("SELECT * FROM driver_state WHERE driver_id=?", (driver_id,)).fetchone()
        if not state:
            return None
        return {"driver_id": driver_id, "vehicle_id": state["vehicle_id"],
                "version": state["manifest_revision"], "route_version": state["route_version"],
                "route_id": state["route_id"], "corridor_id": state["corridor_id"], "status": "published"}

    def get_manifest_for_driver(self, driver_id: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            state = conn.execute("SELECT * FROM driver_state WHERE driver_id=?", (driver_id,)).fetchone()
            if not state:
                return None
            row = conn.execute("SELECT manifest_json FROM demo_manifests WHERE vehicle_id=? AND driver_id=? ORDER BY version DESC LIMIT 1",
                               (state["vehicle_id"], driver_id)).fetchone()
            return json.loads(row["manifest_json"]) if row else self._manifest_from_state(conn, driver_id)

    # -------------------------------------------------------------------------
    # Congestion Reports & Overlays
    # -------------------------------------------------------------------------

    def save_congestion_report(
        self,
        event_id: str,
        driver_id: str,
        vehicle_id: str,
        segment_id: str,
        severity: str,
        delay_seconds: float,
        expires_at: str,
        note: str = "",
    ) -> None:
        with self._lock, self._get_connection() as conn:
            # Keep the read/compare/insert idempotency check atomic across store
            # instances sharing this database.
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute("SELECT driver_id,vehicle_id,segment_id,severity,delay_seconds,expires_at,note FROM congestion_reports WHERE event_id=?",
                                 (event_id,)).fetchone()
            values = (driver_id, vehicle_id, segment_id, severity, float(delay_seconds), expires_at, note)
            if prior:
                existing = tuple(prior[key] for key in ("driver_id", "vehicle_id", "segment_id", "severity", "delay_seconds", "expires_at", "note"))
                if existing != values:
                    raise ValueError("report_conflict")
                return
            conn.execute(
                """
                INSERT INTO congestion_reports (event_id, driver_id, vehicle_id, segment_id, severity, delay_seconds, created_at, expires_at, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, driver_id, vehicle_id, segment_id, severity, delay_seconds, _utcnow_iso(), expires_at, note),
            )

    def get_active_overlays(self) -> dict[str, float]:
        """Return {segment_id: delay_seconds} for non-expired reports."""
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            now = _utcnow_iso()
            cur.execute("SELECT segment_id, delay_seconds FROM congestion_reports WHERE expires_at > ?", (now,))
            rows = cur.fetchall()
            overlays: dict[str, float] = {}
            for r in rows:
                seg = r["segment_id"]
                # Keep maximum reported delay for a segment
                overlays[seg] = max(overlays.get(seg, 0.0), float(r["delay_seconds"]))
            return overlays

    # -------------------------------------------------------------------------
    # Planning Jobs & Audit
    # -------------------------------------------------------------------------

    def create_or_get_job(self, job_id: str, driver_id: str, request_id: str) -> dict[str, Any]:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM planning_jobs WHERE request_id = ?", (request_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            now = _utcnow_iso()
            cur.execute(
                """
                INSERT INTO planning_jobs (job_id, driver_id, request_id, status, outcome, result_json, created_at, updated_at)
                VALUES (?, ?, ?, 'running', NULL, NULL, ?, ?)
                """,
                (job_id, driver_id, request_id, now, now),
            )
            return {
                "job_id": job_id,
                "driver_id": driver_id,
                "request_id": request_id,
                "status": "running",
            }

    def complete_job(self, job_id: str, outcome: str, result: dict[str, Any]) -> None:
        with self._lock, self._get_connection() as conn:
            now = _utcnow_iso()
            conn.execute(
                """
                UPDATE planning_jobs
                SET status = 'completed', outcome = ?, result_json = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (outcome, json.dumps(result), now, job_id),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM planning_jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("result_json"):
                try:
                    res["result"] = json.loads(res["result_json"])
                except Exception:
                    res["result"] = None
            return res

    def log_audit(self, event_type: str, principal: str, payload: Mapping[str, Any]) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (event_type, principal, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, principal, json.dumps(dict(payload)), _utcnow_iso()),
            )

    def get_recent_audits(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
            return [{"id": row["id"], "event_type": row["event_type"], "principal": row["principal"],
                     "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]} for row in rows]

    def list_proposals(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM demo_proposals ORDER BY created_at DESC LIMIT ?",
                                (max(1, min(limit, 200)),)).fetchall()
            out = []
            for row in rows:
                item = dict(row)
                item["proposal"] = json.loads(item.pop("proposal_json"))
                item.pop("driver_id", None)
                out.append(item)
            return out

    def clear_all(self) -> None:
        with self._lock, self._get_connection() as conn:
            for table in ("pairing_codes", "sessions", "driver_state", "congestion_reports",
                          "planning_jobs", "audit_events", "demo_events", "demo_proposals", "demo_manifests"):
                conn.execute(f"DELETE FROM {table}")
