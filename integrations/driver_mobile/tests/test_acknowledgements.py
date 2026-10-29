"""Tests for client route version acknowledgements."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_valid_latest_acknowledgement(client: TestClient, paired_driver_1: dict[str, str]):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Current route_version is 1
    resp = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 1, "client_timestamp": "2026-10-30T01:30:00.000Z"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"
    assert data["version"] == 1
    assert data["driver_id"] == "driver_1"

    # Verify state reflects acknowledgement
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert st["last_ack_version"] == 1


def test_future_version_acknowledgement_rejected(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Published version is 1; client attempts to acknowledge version 2
    resp = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 2, "client_timestamp": "2026-10-30T01:30:00.000Z"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "future_version_rejected"


def test_stale_acknowledgement_does_not_roll_back(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # 1. Bump version to 2 via heavy congestion
    client.post(
        "/api/v1/demo/reports",
        json={"event_id": "evt-ack-bump", "base_route_version": 1, "severity": "heavy"},
        headers=headers,
    )

    # 2. Acknowledge version 2
    r_ack2 = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 2},
        headers=headers,
    )
    assert r_ack2.status_code == 200
    assert r_ack2.json()["version"] == 2

    # 3. Delayed packet arrives acknowledging version 1
    r_ack1 = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 1},
        headers=headers,
    )
    assert r_ack1.status_code == 200
    # Should report version 2 (not rolled backwards!)
    assert r_ack1.json()["version"] == 2

    # Verify last_ack_version remains 2
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert st["last_ack_version"] == 2


def test_foreign_driver_acknowledgement_rejected(
    client: TestClient, paired_driver_1: dict[str, str]
):
    """Driver 1 session attempting to submit an acknowledgement for Driver 2 must be rejected with 403."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 1, "driver_id": "driver_2"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden_resource"
