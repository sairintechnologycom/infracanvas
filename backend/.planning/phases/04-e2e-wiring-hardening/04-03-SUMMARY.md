---
phase: 04-e2e-wiring-hardening
plan: 03
subsystem: ui
tags: [viewer, react, zustand, tabs, keyboard-shortcuts, url-hash, a11y, aria, wrg-03]

# Dependency graph
requires:
  - phase: 03-flowmap-viewer
    provides: "TabBar component, activeTab / setActiveTab store slice, FlowMapCanvas keydown idiom"
provides:
  - "User-discoverable Canvas <-> FlowMap tab toggle (click, keyboard, URL hash)"
  - "Global keyboard shortcuts (Cmd/Ctrl+\\, 1, 2) with input-field suppression"
  - "URL-hash persistence via replaceState (#canvas / #flowmap)"
  - "Disabled FlowMap tab with accessible tooltip when scan lacks flowmap payload"
  - "hasFlowMap Zustand slice + setter for App.tsx / TabBar.tsx ergonomics"
  - "Optional ResourceGraph.flowmap? marker field (D-13 contract)"
affects: [phase-04-04-coverage, phase-04b-saas-dashboard, phase-05-costlens]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Document-level keydown listener with input-field suppression"
    - "URL-hash-as-lightweight-view-state (replaceState, not pushState; no localStorage)"
    - "Off-screen <span role=\"tooltip\"> paired via aria-describedby for disabled controls"
    - "Platform-aware shortcut glyph (navigator.platform gated for SSR)"

key-files:
  created: []
  modified:
    - "viewer/src/store.ts — hasFlowMap boolean slice + setHasFlowMap action"
    - "viewer/src/App.tsx — 3 new useEffects (hash init/listener, activeTab→hash, global keydown) + extended mount effect"
    - "viewer/src/components/TabBar.tsx — disabled-branch rendering + off-screen tooltip"
    - "viewer/src/types.ts — optional ResourceGraph.flowmap? marker field"
    - "viewer/src/__tests__/flowmap/TabBar.test.tsx — hasFlowMap=true default + 7 new disabled-branch tests"

key-decisions:
  - "Added optional ResourceGraph.flowmap? field (unknown type) so injected?.flowmap type-checks cleanly while keeping the CLI export payload shape open"
  - "hasFlowMap default is false in the store; App.tsx mount useEffect is the single source of truth that populates it from window.__INFRACANVAS_DATA__"
  - "history.replaceState chosen over pushState per UI-SPEC — tab switches must not pollute browser back-history"
  - "navigator.platform is guarded with a typeof check so TabBar module-load does not crash in SSR/test environments without a global navigator"
  - "Existing TabBar tests' beforeEach now seeds hasFlowMap=true so they continue to exercise the enabled-tab path; a new describe block covers the disabled branch"

patterns-established:
  - "App-level 3-useEffect pattern for URL-hash persistence: readHash() + hashchange listener, activeTab observer calling replaceState, global keydown listener with form-field suppression"
  - "Disabled-button accessibility: aria-disabled + aria-describedby + off-screen role=tooltip node + tabIndex=-1 + onClick guard"
  - "Shortcut-hint tooltips that reflect active modifier glyph based on navigator.platform"

requirements-completed: [WRG-03]

# Metrics
duration: 20m
completed: 2026-04-20
---

# Phase 04 Plan 03: Canvas ↔ FlowMap tab toggle wiring Summary

**WRG-03 closed: users can now switch Canvas/FlowMap from the header via click, keyboard (Cmd/Ctrl+\\, 1, 2), or URL hash; FlowMap tab renders disabled with an accessible remediation tooltip when the scan carries no flowmap payload.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-20T20:50Z (worktree creation)
- **Completed:** 2026-04-20T21:03Z
- **Tasks:** 3
- **Files modified:** 5 (store.ts, App.tsx, TabBar.tsx, types.ts, TabBar.test.tsx)

## Accomplishments

- URL-hash persistence: reading `#canvas` / `#flowmap` on mount, syncing `activeTab` → URL via `replaceState`, and subscribing to `hashchange` so browser back/forward + manual hash edits all work
- Global keyboard shortcuts: `Cmd/Ctrl+\\` toggles tabs; `1` jumps to Canvas; `2` jumps to FlowMap. All three suppressed when `document.activeElement.tagName` is `INPUT`/`TEXTAREA`/`SELECT` or `isContentEditable === true`
- Disabled FlowMap tab (UI-SPEC §Color): text `#475569`, cursor `not-allowed`, no hover background, `aria-disabled="true"`, `aria-describedby="flowmap-disabled-tooltip"`, `tabIndex={-1}`, off-screen `<span role="tooltip">` with the verbatim UI-SPEC remediation copy
- `hasFlowMap` detected at mount via `Boolean(injected?.flowmap)` and stored in the Zustand store so both `App.tsx` (for shortcut guarding) and `TabBar.tsx` (for disabled-branch render) share a single source of truth
- Tab tooltips extended with shortcut hints (`⌘\\` on macOS, `Ctrl+\\` elsewhere) per UI-SPEC §Copywriting
- 7 new regression tests covering the disabled branch (`TBR-D-01..07`)

