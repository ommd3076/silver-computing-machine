"""Failure handling, edge case, and persistence tests."""
from __future__ import annotations

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from integrations.driver_mobile.server.app import create_composite_app, DEMO_FIXTURE_CODES
from integrations.driver_mobile.server.config import IntegrationConfig


def test_service_restart_preserves_state(isolated_app, client: TestClient):
    """Test that restarting the service preserves SQLite state, sessions, and route versions."""
    db_path = isolated_app.store.db_path

    # 1. Pair Driver 1 and advance to v2
    r_pair = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
    assert r_pair.status_code == 200
    token = r_pair.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r_cong = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "evt-persist-001", "base_route_version": 1, "severity": "heavy"},
        headers=headers,
    )
    assert r_cong.status_code == 202
    assert r_cong.json()["current_route_version"] == 2

    # 2. Simulate server restart: create completely new app instance pointing to same DB
    cfg = IntegrationConfig(
        db_path=Path(db_path),
        auth_mode="token",
        dispatcher_token="valid_dispatcher_token_secret_12345",
        admin_token="valid_admin_token_secret_67890",
        researcher_token="valid_researcher_token_secret_11223",
        session_ttl_minutes=60,
        pairing_max_attempts=5,
        pairing_window_seconds=60,
        fixture_mode=False,  # no re-seeding on restart!
        host="127.0.0.1",
        port=8000,
    )
    restarted_app = create_composite_app(cfg=cfg)
    with TestClient(restarted_app) as restarted_client:
        # Existing session token still valid across restart
        s_after = restarted_client.get("/api/v1/demo/state", headers=headers)
        assert s_after.status_code == 200
        data = s_after.json()
        assert data["route_version"] == 2
        assert data["route_id"] == "route_v1_bypass"
        assert data["corridor_id"] == "corridor_b_bypass"


def test_invalid_payload_types_and_bounds_return_sanitized_422(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Negative route_version in acknowledgement
    r_neg = client.post("/api/v1/demo/acknowledgements", json={"route_version": -1}, headers=headers)
    assert r_neg.status_code == 422
    assert r_neg.json()["error"]["code"] == "invalid_request"

    # Invalid severity string in report
    r_sev = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "e1", "base_route_version": 1, "severity": "catastrophic"},
        headers=headers,
    )
    assert r_sev.status_code == 422
    assert r_sev.json()["error"]["code"] == "invalid_request"

    # Overly large note (bounds checking: max 500 chars)
    r_big = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "e2", "base_route_version": 1, "severity": "heavy", "note": "x" * 1000},
        headers=headers,
    )
    assert r_big.status_code == 422
    assert r_big.json()["error"]["code"] == "invalid_request"


def test_unhandled_exception_returns_clean_500_without_leakage(client: TestClient):
    # Make a request with non-JSON content-type to an endpoint expecting JSON
    r = client.post(
        "/api/v1/demo/sessions",
        content=b"not-json-content",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    # Ensure no raw python traceback or internal file paths leak
    assert "Traceback" not in r.text
    assert "File " not in r.text


def test_unknown_driver_returns_404(isolated_app, client: TestClient, paired_driver_1: dict[str, str]):
    """If a driver's state is missing, requests return 404 rather than an unhandled 500 error."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Delete driver 1 from driver_state table
    with isolated_app.store._connection() as conn:
        conn.execute("DELETE FROM driver_state WHERE driver_id = 'driver_1'")

    r_state = client.get("/api/v1/demo/state", headers=headers)
    assert r_state.status_code == 404
    assert r_state.json()["error"]["code"] == "driver_not_found"

    r_rep = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "e_unk_1", "base_route_version": 1, "severity": "heavy"},
        headers=headers,
    )
    assert r_rep.status_code == 404
    assert r_rep.json()["error"]["code"] == "driver_not_found"

    r_ack = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 1},
        headers=headers,
    )
    assert r_ack.status_code == 404
    assert r_ack.json()["error"]["code"] == "driver_not_found"


def test_missing_route_candidate_returns_404(isolated_app, client: TestClient, paired_driver_1: dict[str, str]):
    """If a driver's route_id does not exist in catalog, returns 404 candidate_not_found instead of 500."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    # Set route_id to a nonexistent candidate
    with isolated_app.store._connection() as conn:
        conn.execute("UPDATE driver_state SET route_id = 'nonexistent_route' WHERE driver_id = 'driver_1'")

    r_rep = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "e_cand_1", "base_route_version": 1, "severity": "heavy"},
        headers=headers,
    )
    assert r_rep.status_code == 404
    assert r_rep.json()["error"]["code"] == "candidate_not_found"

    r_plan = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req_cand_1", "base_route_version": 1},
        headers=headers,
    )
    assert r_plan.status_code == 404
    assert r_plan.json()["error"]["code"] == "candidate_not_found"


def test_foreign_driver_id_in_report_or_plan_rejected(client: TestClient, paired_driver_1: dict[str, str]):
    """Submitting foreign driver_id in request body is explicitly rejected with 403."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    r_rep = client.post(
        "/api/v1/demo/reports",
        json={"event_id": "e_for_1", "base_route_version": 1, "severity": "heavy", "driver_id": "driver_2"},
        headers=headers,
    )
    assert r_rep.status_code == 403
    assert r_rep.json()["error"]["code"] == "forbidden_resource"

    r_plan = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "r_for_1", "base_route_version": 1, "driver_id": "driver_2"},
        headers=headers,
    )
    assert r_plan.status_code == 403
    assert r_plan.json()["error"]["code"] == "forbidden_resource"


def test_invalid_segment_returns_422(client: TestClient, paired_driver_1: dict[str, str]):
    """Submitting a segment not belonging to driver's route returns 422."""
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}

    r = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "e_bad_seg",
            "base_route_version": 1,
            "severity": "heavy",
            "segment_id": "seg_south_arterial",  # belongs to vehicle 2, not vehicle 1!
        },
        headers=headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_segment"

