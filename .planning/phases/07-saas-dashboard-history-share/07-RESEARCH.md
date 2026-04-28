# Phase 7: SaaS Dashboard + Scan History + Share Links — Research

**Researched:** 2026-04-28
**Domain:** Next.js 15 App Router dashboard consuming FastAPI backend (Phase 6), @infracanvas/viewer, Clerk Organizations, R2 presigned URLs, bcrypt share-link tokens
**Confidence:** HIGH (backend contract verified from source; viewer package verified from source; Clerk/Next.js patterns verified from Context7)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**App shell + navigation**
- D-01: App shell = left sidebar (220px fixed) + top bar (48px). Sidebar: team switcher (top), nav items (Scans, Compare, Settings), user menu (bottom). Top bar: breadcrumbs + page-level actions.
- D-02: Team switcher = Clerk `<OrganizationSwitcher/>`. No custom dropdown.
- D-03: Settings = three sub-routes (`/settings/members`, `/settings/billing`, `/settings/integrations`). Members: Clerk `<OrganizationProfile/>`. Billing: Stripe Customer Portal redirect. Integrations: stub.

**Home screen + scan list**
- D-04: `/` = summary dashboard (not redirect). Layout: latest scan score card + sparkline + top 3 critical findings + recent scans table.
- D-05: `/scans` = dense sortable table. Columns: timestamp, source, commit SHA, branch, score badge, critical count, high count, drift count.
- D-06: Scan-list filters (all four in Phase 7): (a) date range, (b) branch + source, (c) score threshold, (d) header-click sort. Backend may need to extend HST-01 query params.

**Scan detail page**
- D-07: `/scans/{id}` = header strip + full-bleed `<DiagramCanvas/>`. Header: back link, date, branch+SHA, score badge, finding counts, `[Compare]` + `[Share]` buttons.
- D-08: Scan JSON = client-direct R2 fetch. Dashboard calls `GET /v1/scans/{id}`, gets presigned URL (≤300s TTL), browser fetches JSON directly, feeds to `<ViewerProvider/>`.

**Compare**
- D-09: Compare entry = "Compare against…" button → picker modal → navigate to `/compare/{from}/{to}`.
- D-10: Diff view = resource-diff list + drill-down drawer (shadcn `<Sheet/>`). Grouped: Added/Removed/Changed/Findings delta. Drill-down: `<DiagramCanvas/>` with drift-overlay coloring.
- D-11: Diff computed server-side by new `GET /v1/scans/{a}/compare/{b}`. Returns `ResourceDiff` JSON: `added[]`, `removed[]`, `changed[]` with attribute deltas, `findings_delta` per severity.
- D-12: "Changed" = any attribute differs. Reuse Phase 1/2 drift attribute set.

