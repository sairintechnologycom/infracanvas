---
phase: 07-saas-dashboard-history-share
plan: 9
subsystem: dashboard-share-frontend
tags: [next-15, share-link, password-gate, react, vitest, security-D-09]
requires:
  - 07-04-share-backend (POST/GET/POST-unlock/DELETE under /v1/scans/.../share-links and /v1/share-links/...)
  - 07-05-dashboard-scaffold (backendFetch, (public) route group, NEXT_PUBLIC_BACKEND_URL)
  - 07-06-scans-list-page (ScoreGradePill UI pattern reused)
  - 07-07-scan-detail-page (ShareButton stub, fetchScanJson, ScanViewerClient pattern)
provides:
  - dashboard.components.share.ShareModal (creates a share link, copy-once UX)
  - dashboard.components.share.PasswordGate (gates protected links with zero pre-auth metadata)
  - dashboard.components.share.ShareViewer (full-bleed read-only viewer for share landing)
  - dashboard.routes.public./share/[token] (public RSC routing PasswordGate vs ShareViewer)
  - dashboard.routes.public./share (no-referrer meta + robots noindex)
  - dashboard.routes.api./api/scan-share (Clerk-authenticated proxy → backend share-link create)
affects:
  - dashboard.components.scans.ShareButton (stub replaced; now opens ShareModal via local useState)
  - dashboard.components.scans.ScanViewerClient (pre-existing Rule-1 bug fixed: ViewerProvider takes `store`, not `scan`)
  - dashboard.lib.types (Share* types now mirror backend/app/schemas/share.py 1:1)
  - dashboard.tsconfig.json (drops broken `extends: "next/tsconfig"` so vitest can run)
