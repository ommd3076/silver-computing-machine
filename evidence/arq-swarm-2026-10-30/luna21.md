# Luna 21: two-driver API contract QA

## Scope

Added `tests/test_swarm_end_to_end.py`. It runs the actual FastAPI demo router, auth middleware, pairing/session manager, coordinator service, and SQLite store in-process. It uses a temporary SQLite database and the repository `.venv`; there are no fake service/store mocks and no live external calls.

The scenario pairs both seeded drivers, checks their distinct vehicle/route state and manifests, submits a heavy congestion report, verifies report replay idempotence and changed-payload conflict, and proves the report does not publish by itself. Driver credentials and researcher credentials cannot approve; the dispatcher can. The test checks route validation and approval idempotence, proves driver 1's acknowledgement/update does not mutate driver 2's state, rejects driver 2 attempting driver 1's version, then acknowledges driver 2's own version. Finally it rebuilds the app/service over the same SQLite file and checks sessions, routes, manifests, acknowledgement state, and dispatcher proposal state persisted.

## Executed results

| Command | Result | Notes |
|---|---|---|
| `.venv\\Scripts\\python.exe -m pytest tests/test_arq_demo_driver_contract.py -q --basetemp=.runtime\\pytest-luna21-baseline` | **2 passed** | Initial baseline before concurrent backend edits. Starlette deprecation and pytest cache permission warnings. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py -q --basetemp=.runtime\\pytest-luna21-e2e` | **FAIL: implementation defect found** | First congestion report raised `sqlite3.OperationalError`: `demo_proposals` had 12 columns after migration but store inserted 11 positional values. Reported to root and luna20. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py -q --basetemp=.runtime\\pytest-luna21-e2e-r1` | **FAIL: test expectation corrected** | luna20 fixed the store insert to name the original 11 columns; then test exposed that `/manifest` returns the driver's initial synthesized version-1 manifest. Updated the test to assert unchanged initial manifest instead of 404. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py -q --basetemp=.runtime\\pytest-luna21-e2e-r2` | **FAIL: test expectation corrected** | Token middleware rejects driver bearer on dispatcher route as 401 before endpoint; adjusted expectation from 403 to observed 401. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py -q --basetemp=.runtime\\pytest-luna21-e2e-r3` | **1 passed** | Full new two-driver pairing/report/approval/ack/restart scenario passes. Starlette deprecation and pytest cache permission warnings. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py -q --basetemp=.runtime\\pytest-luna21-final` | **1 passed** | Final rerun after evidence write; same two non-fatal warnings. |
| `.venv\\Scripts\\python.exe -m pytest tests/test_swarm_end_to_end.py tests/test_arq_demo_driver_contract.py -q --basetemp=.runtime\\pytest-luna21-contracts` | **2 passed, 1 failed** | New test passes. Existing test's validation scope prefix is stale: it expects `catalog vehicle/ordered-stop coverage/geometry/duration/distance only`; service returns `catalog vehicle/ordered-stop/geometry/distance and source-recomputed time proxy only`. Reported to luna19 and root; no edit made outside assigned test file. |

## Boundaries

- The passing test demonstrates local in-process API and SQLite behavior only; it is not a device, network, deployment, or live-fleet integration check.
- Test tokens are fixed non-secret sentinels. No real credentials or external services were used.
- The existing contract-test wording mismatch remains for its owner to resolve. The new owned test passes independently against the current implementation.
- No commit was made.
