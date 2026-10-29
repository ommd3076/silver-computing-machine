"""Tests for routing logic, GeoJSON coordinate ordering, stop preservation, and decision switching."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_initial_driver_states_and_provenance(
    client: TestClient,
    paired_driver_1: dict[str, str],
    paired_driver_2: dict[str, str],
):
    h1 = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    h2 = {"Authorization": f"Bearer {paired_driver_2['token']}"}

    # Driver 1
    r1 = client.get("/api/v1/demo/state", headers=h1)
    assert r1.status_code == 200
    s1 = r1.json()
    assert s1["driver_id"] == "driver_1"
    assert s1["vehicle_id"] == "vehicle_1"
    assert s1["route_id"] == "route_v1_primary"
    assert s1["corridor_id"] == "corridor_a_expressway"
    assert s1["route_version"] == 1
    assert s1["simulation_mode"] is True
    assert s1["data_provenance"] == "synthetic_delhivery_v1"
    assert s1["estimated_duration_seconds"] > 0
    assert len(s1["stops"]) == 4
    assert [st["id"] for st in s1["stops"]] == ["depot", "stop_1", "stop_2", "depot"]

    # GeoJSON coordinate ordering check [longitude, latitude]
    coords1 = s1["geojson"]["geometry"]["coordinates"]
    for pt in coords1:
        lon, lat = pt[0], pt[1]
        assert 76.5 <= lon <= 77.5, f"Expected Delhi longitude around 77, got {lon}"
        assert 28.0 <= lat <= 29.0, f"Expected Delhi latitude around 28.5, got {lat}"

    # Driver 2
    r2 = client.get("/api/v1/demo/state", headers=h2)
    assert r2.status_code == 200
    s2 = r2.json()
    assert s2["driver_id"] == "driver_2"
    assert s2["vehicle_id"] == "vehicle_2"
    assert s2["route_id"] == "route_v2_primary"
    assert s2["corridor_id"] == "corridor_c_south"
    assert s2["route_version"] == 1
    assert len(s2["stops"]) == 4
    assert [st["id"] for st in s2["stops"]] == ["depot", "stop_3", "stop_4", "depot"]


def test_manual_plan_route_with_no_incident(client: TestClient, paired_driver_1: dict[str, str]):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req-manual-01", "base_route_version": 1},
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["outcome"] == "KEEP"
    assert data["result"]["decision"] == "KEEP"
    assert data["result"]["published"] is False


def test_moderate_congestion_retains_expressway(client: TestClient, paired_driver_1: dict[str, str]):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-mod-001",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "moderate",
            "note": "Minor traffic delay",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    # Moderate delay (+180s) leaves expressway at 900s, still faster than 960s bypass -> KEEP
    assert data["decision"] == "KEEP"
    assert data["published_new_route"] is False
    assert data["current_route_version"] == 1

    # Verify state route_version unchanged
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert st["route_version"] == 1
    assert st["route_id"] == "route_v1_primary"


def test_heavy_congestion_triggers_bypass_publication(
    client: TestClient, paired_driver_1: dict[str, str]
):
    headers = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    resp = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-hvy-001",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
            "note": "Complete gridlock on Expressway",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    # Heavy delay (+480s) saves 240s via Mehrauli bypass -> AUTO-PUBLISH
    assert data["decision"] == "PUBLISHED_NEW_ROUTE"
    assert data["published_new_route"] is True
    assert data["current_route_version"] == 2

    # Verify state incremented exactly once
    st = client.get("/api/v1/demo/state", headers=headers).json()
    assert st["route_version"] == 2
    assert st["route_id"] == "route_v1_bypass"
    assert st["corridor_id"] == "corridor_b_bypass"
    # Verify stops are preserved and ordered
    assert [s["id"] for s in st["stops"]] == ["depot", "stop_1", "stop_2", "depot"]
