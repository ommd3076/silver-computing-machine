"""Durability and isolation contracts for the phone-demo SQLite store."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from backend.demo.store import DemoStore


def _seed_two_drivers(store: DemoStore, vehicle_id: str = "shared_vehicle") -> None:
    store.init_driver_state_if_missing("driver_a", vehicle_id, "route_a", "corridor_a")
    store.init_driver_state_if_missing("driver_b", vehicle_id, "route_b", "corridor_b")


def _proposal(store: DemoStore, event: str, driver: str, base: int, route: str) -> str:
    proposal_id = f"proposal_{event}"
    body = {"event_id": event, "driver_id": driver, "route_id": route,
            "base_route_version": base, "decision": "PROPOSE_ROUTE"}
    store.create_event_proposal(event, driver, f"hash_{event}", proposal_id,
                                base, route, f"corridor_{route}", body)
    return proposal_id


def test_publish_is_atomic_idempotent_and_driver_scoped_after_restart(tmp_path):
    db = tmp_path / "demo.sqlite3"
    first = DemoStore(db)
    _seed_two_drivers(first)
    proposal_a1 = _proposal(first, "a1", "driver_a", 1, "route_a2")
    proposal_a2 = _proposal(first, "a2", "driver_a", 2, "route_a3")
    proposal_b1 = _proposal(first, "b1", "driver_b", 1, "route_b2")

    # Separate store objects have separate Python locks; SQLite must serialize
    # the competing publishers and only advance the driver's route once.
    second = DemoStore(db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda store: store.publish_proposal(
            proposal_a1, "dispatcher", {"valid": True}), (first, second)))
    assert results[0] == results[1]
    assert results[0]["version"] == 2
    assert first.get_driver_state("driver_a")["route_version"] == 2

    a2 = first.publish_proposal(proposal_a2, "dispatcher", {"valid": True})
    b1 = first.publish_proposal(proposal_b1, "dispatcher", {"valid": True})
    assert a2["version"] == 3
    assert b1["version"] == 4  # vehicle-wide manifest revisions are monotonic
    assert first.get_manifest_for_driver("driver_a")["driver_id"] == "driver_a"
    assert first.get_manifest_for_driver("driver_b")["driver_id"] == "driver_b"

    # Retrying a prior proposal returns its own committed output, even after a
    # later publication for that same driver and after store reconstruction.
    restarted = DemoStore(db)
    assert restarted.publish_proposal(proposal_a1, "dispatcher", {"valid": True}) == results[0]
    assert restarted.get_manifest_for_driver("driver_a") == a2
    assert restarted.get_manifest_for_driver("driver_b") == b1
    with restarted._get_connection() as conn:
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2


def test_report_event_is_idempotent_and_conflicts_do_not_replace_original(tmp_path):
    store = DemoStore(tmp_path / "reports.sqlite3")
    args = {"event_id": "report-1", "driver_id": "driver_a", "vehicle_id": "vehicle_a",
            "segment_id": "segment-1", "severity": "heavy", "delay_seconds": 480,
            "expires_at": "2099-01-01T00:00:00+00:00", "note": "jam"}
    store.save_congestion_report(**args)
    with store._get_connection() as conn:
        original = dict(conn.execute("SELECT * FROM congestion_reports WHERE event_id='report-1'").fetchone())

    store.save_congestion_report(**args)
    with store._get_connection() as conn:
        assert dict(conn.execute("SELECT * FROM congestion_reports WHERE event_id='report-1'").fetchone()) == original

    with pytest.raises(ValueError, match="report_conflict"):
        store.save_congestion_report(**{**args, "note": "different payload"})
    with store._get_connection() as conn:
        assert dict(conn.execute("SELECT * FROM congestion_reports WHERE event_id='report-1'").fetchone()) == original


def test_event_proposal_retry_checks_owner_and_request_hash(tmp_path):
    store = DemoStore(tmp_path / "events.sqlite3")
    pid = _proposal(store, "same-event", "driver_a", 1, "route_a2")
    assert store.get_event("same-event")["driver_id"] == "driver_a"
    assert store.create_event_proposal("same-event", "driver_a", "hash_same-event", "ignored",
                                       99, None, None, {"retry": True})["event_id"] == "same-event"
    with pytest.raises(ValueError, match="event_conflict"):
        store.create_event_proposal("same-event", "driver_b", "hash_same-event", "ignored",
                                    1, None, None, {})
    assert store.get_proposal(pid)["status"] == "pending"


def test_existing_store_schema_is_migrated_without_replacing_rows(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE demo_proposals (
            proposal_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, driver_id TEXT NOT NULL,
            status TEXT NOT NULL, base_route_version INTEGER NOT NULL, route_id TEXT,
            corridor_id TEXT, proposal_json TEXT NOT NULL, created_at TEXT NOT NULL,
            decided_at TEXT, decided_by TEXT)""")
        conn.execute("INSERT INTO demo_proposals VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     ("legacy-p", "legacy-e", "legacy-driver", "pending", 1, None, None,
                      '{"legacy":true}', "2026-10-01T00:00:00+00:00", None, None))

    DemoStore(db)
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT proposal_id,status,proposal_json,published_manifest_json FROM demo_proposals").fetchone()
        assert row == ("legacy-p", "pending", '{"legacy":true}', None)
