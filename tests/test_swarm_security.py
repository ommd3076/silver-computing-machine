"""Local HTTP security regression checks for role and driver boundaries."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import AuthConfig, TokenAuthMiddleware
from backend.demo.api import create_demo_router
from backend.demo.auth import DemoAuthManager
from backend.demo.service import DemoCoordinatorService
from backend.demo.store import DemoStore


TOKENS = {
    "dispatcher": "SECURITY_DISPATCHER_SENTINEL",
    "researcher": "SECURITY_RESEARCHER_SENTINEL",
    "admin": "SECURITY_ADMIN_SENTINEL",
}


def _driver_app(db_path, auth):
    store = DemoStore(db_path)
    service = DemoCoordinatorService(store)
    app = FastAPI()
    app.state.auth_config = auth
    app.add_middleware(TokenAuthMiddleware, config=auth)
    app.include_router(create_demo_router(store, service, DemoAuthManager(store)))
    return app


def test_driver_sessions_cannot_cross_read_ack_or_approve(tmp_path):
    auth = AuthConfig.from_mapping("token", TOKENS)
    with TestClient(_driver_app(tmp_path / "drivers.sqlite", auth), base_url="http://127.0.0.1") as client:
        session_a = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"}).json()
        session_b = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"}).json()
        headers_a = {"Authorization": f"Bearer {session_a['token']}"}
        headers_b = {"Authorization": f"Bearer {session_b['token']}"}

        # A caller-supplied identity selector cannot change the session principal.
        state_b = client.get("/api/v1/demo/state?driver_id=driver_1", headers=headers_b)
        manifest_b = client.get("/api/v1/demo/manifest?driver_id=driver_1", headers=headers_b)
        assert state_b.status_code == manifest_b.status_code == 200
        assert state_b.json()["driver_id"] == manifest_b.json()["driver_id"] == "driver_2"

        report = client.post(
            "/api/v1/demo/reports",
            headers=headers_a,
            json={"event_id": "cross-driver-event", "base_route_version": 1,
                  "severity": "heavy", "note": "traffic"},
        )
        assert report.status_code == 202
        proposal_id = report.json()["proposal_id"]
        proposal_path = f"/api/v1/demo/proposals/{proposal_id}"

        # Driver sessions have no dispatcher read or publication capability.
        assert client.get(proposal_path, headers=headers_b).status_code == 401
        denied = client.post(f"{proposal_path}/approve", headers=headers_b)
        assert denied.status_code == 401
        assert client.get("/api/v1/demo/state", headers=headers_a).json()["route_version"] == 1

        # The actual owner is not mutated by another driver's acknowledgement attempt.
        attempted_ack = client.post(
            "/api/v1/demo/acknowledgements", headers=headers_b,
            json={"version": 2, "manifest_revision": 2},
        )
        assert attempted_ack.status_code == 409
        assert client.get("/api/v1/demo/state", headers=headers_a).json()["last_ack_version"] == 0

        # Only a configured dispatcher can publish; the manifest remains scoped to its driver.
        approved = client.post(
            f"{proposal_path}/approve",
            headers={"Authorization": f"Bearer {TOKENS['dispatcher']}"},
        )
        assert approved.status_code == 200
        assert client.get("/api/v1/demo/manifest", headers=headers_a).json()["route_version"] == 2
        assert client.get("/api/v1/demo/manifest", headers=headers_b).json()["route_version"] == 1


def test_invalid_demo_and_eta_ids_and_auth_failures_do_not_echo_sentinels(tmp_path, caplog):
    auth = AuthConfig.from_mapping("token", TOKENS)
    client = TestClient(_driver_app(tmp_path / "ids.sqlite", auth), base_url="http://127.0.0.1")
    secret = "REQUEST_SECRET_SENTINEL"
    invalid_id = "INVALID_PROPOSAL_ID_SENTINEL"
    malformed_eta_id = "INVALID!ETA_ID_SENTINEL"

    denied = client.post(
        f"/api/v1/demo/proposals/{invalid_id}/approve",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert denied.status_code == 401
    assert secret not in denied.text
    assert invalid_id not in denied.text

    dispatcher = {"Authorization": f"Bearer {TOKENS['dispatcher']}"}
    missing_demo = client.get(f"/api/v1/demo/proposals/{invalid_id}", headers=dispatcher)
    assert missing_demo.status_code == 404
    assert invalid_id not in missing_demo.text

    # ETA approval identity is derived from the configured token, never a body field.
    eta_client = TestClient(create_app(auth_config=auth, eta_db_path=tmp_path / "eta.sqlite"))
    missing_eta = eta_client.get(f"/api/v1/eta/proposals/{malformed_eta_id}", headers=dispatcher)
    assert missing_eta.status_code == 422
    assert malformed_eta_id not in missing_eta.text
    forged = eta_client.post(
        f"/api/v1/eta/proposals/{invalid_id}/approve",
        headers={"Authorization": f"Bearer {TOKENS['researcher']}"},
        json={"actor": {"subject": "forged-admin", "role": "admin"}},
    )
    assert forged.status_code == 403
    assert "forged-admin" not in forged.text
    assert all(value not in caplog.text for value in (*TOKENS.values(), secret, invalid_id, malformed_eta_id))

