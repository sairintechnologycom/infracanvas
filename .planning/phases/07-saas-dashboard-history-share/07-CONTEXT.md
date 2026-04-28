# Phase 7: SaaS Dashboard + Scan History + Share Links - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the team-facing Next.js 15 SaaS dashboard on Vercel that consumes the Phase 6 backend. Scope is the user-facing surface: login → see your team's scans → open a scan in the embedded viewer → compare two scans → create a share link that renders the scan publicly without auth.

**In scope (DSH-02..06, HST-01..03, SHR-01..02):**
- Next.js 15 App Router scaffold on Vercel, uncached-by-default per-user data
- Clerk auth flow with active-org claim driving team context (uses Phase 6 backend RLS)
- App shell — left sidebar (team switcher + nav: Scans, Compare, Settings) + thin top bar
- Summary dashboard at `/` (latest score, score sparkline, top critical findings, recent scans table)
- `/scans` list page (dense table, filters: date range / branch / source / score threshold; sortable columns; paginated)
- `/scans/{id}` detail page (header strip with metadata + actions, full-bleed embedded `<DiagramCanvas/>` from `@infracanvas/viewer`)
- `/compare/{from}/{to}` page (resource-diff list + drill-down to single canvas with drift-overlay coloring)
- `/share/{token}` public landing (gate page if password-protected; branded full-bleed read-only viewer)
- `/settings/{members,billing,integrations}` sub-routes (members via Clerk `<OrganizationProfile/>`, billing → Stripe Customer Portal, integrations stub)
- Backend additions: `GET /v1/scans/{a}/compare/{b}` (HST-02 server-side diff), share-link endpoints (`POST /v1/scans/{id}/share-links`, `GET /v1/share-links/{token}`, `POST /v1/share-links/{token}/unlock`, `DELETE /v1/scans/{id}/share-links/{share_id}`), and any pagination/filter parameters HST-01 needs that aren't already in Phase 6's list endpoint
- Responsive at 1440p and 1080p (DSH-06)

**Out of scope (belongs in later phases):**
- First-run onboarding / empty-state UX → Phase 7.5 (GitHub Repo Connector — natural home for "scan a repo" flow). Phase 7 ships with a minimal "no scans yet — upload via CLI" message.
- GitHub OAuth + repo browser + on-demand scan → Phase 7.5
- Push webhooks + auto-scan worker + Slack alert → Phase 8
- CostLens panels (TGW/ExpressRoute/Azure Firewall splits) → Phase 9
- DC Agent / FlowMap 3b dashboard surfaces → Phase 10+
- Team-tier paywall + Stripe product gating → Phase 13 (TIR-01..02)
- Mobile / sub-1080p layouts (responsive target is desktop-only per PROJECT.md constraint)
- PR-bot / GitHub status checks → v1.2 (PRB-01..02)

</domain>

<decisions>
## Implementation Decisions

### App shell + navigation
- **D-01:** App shell = left sidebar + top bar pattern. Sidebar holds Clerk team switcher (top), main nav items (Scans, Compare, Settings), user menu (bottom). Top bar holds breadcrumbs + page-level actions. Rationale: standard SaaS pattern, scales cleanly when Phase 7.5 (Repos), Phase 8 (Webhooks), Phase 9 (CostLens) add nav items without redesign.
- **D-02:** Team switcher = Clerk's prebuilt `<OrganizationSwitcher/>` component. No custom dropdown. Rationale: Clerk handles invite-pending, create-org, switch-org out of the box; zero UI for us to maintain; solo-founder ops minimization.
- **D-03:** Settings page = three sub-routes (`/settings/members`, `/settings/billing`, `/settings/integrations`). Each is its own page. Members uses Clerk's `<OrganizationProfile/>` component, Billing links to Stripe Customer Portal (no in-app billing UI), Integrations is a stub list with a Slack webhook URL field placeholder for Phase 8 and a disabled "Connect GitHub" button placeholder for Phase 7.5.

### Home screen + scan list
- **D-04:** `/` = summary dashboard (not a redirect to `/scans`). Layout, top→bottom: latest scan score+grade card with finding counts, score-over-time sparkline (last 10 scans), top 3 critical findings across recent scans, recent-scans table with "View all →" link. Rationale: communicates value at a glance; gives a natural slot for future CostLens / FlowMap summary panels in Phases 9/10+.
- **D-05:** `/scans` = dense sortable table. Columns: timestamp, source (CLI / manual / future github-webhook), commit SHA, branch, score badge, critical count, high count, drift count. Sortable headers. Pagination uses Phase 6 HST-01 paginated list endpoint. Rationale: high-density table beats card grid for active teams generating many scans; matches the "scan history tool" mental model.
- **D-06:** Scan-list filter affordances (all four ship in Phase 7): (a) date range — last 7d / 30d / custom; (b) branch + source filter (free-text branch, source dropdown); (c) score threshold (score < N or grade ≤ C); (d) header-click sort with default = newest first. Backend may need to extend HST-01 query params if Phase 6 only supports basic pagination — planner should verify.

