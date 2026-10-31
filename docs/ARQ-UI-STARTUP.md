# arQ UI local startup

This guide starts the two UIs under `nmit-frontend` against the coordinator-managed V1 API on port 8001. It connects the interfaces to that local API; it does not establish live fleet, cloud solver, or device behavior. The launcher is `tools/start-arq-ui.ps1`. It was authored but not run in this handoff.

## Prerequisites

- Windows PowerShell and Node/npm available in the launching shell.
- `npm ci` already completed in `nmit-frontend/frontend` and `nmit-frontend/apps/driver-mobile`.
- Coordinator API reachable at port 8001 and port 5173 free. Expo web uses 8082; Expo Go/Metro uses 8081.

The launcher does not install packages, change PATH, or start GPU/QPU work.

## Loopback run

From the repository root:

```powershell
.
tools\start-arq-ui.ps1
```

This starts Vite on `127.0.0.1:5173` and Expo web on `localhost:8082`, both pointed at the coordinator API `http://127.0.0.1:8001`. It does not start or stop the API. Open either web UI. To start Expo Go/Metro instead, use `-ExpoMode Native`; `-ExpoMode Both` starts both Expo targets. In loopback Native mode the mobile client points to Android emulator host alias `10.0.2.2:8001`. For iOS simulator or a physical phone use LAN mode.

Each invocation puts logs and a process manifest under `.runtime/arq-ui/<run-id>/`. The API and its database are coordinator-managed and are not reset, overwritten, or deleted by this launcher. Use `logs/*.out.log` and `logs/*.err.log` for startup failures. If the script reports a port collision, stop the service already using 5173 before retrying.

## Optional phone/LAN run

First configure three distinct, nonempty role tokens in the launching PowerShell process using your approved secret source. The launcher only checks that they exist and differ; it never prints or saves their values. Do not put real values in this document, a `.env` file, screenshots, or command history.

```powershell
.
tools\start-arq-ui.ps1 -Lan -ExpoMode Native
```

`-Lan` makes the UI development servers reachable on the selected private IPv4 address and configures their clients for `http://<LAN-IP>:8001`. The coordinator must have already configured the API on that address in token mode. The launcher checks for three distinct role tokens in the current environment but does not start/configure the API or display/save token values. The printed URLs and Expo log show the selected address. Firewall and Wi-Fi client isolation can still block access. In the web UI, enter a dispatcher/admin bearer token through its Access control UI when a protected dispatcher call requires it; the value is not part of the launcher output. The driver app separately redeems its one-time pairing code and stores its scoped demo session on the device.

LAN access is for a trusted development network only. The token role mode is a local prototype and has no TLS, rotation, expiry, rate limits, or production secret manager. Return to loopback for ordinary local use.

## Driver pairing and state

The backend seeds `PAIR01` for Ramesh Kumar / `driver_1` / `vehicle_1` and `PAIR02` for Suresh Patel / `driver_2` / `vehicle_2`. Each code atomically redeems once into a random, expiring driver session. A second redemption from the same database returns `pairing_failed`. Codes use `INSERT OR IGNORE`; restarting the API against the same database does not reissue used codes. This UI launcher does not reset or rotate the coordinator's demo database; confirm the current run's codes have not already been redeemed. Treat these demo codes as public test values, not authentication credentials.

## What the interfaces contain

The web navigation has 10 views: Command center, Live map, Dispatch planning, Plan comparison, Fleet, Drivers, Orders, Analytics, Diagnostics, and Recovery. The mobile app has four persistent tabs: Home, Route, Stops, and Settings/Connection; its flow also includes route guidance, stop details, congestion report, replan status, and route acknowledgement.

The web frontend calls the API contract listed in `nmit-frontend/frontend/src/api/ENDPOINTS.md`. A reachable backend is not proof every page has populated data: unavailable/unimplemented API records stay empty or show errors. The current recovery endpoint is fixture-oriented, and the mobile app's ETA/late probability and many ancillary screens are explicitly simulated or local preview state. Mobile backend-backed functions are pairing, reading route state/manifest, submitting congestion reports, checking published revisions, acknowledging a route, and ending a session. GPS tracking, proof of delivery, live telematics, offline synchronization, calling/texting, and native navigation are not implemented integrations.

The current V1 backend's QAOA path is a local simulator with an explicit classical fallback; VQC inference is a local reference circuit or optional local SDK path. The UI startup process does not invoke QCloud, QpiAI Opt service, or a QPU. Do not describe simulator counts as a solved/validated operational dispatch. See `docs/API-RUNTIME.md`, `docs/V1-RUNBOOK.md`, and `docs/TERRA-V1-REPORT.md` for the backend's actual limits and evidence labels.

## Exact project commands inspected

The launcher implements the checked-in package entry points and the API module. Equivalent commands (with loopback binds and launcher's isolated run databases) are:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
Push-Location nmit-frontend\frontend; $env:ARQ_API_TARGET='http://127.0.0.1:8001'; npm run dev -- --host 127.0.0.1 --port 5173; Pop-Location
Push-Location nmit-frontend\apps\driver-mobile; $env:EXPO_PUBLIC_API_URL='http://127.0.0.1:8001'; npm run web -- --host localhost --port 8082; Pop-Location
# Alternative native target:
Push-Location nmit-frontend\apps\driver-mobile; $env:EXPO_PUBLIC_API_URL='http://10.0.2.2:8001'; npm start -- --lan --port 8081; Pop-Location
```

The Vite config proxies `/api` to port 8001 by default and accepts `ARQ_API_TARGET` as an override. The mobile API client uses `EXPO_PUBLIC_API_URL`; the launcher sets port 8001 for each target. In loopback Native mode, Android emulator requests use `10.0.2.2:8001`. A physical phone needs `-Lan` so its compiled bundle receives the computer's LAN API URL.

## Evidence boundary

Inspected source paths: `README.md`, `docs/V1-ACCEPTANCE.md`, `docs/API-RUNTIME.md`, `docs/V1-RUNBOOK.md`, `sources/problem-extract.txt`, `backend/api.py`, `backend/auth.py`, `backend/demo/api.py`, `backend/demo/auth.py`, `backend/demo/store.py`, both package manifests, Vite config, Expo app config, and both API clients. Source review confirms commands, client URL rules, and one-use code semantics. The coordinator has since moved the API to port 8001 because port 8000 is occupied by a stale process. No service was started by this launcher, no UI/device was rendered by this handoff, and no LAN/authenticated integration was tested here. The script's actual launch behavior remains to be exercised by the coordinator after authorization.
