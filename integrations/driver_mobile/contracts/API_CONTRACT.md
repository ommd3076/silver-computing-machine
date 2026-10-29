# DebugLeaf Driver Mobile API Contract

Version: `1.0.0`  
Protocol: HTTP/1.1 REST + JSON  
Target Launch: `integrations.driver_mobile.server.app:app`

---

## 1. Security & Authentication Model

1. **Driver Authentication**:
   - Mobile driver endpoints require an opaque session bearer token:
     `Authorization: Bearer demo_sess_<40_hex_chars>`
   - Acquired via one-time pairing code redemption at `POST /api/v1/demo/sessions`.
   - Identity (`driver_id`, `vehicle_id`, `driver_name`) is resolved strictly server-side from the bearer token.
   - Mobile clients never send or override their driver or vehicle identity.

2. **Dispatcher Authentication**:
   - Dispatcher overview requires either `DEBUGLEAF_DISPATCHER_TOKEN` or `DEBUGLEAF_ADMIN_TOKEN`:
     `Authorization: Bearer <token>`
   - Driver tokens attempting to access `/dispatcher/*` are rejected with `HTTP 403 Forbidden`.
   - Dispatcher tokens attempting to access driver endpoints are rejected with `HTTP 401 Unauthorized`.

3. **Standard Error Envelope**:
   ```json
   {
     "error": {
       "code": "error_code_string",
       "message": "Human-readable description",
       "details": [
         { "field": "field_name", "message": "Field-specific error" }
       ]
     }
   }
   ```

---

## 2. Endpoints Specification

### 2.1 Driver Pairing & Session Lifecycle

#### `POST /api/v1/demo/sessions`
- **Purpose**: Redeem one-time pairing code for an opaque session token.
- **Auth**: None (Rate limited: max 5 attempts per minute per IP).
- **Request Body**:
  ```json
  { "code": "PAIR01" }
  ```
- **Response `200 OK`**:
  ```json
  {
    "token": "demo_sess_a8f9c104e768b24d7731f90e5561a0b3884c7d01",
    "expires_at": "2026-10-30T05:21:54.000000Z",
    "driver_id": "driver_1",
    "vehicle_id": "vehicle_1",
    "driver_name": "Ramesh Kumar"
  }
  ```
- **Errors**:
  - `401 Unauthorized`: `invalid_code` (code invalid or already used).
  - `422 Unprocessable Entity`: `invalid_request` (payload malformed or code too long).
  - `429 Too Many Requests`: `rate_limit_exceeded`.

#### `DELETE /api/v1/demo/sessions/current`
- **Purpose**: Terminate current driver session.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Response `200 OK`**:
  ```json
  { "status": "revoked" }
  ```

#### `GET /api/v1/demo/me`
- **Purpose**: Get driver identity resolved from token.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Response `200 OK`**:
  ```json
  {
    "driver_id": "driver_1",
    "vehicle_id": "vehicle_1",
    "driver_name": "Ramesh Kumar",
    "role": "driver",
    "simulation_mode": true
  }
  ```

---

### 2.2 Driver Operations

#### `GET /api/v1/demo/state`
- **Purpose**: Fetch authoritative current route state, GeoJSON polyline, stops, and version.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Response `200 OK`**:
  ```json
  {
    "schema_version": "1.0.0",
    "driver_id": "driver_1",
    "vehicle_id": "vehicle_1",
    "route_id": "route_v1_primary",
    "corridor_id": "corridor_a_expressway",
    "route_version": 1,
    "manifest_revision": 1,
    "status": "en_route",
    "estimated_duration_seconds": 1200.0,
    "estimated_distance_metres": 12700.0,
    "active_overlays": {},
    "simulation_mode": true,
    "data_provenance": "synthetic_delhivery_v1",
    "geojson": {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [77.1025, 28.5245],
          [77.0880, 28.5120],
          [77.0650, 28.4980],
          [77.0420, 28.4860],
          [77.0310, 28.4790],
          [77.0250, 28.4850],
          [77.0380, 28.5020],
          [77.1025, 28.5245]
        ]
      },
      "properties": {
        "route_id": "route_v1_primary",
        "corridor_id": "corridor_a_expressway",
        "name": "Expressway Route (Fastest Base)",
        "vehicle_id": "vehicle_1",
        "stop_ids": ["depot", "stop_1", "stop_2", "depot"],
        "duration_seconds": 1200.0,
        "distance_metres": 12700.0
      }
    },
    "stops": [
      { "id": "depot", "name": "Okhla Hub Depot", "coordinates": [77.1025, 28.5245], "status": "completed" },
      { "id": "stop_1", "name": "Cyber Hub, Gurgaon", "coordinates": [77.0310, 28.4790], "status": "next" },
      { "id": "stop_2", "name": "Udyog Vihar Phase IV", "coordinates": [77.0250, 28.4850], "status": "pending" },
      { "id": "depot", "name": "Okhla Hub Depot", "coordinates": [77.1025, 28.5245], "status": "pending" }
    ],
    "last_ack_version": 1,
    "updated_at": "2026-10-30T01:21:54.000000Z"
  }
  ```

