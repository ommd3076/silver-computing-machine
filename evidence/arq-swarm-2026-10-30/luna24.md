# Luna 24: Expo mobile QA

## Scope

QA only for `nmit-frontend/apps/driver-mobile`. No app source was edited and no commit was made. The build and capture artifacts are local; no native device or emulator was tested.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| `npm.cmd run typecheck` | **PASS**, exit code 0 | TypeScript completed without diagnostics. |
| `npx.cmd --no-install expo export --platform web --output-dir C:\ommd3076\Proejcts\nmit-hackathon\.runtime\swarm-mobile-export` | **PASS** | Expo 58 web bundle completed; `index-6cd715ab7fbc5118f8f97fb99ca2ec1a.js` (439 KB). This proves a web bundle only. |
| Serve exported files on `127.0.0.1:8082` using `.venv\Scripts\python.exe -m http.server` | **PASS** | `GET /` returned HTTP 200. Server is loopback only. |
| Local API smoke using `mobile-api-smoke.mjs` | **PARTIAL** | `/api/v1/health` returned 200. PAIR01 and PAIR02 each created a distinct session; both state requests returned 200, both report requests returned 202, and both session revocations returned 200. `/api/v1/demo/manifest` returned 404 for both drivers. Redacted record: [mobile-api-results.json](mobile-api-results.json). |
| 10 mobile viewport screenshots, including pair and report | **NOT RUN** | The CUA browser host reported unavailable. Local Edge and Brave CDP attempts lost or crashed their page targets before app interaction. No screenshots were produced. Attempt details: [mobile-capture-failure.txt](mobile-capture-failure.txt) and [mobile-capture-attempt.txt](mobile-capture-attempt.txt); capture script: [capture-mobile.mjs](capture-mobile.mjs). |

## API findings

The successful HTTP requests used the local FastAPI service at `127.0.0.1:8000`; they were not mocked. Pairing produced distinct identities (Ramesh Kumar / `driver_1` and Suresh Patel / `driver_2`). Each report request returned HTTP 202 with decision `KEEP`; no dispatcher approval or route publication was performed. Both short-lived bearer sessions were revoked, and raw tokens were held only in process memory. The one-time local fixture codes were consumed by this smoke run.

The mobile app refreshes state and manifest together. Since manifest returned 404 for both real sessions, route data could not be verified end to end through the mobile UI. This finding was sent to Luna 06 (mobile UI), Luna 07 (network client), Luna 08 (session), and the root coordinator.

## Evidence limits

- Expo export and HTTP smoke are not Android/iOS runtime, simulator, or physical-device evidence.
- Browser screenshots and visual inspection were not completed; there are no image artifacts in `mobile-screens/`.
- The browser failure is tooling/runtime evidence, not proof that the exported web app itself crashed.
- `mobile-api-smoke.mjs` consumed the seeded one-time fixture codes and submitted two moderate-severity `KEEP` report events; it revoked both sessions and did not approve or publish route changes.
- No native packages or global tools were installed. The export server uses the repository's isolated `.venv` Python executable and binds only to loopback.
