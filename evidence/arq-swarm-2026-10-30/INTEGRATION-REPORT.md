# arQ UI swarm integration report

Batch start: 2026-10-29 22:14:57 UTC / 2026-10-30 03:44:57 IST. Owner's final 24-minute UI instruction: 22:26:57 UTC, deadline 22:50:57 UTC. Usage limits unavailable; owner explicitly waived that check. Thirty named Luna agents actually launched, with non-overlapping ownership; individual execution notes are in this directory. No commits, deployment, paid jobs, model training, checkpoint changes, or alpha changes were authorized or performed in this batch.

## Integrated source

- Active nested repository: `nmit-frontend`, branch `master`; root branch `collab/person2`, initial HEAD `2c7a4fb`. Both were already dirty. Previous reconstruction and archives were preserved; baseline copies already exist in `evidence/arq-build-2026-10-30/baseline`.
- Web entry: `nmit-frontend/frontend/src/App.tsx`, ten connected hash routes: command, map, dispatch, compare, fleet, driver, orders, analytics, diagnostics, recovery. Four former placeholder routes are now real components. Shared shell, primitives, CSS and interaction layer are in `src/features/operations` and `src/App.css`.
- Expo React mobile entry: `nmit-frontend/apps/driver-mobile/App.tsx`, ten reachable views: pair, home, map, navigation, stops, detail, report, replan, updated, settings. Platform map components use actual route geometry; no GPS or turn-by-turn claim.
- Driver API: `backend/demo/api.py`, coordinator `service.py`, SQLite `store.py`. Initial manifests, report payload validation, proposal idempotency, atomic publication, independent catalog checks, exact route-version acknowledgement and two-driver isolation were repaired.
- Shared dispatcher token remains in module memory only; both web API clients now share it. Mobile uses scoped bearer sessions; native session persistence remains ephemeral without a secure-store dependency.

## Executed checks

- Web production build: PASS (`web-build-final.txt`), with large JS chunk advisory.
- Web Vitest: PASS, 11 files / 62 tests (`web-tests-final.txt`). API boundaries are mocked in component/journey tests; these are distinct from live HTTP/browser checks.
- Backend integrated suite: PASS, 23 tests across swarm API/service/store/security/E2E/initial-manifest and existing driver/web truth regressions. Follow-up initial-manifest/driver suite after ordered-stop correction: PASS, 3 tests.
- Expo typecheck: PASS after integration.
- Expo Android export: PASS, 694 modules, Hermes bundle 1.7 MB (`expo-android-export.txt`). This proves bundling, not APK installation or native runtime.
- Web browser smoke: 10 views at desktop 1366x768 and mobile 390x844, 22 screenshots. Map fallback route selection explicitly exercised. See Luna23 evidence and nested screenshots directory.
- Live exact solver: backend returned feasible routes and independent validator valid, objective 10 proxy units; see Luna01 note. This planning result is not a published phone manifest.
- Mobile live browser testing and report/approval/ack acceptance: see final Luna29/Luna23 notes; final outcomes must be read there, not inferred from earlier compile success.

## Substantive refinements

1. Failure: first congestion report raised SQLite column-count error. Change: explicit proposal columns plus additive saved-manifest migration, atomic cross-instance transactions. Retest: store tests and real in-process two-driver E2E pass.
2. Failure: new paired drivers had state but no initial manifest (HTTP404), breaking mobile refresh. Change: persist initial manifest from authoritative state without overwriting existing versions. Retest: fresh-DB dual pairing and state/manifest consistency pass.
3. Failure: editable travel matrix silently reverted values; stale responses could overwrite new state. Change: normalize from patched matrix and generation/abort guards. Retest: request payload test plus actual backend exact job pass.
4. Failure: remote map style/worker failures left blank maps or crashed mobile runtime. Change: inline base style, watchdog/coordinate fallback and platform-specific imports/assets. Retest: web geometry/selection browser check passes; mobile final outcome recorded by Luna29.
5. Failure: dispatcher token configured only one client. Change: shared memory authorization/redaction module. Retest: 21 focused client tests including cross-client authorization pass.

## Runtime and startup

Current web: http://127.0.0.1:5173 ; mobile web export: http://127.0.0.1:8082 ; current FastAPI: http://127.0.0.1:8001 . The prior process on 8000 could not be stopped (Windows access denied), so it was left untouched. Vite proxy targets 8001 with ARQ_API_TARGET override. Current separate demo DB: `.runtime/arq-swarm-live-20261030.sqlite3`; jobs DB: `.runtime/arq-swarm-jobs-20261030.sqlite3`. Existing data was not deleted or reset. See `docs/ARQ-UI-STARTUP.md` and `tools/start-arq-ui.ps1`.

## Evidence boundaries and open acceptance

Physical Phone A/B, Android emulator, APK install, real LAN/firewall reachability, native MapLibre dev-client execution and successful external tile delivery are not established by localhost browser or exports. Native MapLibre requires a development build; Expo Go alone does not contain that native module. Operational whole-delivery ETA remains GBDT alpha=0. Retrospective four-qubit results remain research evidence, not validated road-leg travel times. The tiny scenario planner and catalog recovery demo are separate inputs; solving arbitrary scenarios does not publish them into the seeded driver catalog. Catalog capacity/windows/financial/live-traffic inputs remain unavailable and are labeled. No quantum superiority, QCloud/QPU or real GPS claim is made.

UI Skills MCP list/get worked and relevant instructions were reviewed. RareUI MCP was absent from callable tools. Existing Recharts/EvilCharts-adapted components were retained. No claim that 30 unrelated skills were meaningfully applied is made; see Luna27 actual tool ledger.

## Final browser workflow update

The coordinator's `rootfull-flow.mjs` rendered mobile home/active-map/navigation/stops/report/replanning screens and submitted a real heavy congestion report. It exposed a further live client contract mismatch: persisted proposal owner fields were nested, while the client required top-level fields. The client now normalizes those fields and has a regression test. Final web suite: 62 passed; production build passed. Luna23 then reviewed actual geometry/28-to-24-minute metrics, explicitly confirmed publication through the web UI, and verified route version 2/revision 2. Post-publication mobile acknowledgement requires separate evidence; it is not inferred from publication.

Expo Go requested by owner: compatibility entry now defaults to a coordinate-backed stop overview because native MapLibre is not bundled in Expo Go. Set EXPO_PUBLIC_NATIVE_MAPS=1 only for a development build that includes the native module. Expo Metro is running on 8081, QR artifact `expo-go-qr.png` encodes exp://172.80.6.68:8081. Backend phone gateway launch was rejected by automatic approval review (LAN authentication exposure); owner approval requested and not assumed. The phone cannot reach the loopback backend until a specifically approved connection is configured. Default browser launch via Start-Process failed Windows access denied; local preview services remain available via links.
