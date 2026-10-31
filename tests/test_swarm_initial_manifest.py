"""Regression coverage for the first mobile refresh after pairing."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import AuthConfig
from backend.demo.api import create_demo_router
from backend.demo.auth import DemoAuthManager
from backend.demo.service import DemoCoordinatorService
from backend.demo.store import DemoStore


def test_fresh_pairing_returns_initial_manifest_matching_authoritative_state(tmp_path):
    store = DemoStore(tmp_path / "fresh-pairing.sqlite3")
    service = DemoCoordinatorService(store)
    app = FastAPI()
    app.state.auth_config = AuthConfig.from_mapping("local")
    app.include_router(create_demo_router(store, service, DemoAuthManager(store)))

    with TestClient(app, base_url="http://127.0.0.1") as client:
        for code, expected_driver, expected_vehicle in (
            ("PAIR01", "driver_1", "vehicle_1"),
            ("PAIR02", "driver_2", "vehicle_2"),
        ):
            paired = client.post("/api/v1/demo/sessions", json={"code": code})
            assert paired.status_code == 200
            headers = {"Authorization": f"Bearer {paired.json()['token']}"}
            state = client.get("/api/v1/demo/state", headers=headers)
            manifest = client.get("/api/v1/demo/manifest", headers=headers)

            assert state.status_code == 200
            assert manifest.status_code == 200
            state_body, manifest_body = state.json(), manifest.json()
            assert state_body["driver_id"] == manifest_body["driver_id"] == expected_driver
            assert state_body["vehicle_id"] == manifest_body["vehicle_id"] == expected_vehicle
            assert state_body["route_id"] == manifest_body["route_id"]
            assert state_body["route_version"] == manifest_body["route_version"] == 1
            assert state_body["manifest_revision"] == manifest_body["version"] == 1
