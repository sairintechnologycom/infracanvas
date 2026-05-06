---
phase: 03-flowmap-v1-0
plan: 08
subsystem: viewer
tags: [flowmap, panels, empty-state, colors, ui-spec, tdd]
dependency-graph:
  requires:
    - "viewer/src/types.ts NetworkPath + DCSite interfaces (Plan 03-01)"
    - "viewer/src/components/FindingCard.tsx (existing, reused verbatim)"
    - "viewer/src/components/FilterPanel.tsx (dark-chrome template mirrored)"
    - "viewer/src/components/DetailPanel.tsx (header+tabs pattern mirrored)"
  provides:
    - "FlowMapFilterPanel — 224px dark panel wired to flowMapFilters store slice"
    - "PathDetailPanel — 320px dark panel with Routes tab + FindingCard reuse"
    - "FlowMapEmptyState — centered card with Copy-command CTA + Beta pill"
    - "flowmapPathColors const (5 keys) in viewer/src/lib/colors.ts"
    - "--color-flow-forward / --color-flow-return / --color-flow-divergence CSS vars in @theme"
    - "flowMapFilters + activeTab + selectedPath store slices (coordinated shape with Plan 03-06)"
  affects:
    - "viewer/src/store.ts — extended with FlowMap slices (shape-identical to Plan 03-06 to avoid merge conflict)"
tech-stack:
  added: []
  patterns:
    - "Bare Tailwind + inline styles (no shadcn, no Radix — per UI-SPEC Design System Alignment)"
    - "useStore selector-per-slice subscription pattern (matches FilterPanel idiom)"
    - "const-as-assertion export for color tokens (flowmapPathColors)"
key-files:
  created:
    - "viewer/src/components/flowmap/FlowMapFilterPanel.tsx"
    - "viewer/src/components/flowmap/PathDetailPanel.tsx"
    - "viewer/src/components/flowmap/FlowMapEmptyState.tsx"
    - "viewer/src/__tests__/flowmap/FlowMapFilterPanel.test.tsx"
    - "viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx"
    - "viewer/src/__tests__/flowmap/FlowMapEmptyState.test.tsx"
  modified:
    - "viewer/src/store.ts (extended with flowMapFilters / activeTab / selectedPath slices)"
    - "viewer/src/lib/colors.ts (appended flowmapPathColors const)"
    - "viewer/src/index.css (added 3 --color-flow-* CSS vars to @theme block)"
decisions:
  - "store.ts was extended in this worktree despite Plan 03-06 owning the file — needed so tests + typecheck pass in isolation. Shape is byte-identical to Plan 03-06's spec (plan lines 162-236) so a textual merge is clean. Orchestrator should resolve by taking either side."
  - "FlowMapEmptyState is NOT wired into FlowMapCanvas in this worktree (per objective). The single-line swap (return null → return <FlowMapEmptyState />) is deferred to the post-merge orchestrator step, at which point Plan 03-07's FlowMapCanvas.tsx exists on main."
  - "Routes tab renders only for TGW route-table / VPC route table / vWAN hub node types (ROUTES_ELIGIBLE_TYPES set). Falls through to 'No routes collected' when node.attributes.routes is absent."
  - "Path-selected content mode in PathDetailPanel is intentionally cold in 3a (selectedPath is never populated; falls back to empty-state body). UI-SPEC §PathDetailPanel confirms this is the correct 3a behavior — 3b will populate selectedPath via PathEdge click."
metrics:
  duration: "≈40m (context load + RED/GREEN cycles + verification)"
  tasks: 3
  files-created: 6
  files-modified: 3
  tests-added: 14
  completed: "2026-04-19"
---

# Phase 03 Plan 08: FlowMap FilterPanel + PathDetailPanel + EmptyState + Color Tokens Summary

Shipped the remaining viewer-half of FMV-05: a 224px FlowMapFilterPanel with four filter sections wired to the Zustand `flowMapFilters` slice, a 320px PathDetailPanel with a new Routes tab that reuses FindingCard verbatim for NET-* findings, a 520px centered FlowMapEmptyState card carrying the exact UI-SPEC copy and a clipboard-backed Copy button, plus `flowmapPathColors` in lib/colors.ts and three new `--color-flow-*` CSS vars in the @theme block.

## What landed

### FlowMapFilterPanel (224px, dark chrome parity)

