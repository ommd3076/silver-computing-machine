# Luna20 — demo SQLite publication and replay

Date: 2026-10-30 (Asia/Kolkata)

## Scope and result

Assigned scope: `backend/demo/store.py` and `tests/test_swarm_demo_store.py`. No commits made. The shared checkout also contains concurrent backend work; this note describes only the store guarantees and tests added in this task.

The store now takes SQLite's `BEGIN IMMEDIATE` writer lock before publication and report idempotency checks. Proposal publication increments from the maximum committed vehicle manifest version and persists the exact returned manifest on the proposal row. Manifest lookup filters by both vehicle and driver. Congestion event retries preserve the original report and reject conflicting payloads. SQLite uses WAL plus `synchronous=FULL`; schema startup adds the new nullable publication-result column without replacing existing proposal rows.

## Refinement cycles

| Cycle | Failure hypothesis | Material edit | Retest and evidence | Remaining concern |
|---|---|---|---|---|
| 1 | Two `DemoStore` instances have distinct Python locks, so concurrent publishers can both read the same route version and publish overlapping versions. | Acquire `BEGIN IMMEDIATE` before reading publication state; allocate `max(driver revision, vehicle manifest max) + 1`. | `.venv\\Scripts\\python.exe -m pytest -q -o addopts= --basetemp=.runtime/luna20-testtmp tests/test_swarm_demo_store.py` — PASS, including the two-instance concurrent publisher test; route advances once. | SQLite locking is process-local to a shared DB file; network filesystems and multi-host deployments were not tested. |
| 2 | A repeated approval can return a later manifest for the same driver rather than the exact result of the original proposal; vehicle-only lookup can also expose a different driver's manifest. | Add nullable `published_manifest_json` migration, persist the committed output, and filter manifest queries by driver. | Same command — PASS; restart retry returns proposal 1's version 2 after proposal 2 commits version 3, and manifests remain driver-scoped. | Existing already-published rows have no exact-result snapshot; the compatibility path returns the latest saved manifest belonging to that driver. |
| 3 | `INSERT OR REPLACE` makes a report retry rewrite creation time/content, and check-then-insert can race across store instances; adding schema by destructive replacement risks losing existing proposal rows. | Make report compare/insert transactional with `BEGIN IMMEDIATE`; same-payload retry is a no-op and conflicting reuse raises `report_conflict`. Add a legacy-schema migration preservation test. | Same command — PASS: 4 tests passed, including unchanged retry rows, conflict preservation, shared-vehicle isolation, restart recovery, and existing-row migration. | Concurrent report writers were protected by the same SQLite writer lock but not independently stress-looped. |

## Checks actually run

- `.venv\\Scripts\\python.exe -m pytest -q tests/test_swarm_demo_store.py` — did not reach tests: pytest's configured `.runtime/pytest-tmp-codex` cleanup failed with Windows `PermissionError` because that path was unavailable/occupied.
- `.venv\\Scripts\\python.exe -m pytest -q -o addopts= --basetemp=C:\\tmp\\nmit-sw-store tests/test_swarm_demo_store.py` — did not reach tests: `C:\\tmp` was not writable in this environment.
- `.venv\\Scripts\\python.exe -m pytest -q -o addopts= --basetemp=.runtime/luna20-testtmp tests/test_swarm_demo_store.py` — PASS, 4 passed. Pytest emitted one warning because the existing `.pytest_cache` path was not writable; test execution and assertions completed successfully.

`tests/test_swarm_demo_store.py` covers concurrent publishers using independent store instances, monotonic shared-vehicle versioning, exact proposal replay after later publication and restart, per-driver manifest isolation on a shared vehicle, report idempotency/conflict behavior, event owner/hash conflict checks, and preservation of rows through an additive schema migration.
