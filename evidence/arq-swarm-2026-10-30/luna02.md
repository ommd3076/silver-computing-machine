# Luna 02 — W04 Route Comparison

Date: 2026-10-30 (Asia/Kolkata)

## Changed files
- `nmit-frontend/frontend/src/features/operations/RouteComparisonView.tsx`
- `nmit-frontend/frontend/src/features/operations/RouteComparisonView.test.tsx`

## Implementation
`RouteComparisonView({ operations }: { operations: ReturnType<typeof useOperations> })` selects only pending proposals from the dispatcher snapshot, pairs a proposal with its active vehicle manifest, and shows durations only from the API fields. If either duration is absent, it shows `Unavailable`. SLA and rupee exposure are explicitly unavailable because the dispatcher/catalog contract has no such values. Validation is described as bounded candidate checks only; no full operational-feasibility claim is made.

When both current and candidate GeoJSON contain valid `[longitude, latitude]` coordinates, the view overlays the backend polylines in a shared extent SVG. It rejects a line if any coordinate is malformed. Approval is disabled unless there is a pending record ID, requires a second explicit confirmation, and calls `dispatchApi.approve`; success text appears only after the API response, followed by a state refresh. The route comparison reports “No speed-up claimed.”

## Refinement cycles
1. **Failure hypothesis:** absent SLA/cost/duration data could be filled with attractive but invented numbers. **Change:** display only proposal/manifest duration fields and mark unsupported metrics unavailable. **Evidence:** targeted test checks real supplied durations and the unavailable states.
2. **Failure hypothesis:** an accidental click could publish a candidate before review. **Change:** require a pending backend proposal ID and a separate confirmation before the approval API call. **Evidence:** targeted test verifies no approval call before confirmation and verifies the actual proposal ID is passed after confirmation.
3. **Failure hypothesis:** filtering invalid coordinates could join distant valid points into a route that was never supplied. **Change:** reject the whole line on any invalid point and show the geometry-unavailable state. **Evidence:** targeted test supplies an out-of-range coordinate and confirms no SVG route is rendered.

## Checks
- `npm.cmd run test -- --run src/features/operations/RouteComparisonView.test.tsx` — passed, 1 file / 3 tests.
- `npm.cmd run build` — blocked by existing/concurrent TypeScript errors outside the assigned component: `src/api/client.ts` (`abortError` return type and `map` callback arg mismatch) and `src/features/operations/DiagnosticsView.test.tsx` (`status` inferred as `string`, not `JobStatus`). No RouteComparisonView type errors were reported.

## Evidence boundary
The dispatcher contract and `evidence/arq-build-2026-10-30/agent01-backend.md` describe catalog route proposals and bounded approval validation. This is frontend rendering of backend data; no authenticated live API or browser/device integration was exercised here.
