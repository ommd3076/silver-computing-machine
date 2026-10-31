import time
import json

import pytest
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from backend.api import create_app
from backend.jobs import JobManager


class _Response:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return json.loads(self._body)


class _Client:
    def __init__(self, app):
        self.app = app

    def _call(self, method, path, payload=None):
        for route in self.app.routes:
            if not isinstance(route, APIRoute) or method not in route.methods:
                continue
            if route.path == path:
                result = route.endpoint(payload) if method == "POST" else route.endpoint()
                if isinstance(result, JSONResponse):
                    return _Response(result.status_code, result.body)
                return _Response(route.status_code or 200, json.dumps(result).encode())
            if "{run_id}" in route.path:
                prefix, suffix = route.path.split("{run_id}")
                if path.startswith(prefix) and path.endswith(suffix):
                    run_id = path[len(prefix):len(path) - len(suffix) if suffix else None]
                    result = route.endpoint(run_id)
                    if isinstance(result, JSONResponse):
                        return _Response(result.status_code, result.body)
                    return _Response(route.status_code or 200, json.dumps(result).encode())
        return _Response(404, b'{"error":{"code":"not_found"}}')

    def get(self, path):
        return self._call("GET", path)

    def post(self, path, json=None):
        return self._call("POST", path, json)


@pytest.fixture
def manager(tmp_path):
    value = JobManager(tmp_path / "jobs.sqlite3", max_workers=2, timeout_seconds=2)
    yield value
    value.close(wait=True)


@pytest.fixture
def client(manager):
    return _Client(create_app(manager))


def test_health_advertises_no_unverified_solver_labels(client):
    health = client.get("/api/v1/health").json()
    assert health["engines_available"] == ["exact_enumeration", "qaoa_warm_start", "vqc_inference"]
    assert "qpiai_opt_local" not in health["engines_available"]
    assert "financial_cover" not in health["engines_available"]


def test_fixture_runs_and_unverified_evaluation_are_labelled_or_omitted(client):
    runs = client.get("/api/v1/runs").json()
    assert runs and all(run["data_source"] == "fixture" and run["provenance_badge"] == "Preview" for run in runs)
    evidence = client.get("/api/v1/intelligence/evidence").json()
    assert evidence["user_claim_verified"] is False
    assert evidence["brier_score"] is None and evidence["calibration_points"] == []
    assert evidence["benchmarks"] == []
    assert client.get("/api/v1/events").json() == []


def test_solve_rejects_engine_and_scenario_that_cannot_be_executed(client):
    unsupported = client.post("/api/v1/solve", json={"scenario_id": "blr-urban-express", "engine": "qpiai_opt"})
    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["code"] == "unsupported_capability"

    missing = client.post("/api/v1/solve", json={"scenario_id": "blr-urban-express", "engine": "exact"})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "invalid_request"


def test_named_dispatch_tiny_exact_solve_persists_truthful_metadata(client, manager):
    submitted = client.post("/api/v1/solve", json={"scenario_id": "dispatch_tiny", "engine": "exact_enumeration"})
    assert submitted.status_code == 202
    job_id = submitted.json()["job_id"]
    deadline = time.monotonic() + 3
    current = manager.get(job_id)
    while current["status"] in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(0.01)
        current = manager.get(job_id)
    assert current["status"] == "succeeded"
    assert current["metadata"]["solver"] == "exact_enumeration"
    assert current["metadata"]["execution_type"] == "local_classical"
    assert current["metadata"]["request_sha256"]
    assert current["result"]["validation"]["valid"]


def test_recovery_refuses_fixture_mutation_and_invented_exposure(client):
    before = client.get("/api/v1/runs/run-blr-20261029-01").json()
    response = client.post("/api/v1/recovery/replan", json={
        "run_id": "run-blr-20261029-01", "vehicle_id": "van-blr-01",
        "delayed_stop_id": "stop-blr-04", "delay_minutes": 25, "locked_stop_ids": []
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "unsupported_capability"
    after = client.get("/api/v1/runs/run-blr-20261029-01").json()
    assert after["total_sla_exposure_inr"] == before["total_sla_exposure_inr"]
    assert after["provenance_badge"] == before["provenance_badge"]
