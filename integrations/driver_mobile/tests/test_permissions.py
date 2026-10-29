"""Tests for role separation, dispatcher access controls, and job ownership."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_driver_token_cannot_access_dispatcher_overview(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.get("/api/v1/demo/dispatcher/overview", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "authorization_denied"


def test_unauthenticated_dispatcher_overview_rejected(client: TestClient):
    resp = client.get("/api/v1/demo/dispatcher/overview")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_required"


def test_invalid_dispatcher_token_rejected(client: TestClient):
    resp = client.get(
        "/api/v1/demo/dispatcher/overview",
        headers={"Authorization": "Bearer bad_dispatcher_secret_9999"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_failed"


def test_dispatcher_and_admin_token_access_overview(client: TestClient):
    # Dispatcher token
    disp_headers = {"Authorization": "Bearer valid_dispatcher_token_secret_12345"}
    r1 = client.get("/api/v1/demo/dispatcher/overview", headers=disp_headers)
    assert r1.status_code == 200
    data1 = r1.json()
    assert "drivers" in data1
    assert len(data1["drivers"]) >= 2
    assert "active_incidents" in data1

    # Admin token
    admin_headers = {"Authorization": "Bearer valid_admin_token_secret_67890"}
    r2 = client.get("/api/v1/demo/dispatcher/overview", headers=admin_headers)
    assert r2.status_code == 200


def test_dispatcher_token_cannot_access_driver_endpoints(client: TestClient):
    disp_headers = {"Authorization": "Bearer valid_dispatcher_token_secret_12345"}
    resp = client.get("/api/v1/demo/state", headers=disp_headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_session"


def test_driver_token_cannot_approve_eta_proposals(
    client: TestClient, paired_driver_1: dict[str, str]
):
    # Driver token attempting to call India ETA approval
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    payload = {
        "base_version": 1,
        "event_id": "evt_test_fake",
        "model_version": "india_eta_v1",
        "context_hash": "a" * 64,
    }
    resp = client.post("/api/v1/eta/proposals/prop_test_fake/approve", json=payload, headers=headers)
    # TokenAuthMiddleware or principal check denies it with 401 or 403
    assert resp.status_code in (401, 403)


def test_job_caller_ownership_enforcement(
    client: TestClient,
    paired_driver_1: dict[str, str],
    paired_driver_2: dict[str, str],
):
    h1 = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    h2 = {"Authorization": f"Bearer {paired_driver_2['token']}"}

    # Driver 1 triggers a route planning job
    r_plan = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req-own-001", "base_route_version": 1},
        headers=h1,
    )
    assert r_plan.status_code == 202
    job_id = r_plan.json()["job_id"]

    # Driver 1 can query their own job
    r_own = client.get(f"/api/v1/demo/jobs/{job_id}", headers=h1)
    assert r_own.status_code == 200
    assert r_own.json()["job_id"] == job_id

    # Driver 2 tries to query Driver 1's job -> MUST return 404 (ownership enforced)
    r_foreign = client.get(f"/api/v1/demo/jobs/{job_id}", headers=h2)
    assert r_foreign.status_code == 404
    assert r_foreign.json()["error"]["code"] == "job_not_found"
