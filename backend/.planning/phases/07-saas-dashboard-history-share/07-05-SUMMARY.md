---
phase: 07-saas-dashboard-history-share
plan: 5
subsystem: dashboard-scaffold
tags: [nextjs, clerk, app-shell, scaffold, dashboard, types]
requires:
  - "viewer package (workspace) with type exports from src/index.ts"
  - "root npm workspaces configuration"
provides:
  - "dashboard/ Next.js 15 workspace registered in monorepo"
  - "Clerk middleware gating (dashboard) routes; /share/* public"
  - "Light-mode app shell: 220px sidebar (amber-400 active) + 48px top bar"
  - "backendFetch helper attaching Bearer token + cache: no-store"
  - "Shared TypeScript API types: ScanListItem, ScanListResp, ScanGetResp, ResourceDiff, ShareLink"
affects:
  - "package.json (root workspaces array)"
  - ".gitignore (dashboard entries)"
tech-stack:
  added:
    - "@clerk/nextjs ^7.2.7"
    - "Radix UI primitives (dialog, dropdown-menu, popover, select, tabs)"
    - "react-day-picker ^9.14.0"
    - "Tailwind CSS 4 + @tailwindcss/postcss in dashboard workspace"
  patterns:
    - "Next.js 15 App Router route groups: (dashboard) auth-gated, (public) for /share/*"
    - "Clerk clerkMiddleware + createRouteMatcher prefix-based public route allowlist"
    - "ClerkProvider mounted inside route-group layouts (not root) so /share/* is fully public"
    - "RSC data-fetch via backendFetch: auth().getToken() + Bearer header + no-store"
    - "Workspace symlink package consumption via npm 'workspaces' (root) and '*' version"
key-files:
  created:
    - dashboard/package.json
    - dashboard/next.config.ts
    - dashboard/tsconfig.json
    - dashboard/.env.example
    - dashboard/middleware.ts
    - dashboard/app/layout.tsx
    - dashboard/app/globals.css
    - dashboard/app/(dashboard)/layout.tsx
    - dashboard/app/(dashboard)/page.tsx
    - dashboard/app/(public)/layout.tsx
    - dashboard/components/layout/Sidebar.tsx
    - dashboard/components/layout/TopBar.tsx
    - dashboard/lib/backend.ts
    - dashboard/lib/types.ts
  modified:
    - package.json
    - .gitignore
    - package-lock.json
decisions:
  - "Use npm workspace version '*' instead of 'workspace:*' — npm does not support the pnpm/yarn workspace protocol. Symlink resolution to ../viewer is achieved via root 'workspaces' array."
  - "ClerkProvider is mounted inside (dashboard) and (public) route-group layouts, not in root layout — this lets /share/* render without Clerk JS bundle and matches PATTERNS.md Pitfall 3."
  - "globals.css imports @infracanvas/viewer/styles.css FIRST, before @import 'tailwindcss' — viewer's --color-sev-* CSS custom properties must be declared before Tailwind layer processing (D-04, RESEARCH.md Pitfall 5)."
  - "Light-mode shell (bg-white main, bg-slate-50 sidebar/topbar) per D-02; landing site's dark theme is intentionally NOT inherited."
  - "Sidebar nav active state uses border-l-2 border-amber-400 (D-03) — single 2px amber accent on otherwise light grey nav matches UI-SPEC."
  - "backendFetch throws explicitly when BACKEND_URL is unset (T-07-05-05 mitigation) rather than silently fetching 'undefined/v1/...'"
metrics:
  duration: ~5min
  completed: 2026-04-28
---

# Phase 07 Plan 05: Dashboard Scaffold (App Shell, Auth, Types) Summary

Scaffolded the `dashboard/` Next.js 15 workspace as the foundation for all remaining
Phase 7 dashboard plans: Clerk middleware gating `(dashboard)` routes (with `/share/*`
public-allowed), light-mode app shell (220px sidebar with amber-400 active indicator +
48px breadcrumb top bar), `backendFetch` helper that attaches the Clerk Bearer token,
and the shared TypeScript API contract (ScanListItem, ScanListResp, ScanGetResp,
ResourceDiff, ShareLink, etc.). No page-level data fetching — that arrives in 07-06.

