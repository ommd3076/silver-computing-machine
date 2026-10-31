# Luna 11 operations module evidence

## Scope
Edited only `nmit-frontend/frontend/src/features/operations/useOperations.ts`, `adapter.ts`, their dedicated tests, and this evidence note. No commits made. Existing unrelated edits elsewhere in the shared checkout were left untouched.

## Refinement cycles

| Cycle | Failure hypothesis | Material change | Retest evidence | Remaining concern |
|---|---|---|---|---|
| 1. Refresh lifecycle | A caller can trigger overlapping dispatcher polling, and unmount can leave old calls racing new component state. | Share an active refresh promise, pass an AbortSignal to dispatcher reads, abort on cleanup, and gate all updates by generation/alive checks. | `npm.cmd exec vitest -- run src/features/operations/useOperations.test.ts src/features/operations/adapter.test.ts --reporter=verbose`: 5 tests passed. Includes deduplication, abort, and late result discard. | `apiClient` read methods do not accept signals, so those reads cannot be physically cancelled; their late state is still generation-discarded. |
| 2. Auth and stale dispatcher state | A denied state read can leave the previous dispatcher state or audit trail visible as if current. | Treat state and audit reads as one authenticated snapshot; clear both on either failure; advance `lastSync` only on a complete pair. | Same targeted Vitest command: 5 tests passed, including stale state and stale audits clearing after an Unauthorized rejection. | No live authenticated dispatcher server was used; auth behavior was exercised with a rejected client promise. |
| 3. Adapter provenance | Hardcoded corridor, active status, fixture source, zero demand/risk/financial values and guessed coordinates can masquerade as real data. | Derive corridor, route estimates, geometry, stop order/status/completion, vehicle status and coordinates from dispatcher state. Mark unavailable numeric fields NaN, reject invalid geometry points, and label the plan Preview. | Same targeted Vitest command: 5 tests passed; adapter tests assert source values and unavailable measures. | The shared `PlanRun` schema requires numeric fields and narrows statuses; NaN/casts carry unavailable/unknown values through the map-only adapter. Consumers must not use this projection for KPIs or validation. |

## Executed checks

- Targeted Vitest: PASS, 2 files / 5 tests.
- `npm.cmd run build`: FAIL before Vite build due to unrelated TypeScript errors in `src/api/client.ts` (Abortable response typing and map callback argument) and `src/features/operations/DiagnosticsView.test.tsx` / `DiagnosticsView.tsx`. No diagnostic pointed to the assigned operations hook, adapter, or their tests.
- First plain `npm test` was blocked by PowerShell execution policy for `npm.ps1`; using `npm.cmd` worked.
- API references inspected: `nmit-frontend/frontend/src/api/ENDPOINTS.md`, `dispatch.ts`, and `client.ts`. The repo guidance names `api-contract-and-jobs` and `honest-data-states`, but those skill folders are absent from `.agents/skills`; reviewed `architecture-patterns` was available and used for keeping the adapter as a narrow translation boundary.

## Integration boundary

`dispatchApi.state(signal)` and `dispatchApi.audits(signal)` use the actual `/api/v1/demo/dispatcher/state` and `/api/v1/demo/audits` routes. No demo state, map coordinates, successful auth, live backend access, or deployment was claimed or exercised.