tech-stack:
  added: []
  patterns:
    - createViewerStore() + setGraph() factory pattern for embedding @infracanvas/viewer in dashboard pages
    - Next.js 15 async params (`const { token } = await params`)
    - Public RSC fetch without Clerk JWT (middleware already passes /share/* through)
    - D-09 / D-15 zero-metadata gate enforced both in JSX and via grep gate in acceptance tests
key-files:
  created:
    - dashboard/components/share/ShareModal.tsx
    - dashboard/components/share/PasswordGate.tsx
    - dashboard/components/share/ShareViewer.tsx
    - dashboard/app/(public)/share/layout.tsx
    - dashboard/app/(public)/share/[token]/page.tsx
    - dashboard/app/api/scan-share/route.ts
    - dashboard/__tests__/share-modal.test.tsx
    - dashboard/__tests__/password-gate.test.tsx
  modified:
    - dashboard/components/scans/ShareButton.tsx
    - dashboard/components/scans/ScanViewerClient.tsx
    - dashboard/lib/types.ts
    - dashboard/tsconfig.json
decisions:
  - Use `createViewerStore()` factory + `setGraph()` instead of a non-existent `<ViewerProvider scan={…}>` prop. This matches the actual @infracanvas/viewer API and produces an isolated store per share view (no cross-scan state bleed).
  - Token URL prefers `NEXT_PUBLIC_DASHBOARD_URL` env var (per plan must_haves) and falls back to the backend's canonical `share_url` when the env is unset. Backend-supplied URL stays the source of truth in dev.
  - The backend uses `expires_at` (ISO datetime) — the modal converts the user-friendly "1/7/30 days / Never" choice into an ISO datetime client-side, keeping the backend contract simple.
  - PasswordGate's only prop is `token`. After 200 from `/unlock`, the verified payload is forwarded verbatim to ShareViewer; no metadata is read or rendered in the gate's pre-unlock JSX.
  - Comments in PasswordGate.tsx use `//` line-comments (not `/** … */`) so the acceptance grep gate (which excludes only `//` lines) returns 0 metadata-name hits.
metrics:
  duration: ~22 min
  completed: 2026-04-28
---

# Phase 07 Plan 09: Share Subsystem Frontend Summary

End-to-end public share flow now ships in the SaaS dashboard: authenticated owners create
single-shot share links via the new ShareModal; recipients land on `/share/{token}` which
either reveals a branded full-bleed read-only viewer or a zero-metadata PasswordGate. Token
leakage via Referer is blocked at the layout level; rate limits surface as actionable
"Retry in N minutes" copy.

## What Was Built

| Layer | Component | Behavior |
|-------|-----------|----------|
| Modal | `dashboard/components/share/ShareModal.tsx` | Dialog with expiry select (1 / 7 / 30 days / Never with ⚠ warning), optional password, "Generate share link" CTA. After success: read-only URL input + copy button (`aria-label="Copy share link to clipboard"`). URL prefers `NEXT_PUBLIC_DASHBOARD_URL`. |
| Wire-up | `dashboard/components/scans/ShareButton.tsx` | Stub from 07-07 replaced; opens `<ShareModal />` via local `useState<boolean>`. |
| Proxy | `dashboard/app/api/scan-share/route.ts` | POST handler that revalidates the Clerk JWT via `backendFetch` and forwards to `POST /v1/scans/{id}/share-links`. Required because `backendFetch` is server-only. |
| Layout | `dashboard/app/(public)/share/layout.tsx` | `<meta name="referrer" content="no-referrer">` (T-07-09-02) + `robots: { index: false, follow: false }`. No sidebar/topbar chrome. |
| RSC | `dashboard/app/(public)/share/[token]/page.tsx` | Awaits Next 15 async params, fetches `GET /v1/share-links/{token}` (no auth header). Branches: `has_password=true` → `<PasswordGate token={token} />`; `has_password=false` → `<ShareViewer presignedUrl=… metadata=… />`. 410+detail=expired → "This share link has expired" card; 410+detail=revoked → "no longer active" card; 404 → "Share link not found" card; other → generic error. |
| Gate | `dashboard/components/share/PasswordGate.tsx` | Receives ONLY `token`. Heading "This scan is password-protected", password input, Unlock button, "Made with InfraCanvas" wordmark. Submits `POST /v1/share-links/{token}/unlock`. 200→mount ShareViewer; 401→"Incorrect password."; 410→"no longer active"; 429→"Too many attempts. Retry in N minutes." (parses `Retry-After`, disables input+button); other→generic. Enter key submits. |
| Viewer | `dashboard/components/share/ShareViewer.tsx` | `'use client'`. `useEffect` → `fetchScanJson(presignedUrl)` → `store.setGraph(graph)`. Branded top bar (team name placeholder, formatted timestamp, 7-char SHA, `ScoreGradePill`, `Nc / Nh` finding counts, "Made with InfraCanvas" wordmark). `<ViewerProvider store={store}><DiagramCanvas /></ViewerProvider>` fills the rest. On 403 surfaces actionable error (no auth path to refresh on the public URL). |
| Tests | `dashboard/__tests__/share-modal.test.tsx` (6 tests) | Title, default state, ⚠ warning toggle, password type, success → URL input + Copy button. |
| Tests | `dashboard/__tests__/password-gate.test.tsx` (8 tests) | D-09 zero-metadata, heading, input+button, testid, wordmark, 401, 429+Retry-After, 200→ShareViewer mount. |

## How It Wires Together

```
Authenticated user                       Recipient (unauthenticated)
─────────────────                       ─────────────────────────────

ShareButton ── click ──> ShareModal      Browser visits /share/{token}
                          │                       │
                          │ POST /api/scan-share  │ RSC fetches GET
                          │ (proxy)               │ /v1/share-links/{token}
                          v                       │
                  backendFetch (Clerk)            │
                          │                       v
                          │ POST /v1/scans/      [200 has_password=false]
                          │  {id}/share-links     │
                          v                       │
                  backend returns                 v
                  { token, share_url } ─once──> ShareViewer
                                                  │
                                                  │ fetchScanJson(R2)
                                                  │ ViewerProvider+DiagramCanvas
                                                  v
                                                user views read-only diagram

                                          [200 has_password=true]
                                                  │
                                                  v
                                                PasswordGate
                                                  │
                                                  │ POST /v1/share-links/
                                                  │ {token}/unlock
                                                  v
                                                ShareVerifyResp ─> ShareViewer
```

## Test Results

```
Test Files  4 passed (4)
     Tests  29 passed (29)
       Tsc  0 errors
```

29 = 7 (metadata-header + r2 retry, pre-existing) + 8 (scans-table, pre-existing) +
6 (share-modal, new) + 8 (password-gate, new).

## Verification Gate Results

| # | Gate | Result |
|---|------|--------|
| 1 | `grep -c 'no-referrer' app/(public)/share/layout.tsx` | 3 ≥ 1 ✓ |
| 2 | `grep -c 'await params' app/(public)/share/[token]/page.tsx` | 1 ✓ |
| 3 | `grep -c 'has_password' app/(public)/share/[token]/page.tsx` | 4 ≥ 2 ✓ |
| 4 | `grep -c 'PasswordGate' app/(public)/share/[token]/page.tsx` | 4 ≥ 1 ✓ |
| 5 | `grep -c 'ShareViewer' app/(public)/share/[token]/page.tsx` | 7 ≥ 1 ✓ |
| 6 | `grep -c 'data-testid="password-gate"' components/share/PasswordGate.tsx` | 1 ✓ |
| 7 | Pre-unlock metadata names in PasswordGate (non-comment lines) | 0 ✓ |
| 8 | `grep -c 'Retry-After' components/share/PasswordGate.tsx` | 2 ≥ 1 ✓ |
| 9 | `grep -c 'Generate share link' components/share/ShareModal.tsx` | 1 ✓ |
| 10 | `grep -c 'NEXT_PUBLIC_DASHBOARD_URL' components/share/ShareModal.tsx` | 2 ≥ 1 ✓ |
| 11 | `grep -c 'fetchScanJson' components/share/ShareViewer.tsx` | 3 ≥ 1 ✓ |
| 12 | `grep -c 'Made with' components/share/ShareViewer.tsx` | 1 ✓ |
| 13 | `grep -c 'Made with' components/share/PasswordGate.tsx` | 1 ✓ |
| 14 | `tsc --noEmit` errors | 0 ✓ |
| 15 | All vitest tests | 29/29 pass ✓ |

## Threat-Model Compliance

| ID | Disposition | Implementation |
|----|-------------|----------------|
| T-07-09-01 (Info Disclosure: pre-auth metadata) | mitigate | PasswordGate receives ONLY `token`. Pre-unlock JSX has zero metadata field references; enforced both by the test "renders no scan-metadata fields when has_password=true" and by the grep gate (0 occurrences). |
| T-07-09-02 (Token leakage via Referer) | mitigate | `share/layout.tsx` sets `referrer: 'no-referrer'` and `other: { referrer: 'no-referrer' }` (Next 15 metadata API), plus `robots: { index: false, follow: false }`. |
| T-07-09-03 (Brute-force via UI) | mitigate | Backend rate-limits 5/15min/IP. UI shows "Too many attempts. Retry in N minutes." parsed from `Retry-After` and disables input+button while `retryIn !== null`. |
| T-07-09-04 (Token in browser history) | accept | Documented in plan; same risk profile as presigned URLs. Mitigated by short TTL on revoke and 410 on revoked links. |
| T-07-09-05 (Forged scanId in POST) | mitigate | Frontend forwards the scanId as-received; backend RLS validates ownership (Plan 07-04). API proxy revalidates Clerk JWT before forwarding. |
| T-07-09-06 (Large scan JSON DoS) | accept | Bounded by Phase 6 D-11 25 MB ceiling; R2 CDN serves directly (D-08). |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Inlined `next/tsconfig` settings**
- **Found during:** Pre-Task-1 baseline verification
- **Issue:** `dashboard/tsconfig.json` extends `next/tsconfig`, which Next.js 15 no longer ships. `vitest` (and likely `tsc` via vite-tsconfck) failed to resolve, blocking every share-related test.
- **Fix:** Inlined the equivalent compilerOptions (`module: esnext`, `esModuleInterop`, `skipLibCheck`, `noEmit`, `allowJs`, `resolveJsonModule`, `isolatedModules`, `plugins: [{ name: 'next' }]`).
- **Files:** `dashboard/tsconfig.json`
- **Commit:** 85a0032

**2. [Rule 1 — Bug] `<ViewerProvider scan={graph}>` is invalid**
- **Found during:** Task 1 typecheck
- **Issue:** `ScanViewerClient` (from 07-07) and the initial draft of `ShareViewer` passed `<ViewerProvider scan={graph}>`. The actual `ViewerProvider` API exposes `{ store?: ViewerStoreApi; children }`. The TS error blocked plan 07-09 verification step #14 (`tsc --noEmit → 0 errors`).
- **Fix:** Adopted the proper pattern in both components:
  ```ts
  const store = useMemo(() => createViewerStore(), [])
  // ...later, after fetch:
  store.getState().setGraph(graph)
  // ...JSX:
  <ViewerProvider store={store}><DiagramCanvas /></ViewerProvider>
  ```
- **Files:** `dashboard/components/scans/ScanViewerClient.tsx`, `dashboard/components/share/ShareViewer.tsx`
- **Commit:** 76da3d3

**3. [Rule 2 — Missing critical functionality] Type contract mismatch**
- **Found during:** Reading the plan's `<interfaces>` section vs `dashboard/lib/types.ts`
- **Issue:** `lib/types.ts` defined `ShareLinkCreateResp` (with `url` field) and a discriminated `ShareLandingResp { password_required }` / `ShareLandingUnlockedResp` pair. The actual backend (Plan 07-04, `backend/app/schemas/share.py`) returns `ShareCreateResp { id, token, share_url, expires_at }`, `ShareLandingResp { has_password, scan_id?, presigned_get_url?, branch?, commit_sha?, created_at?, summary_json? }`, and `ShareVerifyResp` for `/unlock`. The frontend types would have caused 401/200 path mismatches at runtime.
- **Fix:** Replaced the divergent types with `ShareCreateReq`, `ShareCreateResp`, `ShareLandingResp`, `ShareVerifyResp` mirroring the backend schemas exactly.
- **Files:** `dashboard/lib/types.ts`
- **Commit:** 76da3d3

**4. [Rule 3 — Blocking] Added `dashboard/app/api/scan-share/route.ts`**
- **Found during:** Task 1 implementation
- **Issue:** `backendFetch` is server-only (Clerk's `auth()` helper). The plan's `ShareModal.tsx` was specced to call `backendFetch` directly inside a `'use client'` component, which is impossible.
- **Fix:** Added a Next.js Route Handler at `/api/scan-share` that revalidates the Clerk JWT via `backendFetch` and forwards `POST /v1/scans/{id}/share-links`. ShareModal now POSTs to `/api/scan-share?scan_id=…`. This mirrors the existing `/api/scan-presigned` route pattern from 07-07.
- **Files:** `dashboard/app/api/scan-share/route.ts`
- **Commit:** 76da3d3

### Plan Path Corrections (no behavior change)

The plan's `<interfaces>` section referenced backend paths `/v1/scans/{id}/share`,
`/v1/share/{token}`, `/v1/share/{token}/verify`. The actual backend (Plan 07-04, already
shipped in main) uses `/v1/scans/{id}/share-links`, `/v1/share-links/{token}`,
`/v1/share-links/{token}/unlock`. Implementation uses the actual paths. The plan's
acceptance grep `pattern: "v1/scans.*share"` matches both. No behavior change required —
documenting here so a future reader is not confused by the plan-vs-code drift.

## TDD Gate Compliance

Each task followed RED → GREEN:

- Task 1: `b799542 test(07-09)` (RED — share-modal.test.tsx, 6 failing) →
  `76da3d3 feat(07-09)` (GREEN — all 6 pass).
- Task 2: `3165ded test(07-09)` (RED — password-gate.test.tsx, 7/8 failing) →
  `45281aa feat(07-09)` (GREEN — all 8 pass).

REFACTOR step on Task 2 was small (rewriting JSDoc as line-comments to satisfy the
metadata grep gate); folded into the GREEN commit since it produced no behavior change.

## Commit Trail

| Commit | Type | Description |
|--------|------|-------------|
| 85a0032 | fix(07-09) | Inline next/tsconfig settings (blocker fix) |
| b799542 | test(07-09) | RED — share-modal.test.tsx |
| 76da3d3 | feat(07-09) | GREEN — ShareModal + share landing RSC + ShareViewer + layout + API proxy + ScanViewerClient bug fix + types alignment |
| 3165ded | test(07-09) | RED — password-gate.test.tsx (D-09 zero-metadata enforcement) |
| 45281aa | feat(07-09) | GREEN — PasswordGate (401/410/429 flows + zero-metadata gate) |

## Self-Check

- All 8 plan-listed files present and committed.
- All 14 plan verification greps pass.
- Tsc clean (0 errors). Vitest 29/29 pass.

## Self-Check: PASSED
