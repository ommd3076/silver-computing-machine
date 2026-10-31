"""In-process API contract for paired drivers and dispatcher-controlled swarm updates."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import AuthConfig, TokenAuthMiddleware
from backend.demo.api import create_demo_router
from backend.demo.auth import DemoAuthManager
from backend.demo.service import DemoCoordinatorService
from backend.demo.store import DemoStore


def _app(db_path):
    store = DemoStore(db_path)
    service = DemoCoordinatorService(store)
    config = AuthConfig.from_mapping("token", {
        "dispatcher": "dispatch-test-token",
        "researcher": "research-test-token",
        "admin": "admin-test-token",
    })
    app = FastAPI()
    app.state.auth_config = config
    app.add_middleware(TokenAuthMiddleware, config=config)
    app.include_router(create_demo_router(store, service, DemoAuthManager(store)))
    return app


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_two_driver_swarm_update_is_dispatcher_approved_isolated_and_durable(tmp_path):
    db_path = tmp_path / "swarm.sqlite3"
    app = _app(db_path)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        # Real pairing/session issuance maps each one-time code to its own driver.
        pair_a = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
        pair_b = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"})
        assert pair_a.status_code == pair_b.status_code == 200
        a, b = pair_a.json(), pair_b.json()
        assert (a["driver_id"], a["vehicle_id"]) == ("driver_1", "vehicle_1")
        assert (b["driver_id"], b["vehicle_id"]) == ("driver_2", "vehicle_2")
        ha, hb = _bearer(a["token"]), _bearer(b["token"])

        state_a = client.get("/api/v1/demo/state", headers=ha).json()
        state_b = client.get("/api/v1/demo/state", headers=hb).json()
        assert state_a["driver_id"] == "driver_1" and state_a["route_version"] == 1
        assert state_b["driver_id"] == "driver_2" and state_b["route_version"] == 1
        assert state_a["route_id"] != state_b["route_id"]

        # Congestion creates a persisted pending proposal; replay is idempotent,
        # while reusing the event ID with changed content is rejected.
        report = {"event_id": "swarm-event-1", "base_route_version": 1,
                  "severity": "heavy", "note": "blocked segment"}
        first = client.post("/api/v1/demo/reports", json=report, headers=ha)
        assert first.status_code == 202
        proposal = first.json()
        assert proposal["status"] == "proposal_pending"
        assert proposal["published"] is False
        assert proposal["decision"] == "PROPOSE_ROUTE"
        assert proposal["proposed_route_id"]
        assert proposal["active_overlays"]
        assert client.post("/api/v1/demo/reports", json=report, headers=ha).json() == proposal
        conflict = client.post("/api/v1/demo/reports", json={**report, "note": "different report"}, headers=ha)
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["error"]["code"] == "event_conflict"

        # The report alone never changes active assignments or manifests.
        assert client.get("/api/v1/demo/state", headers=ha).json()["route_version"] == 1
        manifest_a_before = client.get("/api/v1/demo/manifest", headers=ha)
        assert manifest_a_before.status_code == 200
        assert manifest_a_before.json()["route_id"] == state_a["route_id"]
        assert manifest_a_before.json()["version"] == 1
        manifest_b_before = client.get("/api/v1/demo/manifest", headers=hb)
        assert manifest_b_before.status_code == 200
        assert manifest_b_before.json()["route_id"] == state_b["route_id"]

        approve_path = f"/api/v1/demo/proposals/{proposal['proposal_id']}/approve"
        assert client.post(approve_path, headers=ha).status_code == 401
        assert client.post(approve_path, headers=_bearer("research-test-token")).status_code == 403
        approved = client.post(approve_path, headers=_bearer("dispatch-test-token"))
        assert approved.status_code == 200
        published = approved.json()
        assert published["driver_id"] == "driver_1"
        assert published["route_id"] == proposal["proposed_route_id"]
        assert published["version"] == 2
        assert published["validation"]["valid"] is True
        assert client.post(approve_path, headers=_bearer("dispatch-test-token")).json() == published

        # Acknowledging driver 1's new manifest cannot advance driver 2's state.
        ack_a = client.post("/api/v1/demo/acknowledgements",
                            json={"version": 2, "manifest_revision": 2}, headers=ha)
        assert ack_a.status_code == 200
        state_a_after_ack = client.get("/api/v1/demo/state", headers=ha).json()
        state_b_after_ack = client.get("/api/v1/demo/state", headers=hb).json()
        assert state_a_after_ack["last_ack_version"] == 2
        assert state_b_after_ack["route_version"] == 1
        assert state_b_after_ack["last_ack_version"] == 0
        assert state_b_after_ack["route_id"] == state_b["route_id"]

        # Driver 2 cannot acknowledge a version/revision that belongs to driver 1.
        foreign_ack = client.post("/api/v1/demo/acknowledgements",
                                  json={"version": 2, "manifest_revision": 2}, headers=hb)
        assert foreign_ack.status_code == 409
        ack_b = client.post("/api/v1/demo/acknowledgements",
                            json={"version": 1, "manifest_revision": 1}, headers=hb)
        assert ack_b.status_code == 200

    # Rebuild the router/service over the same SQLite file to exercise recovery.
    with TestClient(_app(db_path), base_url="http://127.0.0.1") as client:
        recovered_a = client.get("/api/v1/demo/state", headers=ha).json()
        recovered_b = client.get("/api/v1/demo/state", headers=hb).json()
        assert recovered_a["route_id"] == proposal["proposed_route_id"]
        assert recovered_a["route_version"] == 2
        assert recovered_a["last_ack_version"] == 2
        assert recovered_b["route_id"] == state_b["route_id"]
        assert recovered_b["route_version"] == 1
        assert recovered_b["last_ack_version"] == 1
        assert client.get("/api/v1/demo/manifest", headers=ha).json()["version"] == 2
        assert client.get("/api/v1/demo/manifest", headers=hb).json()["route_id"] == state_b["route_id"]
        dispatcher = client.get("/api/v1/demo/dispatcher/state", headers=_bearer("dispatch-test-token"))
        assert dispatcher.status_code == 200
        assert len(dispatcher.json()["states"]) == 2
        assert dispatcher.json()["proposals"][0]["status"] == "published"
