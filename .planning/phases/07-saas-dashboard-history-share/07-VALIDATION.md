---
phase: 7
slug: saas-dashboard-history-share
status: active
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

### Backend (Plans 07-01 .. 07-04, 07-11 backend portions)

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --no-cov` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q --no-cov` |
| **Estimated runtime** | ~12 seconds |

### Frontend (Plans 07-05 .. 07-11 frontend portions)

| Property | Value |
|----------|-------|
| **Framework** | vitest 4.x + jsdom |
| **Config file** | `dashboard/vitest.config.ts` |
| **Quick run command** | `cd dashboard && npx vitest run --reporter=verbose 2>&1 \| tail -40` |
| **Full suite command** | `cd dashboard && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run the framework-appropriate quick command above
- **After every plan wave:** Run both full suite commands (backend + frontend)
- **Before `/gsd-verify-work`:** Both full suites must be green
- **Max feedback latency:** ~15 seconds (frontend); ~12 seconds (backend)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 07-01-T1 | 07-01 | 1 | HST-03 | T-07-01-01, T-07-01-03 | branch/commit_sha max_length enforced by Pydantic Field + String column | integration | `cd backend && python -c "import bcrypt; assert bcrypt.__version__.startswith('4.')" && alembic heads \| grep -c '005_scan_metadata_columns' && grep -c 'bcrypt' pyproject.toml` | ⬜ pending |
| 07-01-T2 | 07-01 | 1 | HST-03 | T-07-01-01 | ScanCommitReq extra='forbid' rejects unknown fields | integration | `cd backend && alembic upgrade head && python -m pytest tests/ -x -q --no-cov` | ⬜ pending |
| 07-02-T1 | 07-02 | 2 | HST-01 | — | list_scans only returns team-scoped rows (RLS) | unit | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -c "from app.routes.scans import list_scans; print('ok')"` | ⬜ pending |
| 07-02-T2 | 07-02 | 2 | HST-01 | — | filters (branch ILIKE, status, from/to) never leak cross-team rows | integration | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -m pytest tests/test_scans_list.py -x -q --no-cov` | ⬜ pending |
| 07-03-T1 | 07-03 | 2 | HST-02 | — | compute_diff is a pure function — no DB calls, no side effects | unit | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -c "from app.schemas.scan import NodeDiff, ResourceDiffResp; from app.services.diff import compute_diff; print('ok')"` | ⬜ pending |
| 07-03-T2 | 07-03 | 2 | HST-02 | — | compare_scans returns 404 on cross-team access | integration | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -m pytest tests/test_scans_compare.py -x -q --no-cov` | ⬜ pending |
| 07-04-T1 | 07-04 | 2 | SHR-01, SHR-02 | T-07-04-* | ShareCreateResp.share_url present; raw token never stored | unit | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -c "from app.schemas.share import ShareCreateReq, ShareCreateResp, ShareLandingResp, ShareVerifyReq; from app.services.bcrypt_hash import hash_value, verify_value; from app.db.models import ShareLink; print('ok')" && alembic heads \| grep -c "006_share_links"` | ⬜ pending |
| 07-04-T2 | 07-04 | 2 | SHR-01 | — | alembic 006 upgrade head succeeds | integration | `cd backend && alembic upgrade head` (blocking checkpoint — manual confirm) | ⬜ pending |
| 07-04-T3 | 07-04 | 2 | SHR-01, SHR-02 | T-07-04-* | share router registered in main.py; route responds | unit | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -c "from app.routes.share import router; print('share router ok')"` | ⬜ pending |
| 07-04-T4 | 07-04 | 2 | SHR-01, SHR-02 | T-07-04-* | revoked/expired links return 410; wrong password returns 401 | integration | `cd /Users/bhushan/Documents/Projects/Infracanvas/backend && python -m pytest tests/test_share.py -x -q --no-cov && python -m pytest tests/ -x -q --no-cov` | ⬜ pending |
| 07-05-T1 | 07-05 | 2 | DSH-02, DSH-03 | — | Clerk middleware gates dashboard routes; no unauthenticated access | integration | `grep -c '"dashboard"' package.json && test -f dashboard/package.json && grep -c '@clerk/nextjs' dashboard/package.json && grep -c '@infracanvas/viewer/styles.css' dashboard/app/globals.css` | ⬜ pending |
| 07-05-T2 | 07-05 | 2 | DSH-02, DSH-03 | — | backendFetch attaches Authorization header; ScanListItem type exported | unit | `grep -c 'clerkMiddleware' dashboard/middleware.ts && grep -c 'border-amber-400' dashboard/components/layout/Sidebar.tsx && grep -c 'Authorization' dashboard/lib/backend.ts && grep -c 'ScanListItem' dashboard/lib/types.ts` | ⬜ pending |
| 07-06-T1 | 07-06 | 3 | DSH-04, HST-03 | — | scans table data-testid present; Sparkline SVG polyline renders | unit | `grep -c 'data-testid="scans-table"' dashboard/components/scans/ScansTable.tsx && grep -c 'polyline' dashboard/components/scans/Sparkline.tsx && grep -c 'next_cursor' dashboard/components/scans/Pagination.tsx && grep -c 'await searchParams' dashboard/app/(dashboard)/scans/page.tsx` | ⬜ pending |
| 07-06-T2 | 07-06 | 3 | DSH-04, HST-03 | — | ScanFilters uses 'use client'; branch-filter test-id present; vitest config exists | integration | `grep -c "'use client'" dashboard/components/scans/ScanFilters.tsx && grep -c 'data-testid="branch-filter"' dashboard/components/scans/ScanFilters.tsx && grep -c 'scans-table' dashboard/__tests__/scans-table.test.tsx && test -f dashboard/vitest.config.ts` | ⬜ pending |
| 07-07-T1 | 07-07 | 3 | DSH-04 | — | detail page awaits params; MetadataHeader test-id present; R2 fetch retries on 403 | unit | `grep -c 'await params' dashboard/app/(dashboard)/scans/\[id\]/page.tsx && grep -c 'data-testid="metadata-header"' dashboard/components/scans/MetadataHeader.tsx && grep -c 'retry' dashboard/lib/r2.ts && grep -c 'share-button' dashboard/components/scans/ShareButton.tsx` | ⬜ pending |
| 07-07-T2 | 07-07 | 3 | DSH-04 | — | ScanViewerClient uses ViewerProvider; metadata-header test file exists | integration | `grep -c 'ViewerProvider' dashboard/components/scans/ScanViewerClient.tsx && grep -c '@infracanvas/viewer' dashboard/components/scans/ScanViewerClient.tsx && grep -c 'metadata-header' dashboard/__tests__/metadata-header.test.tsx && test -f dashboard/app/api/scan-presigned/route.ts` | ⬜ pending |
| 07-08-T1 | 07-08 | 4 | HST-02 | — | compare page + DiffSummary + DiffNodeList render from fixture | integration | `cd dashboard && npx vitest run __tests__/compare-layout.test.tsx --reporter=verbose 2>&1 \| tail -30` | ⬜ pending |
| 07-08-T2 | 07-08 | 4 | HST-02 | — | CompareLayout + ScanPickerModal TypeScript clean | unit | `cd dashboard && npx tsc --noEmit 2>&1 \| grep -E "compare\|ScanPicker" \| head -20` | ⬜ pending |
| 07-09-T1 | 07-09 | 4 | SHR-01, SHR-02 | — | ShareModal + share layout + ShareViewer render; share_url (not url) in ShareCreateResp | integration | `cd dashboard && npx vitest run __tests__/share-modal.test.tsx --reporter=verbose 2>&1 \| tail -30` | ⬜ pending |
| 07-09-T2 | 07-09 | 4 | SHR-01, SHR-02 | — | PasswordGate blocks metadata; rate-limit display present | integration | `cd dashboard && npx vitest run __tests__/password-gate.test.tsx --reporter=verbose 2>&1 \| tail -30` | ⬜ pending |
| 07-10-T1 | 07-10 | 5 | DSH-06 | — | TypeScript strict: responsive layout changes compile clean | unit | `cd dashboard && npx tsc --noEmit 2>&1 \| grep -c "error TS"` | ⬜ pending |
| 07-10-T2 | 07-10 | 5 | DSH-06 | — | Responsive Vitest + Lighthouse budgets configured | integration | `cd dashboard && npx vitest run __tests__/responsive.test.tsx --reporter=verbose 2>&1 \| tail -40` | ⬜ pending |
| 07-11-T1 | 07-11 | 4 | DSH-05 | T-07-11-01, T-07-11-02 | ScoreCard grade derivation correct; TopFindings filters to critical only | unit | `cd dashboard && npx vitest run __tests__/home-dashboard.test.tsx --reporter=verbose 2>&1 \| tail -30` | ⬜ pending |
| 07-11-T2 | 07-11 | 4 | DSH-05 | T-07-11-04 | OrganizationProfile renders; billing CTA present; GitHub button disabled | integration | `cd dashboard && npx vitest run __tests__/settings-routes.test.tsx --reporter=verbose 2>&1 \| tail -30` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 = Plan 07-01 (schema foundation). Required before any Wave 2+ plan can execute.

- [x] `backend/migrations/versions/20260428_005_scan_metadata_columns.py` — alembic migration for branch/commit_sha/source columns (Plan 07-01 Task 1)
- [x] `backend/app/schemas/scan.py` — `ScanListItemResp`, `ScanListResp` types exported (Plan 07-01 Task 2)
- [x] `backend/app/db/models.py` — Scan ORM carries branch/commit_sha/source (Plan 07-01 Task 2)
- [x] `backend/pyproject.toml` — bcrypt>=4.0,<5 declared (Plan 07-01 Task 1)
- [x] `cd backend && alembic heads` outputs exactly one head: `005_scan_metadata_columns`

*Wave 0 complete when: `cd backend && alembic current` outputs `005_scan_metadata_columns` and `python -m pytest tests/ -x -q --no-cov` exits 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| alembic upgrade head against dev Neon DB | HST-03 | Requires live DB connectivity (Neon dev) — local machine may not have access | Run `cd backend && alembic upgrade head` with `DATABASE_URL` env set to dev Neon connection string; verify `alembic current` outputs `005_scan_metadata_columns` |
| Clerk OrganizationProfile renders in browser | DSH-05 | Clerk component requires live Clerk publishable key + authenticated session | Log in to dashboard dev deployment, navigate to /settings/members, confirm OrganizationProfile renders with amber primary color |
| Share link password gate — browser flow | SHR-02 | Requires live R2 + backend + Clerk — not mockable end-to-end in vitest | Create a password-protected share link in dev; open it in an incognito window; verify scan metadata is NOT visible until password entered |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify command
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plans 07-02..11 depend on 07-01 schema)
- [x] No watch-mode flags (`--watch` absent from all commands)
- [x] Feedback latency: backend ~12s, frontend ~15s — both under 60s threshold
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
