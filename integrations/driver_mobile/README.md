# DebugLeaf Driver Mobile & Dispatcher Integration

**System Identity:** DebugLeaf (`debugleaf`) / arQ (`arQ`)  
**Track:** Quant-A-Maze 3.0 — QML Track (`QML-01`: Delay-Risk-Aware Fleet Dispatch for Contract Logistics)  
**Location:** Completely isolated under `integrations/driver_mobile/`

---

## 1. Overview & Architecture

This package provides a secure, server-authoritative driver mobile integration for DebugLeaf. It connects two physical driver devices running Expo Go, an integration-owned dispatcher console, and the local FastAPI backend on the Lenovo Legion host without modifying any core backend files.

```text
 Physical Edge Devices (Expo Go)              Dispatcher Tier
 [Phone A: Driver 1] [Phone B: Driver 2]      [Operator Console / arQ]
      | Bearer demo_sess_...                      | Bearer DEBUGLEAF_DISPATCHER_TOKEN
      v                                           v
 ==============================================================================
             Host Network Ingress (Lenovo Legion IPv4 :8000)
 ==============================================================================
                                     |
               +---------------------+---------------------+
               |   Top-Level ASGI Gateway (app.py)        |
               +---------------------+---------------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
 [Path: /api/v1/demo/*]                                  [Path: /api/v1/* (catch-all)]
         v                                                       v
+-----------------------------+                         +-----------------------------+
| Demo Subapplication         |                         | Core Backend API            |
| (FastAPI, auth, coordinator)|                         | (backend/api.py, ETA, QML)  |
+-----------------------------+                         +-----------------------------+
         |                                                       |
         v                                                       v
 SQLite: .runtime/demo_store.sqlite3                     SQLite: .runtime/debugleaf.sqlite3
 - sessions, driver_state                                - exact plans, jobs, eta
 - congestion_reports, audits
```

---

## 2. Strict Repository Isolation

All code, tests, documentation, and dependencies for this mobile integration reside exclusively under `integrations/driver_mobile/`.

- Existing `backend/`, `frontend/`, `experiments_india_qml/`, `experiments_india_vqc4/`, and `tests/` directories remain completely untouched.
- `backend/api.py` was **NOT** modified. The existing backend is instantiated as a dependency via `backend.api.create_app()`.
- Composition is achieved at the ASGI level via `integrations.driver_mobile.server.app:app`.
- The original backend works identically on its own.

---

## 3. Directory Structure

```text
integrations/driver_mobile/
├── server/
│   ├── __init__.py           # Package marker
│   ├── app.py                # Top-level ASGI Gateway composer
│   ├── api.py                # Driver & Dispatcher FastAPI routes (/api/v1/demo/*)
│   ├── schemas.py            # Strict Pydantic v2 schemas
│   ├── auth.py               # Session redemption, token verification, role dependencies
│   ├── coordinator.py        # CAS route re-evaluation & publication coordinator
│   ├── storage.py            # Thread-safe, transaction-safe SQLite store
│   └── config.py             # Integration configuration
│
├── mobile/                   # React Native / Expo application
│   ├── app.json
│   ├── package.json
│   ├── tsconfig.json
│   ├── App.tsx               # Root entrypoint
│   └── src/
│       ├── api/              # client.ts, types.ts, driver.ts, reports.ts, session.ts
│       ├── auth/             # SessionContext.tsx, tokenStorage.ts
│       ├── config/           # env.ts, constants.ts
│       ├── features/         # sync, map, driver components
│       ├── components/       # NetworkBanner, StatusPill, ProvenanceBadge
│       └── screens/          # PairingScreen, DriverHomeScreen, RouteUpdatedAlert
│
├── contracts/
│   ├── openapi.json          # Exported OpenAPI 3.1 specification
│   ├── API_CONTRACT.md       # Comprehensive markdown API specification
│   └── examples/             # Request & response JSON samples
│
├── tests/
│   ├── conftest.py           # Isolated test fixtures
│   ├── test_auth.py          # Pairing, token verification, expiry, rate limiting
│   ├── test_permissions.py   # Role separation, dispatcher guards, job ownership
│   ├── test_routing.py       # Candidate evaluation, GeoJSON order, stop preservation
│   ├── test_idempotency.py   # Event replay safety, conflict detection, stale version checks
│   ├── test_concurrency.py   # CAS concurrency, cross-device state isolation
│   ├── test_acknowledgements.py # Monotonic version acknowledgements
│   ├── test_contracts.py     # Backend compatibility & OpenAPI validation
│   ├── test_failure_handling.py # Service restart, SQLite durability, sanitized errors
│   └── test_e2e_flow.py      # Complete multi-device demo scenario
│
├── scripts/
│   ├── preflight.py          # System environment & host IP discovery
│   ├── reset_demo.py         # Stopped-service clean reset of demo state
│   ├── start_server.ps1      # Server launch script (Uvicorn 0.0.0.0:8000)
│   └── start_mobile.ps1      # Expo Metro bundler launch script
│
├── operator/
│   └── observer.py           # CLI Dispatcher fleet console & watcher
│
├── fixtures/
│   └── deterministic_demo_config.json # Deterministic demo scenario
├── .env.example
├── README.md
└── IMPLEMENTATION_REPORT.md
```

