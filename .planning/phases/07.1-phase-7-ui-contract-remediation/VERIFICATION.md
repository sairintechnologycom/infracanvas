---
phase: 07.1-phase-7-ui-contract-remediation
verified: 2026-05-01T00:57:00Z
status: passed
score: 6/6 success criteria verified
overrides_applied: 0
re_verification:
  previous_status: lost_to_compaction
  previous_score: unknown
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Visual cross-check of compare page 4-card layout against UI-SPEC §Compare page mockup"
    expected: "Sections render in order Added → Removed → Changed → Findings; Changed rows expand to attribute table; row click opens DrillDownSheet"
    why_human: "Visual fidelity to spec mockup cannot be verified by grep alone"
  - test: "Manually trigger share-link copy / revoke / failure paths and confirm toasts render at bottom-right"
    expected: "Sonner toasts appear with success/error styling and dismiss after default duration"
    why_human: "Toast UX (timing, color, position) is observable only at runtime"
  - test: "Visit /scans/{id} route and verify [Compare] [Share] buttons render in top-bar action slot, not in MetadataHeader"
    expected: "Buttons appear in TopBarActionsSlot on the right side of the top bar; MetadataHeader shows only metadata strip"
    why_human: "Layout placement requires browser rendering"
  - test: "Verify Sparkline hover tooltip + relative-date copy ('Just now', '2 hours ago', 'Yesterday', 'Apr 22') render correctly in RecentScansTable"
    expected: "Tooltip appears on data-point hover with score+date; relative-date strings match voice rules"
    why_human: "Hover-driven UI state is observable only at runtime"
---

# Phase 7.1: UI Contract Remediation Verification Report

**Phase Goal:** Bring the Phase 7 dashboard in line with the approved 07-UI-SPEC.md design contract — install the design system, replace the rejected compare visualization, complete the share-link management surface, and close the polish drift on color/typography/spacing/copy.
**Verified:** 2026-05-01T00:57:00Z
**Status:** passed (with human verification recommended for visual/runtime UX)
**Re-verification:** Yes — previous gsd-verifier output was lost to context compaction; full re-run.

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | shadcn/ui initialized + 17 blocks + 4 components migrated | VERIFIED | components.json with `style=new-york`, `baseColor=slate`, `cssVariables=true`; 17 files in `dashboard/components/ui/`; ScanPickerModal/ShareModal/SettingsLayout/ScanFilters all import from `@/components/ui/*` (see Artifact table) |
| 2 | Compare page = 4-section diff card + Sheet + attr expanders | VERIFIED | `CompareLayout.tsx:90-110` renders DiffSection(Added), DiffSection(Removed), ChangedDiffSection, FindingsDeltaSection + DrillDownSheet; `ChangedDiffRow.tsx:21,57` toggles `expanded` state inline; `ChangedAttributesTable.tsx:13-58` renders attr-level table; CompareViewerPair deleted (no occurrences in tree) |
| 3 | Toaster mounted; copied/revoked/failed toasts firing | VERIFIED | `dashboard/app/layout.tsx:3,24` imports + mounts `<Toaster richColors position="bottom-right" />`; `ShareModal.tsx:113` (copy success), `:116` (copy fail), `:86,99` (link gen fail); `RevokeShareLinkButton.tsx:50` (revoke success), `:47,53` (revoke fail) |
| 4 | Active share-links list per spec + AlertDialog destructive Revoke | VERIFIED | `ShareLinksList.tsx:29` exported; mounted in `ShareModal.tsx:235`; backed by `app/api/scan-share/route.ts:33` (GET /v1/scans/{id}/share-links); `RevokeShareLinkButton.tsx:4-12,58-84` uses full shadcn AlertDialog primitive set with `variant="destructive"` action button |
| 5 | Top-bar action slot pattern; [Compare][Share] moved off MetadataHeader on /scans/{id} | VERIFIED | `components/layout/TopBar.tsx:65` renders `<TopBarActionsSlot/>`; `TopBarActions.tsx:26-45` exports Provider+Slot+`useTopBarActions` context; `app/(dashboard)/scans/[id]/ScanDetailActions.tsx:20` (client component injecting actions) wired into `app/(dashboard)/scans/[id]/page.tsx:6,29`; `MetadataHeader.tsx:119-120` confirms buttons removed via comment "Action buttons (Compare, Share) live in the top-bar slot per RMD-05 — mounted by <ScanDetailActions/> on /scans/[id]" |
| 6 | Polish drift closed (typography/color/focus-ring/copy/sparkline tooltip/custom-range filter) | VERIFIED | Off-scale `text-xl`/`text-lg` grep returns zero matches outside ui/ primitives and tests; focus rings normalized to `ring-slate-400` (3 representative call sites); `app/(dashboard)/page.tsx:39` uses `px-8 py-12 ... gap-12` per spec; `Sparkline.tsx:11-91` implements hover tooltip with onMouseMove/onMouseLeave + tooltip render at hover index; `RecentScansTable.tsx:20,95` exports `formatRelativeDate` covering Just now / N hour(s) ago / Yesterday / Mon DD per `__tests__/relative-dates.test.tsx:14-28` voice-rule expectations |

