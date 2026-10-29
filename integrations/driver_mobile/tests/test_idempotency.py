"""Tests for event idempotency, conflict detection, and stale version guards."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_replaying_identical_congestion_event_does_not_double_mutate(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    payload = {
        "event_id": "evt-idem-001",
        "base_route_version": 1,
        "kind": "congestion",
        "severity": "heavy",
        "note": "Severe accident on main carriageway",
    }

    # 1. First submission causes route publish (v1 -> v2)
    resp1 = client.post("/api/v1/demo/reports", json=payload, headers=headers)
    assert resp1.status_code == 202
    assert resp1.json()["decision"] == "PUBLISHED_NEW_ROUTE"
    assert resp1.json()["current_route_version"] == 2

    # 2. Replaying identical event_id and payload returns the saved decision without re-bumping!
    resp2 = client.post("/api/v1/demo/reports", json=payload, headers=headers)
    assert resp2.status_code == 202
    assert resp2.json()["current_route_version"] == 2

    # Verify version in database is still 2 (not 3)
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert st["route_version"] == 2


def test_reused_event_id_with_different_payload_returns_409_conflict(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    p1 = {
        "event_id": "evt-conflict-001",
        "base_route_version": 1,
        "kind": "congestion",
        "severity": "moderate",
        "note": "Initial moderate slowdown",
    }
    r1 = client.post("/api/v1/demo/reports", json=p1, headers=headers)
    assert r1.status_code == 202

    # Second submission reuses evt-conflict-001 but changes severity to heavy
    p2 = {
        "event_id": "evt-conflict-001",
        "base_route_version": 1,
        "kind": "congestion",
        "severity": "heavy",
        "note": "Now heavy slowdown",
    }
    r2 = client.post("/api/v1/demo/reports", json=p2, headers=headers)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "event_conflict"


def test_stale_base_route_version_returns_409_conflict(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Bump version to 2 via heavy congestion
    r_bump = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-advance-01",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
        },
        headers=headers,
    )
    assert r_bump.status_code == 202
    assert r_bump.json()["current_route_version"] == 2

    # Client sends report claiming base_route_version=1 (stale!)
    r_stale = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-new-002",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
        },
        headers=headers,
    )
    assert r_stale.status_code == 409
    assert r_stale.json()["error"]["code"] == "stale_route_version"


def test_route_request_idempotency_and_conflict(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    req_payload = {"request_id": "req-idem-001", "base_route_version": 1}

    # 1. Initial request
    r1 = client.post("/api/v1/demo/route-requests", json=req_payload, headers=headers)
    assert r1.status_code == 202
    data1 = r1.json()

    # 2. Replay returns same job
    r2 = client.post("/api/v1/demo/route-requests", json=req_payload, headers=headers)
    assert r2.status_code == 202
    assert r2.json()["job_id"] == data1["job_id"]

    # 3. Conflicting request with different version
    r3 = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req-idem-001", "base_route_version": 99},
        headers=headers,
    )
    assert r3.status_code == 409


def test_stale_congestion_report_does_not_pollute_overlays(
    isolated_app, client: TestClient, paired_driver_1: dict[str, str]
):
    """A rejected stale congestion report must NOT be saved to the database or pollute overlays."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Driver 1 is at version 1; submit with stale version 99
    r_stale = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-stale-no-pollute",
            "base_route_version": 99,
            "kind": "congestion",
            "severity": "heavy",
        },
        headers=headers,
    )
    assert r_stale.status_code == 409
    assert r_stale.json()["error"]["code"] == "stale_route_version"

    # Verify that NO active overlays exist in the store
    overlays = isolated_app.store.get_active_overlays()
    assert len(overlays) == 0, f"Overlays should be empty after rejected report, found: {overlays}"

    # Verify that driver state estimated duration is unaffected
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert len(st["active_overlays"]) == 0

    # Verify that resubmitting the event with the correct version succeeds without conflict
    r_retry = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-stale-no-pollute",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
        },
        headers=headers,
    )
    assert r_retry.status_code == 202
    assert r_retry.json()["current_route_version"] == 2


def test_stale_route_request_does_not_leave_zombie_job(
    isolated_app, client: TestClient, paired_driver_1: dict[str, str]
):
    """A rejected stale route request must NOT leave a dangling running job in the database."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    r_stale = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req-stale-no-zombie", "base_route_version": 99},
        headers=headers,
    )
    assert r_stale.status_code == 409

    # Verify planning_jobs table has no record for req-stale-no-zombie
    with isolated_app.store._connection() as conn:
        row = conn.execute("SELECT * FROM planning_jobs WHERE request_id = 'req-stale-no-zombie'").fetchone()
        assert row is None, "Planning job was inserted despite stale route version!"


def test_job_id_no_collision_for_shared_prefix(
    client: TestClient, paired_driver_1: dict[str, str]
):
    """Different event IDs sharing the first 12 characters must NOT collide in planning_jobs."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    e1 = "event-2026-10-30-report-01"
    e2 = "event-2026-10-30-report-02"

    r1 = client.post(
        "/api/v1/demo/reports",
        json={"event_id": e1, "base_route_version": 1, "severity": "moderate"},
        headers=headers,
    )
    assert r1.status_code == 202
    job1_id = r1.json()["job_id"]

    r2 = client.post(
        "/api/v1/demo/reports",
        json={"event_id": e2, "base_route_version": 1, "severity": "moderate"},
        headers=headers,
    )
    assert r2.status_code == 202
    job2_id = r2.json()["job_id"]

    assert job1_id != job2_id, f"Job IDs collided: {job1_id} vs {job2_id}"

