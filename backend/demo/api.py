"""Authenticated driver and dispatcher routes for the local mobile demo."""
from __future__ import annotations

import hmac
import ipaddress
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException, Request

from .auth import DemoAuthManager
from .routes import RouteCatalog
from .service import DemoCoordinatorService
from .store import DemoStore


def create_demo_router(store: DemoStore | None = None, service: DemoCoordinatorService | None = None,
                       auth_manager: DemoAuthManager | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
    db = store or DemoStore()
    svc = service or DemoCoordinatorService(db)
    auth = auth_manager or DemoAuthManager(db)
    catalog = svc.catalog if hasattr(svc, "catalog") else RouteCatalog()
    db.seed_pairing_codes([
        {"code": "PAIR01", "driver_id": "driver_1", "vehicle_id": "vehicle_1", "driver_name": "Ramesh Kumar"},
        {"code": "PAIR02", "driver_id": "driver_2", "vehicle_id": "vehicle_2", "driver_name": "Suresh Patel"},
    ])

    def fail(status: int, code: str, message: str):
        raise HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})

    def driver(authorization: str | None) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            fail(401, "authentication_required", "driver bearer session required")
        session = auth.verify_token(authorization[7:].strip())
        if not session:
            fail(401, "invalid_session", "driver session is expired or invalid")
        return session

    def dispatcher(request: Request) -> str:
        config = getattr(request.app.state, "auth_config", None)
        if config is None or not config.ready:
            fail(503, "auth_misconfigured", "dispatcher authorization is unavailable")
        if config.mode == "local":
            host = request.client.host if request.client else ""
            try:
                if not ipaddress.ip_address(host).is_loopback:
                    fail(403, "dispatcher_required", "dispatcher action requires loopback local access")
            except ValueError:
                fail(403, "dispatcher_required", "dispatcher action requires loopback local access")
            return "local_dispatcher"
        header = request.headers.get("authorization", "")
        raw = header[7:].encode() if header.startswith("Bearer ") else b""
        for role in ("dispatcher", "admin"):
            if hmac.compare_digest(raw, config.tokens[role].encode()):
                return role
        fail(403, "dispatcher_required", "dispatcher or admin role required")

    def add_stops(payload: dict[str, Any]) -> dict[str, Any]:
        route = catalog.get_candidate(payload.get("route_id", ""))
        coordinates = {"stop_1": [77.0310, 28.4790], "stop_2": [77.0250, 28.4850],
                       "stop_3": [77.1550, 28.5280], "stop_4": [77.1920, 28.5490]}
        result = dict(payload)
        if route and "geojson" not in result:
            result["geojson"] = route.to_geojson()
        result["stops"] = ([{"id": stop, "sequence": i + 1, "name": stop,
                             "status": "assigned", "address": None, "eta_window": None,
                             "coordinates": coordinates.get(stop), "detail_available": False}
                            for i, stop in enumerate(stop for stop in route.stop_ids if stop != "depot")] if route else [])
        return result

    @router.post("/sessions")
    def create_session(payload: dict[str, Any] = Body(...)):
        if set(payload) != {"code"}:
            fail(422, "invalid_code", "only a pairing code is accepted")
        code = payload.get("code")
        if not isinstance(code, str) or not code.strip():
            fail(422, "invalid_code", "pairing code is required")
        session = auth.redeem_code(code.strip())
        if not session:
            fail(403, "pairing_failed", "pairing code is invalid or already used")
        return session

    @router.delete("/sessions/current")
    def revoke_session(authorization: str | None = Header(None)):
        current = driver(authorization)
        token = authorization[7:].strip()
        if not auth.revoke_token(token):
            fail(404, "not_found", "session is not active")
        return {"status": "revoked", "driver_id": current["driver_id"]}

    @router.get("/me")
    def me(authorization: str | None = Header(None)):
        current = driver(authorization)
        return {**current, "role": "driver"}

    @router.get("/state")
    def state(authorization: str | None = Header(None)):
        current = driver(authorization)
        result = svc.get_driver_state(current["driver_id"])
        if not result:
            fail(404, "driver_not_found", "driver state is unavailable")
        return add_stops(result)

    @router.get("/manifest")
    def manifest(authorization: str | None = Header(None)):
        current = driver(authorization)
        result = db.get_manifest_for_driver(current["driver_id"])
        if not result or result.get("vehicle_id") != current["vehicle_id"]:
            fail(404, "manifest_not_found", "driver manifest is unavailable")
        return add_stops(result)

    @router.post("/reports", status_code=202)
    def report(payload: dict[str, Any] = Body(...), authorization: str | None = Header(None)):
        current = driver(authorization)
        if set(payload) - {"event_id", "base_route_version", "severity", "note"}:
            fail(422, "invalid_report", "report contains unsupported fields")
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128:
            fail(422, "invalid_report", "event_id is required")
        base_version = payload.get("base_route_version")
        if isinstance(base_version, bool) or not isinstance(base_version, int) or base_version < 1:
            fail(422, "invalid_version", "base_route_version must be a positive integer")
        severity = payload.get("severity", "heavy")
        note = payload.get("note", "")
        if severity not in ("moderate", "heavy") or not isinstance(note, str) or len(note) > 240:
            fail(422, "invalid_report", "severity or note is invalid")
        try:
            result = svc.report_congestion(current["driver_id"], event_id,
                base_version, severity, note)
            return result
        except ValueError as exc:
            code = str(exc)
            if code not in ("stale_version", "event_conflict", "invalid_version", "invalid_report"):
                code = "invalid_report"
            status = 409 if code in ("stale_version", "event_conflict") else 422
            messages = {"stale_version": "route version changed; refresh state",
                        "event_conflict": "event_id was already used with different report data",
                        "invalid_version": "base_route_version must be a positive integer",
                        "invalid_report": "severity or note is invalid"}
            fail(status, code, messages.get(code, "report could not be accepted"))

    @router.post("/acknowledgements")
    def acknowledge(payload: dict[str, Any] = Body(...), authorization: str | None = Header(None)):
        current = driver(authorization)
        if set(payload) != {"version", "manifest_revision"}:
            fail(422, "invalid_acknowledgement", "version and manifest_revision are required")
        if any(isinstance(payload[key], bool) or not isinstance(payload[key], int) or payload[key] < 1
               for key in ("version", "manifest_revision")):
            fail(422, "invalid_acknowledgement", "versions must be positive integers")
        try:
            return svc.acknowledge(current["driver_id"], payload["version"], payload["manifest_revision"])
        except ValueError as exc:
            code = str(exc)
            if code not in ("unknown_driver", "stale_acknowledgement"):
                code = "acknowledgement_conflict"
            fail(409, code, "acknowledgement does not match the current manifest")

    @router.get("/dispatcher/state")
    def dispatcher_state(request: Request):
        actor = dispatcher(request)
        states = []
        for driver_id in ("driver_1", "driver_2"):
            row = svc.get_driver_state(driver_id)
            if row:
                states.append(add_stops(row))
        return {"actor": actor, "states": states, "proposals": db.list_proposals(limit=50)}

    @router.get("/audits")
    def audits(request: Request):
        dispatcher(request)
        return db.get_recent_audits(limit=50)

    @router.get("/proposals/{proposal_id}")
    def get_proposal(proposal_id: str, request: Request):
        dispatcher(request)
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            fail(404, "proposal_not_found", "proposal was not found")
        return proposal

    @router.post("/proposals/{proposal_id}/approve")
    def approve(proposal_id: str, request: Request):
        actor = dispatcher(request)
        try:
            result = svc.publish_proposal(proposal_id, actor)
        except ValueError as exc:
            code = str(exc)
            if code not in ("proposal_no_change", "validation_failed", "stale_proposal", "proposal_not_pending"):
                code = "proposal_conflict"
            fail(409, code, "proposal failed validation or is stale")
        if not result:
            fail(404, "proposal_not_found", "proposal was not found")
        return add_stops(result)

    return router
