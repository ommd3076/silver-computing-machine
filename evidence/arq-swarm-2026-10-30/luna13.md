# Luna 13 — API client audit

Date: 2026-10-30 (Asia/Calcutta)

## Scope and inspected contract

- Changed only `nmit-frontend/frontend/src/api/client.ts` and `nmit-frontend/frontend/src/test/apiClient.test.ts`.
- Source inspected: `backend/api.py` routes `/api/v1/solve`, `/api/v1/jobs`, `/api/v1/jobs/{job_id}`, and `/api/v1/jobs/{job_id}/cancel`; `backend/jobs.py` persisted job lifecycle; `nmit-frontend/frontend/src/api/ENDPOINTS.md`; `docs/API-RUNTIME.md`.
- The client talks to the real backend route names. `/solve` accepts a scenario ID / engine request, returns a job ID, active status, submission time, and `/api/v1/jobs/{id}` poll path. Job polling and cancellation return persisted job records. Cancellation is reported true only when the returned server record is `cancelled`.
- API auth is disabled by default in this local prototype. At initial handoff, the dispatcher configured its optional token only in `dispatch.ts`, leaving the main API client unauthenticated. A follow-up fix now shares one in-memory token across both clients and attaches Bearer authorization when configured. No credentials are persisted; no authenticated live call was attempted.

## Changes

- Public methods now accept optional `AbortSignal` parameters while preserving existing call signatures and result types. The client composes caller cancellation with its request timeout and keeps the deadline active while reading the response body.
- Timeout (`timeout`), caller cancellation (`request_aborted`), and connectivity failure (`network_error`) are distinct stable errors. Caller cancellation during a health read is propagated; connectivity/timeout still produce the documented offline health state.
- Submission records require a non-empty job ID, known active status, valid `submitted_at`, and the expected relative polling path. Persisted job records require non-empty IDs, known status, and valid `submitted_at`; individual polling/cancel responses must match the requested ID. Cancellation remains server-confirmed.

## Refinement cycles and executed evidence

| Cycle | Failure hypothesis and edit | Retest evidence | Remaining concern |
| --- | --- | --- | --- |
| 1 | Caller aborts were inaccessible through public methods and fetch failures collapsed abort/timeout into network failure. Added optional signals, composed abort controller, and separate stable error codes. | First focused run: 10 passed, 1 failed. Abort/timeout checks passed; the newly strict job mapping exposed `Array.map` passing its numeric index as the expected ID. | No live backend request was performed. |
| 2 | Strict record identity validation would reject every job list item if the array index leaked into the identity check. Changed to an explicit one-argument mapper. | `npm.cmd test -- --run src/test/apiClient.test.ts`: 11/11 passed. | The suite uses mocked `fetch`; it is client contract coverage, not integration evidence. |
| 3 | A submission could be accepted with an absent timestamp despite the backend contract requiring one; cancellation semantics also needed proof for both server outcomes. Added timestamp validation and positive/negative server-confirmed cancellation coverage. | `npm.cmd test -- --run src/test/apiClient.test.ts`: 12/12 passed. `npm.cmd run build`: passed (`tsc -b` and Vite production build); Vite emitted the existing large-chunk advisory. | A PowerShell read-only attempt to `http://127.0.0.1:8000/api/v1/health` returned `NotSupportedException`; no authenticated or localhost integration result is claimed. |

## Evidence boundary

The tests use mocked fetch responses and abort-aware test doubles; they verify client behavior only. Backend route behavior was source-inspected. No real solver job was submitted, polled, cancelled, or recovered in this task. No live API integration, authorization behavior, or solver execution is claimed.

## Follow-up: shared token-mode fix

The parent later identified that the Operations access form called `configureDispatcherToken`, while health, runs, and solver jobs use the separate main `apiClient`. Added `frontend/src/api/auth.ts` as a shared in-memory getter/setter and recursive redactor; the main client now sends Bearer authorization and redacts token echoes from backend errors. `dispatch.ts` imports the same store and re-exports `configureDispatcherToken` for backwards compatibility. No local/session storage or files are used for token material.

- `npm.cmd test -- --run src/test/apiClient.test.ts src/api/dispatch.test.ts`: **21/21 passed**, including dispatcher-configured token propagation to the main health client, both clients' Authorization headers, and error redaction.
- `npm.cmd run build`: passed; Vite reported its large-chunk advisory.
- Tests use a non-secret sentinel only. A real authenticated API call was not made.
