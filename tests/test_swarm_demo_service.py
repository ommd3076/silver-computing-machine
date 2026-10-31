"""Focused regressions for congestion evaluation and driver-scoped publication."""

import json

import pytest

from backend.demo.service import DemoCoordinatorService
from backend.demo.store import DemoStore


def _service(tmp_path):
    store = DemoStore(tmp_path / "swarm-demo.sqlite3")
    return store, DemoCoordinatorService(store)


def _candidate_proposal(service, driver_id="driver_1"):
    state = service.store.get_driver_state(driver_id)
    current = service.catalog.get_candidate(state["route_id"])
    target = service.catalog.get_candidate("route_v1_bypass")
    overlays = {"seg_nh48_exp": 480.0}
    current_duration = service.catalog.score_route(current, overlays)
    proposed_duration = service.catalog.score_route(target, overlays)
    result = {
        "proposed_route_id": target.route_id,
        "proposed_corridor_id": target.corridor_id,
        "base_route_version": state["route_version"],
        "current_duration_seconds": current_duration,
        "proposed_duration_seconds": proposed_duration,
        "time_saved_seconds": current_duration - proposed_duration,
        "proposed_route_geojson": target.to_geojson(),
        "active_overlays": overlays,
    }
    return {
        "driver_id": driver_id,
        "route_id": target.route_id,
        "corridor_id": target.corridor_id,
        "base_route_version": state["route_version"],
        "proposal": result,
    }


def test_congestion_candidate_is_deterministic_and_keeps_active_route(tmp_path):
    store, service = _service(tmp_path)
    state = store.get_driver_state("driver_1")
    store.save_congestion_report("stress-event", "driver_1", "vehicle_1", "seg_nh48_exp",
                                 "heavy", 480.0, "2999-01-01T00:00:00+00:00")
    result = service._evaluate_proposal("driver_1", state)
    assert result["decision"] == "PROPOSE_ROUTE"
    assert result["route_id"] == "route_v1_bypass"
    assert result["time_saved_seconds"] == 240.0
    assert store.get_driver_state("driver_1")["route_version"] == 1


def test_independent_validation_recomputes_switch_and_marks_finance_unavailable(tmp_path):
    _, service = _service(tmp_path)
    proposal = _candidate_proposal(service)
    report = service.validate_proposal(proposal)
    assert report["valid"] is True
    assert report["checks"]["switch_threshold_met"] is True
    assert report["financial_metrics"]["status"] == "unavailable"
    assert "financial_objective" in report["unavailable"]

    proposal["proposal"]["proposed_duration_seconds"] -= 1
    report = service.validate_proposal(proposal)
    assert report["valid"] is False
    assert report["checks"]["duration_recomputed"] is False


def test_report_idempotency_replays_before_stale_version_check(tmp_path, monkeypatch):
    store, service = _service(tmp_path)

    # Avoid coupling this service-level regression to proposal-table migrations.
    def save_event(event_id, driver_id, request_hash, proposal_id, version, route_id, corridor_id, result):
        with store._get_connection() as conn:
            conn.execute("INSERT INTO demo_events VALUES(?,?,?,?,?)",
                         (event_id, driver_id, request_hash, json.dumps(result), "2026-10-30T00:00:00+00:00"))
        return result

    monkeypatch.setattr(store, "create_event_proposal", save_event)
    first = service.report_congestion("driver_1", "repeat-event", 1, "heavy", "traffic")
    store.update_driver_route("driver_1", "route_v1_bypass", "corridor_b_bypass")
    replay = service.report_congestion("driver_1", "repeat-event", 1, "heavy", "traffic")
    assert replay == first
    with pytest.raises(ValueError, match="event_conflict"):
        service.report_congestion("driver_1", "repeat-event", 1, "moderate", "changed")


def test_plan_route_rejects_stale_and_cross_driver_idempotency_keys(tmp_path):
    store, service = _service(tmp_path)
    with pytest.raises(ValueError, match="stale_version"):
        service.request_plan_route("driver_1", "plan-key", 2)

    service.request_plan_route("driver_1", "shared-key", 1)
    with pytest.raises(ValueError, match="request_conflict"):
        service.request_plan_route("driver_2", "shared-key", 1)

    # Driver state and route versions remain isolated.
    assert store.get_driver_state("driver_1")["route_version"] == 1
    assert store.get_driver_state("driver_2")["route_version"] == 1


def test_approval_retry_returns_its_committed_manifest_after_a_later_version(tmp_path):
    store, service = _service(tmp_path)
    proposal = service.report_congestion("driver_1", "publish-event", 1, "heavy", "jam")
    manifest_v2 = service.publish_proposal(proposal["proposal_id"], "dispatcher")
    assert manifest_v2["route_version"] == 2
    event_replay = service.report_congestion("driver_1", "publish-event", 1, "heavy", "jam")
    assert event_replay["published"] is True
    assert event_replay["published_manifest"] == manifest_v2

    # Simulate a later valid assignment. Replaying the first approval must not
    # accidentally return that newer manifest as the first approval's result.
    store.update_driver_route("driver_1", "route_v1_primary", "corridor_a_expressway")
    replayed = service.publish_proposal(proposal["proposal_id"], "dispatcher")
    assert replayed == manifest_v2
    assert store.get_driver_state("driver_1")["route_version"] == 3