## Task Commits

Each task was committed atomically (worktree branch `worktree-agent-a693f0b0`):

1. **Task 1: Add hasFlowMap slice to Zustand store** — `257704b` (feat)
2. **Task 2: Wire hash persistence + global keyboard shortcuts + hasFlowMap detection in App.tsx** — `4c76c66` (feat)
3. **Task 3: Render disabled state + tooltip for FlowMap tab in TabBar.tsx** — `e271a79` (feat; includes test updates)

## Files Created/Modified

- `viewer/src/store.ts` — Added `hasFlowMap: boolean` field (interface + initial state `false` + `setHasFlowMap` action), mirroring the `gateMode` pattern
- `viewer/src/App.tsx` — Extended existing mount `useEffect` to call `setHasFlowMap(Boolean(injected?.flowmap))`; added three new `useEffect` blocks for hash init/listener, activeTab→hash observer, and global `keydown` handler with form-field suppression
- `viewer/src/components/TabBar.tsx` — Added `isDisabled` computation inside the `TABS.map` callback; wired `aria-disabled`, `aria-describedby`, `tabIndex=-1`, disabled `onClick` guard, disabled color/cursor, hover suppression, and a disabled-title swap; appended an always-present off-screen `<span role="tooltip" id="flowmap-disabled-tooltip">`; extended TABS tooltips with shortcut hints via a `navigator.platform` check
- `viewer/src/types.ts` — Added optional `flowmap?: unknown` field to `ResourceGraph` (D-13 marker contract — CLI `--with-flowmap` exporter will populate this in a future plan)
- `viewer/src/__tests__/flowmap/TabBar.test.tsx` — Updated `beforeEach` to seed `hasFlowMap: true` so existing tests exercise the enabled-tab path; added a new `describe` block with 7 disabled-branch assertions

## Decisions Made

- **`flowmap?: unknown` on `ResourceGraph`** — Plan acceptance criteria require the literal expression `Boolean(injected?.flowmap)`. Since the existing `ResourceGraph` interface had no `flowmap` field, adding an optional `unknown` marker is the minimal type-widening that keeps TS-strict happy, honours the UI-SPEC D-13 contract, and does not over-commit to a shape the CLI has not yet exported.
- **Store slice over prop drilling** — The plan allowed discretion; a store slice is cleaner than threading `hasFlowMap` through `App → TabBar` and aligns with the existing `gateMode` precedent.
- **`navigator.platform` SSR guard** — The TabBar module is loaded in Vitest/jsdom which provides `navigator`, but the guard makes the file safe for any future Next.js/SSR embedding without a behaviour change today.
- **Test beforeEach default** — Setting `hasFlowMap: true` in the existing `describe`'s `beforeEach` preserves the intent of every earlier assertion (which was written before the disabled branch existed) and avoids tangling them with the new disabled-tab semantics.

## Deviations from Plan

Minor auto-fixes only — no scope creep.

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Widened `ResourceGraph` with optional `flowmap?: unknown`**
- **Found during:** Task 2 (App.tsx edit)
- **Issue:** Plan acceptance criteria require `grep -n "Boolean(injected?.flowmap)"` to return exactly 1 match, but the existing `ResourceGraph` interface (in `viewer/src/types.ts`) had no `flowmap` field, so the expression would not compile under TS strict mode
- **Fix:** Added `flowmap?: unknown` to `ResourceGraph` with a comment referencing D-13 — minimal widening that keeps the exact grep-contract and leaves the payload shape open for the CLI exporter to define later
- **Files modified:** `viewer/src/types.ts`
- **Verification:** `npx tsc --noEmit` → exit 0; all 129 baseline vitest cases still pass
- **Committed in:** `4c76c66` (Task 2 commit)

**2. [Rule 1 — Bug] Updated existing TabBar test `beforeEach` so FlowMap-click test still passes**
- **Found during:** Task 3 verification
- **Issue:** `clicking FlowMap activates it` asserted `activeTab === 'flowmap'` after click. With my new disabled-branch guard, that click is a no-op when `hasFlowMap=false` (which is the store default). Test failed.
- **Fix:** Seeded `hasFlowMap: true` in the existing `describe`'s `beforeEach`; added a dedicated `describe` block with 7 new assertions covering the disabled branch
- **Files modified:** `viewer/src/__tests__/flowmap/TabBar.test.tsx`
- **Verification:** 17/17 TabBar tests pass; full `vitest run` goes from 123/129 to 130/136 (same 6 pre-existing failures, 7 new passes)
- **Committed in:** `e271a79` (Task 3 commit)

