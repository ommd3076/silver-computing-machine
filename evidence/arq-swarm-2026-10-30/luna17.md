# Luna 17 — operations shell and primitives

Scope: `frontend/src/features/operations/AppShell.tsx` and `primitives.tsx` only. Existing changes in other files were left untouched.

## Verified changes

- The shell still exposes the ten existing views (`command`, `map`, `dispatch`, `compare`, `fleet`, `driver`, `orders`, `analytics`, `diagnostics`, `recovery`) and keeps the existing `AppShell` props contract.
- Mobile navigation now moves focus into the open navigation, returns focus to the menu control on close, and is inert while closed so offscreen links cannot be tabbed to. The active view retains `aria-current="page"`.
- Health has a named status announcement; refresh reflects busy state; shared API errors announce as alerts and offer a disabled-while-busy retry.
- Optional API token controls now have dialog semantics and a labelled password input. The token remains only in the existing in-memory API configuration; the input state is cleared on apply, close, and Escape. Wording does not imply user authentication.
- `Panel` labels section landmarks when titled (and permits an explicit label); untitled panels no longer create unnamed section landmarks. Empty and error states expose status/alert semantics and decorative icons are hidden from assistive technology. Empty states accept an optional action.

## Refinement record

1. Failure hypothesis: the translated mobile rail remains keyboard reachable while visually closed. Edit: set `inert` for the closed mobile rail and manage focus on open/close. Check: targeted Oxlint passed after shell changes.
2. Failure hypothesis: dismissing API access can leave typed credentials in React input state, and the control can be mistaken for a user login. Edit: labelled non-modal API-access dialog, focus handling, memory-only description, and clear input on dismissal/apply. Check: targeted Oxlint passed after shell changes.
3. Failure hypothesis: generic empty panels create unnamed landmarks and state changes are not consistently announced. Edit: labelled titled panels, non-landmark untitled panels, status/alert state semantics, and optional empty-state action. Check: final targeted Oxlint passed.

## Executed checks and limits

- `npm.cmd exec oxlint -- src/features/operations/AppShell.tsx src/features/operations/primitives.tsx` from `nmit-frontend/frontend`: PASS, exit 0, no diagnostics.
- `npm.cmd run build` from `nmit-frontend/frontend`: NOT PASS. `tsc -b` stops on existing errors outside this assignment: `src/api/client.ts:98,109` (`abortError` is absent from the inferred object type) and `src/features/operations/DiagnosticsView.test.tsx:38` (fixture status inferred as `string`, not `JobStatus`). No build or browser success is claimed.
- No tests, browser checks, or CSS edits were made.
