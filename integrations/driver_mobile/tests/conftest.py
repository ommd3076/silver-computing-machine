"""Shared pytest fixtures for driver mobile integration tests."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from integrations.driver_mobile.server.app import create_composite_app, DEMO_FIXTURE_CODES
from integrations.driver_mobile.server.config import IntegrationConfig


@pytest.fixture
def isolated_app():
    """Create test application with an isolated temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_demo_store.sqlite3"
        cfg = IntegrationConfig(
            db_path=db_path,
            auth_mode="token",
            dispatcher_token="valid_dispatcher_token_secret_12345",
            admin_token="valid_admin_token_secret_67890",
            researcher_token="valid_researcher_token_secret_11223",
            session_ttl_minutes=60,
            pairing_max_attempts=5,
            pairing_window_seconds=60,
            fixture_mode=True,
            host="127.0.0.1",
            port=8000,
        )
        app = create_composite_app(cfg=cfg)
        # Pre-seed pairing codes
        app.store.seed_pairing_codes(DEMO_FIXTURE_CODES, reset=True)
        yield app


@pytest.fixture
def client(isolated_app) -> Generator[TestClient, None, None]:
    with TestClient(isolated_app) as tc:
        yield tc


@pytest.fixture
def paired_driver_1(client: TestClient) -> dict[str, str]:
    """Helper fixture providing an authenticated session for Driver 1."""
    resp = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {"token": data["token"], "driver_id": "driver_1", "vehicle_id": "vehicle_1"}


@pytest.fixture
def paired_driver_2(client: TestClient) -> dict[str, str]:
    """Helper fixture providing an authenticated session for Driver 2."""
    resp = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {"token": data["token"], "driver_id": "driver_2", "vehicle_id": "vehicle_2"}
