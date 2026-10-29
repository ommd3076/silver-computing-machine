"""Tests for driver pairing, session management, and authentication."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


def test_pairing_success_and_replay_rejection(client: TestClient):
    # 1. Pairing succeeds once
    resp1 = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "token" in data1
    assert data1["token"].startswith("demo_sess_")
    assert data1["driver_id"] == "driver_1"
    assert data1["vehicle_id"] == "vehicle_1"
    assert data1["driver_name"] == "Ramesh Kumar"
    assert "expires_at" in data1

    # 2. Pairing replay with same code fails immediately
    resp2 = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
    assert resp2.status_code == 401
    assert resp2.json()["error"]["code"] == "invalid_code"


def test_invalid_pairing_codes(client: TestClient):
    # Unknown code
    resp = client.post("/api/v1/demo/sessions", json={"code": "UNKNOWN99"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_code"

    # Empty code
    resp_empty = client.post("/api/v1/demo/sessions", json={"code": "   "})
    assert resp_empty.status_code == 422
    assert resp_empty.json()["error"]["code"] == "invalid_request"

    # Excessively long code
    resp_long = client.post("/api/v1/demo/sessions", json={"code": "A" * 100})
    assert resp_long.status_code == 422
    assert resp_long.json()["error"]["code"] == "invalid_request"


def test_pairing_rate_limiting(client: TestClient):
    # Perform 5 failed attempts (matching max_attempts=5)
    for _ in range(5):
        resp = client.post("/api/v1/demo/sessions", json={"code": "BADCODE"})
        assert resp.status_code == 401

    # 6th attempt should be blocked by rate limiter
    blocked = client.post("/api/v1/demo/sessions", json={"code": "BADCODE"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"


def test_driver_identity_me(client: TestClient, paired_driver_1: dict[str, str]):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.get("/api/v1/demo/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["driver_id"] == "driver_1"
    assert data["vehicle_id"] == "vehicle_1"
    assert data["driver_name"] == "Ramesh Kumar"
    assert data["role"] == "driver"
    assert data["simulation_mode"] is True


def test_missing_or_malformed_token_rejected(client: TestClient):
    # No auth header
    r1 = client.get("/api/v1/demo/me")
    assert r1.status_code == 401
    assert r1.json()["error"]["code"] == "authentication_required"

    # Not a Bearer scheme
    r2 = client.get("/api/v1/demo/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "authentication_required"

    # Non-existent bearer
    r3 = client.get("/api/v1/demo/me", headers={"Authorization": "Bearer demo_sess_nonexistenttoken12345"})
    assert r3.status_code == 401
    assert r3.json()["error"]["code"] == "invalid_session"


def test_session_revocation_logout(client: TestClient, paired_driver_1: dict[str, str]):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    
    # 1. Access works before logout
    r1 = client.get("/api/v1/demo/me", headers=headers)
    assert r1.status_code == 200

    # 2. Revoke session
    r2 = client.delete("/api/v1/demo/sessions/current", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "revoked"

    # 3. Access fails after revocation
    r3 = client.get("/api/v1/demo/me", headers=headers)
    assert r3.status_code == 401
    assert r3.json()["error"]["code"] == "invalid_session"


def test_session_expiry(isolated_app, client: TestClient):
    # Insert an expired session manually into store
    expired_token = "demo_sess_expired11223344556677889900"
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    with isolated_app.store._connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token, driver_id, vehicle_id, driver_name, created_at, expires_at, is_revoked)
            VALUES (?, 'driver_1', 'vehicle_1', 'Ramesh Kumar', ?, ?, 0)
            """,
            (expired_token, now_iso, past_iso),
        )

    # Calling with expired token
    resp = client.get("/api/v1/demo/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_session"
