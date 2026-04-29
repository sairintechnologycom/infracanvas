# Phase 7 — UI Review

**Audited:** 2026-04-29
**Baseline:** `07-UI-SPEC.md` (Phase 7 design contract, approved 2026-04-28)
**Screenshots:** not captured (no dev server detected on :3000 — code-only audit)
**Auditor stance:** adversarial; assumes contract divergence until proven otherwise.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | **3**/4 | Sentence case + voice mostly clean, but copy contract drift on home heading, share-revoke flow missing, two filter labels deviate (`Last 7 days` is shown without showing it as the default selection; `Filter by branch` matches spec). |
| 2. Visuals | **2**/4 | shadcn/ui is **NOT initialized** (no `components.json`, no `components/ui/`) despite the contract mandating it; compare layout ships the side-by-side dual canvas D-10 *explicitly rejected*; top-bar action slot is empty. |
| 3. Color | **3**/4 | 60/30/10 is broadly respected (white surfaces, slate-50 secondary, amber accent), but accent is overused (~27 amber-class occurrences across 14 elements, vs the "CTA + active-nav left-border" reserved-for list); compare landing CTA uses `bg-amber-500 text-white` instead of the locked `amber-400 + text-slate-900`. |
| 4. Typography | **3**/4 | Sticks to 4 sizes + 2 weights for ~95% of components; two off-scale headings (`text-xl` on Home, `text-lg` on compare landing + 3 error cards) violate the "exactly 4 sizes" rule. tabular-nums + font-mono usage in tables is correct. |
| 5. Spacing | **3**/4 | All spacing uses Tailwind 4 multiples (no arbitrary `[12px]` etc); declared sub-tokens (`h-[52px]`, `w-[220px]`, `h-[64px]`, `min-h-[400px]`) are all justified component primitives. Container widths and `max-w-7xl` gutters match spec. Minor: home page uses `px-6 py-6` instead of the spec's `px-8 py-12 gap-12`. |
| 6. Experience Design | **2**/4 | No `<Toaster/>` mounted at root; share-link copy / revoke / failure toasts from copywriting contract are silently absent. Share modal's revoke flow + active-links list are stubbed (`TODO` in code). Sparkline hover tooltip is absent. Skeleton fallbacks shaped per route are mostly present. |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **shadcn/ui has not been initialized — the entire visual contract assumes it.**
   - User impact: every form control is a raw HTML element styled ad-hoc, so focus rings, disabled states, hover states, and a11y semantics are inconsistent across pages (compare picker uses Radix Dialog directly; ShareModal uses a hand-rolled overlay; filter bar uses native `<select>`; settings tabs are hand-rolled `<Link>` underline). Toasts cannot ship without the shadcn `<Toaster/>` primitive UI-SPEC §Interaction calls out at app root.
   - Concrete fix: run `npx shadcn@latest init` in `dashboard/` (preset `new-york`, base color `slate`, CSS variables on, Tailwind v4), then add the 17 declared blocks: `button dialog alert-dialog dropdown-menu select input popover calendar table tabs sheet skeleton sonner pagination form label card`. Migrate `ScanFilters` (`<select>` → `<Select/>`), `ScanPickerModal` (Dialog primitive → `<Dialog/>`), `ShareModal` (hand-rolled → `<Dialog/>` + `<Form/>` + `<AlertDialog/>` for revoke), `SettingsLayout` (`<Link>` underline → `<Tabs/>`), and add `<Toaster/>` to root layout.

2. **Compare page implements the side-by-side dual canvas the contract explicitly rejects.**
   - User impact: D-10 says diff visualization is "**resource-diff list with drill-down (NOT side-by-side dual canvas, NOT single-canvas overlay)**" because side-by-side fights 1080p horizontal real estate. Phase 7 ships exactly the rejected pattern (`CompareViewerPair` mounts two `<DiagramCanvas/>` panes). The "Changed" rows also have no attribute-level `before → after` expanders the spec mandates as the primary signal.
   - Concrete fix: replace `CompareViewerPair` with the spec'd 4-section card layout (Added / Removed / Changed / Findings delta) using one `<Sheet/>`-driven drill-down drawer for the "open the resource in a single scoped canvas" flow. Add attribute-level expanders to `DiffNodeList` rows of `kind === 'changed'` (collapsed by default, click chevron to reveal a 2-col `attribute_name | before → after` table; cap at 10 attrs with "+N more" expander). The current side-by-side viewer pair can be reused later if added behind a "Side-by-side view" toggle, but the default must be the rejected-then-required diff list.