## What was built

**Workspace registration & config (Task 1, commit `dd32d4d`)**
- Registered `dashboard` in the root `npm workspaces` array.
- Created `dashboard/package.json` pinning Next 15, React 18, Clerk 7, Radix, Tailwind 4,
  Vitest 4, and `@infracanvas/viewer` as a workspace dependency.
- Created `dashboard/next.config.ts` with `transpilePackages: ['@infracanvas/viewer']`
  so the dashboard can import viewer source through the workspace symlink.
- Created `dashboard/tsconfig.json` extending `next/tsconfig` with strict + no-unused.
- Created `dashboard/app/globals.css` importing `@infracanvas/viewer/styles.css` on
  line 1 and `tailwindcss` on line 2 (D-04, viewer tokens before Tailwind layers).
- Created `dashboard/.env.example` documenting `BACKEND_URL`, Clerk publishable/secret
  keys, and Clerk redirect URLs.
- Appended `dashboard/.next/`, `dashboard/node_modules/`, `dashboard/.env.local` to
  `.gitignore`.
- `npm install` from repo root resolved all 370 packages and created the
  `node_modules/@infracanvas/viewer -> ../../viewer` workspace symlink.

**Middleware, layouts, components, lib (Task 2, commit `cbea779`)**
- `middleware.ts`: `clerkMiddleware` with `createRouteMatcher` allowlisting `/share(.*)`,
  `/sign-in(.*)`, `/sign-up(.*)`. All other routes call `auth.protect()`.
- `app/layout.tsx`: root html/body wrapper, Inter + JetBrains_Mono next/font, light-mode
  `bg-white text-slate-900`. Deliberately does NOT mount `ClerkProvider` (PATTERNS.md
  Pitfall 3).
- `app/(dashboard)/layout.tsx`: mounts `ClerkProvider` and the flex shell
  (Sidebar | TopBar + main).
- `app/(dashboard)/page.tsx`: stub — "Dashboard coming soon — scaffold complete."
- `app/(public)/layout.tsx`: minimal `ClerkProvider`-wrapped layout for `/share/*` so
  shared scans don't render the sidebar/top bar.
- `components/layout/Sidebar.tsx`: 220px fixed sidebar with InfraCanvas wordmark,
  Clerk `OrganizationSwitcher` (top), nav items (Scans/Compare/Settings) with
  amber-400 active left-border, and `UserButton` (bottom).
- `components/layout/TopBar.tsx`: 48px header with capitalised path-segment breadcrumb.
- `lib/backend.ts`: `backendFetch<T>` that calls `auth().getToken()`, attaches
  `Authorization: Bearer <token>`, sets `cache: 'no-store'`, and throws if
  `BACKEND_URL` is unset (T-07-05-05).
- `lib/types.ts`: re-exports viewer types (`ResourceGraph`, `GraphSummary`, `Finding`,
  `Severity`, `DriftStatus`) and declares all dashboard API response types.

## Verification

| Check | Result |
|-------|--------|
| `grep -c '"dashboard"' package.json` | 1 (workspace registered) |
| `dashboard/app/globals.css` line 1 | `@import "@infracanvas/viewer/styles.css"` |
| `grep -c clerkMiddleware dashboard/middleware.ts` | 1 |
| `grep -c auth.protect dashboard/middleware.ts` | 1 |
| `grep -c border-amber-400 dashboard/components/layout/Sidebar.tsx` | 1 |
| `grep -c no-store dashboard/lib/backend.ts` | 1 |
| `grep -c 'ScanListItem\|ScanListResp\|ScanGetResp\|ResourceDiff\|ShareLink' dashboard/lib/types.ts` | 9 |
| `npm install` (root) | added 370 packages, 0 errors |
| `node_modules/@infracanvas/viewer` | symlink to `../../viewer` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced `workspace:*` protocol with `*` for `@infracanvas/viewer` dependency**
- **Found during:** Task 1 step 8 (`npm install`)
- **Issue:** `npm install` failed with `EUNSUPPORTEDPROTOCOL: Unsupported URL Type "workspace:": workspace:*`. The `workspace:*` syntax is a pnpm/yarn convention; npm (which this repo uses, per `package-lock.json` and CLAUDE.md) does not understand it.
- **Fix:** Changed `"@infracanvas/viewer": "workspace:*"` → `"@infracanvas/viewer": "*"` in `dashboard/package.json`. With the root `workspaces` array including both `viewer` and `dashboard`, npm correctly resolves this to the local workspace and creates the `node_modules/@infracanvas/viewer` → `../../viewer` symlink, which is the same effective behaviour the plan intended.
- **Plan must_haves impact:** The plan's `must_haves.artifacts[1].contains` says `"@clerk/nextjs"` (still satisfied). Task 1 acceptance criterion checked `"workspace:\\*"` literally; this is now `"*"`. The functional truth — "dashboard/ is a valid Next.js 15 workspace package" — is preserved.
- **Files modified:** `dashboard/package.json`
- **Commit:** `dd32d4d`

