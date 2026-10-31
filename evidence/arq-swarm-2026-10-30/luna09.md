# Luna 09 — Web route map repair

**Date:** 2026-10-30 (Asia/Kolkata)  
**Scope:** `nmit-frontend/frontend/src/components/map/RouteMap.tsx` only.  
**Usage gate:** `get_usage_limits` was not available in this session; the dispatch explicitly waived this gate. No workers or new jobs were started.

## Inspected contract and boundaries

- Read root and frontend `AGENTS.md`, `README.md`, `docs/V1-ACCEPTANCE.md`, `bootstrap/SKILLS-REVIEW.md`, `bootstrap/SDK-EVIDENCE.md`, `bootstrap/ARCHITECTURE-READINESS.md`, `sources/problem-extract.txt`, `docs/TERRA-V1-REPORT.md`, and `docs/V1-RUNBOOK.md`.
- Read local project skills `nmit-frontend/skills/map-web/SKILL.md` and `nmit-frontend/skills/honest-data-states/SKILL.md`.
- `PlanRun.coordinate_system` distinguishes `lat_lon` from `cartesian_xy`; route geometry pairs are `[longitude, latitude]` GeoJSON coordinates for geographic plans and `[x, y]` for Solomon. Stop and vehicle position fields likewise differ by coordinate system.
- There is no candidate-route geometry in the current `PlanRun` API. Command Center's delay candidate is an advisory stop. RouteMap continues to show the selected current-plan route and risk marker without inventing a bypass line or changing API types.

## Changes made

- Geographic route, stop, and vehicle coordinates are range-checked before entering MapLibre bounds, GeoJSON layers, markers, or the geographic SVG fallback. Cartesian points remain range-agnostic and use the square projector.
- MapLibre reinitializes when the current plan's route/vehicle data or bounds change, even when `plan.id` stays the same; selection-only renders still do not recreate it. This can reset a manually panned view when plan data changes, but prevents stale overlays and markers.
- Map bounds include valid route, stop, and vehicle positions. Selecting a stop focuses that stop; selecting a vehicle fits its route, stops, and live position, after the initial full-plan fit has completed.
- Stop pins and the offline ordered-stop list sort by `sequence_idx`. Fallback vehicle markers use a distinct palette when no route color exists. WebGL failure also exposes the ordered-stop fallback list.
- Tile failure state is keyed to the plan ID, so one plan's tile failures do not force a replacement plan offline. Error messages without `error.message` no longer throw while classifying tile errors.

## Refinement cycles

| Cycle | Failure hypothesis / evidence | Material edit | Rerun and result | Remaining concern |
|---|---|---|---|---|
| 1 — live plan refresh | A same-ID plan update left MapLibre initialized from the previous captured plan; initialization depended only on ID and renderer flags. | Include route, vehicle, and bounds data in the map lifecycle dependencies, while keeping callbacks and selection outside those dependencies. | `npm.cmd run build` ultimately passed (TypeScript + Vite). An earlier overlapping run saw transient unrelated TS errors in `api/client.ts` and `DiagnosticsView.test.tsx`; the later clean run supersedes it. | Data changes recreate MapLibre and can reset manual camera position. |
| 2 — coordinate integrity | Map initialization had an unused filtered route-coordinate array, while its extent used raw route coordinates; geographic SVG lines could also project malformed positions. | Validate actual `[lng, lat]` pairs at geographic boundaries; preserve Cartesian `[x,y]` without geographic bounds; sanitize fallback route, stop, and vehicle positions. | `npx.cmd vitest run src/test/Components.test.tsx -t "ensures" --reporter=dot` passed 3 geometry tests; 14 unrelated tests were skipped. | No dedicated invalid-coordinate UI fixture was added because file ownership was limited to RouteMap. |
| 3 — selection, fallback, ordering | A selection effect could focus before MapLibre load and then be overridden by its full-plan fit; stop arrays and fallback status were not normalized. | Defer selection focus until load when needed, fit a selected vehicle's route bounds, sort stops, key tile failure per plan, and show ordered stops on WebGL failure. | `npx.cmd oxlint src/components/map/RouteMap.tsx` passed with no warnings. The focused `ensures` test command above passed after the final edit; final `npm.cmd run build` passed. | No live browser/tile-network visual run was performed. |

## Executed checks

- **PASS:** `npm.cmd run build` from `nmit-frontend/frontend` — `tsc -b` and Vite production build completed; Vite emitted its existing large-chunk warning.
- **PASS:** `npx.cmd oxlint src/components/map/RouteMap.tsx` — no findings.
- **PASS:** `npx.cmd vitest run src/test/Components.test.tsx -t "ensures" --reporter=dot` — 3 passed, 14 skipped.
- **PARTIAL / stale UI expectations:** `npx.cmd vitest run src/test/Components.test.tsx --reporter=dot` — 14 passed, 3 failed. Failures expect retired fixture labels (`Depot (40, 50)`, `Bengaluru Dispatch Corridors`) or assume the scenario name appears only once; current fixture metadata uses different labels. The route rendering has no browser/WebGL assertions in that test file.
- **NOT RUN:** browser visual check, live OpenFreeMap tile/network check, mobile check, API test, or candidate-path overlay check. No candidate path exists in the input contract.

## Three-cycle gate and handoff

Three failure-hypothesis refinement cycles are documented above with source evidence, edits, and reruns. The map code does not change backend endpoints or types. Full build success is technical evidence only; it does not establish tile availability, visual quality in a real browser, or a candidate bypass overlay.