**Share links**
- D-13: Share entry = `[Share]` button on scan detail → modal (expiry select, optional password, `[Copy link]`, existing links list with revoke).
- D-14: `/share/{token}` = branded full-bleed read-only viewer. Top bar shows team name + scan metadata + "Made with InfraCanvas" wordmark.
- D-15: Password gate = separate page step. Zero scan metadata shown until password verified. URL-fragment password rejected.
- D-16: Share-link backend = four endpoints:
  - `POST /v1/scans/{id}/share-links` (auth'd)
  - `GET /v1/share-links/{token}` (public; 401 with `{password_required: true}` if gated)
  - `POST /v1/share-links/{token}/unlock` (public, body: `{password}`)
  - `DELETE /v1/scans/{id}/share-links/{share_id}` (auth'd)
  - Token + password both bcrypt-hashed. Row has `expires_at`, `password_hash` (nullable), `created_by`, `revoked_at`.

**Backend / observability carry-forward**
- D-17: Same `/v1/*` namespace. `clerk_allowed_origins` env adds dashboard Vercel hostnames (CSV, commit `1d68312` supports this).
- D-18: Every dashboard request → Clerk JWT → backend `team_id` resolution. Cross-team returns 404.
- D-19: Stripe Billing Meters fire only on scan upload. Compare + share-link are read-only; no meter events.

### Claude's Discretion
- Server Component vs Client Component split per page (default RSC; "use client" only for stateful UI)
- Concrete shadcn component picks (table, modal, date-range picker)
- Score sparkline: handrolled SVG (~20 LOC per UI-SPEC)
- `landing/` extension vs separate `dashboard/` package (default: separate)
- Data-fetching: TanStack Query / SWR / native `fetch` — whatever pairs best with RSC + Clerk token forwarding
- Diff endpoint URL shape (GET preferred for cacheability)
- `<OrganizationSwitcher/>` placement in sidebar vs top bar
- Empty-state copy

### Deferred Ideas (OUT OF SCOPE)
- First-run onboarding / empty-state UX → Phase 7.5
- GitHub OAuth + repo browser + on-demand scan → Phase 7.5
- Push webhooks + auto-scan worker + Slack alert → Phase 8
- CostLens summary panel on home dashboard → Phase 9
- FlowMap topology summary → Phase 10+
- Compare across more than two scans → v1.2
- Mobile / sub-1080p layouts → out of scope
- PR-bot / GitHub status checks → v1.2 (PRB-01..02)
- Share-link analytics → out of scope Phase 7
- Per-user notification preferences → out of scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSH-02 | Next.js 15 App Router scaffold on Vercel, uncached-by-default | Separate `dashboard/` app; Next.js 15 default fetch: no-store; ClerkProvider + clerkMiddleware |
| DSH-03 | Dashboard auth flow via Clerk with active-org team context | `auth()` in RSC gives `orgId`; `getToken()` for Bearer; `clerkMiddleware` + `createRouteMatcher` |
| DSH-04 | Scan list page + detail page embedding shared viewer | `GET /v1/scans` (new) + `GET /v1/scans/{id}` (Phase 6); `<ViewerProvider>` + `<DiagramCanvas/>` |
| DSH-05 | Settings page — members, billing, integrations | Clerk `<OrganizationProfile/>`, Stripe Customer Portal redirect, integrations stub |
| DSH-06 | Responsive at 1440p and 1080p | `max-w-7xl`, sidebar fixed 220px, full-bleed viewer pages; no mobile |
| HST-01 | List scans paginated, team-filtered | New `GET /v1/scans` endpoint + scan metadata schema extension |
| HST-02 | Compare two scans diff API | New `GET /v1/scans/{a}/compare/{b}` endpoint; `ResourceDiff` response shape |
| HST-03 | Dashboard scan-list UI — timestamp, commit SHA, score, critical count | Requires `branch`, `commit_sha`, `source` fields in scan DB row or summary_json |
| SHR-01 | Generate share link with UUID + token + optional password + configurable expiry | New `share_links` table + 4 endpoints; bcrypt for token + password hashing |
| SHR-02 | Public share-link landing page rendering scan viewer without auth | `/share/{token}` outside Clerk middleware; `GET /v1/share-links/{token}` public endpoint |

</phase_requirements>

---

## Summary

Phase 7 builds the team-facing SaaS dashboard as a **new `dashboard/` Next.js 15 app** alongside the existing `landing/` app. The monorepo root `package.json` already declares `workspaces: ["viewer"]` — adding `"dashboard"` extends the existing workspace topology cleanly. The dashboard consumes `@infracanvas/viewer` (already built at `viewer/dist/lib/`) and the Phase 6 FastAPI backend at `/v1/*`.

The most important finding is a **three-way gap** in the Phase 6 backend that Phase 7 must close before the dashboard can be built: (1) `GET /v1/scans` list endpoint does not exist, (2) the `scans` table has no `branch`, `commit_sha`, or `source` columns — only `summary_json` with resource counts and score, (3) `GET /v1/scans/{a}/compare/{b}` and all share-link endpoints are absent. The Phase 7 plan must open the phase with backend tasks that add these missing pieces before any dashboard UI tasks can run against live data.

The second key finding is the **workspace topology decision**: the root `package.json` only lists `"viewer"` in workspaces. The dashboard must be added here (`"workspaces": ["viewer", "dashboard"]`) and scaffolded as a fresh Next.js 15 app with shadcn/ui new-york preset, Tailwind v4, and Clerk. The `landing/` app is dark-mode/anonymous, the dashboard is light-mode/authenticated — they must remain separate bundles.

**Primary recommendation:** Wave 0 = backend extensions (scan metadata columns + list endpoint + compare endpoint + share-link endpoints + DB migration). Wave 1 = dashboard scaffold + app shell. Wave 2 = scan list + detail. Wave 3 = compare. Wave 4 = share links. Wave 5 = settings. Wave 6 = share public landing outside auth.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auth gate (all dashboard routes except /share) | Frontend Server (middleware) | — | clerkMiddleware in middleware.ts runs at Edge before any RSC; single enforcement point |
| Team context / org-scoped data fetching | Frontend Server (RSC) | — | `auth()` in RSC gives `orgId` + `getToken()` for Bearer; no client round-trip needed |
| Scan list + filters | API / Backend | Frontend Server (RSC) | Backend owns pagination + SQL filtering; RSC fetches on every request (no cache) |
| Scan JSON bytes (diagram data) | CDN / Storage (R2) | — | Client fetches presigned URL directly; backend never proxies bytes (D-08 locked) |
| Compare / diff computation | API / Backend | — | Server-side diff reads two R2 objects, diffs in Python; returns small JSON (D-11 locked) |
| Share-link auth (token + password verify) | API / Backend | — | bcrypt verify is CPU-bound; belongs server-side; frontend only submits and renders result |
| Diagram rendering | Browser / Client | — | @xyflow/react + Zustand are client-only (marked `'use client'`); SSR for canvas is wasted |
| Settings / members | Browser / Client | Frontend Server | Clerk `<OrganizationProfile/>` is client component; billing redirect is a server action or route handler |
| Public share landing (/share/{token}) | Frontend Server (RSC) | Browser / Client | Page is outside Clerk auth group; RSC calls public API endpoint; viewer loads client-side |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | ^15.0.0 | App Router scaffold | Matches `landing/` toolchain; uncached-by-default (no-store) fits per-user data; confirmed in landing/package.json |
| @clerk/nextjs | 7.2.7 | Auth + org session | Locked from Phase 6 D-01; `clerkMiddleware`, `auth()`, `OrganizationSwitcher` all needed |
| tailwindcss | ^4.1.0 | Styling | Matches `landing/` and `viewer/` (Tailwind v4 — @import "tailwindcss" syntax, no tailwind.config.js) |
| shadcn/ui (CLI) | 4.5.0 (`shadcn`) | Component primitives | UI-SPEC locked; blocks: button, dialog, alert-dialog, select, input, table, tabs, sheet, skeleton, toast, pagination, calendar, popover, form, label, card, dropdown-menu |
| lucide-react | ^0.511.0 | Icons | Matches `viewer/` transitive dep; UI-SPEC locked |
| @infracanvas/viewer | workspace:* | DiagramCanvas + ViewerProvider | Phase 5 complete; dist/lib/ built; exports: `DiagramCanvas`, `ViewerProvider`, `createViewerStore`, `useViewerStore`, all types |
| react | ^18.3.1 | UI runtime | Peer dep; matches landing/; viewer peer dep is `^18.0.0 || ^19.0.0` so 18 works |
| react-dom | ^18.3.1 | DOM renderer | Same |

### Supporting (Frontend)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-day-picker | 9.14.0 | Calendar / date-range picker | shadcn `<Calendar/>` block dep; only for `/scans` custom date-range filter |
| next/font/google | (bundled) | Inter + JetBrains Mono | UI-SPEC locked font choice; zero runtime cost (preloaded) |

### Supporting (Backend additions)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bcrypt | 4.x (Python) | Hash share-link tokens + passwords | Share-link security (D-16); not in backend venv yet — must be added to pyproject.toml |
| passlib[bcrypt] | latest | bcrypt wrapper with safe API | Alternative to raw bcrypt; easier constant-time compare; choose one [ASSUMED — planner pick] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `fetch` in RSC | TanStack Query / SWR | TanStack Query adds client-side caching for the scan list; native fetch is sufficient for RSC-first + mutations via server actions; prefer native for simplicity |
| Handrolled SVG sparkline | Recharts | Recharts adds ~45 kB; 10-point polyline needs none of that; UI-SPEC locked: handrolled SVG |
| Separate `dashboard/` Next.js app | Auth-gated routes in `landing/` | landing/ is dark/anonymous/cached; dashboard is light/authenticated/uncached; separate bundle profiles prevent cache poisoning and reduce deployment coupling |

**Installation (dashboard):**
```bash
# From repo root — add dashboard to workspaces then scaffold
# 1. Update package.json workspaces: ["viewer", "dashboard"]
# 2. Scaffold Next.js 15:
cd dashboard && npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --no-import-alias
# 3. Install Clerk:
npm install @clerk/nextjs
# 4. Initialize shadcn/ui (new-york preset, slate base, CSS vars, Tailwind v4):
npx shadcn@latest init
# 5. Add shadcn blocks used in Phase 7:
npx shadcn@latest add button dialog alert-dialog select input table tabs sheet skeleton sonner pagination calendar popover form label card dropdown-menu
# 6. Link viewer workspace package:
npm install @infracanvas/viewer  # resolves from workspaces
```

**Version verification:** [VERIFIED: npm registry] — next@16.2.4 is latest stable; landing/ uses `^15.0.0` (locks to 15.x); dashboard should match `^15.0.0` to stay on the same major. @clerk/nextjs@7.2.7 verified. shadcn@4.5.0 verified. react-day-picker@9.14.0 verified.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser / Client
  │
  ├─ Clerk-hosted sign-in → redirect to /
  │
  ├─ Authenticated routes (/(dashboard) route group)
  │   clerkMiddleware.ts → auth.protect() for all non-/share routes
  │   RSC layout.tsx → <ClerkProvider> + app shell (sidebar + top bar)
  │   │
  │   ├─ GET /                RSC: fetch /v1/scans?limit=5 (latest + sparkline)
  │   ├─ GET /scans            RSC: fetch /v1/scans?{filter params} + URL searchParams
  │   ├─ GET /scans/{id}       RSC: fetch /v1/scans/{id} → presigned URL
  │   │                        Client: fetch R2 presigned URL → JSON → <ViewerProvider>
  │   ├─ GET /compare/{a}/{b}  RSC: fetch /v1/scans/{a}/compare/{b} → ResourceDiff JSON
  │   │                        Client: diff list render + drill-down drawer
  │   └─ GET /settings/*       Clerk <OrganizationProfile/> / Stripe redirect / stub
  │
  └─ Public route (/(public) route group — no clerkMiddleware protect)
      GET /share/{token}
        RSC: GET /v1/share-links/{token} → {password_required} or {scan_metadata + presigned_url}
        Client (if password needed): POST /v1/share-links/{token}/unlock → same shape
        Client: <ViewerProvider readOnly> + <DiagramCanvas/>
  │
  ▼
Vercel Edge (middleware.ts)
  clerkMiddleware — runs on all routes
  createRouteMatcher(['/share(.*)']) → isPublicRoute check → skip auth.protect()
  │
  ▼
FastAPI backend (Fly.io)
  /v1/scans                GET  (NEW — list, paginated, filtered)   [HST-01]
  /v1/scans/{id}           GET  (Phase 6 — metadata + presigned URL)
  /v1/scans/{a}/compare/{b} GET (NEW — server-side diff)             [HST-02]
  /v1/scans/{id}/share-links POST  (NEW — create share link)         [SHR-01]
  /v1/scans/{id}/share-links/{sid} DELETE (NEW — revoke)             [SHR-01]
  /v1/share-links/{token}   GET  (NEW — public, password gate)       [SHR-02]
  /v1/share-links/{token}/unlock POST (NEW — public, bcrypt verify)  [SHR-02]
  │
  ├─ Neon Postgres (RLS)
  │   scans table (extended: +branch, +commit_sha, +source columns)
  │   share_links table (NEW)
  │
  └─ Cloudflare R2
      teams/{team_id}/scans/{scan_id}.json  (presigned GET, ≤300s TTL)
```

### Recommended Project Structure
```
dashboard/
├── app/
│   ├── (dashboard)/          # Route group — all authenticated routes
│   │   ├── layout.tsx         # App shell: sidebar + top bar (ClerkProvider wraps here)
│   │   ├── page.tsx           # / summary dashboard (RSC)
│   │   ├── scans/
│   │   │   ├── page.tsx       # /scans list (RSC, reads searchParams for filters)
│   │   │   └── [id]/
│   │   │       └── page.tsx   # /scans/{id} detail (RSC fetches metadata; client fetches JSON)
│   │   ├── compare/
│   │   │   └── [from]/
│   │   │       └── [to]/
│   │   │           └── page.tsx  # /compare/{from}/{to} (RSC fetches diff)
│   │   └── settings/
│   │       └── [[...slug]]/
│   │           └── page.tsx   # /settings/members|billing|integrations
│   ├── (public)/             # Route group — no auth required
│   │   └── share/
│   │       └── [token]/
│   │           └── page.tsx   # /share/{token} (RSC; calls public API)
│   ├── globals.css            # Tailwind v4 @import + shadcn CSS vars
│   └── layout.tsx             # Root layout (html/body only — no ClerkProvider here)
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx        # Fixed sidebar with nav + Clerk components
│   │   └── TopBar.tsx         # Breadcrumbs + page action slot
│   ├── scans/
│   │   ├── ScanTable.tsx      # 'use client' — sortable table with filter state
│   │   ├── ScanFilters.tsx    # 'use client' — filter bar (debounced inputs)
│   │   ├── ScanDetailHeader.tsx  # Header strip
│   │   └── ComparePickerModal.tsx # 'use client' — shadcn Dialog
│   ├── compare/
│   │   ├── DiffSummaryStrip.tsx
│   │   ├── DiffSection.tsx    # 'use client' — expandable rows
│   │   └── DrillDownDrawer.tsx # 'use client' — shadcn Sheet + viewer
│   ├── share/
│   │   ├── ShareModal.tsx     # 'use client' — shadcn Dialog (create + list links)
│   │   ├── ShareLanding.tsx   # Public landing with viewer
│   │   └── PasswordGate.tsx   # 'use client' — password form
│   ├── home/
│   │   ├── LatestScanCard.tsx
│   │   ├── Sparkline.tsx      # 'use client' — handrolled SVG
│   │   └── TopCriticalFindings.tsx
│   └── ui/                    # shadcn generated components (button, dialog, etc.)
├── lib/
│   ├── api.ts                 # Typed fetch helpers — getToken() + fetch /v1/*
│   ├── types.ts               # TypeScript types for API responses (ScanListItem, ResourceDiff, etc.)
│   └── utils.ts               # cn() from shadcn + date formatting helpers
├── middleware.ts              # clerkMiddleware + createRouteMatcher
├── next.config.ts
├── package.json               # name: "infracanvas-dashboard"
└── tsconfig.json              # strict, ES2020, paths: {"@/*": ["./app/*", "./components/*", "./lib/*"]}
```

### Pattern 1: RSC Data Fetching with Clerk JWT Forwarding
**What:** Server Component calls backend API by getting the Clerk JWT server-side and passing it as Bearer.
**When to use:** Every authenticated RSC that needs backend data.
**Example:**
```typescript
// Source: Context7 /clerk/clerk-docs — auth() server component pattern
// dashboard/lib/api.ts
import { auth } from '@clerk/nextjs/server'

export async function backendFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const { getToken } = await auth()
  const token = await getToken()
  const res = await fetch(`${process.env.BACKEND_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    cache: 'no-store',   // Per-user data — never cache on Vercel
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}

// Usage in a page RSC:
// const scans = await backendFetch<ScanListResp>('/v1/scans?limit=25&page=...')
```

### Pattern 2: Clerk Middleware with Public Share Route
**What:** `clerkMiddleware` gates all routes EXCEPT the `/share/*` public landing.
**When to use:** middleware.ts — single configuration point.
**Example:**
```typescript
// Source: Context7 /clerk/clerk-docs — createRouteMatcher + clerkMiddleware
// dashboard/middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher([
  '/share(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
])

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
```

### Pattern 3: Viewer Client Component Wrapper
**What:** `@infracanvas/viewer` components are marked `'use client'` at the package level (Phase 5 D-13). Wrap in Suspense for loading state.
**When to use:** `/scans/{id}`, `/compare/{from}/{to}` drill-down, `/share/{token}`.
**Example:**
```typescript
// Source: Phase 5 05-CONTEXT.md D-13 + Context7 /vercel/next.js streaming
// dashboard/components/scans/ScanViewer.tsx
'use client'
import { ViewerProvider, DiagramCanvas } from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph } from '@infracanvas/viewer'

interface Props { scan: ResourceGraph }

export function ScanViewer({ scan }: Props) {
  return (
    <ViewerProvider scan={scan}>
      <DiagramCanvas />
    </ViewerProvider>
  )
}

// In page.tsx (RSC):
// const { presigned_get_url } = await backendFetch<ScanGetResp>(`/v1/scans/${id}`)
// const scan: ResourceGraph = await fetch(presigned_get_url).then(r => r.json())
// return <Suspense fallback={<ScanSkeleton />}><ScanViewer scan={scan} /></Suspense>
```

### Pattern 4: URL Search Params → Backend Filters (Scan List)
**What:** Filter state lives in URL searchParams (bookmarkable, shareable). RSC reads `searchParams`, constructs backend query, no client round-trip.
**When to use:** `/scans` page filter bar.
**Example:**
```typescript
// Source: Context7 /vercel/next.js — searchParams in page component
// dashboard/app/(dashboard)/scans/page.tsx (RSC)
export default async function ScansPage({
  searchParams,
}: {
  searchParams: Promise<{ branch?: string; source?: string; from?: string; to?: string; score_lt?: string; page?: string; sort?: string; order?: string }>
}) {
  const sp = await searchParams
  const qs = new URLSearchParams()
  if (sp.branch) qs.set('branch', sp.branch)
  if (sp.source) qs.set('source', sp.source)
  if (sp.from) qs.set('created_after', sp.from)
  if (sp.to) qs.set('created_before', sp.to)
  if (sp.score_lt) qs.set('score_lt', sp.score_lt)
  if (sp.page) qs.set('cursor', sp.page)
  if (sp.sort) qs.set('sort', sp.sort)
  if (sp.order) qs.set('order', sp.order)
  qs.set('limit', '25')
  const data = await backendFetch<ScanListResp>(`/v1/scans?${qs}`)
  return <ScanTable data={data} />
}
// ScanTable is 'use client' — handles debounced filter input + router.push for URL update
```

### Anti-Patterns to Avoid
- **Proxy scan bytes through Vercel:** Dashboard must fetch the R2 presigned URL client-side. Routing the 25 MB blob through Vercel burns bandwidth budget and adds latency. D-08 locked.
- **Sharing Clerk ClerkProvider with landing/:** `landing/` and `dashboard/` are separate apps with separate Clerk instances (dev vs prod). Merging them would break D-14 (Phase 6) env topology.
- **Module-level Zustand singleton in dashboard:** `@infracanvas/viewer` uses `createViewerStore()` factory (Phase 5 D-11). Each page with a viewer wraps in `<ViewerProvider>` — do not import a singleton `store.ts` from the viewer pkg.
- **Caching backend fetch responses:** Dashboard data is per-user, per-org. All `fetch()` calls to `/v1/*` must use `cache: 'no-store'`. Accidentally cached RSC responses serve another team's scan data.
- **Showing scan metadata before password verification:** The password gate page must show zero scan metadata (team name, commit SHA, findings). Only return metadata from `POST /v1/share-links/{token}/unlock` after bcrypt verify passes.
- **Storing raw share-link tokens or passwords:** Tokens and passwords are both stored bcrypt-hashed in the `share_links` table. The raw token is returned once at creation (client stores it); subsequent lookups hash-compare.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Team switcher UI | Custom org switcher dropdown | Clerk `<OrganizationSwitcher/>` | Handles invite-pending, create-org, switch-org; org Clerk component has accessible implementation |
| Members management UI | Custom invite/remove flow | Clerk `<OrganizationProfile/>` | Full invitation lifecycle, role management, remove member — all in one prebuilt component |
| Modal / Dialog primitives | Custom modal with focus-trap | shadcn `<Dialog/>` + `<AlertDialog/>` (Radix primitive) | Accessible focus management, Esc handling, aria-modal; non-trivial to build correctly |
| Date-range picker | Custom calendar component | shadcn `<Calendar/>` + `<Popover/>` (react-day-picker) | Date navigation edge cases (DST, locale, range selection overlap) |
| bcrypt hashing | Custom token hashing (SHA-256 unkeyed) | `bcrypt` Python library | Unkeyed SHA-256 is brute-forceable; bcrypt has adaptive cost factor and built-in salting |
| Sortable table headers | Custom sort state + th click | shadcn `<Table/>` + URL searchParam sort state | URL state is bookmarkable; shadcn table gives correct `aria-sort` semantics |
| Toast notifications | Custom notification stack | shadcn `<Sonner/>` / `<Toaster/>` | Manages auto-dismiss, persistence, stacking, screen-reader announcements |
| Diagram rendering | Custom D3 graph renderer | `<DiagramCanvas/>` from `@infracanvas/viewer` | Phase 5 complete; drift overlay coloring, filter panel, detail panel all pre-built |

**Key insight:** The viewer package is the single highest-value reuse. Every diagram surface (scan detail, compare drill-down, share landing) mounts `<ViewerProvider><DiagramCanvas/></ViewerProvider>` — no reimplementation of layout, grouping, or finding overlays.

---

## Backend API Contract Verification

### CONFIRMED: What Phase 6 Shipped

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /v1/scans` | CONFIRMED [VERIFIED: scans.py L98] | Returns `{scan_id, presigned_put_url, expires_at}` |
| `POST /v1/scans/{id}/commit` | CONFIRMED [VERIFIED: scans.py L129] | Returns `ScanGetResp` |
| `GET /v1/scans/{id}` | CONFIRMED [VERIFIED: scans.py L276] | Returns `ScanGetResp` — `{id, team_id, status, presigned_get_url (300s TTL), size_bytes, created_at, summary_json}` |
| `GET /v1/scans` (list) | MISSING | Not implemented — no route exists |
| `GET /v1/scans/{a}/compare/{b}` | MISSING | Not implemented |
| `POST /v1/scans/{id}/share-links` | MISSING | Not implemented |
| `GET /v1/share-links/{token}` | MISSING | Not implemented |
| `POST /v1/share-links/{token}/unlock` | MISSING | Not implemented |
| `DELETE /v1/scans/{id}/share-links/{share_id}` | MISSING | Not implemented |

### CONFIRMED: presigned_get_url TTL
`_GET_TTL_SECONDS = 300` [VERIFIED: scans.py L73]. Matches D-08 "≤300s TTL". The dashboard's client-side fetch of the JSON from R2 must happen before 300 seconds elapses from when `GET /v1/scans/{id}` was called. A user who leaves the scan-detail page open for >5 minutes and then loads the diagram will see a 403 from R2. The plan should include a refresh-on-error pattern: if R2 returns 403/4xx, re-call `GET /v1/scans/{id}` to get a fresh URL.

### CRITICAL GAP: Scan metadata columns missing
The `scans` table has: `id`, `team_id`, `r2_key`, `sha256` (sha256 of blob, not git sha), `size_bytes`, `status`, `summary_json`, `created_at`. [VERIFIED: models.py + 001_initial_schema.py]

`summary_json` contains: `total_resources`, `findings` (per-severity counts), `estimated_monthly_cost`, `score`, `drift` (per-drift-state counts). [VERIFIED: GraphSummary model in cli/infracanvas/graph/models.py]

**Missing from scans table:** `branch`, `commit_sha` (7-char git sha), `source` (CLI/manual/github-webhook). These are required by D-05 (scan-list columns) and D-07 (scan-detail header strip).

The Phase 7 plan MUST include:
1. Alembic migration adding `branch` (String, nullable), `commit_sha` (String(40), nullable), `source` (Enum/String, nullable) to `scans` table.
2. Extension of `ScanCommitReq` or `ScanCreateReq` to accept these fields from CLI.
3. Extension of `ScanGetResp` and new `ScanListItemResp` to return them.

### CONFIRMED: summary_json shape for scan-list rendering
`summary_json.findings.critical`, `summary_json.findings.high`, `summary_json.score`, `summary_json.drift` are all available once the indexing worker completes. The list endpoint can read these directly from the DB column (no R2 read at list time).

### CONFIRMED: R2 get_bytes for diff computation
`r2.get_bytes(key)` exists [VERIFIED: r2.py L97-L104]. The compare endpoint can call this for both scan keys, parse `ResourceGraph`, and compute the diff in Python.

### CONFIRMED: Alembic migration patterns for RLS
Migration `002_rls_setup.py` established the pattern: `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY ... USING (team_id = current_setting('app.current_team_id', true)::uuid)`. The `share_links` table follows this pattern. [VERIFIED: 002_rls_setup.py]

**share_links RLS design:** Share-link reads by authenticated team members → team-scoped (same pattern as scans). Public reads (`GET /v1/share-links/{token}`) and public unlock (`POST /v1/share-links/{token}/unlock`) run WITHOUT a team GUC — they must use a SECURITY DEFINER function (like the existing `team_by_clerk_org` function in migration 003) or a deliberately permissive SELECT policy on `token_hash` only. The public endpoint should use `infracanvas_app` role with a policy that allows SELECT by `token_hash` match without requiring `app.current_team_id` to be set.

### CONFIRMED: bcrypt not in backend venv
`bcrypt` and `passlib` are not installed in the backend venv [VERIFIED: venv check]. Must be added to `backend/pyproject.toml` `dependencies`. Recommended: `bcrypt>=4.0,<5` (pure Python binding, widely used, well-maintained). [VERIFIED: npm/pypi — bcrypt 4.x is current]

---

## Common Pitfalls

### Pitfall 1: Next.js 15 searchParams is a Promise
**What goes wrong:** In Next.js 15, `searchParams` and `params` in page components are Promises, not plain objects. Code written as `params.id` throws "params is a Promise" at runtime.
**Why it happens:** Next.js 15 changed these props to be async-compatible for streaming.
**How to avoid:** Always `await params` and `await searchParams` before destructuring.
```typescript
// Source: Context7 /vercel/next.js — page.js API reference
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ branch?: string }>
}) {
  const { id } = await params
  const { branch } = await searchParams
  // ...
}
```
**Warning signs:** `TypeError: params.id is undefined` or `params.then is not a function`.

### Pitfall 2: R2 presigned URL expires before viewer mounts
**What goes wrong:** `GET /v1/scans/{id}` is called during RSC render. The presigned URL is embedded in the HTML. By the time JS hydrates and the client component fetches it, >300s may have passed (slow network, tab in background).
**Why it happens:** 300s TTL is correct for security but creates a race on slow clients.
**How to avoid:** Fetch the presigned URL in a client component (not the RSC), immediately before fetching the blob. Pattern: RSC passes only `scan_id` to the client component; the client component calls `GET /v1/scans/{scan_id}` on mount to get a fresh URL, then fetches R2. Add a retry: if R2 returns 403, re-call `/v1/scans/{id}` for a new presigned URL.
**Warning signs:** R2 `403 Forbidden` errors in browser console after the page has been open for a few minutes.

### Pitfall 3: Clerk `auth()` called outside ClerkProvider in layout
**What goes wrong:** `auth()` in a Server Component returns null/throws if the route is outside the `<ClerkProvider>` wrapper. On the public `/share/{token}` route, `auth()` should not be called at all.
**Why it happens:** Route groups that share a layout with `<ClerkProvider>` will have auth; routes outside that group will not.
**How to avoid:** Use two route groups: `(dashboard)` with `<ClerkProvider>` in its `layout.tsx`, and `(public)` with no Clerk wrapper. Never call `auth()` in the public group's RSC.
**Warning signs:** `ClerkProvider was not found in your component tree.` error on the share landing page.

### Pitfall 4: Workspace link to @infracanvas/viewer requires build first
**What goes wrong:** `dashboard/` imports `@infracanvas/viewer` from the workspace, but `viewer/dist/lib/` doesn't exist or is stale. TypeScript build fails with "Cannot find module '@infracanvas/viewer'".
**Why it happens:** Workspace links resolve to the `dist/lib/` path declared in viewer/package.json `"main"` and `"exports"`, not the source.
**How to avoid:** Wave 0 of the plan must include `cd viewer && npm run build` to verify the dist is fresh. The root `package.json` should add a `"build:viewer"` script. In CI, always build viewer before dashboard.
**Warning signs:** `Module not found: Can't resolve '@infracanvas/viewer'` in dashboard build.

### Pitfall 5: Tailwind v4 does not use tailwind.config.js
**What goes wrong:** Developers familiar with Tailwind v3 create a `tailwind.config.js` in dashboard/. Tailwind v4 ignores it. Custom theme tokens (amber-400 etc.) are not applied.
**Why it happens:** Tailwind v4 uses `@theme {}` blocks in CSS (like `viewer/src/lib-styles.css`). Config JS file is v3 syntax.
**How to avoid:** Dashboard defines custom tokens in `app/globals.css` using `@theme {}`. Import `@infracanvas/viewer/styles.css` BEFORE the dashboard's own globals to ensure viewer tokens (sev-critical etc.) are available as utility classes.
**Warning signs:** Custom color classes like `bg-amber-400` work; but `text-sev-critical` does nothing.

### Pitfall 6: share_links public SELECT policy allows cross-team token lookup
**What goes wrong:** A malicious user enumerates token hashes. If the SELECT policy on `share_links` allows unrestricted SELECT for `GET /v1/share-links/{token}`, an attacker could time-diff requests to determine which token hashes exist.
**Why it happens:** The public endpoint must SELECT by token_hash without a team GUC. Naive implementation opens the whole table to public read.
**How to avoid:** The lookup should be via a SECURITY DEFINER function (like `team_by_clerk_org`) that accepts a token_hash and returns ONLY the columns needed for the public response (no team_id, no internal metadata). The function's body runs as the migrator role, which is not subject to RLS. The GRANT allows only `EXECUTE` for `infracanvas_app` on this function.
**Warning signs:** Any SELECT policy on `share_links` with `USING (true)` or `USING (token_hash = $1)` without function-level isolation.

### Pitfall 7: Compare endpoint reads two 25 MB files synchronously
**What goes wrong:** `GET /v1/scans/{a}/compare/{b}` calls `r2.get_bytes` twice sequentially. For large scans, this blocks the asyncio event loop for 2-3 seconds each.
**Why it happens:** `r2.get_bytes` is a blocking boto3 call; scans.py wraps it in `run_in_threadpool` but naively sequential double-call doubles the wait.
**How to avoid:** Use `asyncio.gather` with two `run_in_threadpool(r2.get_bytes, key)` calls to fetch both scan blobs concurrently. This matches the pattern already established in `indexing.py` (uses `asyncio.to_thread`).
**Warning signs:** P95 compare endpoint latency > 5s on large scans.

---

## Code Examples

### Backend: `GET /v1/scans` List Endpoint Pattern
```python
# Source: Based on Phase 6 scans.py established pattern
# backend/app/routes/scans.py (addition)
@router.get("", response_model=ScanListResp)
async def list_scans(
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None),  # UUIDv7 cursor for keyset pagination
    branch: str | None = Query(default=None),
    source: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    score_lt: int | None = Query(default=None, ge=0, le=100),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    principal: ClerkPrincipal = Depends(require_role("owner", "admin", "member", "basic_member")),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ScanListResp:
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            q = select(Scan).where(Scan.status == ScanStatus.ready)
            if cursor:
                q = q.where(Scan.id < uuid.UUID(cursor))  # keyset by UUIDv7
            if branch:
                q = q.where(Scan.branch == branch)
            if source:
                q = q.where(Scan.source == source)
            if created_after:
                q = q.where(Scan.created_at >= created_after)
            if created_before:
                q = q.where(Scan.created_at <= created_before)
            if score_lt is not None:
                q = q.where(
                    Scan.summary_json["score"].as_integer() < score_lt
                )
            q = q.order_by(Scan.created_at.desc()).limit(limit + 1)
            rows = (await session.execute(q)).scalars().all()
            has_more = len(rows) > limit
            items = rows[:limit]
            next_cursor = str(items[-1].id) if has_more and items else None
            return ScanListResp(
                items=[ScanListItemResp.from_orm(r) for r in items],
                next_cursor=next_cursor,
                total=None,  # avoid COUNT(*) on large tables
            )
```

### Backend: `share_links` Table Migration Pattern
```python
# Source: Based on Phase 6 002_rls_setup.py migration pattern
# migrations/versions/20260428_005_share_links.py (new)
def upgrade() -> None:
    op.create_table("share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),  # bcrypt hash of raw token
        sa.Column("password_hash", sa.String(255), nullable=True),  # bcrypt hash or NULL
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),  # NULL = never
        sa.Column("created_by", sa.String(64), nullable=False),  # Clerk user_id
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("share_links_token_hash_key", "share_links", ["token_hash"])
    op.create_index("ix_share_links_team_id", "share_links", ["team_id"])
    op.create_index("ix_share_links_scan_id", "share_links", ["scan_id"])
    op.create_index("ix_share_links_expires_at", "share_links", ["expires_at"])
    # RLS
    op.execute("ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE share_links FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY share_links_team_isolation ON share_links
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
    """)
    # SECURITY DEFINER function for public token lookup (bypasses RLS)
    op.execute("""
        CREATE OR REPLACE FUNCTION share_link_by_token_hash(p_hash text)
        RETURNS share_links LANGUAGE sql SECURITY DEFINER AS $$
          SELECT * FROM share_links WHERE token_hash = p_hash LIMIT 1;
        $$;
        REVOKE ALL ON FUNCTION share_link_by_token_hash(text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION share_link_by_token_hash(text) TO infracanvas_app;
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON share_links TO infracanvas_app;")
```

### Frontend: Auth-guarded backendFetch with X-Request-ID forwarding
```typescript
// Source: Phase 6 D-21 X-Request-ID pattern + Context7 Clerk auth()
// dashboard/lib/api.ts
import { auth } from '@clerk/nextjs/server'
import { headers } from 'next/headers'

export async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { getToken } = await auth()
  const token = await getToken()
  const hdrs = await headers()
  const requestId = hdrs.get('x-request-id') ?? crypto.randomUUID()

  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Request-ID': requestId,
      ...init?.headers,
    },
    cache: 'no-store',
  })

  if (res.status === 401) throw new AuthError(res)
  if (res.status === 404) throw new NotFoundError(res)
  if (res.status >= 500) throw new ServerError(res, requestId)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js 14 fetch cached by default | Next.js 15 fetch NOT cached by default | Next.js 15.0 (2024) | Dashboard must NOT add `cache: 'force-cache'` — default is already `no-store`, correct for per-user data |
| `params` as plain object in page props | `params` as Promise in Next.js 15 | Next.js 15.0 | Must `await params` everywhere |
| Tailwind config in `tailwind.config.js` | Tailwind v4 CSS-first config in `@theme {}` | Tailwind v4 (2025) | No `tailwind.config.js` needed; theme tokens go in CSS |
| Clerk `withAuth()` HOC / `getAuth()` | `auth()` async function + `clerkMiddleware()` | @clerk/nextjs v5+ | Current pattern confirmed in Context7; old HOC deprecated |

**Deprecated/outdated:**
- `withAuth` HOC: replaced by `clerkMiddleware` + `auth()` — do not use.
- `getAuth(req)` in API routes: replaced by `auth()` imported from `@clerk/nextjs/server`.
- `next/font` local font loading: use `next/font/google` for Inter + JetBrains Mono (zero-config, preloaded).

---

## Runtime State Inventory

> Phase 7 is greenfield for the dashboard. No rename/refactor involved.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Neon `scans` table rows exist in dev env (Phase 6 test data) | Phase 7 migration adds nullable columns — no data migration; existing rows get NULL for branch/commit_sha/source |
| Live service config | Backend Fly.io CORS env (`CLERK_ALLOWED_ORIGINS`) needs dashboard hostnames | Add `https://app.infracanvas.dev` (prod) + Vercel preview pattern to CSV env var — documented in plan, done at deploy time |
| OS-registered state | None | None |
| Secrets/env vars | Backend: no new secrets needed beyond Phase 6 set. Dashboard: needs `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` — new Vercel env vars | Add to Vercel dashboard (prod + preview envs) |
| Build artifacts | `viewer/dist/lib/` — must be current before dashboard can build | Wave 0 task: `cd viewer && npm run build` to confirm dist is fresh; add `"build:viewer"` to root package.json |

---

## Open Questions

1. **Where do `branch`, `commit_sha`, `source` come from at upload time?**
   - What we know: `ScanCommitReq` currently only accepts `sha256` (blob hash, not git SHA). The CLI runs `infracanvas scan ./terraform` — it does not currently pass git metadata.
   - What's unclear: Does the CLI know the git branch/commit at scan time? Phase 5.1 (parser realism) may have added this. The `ResourceGraph.metadata` is `dict[str, object]` — the CLI may already embed `commit_sha` there.
   - Recommendation: Check `cli/infracanvas/main.py` for any `git` subprocess call or metadata population. If not present, the plan should add `branch` + `commit_sha` + `source` as OPTIONAL fields to `ScanCommitReq` (nullable, CLI-supplied on commit). The scan-list UI can display "—" for scans uploaded without this metadata.

2. **What is the ResourceDiff response shape for the compare endpoint?**
   - What we know: D-11 says the endpoint returns `added[]`, `removed[]`, `changed[]` (with per-attribute deltas), `findings_delta` per severity. The viewer's existing `DriftStatus` type (`added | changed | deleted | unchanged | shadow`) matches.
   - What's unclear: Whether `AttributeChange` from `viewer/src/types.ts` is the right shape for the `changed[].deltas` sub-array, or if a new `ResourceDiff` Pydantic model is needed.
   - Recommendation: Define `ResourceDiff` in `backend/app/schemas/compare.py` with `added: list[str]` (resource IDs), `removed: list[str]`, `changed: list[ResourceAttrDiff]` where `ResourceAttrDiff = {id: str, deltas: list[{attr: str, before: Any, after: Any}]}`, `findings_delta: dict[str, int]`. Mirror the `AttributeChange` type from `viewer/src/types.ts`.

3. **Does `ViewerProvider` accept a `readOnly` prop?**
   - What we know: Phase 5 D-04 says all components are exported. The `StoreState` type is exported. The viewer's FilterPanel + DetailPanel are read-only in nature (they explore, not edit). D-14 says share landing is "read-only" — but the viewer pkg doesn't expose Compare/Share buttons anyway (those are dashboard chrome).
   - What's unclear: Whether `readOnly` is a prop that needs to be added to `ViewerProvider`, or whether "read-only" just means the dashboard doesn't add its own Compare/Share buttons on the share landing.
   - Recommendation: Based on current Phase 5 exports, `readOnly` is not a viewer prop — the viewer only renders diagrams and doesn't have Compare/Share UI of its own. No prop addition needed. The share landing just omits the dashboard's Compare/Share buttons.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js scaffold | ✓ | v25.8.2 | — |
| Python 3.12 | Backend | ✓ | 3.14.3 | — (3.14 is forward-compatible; backend targets >=3.12) |
| npm | Package install | ✓ | bundled with Node | — |
| viewer/dist/lib/ | dashboard import | ✓ | built | Wave 0 must verify freshness |
| bcrypt (Python) | share-link hashing | ✗ | — | Must add `bcrypt>=4.0,<5` to backend/pyproject.toml |
| backend/.venv | Backend dev | ✓ | present | — |
| Vercel CLI | Deployment | [ASSUMED] | — | Manual Vercel dashboard deploy |
| Neon DB (dev) | Backend | [ASSUMED] | Postgres 16 | — |
| R2 bucket (dev) | Scan storage | [ASSUMED] | — | — |

**Missing dependencies with no fallback:**
- `bcrypt` Python package — required for share-link token + password hashing. Must be added before share-link backend routes can be implemented.

**Missing dependencies with fallback:**
- None beyond bcrypt.

---

## Validation Architecture

> `workflow.nyquist_validation: true` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Frontend framework | Vitest 4.1.4 + @testing-library/react (already in viewer/; dashboard adds separately) |
| Backend framework | pytest 8.3.0 + pytest-asyncio (already in backend/pyproject.toml) |
| Frontend config file | `dashboard/vite.config.ts` (Wave 0 gap — does not exist yet) |
| Backend config file | `backend/pyproject.toml` [tool.pytest.ini_options] (exists) |
| Frontend quick run | `cd dashboard && npm test -- --run` |
| Backend quick run | `cd backend && python -m pytest tests/ -x -q --no-cov` |
| Full suite | `cd dashboard && npm test -- --run && cd ../backend && python -m pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DSH-02 | Next.js 15 app builds and renders root page | smoke | `cd dashboard && npm run build` | ❌ Wave 0 |
| DSH-03 | clerkMiddleware redirects unauthenticated to sign-in; /share bypasses auth | unit | `cd dashboard && npm test -- --run middleware.test.ts` | ❌ Wave 0 |
| DSH-04 | Scan list renders rows from mock API; detail page mounts viewer | integration | `cd dashboard && npm test -- --run scans.test.tsx` | ❌ Wave 0 |
| DSH-05 | Settings tabs render correct Clerk/Billing/Integrations content | unit | `cd dashboard && npm test -- --run settings.test.tsx` | ❌ Wave 0 |
| DSH-06 | Layout renders at 1440px without horizontal scroll | manual | n/a — browser resize check | manual |
| HST-01 | GET /v1/scans returns paginated list filtered by branch/source/date/score | integration (backend) | `cd backend && python -m pytest tests/test_scans_list.py -x` | ❌ Wave 0 |
| HST-02 | GET /v1/scans/{a}/compare/{b} returns ResourceDiff with added/removed/changed | integration (backend) | `cd backend && python -m pytest tests/test_compare.py -x` | ❌ Wave 0 |
| HST-03 | Scan-list table shows branch/commit_sha/source columns | integration (frontend) | `cd dashboard && npm test -- --run ScanTable.test.tsx` | ❌ Wave 0 |
| SHR-01 | POST share-link; GET returns 401+password_required; POST unlock with wrong pw returns error | integration (backend) | `cd backend && python -m pytest tests/test_share_links.py -x` | ❌ Wave 0 |
| SHR-02 | /share/{token} page renders viewer after successful unlock; expired link shows error card | integration (frontend) | `cd dashboard && npm test -- --run share.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q --no-cov` (backend tasks) or `cd dashboard && npm test -- --run` (frontend tasks)
- **Per wave merge:** full backend suite + dashboard build check
- **Phase gate:** Full backend pytest + dashboard build + manual 1440p layout review before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `dashboard/` — does not exist; scaffold required
- [ ] `dashboard/vite.config.ts` (or vitest.config.ts) — test runner config
- [ ] `dashboard/tests/` directory with test fixtures
- [ ] `backend/tests/test_scans_list.py` — covers HST-01
- [ ] `backend/tests/test_compare.py` — covers HST-02
- [ ] `backend/tests/test_share_links.py` — covers SHR-01
- [ ] Framework install for dashboard: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react`
- [ ] Alembic migration 005: `branch`, `commit_sha`, `source` columns + `share_links` table + SECURITY DEFINER function

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Clerk JWT validation — handled by `clerkMiddleware` + `auth()` in all authenticated RSC/routes |
| V3 Session Management | yes | Clerk session cookies managed by Clerk; dashboard does not manage sessions directly |
| V4 Access Control | yes | RLS (team isolation); `require_role()` FastAPI dep; 404 not 403 for cross-team |
| V5 Input Validation | yes | Pydantic v2 `strict=True, extra='forbid'` on all new request schemas; query param types via FastAPI `Query()` |
| V6 Cryptography | yes | bcrypt for share-link tokens + passwords; never SHA-256 unkeyed; never raw token storage |
| V7 Error Handling | yes | Public error messages must not leak scan metadata (D-15); 410 Gone for revoked links; structured error shapes |
| V13 API and Web Service | yes | CORS via `clerk_allowed_origins` CSV (Phase 6 D-17); presigned URL scoped to team key prefix |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-team scan ID guessing via share-link | Information Disclosure | 410/404 for revoked/unknown; no existence disclosure on wrong password; bcrypt token hashing prevents enumeration |
| Presigned URL forwarding (leaked URL) | Information Disclosure | ≤300s TTL limits leak window; URL is team-scoped in R2 key prefix |
| Share-link password brute force | Elevation of Privilege | bcrypt adaptive cost (work factor 12); no lockout needed (cost is sufficient) |
| CORS bypass from unauthorized origin | Spoofing | `clerk_allowed_origins` in backend settings; Vercel preview URLs must be added explicitly |
| JWT replay from expired session | Spoofing | Clerk handles JWT expiry; `clerkMiddleware` auto-validates on every request |
| Scan metadata leakage on password gate | Information Disclosure | `GET /v1/share-links/{token}` returns only `{password_required: true}` when gated — no scan fields |
| RLS bypass via public share_links SELECT | Elevation of Privilege | SECURITY DEFINER function for token lookup; no open SELECT policy on table |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `passlib[bcrypt]` vs raw `bcrypt` choice is planner discretion | Standard Stack | Low — both provide bcrypt; API differs slightly but both correct |
| A2 | Vercel CLI is available for deployment | Environment Availability | Low — Vercel dashboard deploy is an alternative; no code impact |
| A3 | CLI does not currently pass `branch`/`commit_sha` to `ScanCommitReq` | Open Questions #1 | Medium — if CLI already passes this in `ResourceGraph.metadata`, the plan approach changes (extract from metadata in indexing worker instead of adding to commit req) |
| A4 | `ViewerProvider` does not need a `readOnly` prop for the share landing | Open Questions #3 | Low — the share landing omits dashboard Compare/Share buttons; viewer itself has no editing capability |
| A5 | Neon dev DB is accessible from local dev environment | Environment Availability | Medium — if connection fails, backend tests that use testcontainers (already set up in backend pyproject.toml) are the fallback |
| A6 | Dashboard Vercel project does not yet exist | Runtime State Inventory | Low — creating a new Vercel project is a one-time manual step documented in the plan |

---

## Sources

### Primary (HIGH confidence)
- `backend/app/routes/scans.py` — confirmed all three existing routes; confirmed missing list + compare + share-link
- `backend/app/db/models.py` + `migrations/versions/20260424_001_initial_schema.py` — confirmed scans table schema; confirmed missing branch/commit_sha/source columns
- `backend/app/storage/r2.py` — confirmed `presigned_get` TTL=300s; confirmed `get_bytes` exists for diff computation
- `backend/app/schemas/scan.py` — confirmed `ScanGetResp` shape; confirmed no list/diff schemas exist
- `backend/pyproject.toml` — confirmed bcrypt/passlib not in dependencies
- `cli/infracanvas/graph/models.py` — confirmed `GraphSummary` fields available in `summary_json`
- `viewer/src/index.ts` — confirmed all exports: `DiagramCanvas`, `ViewerProvider`, `createViewerStore`, `useViewerStore`, all types
- `viewer/package.json` — confirmed `@infracanvas/viewer`, dist/lib/ path, exports map
- `viewer/src/lib-styles.css` — confirmed severity CSS tokens (sev-critical, sev-high, etc.)
- `landing/package.json` — confirmed `next: ^15.0.0`, `react: ^18.3.1`, `tailwindcss: ^4.1.0`
- `package.json` (root) — confirmed `workspaces: ["viewer"]`; dashboard must be added
- `backend/migrations/versions/20260424_002_rls_setup.py` — confirmed RLS migration pattern for share_links table
- Context7 `/clerk/clerk-docs` — `clerkMiddleware`, `createRouteMatcher`, `auth()`, `getToken()`, `OrganizationSwitcher` patterns verified
- Context7 `/vercel/next.js` — Next.js 15 `searchParams` as Promise, `cache: 'no-store'` default, Suspense/streaming patterns verified

### Secondary (MEDIUM confidence)
- npm registry: next@16.2.4 latest (landing locks to ^15.0.0); @clerk/nextjs@7.2.7; shadcn@4.5.0; react-day-picker@9.14.0 — all verified via `npm view`

### Tertiary (LOW confidence)
- bcrypt Python package choice (bcrypt>=4.0 vs passlib[bcrypt]) — planner discretion [ASSUMED A1]
- CLI git metadata behavior — not verified in this session [ASSUMED A3]

---

## Metadata

**Confidence breakdown:**
- Backend API contract: HIGH — read directly from source files
- Viewer package contract: HIGH — read index.ts, package.json, dist/lib confirmed built
- Next.js 15 + Clerk patterns: HIGH — verified from Context7 (official docs)
- Standard stack versions: HIGH — verified via npm view
- Missing columns / endpoints gap analysis: HIGH — read actual migration files and route files

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable libraries; Next.js and Clerk update frequently, re-verify if >30 days)
