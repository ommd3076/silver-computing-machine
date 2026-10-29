"""Tests for cross-device state isolation, concurrent mutations, and CAS safety."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient


def test_cross_device_isolation_phone_b_unaffected(
    client: TestClient,
    paired_driver_1: dict[str, str],
    paired_driver_2: dict[str, str],
):
    h1 = {"Authorization": f"Bearer {paired_driver_1['token']}"}
    h2 = {"Authorization": f"Bearer {paired_driver_2['token']}"}

    # Initial check: both drivers are at route_version=1
    s1_init = client.get("/api/v1/demo/state", headers=h1).json()
    s2_init = client.get("/api/v1/demo/state", headers=h2).json()
    assert s1_init["route_version"] == 1
    assert s2_init["route_version"] == 1

    # Phone A (Driver 1) reports heavy congestion on NH-48 Expressway
    r_cong = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-d1-cong",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
        },
        headers=h1,
    )
    assert r_cong.status_code == 202
    assert r_cong.json()["current_route_version"] == 2

    # Verify Phone A receives new route v2
    s1_after = client.get("/api/v1/demo/state", headers=h1).json()
    assert s1_after["route_version"] == 2
    assert s1_after["route_id"] == "route_v1_bypass"
    assert s1_after["corridor_id"] == "corridor_b_bypass"

    # CRITICAL CHECK: Phone B (Driver 2) remains strictly unaffected!
    s2_after = client.get("/api/v1/demo/state", headers=h2).json()
    assert s2_after["route_version"] == 1
    assert s2_after["route_id"] == "route_v2_primary"
    assert s2_after["corridor_id"] == "corridor_c_south"
    # Delay on Driver 2's route segments should still be 0 (NH-48 congestion does not impact South Arterial)
    cand2_delays = sum(s2_after["active_overlays"].get(s["id"], 0.0) for s in s2_after["stops"])
    assert cand2_delays == 0.0


def test_concurrent_cas_mutations(isolated_app):
    """Test that concurrent compare-and-swap mutations allow exactly one winner."""
    store = isolated_app.store
    driver_id = "driver_1"
    base_version = 1

    results = []

    def attempt_mutation(idx: int):
        try:
            res = store.atomic_publish_route(
                driver_id=driver_id,
                base_route_version=base_version,
                new_route_id=f"route_alt_{idx}",
                new_corridor_id=f"corridor_alt_{idx}",
                audit_event_type="test_concurrent_publish",
                audit_payload={"thread_idx": idx},
            )
            return ("success", res)
        except Exception as exc:
            return ("error", type(exc).__name__)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_mutation, i) for i in range(5)]
        results = [f.result() for f in futures]

    successes = [r for r in results if r[0] == "success"]
    conflicts = [r for r in results if r[0] == "error"]

    # Exactly ONE CAS operation must succeed
    assert len(successes) == 1
    # All others must fail with StaleVersionError
    assert len(conflicts) == 4
    for _, err_name in conflicts:
        assert err_name == "StaleVersionError"

    # Final route_version is exactly 2
    state = store.get_driver_state(driver_id)
    assert state["route_version"] == 2
