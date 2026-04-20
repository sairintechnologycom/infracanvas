---
phase: 4
slug: e2e-wiring-hardening
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-20
---

# Phase 4 — UI Design Contract

> Visual and interaction contract for the single viewer-facing change in Phase 4 (WRG-03: Canvas ↔ FlowMap tab toggle). WRG-01, WRG-02, and WRG-04 are CLI-only and introduce no UI surface. This spec formalizes the existing dark-header segmented-tab pattern already present in `viewer/src/components/TabBar.tsx` and locks the three additive deltas Phase 4 must implement: URL-hash persistence, keyboard shortcuts, and disabled-with-tooltip when FlowMap payload is absent.

---

## Scope

| Requirement | UI Surface? | Spec Section |
|-------------|-------------|--------------|
| WRG-01 CLI exit codes + `--gate-mode` | No (CLI stdout/stderr only) | Out of scope |
| WRG-02 Drift counts (5 keys sum to node count) | No (CLI summary only; D-08 explicitly defers viewer badges) | Out of scope |
| WRG-03 Canvas ↔ FlowMap tab toggle | **Yes** | Entire spec |
| WRG-04 pytest coverage (security/cost/drift) | No (CI test matrix, no UI) | Out of scope |

**Delta from existing viewer:** `TabBar.tsx` already renders a dark-header tablist at `height: 36`, `background: #0f1419`, with Canvas/FlowMap buttons, ArrowLeft/ArrowRight/Home/End keyboard nav, `role="tablist"`/`role="tab"`/`aria-selected`, a BETA pill on FlowMap, and a tooltip via `title`. Phase 4 adds three behaviors without re-skinning:

1. URL-hash persistence (`#canvas` / `#flowmap`) — init + sync on change.
2. Global keyboard shortcuts `Cmd/Ctrl+\` (toggle), `1` (Canvas), `2` (FlowMap), ignored when focus is inside input/textarea/select.
3. Disabled state + tooltip on the FlowMap tab when `window.__INFRACANVAS_DATA__.flowmap` is absent.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (manual tokens in `viewer/src/index.css` via Tailwind 4 `@theme`) |
| Preset | not applicable |
| Component library | none — custom React components; @xyflow/react for canvas; no Radix/Base UI |
| Icon library | lucide-react 0.511.0 (primary); aws-react-icons 3.3.0 (resource glyphs) |
| Font | Inter (sans, default), JetBrains Mono (mono) — both bundled via @fontsource |

Source: `viewer/package.json`, `viewer/src/index.css` `@theme` block, existing `TabBar.tsx`.

---

## Spacing Scale

Declared values (all multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps in the tab label (between "FlowMap" text and BETA pill) |
| sm | 8px | Gap between tab label text and inline badge |
| md | 16px | Horizontal padding inside each tab button (`padding: '0 16px'`) |
| lg | 20px | Left padding of the tablist container (`paddingLeft: 20`) |
| xl | 32px | Reserved — not used by tabbar |

**Tab-specific fixed dimensions (load-bearing, preserve as-is):**

| Dimension | Value | Rationale |
|-----------|-------|-----------|
| Tablist height | 36px | Keeps the header stack (SummaryBar 48 + TabBar 36 = 84px chrome) under 100px so canvas real estate stays ≥ `calc(100vh - 84px)` |
| Tab min-width | 120px | Prevents label reflow when switching between "Canvas" (6ch) and "FlowMap" + BETA (13ch) |
| Active underline thickness | 2px | Existing `borderBottom: '2px solid #3B82F6'` contract |
| BETA pill padding | 1px × 6px | Existing inline-label density; must remain readable at 10px text |
| Disabled-tab tooltip offset | 6px below tab bottom edge | Matches existing `#edge-legend-tooltip` offset of 8px in SummaryBar (close enough family) |

Exceptions: The 36px tablist height is intentionally **not** on the 8-point scale — it is an existing contract from Phase 3 that must not change to avoid visual regression. Justified.

---

## Typography

| Role | Size | Weight | Line Height | Used For |
|------|------|--------|-------------|----------|
| Tab label (inactive) | 12px | 500 | 1.0 (flex-centered) | Canvas/FlowMap text when unselected |
| Tab label (active) | 12px | 700 | 1.0 (flex-centered) | Canvas/FlowMap text when selected |
| BETA pill | 10px | 600 | 1.4 | Inline badge next to "FlowMap" label |
| Disabled tooltip | 12px | 500 | 1.5 | Tooltip body when FlowMap is disabled |
| Shortcut hint in tooltip | 10px | 500 | 1.4 | Kbd hint `⌘\ · 1 · 2` rendered inside the title tooltip |

Four sizes (12, 10) × two weights (500, 600/700) — inside the ≤4 sizes / ≤2 weights budget when treated as a single "label weight family" (500 regular / 700 bold, with 600 as a de-facto semibold already used elsewhere in SummaryBar — documented but not introduced here).

Font family for all text: Inter (`--font-sans`).

---

## Color