**Score:** 6/6 success criteria verified.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `dashboard/components.json` | shadcn config (new-york + slate + cssVars + @/* alias) | VERIFIED | Read confirms exact required keys |
| `dashboard/components/ui/{17 blocks}` | 17 shadcn primitives | VERIFIED | `ls | wc -l` = 17 — alert-dialog, button, calendar, card, dialog, dropdown-menu, form, input, label, pagination, popover, select, sheet, skeleton, sonner, table, tabs |
| `dashboard/components/scans/ScanPickerModal.tsx` | Migrated to shadcn Dialog | VERIFIED | `:10` imports `@/components/ui/dialog` |
| `dashboard/components/share/ShareModal.tsx` | Migrated to shadcn Dialog | VERIFIED | `:10` imports `@/components/ui/dialog` |
| `dashboard/app/(dashboard)/settings/layout.tsx` | Migrated to shadcn Tabs | VERIFIED | `:5` imports Tabs/TabsList/TabsTrigger from `@/components/ui/tabs` |
| `dashboard/components/scans/ScanFilters.tsx` | Migrated to shadcn Select + Calendar + Popover | VERIFIED | `:12-14` imports Select / Popover / Calendar |
| `dashboard/components/compare/CompareLayout.tsx` | 4-section card layout entry | VERIFIED | `:8-11,90-110` mounts DiffSection×2, ChangedDiffSection, FindingsDeltaSection, DrillDownSheet |
| `dashboard/components/compare/DrillDownSheet.tsx` | Per-resource Sheet drill-down | VERIFIED | `:33-60` wraps Sheet/SheetContent/SheetHeader/SheetTitle/SheetDescription |
| `dashboard/components/compare/ChangedDiffRow.tsx` | Inline attribute expander on Changed rows | VERIFIED | `:21` `useState(expanded)`, `:39` chevron toggle, `:57` conditional render |
| `dashboard/components/compare/ChangedAttributesTable.tsx` | Before/after attribute table | VERIFIED | `:13-58` table + "+N more attributes" toggle |
| Old `CompareViewerPair.tsx` | Deleted | VERIFIED | `find -name 'CompareViewerPair*'` returns no results |
| `dashboard/app/layout.tsx` | `<Toaster/>` mounted at root | VERIFIED | `:3` import + `:24` mount with richColors + bottom-right |
| `dashboard/components/share/ShareLinksList.tsx` | Active links list component | VERIFIED | `:29` export + `:18` doc-comment "Active share-links list inside ShareModal (RMD-04)" |
| `dashboard/components/share/RevokeShareLinkButton.tsx` | AlertDialog destructive-confirm | VERIFIED | `:4-12` shadcn AlertDialog imports, `:58-84` full dialog markup, `:79` `variant="destructive"` |
| `dashboard/app/api/scan-share/route.ts` | GET/POST/DELETE proxy to backend `/v1/scans/{id}/share-links` | VERIFIED | `:33` GET, `:70` POST, `:117` DELETE — all proxy to backend |
| `backend/app/routes/share.py` | GET /v1/scans/{id}/share-links list endpoint | VERIFIED | `:158-200` `@router.get("/scans/{scan_id}/share-links")` with active filter (non-revoked, non-expired) |
| `dashboard/components/layout/TopBar.tsx` | Top-bar with action slot | VERIFIED | `:4,65` imports + renders `<TopBarActionsSlot/>` |
| `dashboard/components/layout/TopBarActions.tsx` | Provider + Slot + hook | VERIFIED | `:26-45` Provider, hook, Slot exports — full context-based injection pattern |
| `dashboard/app/(dashboard)/scans/[id]/ScanDetailActions.tsx` | Detail-page injector | VERIFIED | `:20` ScanDetailActions component; wired in `[id]/page.tsx:6,29` |
| `dashboard/components/scans/Sparkline.tsx` | Hover tooltip | VERIFIED | `:16` hoverIdx state, `:65-66` mouse handlers, `:77-91` tooltip render |
| `dashboard/components/home/RecentScansTable.tsx` | `formatRelativeDate` per voice rules | VERIFIED | `:20,95` export + use; voice-rule cases tested in `__tests__/relative-dates.test.tsx:14-28` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| ScanModalDetailActions | TopBar | `useTopBarActions().set(...)` | WIRED | Context provider in `(dashboard)/layout.tsx`; consumer in `[id]/ScanDetailActions.tsx`; slot reader in `TopBar.tsx:65` |
| ShareModal | RevokeShareLinkButton | `<ShareLinksList/>` → list rows | WIRED | `ShareModal.tsx:11,235` mounts ShareLinksList; ShareLinksList rows render RevokeShareLinkButton |
| RevokeShareLinkButton | Backend DELETE | `fetch('/api/scan-share?...')` → DELETE proxy | WIRED | `RevokeShareLinkButton.tsx:47-53` + `app/api/scan-share/route.ts:117` |
| ShareLinksList | Backend GET | `fetch('/api/scan-share?scan_id=...')` → GET proxy | WIRED | Backend route at `routes/share.py:158`; proxy at `app/api/scan-share/route.ts:33` |
| ShareModal copy/error | Sonner Toaster | `toast.success` / `toast.error` | WIRED | All three failure paths fire toast (`ShareModal.tsx:86,99,113,116`); Toaster mounted at root |
| RevokeShareLinkButton confirm | toast | `toast.success/error` | WIRED | `:50` success, `:47,53` failure |
| Compare page | CompareLayout → DrillDownSheet | `drillResourceId` state passed down | WIRED | `CompareLayout.tsx:110` mounts DrillDownSheet; opening per-resource lazy-loads presigned URL (per design comment in page.tsx) |
| ChangedDiffRow | ChangedAttributesTable | Expanded state + table render | WIRED | `:57` conditional renders ChangedAttributesTable with row diff |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|---------------------|--------|
| ShareLinksList | `links` | GET `/api/scan-share?scan_id=...` → backend `routes/share.py:158-200` (DB query) | Yes — real DB query filters revoked_at IS NULL AND expires_at > NOW | FLOWING |
| CompareLayout | `diff` | RSC fetch in `compare/page.tsx` via `backendFetch(/v1/scans/{a}/compare/{b})` | Yes — backend computes diff | FLOWING |
| RecentScansTable | `scans` (sparkline + relative dates) | Server-side fetch through `lib/backend.ts` (Phase 7 wiring) | Yes — pre-existing wiring carried into 7.1 polish | FLOWING |
| ShareModal | share-link create response | POST `/api/scan-share?scan_id=...` | Yes — backend POST creates row | FLOWING |

No HOLLOW or DISCONNECTED artifacts surfaced.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Vitest dashboard suite passes | `cd dashboard && npm run test -- --run` | 18 files / 170 tests passed | PASS |
| 17 shadcn blocks present | `ls dashboard/components/ui/ \| wc -l` | 17 | PASS |
| CompareViewerPair removed | `find dashboard -name 'CompareViewerPair*'` | empty | PASS |
| Top-bar slot wiring throws if misused (defensive contract) | useTopBarActions test in `topbar-actions.test.tsx` | Throws "must be used inside <TopBarActionsProvider/>" — intentional, test passes | PASS |

The two stderr "Error: useTopBarActions must be used inside <TopBarActionsProvider/>" entries during the test run are **intentional negative-path assertions**, not failures. The final summary reads `Test Files 18 passed (18) | Tests 170 passed (170)`.

---

### Requirements Coverage

| Req | Description | Status | Evidence |
|-----|-------------|--------|----------|
| RMD-01 | Install shadcn/ui design system | SATISFIED | components.json + 17 blocks; 4 component migrations |
| RMD-02 | Replace dual-canvas compare with diff cards + Sheet | SATISFIED | CompareLayout 4-section + DrillDownSheet + attribute expanders |
| RMD-03 | Toaster + share-link toasts | SATISFIED | Toaster at root; toast.success/error on copy/revoke/failure paths |
| RMD-04 | Active share-links list + destructive Revoke | SATISFIED | ShareLinksList + RevokeShareLinkButton AlertDialog + GET endpoint |
| RMD-05 | Top-bar action slot; move buttons off MetadataHeader | SATISFIED | TopBarActions Provider/Hook/Slot; ScanDetailActions injector; MetadataHeader cleaned |
| RMD-06 | Polish drift (typography/color/spacing/copy/sparkline tooltip/custom-range) | SATISFIED | Focus rings normalized; off-scale headings absent; home page gutters fixed; relative-date voice rules implemented; sparkline hover tooltip wired |

No orphaned requirements detected.

---

### Anti-Patterns Found

None blocking. The deferred-items.md table records four pre-existing build-tree issues — two were resolved inline in plan 07.1-08 (Inter unused import; form.tsx registry path), and the `lib/backend.ts` server-only-into-client transitive import was resolved at merge time on `dev/local-no-auth` by swapping `backendFetch` → `fetch('/api/scans-list')`. Four flaky tests are documented as timeout flakes (44/44 pass in isolation) and tied to vitest thread contention, not Phase 7.1 logic.

---

### Human Verification Required

See frontmatter `human_verification` block. Four runtime/visual checks recommended before declaring the dashboard 100% spec-aligned:

1. Compare page mockup fidelity (4-card order, expander behavior, Sheet drill-down) vs `07-UI-SPEC.md`.
2. Toast surface (sonner position, color, dismissal) on share copy/revoke/failure paths.
3. Top-bar action placement on `/scans/{id}` route in browser.
4. Sparkline hover tooltip + relative-date voice strings in `RecentScansTable`.

These are observable only at runtime and lie outside grep-driven verification.

---

### Gaps Summary

No blocker gaps. All 6 roadmap success criteria are satisfied by codebase evidence; all 6 RMD requirements have artifacts wired end-to-end; the 170-test dashboard suite is green; data flows from UI → API proxy → backend → DB on the share-link surface.

The only outstanding items are visual/runtime checks that require a human-driven smoke test, listed in the `human_verification` frontmatter. None of those carry to Phase 7.5 or Phase 8 — they are confirmation of work already in the tree, not undone work.

---

_Verified: 2026-05-01T00:57:00Z_
_Verifier: Claude (gsd-verifier)_
