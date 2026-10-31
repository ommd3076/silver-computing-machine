# Luna 26 — initial authoritative manifest

## Change

`DemoStore.init_driver_state_if_missing` now writes a durable manifest snapshot for each initialized driver when none exists. It derives the snapshot from the actual persisted `driver_state` row, so existing databases with advanced route/revision state are backfilled accurately instead of assuming version 1. Existing manifest history is left intact. The demo manifest endpoint was already declared in `backend/demo/api.py`; the observed live 404 therefore also requires restarting the API process so it loads the current router.

Added `tests/test_swarm_initial_manifest.py`: on a fresh SQLite DB, pair both driver fixtures, fetch state and manifest immediately, and verify driver/vehicle/route identity and matching route/manifest versions.

## Executed checks

- `.venv\\Scripts\\python.exe -m pytest -q tests/test_swarm_initial_manifest.py tests/test_swarm_demo_api.py tests/test_swarm_end_to_end.py` — could not initialize pytest temporary directories because the configured shared `.runtime\\pytest-tmp-codex` path returned Windows access denied.
- `.venv\\Scripts\\python.exe -m pytest -q --basetemp=.runtime/pytest-luna26-run1 -o cache_dir=.runtime/pytest-luna26-cache tests/test_swarm_initial_manifest.py tests/test_swarm_demo_api.py tests/test_swarm_end_to_end.py` — **5 passed**, one existing Starlette/httpx deprecation warning.

## Handoff

Restart the localhost API, then repeat the mobile smoke against `/api/v1/demo/manifest` for each newly paired session. This code change cannot itself prove the already-running process has reloaded; no live HTTP rerun was performed here. No commit made.
