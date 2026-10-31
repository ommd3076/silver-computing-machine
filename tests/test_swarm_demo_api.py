"""Boundary tests for the authenticated two-driver local demo API."""

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


def _error(response):
    assert "detail" in response.json()
    return response.json()["detail"]["error"]["code"]


def test_driver_identity_is_session_scoped_and_input_errors_are_stable(tmp_path):
    with TestClient(_app(tmp_path / "scope.sqlite3"), base_url="http://127.0.0.1") as client:
        malformed_pair = client.post("/api/v1/demo/sessions", json={"code": "PAIR01", "role": "admin"})
        assert malformed_pair.status_code == 422
        assert _error(malformed_pair) == "invalid_code"
        a = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"}).json()
        b = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"}).json()
        ha, hb = ({"Authorization": f"Bearer {a['token']}"},
                  {"Authorization": f"Bearer {b['token']}"})

        state_a = client.get("/api/v1/demo/state?driver_id=driver_2", headers=ha)
        assert state_a.status_code == 200
        assert state_a.json()["driver_id"] == "driver_1"
        assert state_a.json()["vehicle_id"] == "vehicle_1"
        assert client.get("/api/v1/demo/manifest", headers=hb).json()["driver_id"] == "driver_2"

        for malformed in (
            {"event_id": "  ", "base_route_version": 1},
            {"event_id": "bad-note", "base_route_version": 1, "note": 7},
            {"event_id": "bad-version", "base_route_version": True},
            {"event_id": "bad-severity", "base_route_version": 1, "severity": ["heavy"]},
            {"event_id": "spoof", "base_route_version": 1, "driver_id": "driver_2"},
        ):
            response = client.post("/api/v1/demo/reports", json=malformed, headers=ha)
            assert response.status_code == 422
            assert _error(response) in {"invalid_report", "invalid_version"}
            assert a["token"] not in response.text

        ack_spoof = client.post("/api/v1/demo/acknowledgements",
                                json={"version": 1, "manifest_revision": 1, "driver_id": "driver_2"},
                                headers=ha)
        assert ack_spoof.status_code == 422
        ack_b = client.post("/api/v1/demo/acknowledgements",
                            json={"version": 1, "manifest_revision": 1}, headers=hb)
        assert ack_b.status_code == 200
        assert client.get("/api/v1/demo/state", headers=ha).json()["last_ack_version"] == 0


def test_dispatcher_local_mode_checks_peer_loopback_and_token_mode_checks_role(tmp_path):
    local = _app(tmp_path / "local.sqlite3")
    with TestClient(local, base_url="http://127.0.0.1", client=("127.0.0.1", 1234)) as client:
        assert client.get("/api/v1/demo/dispatcher/state").status_code == 200
    with TestClient(local, base_url="http://192.0.2.10", client=("192.0.2.10", 1234)) as client:
        denied = client.get("/api/v1/demo/audits")
        assert denied.status_code == 403
        assert _error(denied) == "dispatcher_required"

    config = AuthConfig.from_mapping("token", {
        "dispatcher": "dispatcher-sentinel",
        "researcher": "researcher-sentinel",
        "admin": "admin-sentinel",
    })
    with TestClient(_app(tmp_path / "token.sqlite3", config), base_url="http://127.0.0.1") as client:
        path = "/api/v1/demo/dispatcher/state"
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer researcher-sentinel"}).status_code == 403
        assert client.get(path, headers={"Authorization": "Bearer dispatcher-sentinel"}).status_code == 200


def test_service_exception_text_is_never_returned_as_an_error_code(tmp_path, monkeypatch):
    def leak(*args, **kwargs):
        raise ValueError("private-service-detail")

    monkeypatch.setattr(DemoCoordinatorService, "report_congestion", leak)
    monkeypatch.setattr(DemoCoordinatorService, "acknowledge", leak)
    monkeypatch.setattr(DemoCoordinatorService, "publish_proposal", leak)
    with TestClient(_app(tmp_path / "errors.sqlite3"), base_url="http://127.0.0.1",
                    client=("127.0.0.1", 1234)) as client:
        driver = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"}).json()
        headers = {"Authorization": f"Bearer {driver['token']}"}
        report = client.post("/api/v1/demo/reports", headers=headers,
                             json={"event_id": "safe-error", "base_route_version": 1})
        acknowledgement = client.post("/api/v1/demo/acknowledgements", headers=headers,
                                      json={"version": 1, "manifest_revision": 1})
        approval = client.post("/api/v1/demo/proposals/arbitrary-id/approve")
        assert [_error(report), _error(acknowledgement), _error(approval)] == [
            "invalid_report", "acknowledgement_conflict", "proposal_conflict"]
        assert "private-service-detail" not in (report.text + acknowledgement.text + approval.text)
