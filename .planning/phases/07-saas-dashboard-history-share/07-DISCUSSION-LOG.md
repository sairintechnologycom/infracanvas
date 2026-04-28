# Phase 7: SaaS Dashboard + Scan History + Share Links - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 07-saas-dashboard-history-share
**Areas discussed:** App shell + home screen, Scan list + detail layout, Compare-two-scans UX, Share link + public landing

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| App shell + home screen | Sidebar vs top-nav, scan-list-as-home vs summary dashboard, breadcrumbs, team-switcher placement | ✓ |
| Scan list + detail layout | Table vs card grid, default columns, sort/filter affordances, scan detail page chrome | ✓ |
| Compare-two-scans UX | How user picks two scans, diff visualization style, what counts as "changed" | ✓ |
| Share link + public landing | Where Create-share lives, password/expiry UI, public landing branding, expired/wrong-password behavior | ✓ |

| Onboarding option | Description | Selected |
|-------------------|-------------|----------|
| Discuss now | Decide what 0-scan team sees | |
| Defer to Phase 7.5 | Phase 7.5 (GitHub Repo Connector) is natural home for onboarding | ✓ |

---

## App shell + home screen

### Q1 — Primary navigation pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Left sidebar + top bar (Recommended) | Fixed sidebar (team switcher + nav), top bar with user menu + breadcrumbs | ✓ |
| Top bar only, full-bleed canvas | Single top bar, edge-to-edge content, max diagram space | |
| Hybrid: collapsible sidebar | Sidebar collapses on detail page, expands on list/settings | |

**User's choice:** Left sidebar + top bar.

### Q2 — Post-login root screen

| Option | Description | Selected |
|--------|-------------|----------|
| Scans list | / redirects to /scans | |
| Summary dashboard (Recommended) | Latest scan card, sparkline, top critical findings, recent scans | ✓ |
| Empty/placeholder home | Hero with "View scans" + "Upload scan" CTAs | |

**User's choice:** Summary dashboard.

### Q3 — Team switcher

| Option | Description | Selected |
|--------|-------------|----------|
| Clerk OrganizationSwitcher (Recommended) | Use prebuilt component | ✓ |
| Custom dropdown reading Clerk orgs | Build our own from useOrganizationList() | |
| Single-org-only for v1 | Switching only via Clerk's hosted page | |

**User's choice:** Clerk OrganizationSwitcher.

### Q4 — Settings page structure

| Option | Description | Selected |
|--------|-------------|----------|
| Three sub-routes under /settings (Recommended) | /settings/{members,billing,integrations}, each its own page | ✓ |
| Single /settings page with tabs | One route with three tabs | |
| Defer Settings to a later phase | Members only in Phase 7; billing+integrations to Phases 13/8 | |

**User's choice:** Three sub-routes under /settings.

---

## Scan list + detail layout

### Q1 — Scan list display

| Option | Description | Selected |
|--------|-------------|----------|
| Dense table (Recommended) | Sortable columns: timestamp, source, commit, branch, score, crit, high, drift | ✓ |
| Card grid | Each scan a card with score badge + sparkline | |
| Timeline view | Vertical timeline grouped by day | |

**User's choice:** Dense table.

### Q2 — Filters / sort affordances (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Date range | Last 7d / 30d / custom | ✓ |
| Branch / source filter | Free-text branch + source dropdown | ✓ |
| Score threshold | Score < N or grade ≤ C | ✓ |
| Sort by score / critical count | Click headers to sort, default newest first | ✓ |

**User's choice:** All four ship in Phase 7.

### Q3 — Scan detail page layout

| Option | Description | Selected |
|--------|-------------|----------|
| Header strip + full-bleed viewer (Recommended) | Thin header (date, branch, SHA, score, [Compare] [Share]); viewer fills below | ✓ |
| Left rail metadata + viewer | Permanent left rail with metadata, score breakdown, findings list | |
| Tab strip (Diagram / Findings / Score / Raw JSON) | Detail page is tabbed | |

**User's choice:** Header strip + full-bleed viewer.

### Q4 — Scan JSON fetch path

| Option | Description | Selected |
|--------|-------------|----------|
| Client direct from R2 (Recommended) | Browser fetches via presigned URL from `GET /v1/scans/{id}` | ✓ |
| Server-side proxy through Next.js route handler | /api/scan/{id} streams from R2 | |

**User's choice:** Client direct from R2.

---

## Compare-two-scans UX

### Q1 — Compare entry

| Option | Description | Selected |
|--------|-------------|----------|
| From scan detail — "Compare against…" (Recommended) | [Compare] button on detail header opens recent-scans picker | ✓ |
| Multi-select on the scan list | Checkboxes on /scans rows | |
| Dedicated /compare page with two pickers | Standalone page, two dropdowns | |

**User's choice:** From scan detail.

### Q2 — Diff visualization

