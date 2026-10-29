"""FastAPI Router for DebugLeaf Driver Mobile Integration."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth import (
    DemoAuthManager,
    get_current_driver,
    require_dispatcher_or_admin,
)
from .coordinator import TransactionalDemoCoordinator
from .schemas import (
    AcknowledgementRequest,
    AcknowledgementResponse,
    CongestionReportRequest,
    CongestionReportResponse,
    DispatcherOverviewResponse,
    DriverIdentityResponse,
    DriverStateResponse,
    JobResponse,
    PairingRequest,
    PairingResponse,
    RoutePlanRequest,
    RoutePlanResponse,
)
from .storage import (
    DriverNotFoundError,
    EventConflictError,
    InvalidAckError,
    RateLimitExceededError,
    RouteCandidateNotFoundError,
    StaleVersionError,
    TransactionalDemoStore,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["Driver Mobile Demo"])


def _client_ip(request: Request) -> str:
    """Safely obtain client IP address for rate limiting."""
    if request.client and request.client.host:
        return request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return "127.0.0.1"


# -----------------------------------------------------------------------------
# Driver Session & Pairing Endpoints
# -----------------------------------------------------------------------------

@router.post("/sessions", response_model=PairingResponse, status_code=200)
async def redeem_session(payload: PairingRequest, request: Request) -> PairingResponse:
    """Redeem a one-time pairing code for an opaque driver bearer session token."""
    auth_mgr: DemoAuthManager = request.app.state.demo_auth_manager
    ip = _client_ip(request)

    try:
        session = auth_mgr.redeem_code(payload.code, ip)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "rate_limit_exceeded", "message": str(exc)}},
        )

    if not session:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "invalid_code", "message": "Pairing code is invalid or already used"}},
        )

    return PairingResponse(**session)


@router.delete("/sessions/current", status_code=200)
async def revoke_current_session(
    request: Request, driver: dict[str, Any] = Depends(get_current_driver)
) -> dict[str, str]:
    """Revoke driver's current session token."""
    auth_mgr: DemoAuthManager = request.app.state.demo_auth_manager
    token = driver["token"]
    revoked = auth_mgr.revoke_token(token)
    return {"status": "revoked" if revoked else "not_found"}


@router.get("/me", response_model=DriverIdentityResponse, status_code=200)
async def get_me(driver: dict[str, Any] = Depends(get_current_driver)) -> DriverIdentityResponse:
    """Return server-verified driver identity from bearer session."""
    return DriverIdentityResponse(
        driver_id=driver["driver_id"],
        vehicle_id=driver["vehicle_id"],
        driver_name=driver["driver_name"],
        role="driver",
        simulation_mode=True,
    )


# -----------------------------------------------------------------------------
# Driver Operations Endpoints
# -----------------------------------------------------------------------------

@router.get("/state", response_model=DriverStateResponse, status_code=200)
async def get_state(
    request: Request, driver: dict[str, Any] = Depends(get_current_driver)
) -> DriverStateResponse:
    """Fetch authoritative driver route state, GeoJSON polyline, stops, and version."""
    coord: TransactionalDemoCoordinator = request.app.state.demo_coordinator
    state = coord.get_driver_state(driver["driver_id"])
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "driver_not_found", "message": "Driver state not initialized"}},
        )
    return state


@router.post("/reports", response_model=CongestionReportResponse, status_code=202)
async def report_congestion(
    payload: CongestionReportRequest,
    request: Request,
    driver: dict[str, Any] = Depends(get_current_driver),
) -> CongestionReportResponse:
    """Submit driver congestion report; re-scores routes and auto-publishes if warranted."""
    if payload.driver_id and payload.driver_id != driver["driver_id"]:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "forbidden_resource", "message": "Cannot submit report for another driver"}},
        )
    coord: TransactionalDemoCoordinator = request.app.state.demo_coordinator
    try:
        result = coord.report_congestion(
            driver_id=driver["driver_id"],
            event_id=payload.event_id,
            base_route_version=payload.base_route_version,
            severity=payload.severity,
            note=payload.note or "",
            segment_id=payload.segment_id,
        )
        return CongestionReportResponse(**result)
    except StaleVersionError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "stale_route_version", "message": str(exc)}},
        )
    except EventConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "event_conflict", "message": str(exc)}},
        )
    except DriverNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "driver_not_found", "message": str(exc)}},
        )
    except RouteCandidateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "candidate_not_found", "message": str(exc)}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_segment", "message": str(exc)}},
        )