3. **Share modal is incomplete: no toasts, no active-links list, no revoke flow.**
   - User impact: the ENTIRE post-creation share-management surface is missing. Copy acknowledges this (`/* TODO: GET /v1/scans/{id}/share-links not yet implemented */`). The single-line "No share links yet for this scan." renders even after a successful generate. The "Copy" button silently fails on permission errors. Share-link copied/revoked/failed toasts (3 strings in copywriting contract) cannot fire without `<Toaster/>`.
   - Concrete fix: backend ships `GET /v1/scans/{id}/share-links` + `DELETE /v1/scans/{id}/share-links/{share_id}` (the second is already in D-16 and likely already implemented per backend phase 6); render the "Active share links" list per UI-SPEC `Expires {date} · Created by {Sam} · {with password / no password}` format with a red text-link `[Revoke]` per row that opens an `<AlertDialog/>` with the destructive copy already in the spec. Wire `<Toaster/>`-backed `toast.success('Link copied to clipboard')`, `toast.success('Share link revoked')`, `toast.error('Couldn't generate share link. Try again.')` on the three success/failure paths.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**PASS — voice rules:**
- Sentence case throughout (page headings: `Overview`, `Scans`, `Settings`, `Compare two scans`, `Share this scan`, `Compare against…`).
- No exclamation marks anywhere in chrome.
- Brand wordmark "InfraCanvas" Title Case preserved in sidebar (`Sidebar.tsx:46`) and share-landing (`ShareViewer.tsx:178`, `PasswordGate.tsx:140`, `share/[token]/page.tsx:48`).
- Mono used correctly for SHAs, branches in strips, and CLI hint (`p-3` code blocks in empty states).
- ⚠ used only for "Never (not recommended)" warning (`ShareModal.tsx:167`) ✓ matches contract.
- ✓ used in copy-button confirmation (`ShareModal.tsx:228`) ✓.

**WARNING — copy drift from contract:**