---

## 4. Quick Start & Execution Guide

Run all commands from the git repository root (`silver-computing-machine`):

### Step 1: Preflight Check & Host IP Discovery
```powershell
.\.venv\Scripts\python.exe integrations/driver_mobile/scripts/preflight.py
```
Outputs the Lenovo Legion private IPv4 address (e.g. `172.80.1.249`) to target from physical devices.

### Step 2: Seed or Reset Demo State
```powershell
.\.venv\Scripts\python.exe integrations/driver_mobile/scripts/reset_demo.py
```
Initializes pairing codes `PAIR01` (Driver 1) and `PAIR02` (Driver 2) and default routes.

### Step 3: Run Automated Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest integrations/driver_mobile/tests -v
```
Executes 42 comprehensive integration and unit tests covering auth, concurrency, idempotency, routing, and contracts.

### Step 4: Launch Unified Server
```powershell
# Using PowerShell launch script:
.\integrations\driver_mobile\scripts\start_server.ps1

# Or directly with Uvicorn:
$env:DEBUGLEAF_AUTH_MODE = "token"
$env:DEBUGLEAF_DISPATCHER_TOKEN = "DEBUGLEAF_DISPATCHER_SECRET_KEY_9988"
$env:DEBUGLEAF_DEMO_FIXTURE_MODE = "1"
.\.venv\Scripts\python.exe -m uvicorn integrations.driver_mobile.server.app:app --host 0.0.0.0 --port 8000
```

### Step 5: Run Dispatcher Operator Observer (Terminal 2)
```powershell
.\.venv\Scripts\python.exe integrations/driver_mobile/operator/observer.py --watch
```
Monitors both drivers, route versions, active delay seconds, and incident overlays in real-time.

### Step 6: Launch Expo Mobile App (Terminal 3)
```powershell
cd integrations/driver_mobile/mobile
npm install
npx expo start --lan
```
Scan the displayed QR code with the **Expo Go** app on Phone A (Pair with `PAIR01`) and Phone B (Pair with `PAIR02`).

---

## 5. Security Architecture & Threat Model

1. **Scoped Driver Sessions**:
   - `POST /api/v1/demo/sessions` redeems a one-time code for `demo_sess_<40_hex>`.
   - Driver identity is resolved exclusively from the bearer token.
   - Client-provided driver IDs in request headers are rejected/ignored.
   - Session tokens expire after 240 minutes and support instant revocation.

2. **Role & Privilege Separation**:
   - Dispatcher overview requires `DEBUGLEAF_DISPATCHER_TOKEN` or `DEBUGLEAF_ADMIN_TOKEN`.
   - Driver bearer tokens attempting to call dispatcher routes return `HTTP 403 Forbidden`.
   - Driver tokens cannot approve India ETA proposals.

3. **Rate Limiting & Input Bounds**:
   - Pairing attempts are rate-limited to 5 attempts per minute per IP to prevent brute-force attacks.
   - Pairing codes, notes, and request IDs are bounded in length and character sets.

4. **Transactional CAS Mutations & Idempotency**:
   - Route version publication utilizes SQLite compare-and-swap semantics (`WHERE driver_id = ? AND route_version = ?`).
   - Simultaneous conflicting mutations fail with `HTTP 409 Conflict` (`stale_route_version`).
   - Replayed event IDs return the previously computed outcome without re-mutating route state.
   - Reused event IDs with conflicting payloads return `HTTP 409 Conflict` (`event_conflict`).

5. **Sanitized Error Responses**:
   - All errors follow `{"error": {"code": "...", "message": "..."}}`.
   - Internal exception tracebacks and local filesystem paths are never echoed in HTTP 500 responses.

---

## 6. Model Provenance & Simulation Labeling

- **Data Attribution**: All mobile route durations, distances, and geometries are explicitly labeled with `data_provenance: "synthetic_delhivery_v1"` and `simulation_mode: true`.
- **Honest Provenance**: The corridor scoring uses synthetic segment delays and duration matrices. It is **NOT** represented as running the 59-feature trained GBDT or 4-qubit VQC model.
- **No Quantum Superiority Claims**: The operational quantum fusion coefficient is $\alpha=0$; all route decisions are computed classically via the deterministic switching policy.
