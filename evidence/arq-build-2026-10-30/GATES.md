# arQ 44-minute implementation evidence

Start: 2026-10-29 22:03:33 UTC (2026-10-30 03:33:33 IST).
Deadline: 2026-10-29 22:47:33 UTC. Wrap-up begins 22:42 UTC.

Owner's latest instruction to finish without questions overrides the unavailable usage-check gate for this batch. Usage remains unknown; no account allowance is inferred. Four concurrent slots including coordinator are available. All implementation workers use Luna. No commits or deployment authorized.

## Preservation

Root branch collab/person2, HEAD 2c7a4fb. Initial dirty root files: backend/api.py, backend/demo/__init__.py, backend/jobs.py, skills-lock.json, plus existing untracked frontend, backend demo facade, runs_service, fixtures, reports, skills, and tests. Existing App, Navbar, SidebarRail, HealthPill, index.css copied into baseline/ before edits. Archives and trained checkpoints remain untouched.

## Acceptance requirements

- W01–W10 functional dispatcher views; M01–M10 driver views; shared design primitives and consistent tokens.
- Actual backend calls, backend job IDs, terminal states, independent validation, explicit unsupported and offline states; no successful mock fallback.
- Dominant map uses actual route coordinates; [longitude,latitude] ordering, selected route/stops, alternate routes, fit/zoom and tile-failure/list fallback.
- Scoped driver pairing; idempotent congestion; candidate evaluation; authorized approval; durable version publication; version-specific acknowledgement; second-driver isolation; reconnect.
- Alpha=0 and model checkpoints frozen; experimental four-qubit residual labeled; no road-leg inference from whole-delivery ETA.
- Web typecheck/build/component tests, backend contracts/security regression, mobile typecheck/export/runtime, browser responsive smoke and screenshots. Physical phones require actual device evidence.
- Three substantive failure/change/retest cycles with exact results.
- Startup instructions, agent execution ledger, endpoint inventory, screenshots, test results, unsupported capabilities, security limitations and release report.

## Initial executed baseline

- Web `npm run build`: PowerShell execution policy rejected npm.ps1. Retried `npm.cmd run build`: PASS, 2624 modules, 1.86 MB JS warning.
- Backend truth tests first failed on existing inaccessible pytest basetemp. Retried unique basetemp; collection overlapped active backend edit and observed transient SyntaxError. Backend worker notified; rerun after completed edit is required.
- UI Skills MCP catalog discovery executed. Shadcn tools available; no Rare UI MCP tool found. EvilCharts official docs inspected; existing locally adapted Recharts components and Iconoir SVG assets found. No new competing chart library required.

This ledger records targets, not completion. Agent reports and final report contain executed outcomes.