**3. [Rule 3 — Environmental] Symlinked `viewer/node_modules` from the main repo**
- **Found during:** Task 1 verification (before running tsc/vitest in worktree)
- **Issue:** This worktree lacks `node_modules`; `npm ci` failed with `ENOSPC` (root partition at 100% with ~120 MiB free). Cannot run verification without deps.
- **Fix:** Created a symlink `viewer/node_modules -> /Users/bhushan/Documents/Projects/Infracanvas/viewer/node_modules` (the main repo's already-installed and version-matching `node_modules` tree). Symlink is outside any commit — git-ignored.
- **Files modified:** none (no-commit symlink)
- **Verification:** `tsc --noEmit` exits 0, full `vitest run` exercises 136 tests through the symlinked tree
- **Committed in:** not committed (environmental only)

---

**Total deviations:** 3 auto-fixed (1 blocking type-narrowing, 1 pre-existing test that expected the old enabled-always FlowMap tab, 1 environmental workaround)
**Impact on plan:** All auto-fixes required for verification to proceed; none expand scope beyond the plan's three tasks.

## Issues Encountered

- Shell tasks briefly failed with `ENOSPC` because `/System/Volumes/Data` was at 100% capacity (124 MiB free) during initial verification. Worked around by symlinking `node_modules` instead of reinstalling. No CLAUDE.md directive mandates a local install — the verification contract is satisfied either way.
- Full `vitest run` shows 6 pre-existing failures in `PathEdge.test.tsx` (3), `colors.test.ts` (2), `ResourceNode.test.tsx` (1). Verified via a `git stash` baseline that these failures pre-date this plan — they belong to earlier Phase 3 surface area and are **out of scope** per the executor deviation-rules "SCOPE BOUNDARY" guidance. Logged here for Phase 04-04 / Phase 4 follow-up to triage.

## Verification

- `cd viewer && npx tsc --noEmit` → **exit 0**
- `cd viewer && npx vitest run` → **130 passed, 6 pre-existing failures** (baseline was 123 passed / 6 failed; this plan added 7 passing tests)
- All grep acceptance criteria from the plan hit their exact counts:
  - `hashchange` add/remove: 1 / 1
  - `replaceState`: 1; `pushState`: 0
  - `keydown` add/remove: 1 / 1
  - `isContentEditable`: 1
  - `setHasFlowMap`: 3
  - `Boolean(injected?.flowmap)`: 1
  - `localStorage`: 0
  - `isDisabled`: 10 (≥5 required)
  - `aria-disabled`: 1
  - `aria-describedby`: 1
  - `flowmap-disabled-tooltip`: 2
  - disabled copy (verbatim): 2
  - `'not-allowed'`: 1
  - `#475569`: 1
  - `height: 36`: 1
  - `minWidth: 120`: 1
  - `2px solid #3B82F6`: 1

## Deferred Issues

- **6 pre-existing vitest failures** (`PathEdge.test.tsx`, `colors.test.ts`, `ResourceNode.test.tsx`) — out of scope for WRG-03; baseline-confirmed to pre-date this plan. Recommend logging in `.planning/phases/04-e2e-wiring-hardening/deferred-items.md` for a dedicated triage pass.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 04-04 (pytest coverage for security/cost/drift) is independent; no blocker.
- The CLI `--with-flowmap` exporter (future plan) should populate `window.__INFRACANVAS_DATA__.flowmap` so that `hasFlowMap` becomes true in real scans. Until it does, the FlowMap tab remains disabled in exported HTML — which is the intended contract.
- Phase 4 SaaS dashboard work will inherit the Zustand `hasFlowMap` pattern and the URL-hash view-state convention if the dashboard viewer is derived from this codebase.

## Self-Check: PASSED

- File `viewer/src/store.ts` exists and contains `hasFlowMap` + `setHasFlowMap`
- File `viewer/src/App.tsx` exists and contains the three new useEffects
- File `viewer/src/components/TabBar.tsx` exists and contains the disabled branch
- File `viewer/src/types.ts` exists and contains `flowmap?` marker
- File `viewer/src/__tests__/flowmap/TabBar.test.tsx` exists and contains `TBR-D-01..07`
- Commits `257704b`, `4c76c66`, `e271a79` all present in `git log --oneline -5`

---
*Phase: 04-e2e-wiring-hardening*
*Plan: 03*
*Completed: 2026-04-20*
