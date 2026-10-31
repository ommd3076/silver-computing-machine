# Luna 15 — Fleet, driver, and order views

**Scope:** `nmit-frontend/frontend/src/features/operations/FleetOrderViews.tsx` only (plus this requested evidence note).

## Changes

- Search now matches vehicle, driver, route, corridor, status, and available manifest stop fields; matching is trimmed and case-insensitive.
- Added selectable sort fields and ascending/descending control for fleet, driver, and stop records.
- Added route/stop inspectors using dispatcher fields: route and manifest versions, acknowledgement label/timestamp, route-reported duration/distance, and stop status/address. Map actions preserve the existing `onOpenMap(vehicleId, stopId)` contract.
- Acknowledgement labels distinguish current, not acknowledged, behind, and anomalously newer reported versions.
- ETA and service windows remain `Unavailable`; no demand, contact, capacity, or live-GPS values are derived or invented.

## Checks actually run

- `npm.cmd exec -- oxlint src/features/operations/FleetOrderViews.tsx` from `nmit-frontend/frontend`: **PASS**, no diagnostics after removing one unused helper found on the first lint pass.
- `npm.cmd run build` from `nmit-frontend/frontend`: **BLOCKED by unrelated existing/workspace errors**. TypeScript reported missing `./features/operations/RecoveryView`, undefined `timedOut` in `src/api/client.ts`, a `map` callback type mismatch in that client, and errors in `DiagnosticsView.test.tsx` and `RouteComparisonView.test.tsx`. It reported no diagnostic in `FleetOrderViews.tsx`.

## Limits

No browser or live-backend interaction was run. Reviewed skill paths named in nested `AGENTS.md` (`.agents/skills/honest-data-states` and `api-contract-and-jobs`) were not present in this checkout; used the local endpoint contract, dispatcher types, and project rules instead. Parent-owned concurrent workspace changes were left untouched.
