"""Transactional Coordinator for DebugLeaf driver mobile integration.

Enforces base route versioning, idempotency, same-vehicle constraints,
stop preservation, deterministic route switching, and atomic publication.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from backend.demo.routes import RouteCatalog, RouteCandidate
from .schemas import (
    DriverStateResponse,
    StopInfo,
    DispatcherDriverSummary,
    DispatcherIncidentSummary,
    DispatcherOverviewResponse,
)
from .storage import (
    TransactionalDemoStore,
    StaleVersionError,
    EventConflictError,
    InvalidAckError,
    DriverNotFoundError,
    RouteCandidateNotFoundError,
)

# Canonical stop locations and metadata for the demo corridors
DELHI_STOPS_METADATA: dict[str, dict[str, Any]] = {
    "depot": {"name": "Okhla Hub Depot", "coordinates": [77.1025, 28.5245]},
    "stop_1": {"name": "Cyber Hub, Gurgaon", "coordinates": [77.0310, 28.4790]},
    "stop_2": {"name": "Udyog Vihar Phase IV", "coordinates": [77.0250, 28.4850]},
    "stop_3": {"name": "Saket District Centre", "coordinates": [77.1550, 28.5280]},
    "stop_4": {"name": "Nehru Place Market", "coordinates": [77.1920, 28.5490]},
}

DRIVER_NAMES = {
    "driver_1": "Ramesh Kumar",
    "driver_2": "Suresh Sharma",
}


def build_stops_for_candidate(candidate: RouteCandidate) -> list[StopInfo]:
    """Generate ordered stop objects with coordinates and delivery progression."""
    stops: list[StopInfo] = []
    total_stops = len(candidate.stop_ids)
    for idx, sid in enumerate(candidate.stop_ids):
        meta = DELHI_STOPS_METADATA.get(sid, {"name": f"Stop {sid}", "coordinates": [77.1000, 28.5000]})
        if idx == 0:
            status = "completed"
        elif idx == 1:
            status = "next"
        else:
            status = "pending"
        stops.append(StopInfo(
            id=sid,
            name=meta["name"],
            coordinates=list(meta["coordinates"]),
            status=status,
        ))
    return stops


class TransactionalDemoCoordinator:
    """Safe coordinator for driver state and route mutations."""

    def __init__(self, store: TransactionalDemoStore, catalog: Optional[RouteCatalog] = None) -> None:
        self.store = store
        self.catalog = catalog or RouteCatalog()
        self._ensure_default_state()

    def _ensure_default_state(self) -> None:
        """Seed default driver assignments if missing."""
        d1 = self.catalog.get_default_route("vehicle_1")
        if d1:
            self.store.init_driver_state_if_missing("driver_1", "vehicle_1", d1.route_id, d1.corridor_id)
        d2 = self.catalog.get_default_route("vehicle_2")
        if d2:
            self.store.init_driver_state_if_missing("driver_2", "vehicle_2", d2.route_id, d2.corridor_id)

    # -------------------------------------------------------------------------
    # State Retrieval
    # -------------------------------------------------------------------------

    def get_driver_state(self, driver_id: str) -> Optional[DriverStateResponse]:
        state = self.store.get_driver_state(driver_id)
        if not state:
            return None

        route_id = state["route_id"]
        candidate = self.catalog.get_candidate(route_id)
        overlays = self.store.get_active_overlays()
        current_duration = self.catalog.score_route(candidate, overlays) if candidate else 0.0
        stops = build_stops_for_candidate(candidate) if candidate else []

        return DriverStateResponse(
            schema_version="1.0.0",
            driver_id=driver_id,
            vehicle_id=state["vehicle_id"],
            route_id=route_id,
            corridor_id=state["corridor_id"],
            route_version=state["route_version"],
            manifest_revision=state["manifest_revision"],
            status=state["status"],
            estimated_duration_seconds=current_duration,
            estimated_distance_metres=candidate.total_distance_metres if candidate else 0.0,
            active_overlays=overlays,
            simulation_mode=True,
            data_provenance="synthetic_delhivery_v1",
            geojson=candidate.to_geojson() if candidate else None,
            stops=stops,
            last_ack_version=state.get("last_ack_version", 0) or 0,
            updated_at=state["updated_at"],
        )

    # -------------------------------------------------------------------------
    # Congestion Reporting & Route Re-evaluation
    # -------------------------------------------------------------------------

    def report_congestion(
        self,
        driver_id: str,
        event_id: str,
        base_route_version: int,
        severity: str = "heavy",
        note: str = "",
        segment_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Report congestion incident, score alternatives, and atomically publish if warranted."""
        state = self.store.get_driver_state(driver_id)
        if not state:
            raise DriverNotFoundError(f"Driver '{driver_id}' not found")

        current_candidate = self.catalog.get_candidate(state["route_id"])
        if not current_candidate:
            raise RouteCandidateNotFoundError(f"Route candidate '{state['route_id']}' not found in catalog")

        # 1. Map severity to synthetic delay: moderate = +180s (3 min), heavy = +480s (8 min)
        delay_seconds = 480.0 if severity.lower() == "heavy" else 180.0
        now_dt = datetime.now(timezone.utc)
        expires_at = (now_dt + timedelta(seconds=300)).isoformat()

        # 2. Identify driver's active route segment
        valid_segment_ids = [s.segment_id for s in current_candidate.segments]
        if segment_id:
            if segment_id not in valid_segment_ids:
                raise ValueError(f"Segment '{segment_id}' does not belong to active route")
            target_segment = segment_id
        else:
            target_segment = (
                current_candidate.segments[0].segment_id
                if current_candidate.segments
                else "seg_unknown"
            )

        clean_key = hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:16]
        job_id = f"job_cong_{clean_key}"

        # 3. Check for existing event_id (idempotency vs conflict) & enforce base_route_version atomically
        is_new, report = self.store.admit_congestion_report(
            event_id=event_id,
            driver_id=driver_id,
            vehicle_id=state["vehicle_id"],
            base_route_version=base_route_version,
            segment_id=target_segment,
            severity=severity,
            delay_seconds=delay_seconds,
            expires_at=expires_at,
            note=note,
        )

        if not is_new:
            # Replayed identical event: return existing job result
            existing_job = self.store.get_job(job_id, driver_id)
            if existing_job and existing_job.get("result"):
                res = existing_job["result"]
                return {
                    "status": "accepted",
                    "event_id": event_id,
                    "job_id": job_id,
                    "delay_applied_seconds": delay_seconds,
                    "segment_id": target_segment,
                    "decision": res.get("decision", "KEEP"),
                    "published_new_route": res.get("published", False),
                    "current_route_version": res.get("route_version", state["route_version"]),
                }

        current_version = state["route_version"]

        # 4. Create planning job
        self.store.create_or_get_planning_job(job_id, driver_id, event_id, base_route_version)

        # 7. Evaluate route candidates under active congestion
        overlays = self.store.get_active_overlays()
        current_cost = self.catalog.score_route(current_candidate, overlays) if current_candidate else 0.0

        alternatives = self.catalog.get_alternatives(state["vehicle_id"])
        # Validate that candidates belong to same vehicle and cover all stops
        valid_alts = [
            alt for alt in alternatives
            if alt.vehicle_id == state["vehicle_id"] and alt.stop_ids == current_candidate.stop_ids
        ]

        scored: list[tuple[float, RouteCandidate]] = []
        for alt in valid_alts:
            cost = self.catalog.score_route(alt, overlays)
            scored.append((cost, alt))

        scored.sort(key=lambda item: (item[0], item[1].route_id))
        best_cost, best_candidate = scored[0]

        # 8. Switching policy: savings >= 120s AND >= 10% relative improvement
        time_saved = current_cost - best_cost
        relative_improvement = time_saved / max(current_cost, 1.0)

        should_switch = (
            best_candidate.route_id != current_candidate.route_id
            and time_saved >= 120.0
            and relative_improvement >= 0.10
        )

        if should_switch:
            # CAS publication of new route
            decision_payload = {
                "decision": "PUBLISHED_NEW_ROUTE",
                "published": True,
                "previous_route": current_candidate.name,
                "previous_cost_seconds": current_cost,
                "new_route": best_candidate.name,
                "new_cost_seconds": best_cost,
                "time_saved_seconds": time_saved,
                "relative_improvement": relative_improvement,
            }
            new_state = self.store.atomic_publish_route(
                driver_id=driver_id,
                base_route_version=base_route_version,
                new_route_id=best_candidate.route_id,
                new_corridor_id=best_candidate.corridor_id,
                audit_event_type="congestion_route_published",
                audit_payload={
                    "event_id": event_id,
                    "job_id": job_id,
                    "severity": severity,
                    "delay_seconds": delay_seconds,
                    "decision": decision_payload,
                },
                job_id=job_id,
                job_outcome="PUBLISHED_NEW_ROUTE",
                job_result=decision_payload | {"route_version": state["route_version"] + 1},
            )
            return {
                "status": "accepted",
                "event_id": event_id,
                "job_id": job_id,
                "delay_applied_seconds": delay_seconds,
                "segment_id": target_segment,
                "decision": "PUBLISHED_NEW_ROUTE",
                "published_new_route": True,
                "current_route_version": new_state["route_version"],
            }
        else:
            decision_payload = {
                "decision": "KEEP",
                "published": False,
                "reason": f"Current route retained (current={current_cost:.0f}s vs alternate={best_cost:.0f}s)",
                "route_version": current_version,
                "current_cost_seconds": current_cost,
            }
            self.store.atomic_record_decision(
                driver_id=driver_id,
                audit_event_type="congestion_evaluated_keep",
                audit_payload={
                    "event_id": event_id,
                    "job_id": job_id,
                    "severity": severity,
                    "delay_seconds": delay_seconds,
                    "decision": decision_payload,
                },
                job_id=job_id,
                job_outcome="KEEP",
                job_result=decision_payload,
            )
            return {
                "status": "accepted",
                "event_id": event_id,
                "job_id": job_id,
                "delay_applied_seconds": delay_seconds,
                "segment_id": target_segment,
                "decision": "KEEP",
                "published_new_route": False,
                "current_route_version": current_version,
            }

    # -------------------------------------------------------------------------
    # Route Planning Requests
    # -------------------------------------------------------------------------

    def request_plan_route(
        self, driver_id: str, request_id: str, base_route_version: int
    ) -> dict[str, Any]:
        """Manual plan route request from driver cockpit."""
        state = self.store.get_driver_state(driver_id)
        if not state:
            raise DriverNotFoundError(f"Driver '{driver_id}' not found")

        current_candidate = self.catalog.get_candidate(state["route_id"])
        if not current_candidate:
            raise RouteCandidateNotFoundError(f"Route candidate '{state['route_id']}' not found in catalog")

        clean_key = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:16]
        job_id = f"job_plan_{clean_key}"

        # Atomically check existing or create running job, enforcing base_route_version before insertion
        is_new, job = self.store.create_or_get_planning_job(
            job_id, driver_id, request_id, base_route_version
        )
        if not is_new and job["status"] == "completed":
            return {
                "job_id": job["job_id"],
                "status": "completed",
                "outcome": job["outcome"],
                "result": job["result"] or {},
            }

        current_version = state["route_version"]
        overlays = self.store.get_active_overlays()
        current_cost = self.catalog.score_route(current_candidate, overlays)

        alternatives = self.catalog.get_alternatives(state["vehicle_id"])
        valid_alts = [
            alt for alt in alternatives
            if alt.vehicle_id == state["vehicle_id"] and alt.stop_ids == current_candidate.stop_ids
        ]

        scored: list[tuple[float, RouteCandidate]] = []
        for alt in valid_alts:
            cost = self.catalog.score_route(alt, overlays)
            scored.append((cost, alt))
        scored.sort(key=lambda item: (item[0], item[1].route_id))
        best_cost, best_candidate = scored[0]

        time_saved = current_cost - best_cost
        relative_improvement = time_saved / max(current_cost, 1.0)

        should_switch = (
            best_candidate.route_id != current_candidate.route_id
            and time_saved >= 120.0
            and relative_improvement >= 0.10
        )

        if should_switch:
            decision_payload = {
                "decision": "PUBLISHED_NEW_ROUTE",
                "published": True,
                "previous_route": current_candidate.name,
                "previous_cost_seconds": current_cost,
                "new_route": best_candidate.name,
                "new_cost_seconds": best_cost,
                "time_saved_seconds": time_saved,
                "route_version": current_version + 1,
            }
            new_state = self.store.atomic_publish_route(
                driver_id=driver_id,
                base_route_version=base_route_version,
                new_route_id=best_candidate.route_id,
                new_corridor_id=best_candidate.corridor_id,
                audit_event_type="plan_route_published",
                audit_payload={"request_id": request_id, "job_id": job_id, "decision": decision_payload},
                job_id=job_id,
                job_outcome="PUBLISHED_NEW_ROUTE",
                job_result=decision_payload,
            )
            return {
                "job_id": job_id,
                "status": "completed",
                "outcome": "PUBLISHED_NEW_ROUTE",
                "result": decision_payload,
            }
        else:
            decision_payload = {
                "decision": "KEEP",
                "published": False,
                "reason": "Current route optimal",
                "route_version": current_version,
                "current_cost_seconds": current_cost,
            }
            self.store.atomic_record_decision(
                driver_id=driver_id,
                audit_event_type="plan_route_evaluated_keep",
                audit_payload={"request_id": request_id, "job_id": job_id, "decision": decision_payload},
                job_id=job_id,
                job_outcome="KEEP",
                job_result=decision_payload,
            )
            return {
                "job_id": job_id,
                "status": "completed",
                "outcome": "KEEP",
                "result": decision_payload,
            }

    # -------------------------------------------------------------------------
    # Acknowledgements
    # -------------------------------------------------------------------------

    def acknowledge(self, driver_id: str, version: int, client_timestamp: Optional[str] = None) -> int:
        return self.store.record_acknowledgement(driver_id, version, client_timestamp)

    # -------------------------------------------------------------------------
    # Dispatcher Overview
    # -------------------------------------------------------------------------

    def get_dispatcher_overview(self) -> DispatcherOverviewResponse:
        driver_states = self.store.get_all_driver_states()
        overlays = self.store.get_active_overlays()

        incidents_raw = self.store.get_active_incidents()
        incidents: list[DispatcherIncidentSummary] = [
            DispatcherIncidentSummary(
                event_id=inc["event_id"],
                driver_id=inc["driver_id"],
                segment_id=inc["segment_id"],
                severity=inc["severity"],
                delay_seconds=inc["delay_seconds"],
                reported_at=inc["created_at"],
            )
            for inc in incidents_raw
        ]

        drivers: list[DispatcherDriverSummary] = []
        for ds in driver_states:
            did = ds["driver_id"]
            dname = DRIVER_NAMES.get(did, f"Driver {did}")
            cand = self.catalog.get_candidate(ds["route_id"])
            delay = 0.0
            if cand:
                for seg in cand.segments:
                    delay += overlays.get(seg.segment_id, 0.0)
            driver_incidents = [inc for inc in incidents_raw if inc["driver_id"] == did]
            inc_delay = max([float(inc["delay_seconds"]) for inc in driver_incidents], default=0.0)
            active_delay = max(delay, inc_delay)

            drivers.append(DispatcherDriverSummary(
                driver_id=did,
                driver_name=dname,
                vehicle_id=ds["vehicle_id"],
                status=ds["status"],
                route_version=ds["route_version"],
                corridor=ds["corridor_id"],
                last_ack_version=ds.get("last_ack_version", 0) or 0,
                active_delay_seconds=active_delay,
            ))

        return DispatcherOverviewResponse(
            drivers=drivers,
            active_incidents=incidents,
        )