### Scan detail page
- **D-07:** `/scans/{id}` = header strip + full-bleed viewer. Header strip shows: back link to scans list, scan date, branch + commit SHA, score badge, finding counts (critical/high), action buttons `[Compare against…]` and `[Share]`. Below the strip, `<DiagramCanvas/>` from `@infracanvas/viewer` takes the remaining viewport. The viewer's own filter + detail panels (built in Phase 5) handle inline drill-down — do NOT duplicate that UI in dashboard chrome.
- **D-08:** Scan JSON fetch path = client-direct from R2. Dashboard calls `GET /v1/scans/{id}` (Phase 6 D-10), receives metadata + presigned R2 URL (≤300s TTL), the browser fetches the JSON directly from R2 and feeds it to `<ViewerProvider/>`. Rationale: keeps Vercel functions off the byte path (scan JSONs up to 25 MB per Phase 6 D-11); halves bandwidth cost vs. proxying; matches Phase 6 retrieval contract; RLS already gates which scans can be requested.

### Compare-two-scans
- **D-09:** Compare entry = "Compare against…" button on the scan detail header strip. Clicking opens a picker modal that lists recent scans (same branch first, then any scan), search by commit SHA. Selecting a target navigates to `/compare/{from}/{to}`. Rationale: most common flow is "what changed since the last scan on this branch" — make it one click from the scan you're already looking at.
- **D-10:** Diff visualization = resource-diff list with drill-down (NOT side-by-side dual canvas, NOT single-canvas overlay). Primary view = grouped list at the top: Added (green +N), Removed (red −N), Changed (amber ~N, expanders show attribute-level deltas), Findings delta (per-severity ±counts). Clicking a row jumps to that resource in a single `<DiagramCanvas/>` rendered with drift-overlay coloring (reuses Phase 1/2 drift styling already in viewer pkg). Rationale: smallest UI build, biggest signal-to-noise, doesn't fight 1080p horizontal real estate.
- **D-11:** Diff is computed server-side. New endpoint `GET /v1/scans/{a}/compare/{b}` returns a structured `ResourceDiff` JSON: `added[]`, `removed[]`, `changed[]` with per-attribute deltas, `findings_delta` per severity. Backend reads both scans from R2, runs the diff, returns ~tens of KB. Rationale: reusable by future PR-bot (v1.2 PRB-01) and a future CLI `infracanvas diff` command; keeps heavy CPU + 25 MB×2 bandwidth off the user's browser; cross-team protected by RLS.
- **D-12:** "Changed" definition = any attribute differs. Reuse the same attribute set the v1.0 drift overlay tracks (Phase 1/2). Rationale: matches user intuition for `infracanvas plan` overlay; new attribute fields auto-included as parser grows; no per-resource-type allowlist to maintain.

