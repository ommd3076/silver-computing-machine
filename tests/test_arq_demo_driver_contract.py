"""End-to-end contract checks for authenticated driver proposal and manifest flow."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import AuthConfig, TokenAuthMiddleware
from backend.demo.api import create_demo_router
from backend.demo.auth import DemoAuthManager
from backend.demo.service import DemoCoordinatorService
from backend.demo.store import DemoStore


def _app(db_path, config=None):
    store = DemoStore(db_path)
    service = DemoCoordinatorService(store)
    app = FastAPI()
    app.state.auth_config = config or AuthConfig.from_mapping("local")
    if config:
        app.add_middleware(TokenAuthMiddleware, config=config)
    app.include_router(create_demo_router(store, service, DemoAuthManager(store)))
    return app


def test_driver_scope_idempotent_proposal_publish_ack_and_restart(tmp_path):
    db_path = tmp_path / "driver.sqlite3"
    config = AuthConfig.from_mapping("token", {
        "dispatcher": "dispatcher-sentinel", "researcher": "researcher-sentinel", "admin": "admin-sentinel"
    })
    app = _app(db_path, config)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        a = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"}).json()
        b = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"}).json()
        ha, hb = {"Authorization": f"Bearer {a['token']}"}, {"Authorization": f"Bearer {b['token']}"}
        state_a = client.get("/api/v1/demo/state?driver_id=driver_2", headers=ha).json()
        assert state_a["driver_id"] == "driver_1"
        assert state_a["vehicle_id"] == "vehicle_1"
        assert state_a["stops"][0]["coordinates"] == [77.031, 28.479]
        assert "token" not in client.get("/api/v1/demo/me", headers=ha).json()

        request = {"event_id": "driver-event-1", "base_route_version": 1,
                   "severity": "heavy", "note": "traffic observed"}
        proposal = client.post("/api/v1/demo/reports", json=request, headers=ha)
        assert proposal.status_code == 202
        result = proposal.json()
        assert result["status"] == "proposal_pending"
        assert result["decision"] == "PROPOSE_ROUTE"
        assert result["published"] is False
        assert result["proposed_route_geojson"]["type"] == "Feature"
        assert client.get("/api/v1/demo/state", headers=ha).json()["route_version"] == 1
        assert client.post("/api/v1/demo/reports", json=request, headers=ha).json() == result
        conflict = client.post("/api/v1/demo/reports", json={**request, "note": "changed"}, headers=ha)
        assert conflict.status_code == 409
        assert client.get("/api/v1/demo/manifest", headers=hb).json()["driver_id"] == "driver_2"

        # The other driver's acknowledgement is only allowed to acknowledge their own manifest.
        ack_b = client.post("/api/v1/demo/acknowledgements",
                            json={"version": 1, "manifest_revision": 1}, headers=hb)
        assert ack_b.status_code == 200
        assert client.get("/api/v1/demo/state", headers=ha).json()["last_ack_version"] == 0
        bad_ack = client.post("/api/v1/demo/acknowledgements",
                              json={"version": 2, "manifest_revision": 2}, headers=ha)
        assert bad_ack.status_code == 409

        dispatcher_headers = {"Authorization": "Bearer dispatcher-sentinel"}
        published = client.post(f"/api/v1/demo/proposals/{result['proposal_id']}/approve", headers=dispatcher_headers)
        assert published.status_code == 200
        validation = published.json()["validation"]
        assert validation["status"] == "validated" and validation["valid"] is True
        assert validation["scope"].startswith("catalog vehicle/ordered-stop coverage/geometry/duration/distance only")
        manifest = client.get("/api/v1/demo/manifest", headers=ha).json()
        assert manifest["route_id"] == "route_v1_bypass"
        assert manifest["version"] == 2
        assert client.post(f"/api/v1/demo/proposals/{result['proposal_id']}/approve", headers=dispatcher_headers).json() == published.json()
        ack = client.post("/api/v1/demo/acknowledgements",
                          json={"version": 2, "manifest_revision": 2}, headers=ha).json()
        assert ack["status"] == "acknowledged"
        assert ack["manifest_revision"] == 2

    restarted = _app(db_path, config)
    with TestClient(restarted, base_url="http://127.0.0.1") as client:
        # Sessions and approved manifest survive router/service re-creation.
        assert client.get("/api/v1/demo/state", headers=ha).json()["route_id"] == "route_v1_bypass"
        recovered = client.get("/api/v1/demo/manifest", headers=ha).json()
        assert recovered["version"] == 2
        assert recovered["route_id"] == "route_v1_bypass"
        assert recovered["stops"][0]["id"] == "stop_1"
        assert client.get("/api/v1/demo/state", headers=hb).json()["last_ack_manifest_revision"] == 1
        assert client.get("/api/v1/demo/dispatcher/state",
                          headers={"Authorization": "Bearer researcher-sentinel"}).status_code == 403
        summary = client.get("/api/v1/demo/dispatcher/state",
                             headers={"Authorization": "Bearer dispatcher-sentinel"})
        assert summary.status_code == 200
        assert len(summary.json()["states"]) == 2
        assert summary.json()["proposals"][0]["status"] == "published"


def test_configured_dispatcher_role_is_required_for_publication(tmp_path):
    config = AuthConfig.from_mapping("token", {
        "dispatcher": "dispatcher-sentinel", "researcher": "researcher-sentinel", "admin": "admin-sentinel"
    })
    with TestClient(_app(tmp_path / "roles.sqlite3", config), base_url="http://127.0.0.1") as client:
        driver = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"}).json()
        proposal = client.post("/api/v1/demo/reports", headers={"Authorization": f"Bearer {driver['token']}"},
                              json={"event_id": "role-event", "base_route_version": 1,
                                    "severity": "heavy", "note": "jam"}).json()
        path = f"/api/v1/demo/proposals/{proposal['proposal_id']}/approve"
        assert client.post(path, headers={"Authorization": f"Bearer {driver['token']}"}).status_code == 401
        assert client.post(path, headers={"Authorization": "Bearer researcher-sentinel"}).status_code == 403
        response = client.post(path, headers={"Authorization": "Bearer dispatcher-sentinel"})
        assert response.status_code == 200
        assert response.json()["route_id"] == "route_v1_bypass"
