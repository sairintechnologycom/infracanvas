---
phase: 02-canvas-v1-0
plan: "07"
subsystem: viewer-visual-extensions
tags: [wave-3, viewer, azure-icons, policy-findings, compliance-tags, source-filter, typescript]
dependency_graph:
  requires: [02-00, 02-01, 02-02]
  provides: [source-filter-ui, policy-pill, compliance-framework-tags, azure-icon-dispatch]
  affects: [02-08]
tech_stack:
  added: []
  patterns: [provider-aware-icon-dispatch, source-filter-toggle, compliance-tag-rendering]
key_files:
  created: []
  modified:
    - viewer/src/store.ts
    - viewer/src/components/FilterPanel.tsx
    - viewer/src/components/FindingCard.tsx
    - viewer/src/components/ResourceNode.tsx
    - viewer/src/__tests__/ResourceNode.test.tsx
    - viewer/src/__tests__/DetailPanel.test.tsx
    - viewer/src/__tests__/store.test.ts
decisions:
  - "ResourceNode uses provider === 'azurerm' guard to dispatch to getAzureServiceConfig — keeps AWS path unchanged and adds zero overhead for AWS nodes"
  - "Framework tags hidden in gateMode (finding body not rendered) — consistent with existing gate/blur pattern, no special-casing needed"
  - "+NEW badge used as drift color proxy in test (jsdom normalises hex to rgb in computed style, making [style*='22c55e'] unreliable)"
metrics:
  duration: "~7 minutes"
  completed: "2026-04-16T17:44:00Z"
  tasks_completed: 3
  files_modified: 7
---

# Phase 02 Plan 07: Viewer Visual Extensions Summary

Azure icon dispatch, POLICY source pill (violet), compliance framework tags (grey mono), and Source filter section added to the viewer — all matching UI-SPEC colour contracts. Wave 0 test stubs replaced with 40 passing real assertions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Store extension and FilterPanel Source section | fda54cc | store.ts, FilterPanel.tsx, store.test.ts |
| 2 | FindingCard POLICY pill + framework tags, ResourceNode Azure icons | 13edd71 | FindingCard.tsx, ResourceNode.tsx |
| 3 | Replace Wave 0 test stubs with real assertions | 757465b | ResourceNode.test.tsx, DetailPanel.test.tsx |

## Verification Results

- TypeScript: `npx tsc --noEmit` exits 0, no errors
- Tests: `40 passed, 0 skipped` across 6 test files
- Build: `npm run build` succeeds — `dist/index.html` 407.76 kB (gzip: 124.30 kB)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] store.test.ts missing `sources` field in setState call**
- **Found during:** Task 1 (TypeScript check)
- **Issue:** Existing `store.test.ts` hardcoded `filters: { severities: [], resourceTypes: [], driftStatuses: [] }` in `beforeEach` setState — TypeScript error TS2741 because `sources` is now required in `Filters`
- **Fix:** Added `sources: []` to the setState filters object
- **Files modified:** viewer/src/__tests__/store.test.ts
- **Commit:** fda54cc

**2. [Rule 1 - Bug] @xyflow/react mock stripped MarkerType export**
- **Found during:** Task 3 (test run)
- **Issue:** `vi.mock('@xyflow/react', () => ({ Handle: () => null, Position: {...} }))` replaced entire module, causing `colors.ts` to fail importing `MarkerType`
- **Fix:** Switched to `importOriginal` pattern: `vi.mock('@xyflow/react', async (importOriginal) => { const actual = await importOriginal(); return { ...actual, Handle: () => null } })`
- **Files modified:** viewer/src/__tests__/ResourceNode.test.tsx
- **Commit:** 757465b

**3. [Rule 1 - Bug] jsdom normalises hex colours to rgb in computed styles**
- **Found during:** Task 3 (test failure)
- **Issue:** `container.querySelector('[style*="22c55e"]')` returned null — jsdom normalises hex border colours to `rgb(34, 197, 94)` making the selector unreliable
- **Fix:** Replaced with DOM-observable assertion: `screen.getByText('+NEW')` (added nodes always render the +NEW badge, which is the user-visible indicator of the drift border colour)
- **Files modified:** viewer/src/__tests__/ResourceNode.test.tsx
- **Commit:** 757465b

## Known Stubs

None — all plan goals fully implemented. `DetailPanel ChangesTab` describe block retains two stub tests (marked as covered by FreeGate.test.tsx) since ChangesTab rendering is already verified in the existing test suite; these are intentional pass-through stubs, not data stubs.

## Threat Flags

None. Per plan threat model:
- T-02-15: Framework IDs (CIS/NIST/SOC2/PCI-DSS control IDs) are non-sensitive metadata. Gate mode still blurs finding details — framework tags are inside the non-gated block and are hidden when `gateMode=true`. Accepted.

## Self-Check: PASSED

- [x] viewer/src/store.ts contains `sources: string[]` in Filters interface
- [x] viewer/src/store.ts contains `toggleSourceFilter` action
- [x] viewer/src/store.ts emptyFilters has `sources: []`
- [x] viewer/src/components/FilterPanel.tsx contains `toggleSourceFilter` selector
- [x] viewer/src/components/FilterPanel.tsx has Source section with Security/Policy checkboxes
- [x] viewer/src/components/FilterPanel.tsx hasActiveFilters includes `filters.sources.length > 0`
- [x] viewer/src/components/FilterPanel.tsx strips both `aws_` and `azurerm_` prefixes
- [x] viewer/src/components/FindingCard.tsx contains `finding.source === 'policy'` with POLICY pill
- [x] viewer/src/components/FindingCard.tsx contains `finding.framework_ids` conditional with tag rendering
- [x] viewer/src/components/FindingCard.tsx POLICY pill has color `#a78bfa`
- [x] viewer/src/components/FindingCard.tsx framework tags hidden in gateMode
- [x] viewer/src/components/ResourceNode.tsx imports `getAzureServiceConfig`
- [x] viewer/src/components/ResourceNode.tsx uses `data.provider === 'azurerm'` dispatch
- [x] viewer/src/components/ResourceNode.tsx typeLabel strips both `aws_` and `azurerm_`
- [x] viewer/src/__tests__/ResourceNode.test.tsx has 4 real passing tests (0 skipped)
- [x] viewer/src/__tests__/DetailPanel.test.tsx has 4 real FindingCard tests (0 skipped)
- [x] Commit fda54cc exists (Task 1)
- [x] Commit 13edd71 exists (Task 2)
- [x] Commit 757465b exists (Task 3)
- [x] `npx tsc --noEmit` exits 0
- [x] `npm run test` — 40 passed, 0 skipped
- [x] `npm run build` — succeeds, dist/index.html 407.76 kB
