---
phase: 00-validation
plan: "01"
subsystem: landing
tags: [next.js, tailwind, landing-page, static-site, marketing]
dependency_graph:
  requires: []
  provides: [landing-page-scaffold, all-7-sections, stripe-cta, typeform-cta]
  affects: [00-02, 00-03]
tech_stack:
  added:
    - next@^15.0.0
    - tailwindcss@^4.1.0
    - "@tailwindcss/postcss@^4.1.0"
  patterns:
    - Next.js 15 App Router static export
    - Tailwind CSS v4 with postcss plugin
    - next/font/google for Inter with display swap
    - Metadata API with metadataBase for OG image resolution
key_files:
  created:
    - landing/package.json
    - landing/tsconfig.json
    - landing/next.config.ts
    - landing/postcss.config.mjs
    - landing/app/globals.css
    - landing/app/layout.tsx
    - landing/app/page.tsx
    - landing/components/Nav.tsx
    - landing/components/Hero.tsx
    - landing/components/DemoVideo.tsx
    - landing/components/ValueProps.tsx
    - landing/components/FoundingMember.tsx
    - landing/components/TypeformCTA.tsx
    - landing/components/Footer.tsx
    - landing/.env.example
    - landing/.gitignore
  modified: []
decisions:
  - "Used output: 'export' for static export with comment noting Vercel deployment can omit it"
  - "Stub Nav/Footer created for Task 1 build, then replaced with full implementations in Task 2"
  - "metadataBase set to https://infracanvas.dev to resolve OG image URL warning (Rule 2)"
  - "Inline SVGs used for value prop icons — no icon package installed per UI-SPEC registry safety"
metrics:
  duration_seconds: 252
  completed_date: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 16
  files_modified: 0
---

# Phase 00 Plan 01: Landing Page Scaffold and Components Summary

**One-liner:** Next.js 15 App Router static site with 7 locked-copy sections, env-var-driven Stripe+Typeform CTAs, and spot counter — builds to zero-warning static export.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold Next.js landing page project with layout and global styles | 457f7cf | package.json, tsconfig.json, next.config.ts, postcss.config.mjs, app/globals.css, app/layout.tsx, app/page.tsx (stub), components/Nav.tsx (stub), components/Footer.tsx (stub), .env.example, .gitignore |
| 2 | Implement all 7 landing page components and assemble page | 171fb60 | app/page.tsx, app/layout.tsx, components/Nav.tsx, components/Hero.tsx, components/DemoVideo.tsx, components/ValueProps.tsx, components/FoundingMember.tsx, components/TypeformCTA.tsx, components/Footer.tsx |

## Verification Results

- `npx next build` exits with code 0, zero warnings
- All 7 sections assembled in correct order in `app/page.tsx`
- `SPOTS_REMAINING = 50` constant defined at module level, passed as prop to Hero and FoundingMember
- All external CTAs use `process.env.NEXT_PUBLIC_*` — no hardcoded URLs
- `id="founding-member"` on FoundingMember section, Nav anchor links to it
- DemoVideo renders `<iframe>` when `embedUrl` truthy, fallback "Video coming soon" when falsy
- No `@radix-ui`, `framer-motion`, or `shadcn` packages in `package.json`
- Inter font loaded via `next/font/google` with `display: 'swap'`
- OG metadata and title match UI-SPEC SEO contract exactly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing correctness] Added metadataBase to layout metadata**
- **Found during:** Task 2 build verification
- **Issue:** Next.js emits `metadataBase not set` warning causing OG image URLs to resolve to `http://localhost:3000` in production
- **Fix:** Added `metadataBase: new URL('https://infracanvas.dev')` to the `Metadata` export in `layout.tsx`
- **Files modified:** `landing/app/layout.tsx`
- **Commit:** 171fb60

## Known Stubs

None — all components render real content. The `SPOTS_REMAINING = 50` constant and env-var placeholder values in `.env.example` are intentional — they are updated manually per the UI-SPEC pattern, not stubs preventing the plan's goal.

## Threat Flags

No new threat surface introduced beyond what is in the plan's threat model. All env vars use `NEXT_PUBLIC_` prefix (public URLs only, no secrets). No server-side routes, API endpoints, or auth paths added.

## Self-Check: PASSED

- [x] `landing/app/page.tsx` exists and contains `SPOTS_REMAINING`
- [x] `landing/app/layout.tsx` exists and contains `InfraCanvas — Your infrastructure, visualised`
- [x] `landing/components/FoundingMember.tsx` exists and contains `id="founding-member"`
- [x] `landing/components/Hero.tsx` exists and contains `5 tabs open. 0 clarity.`
- [x] Commit 457f7cf exists (Task 1 scaffold)
- [x] Commit 171fb60 exists (Task 2 components)
- [x] `npx next build` exits 0 with no warnings
