# Luna 14 — Command map composition

## Scope
- Edited `nmit-frontend/frontend/src/features/operations/CommandMapViews.tsx` only for implementation.
- The map keeps the existing `RouteMap` API and callbacks; vehicle rows and stop rows still select the corresponding vehicle and stop.
- The command overview now summarizes backend catalog vehicle state, pending dispatcher proposals, and persistent audit records. Pending proposals are presented as pending incident proposals because the dispatcher has proposal records and no separate incident list in this view.
- Recent activity is sourced from `operations.audits`; summaries use available severity/decision fields and otherwise show the recorded principal. Missing times are explicitly labeled.
- No GPS, live movement, ETA, service window, demand, risk, or fabricated incidents/KPIs were added. The existing Preview source badge remains.

## Files and coordination
- Component: `nmit-frontend/frontend/src/features/operations/CommandMapViews.tsx`
- Requested styling coordination: parent agent owns `App.css`; asked it to style `.arq-command-activity`, `.arq-command-summary`, `.arq-activity-list`, `.arq-activity-icon`, `.arq-activity-empty` and make the map dominant responsively.
- Other checkout changes were present and left untouched.

## Verification
- Source-inspected dispatcher contracts in `frontend/src/api/dispatch.ts`, `RecoveryView.tsx`, and `backend/demo/store.py` to confirm proposal and audit fields.
- No tests or typecheck were run in this subtask.

## Remaining concerns
- Visual quality depends on the parent adding CSS for the new activity classes and checking narrow layouts.
- No independent incident endpoint exists in the current `DispatcherState`; this view therefore reports only backend route proposals awaiting review.
