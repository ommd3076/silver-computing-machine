"""Tests for API contract compliance, OpenAPI generation, and backend compatibility."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_existing_backend_health_and_scenarios_preserved(client: TestClient):
    # Core health endpoint preserved
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    data = r_health.json()
    assert data["status"] == "ok"
    assert "api_version" in data

    # Core scenario validation preserved
    import json
    from pathlib import Path
    fixture_path = Path(__file__).parents[3] / "fixtures" / "dispatch_tiny.json"
    valid_scenario = json.loads(fixture_path.read_text())
    headers = {"Authorization": "Bearer valid_researcher_token_secret_11223"}
    r_val = client.post("/api/v1/scenarios/validate", json=valid_scenario, headers=headers)
    assert r_val.status_code == 200
    assert r_val.json()["valid"] is True


def test_existing_backend_eta_route_preserved(client: TestClient):
    import json
    from pathlib import Path
    fixture_path = Path(__file__).parents[3] / "fixtures" / "india_eta" / "prediction_request.json"
    if fixture_path.exists():
        payload = json.loads(fixture_path.read_text())
        payload["features"]["distance_km"] = 1.875
        headers = {"Authorization": "Bearer valid_researcher_token_secret_11223"}
        resp = client.post("/api/v1/eta/predictions", json=payload, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "predicted_duration_minutes" in data
        assert data["predicted_duration_minutes"] == 20



def test_demo_openapi_schema_contains_all_demo_routes(client: TestClient):
    resp = client.get("/api/v1/demo/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    paths = openapi.get("paths", {})

    expected_paths = [
        "/api/v1/demo/sessions",
        "/api/v1/demo/sessions/current",
        "/api/v1/demo/me",
        "/api/v1/demo/state",
        "/api/v1/demo/reports",
        "/api/v1/demo/route-requests",
        "/api/v1/demo/jobs/{job_id}",
        "/api/v1/demo/acknowledgements",
        "/api/v1/demo/dispatcher/overview",
    ]

    for p in expected_paths:
        assert p in paths, f"Expected endpoint '{p}' missing from demo OpenAPI schema"
