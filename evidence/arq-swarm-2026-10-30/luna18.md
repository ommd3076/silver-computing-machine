# Luna 18: Demo API boundary audit

## Scope

Owned `backend/demo/api.py` and `tests/test_swarm_demo_api.py`. The router creates one-time pairing sessions, derives driver identity only from the bearer session, scopes state/manifests/reports/acknowledgements to that identity, and gates dispatcher actions using either a configured dispatcher/admin token or the ASGI peer's loopback address in local mode.

## Failure hypotheses and edits

| Hypothesis | Evidence | Edit | Retest |
|---|---|---|---|
| A malformed report such as a numeric `note` can escape route validation and cause an uncaught `TypeError`; whitespace-only event IDs are accepted. | The previous route checked only the event ID's type/length and delegated note validation; service computes `len(note)`. | Require nonblank event ID, positive integer non-bool base version, known severity, string note up to 240 chars, and exact pairing payload keys before service invocation. | `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_demo_api.py -q -p no:cacheprovider --basetemp=.runtime/test-sw-demo-api-luna18c` — **3 passed**. |
| Unrecognized `ValueError` text from services could leak internal details as response error codes. | Report, acknowledgement, and approval handlers previously copied `str(exc)` into their error code. | Whitelist documented service codes and map all unexpected values to stable generic codes. Added sentinel exception-redaction coverage. | Same command — **3 passed**; response bodies did not contain `private-service-detail`. |
| An apparent local dispatcher authorization failure could be caused by the test peer defaulting to `testclient`, not a loopback address. | Initial test run returned `dispatcher_required` on approval because TestClient's default peer is not loopback. | Set an explicit loopback peer for the local approval error-redaction test; separately test a non-loopback peer is denied. | Same command — **3 passed**; loopback allowed, `192.0.2.10` denied. |

## Executed checks

| Command | Result | Notes |
|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_demo_api.py -q -p no:cacheprovider --basetemp=.runtime/test-sw-demo-api-luna18c` | **3 passed** | API input, driver scoping, peer loopback, token-role gating, and exception redaction. One upstream Starlette deprecation warning. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_demo_api.py tests/test_arq_demo_driver_contract.py -q --basetemp=.runtime/test-sw-demo-api-luna18` | **3 passed, 1 failed** | Existing `tests/test_arq_demo_driver_contract.py` expected an outdated validation `scope` string; live service returned `catalog vehicle/ordered-stop/geometry/distance and source-recomputed time proxy only`. No out-of-scope files changed. |

The first attempted pytest setup used shared `.runtime/pytest-tmp-codex` and failed cleanup with Windows `WinError 5`; rerunning with a unique `--basetemp` avoided that contention. This is local in-process API evidence only, not a device, deployment, or live-fleet integration check. No real credentials, external services, or commits were used.