- **`page.tsx:41`** — Home heading is `Overview`, but UI-SPEC §`/` does not declare a heading for the home page (the latest-scan card *is* the focal element). Adding `Overview` introduces an unspec'd string AND uses the wrong size (`text-xl`, see Pillar 4).
- **`scans/[id]/page.tsx`** + **`MetadataHeader.tsx:64`** — back link reads `← Scans` (icon + word) ✓ but UI-SPEC §`/scans/{id}` says it should render as `← Scans / 04-28 main@a1b2c3d` (i.e. the breadcrumb path including the current scan, not just the parent collection). Implementation drops the trailing crumb segment.
- **`TopBar.tsx:30-37`** — breadcrumb just title-cases path segments, so `/scans/uuid-here` renders as `Scans / Uuid-here` (uppercase first char of UUID). The contract says active crumb is the human-readable scan title (`Scans / 2026-04-28 main@a1b2c3d`).
- **`RecentScansTable.tsx:17-26`** — relative-date format is `2h ago / 1d ago / 2026-04-28`. UI-SPEC §"Voice rules" specifies full words: `2 hours ago` / `Yesterday` / `Apr 26`. Drift on word-form and on the absolute fallback (ISO instead of `Apr 26`).
- **`compare/page.tsx:17`** — `Compare two scans` is an unspec'd page heading on a route that the spec doesn't explicitly cover (`/compare` was an interim landing), so the deviation is forgivable but should not be `text-lg`.
- **`scans/compare/page.tsx:36,62,80`** — three error cards use `text-lg` headings (`Invalid compare URL`, `Scan not found`, `Compare failed`). The spec's locked error headings are `Sign-in expired`, `Scan not found`, `Something went wrong`. `Compare failed` is a new (acceptable) variant; `Invalid compare URL` is a 400-state the spec does not cover (defensible — but copy could be tightened to `Couldn't open this comparison`).
- **`ScanFilters.tsx:21`** — date-range default option is rendered as `Last 7 days` ✓; but the spec also requires a `Custom range…` option that opens a `<Calendar/>` popover — entirely missing from the implementation.
- **`Pagination.tsx`** lacks the `Showing 1–25 of 127` count copy (UI-SPEC §`/scans` item 4).
- **`PasswordGate.tsx:77,80`** — wrong-password copy is `Something went wrong. Please try again.` for non-401 errors, but the 401 branch correctly says `Incorrect password.` ✓.

**No generic labels** (`Submit`, `OK`, `Click Here`) detected outside React state/handler identifiers.

### Pillar 2: Visuals (2/4)

**BLOCKER — shadcn/ui not initialized** despite the contract being explicit:
> "shadcn/ui (recommended for primitives — Table, Dialog, DropdownMenu, Select, Tabs, Toast, Skeleton, Form). Initialize with `npx shadcn@latest init` in the new `dashboard/` Next 15 app at the start of the phase."

Evidence:
- No `dashboard/components.json` exists.
- No `dashboard/components/ui/` directory.
- `grep "from '@/components/ui/" → 0 matches`.
- The spec's "Registry Safety" section lists 17 official shadcn blocks as "used"; ZERO of them are installed.

What's there instead:
- `@radix-ui/react-dialog`, `dropdown-menu`, `popover`, `select`, `tabs` are in `package.json` and used directly (e.g. `ScanPickerModal` imports `import * as Dialog from '@radix-ui/react-dialog'`) — this is *Radix*, not shadcn.
- `react-day-picker` installed but unused (no `Calendar` block).
- `ShareModal.tsx:112-123` uses a hand-rolled `<div role="dialog" aria-modal>` overlay — not even Radix Dialog primitive.
- `SettingsLayout.tsx:26-44` is a hand-rolled `<nav>` + `<Link>` underline strip, not shadcn `<Tabs/>`. Spec § `/settings/*` says `shadcn <Tabs/>`.

**BLOCKER — compare diff visualization shape contradicts D-10.**
- `CompareLayout.tsx:77-91` puts `DiffNodeList` (380px left rail) next to `CompareViewerPair` (right pane).
- `CompareViewerPair.tsx:144-166` mounts two `<DiagramCanvas/>` instances side-by-side.
- D-10: "Diff visualization = resource-diff list with drill-down (NOT side-by-side dual canvas, NOT single-canvas overlay)."
- The spec layout is 4 vertically-stacked cards (Added / Removed / Changed / Findings delta) with a single `<Sheet/>` drawer on row click, scoped to that resource + 1-hop neighbors. Implementation ships none of that.

**BLOCKER — top-bar action slot empty.**
- UI-SPEC §"App shell" right side of top bar: "Page-level actions slot (varies per route — empty on `/` and `/scans`; on `/scans/{id}` shows `[Compare] [Share]` buttons)".
- `TopBar.tsx:40` has only a placeholder `<div className="md:flex-row flex-col gap-1" />` with comment `Page-level actions injected by child pages via a slot pattern in later plans` — slot pattern never materialized.
- Compare/Share buttons live inside `MetadataHeader.tsx:124-125` (the 52px scan-detail strip), which is the secondary location, not the primary contract location.

**WARNING — focal point clarity:**
- Home page (`page.tsx:38-53`) uses `gap-4` between sections; spec says `gap-12`. The score card and the rest of the page have the same visual weight; the latest-score number is supposed to dominate via `text-[28px]` (correct in `ScoreCard.tsx:69` ✓) but the `gap-12` separation is missing.
- Sparkline placement: spec puts sparkline in a full-width strip *below* the latest-scan card (vertical stack). Implementation puts sparkline + TopFindings in a 2-col grid (`grid-cols-1 lg:grid-cols-2`), which compresses both.

**PASS:**
- Active sidebar nav indicator: `border-l-2 border-amber-400` (`Sidebar.tsx:77`) ✓ exactly matches spec.
- Score grade pill chip shape (`w-7 h-7 rounded-md`) ✓ spec calls 28×28 rounded-md, w-7 = 28px ✓.
- Dashboard chrome is light mode by default ✓ matches spec D-09/D-10.
- Empty state for `/` has card + heading + body + code block ✓ (`page.tsx:21-33`).
- Score-grade pills: `gradeInfo()` thresholds match spec (≥95 A+, 90-94 A, 85-89 B+, 80-84 B, 70-79 C, 60-69 D, <60 F). ⚠ one inconsistency: `ScansTable.tsx:16-20` uses simplified thresholds (≥80 → "B+"; ≥70 → "C") — does not distinguish A+/A or B+/B. `MetadataHeader.tsx:14-29` has the same simplified logic. Two divergent grade-pill implementations (`ScoreCard` strict vs `ScansTable`/`MetadataHeader` simplified) is its own consistency bug.

### Pillar 3: Color (3/4)

**PASS — palette structure:**
- Dominant white, secondary slate-50, border slate-200, body slate-900, muted slate-500 — all match spec exactly across surveyed files.
- Severity tokens (`text-sev-critical`, etc.) used correctly via Tailwind's CSS-variable bridge from the viewer pkg's `lib-styles.css`.
- Drift palette correct: `bg-green-50/100` / `text-green-700` for added, red for removed, amber for changed (`DiffNodeList.tsx:14-26`, `DiffSummary.tsx:25-43`).
- No raw hex outside the SeverityBadge fallback `text-[color:var(--color-sev-X,#hex)]` (defensible — the comment explains it's a build-time guard) and Clerk's `colorPrimary: '#f59e0b'` (also defensible — Clerk theming requires a literal hex).

**WARNING — accent overuse:**
- Counted **27 distinct amber-class occurrences across 14 unique source elements**.
- UI-SPEC §"Accent reserved for" allows amber on: (1) primary CTA backgrounds, (2) active sidebar nav 2px left border, (3) `Manage plan` text-link in `/settings/billing`. That's it.
- Found amber leaking onto:
  - `text-amber-600` on "Open scan →" links (`ScoreCard.tsx:107`, `TopFindings.tsx:53`, `RecentScansTable.tsx:44-45`, `ShareViewer.tsx:178`)
  - `text-amber-600` on "Try again" / "Back to scans" / "Clear all filters" / `Browse scans` (`ScanViewerClient.tsx:85`, `ScansTable.tsx:80`, `scans/compare/page.tsx:43,67,84`)
  - `bg-amber-50` decorative chip on the `/compare` landing icon (`compare/page.tsx:14`)
  - `focus:ring-amber-300` on ScanPickerModal search input (`ScanPickerModal.tsx:121`) — spec says focus rings are `ring-slate-400`, **NEVER** amber.

**WARNING — accent shade drift:**
- `compare/page.tsx:24` — Browse scans CTA is `bg-amber-500 hover:bg-amber-600 text-white`. Spec locks accent to `bg-amber-400` + `text-slate-900` (the amber-400-on-slate-900 pair was the very combo verified for 7:1 contrast in §Accessibility).
- `BillingPage` button (`billing/page.tsx:30`) uses `bg-amber-400 hover:bg-amber-500 text-slate-900` — half-correct (correct base, but hover bumps shade).
- `ShareModal` and `PasswordGate` use `bg-amber-400 hover:bg-amber-300` ✓ — correct (amber-300 hover is acceptable as a *lighter* hover, but the spec doesn't lock hover; the inconsistency between Billing and ShareModal is the issue).

**WARNING — destructive color:**
- No filled `bg-red-600` destructive button found (only red text-links). Spec says destructive *paired with `<AlertDialog/>`*. Since revoke flow is not implemented (Pillar 6), this is fine — but the absence is itself a Pillar 6 finding.

### Pillar 4: Typography (3/4)

**PASS:**
- `font-semibold` is the only weight other than the default; `font-medium` appears 8 times (mostly button text). Total of 2 weights in active use ✓.
- The 4 declared sizes (`text-xs`, `text-sm`, `text-base`, `text-[28px]`) all present and used per spec.
- `tabular-nums` consistently applied to all numeric table columns and the score display ✓.
- `font-mono` correctly scoped to commit SHAs, branches in strips, scan IDs, CLI hint, and code-fenced empty-state hints (20 occurrences, all justified).

**WARNING — off-scale sizes:**
- `text-xl` used once: `app/(dashboard)/page.tsx:41` — `<h1>Overview</h1>`. Spec allows only 12/14/16/28; `text-xl` (20px) is not declared.
- `text-lg` used 4 times:
  - `compare/page.tsx:17` — Compare landing heading
  - `scans/compare/page.tsx:36,62,80` — three error-card headings (Invalid compare URL / Scan not found / Compare failed)
  - All four should be `text-base` per spec.
- That's 5 off-scale heading instances total; small surface but a clear divergence from "exactly 4 sizes" rule.

**PASS — display size:**
- The single `text-[28px]` usage (`ScoreCard.tsx:69`) is on the score number, the only display-sized number per spec ✓.

### Pillar 5: Spacing (3/4)

**PASS — scale discipline:**
- Heatmap of spacing classes: every value in active use is a Tailwind 4 multiple-of-4 (`p-1, p-2, p-3, p-4, p-6, p-8, p-12, p-16` — all on the 4px grid).
- Container widths match spec: `max-w-7xl mx-auto px-8 py-8` on `/scans`, `/settings/*` ✓.
- Sidebar `xl:w-[220px]` ✓ (sub-token, justified — sidebar fixed width).
- Header strips `h-[52px]` (`MetadataHeader.tsx:59`, `CompareLayout.tsx:51`) ✓.
- Top bar `h-12` (48px) ✓.
- Touch targets: most icon buttons are `px-3 py-1.5` ≈ 32px tall — slightly **below** the 36px minimum the spec's hit-target paragraph mandates; close to acceptable but technically a drift.

**WARNING — home page gutters/gaps:**
- `app/(dashboard)/page.tsx:39` uses `max-w-7xl mx-auto px-6 py-6 flex flex-col gap-4`. Spec §`/` says `max-w-7xl mx-auto px-8 py-12 gap-12`. Three numerical drifts:
  - `px-6` (24px) instead of `px-8` (32px)
  - `py-6` (24px) instead of `py-12` (48px)
  - `gap-4` (16px) instead of `gap-12` (48px)
- Cumulative impact: the home dashboard feels visually compressed; the score card and sparkline read as one block instead of distinct sections.

**WARNING — section internal padding:**
- ScoreCard uses `p-6` ✓; ScoreSparkline uses `p-6` ✓; TopFindings uses `p-6` ✓; RecentScansTable title bar uses `px-6 py-4` ✓ — all spec-compliant.
- Settings cards use `p-4` (`integrations/page.tsx`) and `p-6` (`billing/page.tsx`) — inconsistent; spec doesn't lock card padding but visual consistency suggests `p-4` for compact integration rows / `p-6` for primary cards is fine.

**PASS — arbitrary values:**
- Survey of `[Npx]` arbitrary values returned only justified single-component primitives (52px header strip, 220px sidebar, 64px sparkline, 28px score, 380px diff rail, 400px viewer min-height, 200px modal min-height, 160/120px branch/sha truncation widths). No unjustified `[13px]` or `[7px]` ad-hoc values.

### Pillar 6: Experience Design (2/4)

**BLOCKER — no toast surface.**
- `grep "Toaster|sonner|<Toast"` against components+app: **zero hits**.
- UI-SPEC §"Interaction" requires `<Toaster/>` mounted at app root (`bottom-right, text-sm, max-width 360px`).
- UI-SPEC §"Copywriting Contract" lists 3 toast strings (`Link copied to clipboard`, `Share link revoked`, `Couldn't generate share link. Try again.`) — none of them can fire.
- Concrete impact: ShareModal copy-button silently fails when clipboard permission is denied (`ShareModal.tsx:106-109` has empty catch; the comment even says "No toast component shipped yet").

**BLOCKER — share-link management surface incomplete.**
- ShareModal renders a single static line `No share links yet for this scan.` (`ShareModal.tsx:249-251`) regardless of actual state. The spec's "Active share links" section showing `Expires {date} · Created by {Sam} · {with password / no password}` rows + `[Revoke]` text-link is not implemented.
- Code comment at `ShareModal.tsx:245-248` acknowledges: `TODO: GET /v1/scans/{id}/share-links not yet implemented in backend — ShareList deferred to a follow-on plan.` — confirms scope cut.
- Revoke `<AlertDialog/>` confirm flow with destructive copy is not implemented.

**WARNING — sparkline interaction stubbed:**
- `Sparkline.tsx` is a static SVG. UI-SPEC §`/` item 2 specifies "Hover (mouse on SVG): tooltip on closest point (`bg-slate-900 text-white text-xs px-2 py-1 rounded-sm`) showing `Score 87 · Apr 28`". Implementation has zero hover state, no tooltip, no mouseenter handler.

**WARNING — compare picker missing keyboard:**
- UI-SPEC §"Interaction": "Compare-picker modal: `↑` / `↓` to walk through results, `Enter` to compare." Not implemented in `ScanPickerModal.tsx`.
- `j`/`k` vim navigation on `/scans` table also not implemented (also spec'd).

**WARNING — scan-list filters missing custom range:**
- `ScanFilters.tsx:20-24` declares only `Last 7 days`, `Last 30 days`, `All time`. Spec has 4th option `Custom range…` opening a `<Popover/>` + `<Calendar/>` two-month range picker. `react-day-picker` is in `package.json` but unused.
- No source-icon support for the spec'd `GitHub webhook` reserved slot (only CLI / manual / github_webhook with the github option not in the dropdown).

**PASS — error/empty/loading states:**
- Loading: `ScansPage` has `<ScansTableSkeleton/>` with 10 animate-pulse rows ✓.
- Empty (no scans): `page.tsx:21-33` and `ScansTable.tsx:87-99` both render the spec's CLI-hint card ✓.
- Empty (filtered): `ScansTable.tsx:71-85` renders `No scans match your filters` + Clear all filters link ✓ matching spec exactly.
- Error 404: `scans/[id]/page.tsx:20` calls `notFound()` ✓; share `[token]` page maps backend 410/404 to spec'd dead-end cards ✓ (`share/[token]/page.tsx:73-113`).
- Loading state for scan diagram: `ScanViewerClient.tsx:71-76` renders `Loading scan diagram…` (no spinner) ✓ matches spec.
- Disabled state on Compare button: `ScanPickerModal.tsx:172-174` `disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed` ✓.
- Aria labels: 16 occurrences across modals + buttons; CompareButton ✓, ShareButton ✓, copy button ✓, sortable th's missing `aria-sort` (spec'd but not present).

**WARNING — focus rings:**
- `ScanPickerModal.tsx:121` uses `focus:ring-2 focus:ring-amber-300` on the search input — spec explicitly says **never** amber for focus, only `ring-slate-400`. Direct contract violation.
- `Slack` integration input uses `focus:ring-2 focus:ring-slate-400` ✓.
- Mixed implementation; should be normalized to slate-400 ring.

---

## Files Audited

**Routes (8):**
- `app/layout.tsx`
- `app/(dashboard)/layout.tsx`
- `app/(dashboard)/page.tsx`
- `app/(dashboard)/scans/page.tsx`
- `app/(dashboard)/scans/[id]/page.tsx`
- `app/(dashboard)/scans/compare/page.tsx`
- `app/(dashboard)/compare/page.tsx`
- `app/(dashboard)/settings/{layout,members,billing,integrations}/page.tsx`
- `app/(public)/share/[token]/page.tsx`

**Components (21):**
- `components/layout/{Sidebar,TopBar}.tsx`
- `components/home/{ScoreCard,ScoreSparkline,TopFindings,RecentScansTable}.tsx`
- `components/scans/{ScansTable,ScanFilters,SeverityBadge,Pagination,Sparkline,ScanPickerModal,ScanViewerClient,MetadataHeader,CompareButton,ShareButton}.tsx`
- `components/compare/{CompareLayout,DiffSummary,DiffNodeList,CompareViewerPair}.tsx`
- `components/share/{ShareViewer,ShareModal,PasswordGate}.tsx`

**Stylesheets (2):**
- `app/globals.css`
- `viewer/src/lib-styles.css` (token source-of-truth)

**Configuration:**
- `dashboard/package.json` (dependency surface)
- `dashboard/components.json` — **MISSING** (registry safety contract violation)

---

## Registry Safety

`components.json` does not exist; shadcn was never initialized. UI-SPEC §"Registry Safety" states "shadcn official: 17 blocks used; not required (gate)" — but the gate is moot because the blocks themselves are not installed. **No third-party registries declared, no third-party blocks audited.** The Phase 7 dashboard ships entirely without the design system the contract mandates; this is the dominant cross-cutting finding.

No suspicious-pattern flags raised; nothing to scan.