The viewer has a two-register palette: **light canvas area** (`#FAFBFC`) and **dark header/chrome** (`#0f1419` → `#1a202c` gradient). The tab toggle lives in the dark register.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0f1419` | Tablist background, matches SummaryBar gradient start |
| Secondary (30%) | `#252d3d` | Tablist border-bottom (`1px solid`), separates tabs from panel |
| Accent (10%) | `#3B82F6` | Active tab underline (2px) + active-tab background tint `rgba(59,130,246,0.08)` |
| Destructive | `#ef4444` | Not used by tab toggle (reserved for Critical severity elsewhere) |

**Accent `#3B82F6` is reserved for these specific tab-toggle elements ONLY in this phase:**

1. Active-tab bottom underline (2px solid).
2. Active-tab background wash at 8% opacity (`rgba(59,130,246,0.08)`).
3. Focus ring on a tab button when keyboard-focused (browser default `outline` with `outlineOffset: 2`).

The accent is NOT used for hover states — hover uses neutral `#94A3B8` text + `rgba(45,55,72,0.3)` background. This preserves the "accent = current selection" signal.

**Text color states on tab buttons:**

| State | Text Color | Rationale |
|-------|-----------|-----------|
| Active | `#F1F5F9` | Near-white, highest legibility |
| Inactive | `#64748B` | Slate-500, clearly secondary |
| Inactive-hover | `#94A3B8` | Slate-400, midpoint reveal |
| Disabled (no FlowMap data) | `#475569` | Slate-600, noticeably dimmer than inactive — communicates non-interactivity |

**Disabled tab visual contract (new in Phase 4):**

- Text: `#475569` (dimmer than inactive `#64748B`)
- Background: `transparent` (no hover background even on hover)
- Cursor: `not-allowed`
- Opacity: 1.0 (use text color, not opacity, to dim — preserves BETA pill contrast which stays at full opacity)
- Tooltip appears on hover/focus with the copy specified in Copywriting section

**BETA pill (unchanged):** background `rgba(217,119,6,0.12)`, text `#D97706`. Inherited from existing TabBar; do not alter.

---

## Interaction Contract

### URL Hash Persistence (D-11)

| Event | Behavior |
|-------|----------|
| Mount | Read `window.location.hash`; if `#flowmap`, set `activeTab='flowmap'`; else default `'canvas'` (covers `#canvas`, empty, and unknown hashes — unknown hashes silently fall through to Canvas, no error toast). |
| `setActiveTab('flowmap')` | Call `history.replaceState(null, '', '#flowmap')`. Use `replaceState` not `pushState` — tab switches should not pollute browser history. |
| `setActiveTab('canvas')` | Call `history.replaceState(null, '', '#canvas')`. |
| `hashchange` event | Sync `activeTab` to match new hash (supports browser back/forward and manual hash edits). |

No localStorage. No URL query params. Hash only.

### Keyboard Shortcuts (D-12)