| Option | Description | Selected |
|--------|-------------|----------|
| Resource diff list + drill-down (Recommended) | Grouped Added/Removed/Changed list with attr-level expanders, click to view in single canvas with drift overlay | ✓ |
| Side-by-side dual canvas | Two viewers, scroll/zoom synced | |
| Single canvas with overlay | One canvas, color-by-drift-state, click for attribute diff | |

**User's choice:** Resource diff list + drill-down.

### Q3 — Diff compute location

| Option | Description | Selected |
|--------|-------------|----------|
| Backend endpoint (Recommended) | `GET /v1/scans/{a}/compare/{b}` returns ResourceDiff JSON | ✓ |
| Client-side compute | Browser fetches both JSONs, runs diff | |
| Client-side, but spawn a Web Worker | Same but offloaded from main thread | |

**User's choice:** Backend endpoint.

### Q4 — "Changed" definition

| Option | Description | Selected |
|--------|-------------|----------|
| Any attribute diff (Recommended) | Reuse v1.0 drift overlay attribute set | ✓ |
| Significant fields only (allowlist) | Hand-curated per resource type | |
| Findings-only diff | Resource changed only if findings changed | |

**User's choice:** Any attribute diff.

---

## Share link + public landing

### Q1 — Share entry location

| Option | Description | Selected |
|--------|-------------|----------|
| Action button on scan detail (Recommended) | [Share] in detail header → modal with expiry + password + copy + existing-links list | ✓ |
| Dedicated /scans/{id}/share page | Full-page share management | |
| From the scans list (row action) | Kebab menu on each row | |

**User's choice:** Action button on scan detail.

### Q2 — Public landing layout

| Option | Description | Selected |
|--------|-------------|----------|
| Branded full-bleed viewer (Recommended) | Top bar with team + scan + score + "Made with InfraCanvas"; viewer full-bleed read-only | ✓ |
| Marketing-wrapped viewer | "Try InfraCanvas free" CTA strips | |
| Token-only, no team identity | Hide team name on public page | |

**User's choice:** Branded full-bleed viewer.

### Q3 — Password gate

| Option | Description | Selected |
|--------|-------------|----------|
| Gate page before viewer (Recommended) | Separate "Enter password" page; scan never sent until auth passes | ✓ |
| Inline password prompt with shimmer | Viewer skeleton with modal overlay | |
| Password as URL fragment (#pw=…) | Embedded in URL fragment | |

**User's choice:** Gate page before viewer.

### Q4 — Default expiry options

| Option | Description | Selected |
|--------|-------------|----------|
| 1 day / 7 days / 30 days / Never (Recommended) | 7d default; "Never" warned | ✓ |
| 1 hour / 1 day / 7 days / Custom datetime | Includes datetime picker | |
| Always 7 days, no choice | Hard-coded expiry | |

**User's choice:** 1 day / 7 days / 30 days / Never (7d default).

### Q5 — Backend share-link endpoints

| Option | Description | Selected |
|--------|-------------|----------|
| Three new endpoints (Recommended) | POST create / GET token / POST unlock + DELETE revoke; bcrypt token + password hashes | ✓ |
| Single endpoint with password as header/body | One GET that accepts optional password | |
| Use signed URLs, no DB rows | JWT-encoded scan_id + expiry + password-hash | |

**User's choice:** Three new endpoints.

---

## Claude's Discretion

- Server Component vs Client Component split per page (default: RSC for data fetching, "use client" for stateful UI like diff expanders, share modal, scan-list filter form).
- shadcn/ui component picks (table primitives, modal, date-range picker) — match landing/'s Tailwind 4 setup.
- Score sparkline implementation — Recharts vs handrolled SVG vs react-sparklines.
- Whether dashboard extends `landing/` or lives in a separate `dashboard/` Next.js app (planner recommendation: separate).
- TanStack Query / SWR / native fetch choice for client data fetching.
- Diff endpoint URL shape (`GET /v1/scans/{a}/compare/{b}` vs `POST /v1/scans/compare`).
- `<OrganizationSwitcher/>` placement (sidebar header vs top bar).
- Empty-state copy for "no scans yet" — minimal one-liner; full onboarding belongs to Phase 7.5.

## Deferred Ideas

- First-run / empty-state onboarding flow — Phase 7.5.
- GitHub OAuth + repo browser + on-demand scan — Phase 7.5.
- Push webhook + auto-scan worker + Slack alert — Phase 8.
- CostLens summary panel on home dashboard — Phase 9.
- FlowMap topology summary on home dashboard — Phase 10+.
- Compare across >2 scans / extended score history — possible v1.2 enhancement.
- Mobile / sub-1080p layouts — out of scope per PROJECT.md.
- PR-bot diagram diff comments + GitHub status checks — v1.2 (PRB-01..02). Compare endpoint designed to be reusable.
- Share-link analytics (view counts, geographic spread) — schema supports it; no UI in Phase 7.
- Per-user notification preferences — out of scope.
