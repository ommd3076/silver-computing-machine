# Luna 19 — backend demo service

Date: 2026-10-30 (Asia/Kolkata)

## Scope and changes

- Updated `backend/demo/service.py` and added `tests/test_swarm_demo_service.py`.
- Planning requests now validate request IDs and route versions, reject stale versions, prevent an idempotency key from crossing driver scope, and use the proposal-only evaluator instead of the removed auto-publishing method.
- Congestion events validate identifiers and payloads before mutation, replay same-key requests before checking the now-advanced route version, reject conflicting reuse, and return published status plus the committed manifest after approval.
- Proposal validation independently recomputes the current and proposed catalog time proxy, route geometry/distance, claimed time saved, proposal/record consistency, and the minimum switch threshold. It explicitly marks capacity, contractual windows, financial objective, and live conditions unavailable because those source fields do not exist in this demo catalog.
- Retrying a published approval now delegates to the store's idempotent publication path so it returns that approval's committed manifest even after a newer version exists.

## Refinement cycles

| Cycle | Failure hypothesis and evidence | Material edit | Retest and result | Remaining concern |
|---|---|---|---|---|
| 1 | Planning could call the removed `_evaluate_and_decide` method and did not validate the requested route version or driver scope. Targeted test initially reproduced `AttributeError`; test also checks stale version and cross-driver request ID. | Use the proposal evaluator, enforce route version/request ID validation, and reject an existing job owned by another driver. | `.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider --basetemp=.runtime\\pytest-luna19 tests/test_swarm_demo_service.py -q` — after the edit, 4 passed. | Store job IDs remain globally unique by request ID; full idempotent replay after route advancement is not implemented for planning jobs. |
| 2 | A retry of a congestion event after approval could fail `stale_version` before checking the persisted idempotency key. | Check the stored event hash before stale-version rejection; same payload replays and conflicting payload fails. | Included in the final focused run — passed. | Persistence ordering across report, job, and proposal creation is not one SQLite transaction; see store/API follow-up. |
| 3 | A candidate's proposed duration alone was checked; current duration, claimed time saved, threshold, and finance/capacity/window scope were not fully represented. | Recompute both catalog times and switch threshold, compare claimed savings, harden malformed numeric handling, and state unavailable business metrics explicitly. | Tampered proposed duration test fails validation; valid 240-second time-proxy improvement passes. Final focused run — passed. | These checks prove catalog proxy consistency, not operational feasibility or financial benefit. |
| 4 | Repeating approval after a later publication could return the driver's latest manifest instead of the original proposal's committed version; replaying its congestion event could also still report `published: false`. | Delegate published retries to `DemoStore.publish_proposal`, and enrich a replayed event from its durable proposal state. | Regression confirms the event replay reports published with the committed version-2 manifest and approval retry still returns that version after driver state advances to version 3. Final focused run — passed. | Store migration/version behavior remains owned by the store agent. |

## Executed checks

Command:

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=.runtime\pytest-luna19 tests/test_swarm_demo_service.py tests/test_arq_demo_driver_contract.py -q
```

Outcome: **7 passed** in 1.92 seconds. This included the authenticated two-driver proposal, dispatcher publication, acknowledgement, idempotent report replay, and process/service re-creation flow in `tests/test_arq_demo_driver_contract.py`. One Starlette `httpx` deprecation warning was emitted. No network or cloud integration was exercised.

The initial test invocation had one test assertion expecting `stale_version` for version 0; input validation correctly returns `invalid_version`. The test was corrected to use a positive stale version (2). That run then exposed the removed `_evaluate_and_decide` call, which was fixed and retested.

## Limits

No financial objective is computed for the phone demo: candidate routes have no financial rates, currency, contract penalty, capacity, or contractual-window inputs. API validation describes an independently recomputed catalog time proxy and does not establish real-world route feasibility. Store migration changes and concurrent API/security QA were performed by other agents and are not attributed to this service work.