| Shortcut | Action | Scope |
|----------|--------|-------|
| `Cmd+\` (macOS) / `Ctrl+\` (Linux/Win) | Toggle between Canvas and FlowMap | Global, document-level listener |
| `1` | Jump to Canvas | Global, document-level listener |
| `2` | Jump to FlowMap | Global, document-level listener |
| ArrowLeft / ArrowRight / Home / End | Navigate between tabs | Tablist-scoped (existing behavior, preserve) |

**Suppression rule:** Global shortcuts (`Cmd/Ctrl+\`, `1`, `2`) must be ignored when `document.activeElement` is one of: `<input>`, `<textarea>`, `<select>`, or any element with `contenteditable="true"`. This prevents the SearchBar (`SummaryBar.tsx`) from swallowing search digits. Implementation: early return in the keydown handler if `target.tagName` matches that set or `target.isContentEditable === true`.

**Disabled-tab shortcut behavior:** If FlowMap has no data, pressing `2` or `Cmd+\` (when on Canvas) is a no-op. Do not show a toast. The tooltip on hover/focus is the sole affordance that communicates why.

### Disabled State Detection (D-13)

On mount, compute `hasFlowMap = Boolean(window.__INFRACANVAS_DATA__?.flowmap)`. Derived boolean; no new store field required for gate (but may be added to store for ergonomics).

| `hasFlowMap` | FlowMap tab behavior |
|--------------|----------------------|
| `true` | Enabled, clickable, keyboard-focusable, URL hash responds |
| `false` | Disabled: `aria-disabled="true"`, no `onClick` dispatch, `cursor: not-allowed`, tooltip copy surfaces remediation (see Copywriting), `tabIndex={-1}` so keyboard Tab skips it, shortcuts `2` and `Cmd+\` become no-ops |

### Focus & Accessibility

Preserve existing contracts from `TabBar.tsx`:

- `role="tablist"` on container; `aria-label="Viewer mode"`.
- `role="tab"` on each button; `aria-selected`, `aria-controls="panel-{id}"`, `id="tab-{id}"`.
- Roving tabindex: active tab is `tabIndex={0}`; others are `tabIndex={-1}`.
- Panel container in `App.tsx` already has `role="tabpanel"`, `id="panel-{activeTab}"`, `aria-labelledby="tab-{activeTab}"`.

**New a11y additions for Phase 4:**

- Disabled tab: add `aria-disabled="true"` (don't remove from tab order of SR navigation — screen reader users should still discover it and hear the tooltip).
- Tooltip: pair `aria-describedby` on the disabled FlowMap button to an off-screen `<span role="tooltip" id="flowmap-disabled-tooltip">` that contains the remediation copy. Always-present in DOM; visual display toggled via hover/focus with Tailwind's `group`/`peer-focus-visible` pattern (mirrors the existing edge-legend pattern in SummaryBar).
- Keyboard shortcut discoverability: extend the existing `title` attribute on each tab to include shortcut hints. Example: `title="Infrastructure diagram — press 1 or ⌘\\"`.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Canvas tab label | `Canvas` |
| FlowMap tab label | `FlowMap` + inline `BETA` pill (existing) |
| Canvas tab tooltip (enabled) | `Infrastructure diagram — press 1 or ⌘\` |
| FlowMap tab tooltip (enabled) | `Hybrid network topology — beta, free during preview. Press 2 or ⌘\` |
| FlowMap tab tooltip (disabled) | `No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable.` |
| Primary CTA | n/a for this phase (no CTAs — tab toggle is navigation, not action) |
| Empty state heading | n/a (disabled state replaces empty state) |
| Empty state body | n/a |
| Error state | n/a (tab toggle has no error path; failures are silent no-ops) |
| Destructive confirmation | n/a (no destructive actions in Phase 4 UI) |

**Copy rules:**

- Use `⌘\` on macOS-detected user-agents; use `Ctrl+\` otherwise. Detection: `navigator.platform.toLowerCase().includes('mac')`. If ambiguous, default to `Ctrl+\` (broader base).
- The disabled tooltip MUST be actionable — the `infracanvas scan --with-flowmap` command literal is the remediation. Do not shorten to "FlowMap unavailable" — users then have to go hunt.
- "beta, free during preview" in the FlowMap tooltip is an existing commitment from Phase 3 — do not remove. Product pricing tie-in will surface in Phase 13 (TIR-02).

---

## Component Inventory

| Component | File | Phase 4 Change |
|-----------|------|----------------|
| `TabBar` | `viewer/src/components/TabBar.tsx` | **Extend** — add hash sync, global shortcuts, disabled state + tooltip |
| `App` | `viewer/src/App.tsx` | **No visual change** — may gain a `useEffect` for hash/shortcut wiring if TabBar doesn't absorb it internally |
| `useStore` | `viewer/src/store.ts` | **No new slices** — `activeTab` + `setActiveTab` already exist. Consider adding a derived `hasFlowMap` boolean if convenient (discretion) |
| `SummaryBar` | `viewer/src/components/SummaryBar.tsx` | **No change** — 48px header stays, tabbar sits below it |
| `DetailPanel` / `PathDetailPanel` | — | **No change** — `activeTab` in these files is unrelated local state per CONTEXT.md canonical_refs |

No new components. No new icon imports. No new font weights.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none — shadcn not initialized | not applicable |
| third-party | none | not applicable |

No components pulled from any registry in Phase 4. All UI changes are edits to existing hand-written TSX. Registry safety gate: trivially satisfied.

---

## States & Visual Checklist

| State | Must-Have Visual Signal |
|-------|-------------------------|
| Canvas active, FlowMap enabled | Canvas has `#F1F5F9` text + blue underline; FlowMap has `#64748B` text + BETA pill |
| FlowMap active, Canvas enabled | FlowMap has `#F1F5F9` text + blue underline + BETA pill; Canvas has `#64748B` text |
| Canvas active, FlowMap disabled | Canvas styled as active; FlowMap has `#475569` text, `cursor: not-allowed`, `aria-disabled`, tooltip describes remediation |
| Hover inactive enabled tab | Text fades to `#94A3B8`, background tints to `rgba(45,55,72,0.3)` |
| Hover disabled tab | No hover state change; tooltip appears |
| Keyboard focus on tab | Browser default focus ring visible with 2px `outlineOffset` (existing) |
| User pastes `#flowmap` into URL + reloads, FlowMap disabled | Falls back to Canvas silently. No error toast. |

---

## Out of Scope (Explicit)

- Viewer surfacing `unchanged` and `shadow` drift states in FilterPanel/summary badges (deferred per D-08).
- Any restyle of `SummaryBar`, `FilterPanel`, `DiagramCanvas`, `FlowMapCanvas`, `DetailPanel`, or `PathDetailPanel`.
- Light-mode toggle, theme switcher, or any additional color register changes.
- Icon additions or replacements.
- Responsive breakpoints — viewer is desktop-first (≥1080p); no mobile UI work in Phase 4.
- Any UI driven by CLI exit codes or new drift counts — CLI changes don't paint anything new in the viewer this phase.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 04-e2e-wiring-hardening*
*Contract generated: 2026-04-20*
*Upstream inputs: CONTEXT.md (D-10..D-13), REQUIREMENTS.md (WRG-03), existing TabBar.tsx / index.css tokens*