- Background `#161b27`, border-right `1px solid #252d3d`, eyebrow labels `#4a5568`. Matches FilterPanel verbatim.
- Four sections in strict UI-SPEC order: Severity (checkbox + finding-count badge over network-type nodes), Cloud (tri-state radio pills with AWS orange / Azure blue / slate rings), Node Type (11 options, hides zero-count types), Flow Logs (single toggle row).
- Header Clear button appears only when any filter is active. Close button toggles `filterPanelOpen` (shared with Canvas tab).
- All 5 vitest assertions pass: render, conditional hide, AWS pill click → store update, severity toggle → store array mutation, Clear button → full reset to defaults.

### PathDetailPanel (320px, 3 content modes)

- Empty mode: centered Network icon + "Select a node" + body copy ("Click any TGW, VPC, vWAN hub, vNet, or ExpressRoute circuit …").
- Node-selected mode: type pill + name + id header, then 4 tabs (Overview / Findings / Attributes / Routes). Routes tab only for `aws_ec2_transit_gateway_route_table`, `aws_route_table`, `azurerm_virtual_hub`.
- Routes table columns: Destination CIDR (mono) | Source (plain) | State (green when active/available, amber otherwise). Empty state: "No routes collected for this node."
- Findings tab imports `FindingCard` verbatim from `viewer/src/components/FindingCard.tsx` — NET-* findings carry the existing `Finding` shape (source, framework_ids, evidence) so no visual divergence.
- All 5 vitest assertions pass.

### FlowMapEmptyState (520px card)

- Full UI-SPEC copy: heading "No network topology collected yet", body line 1 (FlowMap needs …), CLI block `infracanvas scan ./terraform --flowmap`, body line 2 (creds chain …), secondary link "Read the FlowMap docs →" with `rel="noopener noreferrer"` (T-03-08-02 mitigation).
- Copy button: `navigator.clipboard.writeText(COMMAND)` in a try/catch; success morphs to "Copied ✓" green `#22C55E` for 2 seconds. Silent fallback on non-HTTPS contexts (T-03-08-05 accepted).
- Beta pill: bottom-right `rgba(217,119,6,0.12)` bg + `#D97706` text + rounded 4px.
- `role="status"` on the outer container so screen readers announce the empty state.
- All 4 vitest assertions pass.

### Color tokens

- `viewer/src/lib/colors.ts` appended `export const flowmapPathColors = { forward, return, divergence, flowOk, flowStale } as const;` — byte-for-byte match to UI-SPEC §Design System Alignment color reference.
- `viewer/src/index.css` @theme block appended three CSS vars: `--color-flow-forward: #3B82F6`, `--color-flow-return:  #F97316`, `--color-flow-divergence: #EF4444`. PathEdge (Plan 03-07) will consume these in 3b.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Extended `viewer/src/store.ts` with flowMapFilters slice**

- **Found during:** Task 1 RED phase — test imports `s.flowMapFilters`, `s.toggleFlowMapSeverity`, etc. which do not exist in the base commit's `store.ts`.
- **Issue:** Plan 03-06 (parallel wave) owns the store extension but has not landed on main. Without the slice, `npx tsc --noEmit` fails, the RED gate cannot fire cleanly, and the GREEN component cannot mount the store actions.
- **Fix:** Inserted the slice byte-for-byte per Plan 03-06 lines 162-236 (types above StoreState, interface fields, initializer entries, actions). Shape is:
  - `activeTab: 'canvas' | 'flowmap'` (default `'canvas'`)
  - `flowMapFilters: { severities, cloud, nodeTypes, hasFlowLogs }`
  - `selectedPath: NetworkPath | null`
  - Actions: `setActiveTab`, `toggleFlowMapSeverity`, `setFlowMapCloud`, `toggleFlowMapNodeType`, `toggleFlowMapFlowLogs`, `clearFlowMapFilters`, `setSelectedPath`
- **Files modified:** `viewer/src/store.ts`
- **Commit:** `47e9848`
- **Merge-coordination note:** When Plan 03-06's worktree merges, the orchestrator will see identical text on both sides. Resolution: take either side. If 03-06 drifts from its spec (e.g., adds `setSelectedHop` or renames a field), the merge resolver should take 03-06's version and adjust this plan's consumers accordingly. No consumer in 03-08 references anything beyond the spec-listed shape.

### Intentional omission (per plan objective)

