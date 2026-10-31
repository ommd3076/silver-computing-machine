# Luna 10 — map geometry

## Scope

Owned only `nmit-frontend/frontend/src/components/map/geometry.ts` and `geometry.test.ts`. RouteMap owner confirmed GeoJSON semantics: geographic positions are `[longitude, latitude]`; Solomon positions are Cartesian `[x, y]` and must not receive geographic transforms.

## Failure hypothesis

Malformed geographic bounds could be accepted despite extra ordinates, and padded single-point bounds exactly on a world edge could collapse to zero width or height. Separately, invalid geographic coordinates could contaminate fallback SVG projection, while out-of-range reference latitudes distort longitude scaling. The existing Cartesian projector also accepted invalid padding values.

## Edit

- Added `isValidLngLat` to validate finite `[lng, lat]` positions against geographic ranges.
- Required exactly two ordinates per bounds corner.
- Kept edge-clamped singleton bounds non-degenerate.
- Geographic fallback projection now marks invalid positions as NaN and clamps its reference latitude to `[-90, 90]`.
- Cartesian square projection filters malformed points and safely defaults/clamps padding; equal-aspect scaling remains intact.
- Added focused tests for each case, including aspect-preserving Cartesian mapping.

## Retest

Command: `npm.cmd exec vitest run src/components/map/geometry.test.ts`

Result: **PASS** — 1 test file, 6 tests passed; exit code 0. First invocation via `npm` was blocked by PowerShell execution policy; rerun via `npm.cmd` completed normally.

## Limitation

`RouteMap.tsx` remains outside my ownership. I notified its owner to filter invalid geographic route positions before rendering, because a NaN pair is intentionally not converted into an apparently valid point by the helper. No claims made for dateline-crossing extents or live map rendering.
