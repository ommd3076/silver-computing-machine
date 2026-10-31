"""Core application service and route publication coordinator for the phone demo.

Orchestrates:
  - Current driver state & GeoJSON route retrieval
  - Congestion admission & segment delay overlays
  - Candidate scoring & deterministic tie-break selection
  - Automatic publication policy (same vehicle, remaining stops covered)
  - Full audit logging of all decisions
"""

from __future__ import annotations

import uuid
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .routes import RouteCatalog, RouteCandidate
from .store import DemoStore


def _finite_close(actual: float, supplied: Any) -> bool:
    return (not isinstance(supplied, bool) and isinstance(supplied, (int, float))
            and math.isfinite(supplied) and math.isclose(actual, supplied, rel_tol=1e-9, abs_tol=1e-6))


class DemoCoordinatorService:
    """Coordinates driver actions, incident admissions, and route publication."""

    def __init__(self, store: DemoStore, catalog: RouteCatalog | None = None) -> None:
        self.store = store
        self.catalog = catalog or RouteCatalog()
        self._ensure_default_state()

    def _ensure_default_state(self) -> None:
        """Seed default routes for demo drivers."""
        # Vehicle 1 -> Driver 1
        d1 = self.catalog.get_default_route("vehicle_1")
        if d1:
            self.store.init_driver_state_if_missing("driver_1", "vehicle_1", d1.route_id, d1.corridor_id)
        # Vehicle 2 -> Driver 2
        d2 = self.catalog.get_default_route("vehicle_2")
        if d2:
            self.store.init_driver_state_if_missing("driver_2", "vehicle_2", d2.route_id, d2.corridor_id)

    # -------------------------------------------------------------------------
    # Driver State & Navigation
    # -------------------------------------------------------------------------

    def get_driver_state(self, driver_id: str) -> dict[str, Any] | None:
        state = self.store.get_driver_state(driver_id)
        if not state:
            return None

        route_id = state["route_id"]
        candidate = self.catalog.get_candidate(route_id)
        overlays = self.store.get_active_overlays()
        current_duration = self.catalog.score_route(candidate, overlays) if candidate else 0.0

        return {
            "driver_id": driver_id,
            "vehicle_id": state["vehicle_id"],
            "route_id": route_id,
            "corridor_id": state["corridor_id"],
            "route_version": state["route_version"],
            "manifest_revision": state["manifest_revision"],
            "status": state["status"],
            "estimated_duration_seconds": current_duration,
            "estimated_distance_metres": candidate.total_distance_metres if candidate else 0.0,
            "active_overlays": overlays,
            "geojson": candidate.to_geojson() if candidate else None,
            "last_ack_version": state.get("last_ack_version", 0),
            "last_ack_manifest_revision": state.get("last_ack_manifest_revision", 0),
            "last_ack_at": state.get("last_ack_at"),
            "updated_at": state["updated_at"],
        }

    # -------------------------------------------------------------------------
    # Planning Route Requests
    # -------------------------------------------------------------------------

    def request_plan_route(
        self, driver_id: str, request_id: str, base_route_version: int
    ) -> dict[str, Any]:
        """Driver taps 'Plan route'. Runs deterministic candidate evaluation."""
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
            raise ValueError("invalid_request_id")
        state = self.store.get_driver_state(driver_id)
        if not state:
            raise ValueError(f"Unknown driver {driver_id}")
        if isinstance(base_route_version, bool) or not isinstance(base_route_version, int) or base_route_version < 1:
            raise ValueError("invalid_version")
        if base_route_version != state["route_version"]:
            raise ValueError("stale_version")

        job_id = f"job_plan_{uuid.uuid4().hex[:12]}"
        job = self.store.create_or_get_job(job_id, driver_id, request_id)
        if job.get("driver_id") != driver_id:
            raise ValueError("request_conflict")
        if job["status"] == "completed":
            return job

        # The mobile request can suggest a route but cannot publish it. A
        # dispatcher approval is the only path that advances route versions.
        result = self._evaluate_proposal(driver_id, state)
        self.store.complete_job(job_id, result["decision"], result)
        self.store.log_audit(
            event_type="plan_route_evaluated",
            principal=driver_id,
            payload={"job_id": job_id, "request_id": request_id, "result": result},
        )
        return {"job_id": job_id, "status": "completed", "outcome": result["decision"], "result": result}

    # -------------------------------------------------------------------------
    # Congestion Reports
    # -------------------------------------------------------------------------

    def report_congestion(
        self,
        driver_id: str,
        event_id: str,
        base_route_version: int,
        severity: str = "heavy",
        note: str = "",
    ) -> dict[str, Any]:
        """Driver taps 'Report Congestion'. Admits report and evaluates auto-publication."""
        state = self.store.get_driver_state(driver_id)
        if not state:
            raise ValueError(f"Unknown driver {driver_id}")
        if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128:
            raise ValueError("invalid_event_id")
        if isinstance(base_route_version, bool) or not isinstance(base_route_version, int) or base_route_version < 1:
            raise ValueError("invalid_version")
        if severity not in ("moderate", "heavy") or not isinstance(note, str) or len(note) > 240:
            raise ValueError("invalid_report")
        request_hash = hashlib.sha256(json.dumps({"driver_id": driver_id, "base_route_version": base_route_version,
            "severity": severity, "note": note}, sort_keys=True).encode()).hexdigest()
        prior = self.store.get_event(event_id)
        if prior:
            if prior["driver_id"] != driver_id or prior["request_hash"] != request_hash:
                raise ValueError("event_conflict")
            replay = json.loads(prior["proposal_json"])
            proposal = self.store.get_proposal(replay.get("proposal_id", ""))
            if proposal and proposal.get("status") == "published":
                manifest = self.store.publish_proposal(
                    proposal["proposal_id"], driver_id,
                    proposal.get("proposal", {}).get("validation", {}),
                )
                replay.update({"status": "proposal_published", "published": True,
                               "published_manifest": manifest,
                               "validation": proposal.get("proposal", {}).get("validation")})
            return replay
        if base_route_version != state["route_version"]:
            raise ValueError("stale_version")

        # Map severity to synthetic delay: moderate = +3 min (180s), heavy = +8 min (480s)
        delay_seconds = 480.0 if severity.lower() == "heavy" else 180.0
        # TTL: 5 minutes (300 seconds)
        now_dt = datetime.now(timezone.utc)
        expires_at = (now_dt + timedelta(seconds=300)).isoformat()

        # Identify driver's active road segment
        current_route = self.catalog.get_candidate(state["route_id"])
        target_segment = current_route.segments[0].segment_id if current_route and current_route.segments else "seg_unknown"

        # Persist report and evaluate a proposal; driver input never publishes a route.
        self.store.save_congestion_report(
            event_id=event_id,
            driver_id=driver_id,
            vehicle_id=state["vehicle_id"],
            segment_id=target_segment,
            severity=severity,
            delay_seconds=delay_seconds,
            expires_at=expires_at,
            note=note,
        )

        job_id = f"job_cong_{uuid.uuid4().hex[:12]}"
        job = self.store.create_or_get_job(job_id, driver_id, event_id)

        # Run decision evaluation under updated congestion
        decision_result = self._evaluate_proposal(driver_id, state)
        proposal_id = f"proposal_{uuid.uuid4().hex}"
        proposed_route_id = decision_result.get("route_id")
        result = {
            "status": "proposal_pending", "event_id": event_id, "proposal_id": proposal_id,
            "job_id": job_id, "driver_id": driver_id, "vehicle_id": state["vehicle_id"],
            "base_route_version": base_route_version, "decision": decision_result["decision"],
            "reason": decision_result.get("reason"), "proposed_route_id": proposed_route_id,
            "proposed_corridor_id": decision_result.get("corridor_id"), "published": False,
            "current_route_version": state["route_version"],
            "current_route_id": decision_result.get("current_route_id", state["route_id"]),
            "current_duration_seconds": decision_result.get("current_cost_seconds"),
            "proposed_duration_seconds": decision_result.get("proposed_cost_seconds"),
            "time_saved_seconds": decision_result.get("time_saved_seconds"),
            "proposed_route_geojson": decision_result.get("proposed_route_geojson"),
            "validation": {"status": "pending_dispatcher_validation", "valid": None},
            "active_overlays": decision_result.get("active_overlays", {}),
        }
        result = self.store.create_event_proposal(event_id, driver_id, request_hash, proposal_id,
            base_route_version, proposed_route_id, decision_result.get("corridor_id"), result)
        self.store.complete_job(job_id, result["decision"], result)

        self.store.log_audit(
            event_type="congestion_reported_and_evaluated",
            principal=driver_id,
            payload={
                "event_id": event_id,
                "job_id": job_id,
                "severity": severity,
                "delay_seconds": delay_seconds,
                "decision": decision_result,
                "proposal_id": proposal_id,
            },
        )

        return result

    # -------------------------------------------------------------------------
    # Proposal evaluation and driver acknowledgement
    # -------------------------------------------------------------------------
    def _evaluate_proposal(self, driver_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
        """Score alternatives without mutating the active driver assignment."""
        candidate_state = dict(state)
        vehicle_id = candidate_state["vehicle_id"]
        current = self.catalog.get_candidate(candidate_state["route_id"])
        if not current:
            return {"decision": "ALERT", "reason": "No active route found"}
        overlays = self.store.get_active_overlays()
        current_cost = self.catalog.score_route(current, overlays)
        scored = sorted(((self.catalog.score_route(c, overlays), c)
                         for c in self.catalog.get_alternatives(vehicle_id)),
                        key=lambda item: (item[0], item[1].route_id))
        if not scored:
            return {"decision": "KEEP", "reason": "No alternate route configured"}
        best_cost, best = scored[0]
        saved = current_cost - best_cost
        improvement = saved / max(current_cost, 1.0)
        if best.route_id != current.route_id and saved >= 120 and improvement >= .10:
            return {"decision": "PROPOSE_ROUTE", "route_id": best.route_id,
                    "corridor_id": best.corridor_id, "time_saved_seconds": saved,
                    "current_route_id": current.route_id, "current_cost_seconds": current_cost,
                    "proposed_cost_seconds": best_cost, "proposed_route_geojson": best.to_geojson(),
                    "active_overlays": dict(overlays)}
        return {"decision": "KEEP", "reason": "Current route retained", "route_id": None,
                "corridor_id": None, "current_route_id": current.route_id,
                "current_cost_seconds": current_cost, "proposed_cost_seconds": None,
                "proposed_route_geojson": None, "active_overlays": dict(overlays)}

    def validate_proposal(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Recompute available route/time invariants before dispatcher publication.

        The catalog has no capacity, contractual-window, or monetary source fields;
        those checks are explicitly reported unavailable rather than inferred.
        """
        state = self.store.get_driver_state(proposal.get("driver_id", ""))
        route = self.catalog.get_candidate(proposal.get("route_id") or "")
        current = self.catalog.get_candidate(state["route_id"]) if state else None
        body = proposal.get("proposal", {})
        checks: dict[str, bool] = {
            "base_version_current": bool(state and state["route_version"] == proposal.get("base_route_version")),
            "candidate_exists": route is not None,
            "same_vehicle": bool(route and state and route.vehicle_id == state["vehicle_id"]),
            "same_ordered_stops": bool(route and current and route.stop_ids == current.stop_ids),
            "proposal_matches_record": bool(route and proposal.get("route_id") == body.get("proposed_route_id")
                and proposal.get("corridor_id") == body.get("proposed_corridor_id")
                and proposal.get("base_route_version") == body.get("base_route_version")),
        }
        overlay = body.get("active_overlays", {})
        if route and current and isinstance(overlay, dict) and all(
            isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) and v >= 0 for k, v in overlay.items()
        ):
            flat = [point for segment in route.segments for point in segment.coordinates]
            coords_valid = all(len(point) == 2 and math.isfinite(float(point[0])) and math.isfinite(float(point[1]))
                               and -180 <= float(point[0]) <= 180 and -90 <= float(point[1]) <= 90
                               for point in flat)
            recomputed_duration = self.catalog.score_route(route, overlay)
            recomputed_current = self.catalog.score_route(current, overlay)
            recomputed_distance = sum(segment.length_metres for segment in route.segments)
            saved = recomputed_current - recomputed_duration
            improvement = saved / max(recomputed_current, 1.0)
            supplied_geo = body.get("proposed_route_geojson")
            checks["finite_bounded_geometry"] = coords_valid
            checks["duration_recomputed"] = math.isfinite(recomputed_duration) and _finite_close(
                recomputed_duration, body.get("proposed_duration_seconds"))
            checks["current_duration_recomputed"] = math.isfinite(recomputed_current) and _finite_close(
                recomputed_current, body.get("current_duration_seconds"))
            checks["improvement_recomputed"] = _finite_close(saved, body.get("time_saved_seconds"))
            checks["switch_threshold_met"] = route.route_id != current.route_id and saved >= 120 and improvement >= .10
            checks["distance_recomputed"] = math.isfinite(recomputed_distance) and recomputed_distance > 0
            checks["geojson_matches_catalog"] = bool(supplied_geo == route.to_geojson())
        else:
            checks["finite_bounded_geometry"] = False
            checks["duration_recomputed"] = False
            checks["current_duration_recomputed"] = False
            checks["improvement_recomputed"] = False
            checks["switch_threshold_met"] = False
            checks["distance_recomputed"] = False
            checks["geojson_matches_catalog"] = False
        return {"status": "validated" if all(checks.values()) else "failed", "valid": all(checks.values()),
                "scope": "catalog vehicle/ordered-stop coverage/geometry/duration/distance only; capacity, windows, financial objective, and live conditions unavailable",
                "unavailable": ["capacity", "contractual_windows", "financial_objective", "live_conditions"],
                "financial_metrics": {"status": "unavailable", "reason": "catalog has no financial inputs"},
                "checks": checks}

    def publish_proposal(self, proposal_id: str, actor: str) -> dict[str, Any] | None:
        proposal = self.store.get_proposal(proposal_id)
        if not proposal:
            return None
        if proposal.get("status") == "published":
            # Store-level replay returns the manifest committed by this proposal,
            # even if that driver has since received a newer route version.
            return self.store.publish_proposal(
                proposal_id, actor, proposal.get("proposal", {}).get("validation", {})
            )
        if not proposal.get("route_id"):
            raise ValueError("proposal_no_change")
        validation = self.validate_proposal(proposal)
        if not validation["valid"]:
            raise ValueError("validation_failed")
        return self.store.publish_proposal(proposal_id, actor, validation)
    def acknowledge(self, driver_id: str, version: int, manifest_revision: int) -> dict[str, Any]:
        state = self.store.get_driver_state(driver_id)
        if not state:
            raise ValueError("unknown_driver")
        if version != state["route_version"] or manifest_revision != state["manifest_revision"]:
            raise ValueError("stale_acknowledgement")
        acknowledged_at = self.store.record_acknowledgement(driver_id, version, manifest_revision)
        self.store.log_audit(
            event_type="driver_acknowledgement",
            principal=driver_id,
            payload={"version": version},
        )
        return {"status": "acknowledged", "driver_id": driver_id, "vehicle_id": state["vehicle_id"],
                "version": version, "manifest_revision": manifest_revision,
                "acknowledged_at": acknowledged_at}
