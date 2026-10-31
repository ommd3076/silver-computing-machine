# Luna 16 — RecoveryView

Scope: `nmit-frontend/frontend/src/features/operations/RecoveryView.tsx` only.

## Implemented

- Proposal cards now show the backend candidate validation result and returned base/candidate route versions when present. Missing validation and version data remain explicitly unavailable.
- Approval requires the operator to open the review dialog and click **Confirm & publish revision**. The API call is made only for a still-pending proposal; success notice uses the returned manifest vehicle and route version.
- Recovery timeline uses persisted API audit events and displays terminal recovery job failures only when job metadata explicitly identifies a recovery operation. No client-created event or savings figure is shown.
- Added a sentence-case source note identifying dispatcher, manifest, recovery audit, and persisted job APIs.

## Evidence

- Read frontend endpoint contract: `/api/v1/recovery/replan` returns `success`, `audit_log`, `exposure_delta_inr`, `reordered_count`, and optional `updated_run`; dispatcher approval is `/api/v1/demo/proposals/{id}/approve` and returns a driver state.
- `npm run build` was blocked by PowerShell execution policy. `npm.cmd run build` then reached TypeScript and failed on pre-existing errors in `src/api/client.ts` lines 98, 109, 188 and `src/features/operations/DiagnosticsView.test.tsx` line 38. The initial run also found this file's `Row` inference issue; fixed it, and the subsequent build output contained no RecoveryView diagnostic.
- No tests or live API action were run. No backend publication is claimed.

## Open limitation

Recovery failure jobs appear only if persisted job metadata marks `operation`, `kind`, or `workflow` as `recovery` / `recovery_replan`; absent such metadata, the screen does not guess that an unrelated failed solver job was a recovery attempt. Audit events are shown when their returned event type contains `recovery` or `replan`.
