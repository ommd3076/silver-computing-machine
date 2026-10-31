# Luna07 mobile API client evidence

## Scope

Changed only `nmit-frontend/apps/driver-mobile/src/api/client.ts` for the assigned client work. Existing `driverApi` methods and exported payload/result types are unchanged. Backend route definitions were inspected in `backend/demo/api.py`: session create/revoke, state, manifest, report (202), and acknowledgement are real routes. Report deduplication uses `event_id` (`backend/demo/service.py`, `backend/demo/store.py`).

## Changes

- Kept `EXPO_PUBLIC_API_URL` as the override. Default is Android emulator `http://10.0.2.2:8000`; iOS/web local development uses `http://127.0.0.1:8000`. Invalid origins fail with a stable `invalid_api_url` error and tell physical-phone users to configure the development computer's LAN address.
- Bound each request to 10 seconds and preserved caller abort signals. Caller cancellation returns `aborted`; deadline expiration returns `timeout`.
- Decode backend `{detail:{error:{code,message}}}` errors, retain HTTP fallback codes, and report unreadable successful JSON as `invalid_response`.
- Use CORS mode in web and omit cookies on all requests. Bearer auth remains attached only to the existing authenticated driver calls.
- Add an `X-Request-ID` trace header and expose the ID on `ApiError`; reports reuse their backend-deduplicated `event_id` so retries retain the same identifier.

## Executed checks

- `npm.cmd run typecheck` in `nmit-frontend/apps/driver-mobile`: exit 0; output:

  ```text
  > driver-mobile@1.0.0 typecheck
  > tsc --noEmit
  ```

- Node source hygiene check on `apps/driver-mobile/src/api/client.ts`: exit 0; output `client.ts: no trailing whitespace; final newline present`.
- A combined `npm.cmd run typecheck; git diff --check` also ran. The typecheck completed without diagnostics, but the combined command exited 1 because the repository-wide diff check reported an unrelated existing/new `apps/driver-mobile/App.tsx:221: new blank line at EOF.` Other worktree paths were already modified/untracked; they were not edited as part of this task.
- No live backend, browser CORS, Expo emulator, or physical-device request was executed. Typecheck is not integration or device evidence.

## Limitations

A physical phone must set `EXPO_PUBLIC_API_URL` to the development computer's reachable LAN origin, and the backend must bind to a reachable interface (the local Makefile's `dev-api` uses `--host 0.0.0.0`). Automatic discovery is intentionally not claimed. `X-Request-ID` is diagnostic metadata; backend request-ID logging was not verified. Client abort does not establish server-side cancellation.

