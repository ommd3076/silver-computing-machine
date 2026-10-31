# Luna 12 — Dispatcher web API client

## Scope

Changed only `nmit-frontend/frontend/src/api/dispatch.ts` and added `nmit-frontend/frontend/src/api/dispatch.test.ts`. Backend contract was inspected in `backend/demo/api.py`, `backend/demo/service.py`, `backend/demo/store.py`, `backend/auth.py`, and `backend/api.py`. The referenced local `api-contract-and-jobs` skill was not present under `.agents/skills/`, so no unreviewed/global skill was used.

## Verified contract details

- Dispatcher reads are `GET /api/v1/demo/dispatcher/state` and `GET /api/v1/demo/audits`.
- Approval is `POST /api/v1/demo/proposals/{proposal_id}/approve`; backend authorization is dispatcher/admin-only and the service/store rechecks pending status, proposal validity, and `base_route_version` before publishing. Approval returns a published manifest (driver/vehicle, versions, route/corridor, status), not the full `DriverState` shape.
- The exact solver accepts `{scenario_id, engine, scenario}` at `/api/v1/solve` and supports only `exact_enumeration`/`exact`; QAOA accepts `{scenario, seed, shots, warm_start, angle_grid}` at `/api/v1/scenarios/qaoa`.
- Dispatcher failures may use either top-level `{error: ...}` or FastAPI `{detail: {error: ...}}` envelopes.

## Changes

- Preserve existing exported dispatcher data interfaces and add `ApprovalManifest` for the actual approval response.
- Validate dispatcher-state, audit, proposal, and approval JSON at the client boundary.
- Keep per-request `X-Request-ID`; keep the bearer token in the Authorization header only. Redact its value from backend error messages/details.
- Distinguish timeouts (`timeout`, HTTP-style status 408), explicit caller cancellation (`cancelled`), and connection failures (`network_error`). Preserve stable authorization and stale-proposal error codes.
- Keep stale-version approval enforcement server-owned; the client does not optimistically publish or infer success.

## Executed checks

- `npm.cmd test -- --run src/api/dispatch.test.ts` in `nmit-frontend/frontend`: **PASS**, 1 file / 7 tests.
- `npm.cmd run build` in `nmit-frontend/frontend`: **FAIL**, TypeScript reports four errors outside the assigned files: `src/api/client.ts` lines 98, 109, 188 (owned by luna13) and `src/features/operations/DiagnosticsView.test.tsx` line 38. No reported diagnostic points to `dispatch.ts` or `dispatch.test.ts`. Build did not reach successful Vite production bundling.
- An initial `npm test` invocation was blocked by PowerShell execution policy (`npm.ps1`); rerunning as `npm.cmd` executed the test suite successfully.

No live backend, browser, mobile device, or authenticated dispatcher integration was exercised. Approval/auth tests mock HTTP responses; they check request routing, status/code propagation, and token non-disclosure in client errors.