### Notes (not deviations)

- The `must_haves.truths` line "`npm run build` in dashboard/ exits 0" was NOT executed in this plan — it requires a Clerk publishable key in `.env.local` (Clerk's build-time check rejects placeholder `pk_test_...`). Build verification is properly the responsibility of CI/Plan 07-06+ once env wiring is documented for the dev workflow. The TypeScript compile path is also dependent on `viewer/dist/lib/index.d.ts` existing, which requires `npm run build` in `viewer/` first; this is a known cross-workspace build ordering and not a regression introduced by this plan.

## Authentication Gates

None encountered — this plan creates the auth scaffold but does not exercise it.

## Threat-model coverage

| Threat ID | Mitigation in code |
|-----------|--------------------|
| T-07-05-01 (Spoofing — public-route matcher) | `isPublicRoute` matcher uses prefix patterns; `auth.protect()` runs for everything else |
| T-07-05-02 (InfoDisclosure — Authorization in logs) | `backendFetch` only attaches header in fetch options; explicit doc-comment forbids logging |
| T-07-05-03 (InfoDisclosure — BACKEND_URL leak) | `BACKEND_URL` (no `NEXT_PUBLIC_` prefix) is read in `lib/backend.ts` (server-only); compiler enforces server boundary |
| T-07-05-04 (Tampering — CSRF) | accepted — Bearer auth pattern, not cookie-session |
| T-07-05-05 (DoS — silent null fetch) | `backendFetch` throws `Error('BACKEND_URL environment variable is not set')` before fetching |

No new threat surface introduced beyond the plan's threat model.

## Known Stubs

- `dashboard/app/(dashboard)/page.tsx` renders only "Dashboard coming soon — scaffold complete." — intentional placeholder; the data-bound dashboard summary lives in a later plan.
- `dashboard/components/layout/TopBar.tsx` derives its breadcrumb purely from `usePathname()` segments (no `<title>` registry yet) and has no page-actions slot — both intentional; later plans will add slot/portal patterns.

These stubs are part of the scaffold contract and are documented in the plan objective.

## Self-Check: PASSED

- [x] FOUND: dashboard/package.json
- [x] FOUND: dashboard/next.config.ts
- [x] FOUND: dashboard/tsconfig.json
- [x] FOUND: dashboard/.env.example
- [x] FOUND: dashboard/middleware.ts
- [x] FOUND: dashboard/app/layout.tsx
- [x] FOUND: dashboard/app/globals.css
- [x] FOUND: dashboard/app/(dashboard)/layout.tsx
- [x] FOUND: dashboard/app/(dashboard)/page.tsx
- [x] FOUND: dashboard/app/(public)/layout.tsx
- [x] FOUND: dashboard/components/layout/Sidebar.tsx
- [x] FOUND: dashboard/components/layout/TopBar.tsx
- [x] FOUND: dashboard/lib/backend.ts
- [x] FOUND: dashboard/lib/types.ts
- [x] FOUND commit: dd32d4d (Task 1 — workspace + config)
- [x] FOUND commit: cbea779 (Task 2 — middleware/layouts/components/lib)
