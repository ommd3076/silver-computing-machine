"""Tests for DebugLeaf Web UI integration."""

from fastapi.testclient import TestClient

from backend.api import app

client = TestClient(app)


def test_ui_index_endpoints() -> None:
    for path in ("/", "/ui"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        body = response.text
        assert "DebugLeaf Platform" in body
        assert "Fleet Dispatch" in body
        assert "India Delivery ETA" in body
        assert "/api/v1/health" in body
        assert "/api/v1/scenarios/plan" in body
        assert "/api/v1/scenarios/qaoa" in body
