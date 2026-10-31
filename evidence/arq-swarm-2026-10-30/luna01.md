# Luna 01 — W03 dispatch planning

## Delivered
- `nmit-frontend/frontend/src/features/operations/DispatchView.tsx` exports `DispatchView(): ReactElement` with no props.
- Editable depot, vehicles/capacities, delivery IDs/demand/windows/service/penalty, and travel-time matrix.
- Calls backend `/api/v1/scenarios/validate`; only submits if backend returns valid.
- Exact enumeration submits `/api/v1/jobs`; warm-start QAOA submits `/api/v1/jobs/qaoa` with bounded explicit settings. Polls `/api/v1/jobs/{id}` and POST-cancels the real job. UI state comes from returned API data; no client-side solver or fake progress.
- Renders recognized exact/QAOA plan payloads, route order, returned stop timing, objective/travel/late exposure, backend independent validator output, provenance metadata, and explicit API/job failures.
- `nmit-frontend/frontend/src/features/operations/DispatchView.test.tsx` exercises validation -> submission -> status polling -> route and validation rendering using backend response fixtures.

## Checks actually run
- `npm.cmd run test -- src/features/operations/DispatchView.test.tsx` — PASS (1 test).
- `npm.cmd run build` — BLOCKED by unrelated/integration compile errors present in the shared tree: `App.tsx` imports missing `./features/operations/RecoveryView`; `api/client.ts` references undefined `timedOut` and has an incompatible `.map(jobFromApi)` callback; existing `DiagnosticsView.test.tsx` and `RouteComparisonView.test.tsx` type errors. No reported TypeScript errors in DispatchView or its test.
- Plain `npm` PowerShell launcher is blocked by execution policy; `npm.cmd` works.

## Remaining gaps
- API responses are type-checked for validation but plan/job data are intentionally treated as unknown-shape records at the rendering edge; malformed/unrecognized plans show an explicit message.
- Route geometry/map overlay and publish/approval remain outside W03.
- No live backend session was run in this bounded UI task; focused test uses response fixtures and proves client contract sequencing only.

## Follow-up integration fixes and live check
- Fixed travel-matrix edits being discarded during scenario normalization; the focused UI test now edits D→A from 2 to 9 and asserts the validation request contains 9.
- Added a per-run generation guard and AbortController for validation/submission/status polling; new runs and unmount abort stale requests, and stale responses cannot overwrite the active run. Cancel also aborts the poll before posting the cancellation request.
- `npm.cmd run test -- src/features/operations/DispatchView.test.tsx` — PASS (1 test).
- `npm.cmd run build` — PASS (`tsc -b` + Vite production build); Vite reports the existing large bundle warning (~1.8 MB minified JS).
- Real local API check at `http://127.0.0.1:8000`: `/api/v1/scenarios/validate` returned `valid=true`; POST `/api/v1/jobs` returned job `de5cd236-65cb-4da2-bfd4-f33167f9d50c`; GET polling reached `succeeded`. Execution metadata reported `local_classical` / `exact_enumeration`. Plan was feasible with V1→A,B and V2→C; objective 10.0 proxy units, travel cost 10.0 minutes, lateness exposure 0; independent validator returned `valid=true`, `feasible=true`, recomputed objective 10.0. This is local synthetic tiny-scenario evidence, not live-fleet evidence.
- Browser UI verification attempted using the available computer-use browser surface, but its browser access host is unavailable (inventory error); no browser-visible UI claim is made.
