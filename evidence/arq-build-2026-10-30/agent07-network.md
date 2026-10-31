# Agent 07 — Driver mobile network and session reliability

Checked: 2026-10-30 (Asia/Calcutta). No commits made. Implemented only in the driver-mobile API/state boundary and App network/session handlers; visual screen layout was preserved.

## Changes

- `nmit-frontend/apps/driver-mobile/src/api/client.ts`: all requests have a 12-second timeout, accept abort signals, parse backend `{detail:{error:{code,message}}}` errors into stable `ApiError`, avoid sending JSON content type on GET, and expose current-session revocation. API origin remains configurable by `EXPO_PUBLIC_API_URL`; Android emulator and browser defaults remain distinct. A physical phone needs a reachable LAN API URL, never its own `localhost`.
- `nmit-frontend/apps/driver-mobile/src/state/session.ts`: session-scoped browser restoration via `sessionStorage`; expired/corrupt entries are discarded. Native persistence is currently memory-only because Expo SecureStore is not installed.
- `App.tsx`: refreshes are single-flight; periodic polling runs every 30 seconds and is skipped while app is backgrounded; requests abort on unmount; token checks prevent stale session responses writing into a later session. State and manifest must match driver, vehicle, route version, and revision before use/acknowledgement. Session expiry and 401 clear local session data. Logout clears UI/token first and then best-effort revokes server session. Report severity controls now match backend values (`moderate`, `heavy`). Acknowledgement uses route version plus matching manifest revision.

## Refinement cycles

| Cycle | Failure hypothesis and material edit | Retest and evidence | Remaining concern |
|---|---|---|---|
| 1 | A hung/offline fetch leaves UI actions waiting or hides backend error codes. Added 12-second abort, cancellation propagation, nested API error parsing, and typed error codes. | `npm.cmd run typecheck` passed after the change; Expo export passed. | No simulated mobile network-loss test. |
| 2 | Overlapping polls or an old session response could overwrite a newer route/session. Added single-flight polling, abort on unmount, token-scoped writes, identity matching, and exact route/revision matching. | `npm.cmd run typecheck` passed; `npx.cmd expo export --platform web` passed. Backend contract test also passed (see below). | No React Native runtime or rapid session-switch UI test. |
| 3 | Expired sessions and unsupported report enums could strand stale UI or be rejected; logout did not revoke server credentials. Added expiry/401 cleanup, browser session restore, local-first logout with revoke, and server-supported severity values. | Re-ran typecheck and web export successfully; backend driver contract test passed. | Native secure persistence is blocked by unavailable package/network access; native restart requires pairing again. |

## Checks actually run

- `npm.cmd run typecheck` in `nmit-frontend/apps/driver-mobile`: PASS (`tsc --noEmit`).
- `npx.cmd expo export --platform web`: PASS (Metro bundled `index.ts`, 197 modules; generated web export).
- `.venv\Scripts\python.exe -m pytest -q tests/test_arq_demo_driver_contract.py -o addopts= --basetemp=.testtmp-mobile`: PASS, 2 tests. Pytest's default `.runtime/pytest-tmp-codex` cleanup hit Windows access denial, so a workspace-local temporary basetemp was used. Pytest emitted cache permission and Starlette deprecation warnings.
- `npx.cmd expo install expo-secure-store`: BLOCKED by network `EACCES` / `AggregateError`; no dependency/package lock mutation occurred. No native token persistence is claimed.
- No live mobile API pairing/session or physical-phone test was run; no pairing codes were consumed. No authenticated route action from a phone was verified.

## API contract evidence inspected

Backend routes in `backend/demo/api.py` provide `POST /sessions`, `DELETE /sessions/current`, `GET /state`, `GET /manifest`, `POST /reports`, and `POST /acknowledgements`. Backend contract tests and `backend/demo/store.py` confirm `manifest.version` is the manifest revision while `manifest.route_version` is the route version. Ack requires `{version: route_version, manifest_revision}`. State and manifest identity/revision are checked before enabling an ack.

## Limits

Expo SecureStore was not added because the scoped install could not access the registry. Browser storage is session-only, not durable local storage. Native session restore therefore remains open. The physical-device LAN address and live API behavior are unverified. The map JSX was not changed as part of this network/state assignment.