### Share links
- **D-13:** Share entry = `[Share]` action button on scan detail header strip → modal. Modal shows: expiry select (1 day / 7 days / 30 days / Never — 7 days default, "Never" flagged with a warning), optional password input, `[Copy link]` button. Below the form: list of existing share links for this scan with revoke action. Rationale: action lives where the user is looking at the thing they want to share.
- **D-14:** Public landing `/share/{token}` = branded full-bleed read-only viewer. Top bar shows team display name + scan timestamp + commit SHA + score badge + finding counts + small "Made with InfraCanvas" wordmark linking to infracanvas.dev. Below: `<DiagramCanvas/>` full-bleed, read-only (no Compare, no Share creation, no editing). Rationale: matches the CLI single-file HTML feel a recipient already trusts; engineer-shareable; "Made with" wordmark is light-touch lead-gen without feeling spammy.
- **D-15:** Password gate = separate page step. `/share/{token}` renders a small "Enter password" card if the link is password-protected; on submit, the server verifies and returns the scan metadata + presigned URL. Wrong password → same gate with error. Scan JSON is never sent to the client until auth passes. Rationale: standard, secure pattern; URL-fragment-as-password is rejected (history/referrer leakage).
- **D-16:** Share-link backend = three new endpoints + delete:
  - `POST /v1/scans/{id}/share-links` (auth'd, role: any team member can create)
  - `GET /v1/share-links/{token}` (public — returns scan metadata + presigned R2 URL on success; returns 401 with `{password_required: true}` if password-protected)
  - `POST /v1/share-links/{token}/unlock` (public, body: `{password}` — verifies bcrypt hash, returns scan metadata + presigned URL on success)
  - `DELETE /v1/scans/{id}/share-links/{share_id}` (auth'd, revokes)
  Tokens stored as bcrypt hashes (never raw); passwords stored as bcrypt hashes. Each share link row has `expires_at`, `password_hash` (nullable), `created_by`, `revoked_at`. Rationale: structured DB rows enable revocation + future analytics; signed-URL-only approach loses both.

### Backend / observability carry-forward (locked from Phase 6)
- **D-17:** Dashboard talks to backend on the same `/v1/*` namespace established in Phase 6. CORS = backend `clerk_allowed_origins` includes the dashboard's Vercel preview + production hostnames. Phase 6 already accepts CSV from env (commit `1d68312`).
- **D-18:** Every dashboard request flows through Clerk auth → backend's `team_id` resolution (Phase 6 D-02 — `SET LOCAL app.current_team_id`). No new auth path. Cross-team requests return 404 (Phase 6 D-10), not 403 — dashboard treats 404 as "scan does not exist" without leaking existence.
- **D-19:** Stripe Billing Meters fire on scan upload (Phase 6 D-08). Phase 7 does NOT add a metered event for compare or share-link operations — those are read-only views. Compute cost is bounded by D-11's server-side diff sizing.

### Claude's Discretion
- Next.js Server Component vs Client Component split per page (planner picks based on auth-cookie / streaming / RSC fetch ergonomics; default to RSC for data fetching, "use client" only for stateful UI like the diff list expanders, share modal, scan-list filter form).
- Concrete UI library choice within shadcn/ui ecosystem — landing/ already uses Tailwind 4 + Next 15; dashboard should match. Specific component picks (table primitives, modal, date-range picker) are planner discretion.
- Score sparkline implementation — Recharts vs lightweight handrolled SVG vs `react-sparklines`. Whichever fits Vercel bundle budget cleanly.
- Whether the dashboard lives under `landing/` (extending the existing Next 15 app with auth-gated routes) or a separate `dashboard/` package alongside `landing/` and `viewer/`. Trade-off: shared marketing/dashboard codebase vs. cleanly separated bundles. Default recommendation: separate `dashboard/` Next.js app — landing is anonymous + cached, dashboard is authenticated + uncached, very different cache + bundle profiles.
- Exact TanStack Query / SWR / native `fetch` choice for dashboard data fetching. Picks whatever pairs best with Next 15 RSC + Clerk session token forwarding.
- Diff endpoint URL shape — `GET /v1/scans/{a}/compare/{b}` vs `POST /v1/scans/compare {from, to}`. Planner picks based on caching ergonomics (GET is cacheable + idempotent; preferred).
- Whether `<OrganizationSwitcher/>` lives in the sidebar header or the top bar — planner picks based on visual balance.
- Empty-state copy / illustration for "no scans yet" — keep it minimal (one line + a `pip install infracanvas` hint), full onboarding belongs to Phase 7.5.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` § "Phase 7: SaaS Dashboard + Scan History + Share Links" — goal, requirements list (DSH-02..06, HST-01..03, SHR-01..02), 5 success criteria, depends on Phase 5 (viewer pkg ✓) + Phase 6 (backend ✓)
- `.planning/REQUIREMENTS.md` DSH-02..06 — Next.js 15 scaffold, Clerk auth flow with team context, scan list+detail pages, settings page (members/billing/integrations), 1440p+1080p responsive
- `.planning/REQUIREMENTS.md` HST-01..03 — list scans paginated team-filtered, compare two scans diff API, dashboard scan-list UI
- `.planning/REQUIREMENTS.md` SHR-01..02 — generate share link with UUID + token + optional password + expiry, public share-link landing page rendering scan viewer without auth
- `.planning/PROJECT.md` § Key Decisions — Next.js 15 over 14 (uncached-by-default for SaaS); Stripe Billing Meters only; viewer extracted to dual-build package BEFORE dashboard work (DSH-01 ✓)
- `.planning/PROJECT.md` § Constraints — solo founder (minimize ops surface), $10–104/mo budget, Next.js 15 App Router on Vercel, ES2020+ browsers, no IE

### Prior-phase constraints (carry forward — read these)
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-01 — Teams = Clerk Organizations, mirrored in `teams` table by `clerk_org_id`
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-02 — `SET LOCAL app.current_team_id` per-request RLS pattern; dashboard inherits this transparently via the auth dependency
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-03 — Role enforcement via FastAPI `require_role(...)` dependency reading active-org claim from Clerk JWT (dashboard's compare + share-link create need to know which roles allow what)
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-06, D-07, D-09, D-10, D-11 — scan upload/retrieval contract, R2 key layout `teams/{team_id}/scans/{scan_id}.json`, sync-vs-async commit split, `GET /v1/scans/{id}` returns metadata + presigned R2 URL with ≤300s TTL, 25 MB ceiling — Phase 7 fetches scans via this contract unchanged
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-14 — two full envs (dev + prod), Stripe test on dev / live on prod — dashboard deploys must match (Vercel preview → backend dev; Vercel production → backend prod)
- `.planning/phases/06-saas-backend-foundation/06-CONTEXT.md` D-21 — `X-Request-ID` propagation (UUIDv7); dashboard should forward `X-Request-ID` from inbound requests on its API proxy calls so backend traces stay linked
- `.planning/phases/05-viewer-extraction/05-CONTEXT.md` — `@infracanvas/viewer` shared package contract: `<DiagramCanvas/>`, `<FlowMapCanvas/>`, `<ViewerProvider/>`, `createViewerStore`, `useViewerStore`. Dashboard imports these as React components (not the single-file HTML build).
- `.planning/phases/04-e2e-wiring-hardening/04-CONTEXT.md` — CLI exit-code + stderr contract; informs how Phase 7.5 will eventually bridge CLI uploads, but not Phase 7 directly

### Vendor docs (read during planning)
- Next.js 15 App Router: https://nextjs.org/docs/app
- Next.js 15 Caching (uncached-by-default rationale): https://nextjs.org/docs/app/building-your-application/caching
- Clerk Next.js integration: https://clerk.com/docs/quickstarts/nextjs
- Clerk `<OrganizationSwitcher/>` + `<OrganizationProfile/>` components: https://clerk.com/docs/components/organization
- Vercel deployment + env vars per env: https://vercel.com/docs/projects/environment-variables
- Stripe Customer Portal (billing settings page): https://docs.stripe.com/customer-management
- shadcn/ui components: https://ui.shadcn.com/docs (if planner adopts; landing/ uses Tailwind 4 already)

### Cross-package integration points (dashboard consumes)
- `@infracanvas/viewer` package barrel — `<DiagramCanvas>`, `<FlowMapCanvas>`, `<ViewerProvider>`, `createViewerStore`, `useViewerStore` (from `viewer/src/index.ts`, built to `viewer/dist/lib/`)
- `cli/infracanvas/graph/models.py` — `ResourceGraph` Pydantic v2 schema (TypeScript types in `viewer/src/types.ts` mirror this; dashboard uses the TS types for the diff list rendering)
- `backend/app/routes/scans.py` — Phase 6 scan endpoints; Phase 7 adds compare + share-link routes alongside

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `@infracanvas/viewer` shared package (Phase 5) — exports `<DiagramCanvas/>` + `<FlowMapCanvas/>` + provider + store factory. Dashboard imports these directly; no need to reimplement diagram rendering, drift overlay coloring, filter panel, detail panel, or VPC/subnet grouping. The drift coloring (added/removed/changed/unchanged/shadow) already exists from v1.0 plan-overlay work — reused for compare view.
- `landing/` Next.js 15 app already scaffolded — `next@^15.0.0`, `react@^18.3.1`, Tailwind 4, TypeScript. Dashboard either extends this app with auth-gated routes or sits alongside as a sibling Next app (Claude's discretion D-19); either way, the toolchain and Tailwind config are already proven.
- Phase 6 `backend/app/routes/scans.py` — pattern for new routes (auth dep, `require_role(...)`, RLS-scoped session via `team_scoped_session`, presigned URL generation). New compare + share-link endpoints follow the same shape.
- Phase 6 `backend/app/db/models.py` — SQLAlchemy 2.0 async models (Team, Scan). New `ShareLink` model uses the same `team_id` FK pattern + RLS policy.
- Clerk components — `<OrganizationSwitcher/>`, `<OrganizationProfile/>`, `<UserButton/>` provide team switcher, members management, user menu out of the box.
- Stripe Customer Portal — backend can mint a portal session URL; dashboard `/settings/billing` is just a button that POSTs to backend, gets a URL, redirects.

### Established Patterns
- Backend: SQLAlchemy 2.0 async + asyncpg + Alembic migrations + RLS policies authored as raw SQL (Phase 6 D-15, D-17). New share-link table + RLS policy follows.
- Backend: every authenticated route opens a transaction, sets `app.current_team_id`, runs query, commits — encapsulated in `team_scoped_session` dep (Phase 6). New compare + share-link auth'd endpoints reuse this.
- Backend: presigned R2 URLs minted server-side with ≤300s TTL (Phase 6 D-10). Share-link landing follows the same pattern (mint URL after token + optional password verify).
- Frontend: TypeScript strict mode + ES2020 target + 2-space indent, no semicolons (existing `viewer/` + `landing/` convention).
- Frontend (viewer pkg, Phase 5): Zustand store factory + Provider — dashboard's per-page viewer instance gets its own store via `<ViewerProvider scan={...}>`.

### Integration Points
- Dashboard ↔ backend: same `/v1/*` namespace as Phase 6. Backend's `clerk_allowed_origins` env adds dashboard hostnames (Vercel preview + production); Phase 6 commit `1d68312` already supports CSV format.
- Dashboard ↔ R2: client-direct fetch via presigned URLs from backend `GET /v1/scans/{id}`. No CORS work needed beyond what Phase 6 R2 bucket policy already permits.
- Dashboard ↔ Clerk: Clerk Next.js middleware gates routes; active-org claim drives team context. JWT forwarded to backend on every API call.
- Dashboard ↔ Stripe Customer Portal: redirect-only integration. No card UI in our app.
- Backend additions land in `backend/app/routes/`: `compare.py` (new), `share_links.py` (new). Migrations: `share_links` table + RLS policies + indexes (`token_hash` unique, `expires_at`, `team_id`).

</code_context>

<specifics>
## Specific Ideas

- Sidebar layout (selected via preview during discussion): logo + team switcher at top, nav items in middle (Scans / Compare / Settings), user menu at bottom. Compact width (~220px).
- Summary dashboard layout (selected via preview): latest-scan card at top with score+grade prominent, sparkline strip below, top-3 critical findings list, recent-scans table at bottom with "View all →" affordance.
- Scan list table layout (selected via preview): columns Date / Source / Commit / Branch / Score / Crit / High / Drift, sortable, dense rows.
- Scan detail layout (selected via preview): thin header strip with `← Scans / 04-28 main@a1b2  B+ 87  3c/12h   [Compare] [Share]`, viewer full-bleed below.
- Compare diff layout (selected via preview): top summary line `a1b2 → 9f8e   +3 −5 ~7   findings: +1 critical, −2 high`; grouped sections Added (green) / Removed (red) / Changed (amber) with attribute-level expanders showing `before → after`.
- Share landing layout (selected via preview): top bar `Acme  scan 04-28 main@a1b2  B+ 87  3c/12h     ⤷ InfraCanvas`, viewer full-bleed read-only below.
- Default share-link expiry = 7 days; "Never" allowed but flagged with a warning.
- Wrong-password share-link error stays on the same gate page (no redirect, no exposed scan metadata).

</specifics>

<deferred>
## Deferred Ideas

- **First-run / empty-state onboarding flow** — full UX (CLI install instructions, sample scan, "Connect GitHub" button, drag-and-drop scan JSON upload) deferred to Phase 7.5 per user choice during this discussion. Phase 7 ships a minimal one-line "no scans yet — upload via CLI" empty state.
- **GitHub OAuth + repo browser + on-demand scan** — Phase 7.5.
- **Push webhook + auto-scan worker + Slack alert on Critical findings** — Phase 8 (WBH-01..03).
- **CostLens summary panel on the home dashboard** — Phase 9. Home dashboard layout (D-04) reserves a slot conceptually but ships without it.
- **FlowMap topology summary on home dashboard** — Phase 10+.
- **Compare across more than two scans / scan-over-time score history beyond a sparkline** — out of scope, can be a v1.2 enhancement if user-requested.
- **Mobile / sub-1080p layouts** — explicitly out of scope per PROJECT.md "modern browsers only, web-first" constraint.
- **PR-bot diagram diff comments + GitHub status checks** — v1.2 (PRB-01..02). The compare endpoint (D-11) is designed to be reusable for this.
- **Share-link analytics (view counts, geographic spread)** — backend stores enough to support this later (`share_links` row), but no UI in Phase 7.
- **Per-user notification preferences** — out of scope; settings page only covers members + billing + integrations stub.

</deferred>

---

*Phase: 07-saas-dashboard-history-share*
*Context gathered: 2026-04-28*
