# Luna 29: Expo mobile browser runtime smoke

## Scope and method

QA only for `nmit-frontend/apps/driver-mobile`. No product source was edited and no commit was made. CUA's browser host was unavailable, so I used the repository-installed Playwright Chromium against the exported Expo web app at a 390 × 844 mobile viewport. Chromium launched with GPU disabled. The final Expo export was built from current app source with `EXPO_PUBLIC_API_URL=http://127.0.0.1:8001`; the target was the live local FastAPI service on port 8001, not a mocked API. This is browser/web-runtime evidence, not Android/iOS or device evidence.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Expo web export from current source | **PASS** | `.runtime/swarm-mobile-export`; current bundle `_expo/static/js/web/index-ee05184374607617df582b0b29f78162.js` (1.5 MB). MapLibre CSS also emitted. |
| Playwright Chromium launch with `--disable-gpu --disable-software-rasterizer` | **PASS** | Browser ran and rendered the app; no GPU fatal. |
| PAIR01 against local API 8001 | **PASS** | Pair form and authenticated home screenshots captured; home transition awaited the actual `Ramesh Kumar` session identity. |
| PAIR02 against local API 8001 | **PASS** | Separate pair form and authenticated home screenshots captured; home transition awaited `Suresh Patel`. |
| Tap Route | **FAIL** | Uncaught browser error `Cannot read properties of undefined (reading 'Map')`; the route screen went blank. `View route guidance` did not render. See `mobile-capture-attempt.txt` and `mobile-screens/05-route-map.png`. Reported to Luna 28 and root. |
| Navigation, stops, report, and settings screens | **NOT RUN** | Blocked by the Route screen crash before those interactions. |

Screenshots captured: `mobile-screens/01-pair-driver-1.png`, `02-home-driver-1.png`, `03-pair-driver-2.png`, `04-home-driver-2.png`, and `05-route-map.png`. A prior attempt on the stale API port 8000 recorded HTTP 403 for PAIR01 because that one-time code had already been redeemed by the earlier smoke; the current run used the fresh API 8001 and succeeded for both codes.

## Limits

- The browser screenshots do not establish a native Expo runtime, emulator, or physical-device pass.
- The API sessions were live localhost requests through the mobile client; no dispatcher approval or route publication was performed.
- The route runtime failure is an app error, not an API failure. Additional navigation and report flows remain unverified until the Map crash is fixed and fresh pairing codes are available.

## Post-map-change rerun

After Luna 28 changed the map renderer, I rebuilt the Expo web export with API origin 8001 and reran both fresh driver pairings. SCREENA and SCREENB each authenticated successfully and rendered their separate home states. Tapping Route still raised uncaught `(0 , a.supported) is not a function`; the route heading/map did not render. The run stopped before reports or proposal creation. Current evidence: `mobile-flow-failure.txt`, `mobile-flow-results.json`, and `mobile-screens/flow-01-home-driver-a.png` / `flow-02-home-driver-b.png`. Both new one-time pairing codes were consumed. Luna 28, root, and Luna 23 were notified; no web approval was attempted.

## Final map runtime check

The next source update removed the `supported()` runtime error. A new export rendered the route screen, but MapLibre failed to load its worker: Playwright recorded HTTP 404 for `/_expo/static/js/web/maplibre-gl-worker.mjs?v=6.16.0` and `Worker failed to load`. The captured map canvas has no visible path or stop markers, so actual route geometry visibility remains **FAILED**. Evidence: `mobile-flow-results.json` and `mobile-screens/flow-03-active-route-map.png`. This run stopped before submitting a report; FINAL01 and FINAL02 were consumed. Luna 28, root, and Luna 23 were notified.

## Coordinator's final worker-fix run

Root then bundled MapLibre's worker at the same origin and used an SVG overlay fallback. I visually inspected the newer `mobile-screens/flow-03-active-route-map.png`: route polylines and the two stop coordinate markers are visible, while external OSM tiles are unavailable in the sandbox. The root flow captured driver A/B home, route map, navigation, stops, report form, heavy report, and pending proposal screenshots (`flow-01` through `flow-08`). Live API result: proposal `proposal_a6b621e911424617921ba6d800053913` for `vehicle_1` / `driver_1`, `PROPOSE_ROUTE`, base route version 1. The independent dispatcher UI could not review or approve it because the browser client rejected the server proposal shape (driver/vehicle identifiers nested instead of at the top level). Luna 23 did not call the API directly. Therefore post-publication mobile refresh, acknowledgement, driver B isolation after approval, stop detail, and settings after the latest export remain **NOT VERIFIED**; no approval or route publication is claimed.