@router.post("/route-requests", response_model=RoutePlanResponse, status_code=202)
async def request_plan_route(
    payload: RoutePlanRequest,
    request: Request,
    driver: dict[str, Any] = Depends(get_current_driver),
) -> RoutePlanResponse:
    """Manually trigger candidate evaluation from driver cockpit."""
    if payload.driver_id and payload.driver_id != driver["driver_id"]:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "forbidden_resource", "message": "Cannot plan route for another driver"}},
        )
    coord: TransactionalDemoCoordinator = request.app.state.demo_coordinator
    try:
        result = coord.request_plan_route(
            driver_id=driver["driver_id"],
            request_id=payload.request_id,
            base_route_version=payload.base_route_version,
        )
        return RoutePlanResponse(**result)
    except StaleVersionError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "stale_route_version", "message": str(exc)}},
        )
    except EventConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "event_conflict", "message": str(exc)}},
        )
    except DriverNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "driver_not_found", "message": str(exc)}},
        )
    except RouteCandidateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "candidate_not_found", "message": str(exc)}},
        )


@router.get("/jobs/{job_id}", response_model=JobResponse, status_code=200)
async def get_job_status(
    job_id: str,
    request: Request,
    driver: dict[str, Any] = Depends(get_current_driver),
) -> JobResponse:
    """Inspect durable planning job status. Enforces driver ownership."""
    store: TransactionalDemoStore = request.app.state.demo_store
    job = store.get_job(job_id, driver_id=driver["driver_id"])
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "job_not_found", "message": "Planning job not found"}},
        )
    return JobResponse(
        job_id=job["job_id"],
        status=job["status"],
        outcome=job.get("outcome"),
        result=job.get("result"),
    )


@router.post("/acknowledgements", response_model=AcknowledgementResponse, status_code=200)
async def submit_acknowledgement(
    payload: AcknowledgementRequest,
    request: Request,
    driver: dict[str, Any] = Depends(get_current_driver),
) -> AcknowledgementResponse:
    """Acknowledge rendered route version on mobile client."""
    if payload.driver_id and payload.driver_id != driver["driver_id"]:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "forbidden_resource", "message": "Cannot acknowledge route for another driver"}},
        )
    coord: TransactionalDemoCoordinator = request.app.state.demo_coordinator
    try:
        ack_ver = coord.acknowledge(
            driver_id=driver["driver_id"],
            version=payload.route_version,
            client_timestamp=payload.client_timestamp,
        )
        return AcknowledgementResponse(
            status="acknowledged",
            driver_id=driver["driver_id"],
            version=ack_ver,
        )
    except InvalidAckError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "future_version_rejected", "message": str(exc)}},
        )
    except DriverNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "driver_not_found", "message": str(exc)}},
        )


# -----------------------------------------------------------------------------
# Dispatcher Endpoints
# -----------------------------------------------------------------------------

@router.get("/dispatcher/overview", response_model=DispatcherOverviewResponse, status_code=200)
async def get_dispatcher_overview(
    request: Request,
    _actor: dict[str, str] = Depends(require_dispatcher_or_admin),
) -> DispatcherOverviewResponse:
    """Fleet status overview for arQ dashboard or integration operator console."""
    coord: TransactionalDemoCoordinator = request.app.state.demo_coordinator
    return coord.get_dispatcher_overview()
