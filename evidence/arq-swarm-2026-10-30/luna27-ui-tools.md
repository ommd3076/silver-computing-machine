# UI Skills MCP and RareUI MCP findings

Checked: 2026-10-29 22:28 UTC (registry source states `https://www.ui-skills.com/skills/registry.json`).

## Tool availability and scope

- The UI Skills MCP tools are callable: `mcp__ui_skills__list_skills` and `mcp__ui_skills__get_skill`.
- The full registry call returned 439 skills. I also searched relevant categories (dashboard, accessibility, web design, React, data visualization) and fetched the skill guidance listed below. Registry count/listing is tool discovery, not an endorsement or quality verification.
- No tool matching RareUI was present in `ALL_TOOLS` by name or description. No RareUI search/call was made; capability is unavailable in this session, so there are no RareUI results to report.
- This task was evidence-only. No product source, tests, or runtime state were modified.

## Relevant skill guidance read

- `ibelick/ui-skills-root`: route to the smallest appropriate skill set; use one by default, at most three for a broad review/redesign. For this polish task, `dammyjay93/interface-design` was the primary guide, with accessibility and engineering guidance as checks.
- `dammyjay93/interface-design`: understand the actual dispatcher, decision to make, and operational domain before choosing layout; give the view one clear focal workflow; build meaningful hierarchy through type/space/color; inspect and reuse current components, tokens, and accessible primitives; avoid repetitive metric-card grids and default dashboard patterns. Design the meaningful loading, empty, error, and action-confirmation states.
- `ibelick/fixing-accessibility`: prioritize accessible names for icon-only controls and fields, keyboard access and visible focus, semantic native controls, dialog focus handling, linked field errors, status announcements, and contrast. Do small targeted fixes; do not add redundant ARIA or migrate libraries.
- `addyosmani/frontend-ui-engineering`: compose focused components; separate fetching from presentation; retain simple state ownership; use the established design system and realistic content; do not rely on color alone; design mobile-first and check 320/768/1024/1440 widths plus loading/empty/error/success/permission states.
- `vercel-labs/react-best-practices`: avoid request waterfalls (parallelize independent requests), load heavy features conditionally, keep state/effects minimal, derive state during render, and optimize only where the actual React app needs it. Next.js-specific server/RSC guidance does not apply to this Vite frontend.
- `vercel-labs/web-design-guidelines`: this skill requires fetching its live rule file before performing a formal review; that live audit was not part of this MCP availability task, so no compliance verdict is claimed.
- `larashero3-dotcom/lieflat-charts`: choose charts from the data shape and honest units; every encoded visual mark must map to a real record or explicit aggregation; use clear titles/units/source and stable deterministic values; no decorative interactivity or fabricated values. Its report/template-specific rules are not a general product-dashboard spec, so use only the honesty and chart-encoding principles here.

## Actionable guidance for ArQ polish owners

1. Keep the primary dispatcher loop visually dominant: inspect a backend proposal, compare it with the active validated manifest, surface constraint/validation provenance, then require an explicit approval action. Avoid making overview KPIs the primary workflow.
2. Distinguish observed API data, deterministic demo fixtures, illustrative graphics, unavailable metrics, and validation status at the point of display. Never let placeholder routes, costs, ETAs, risk, or chart points read as live fleet evidence.
3. Keep unavailable states actionable and truthful: state what data is missing and which backend workflow produces it; do not fill the gap with a chart skeleton that looks like measured values.
4. Check icon-only navigation/actions for accessible names; ensure keyboard users can reach and understand active navigation, dialogs, approval controls, map selections, errors, loading and success announcements. Color needs a text/icon cue.
5. For the operations map and dense tables, preserve readable labels and responsive behavior; verify narrow layouts at 320/768px and desktop at 1024/1440px. Prefer a schematic when route geometry is missing and label it as such.
6. For analytics, only plot API-backed quantities with explicit unit/source and valid aggregation; if the service does not return a measure, show an explicit unavailable state rather than inferred trend data.
7. Reuse existing app shell, primitives, tokens, API operations hook, and feature components. Keep UI fixes scoped and avoid introducing a second component/design system.

## Boundaries

These are implementation suggestions derived from the fetched skill guidance and the current ArQ product goal, not a completed visual audit or an owner-approved art direction. The UI skills registry is external reference material; it does not prove that the interface passes accessibility, visual, browser, or responsive QA.
