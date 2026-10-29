"""Full end-to-end integration test flow for two drivers, mobile polling, and dispatcher."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_complete_two_driver_demo_lifecycle(client: TestClient):
    dispatcher_headers = {"Authorization": "Bearer valid_dispatcher_token_secret_12345"}

    # -------------------------------------------------------------------------
    # 1. Pairing Phone A (Driver 1) and Phone B (Driver 2)
    # -------------------------------------------------------------------------
    r_pair_a = client.post("/api/v1/demo/sessions", json={"code": "PAIR01"})
    assert r_pair_a.status_code == 200
    token_a = r_pair_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_pair_b = client.post("/api/v1/demo/sessions", json={"code": "PAIR02"})
    assert r_pair_b.status_code == 200
    token_b = r_pair_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # -------------------------------------------------------------------------
    # 2. Initial state sync for both phones
    # -------------------------------------------------------------------------
    s_a = client.get("/api/v1/demo/state", headers=headers_a).json()
    assert s_a["driver_id"] == "driver_1"
    assert s_a["route_id"] == "route_v1_primary"
    assert s_a["route_version"] == 1
    assert s_a["last_ack_version"] == 0

    s_b = client.get("/api/v1/demo/state", headers=headers_b).json()
    assert s_b["driver_id"] == "driver_2"
    assert s_b["route_id"] == "route_v2_primary"
    assert s_b["route_version"] == 1
    assert s_b["last_ack_version"] == 0

    # -------------------------------------------------------------------------
    # 3. Initial dispatcher overview check
    # -------------------------------------------------------------------------
    disp_init = client.get("/api/v1/demo/dispatcher/overview", headers=dispatcher_headers).json()
    assert len(disp_init["drivers"]) == 2
    assert len(disp_init["active_incidents"]) == 0

    # -------------------------------------------------------------------------
    # 4. Manual "Plan Route" tap on Phone A (no incident -> KEEP)
    # -------------------------------------------------------------------------
    r_plan = client.post(
        "/api/v1/demo/route-requests",
        json={"request_id": "req-client-001", "base_route_version": 1},
        headers=headers_a,
    )
    assert r_plan.status_code == 202
    assert r_plan.json()["outcome"] == "KEEP"

    # State on Phone A remains version 1
    assert client.get("/api/v1/demo/state", headers=headers_a).json()["route_version"] == 1

    # -------------------------------------------------------------------------
    # 5. Congestion Reported by Driver 1 (Heavy congestion on Expressway)
    # -------------------------------------------------------------------------
    r_cong = client.post(
        "/api/v1/demo/reports",
        json={
            "event_id": "evt-client-cong-001",
            "base_route_version": 1,
            "kind": "congestion",
            "severity": "heavy",
            "note": "Severe traffic jam at Mahipalpur flyover",
        },
        headers=headers_a,
    )
    assert r_cong.status_code == 202
    cong_data = r_cong.json()
    assert cong_data["decision"] == "PUBLISHED_NEW_ROUTE"
    assert cong_data["published_new_route"] is True
    assert cong_data["current_route_version"] == 2

    # -------------------------------------------------------------------------
    # 6. Phone A polls and renders revision 2; acknowledges version 2
    # -------------------------------------------------------------------------
    s_a_updated = client.get("/api/v1/demo/state", headers=headers_a).json()
    assert s_a_updated["route_version"] == 2
    assert s_a_updated["route_id"] == "route_v1_bypass"
    assert s_a_updated["corridor_id"] == "corridor_b_bypass"

    # Phone A sends acknowledgement
    r_ack = client.post(
        "/api/v1/demo/acknowledgements",
        json={"route_version": 2, "client_timestamp": "2026-10-30T01:45:00.000Z"},
        headers=headers_a,
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["version"] == 2

    # -------------------------------------------------------------------------
    # 7. CRITICAL VERIFICATION: Phone B (Driver 2) remains isolated & untouched
    # -------------------------------------------------------------------------
    s_b_poll = client.get("/api/v1/demo/state", headers=headers_b).json()
    assert s_b_poll["driver_id"] == "driver_2"
    assert s_b_poll["route_id"] == "route_v2_primary"
    assert s_b_poll["route_version"] == 1

    # -------------------------------------------------------------------------
    # 8. Dispatcher observes authoritative state matching both devices
    # -------------------------------------------------------------------------
    disp_after = client.get("/api/v1/demo/dispatcher/overview", headers=dispatcher_headers).json()
    assert len(disp_after["active_incidents"]) == 1
    assert disp_after["active_incidents"][0]["event_id"] == "evt-client-cong-001"

    d1_disp = next(d for d in disp_after["drivers"] if d["driver_id"] == "driver_1")
    assert d1_disp["route_version"] == 2
    assert d1_disp["corridor"] == "corridor_b_bypass"
    assert d1_disp["last_ack_version"] == 2
    assert d1_disp["active_delay_seconds"] == 480.0

    d2_disp = next(d for d in disp_after["drivers"] if d["driver_id"] == "driver_2")
    assert d2_disp["route_version"] == 1
    assert d2_disp["corridor"] == "corridor_c_south"

    # -------------------------------------------------------------------------
    # 9. Session logout and invalidation
    # -------------------------------------------------------------------------
    r_logout = client.delete("/api/v1/demo/sessions/current", headers=headers_a)
    assert r_logout.status_code == 200

    r_unauth = client.get("/api/v1/demo/state", headers=headers_a)
    assert r_unauth.status_code == 401