- **FlowMapCanvas.tsx NOT modified.** Plan 03-08 was instructed to "LEAVE INTEGRATION INTO FlowMapCanvas FOR THE POST-MERGE STEP". FlowMapEmptyState is importable from its own file. The one-line swap (`return null` → `return <FlowMapEmptyState />`) happens after Plans 03-07 and 03-08 both merge to main. This is not a deviation — it is the plan.

## Verification

- `npx tsc --noEmit` — clean (0 errors) across both worktree and main-repo mirror.
- `npx vitest run src/__tests__/flowmap/` — 14/14 tests pass (5 FlowMapFilterPanel + 5 PathDetailPanel + 4 FlowMapEmptyState).
- `npx vitest run` (full suite) — 79 pass / 3 fail. The 3 failures are pre-existing in `src/__tests__/colors.test.ts` on `ZONE_COLORS.regional.background` + `ZONE_COLORS.category.pillText`; they exist on the base commit and are out of scope for this plan (documented below).

## Deferred Issues

- **[pre-existing] `viewer/src/__tests__/colors.test.ts` — ZONE_COLORS regional/category test regressions.** 3 assertions expect `#FFFFFF` or a specific pillText hex but the file has `transparent` / `#64748B` after a prior light-theme refactor. Not caused by Plan 03-08. Recommended to open a follow-up test-cleanup task after Phase 3a closes.

## Panel-width and clipboard confirmation

- FlowMapFilterPanel: `w-56` (Tailwind 14rem = 224px) — matches UI-SPEC parity.
- PathDetailPanel: `w-80` (Tailwind 20rem = 320px) — matches UI-SPEC parity. Note: `w-80` appears twice in the component source (once for empty-state wrapper, once for node-selected wrapper). Both render 320px; the grep returns 2 which is expected.
- Clipboard API: vitest test `Copy button calls clipboard API` mocks `navigator.clipboard.writeText` via `Object.assign(navigator, { clipboard: { writeText: vi.fn() } })` and asserts invocation with the exact CLI command. Pass.

## Phase 3a handoff

Plan 03-08 completes the viewer half of Phase 3a (alongside Plans 03-06 Wave-2 store+TabBar+App and 03-07 Wave-2 FlowMapCanvas+nodes+edges). After all five Wave-2 plans merge, the orchestrator must perform ONE post-merge edit to close the empty-state contract:

- **Edit `viewer/src/components/flowmap/FlowMapCanvas.tsx`:**
  1. Add `import { FlowMapEmptyState } from './FlowMapEmptyState';` at the top.
  2. Replace `if (isEmpty) return null;` with `if (isEmpty) return <FlowMapEmptyState />;`.

That single edit closes D-08 (the empty-state flow). Orchestrator should then run `cd viewer && npx tsc --noEmit && npx vitest run && npm run build` as the phase-3a close-out verification before transitioning to 3b roadmap insertion.

## Threat Flags

No new security-relevant surface beyond the plan's threat model. `JSON.stringify` in AttributesTab renders as JSX text content (T-03-08-01 mitigated by React auto-escape); docs link uses `rel="noopener noreferrer"` (T-03-08-02 mitigated).

## Self-Check: PASSED

- FOUND: viewer/src/components/flowmap/FlowMapFilterPanel.tsx
- FOUND: viewer/src/components/flowmap/PathDetailPanel.tsx
- FOUND: viewer/src/components/flowmap/FlowMapEmptyState.tsx
- FOUND: viewer/src/lib/colors.ts (modified)
- FOUND: viewer/src/index.css (modified)
- FOUND: viewer/src/__tests__/flowmap/FlowMapFilterPanel.test.tsx
- FOUND: viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx
- FOUND: viewer/src/__tests__/flowmap/FlowMapEmptyState.test.tsx
- FOUND: commit fa2ea80 (test RED — FlowMapFilterPanel)
- FOUND: commit 47e9848 (feat GREEN — FlowMapFilterPanel + store slice)
- FOUND: commit 9ffa87e (test RED — PathDetailPanel)
- FOUND: commit 9ff9adb (feat GREEN — PathDetailPanel)
- FOUND: commit 603ce0a (test RED — FlowMapEmptyState)
- FOUND: commit 9af1283 (feat GREEN — FlowMapEmptyState + colors + css)
- FlowMapCanvas.tsx not modified (owned by Plan 03-07, integration deferred to post-merge).