#### `POST /api/v1/demo/reports`
- **Purpose**: Driver submits a congestion report. Triggers real server-side re-evaluation and auto-publication if policy conditions hold.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Request Body**:
  ```json
  {
    "event_id": "client-uuid-9821-43ef",
    "base_route_version": 1,
    "kind": "congestion",
    "severity": "heavy",
    "segment_id": "seg_nh48_exp",
    "note": "Traffic gridlock at Mahipalpur flyover"
  }
  ```
- **Response `202 Accepted`**:
  ```json
  {
    "status": "accepted",
    "event_id": "client-uuid-9821-43ef",
    "job_id": "job_cong_8f4b23a19e830c2d",
    "delay_applied_seconds": 480.0,
    "segment_id": "seg_nh48_exp",
    "decision": "PUBLISHED_NEW_ROUTE",
    "published_new_route": true,
    "current_route_version": 2
  }
  ```
- **Errors**:
  - `403 Forbidden`: `forbidden_resource` (foreign driver_id in request body).
  - `404 Not Found`: `candidate_not_found` or `driver_not_found`.
  - `409 Conflict`: `stale_route_version` (base_route_version != current version; no state mutation or overlay pollution occurs).
  - `409 Conflict`: `event_conflict` (event_id reused with differing payload).
  - `422 Unprocessable Entity`: `invalid_segment` (segment does not belong to driver's route).

#### `POST /api/v1/demo/route-requests`
- **Purpose**: Driver manually triggers a plan-route re-evaluation.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Request Body**:
  ```json
  {
    "request_id": "client-req-5541-11aa",
    "base_route_version": 1
  }
  ```
- **Response `202 Accepted`**:
  ```json
  {
    "job_id": "job_plan_clientreq554",
    "status": "completed",
    "outcome": "KEEP",
    "result": {
      "decision": "KEEP",
      "published": false,
      "reason": "Current route optimal",
      "route_version": 1,
      "current_cost_seconds": 1200.0
    }
  }
  ```

#### `GET /api/v1/demo/jobs/{job_id}`
- **Purpose**: Query durable planning job state. Enforces caller ownership.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Response `200 OK`**:
  ```json
  {
    "job_id": "job_cong_clientuuid98",
    "status": "completed",
    "outcome": "PUBLISHED_NEW_ROUTE",
    "result": { ... }
  }
  ```
- **Errors**:
  - `404 Not Found`: `job_not_found` (missing job or job belongs to a different driver).

#### `POST /api/v1/demo/acknowledgements`
- **Purpose**: Confirm device rendered the new route version.
- **Auth**: `Authorization: Bearer demo_sess_...`
- **Request Body**:
  ```json
  {
    "route_version": 2,
    "client_timestamp": "2026-10-30T01:22:15.120Z"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "status": "acknowledged",
    "driver_id": "driver_1",
    "version": 2
  }
  ```
- **Errors**:
  - `400 Bad Request`: `future_version_rejected` (cannot acknowledge route version ahead of published server version).

---

### 2.3 Dispatcher Fleet Overview

#### `GET /api/v1/demo/dispatcher/overview`
- **Purpose**: Real-time aggregated fleet status for the arQ dashboard and operator console.
- **Auth**: `Authorization: Bearer <DEBUGLEAF_DISPATCHER_TOKEN | DEBUGLEAF_ADMIN_TOKEN>`
- **Response `200 OK`**:
  ```json
  {
    "drivers": [
      {
        "driver_id": "driver_1",
        "driver_name": "Ramesh Kumar",
        "vehicle_id": "vehicle_1",
        "status": "en_route",
        "route_version": 2,
        "corridor": "corridor_b_bypass",
        "last_ack_version": 2,
        "active_delay_seconds": 480.0
      },
      {
        "driver_id": "driver_2",
        "driver_name": "Suresh Sharma",
        "vehicle_id": "vehicle_2",
        "status": "en_route",
        "route_version": 1,
        "corridor": "corridor_c_south",
        "last_ack_version": 1,
        "active_delay_seconds": 0.0
      }
    ],
    "active_incidents": [
      {
        "event_id": "client-uuid-9821-43ef",
        "driver_id": "driver_1",
        "segment_id": "seg_nh48_exp",
        "severity": "heavy",
        "delay_seconds": 480.0,
        "reported_at": "2026-10-30T01:22:00.000000Z"
      }
    ]
  }
  ```
- **Errors**:
  - `401 Unauthorized`: `authentication_required` or `authentication_failed`.
  - `403 Forbidden`: `authorization_denied` (e.g. driver token supplied).
