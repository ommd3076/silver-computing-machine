"""Strict Pydantic request and response schemas for DebugLeaf driver mobile integration."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class PairingRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32, description="One-time pairing code")

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Pairing code cannot be empty")
        return cleaned


class PairingResponse(BaseModel):
    token: str = Field(..., description="Opaque driver bearer token")
    expires_at: str = Field(..., description="ISO-8601 session expiration timestamp")
    driver_id: str = Field(..., description="Assigned driver ID")
    vehicle_id: str = Field(..., description="Assigned vehicle ID")
    driver_name: str = Field(..., description="Driver full name")


class DriverIdentityResponse(BaseModel):
    driver_id: str
    vehicle_id: str
    driver_name: str
    role: str = "driver"
    simulation_mode: bool = True


class StopInfo(BaseModel):
    id: str
    name: str
    coordinates: list[float] = Field(..., description="[longitude, latitude] GeoJSON coordinate pair")
    status: str = Field(..., description="'completed' | 'next' | 'pending'")

    @field_validator("coordinates")
    @classmethod
    def validate_coords(cls, v: list[float]) -> list[float]:
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        lon, lat = v
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("Coordinates out of valid WGS84 range")
        return v


class DriverStateResponse(BaseModel):
    schema_version: str = "1.0.0"
    driver_id: str
    vehicle_id: str
    route_id: str
    corridor_id: str
    route_version: int
    manifest_revision: int
    status: str = "en_route"
    estimated_duration_seconds: float
    estimated_distance_metres: float
    active_overlays: dict[str, float] = Field(default_factory=dict)
    simulation_mode: bool = True
    data_provenance: str = "synthetic_delhivery_v1"
    geojson: Optional[dict[str, Any]] = None
    stops: list[StopInfo] = Field(default_factory=list)
    last_ack_version: int = 0
    updated_at: str


class CongestionReportRequest(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128, description="Client idempotency key")
    base_route_version: int = Field(..., ge=1, description="Driver's current route version")
    kind: str = Field(default="congestion", description="Incident kind")
    severity: str = Field(..., pattern="^(moderate|heavy)$", description="'moderate' or 'heavy'")
    segment_id: Optional[str] = Field(default=None, max_length=64, description="Optional segment ID on the active route")
    note: Optional[str] = Field(default="", max_length=500, description="Optional incident note")
    driver_id: Optional[str] = Field(default=None, max_length=64, description="Optional driver ID; if provided, must match session driver")


class CongestionReportResponse(BaseModel):
    status: str = "accepted"
    event_id: str
    job_id: str
    delay_applied_seconds: float
    segment_id: str
    decision: str
    published_new_route: bool
    current_route_version: int


class RoutePlanRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=128, description="Client idempotency key")
    base_route_version: int = Field(..., ge=1, description="Driver's current route version")
    driver_id: Optional[str] = Field(default=None, max_length=64, description="Optional driver ID; if provided, must match session driver")


class RoutePlanResponse(BaseModel):
    job_id: str
    status: str = "completed"
    outcome: str
    result: dict[str, Any]


class JobResponse(BaseModel):
    job_id: str
    status: str
    outcome: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class AcknowledgementRequest(BaseModel):
    route_version: int = Field(..., ge=1, description="Route version rendered and acknowledged")
    client_timestamp: Optional[str] = Field(default=None, description="Client ISO timestamp")
    driver_id: Optional[str] = Field(default=None, max_length=64, description="Optional driver ID; if provided, must match session driver")


class AcknowledgementResponse(BaseModel):
    status: str = "acknowledged"
    driver_id: str
    version: int


class DispatcherDriverSummary(BaseModel):
    driver_id: str
    driver_name: str
    vehicle_id: str
    status: str
    route_version: int
    corridor: str
    last_ack_version: int
    active_delay_seconds: float


class DispatcherIncidentSummary(BaseModel):
    event_id: str
    driver_id: str
    segment_id: str
    severity: str
    delay_seconds: float
    reported_at: str


class DispatcherOverviewResponse(BaseModel):
    drivers: list[DispatcherDriverSummary]
    active_incidents: list[DispatcherIncidentSummary]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[list[ErrorDetail]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
