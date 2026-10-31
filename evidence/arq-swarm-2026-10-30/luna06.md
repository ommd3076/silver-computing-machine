# Luna 06 — driver mobile UI

## Scope
Owned `nmit-frontend/apps/driver-mobile/App.tsx`. Kept the existing ten screens and session/refresh coordination; coordinated the map boundary with Luna 05. Consumed `DriverRouteMap` from `src/components/DriverRouteMap` with `geojson`, ordered `stops`, `selectedStopId`, and `onSelectStop`. No changes to API client or session store.

## Refinement cycles
1. **Failure hypothesis:** retrying after a dropped report response can create another congestion event because each tap used a new event ID. The report draft now reuses its event ID for the same route/severity/note payload and creates a new ID only when the draft changes; it clears after accepted response or session clear.
2. **Failure hypothesis:** the existing schematic was unrelated to dispatched geometry and implied a route shape. Replaced it with `DriverRouteMap`, passing the current state GeoJSON and manifest stops. Map selection highlights the selected manifest stop. The UI describes this as planned route only and explicitly disclaims live location and turn-by-turn guidance.
3. **Failure hypothesis:** an acknowledgement can be stale or refer to a route changed since the screen loaded. The action snapshots current route version/revision, blocks duplicate calls, verifies the response matches that exact pair, and clears prior acknowledgement when refreshed route identity changes. Errors are announced and dismissible; pairing supports keyboard submit, severity controls expose selected state, and refresh is disabled without a session or during work.

## Checks and evidence
- `npm.cmd run typecheck` in `nmit-frontend/apps/driver-mobile`: final run passed (exit 0). A prior run exposed TS2322 for the new live error announcement prop on `Card`; generalized the wrapper to forward native `View` props, then reran successfully.
- Read the reviewed `map-mobile`, `honest-data-states`, and `tokens-glass-light` project-local skills.
- Checked Expo SDK 58 docs at https://docs.expo.dev/versions/v58.0.0/ (2026-10-29 UTC); package.json is Expo `~58.0.21`, matching React Native 0.88. No Expo packages or native APIs were added.
- No device/emulator, visual screenshot, live API, or end-to-end test was run. Typecheck confirms compilation only.
- `pasted-text-1.txt` was not found in the checkout; the implementation followed supplied AGENTS instructions and the current ten-screen app.

## Remaining boundary
The map component reports its offline map fallback and fits route coordinates; basemap tiles are unavailable. Native device and live-backend behavior remain unverified.