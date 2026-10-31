# Luna22 security QA evidence

## Scope

Reviewed `backend/auth.py`, `backend/api.py`, `backend/demo/auth.py`,
`backend/demo/api.py`, the ETA approval API/controller boundary, and frontend
session/request handling. No implementation files were changed. Tests use
sentinel-only credentials; no real secrets were read or printed.

The project React frontend (`frontend/src`) has no bearer-session integration:
its API wrapper sends no `Authorization` header and its `approvalsStore` is a
local UI record. The separate mobile client (`nmit-frontend/apps/driver-mobile`)
does send a bearer token and stores its web session in `sessionStorage`; native
storage is ephemeral because there is no secure-storage dependency. These are
distinct product surfaces, not evidence that the React app has authenticated
server approval.

## Executed checks

Command:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_swarm_security.py -q -p no:cacheprovider --basetemp=evidence/arq-swarm-2026-10-30/pytest-tmp2
```

Result: **2 passed**, with one existing Starlette/httpx deprecation warning.
The checks use real local FastAPI `TestClient` requests and temporary SQLite
databases.

- Driver 2 cannot use a query parameter to impersonate driver 1, read driver 1's
  proposal, approve it, or acknowledge driver 1's manifest.
- A configured dispatcher can approve a proposal; only the owning driver's
  manifest advances.
- A researcher cannot turn a forged request-body `actor` into ETA approval
  authority.
- Missing demo IDs and malformed ETA IDs return generic errors without
  reflecting the identifiers. Sentinel credentials and identifiers are absent
  from tested response bodies and captured logs.

## Failed attempt / environment note

The first invocation used the repository's configured pytest basetemp and
failed in fixture setup/cleanup with Windows `WinError 5` for
`.runtime/pytest-tmp-codex`; no test ran in that attempt. Redirecting pytest's
basetemp into the assigned evidence directory and disabling the cache provider
made the focused run pass.

## Findings and limits

No concrete cross-driver authorization, approval spoofing, invalid-ID reflection,
or tested secret-leak defect was reproduced in the inspected paths. This is a
bounded local check, not a production security review. The main UI's local
approval annotation must not be interpreted as authenticated server approval;
the separate mobile session implementation is the only inspected frontend
surface that currently carries a driver bearer token.
