# Luna 05 — mobile route map component

Date: 2026-10-30 (Asia/Calcutta). Scope: `nmit-frontend/apps/driver-mobile/src/components/DriverRouteMap.tsx` and `src/components/routeProjection.ts` only. No commits made.

## Delivered

- `DriverRouteMap` accepts `{ geojson: unknown; stops: DriverStop[]; selectedStopId?: string; onSelectStop?: (stop: DriverStop) => void }`; it imports `DriverStop` from `src/api/client.ts`.
- It renders actual GeoJSON LineString/MultiLineString geometry and valid backend stop coordinates, sorted by sequence. It does not create a synthetic origin, vehicle marker, GPS dot, or stop coordinate.
- It fits the provided geometry and stop coordinates to the available viewport with a local equirectangular projection. Web uses SVG polylines; native uses rotated React Native segments. Stops remain selectable.
- Basemap tiles are unavailable and stated as such; the component labels the output a schematic fitted to coordinates. Missing geometry and stop coordinates each produce explicit unavailable states.

## Refinement cycles and evidence

1. Failure hypothesis: mobile map would render only a placeholder and fail to show real route/stop data. Added the complete map component and actual GeoJSON/stop projection. `npm.cmd run typecheck` passed before App integration.
2. Failure hypothesis: malformed route vertices could be filtered and accidentally connected, and native route segments could pivot around incorrect positions. Reject malformed lines whole; position native segments around their midpoint. Whole-app `tsc --noEmit` passed after these edits.
3. Failure hypothesis: viewport fitting would misplace a singleton route point or mishandle unusable dimensions. Extracted `projectRouteMapPoints` into `routeProjection.ts`; added a deterministic local Node check. Check passed for fit bounds, geographic orientation, singleton centering, and zero viewport. The singleton assertion first failed, the centering edge case was fixed, and the rerun passed.

Latest whole-app check: `npm.cmd run typecheck` now reports one error in the concurrently edited, out-of-scope `App.tsx` at line 211: `accessibilityLiveRegion` is not a valid prop on its custom wrapper (TS2322). It reported no diagnostic in either map component file. I notified Luna 06 and the coordinator; a final whole-app pass is pending that App fix.

## Boundaries

- No live basemap, geocoder, GPS, API request, native device run, or browser visual screenshot was performed.
- GeoJSON input is typed `unknown`; only FeatureCollection/Feature wrapping LineString or MultiLineString is rendered. Invalid lines are omitted rather than repaired.
- No runtime dependency was added. Expo 58 versioned reference was checked (React Native 0.88; https://docs.expo.dev/versions/v58.0.0/).
