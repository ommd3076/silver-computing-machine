# Luna 28 route map work

## Implemented

- Web route map uses MapLibre GL JS with an inline style and OpenStreetMap raster tiles, so route GeoJSON layers do not wait for a remote style file. The map begins at the first supplied coordinate, fits route bounds, and supports pan, zoom, and numbered stop selection.
- If browser WebGL is unavailable or MapLibre construction fails, the web view falls back to a fitted SVG of the same supplied route coordinates with selectable stops.
- Native route map is isolated in `src/components/DriverRouteMap.native.tsx` and uses MapLibre React Native. No device location permission or simulated GPS marker was added.
- Expo config plugin was added. Native MapLibre requires a development build and does not run in Expo Go.
- Route geometry is validated as actual longitude/latitude pairs. Malformed lines are rejected as a whole rather than joined across missing vertices.

## Evidence actually run

- `npx.cmd expo install @maplibre/maplibre-react-native` — installed `@maplibre/maplibre-react-native` 11.5.1 and added its Expo config plugin.
- `npm.cmd install maplibre-gl@^6.16.0` — installed MapLibre GL JS 6.16.x.
- `npm.cmd run typecheck` — PASS after fixing platform API/type mismatches.
- `npx.cmd expo export --platform web` — PASS; Metro emitted the MapLibre stylesheet (71 KB) and web JS bundle (1.5 MB).
- No native development build, emulator, physical device or GPS flow was run here. Expo export verifies web bundling only.
- A browser runtime retest was requested from the browser QA agent after the fresh web export; awaiting its report.

## Sources checked 2026-10-30

- Expo SDK 58 map-view reference: https://docs.expo.dev/versions/v58.0.0/sdk/map-view/ (reviewed; react-native-maps is Google Maps on Android and needs a configured Google key, therefore not selected).
- MapLibre React Native Expo setup: https://maplibre.org/maplibre-react-native/docs/setup/expo/ (documented: native module is not in Expo Go, install through Expo, configure plugin, rebuild).
- OpenStreetMap tile usage policy: https://operations.osmfoundation.org/policies/tiles/ (checked 2026-10-30; attribution is visible in the map control and footer; raster tiles are best-effort and not bundled offline).
- Project-reviewed local mobile map choice: `.agents/skills/map-mobile/SKILL.md` (MapLibre RN with OpenFreeMap; no keyed provider; no GPS dot).

## Remaining limits

- OpenFreeMap requires network access; no offline tile pack is bundled.
- Native physical-device usability still needs a development build and device verification.
- Browser QA must confirm map-style load, visible route fitting, stop selection and no regression in the driver flow.
