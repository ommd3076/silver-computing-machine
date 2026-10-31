# Agent 01 backend integration evidence

Checked 2026-10-30, Asia/Kolkata. Scope is the local mobile driver and dispatcher demo. This is a prototype SQLite/API workflow; it is not production identity, a live-fleet integration, or a fully validated dispatch solver.

## Implemented interfaces

- `POST /api/v1/demo/sessions` accepts `{ "code": "PAIR01" }` and returns the opaque bearer token plus driver and vehicle IDs and expiry. Pairing codes are one-use across router restarts.
- Set `DEBUGLEAF_DEMO_DB_PATH` to a fresh path under `.runtime/` when starting an isolated local demo; absent that variable, the existing default `.runtime/demo_store.sqlite3` remains in use. Existing state is not cleared by startup.
- `GET /api/v1/demo/me`, `GET /api/v1/demo/state`, `GET /api/v1/demo/manifest`, `POST /api/v1/demo/reports`, `POST /api/v1/demo/acknowledgements`, and `DELETE /api/v1/demo/sessions/current` require the bearer driver session. State and manifest are derived from the session identity; caller-supplied target driver IDs are ignored or rejected.
- Reports take `{event_id,base_route_version,severity,note}`. The event is idempotent for identical driver and content; a conflicting replay returns 409. A report is evaluated against the demo catalog and persisted as a proposal without changing route state.
- Dispatcher state is `GET /api/v1/demo/dispatcher/state` and audits are `GET /api/v1/demo/audits`. `GET /api/v1/demo/proposals/{proposal_id}` and `POST /api/v1/demo/proposals/{proposal_id}/approve` are dispatcher/admin-only in configured token mode. Local mode permits dispatcher actions only from a loopback client. Driver sessions cannot approve.
- Approval atomically checks the proposal's base route version, writes a versioned vehicle-scoped manifest, advances route and manifest versions, and records the approving actor. A stale proposal returns a stable conflict. Repeated approval returns the current manifest without advancing version.
- Acknowledgement takes `{version,manifest_revision}` and only records the exact current driver's versions. The saved acknowledgement includes version, manifest revision, and timestamp; it is scoped by bearer identity.

State and manifest stop entries include catalog stop ID, sequence, catalog coordinate, assigned status, and explicit null address/ETA-window fields. The catalog does not contain individual progress, delivery addresses, SLA windows, capacity details, or financial terms. The API does not invent those fields.

Approval validation independently checks that the candidate exists, belongs to the same vehicle, preserves the active ordered stop sequence, has finite geographic coordinates in valid longitude/latitude bounds, and has a recomputed duration matching the proposal-time congestion overlay and catalog segment durations. It also confirms the GeoJSON matches the catalog and distance is finite and nonzero. The returned validation scope explicitly excludes capacity, delivery windows, financial objective, live conditions, and full operational feasibility. Map clients should treat the route as a catalog candidate, not a validated dispatch plan.

## Refinement cycles

| Cycle | Failure hypothesis | Material change | Retest and evidence | Remaining limit |
|---|---|---|---|---|
| 1 | Driver query/default fallback lets one phone read another driver's state. | Require bearer session for driver operations and derive scope only from the session. Remove driver ID from state/report/ack targeting. | `tests/test_arq_demo_driver_contract.py` checks `driver_1` remains the state target even when the URL asks for `driver_2`; cross-driver driver token cannot access dispatcher endpoints. | Pairing code provisioning is demo-only; no external identity provider. |
| 2 | A retried congestion report can create repeated side effects and publishes a route before a dispatcher decides. | Persist event content hash and proposal; same-content replay returns the saved proposal, conflicting replay returns 409; route remains unchanged until separate approval. | Targeted HTTP integration test verifies repeated response equality, conflict 409, and route version remains 1 before approval. | Proposal replan uses the fixed local route catalog and a synthetic severity-to-delay overlay. |
| 3 | In-memory/implicit versions lose published assignments and acknowledgements on process restart. | Add SQLite proposal, event, manifest and exact acknowledgement-revision persistence; pair code seeding no longer resets redemption. | Targeted restart reconstruction confirms published bypass route, manifest revision 2, sessions, and driver 2 acknowledgement revision persist. | This test reconstructs the router/service over SQLite in-process; it does not kill/restart a separate Uvicorn process. |
| 4 | A catalog candidate can be published without checking it against the active vehicle/stops or its cost/geometry. | Recompute catalog vehicle, ordered stop, geometry, duration, distance, and GeoJSON checks before approval; persist validation scope with manifest. | Targeted test checks successful validation result and bounded scope, then confirms route publication. | Not a full fleet/financial/time-window validator; live conditions and stop completion are unavailable. |

## Executed checks

- `.venv\Scripts\python.exe -m compileall -q backend` — passed.
- `.venv\Scripts\python.exe -m pytest tests/test_arq_demo_driver_contract.py -q --basetemp=.runtime/arq-backend-driver-final -o cache_dir=.runtime/arq-cache-driver-final` — passed, 2 tests, 1 environment deprecation warning. Covers pairing, bearer scope, proposal replay/conflict, no pre-approval publish, role denial, approval validation, version publication, exact acknowledgement, dispatcher snapshot and SQLite-backed reconstruction.
- `.venv\Scripts\python.exe -m compileall -q backend` — passed after the backend edits.
- Test transport is FastAPI `TestClient` against a loopback base URL with SQLite under pytest's isolated temporary directory. No external server, fleet, or mobile device was exercised.
- One Starlette deprecation warning notes the environment's `httpx` integration; it did not fail the tests.

## Not changed / open

`backend/runs_service.py` remains the static run-fixture service; `/api/v1/demo/dispatcher/state` is the authoritative South Delhi driver snapshot. Existing `/runs` preview rows should remain labeled fixtures. The static route catalog does not contain capacity, financial terms, individual completion state, or contractual windows. No real rupee savings or operational feasibility claim is made.
