# Luna 03 — Analytics view

## Deliverable

- Implemented `nmit-frontend/frontend/src/features/operations/AnalyticsView.tsx` with the interface `AnalyticsView({ operations }: { operations: ReturnType<typeof useOperations> })`.
- Added focused coverage in `nmit-frontend/frontend/src/test/AnalyticsView.test.tsx`.
- The coordinator still needs to render the component from `App.tsx`; that integration was outside this assignment's file ownership.

## Verified data behavior

- Plan exposure uses `PlanRun.total_sla_exposure_inr`; objective cost is charted only if its string explicitly includes `₹` or `INR` and has a parseable numeric amount.
- Calibration, Brier score, benchmark gap, and solver elapsed seconds come from `IntelligenceEvidence` and `SolverJob` values returned by the operations hook. No calibration or benchmark results are derived from route predictions.
- Empty plan, cost, benchmark, and model evidence states are explicit. No fixture values are inserted into the view.
- Money labels use INR/₹ and retain each plan's `assumed_rate_label`; runtime is in seconds and benchmark gap is in percent.

## Refinement cycles

| Cycle | Failure hypothesis | Material change | Retest evidence | Remaining concern |
|---|---|---|---|---|
| A | Putting objective cost and SLA exposure on one axis would imply they are interchangeable. | Separated exposure and objective cost into independently labeled charts, both restricted to INR. | Focused component test passes with actual typed records and checks chart labels/units. | Objective costs without explicit rupee denomination remain unavailable. |
| B | Parsing an unlabelled numeric objective-cost string as rupees would invent a unit. | Added strict denomination and numeric parsing; unknown formats are omitted from cost series. | Focused test passes for `objective_cost: "12400"`, showing the cost empty state. | Other backend currency formats require a typed currency contract before they can be charted. |
| C | Missing backend artifacts could look like zero outcomes or sample analytics. | Added independent empty states and an unavailable exposure metric when no plan records exist. | Focused test passes with empty operations data and asserts empty/unavailable text plus no fixture amount. | Hook retains previously loaded values on some request failures; view displays the hook's current records without adding separate stale/error semantics. |
| D | A fixed `GBDT + Platt` badge could misstate which model supplied API calibration artifacts. | Replaced the hard-coded badge with `IntelligenceEvidence.model_name`. | Focused test rerun passes and asserts the exact model name is rendered. | API model names are backend-provided strings and are displayed as reported. |

## Checks run

- PASS — `npm.cmd exec -- vitest run src/test/AnalyticsView.test.tsx` — final run: 1 test file, 3 tests passed. Earlier run also passed before the model badge adjustment. Recharts emits its expected zero-size container warnings in jsdom; browser layout was not checked.
- BLOCKED — `npm.cmd exec -- tsc --noEmit -p tsconfig.app.json` — fails on existing unrelated errors in `src/api/client.ts`, `src/features/operations/DiagnosticsView.test.tsx`, and `src/features/operations/RecoveryView.tsx`. It reported no diagnostics in `AnalyticsView.tsx`.
- BLOCKED — `npm.cmd run build` — `tsc -b` stops on existing matcher type errors in `DispatchView.test.tsx` and `RouteComparisonView.test.tsx`.
- The first direct `npm` invocation was blocked by PowerShell execution policy; rerunning through `npm.cmd` executed the focused tests.

## Gaps

- `pasted-text-1.txt` was not present in the checkout when searched; coordinator was informed. Implementation followed the delegated contract and repository-local API/schema.
- No screenshot, browser interaction, live backend, or app-route integration check was run.
- Upstream chart guidance was read-only inspected; existing Recharts dependency was reused. No package changes or installs were made.
