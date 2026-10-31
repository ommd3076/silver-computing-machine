# Agent 03 — maps/geospatial

## Ownership and scope

Changed map-only files in `nmit-frontend/frontend/src/components/map/`: `RouteMap.tsx`, `geometry.ts`, and `geometry.test.ts`. Shared APIs, page components, shared CSS, and datasets were left to their owners. No commits or dependency installs.

## Diagnosis

- Geographic routes used MapLibre/OpenFreeMap, but tile errors only displayed a banner. The SVG fallback activated for WebGL failure and Solomon x/y, so a tile/style failure could leave the map visually blank.
- The geographic SVG fallback treated degrees as Cartesian units, distorting east-west distances.
- Initial bounds and reset trusted static `plan.bounds`, which could exclude updated route features.
- Geographic renderers labeled the map as Bengaluru and placed a “Central Hub” at the first route coordinate without source metadata.

## Changes

- Tile failure now switches to an interactive offline SVG route view, with numbered selectable stops and an ordered stop list.
- The local equirectangular fallback scales longitude by cosine of the mean latitude; Solomon coordinate projection remains its original equal-aspect x/y path.
- Geographic extents are recomputed from available route geometry, stop coordinates, and vehicle coordinates for fit/reset, with existing bounds as fallback only when features are absent.
- Removed the fabricated geographic depot marker. Scenario title is data-driven. Vehicle markers use their route color.
- Added a geometry unit case for longitude scaling.

## Refinement evidence

| Cycle | Failure hypothesis | Edit and retest | Result |
|---|---|---|---|
| 1 | A geographic fallback that scales raw longitude and latitude equally distorts route geometry. | Added local equirectangular scaling; `npm.cmd test -- --run src/components/map/geometry.test.ts`. | 4 tests passed, including equator and 28.6° latitude scaling. |
| 2 | Tile errors can leave a remote basemap canvas blank despite the warning banner. | Route rendering now switches to an interactive SVG and ordered stop list on tile errors; `npm.cmd run build`. | TypeScript and Vite production build passed. |
| 3 | Static scenario bounds and inferred depot markers can hide updated features or imply unsupported geography. | Fit/reset uses extant feature coordinates; removed the inferred geographic depot marker; `npm.cmd test -- --run src/components/map/geometry.test.ts` and `npm.cmd run build`. | 4 tests passed; production build passed. |

## Executed checks and limits

- `npm.cmd test -- --run src/components/map/geometry.test.ts` — PASS, 4 tests.
- `npm.cmd run build` — PASS. Vite emitted the existing large-chunk advisory (~1.86 MB JS minified).
- Browser interaction and live tile outage were not exercised. OpenFreeMap availability, authoritative South Delhi/Gurgaon road geometry, and real depot metadata remain external/source-data requirements; no GPS or road coordinates were invented here.
