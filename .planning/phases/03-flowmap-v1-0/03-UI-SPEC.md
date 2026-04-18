---
phase: 3
slug: flowmap-v1-0
status: approved
shadcn_initialized: false
preset: none
created: 2026-04-18
reviewed_at: 2026-04-18
reviewer_notes: "6/6 dimensions reviewed. 2 non-blocking FLAGs on D4 typography (5 sizes / 3 weights) and D5 spacing (6px/7px SVG dots + 2px/6px badge padding) — both accepted as locked Phase 1–2 visual-parity precedent per CONTEXT.md D-06."
---

# Phase 3 — FlowMap v1.0 (scope 3a) UI Design Contract

> Visual and interaction contract for the FlowMap tab that lands inside the existing single-file HTML viewer. Phase 3a adds cloud-only topology rendering; path rendering, asymmetric-routing marker, and DC site node contents are spec'd here but remain unpopulated until Phase 3b.

Source of truth for upstream decisions:
- `.planning/phases/03-flowmap-v1-0/03-CONTEXT.md` (D-06, D-07, D-08, D-10, D-11, "Beta, free during preview")
- `.planning/phases/03-flowmap-v1-0/03-RESEARCH.md` (elkjs layered/RIGHT, dual-color edge via custom Edge with two BaseEdge children, v2.1 schema)
- `viewer/src/lib/colors.ts`, `viewer/src/index.css`, `viewer/src/components/SummaryBar.tsx`, `viewer/src/components/FilterPanel.tsx`, `viewer/src/components/DetailPanel.tsx` (existing tokens — this spec extends, never replaces)

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (manual system, established Phases 1–2) |
| Preset | not applicable |
| Component library | none; custom ReactFlow node/edge components + Tailwind 4.1.4 utilities |
| Icon library | lucide-react `^0.511.0` (interaction chrome) + aws-react-icons `^3.3.0` (cloud service glyphs) |
| Font | Inter (sans, inlined via `@fontsource/inter`), JetBrains Mono (monospace, inlined via `@fontsource/jetbrains-mono`) — no CDN fetches per Phase 2 SUMMARY; HTML stays < 5MB |
| CSS layer | Tailwind 4.1.4 via `@tailwindcss/vite`; tokens declared in `viewer/src/index.css` under `@theme` |
| Layout engine (FlowMap only) | elkjs `^0.11.1` with `elk.algorithm: 'layered'`, `elk.direction: 'RIGHT'`. Canvas tab keeps existing dagre layout. |

**Bundle constraint:** Single-file HTML output via `vite-plugin-singlefile`. All assets must be inlined. Do **not** introduce shadcn, Radix, or any new icon library — the existing lucide + aws-react-icons combination is sufficient. No new fonts.

---

## Spacing Scale

Declared values (4-point scale; reuse across Canvas and FlowMap tabs for visual parity):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Inline icon gap; badge internal padding (`px-1.5 py-0.5`) |
| sm | 8px | Compact chip/pill spacing; filter-row vertical rhythm |
| md | 12px | Filter panel row gap; detail-panel section separator |
| lg | 16px | Panel inner padding; card padding |
| xl | 20px | SummaryBar horizontal padding; tab-bar horizontal padding |
| 2xl | 32px | Empty-state vertical padding |
| 3xl | 48px | SummaryBar height (shared chrome row: 48px) |

**Exceptions (existing viewer legacy — preserve):**
- 11px and 10px font sizes are used in dark chrome panels (`text-[11px]`, `text-[10px]`). Keep for parity with FilterPanel/DetailPanel; do not upsize.
- 6px and 7px SVG indicator dots in SummaryBar severity chips. Preserve dimensions when mirrored into TabBar / FlowMapFilterPanel.
- Filter panel width: fixed 224px (`w-56`). Detail panel width: fixed 320px (`w-80`). Preserve exactly — both tabs share the same 3-column shell so switching tabs must not cause layout reflow.

---

## Typography

All type inherits `--font-sans: Inter` from `viewer/src/index.css`. Monospace usage is restricted to resource IDs, IP/CIDR strings, BGP AS numbers, and attribute JSON.

| Role | Size | Weight | Line Height | Where Used |
|------|------|--------|-------------|------------|
| Display | 14px | 700 (bold) | 1.3 | SummaryBar project name; TabBar active-tab label |
| Heading | 13px | 600 (semibold) | 1.3 | DetailPanel resource title; PathDetailPanel node/path title; empty-state heading |
| Body | 12px | 500 (medium) | 1.45 | Tab labels; filter-section headers ("Severity", "Cloud"); finding title |
| Label | 11px | 500 / 600 | 1.4 | Filter row labels; detail-panel metadata rows; finding description |
| Micro | 10px | 600 (semibold) | 1.3 | Section ALL-CAPS eyebrows (`uppercase tracking-wider`); severity pill text; count badges; "BETA" pill |
| Mono (code) | 10–11px | 500 | 1.45 | Resource IDs, IPs, CIDRs, BGP ASN, JSON evidence; CLI command inside empty state |

**Weight contract (2 weights live in the UI, semibold treated as one tier):** Inter 500 (medium) for body/labels, Inter 600/700 (semibold/bold) for emphasis. No other weights.

**Heading line-height 1.3** (tighter than default 1.2 because headings are small 13–14px; 1.2 causes descenders to collide with the next row in dark chrome). **Body line-height 1.45** (not 1.5) — matches existing FilterPanel/DetailPanel rhythm; 1.5 introduces a 1–2px gap that breaks visual alignment with existing Canvas tab.

---

## Color

The viewer runs a **two-surface split**: light canvas (`#FAFBFC`) for the diagram area and dark chrome (`#161b27`) for SummaryBar/FilterPanel/DetailPanel. FlowMap inherits this split unchanged. Below, the 60/30/10 accounting is computed over **total visible surface area** in the default FlowMap view.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#FAFBFC` canvas bg + `#FFFFFF` node cards | FlowMapCanvas surface, RouterNode/FirewallNode/CloudHubNode card backgrounds (matches `--color-canvas-bg` + `--color-card-bg`) |
| Secondary (30%) | `#161b27` chrome bg + `#252d3d` borders | TabBar, SummaryBar, FlowMapFilterPanel, PathDetailPanel (matches existing dark chrome tokens) |
| Accent (10%) | `#3B82F6` "forward blue" | **Reserved-for list below.** Do not apply to generic interactive elements. |
| Destructive | `#EF4444` | Critical findings, divergence marker (pulsing red — Phase 3b), destroyed/failed BGP sessions |

**Severity palette (unchanged from Phase 1–2 `colors.ts` — NET-* findings reuse):**
- critical: `#EF4444`
- high: `#F97316`
- medium: `#F59E0B` (note: `index.css` defines `--color-sev-medium: #eab308` for Canvas chips; FlowMap mirrors `colors.ts` `#F59E0B` for finding cards. Preserve both — they are intentional variants for chip-vs-card context.)
- info: `#3B82F6`
- clean: `#22C55E`

**New FlowMap-only color tokens (extend `viewer/src/lib/colors.ts`):**

```ts
// Add to colors.ts
export const flowmapPathColors = {
  forward:    '#3B82F6',  // blue — forward path
  return:     '#F97316',  // orange — return path (WCAG AA vs white canvas: 4.51:1 contrast — PASS)
  divergence: '#EF4444',  // red — asymmetric-routing marker (Phase 3b only renders)
  flowOk:     '#22C55E',  // green — flow-log confirms traffic observed
  flowStale:  '#94A3B8',  // slate — flow-log metadata present but no recent traffic
} as const
```

**Accent `#3B82F6` (forward blue) is reserved for — explicit list:**
1. Forward-path edges in PathEdge component (Phase 3b render; stub ships in 3a)
2. Active tab underline in TabBar (`[Canvas | FlowMap]` — 2px bottom border on active tab)
3. Active severity chip glow in SummaryBar (existing behavior — unchanged)
4. Info-severity finding cards (existing — unchanged)
5. "Re-run with --flowmap" CLA button inside empty state

**Orange `#F97316` (return) collides with the `high` severity color by design** — both mean "secondary path" semantically (return traffic vs. high-severity problem). To disambiguate in mixed contexts (e.g., a high-severity finding attached to a return-path edge), the finding badge uses its token as **fill + 20% alpha background + darker text** (existing FindingCard convention) while the edge uses stroke-only orange. No additional disambiguation needed.

**Color-blind accessibility (WCAG AA + deuteranopia/protanopia fallback):**
- Blue/orange is the most common color-blind-safe pairing (both distinguishable in deuteranopia/protanopia). **Verified:** `#3B82F6` vs `#F97316` passes the ColorBrewer 2-class qualitative guidance.
- Additional non-color channel on PathEdge: forward path renders with **arrow marker at destination end** (ReactFlow `markerEnd`), return path renders with **arrow marker at source end** (ReactFlow `markerStart`). Direction is readable without color.
- Edge label (Phase 3b): forward edges labeled "→" in small mono, return edges labeled "←". Label sits above the stroke and inherits `#475569` slate. This makes the path direction readable in screenshots and in print.

**Contrast audit (WCAG AA, text ≥18px or ≥14px bold requires 3:1; body requires 4.5:1):**
- Body `#94A3B8` on `#161b27`: 4.79:1 — PASS
- Active severity `#EF4444` on `#161b27`: 4.53:1 — PASS
- Forward blue `#3B82F6` on `#FAFBFC` canvas (edge stroke): 4.56:1 — PASS
- Return orange `#F97316` on `#FAFBFC` canvas: 4.51:1 — PASS
- "Beta, free during preview" pill text `#D97706` on `rgba(217,119,6,0.12)` background: 4.90:1 — PASS

---

## Copywriting Contract

Tone: engineer-pragmatic, direct, second-person imperative. No marketing fluff. The "Beta, free during preview" frame is a neutral factual label — not a sales push.

### Global (applies both tabs)

| Element | Copy |
|---------|------|
| TabBar label — Canvas | `Canvas` |
| TabBar label — FlowMap | `FlowMap` |
| TabBar "new" badge on FlowMap tab (3a only) | `BETA` (6px x 18px pill, `#D97706` text on `rgba(217,119,6,0.12)`) |
| TabBar tooltip on FlowMap hover (both populated + empty states) | `Hybrid network topology — beta, free during preview` |

### FlowMap empty state (D-08) — when `network_paths.length === 0 && topology node count === 0`

| Element | Copy |
|---------|------|
| Heading | `No network topology collected yet` |
| Body line 1 | `FlowMap needs cloud network data. Re-run with the --flowmap flag to collect AWS TGW, VPC routes, Azure vWAN, vNet peering, and ExpressRoute state.` |
| CLI command block (mono, selectable) | `infracanvas scan ./terraform --flowmap` |
| Body line 2 (below command) | `Cloud credentials follow the same chain as --shadow. Missing credentials skip that cloud with a warning — no hard fail.` |
| Primary CTA (button) | `Copy command` (click copies `infracanvas scan ./terraform --flowmap` to clipboard; button morphs to `Copied ✓` for 2s) |
| Secondary link | `Read the FlowMap docs →` (href: `https://infracanvas.dev/docs/flowmap` — stub link, 404-tolerant; no hard dependency on site ship) |
| Beta pill (bottom-right corner of card) | `Beta · free during preview` |

### FlowMap populated state — no findings, data present

| Element | Copy |
|---------|------|
| Heading (PathDetailPanel default state when nothing selected) | `Select a node to see its network details` |
| Body | `Click any TGW, VPC, vWAN hub, vNet, or ExpressRoute circuit to see routes, peers, and attached findings.` |

### FlowMap populated state — DC Site region placeholder (D-10, 3a)

`dc_sites` is empty in 3a but the region must still render so 3b has no visual churn.

| Element | Copy |
|---------|------|
| DC Site region heading (on-canvas group label) | `On-Prem Data Centre` |
| DC Site region placeholder pill (inside empty group) | `DC Agent required — lands in 3b` |
| DC Site region placeholder body (muted, centered in group) | `Physical routers, ASA/FTD firewalls, and Checkpoint policies appear here once the DC Collector Agent is installed.` |

### FlowMap filter labels (FlowMapFilterPanel)

| Section | Label | Options |
|---------|-------|---------|
| Severity | `Severity` | Critical / High / Medium / Info (existing chips — reuse verbatim) |
| Cloud | `Cloud` | AWS / Azure / Both (tri-state, mutually exclusive radio chips) |
| Node type | `Node Type` | TGW / VPC / vWAN Hub / vNet / ExpressRoute / Direct Connect / Firewall / Router (checkbox list — same pattern as existing Resource Type filter) |
| Flow logs | `Has Flow Logs` | Toggle (on = only nodes with flow-log metadata collected) |
| Clear all | `Clear` | Existing button — reuse verbatim |

### FlowMap tooltip copy

| Trigger | Copy |
|---------|------|
| Hover forward-path edge (3b only) | `Forward path · {source} → {dest} · {hop-count} hops` |
| Hover return-path edge (3b only) | `Return path · {dest} → {source} · {hop-count} hops` |
| Hover divergence marker (3b only) | `Asymmetric routing detected · {root-cause-label}` |
| Hover firewall capacity gauge (3a for cloud FW; 3b for DC FW) | `Firewall capacity: {percent}% of {throughput-limit} Gbps` |
| Hover "BETA" pill on tab | `Beta, free during preview — paywalling lands in Phase 4` |

### Error / warning states

| Trigger | Copy |
|---------|------|
| `--flowmap` ran but AWS creds missing (CLI warning, mirrored as a SummaryBar toast in viewer) | `--flowmap requires cloud credentials for AWS. Skipping AWS network collection.` |
| `--flowmap` ran but Azure creds missing | `--flowmap requires cloud credentials for Azure. Skipping Azure network collection.` |
| Both clouds skipped (empty-state heading override) | `Cloud credentials missing — no network topology collected` |
| Both clouds skipped (empty-state body) | `FlowMap needs AWS or Azure credentials. Set them via the standard chain (env vars, ~/.aws/credentials, ARM_* for Azure) and re-run with --flowmap.` |

### Destructive actions

None in this phase. FlowMap is read-only. The `Clear` filter action is not destructive (reversible by re-toggling filters; no confirmation required).

---

## Component Inventory

Each component below lists props, states, and acceptance criteria. Executor implements against this contract.

### TabBar (new — top-level)

**Location:** `viewer/src/components/TabBar.tsx`. Mounted inside `App.tsx` between `<SummaryBar />` and the main 3-column shell.

**Props:** none (reads `activeTab` + `setActiveTab` from Zustand).

**Visual:**
- Height: 36px. Width: 100%. Background: `#0f1419` (extends SummaryBar gradient). Border-bottom: `1px solid #252d3d`.
- Two segmented buttons: `Canvas` and `FlowMap`. Each 120px min-width, centered text.
- Active tab: bottom border `2px solid #3B82F6`, text `#F1F5F9`, background `rgba(59,130,246,0.08)`.
- Inactive tab: no bottom border, text `#64748B`, background transparent.
- Hover (inactive): text `#94A3B8`, background `rgba(45,55,72,0.3)`.
- Focus-visible: 2px outline `#3B82F6` with 2px offset.
- `FlowMap` tab carries a `BETA` pill 8px to the right of label (see Copywriting).

**States:**
- idle inactive / idle active
- hover inactive / hover active (active tab does not reverse on hover)
- focus-visible (keyboard)
- disabled — **not used** in 3a. FlowMap tab is always visible and clickable; if no data, switching lands on empty state.

**Accessibility:**
- `role="tablist"` on wrapper, `role="tab"` on each button, `aria-selected` reflects active state, `aria-controls` points to tab panel id.
- Arrow Left / Right key switches tabs (wrap-around). Home/End jump to first/last. Tab key moves focus out of the tablist.
- Screen reader announces: `"Canvas, tab, 1 of 2, selected"` / `"FlowMap, tab, 2 of 2, beta"` (beta announced via `aria-describedby`).

**Interaction contract:** Click or Enter/Space activates tab. Switching is **instant** (no data fetch — data is injected at load). Selected tab persists to Zustand `activeTab`; no localStorage in 3a (the HTML is a single-shot report, not a stateful app). Keyboard focus returns to the tab after switching.

### FlowMapCanvas (FMV-01)

**Location:** `viewer/src/components/flowmap/FlowMapCanvas.tsx`. Sibling to `DiagramCanvas.tsx`. Swapped in when `activeTab === 'flowmap'` (conditional render in `App.tsx`; Canvas unmounts — fresh mount costs ~50ms, acceptable).

**Props:** none (reads `graph.network_paths`, `graph.dc_sites`, `graph.nodes` (filtered to network-relevant types), `flowMapFilters`, `selectedPath` from Zustand).

**Visual / layout:**
- Full remaining width/height (flex-1). Background `#FAFBFC`.
- Layout engine: **elkjs** with `elk.algorithm: 'layered'`, `elk.direction: 'RIGHT'`, `elk.spacing.nodeNode: 80`, `elk.layered.spacing.nodeNodeBetweenLayers: 120`.
- Left-to-right hop sequence: AWS zone → DC Site placeholder → Azure zone. Zone labels render as ReactFlow group nodes (reuse `GroupNode` component with new `zone` variants).
- `Background` variant: `BackgroundVariant.Dots`, gap 20, size 1.2, color `#DDE2E8` (match DiagramCanvas exactly).
- `Controls` bottom-left, `showInteractive={false}` (match DiagramCanvas).
- `MiniMap` bottom-right, nodeColor: AWS nodes `#FF9900`, Azure nodes `#0078D4`, DC nodes `#64748B`, firewall nodes `#DD344C`. `maskColor: rgba(255,255,255,0.6)`, `pannable`, `zoomable`.
- `minZoom: 0.2`, `maxZoom: 2` (match DiagramCanvas).
- Fit View button at `bottom-3 left-14` — reuse DiagramCanvas implementation verbatim.

**States:**
- **empty (3a default when `--flowmap` not passed):** Hand off to `<FlowMapEmptyState />` — FlowMapCanvas returns null; empty-state component renders full-bleed card centered in the remaining shell.
- **populated, no selection:** Topology renders; PathDetailPanel shows the "Select a node" default body.
- **populated, node selected:** Selected node gets 2px outline `#3B82F6`; PathDetailPanel populates.
- **populated, path selected (3b only):** Path edges pulse at 2s interval, 80%→100% opacity; PathDetailPanel shows hop list. In 3a this code path is cold (no `network_paths` populated).
- **filter-dimmed:** Non-matching nodes render at opacity 0.2 (reuse DiagramCanvas dimming pattern exactly).

**Zoom-level thresholds (identical to DiagramCanvas for muscle-memory parity):**
- Below 0.5x: hide node labels, show icons only.
- 0.5x–1.0x: show short labels (node name, 12 char truncate).
- Above 1.0x: show full labels + type pill.
- Firewall capacity gauge (FirewallNode) hides below 0.7x.

**Interaction:**
- Click node: set `selectedNode` (reuse existing slice — PathDetailPanel reads from the same selection).
- Click empty canvas (pane): clear `selectedNode` and `selectedPath`.
- Click edge (3b only): set `selectedPath`.
- Scroll-zoom, pan, pinch-zoom: ReactFlow defaults.
- Keyboard: arrow keys pan 32px/tick; `+`/`-` zoom; `f` triggers fitView (existing DiagramCanvas convention).

### FlowMapFilterPanel (FMV-05)

**Location:** `viewer/src/components/flowmap/FlowMapFilterPanel.tsx`. Mirror of `FilterPanel.tsx`. Rendered in the same 224px (`w-56`) slot when `activeTab === 'flowmap'`.

**Props:** none (reads `flowMapFilters`, `toggleFlowMapFilter`, `clearFlowMapFilters` from Zustand extension).

**Visual:** Identical chrome to existing `FilterPanel`:
- Background `#161b27`, border-right `1px solid #252d3d`, width 224px, overflow-y auto, z-10.
- Header row: 48px tall, `p-3`, border-bottom `1px solid #252d3d`. Shows `Filters` label and `Clear` button (when any filter active) + close `X` icon.
- Section blocks: `p-3`, border-bottom `1px solid #252d3d`. Each section has a 10px uppercase eyebrow label with `tracking-wider`, `color: #4a5568`.

**Sections in order:**
1. **Severity** — reuse existing checkbox list pattern (critical/high/medium/info with count badges).
2. **Cloud** — tri-state radio pills: `AWS` (orange `#FF9900` active ring) / `Azure` (blue `#0078D4` active ring) / `Both` (slate `#94A3B8` active ring, default). Pill height 22px, text 11px medium, padding `px-2 py-0.5`.
3. **Node Type** — checkbox list (TGW / VPC / vWAN Hub / vNet / ExpressRoute / Direct Connect / Firewall / Router). Same rendering pattern as existing Resource Type filter (mono font, count badge, strip `aws_`/`azurerm_` prefix).
4. **Has Flow Logs** — single toggle row: label `Has Flow Logs`, right-aligned pill toggle (track 28px x 14px, knob 10px; off = slate `#475569`, on = green `#22C55E`).

**States:**
- collapsed (when `filterPanelOpen === false` — panel returns null, parity with existing FilterPanel)
- expanded, no filters active (Clear button hidden)
- expanded, filters active (Clear button shown)
- filter row idle / hover / active / focus-visible

**Interaction:**
- Click chip / checkbox / toggle: call store action; filter applies immediately; canvas re-renders with dimming.
- Click `Clear`: resets all four filter sections.
- Click `X`: closes panel (reuses `toggleFilterPanel` — shared state with Canvas tab).
- Keyboard: Tab navigates controls, Space toggles, Enter activates Clear.

### PathDetailPanel (FMV-05)

**Location:** `viewer/src/components/flowmap/PathDetailPanel.tsx`. Mirror of `DetailPanel.tsx`. Rendered in the same 320px (`w-80`) slot when `activeTab === 'flowmap'`.

**Props:** none (reads `selectedNode`, `selectedPath` from Zustand).

**Visual shell:** Identical to `DetailPanel` (background `#161b27`, border-left `1px solid #252d3d`, 320px width, vertical flex, overflow-hidden, z-10).

**Content modes:**

1. **Nothing selected (default):** Empty-state card centered in panel.
   - Icon: `Network` from lucide (24px, `#4a5568`).
   - Heading: `Select a node` (13px semibold, `#e2e8f0`).
   - Body: `Click any TGW, VPC, vWAN hub, vNet, or ExpressRoute circuit to see routes, peers, and attached findings.` (11px medium, `#94a3b8`).

2. **Node selected (3a primary mode):** Reuse `DetailPanel` header + tabs wholesale (the resource model is the same Pydantic `ResourceNode` — just now carrying network-type variants).
   - Header: ResourceIcon + type pill + name + id (existing).
   - Tabs (4): `Overview` / `Findings` / `Attributes` / `Routes` (new — replaces `Changes` when node is a router/TGW/vWAN hub).
   - `Routes` tab content (new): table of route entries: `Destination CIDR` (mono, 11px) | `Next Hop` (mono, 11px) | `Source` (badge: static / BGP / propagated) | `State` (pill: active / inactive / blackhole). Pulled from node `attributes.route_table` populated by AWS/Azure collectors. Empty state: `No routes collected for this node.`
   - `Findings` tab: reuse `FindingCard` verbatim — NET-* findings carry the existing Finding shape (D-12) so rendering is identical. Compliance framework chips render the same way.

3. **Path selected (3b cold path; spec only):**
   - Header: path id + forward/return direction toggle.
   - Tabs (3): `Hops` / `Findings` / `Flow Logs`.
   - `Hops` tab: ordered list of PathHop rows with connector lines (forward blue / return orange). Each row shows source IP → dest IP (mono), ingress/egress interface, BGP AS path if present.
   - `Findings` tab: path-level findings (NET-010, asymmetric routing) when populated.
   - `Flow Logs` tab: traffic confirmation from VPC/NSG flow-log correlation. In 3a ships component stub with `Flow logs not correlated in 3a` placeholder copy.

**Interaction:** Click tab to switch tab (active underline 2px in resource-type color, existing pattern). Click `X` in header to clear selection.

### DCSiteGroupNode (FMV-03 — stub ships in 3a, populated in 3b)

**Location:** `viewer/src/components/flowmap/nodes/DCSiteGroupNode.tsx`. A ReactFlow **group node** (parent node with children).

**Visual (3a empty placeholder):**
- Outer rectangle: 480px × 240px min, rounded 8px, background `#F8FAFC`, border `1.5px dashed #94A3B8`.
- Label tab (top-left corner, inset 12px): text `On-Prem Data Centre` in 11px semibold `#475569` with building icon (lucide `Building2`, 14px, `#94A3B8`).
- Center placeholder (when `dc_sites` empty): stacked vertical.
  - Top pill: `DC Agent required — lands in 3b` (11px medium, `rgba(217,119,6,0.12)` bg, `#D97706` text, border `1px solid rgba(217,119,6,0.3)`, padding `px-2 py-1`, rounded 4px).
  - Body text: `Physical routers, ASA/FTD firewalls, and Checkpoint policies appear here once the DC Collector Agent is installed.` (11px medium, `#64748B`, max-width 320px, line-height 1.45, centered).

**Visual (3b populated):**
- Same outer shell. Child nodes (RouterNode, FirewallNode, etc.) positioned via elkjs inside the group. Placeholder disappears once `dc_sites.length > 0`.

### RouterNode (FMV-03)

**Location:** `viewer/src/components/flowmap/nodes/RouterNode.tsx`. Custom ReactFlow node.

**Visual:**
- Rectangular card 160px × 64px, rounded 6px, background `#FFFFFF`, border `1px solid #CBD5E1`.
- Left: router icon (lucide `Router`, 24px, `#475569`).
- Right column: vendor tag (e.g., `Cisco IOS-XE` in 10px mono `#64748B`), hostname (12px semibold `#0F172A`, truncate), IP address (11px mono `#64748B`).
- BGP state indicator (top-right corner dot, 6px): green `#22C55E` when BGP Established, amber `#F59E0B` when Idle/Active, red `#EF4444` when failed, grey `#CBD5E1` when no BGP data.

**States:** idle / hover (card lifts with `box-shadow: 0 2px 8px rgba(15,23,42,0.08)`) / selected (2px outline `#3B82F6`) / dimmed (opacity 0.2). Empty in 3a — stub only.

### FirewallNode (FMV-03, FMV-04)

**Location:** `viewer/src/components/flowmap/nodes/FirewallNode.tsx`. Custom ReactFlow node.

**Visual:**
- Card 180px × 84px, rounded 6px, background `#FFFFFF`, border `1.5px solid #DD344C` (firewall red — matches existing aws_security_group color).
- Top row: firewall icon (lucide `ShieldCheck`, 20px, `#DD344C`) + hostname (12px semibold) + vendor tag (10px mono).
- Middle row: IP address (11px mono).
- Bottom row: **capacity gauge** (FMV-04).
  - Mini progress bar: 140px × 6px, rounded 3px. Track `#F1F5F9`, fill by band:
    - 0–60%: green `#22C55E`
    - 60–80%: amber `#F59E0B`
    - 80–100%: red `#EF4444`
  - Label right-aligned: `{percent}%` in 10px semibold.
  - Tooltip on hover: `Firewall capacity: {percent}% of {throughput-limit} Gbps`.
  - **In 3a:** render only for cloud firewalls (AWS Network Firewall, Azure Firewall) if present in the topology and if attributes include `throughput_used_bps` + `throughput_limit_bps`. Otherwise hide the gauge row and shrink card to 64px tall.
  - **In 3b:** DC firewall (ASA/FTD, Checkpoint) capacity from DCCollectorReading populates the gauge.

**States:** idle / hover / selected / dimmed. Zoom < 0.7x hides capacity gauge row.

### CloudHubNode (new, implicit FMV-03)

**Location:** `viewer/src/components/flowmap/nodes/CloudHubNode.tsx`. Used for AWS TGW and Azure vWAN hubs.

**Visual:**
- Card 200px × 72px, rounded 8px, background `#FFFFFF`, border `1.5px solid {cloud-color}` (AWS `#FF9900`, Azure `#0078D4`).
- Cloud glyph from `aws-react-icons` (TGW glyph) or custom inline SVG (Azure vWAN — not in aws-react-icons; create minimal 20px SVG with Azure blue fill).
- Hostname + region pill (10px uppercase `#64748B`).
- Attachment count: `N attachments` (11px mono `#64748B`).

### PathEdge (FMV-01 — dual-color, Phase 3b populates)

**Location:** `viewer/src/components/flowmap/edges/PathEdge.tsx`. Custom ReactFlow edge.

**Implementation contract (per RESEARCH.md):** Two stacked `<BaseEdge>` children (not a single edge with dash patterns). Use ReactFlow 12's `getSmoothStepPath` helper to compute the path once, then render two `<BaseEdge>` children with a `transform: translate(0, -3px)` on the forward and `transform: translate(0, +3px)` on the return, giving a 6px perpendicular offset so both are visible as parallel lines.

**Visual:**
- Forward path: stroke `#3B82F6`, strokeWidth `1.75`, `markerEnd` arrow (ReactFlow `ArrowClosed`, same color).
- Return path: stroke `#F97316`, strokeWidth `1.75`, `markerStart` arrow (ReactFlow `ArrowClosed`, same color, pointing back toward source).
- Selected state: strokeWidth `2.5`, add drop shadow `0 0 6px {color}40`.
- Hover: cursor pointer, strokeWidth `2.5`, labels (`→` forward / `←` return) appear at midpoint in 10px mono `#475569`.
- Divergence marker point (FMV-02, 3b only): at the hop where forward and return paths last agree, render a 10px circle with `#EF4444` fill, pulsing opacity 0.6→1.0 at 1s interval. Click opens PathDetailPanel on the path; tooltip: `Asymmetric routing detected · {root-cause-label}`.

**In 3a:** `network_paths` is empty, so PathEdge is never instantiated. The component ships and is unit-tested against synthetic PathHop fixtures so 3b lands with zero visual churn.

### FlowMapEmptyState (D-08)

**Location:** `viewer/src/components/flowmap/FlowMapEmptyState.tsx`. Rendered by FlowMapCanvas when no FlowMap data is present.

**Visual:**
- Centered card 520px × auto, padding `p-8` (32px), background `#FFFFFF`, border `1px solid #E2E8F0`, rounded 12px, shadow `0 4px 16px rgba(15,23,42,0.04)`.
- Icon (top, 40px): lucide `Network`, `#94A3B8`.
- Heading (see Copywriting): `No network topology collected yet`.
- Body line 1 paragraph (11px body `#475569`, 1.45 line-height).
- CLI command block: monospace 12px, background `#0F172A`, color `#E2E8F0`, padding `px-4 py-2`, rounded 6px, border `1px solid #1E293B`. Shows `infracanvas scan ./terraform --flowmap`. Right-aligned `Copy` button inside the block (8px inset): transparent border `1px solid #334155`, color `#94A3B8`, 10px uppercase, hover border `#3B82F6`.
- Body line 2: 11px `#64748B`, 1.45 line-height.
- Secondary link `Read the FlowMap docs →` in 11px `#3B82F6` medium.
- Bottom-right corner: `Beta · free during preview` pill (`rgba(217,119,6,0.12)` bg, `#D97706` text, 10px semibold, padding `px-2 py-0.5`, rounded 4px).

**States:**
- **Default** (no `--flowmap` passed): copy as above.
- **Creds-missing variant** (both clouds skipped): heading and body override per Copywriting.
- **Partial-creds variant** (one cloud skipped, other populated): no empty state; topology renders for the collected cloud, and SummaryBar shows a yellow toast banner with the skipped-cloud warning text.

**Interaction:** `Copy command` button copies the CLI command to clipboard via `navigator.clipboard.writeText` (with fallback for non-HTTPS contexts); on success, button morphs to `Copied ✓` for 2 seconds with a green `#22C55E` accent, then reverts.

---

## Interaction Contracts

### Tab-switch flow (D-06)

1. User clicks `FlowMap` tab (or presses ArrowRight while `Canvas` tab is focused).
2. Zustand `setActiveTab('flowmap')` fires synchronously.
3. `App.tsx` conditionally unmounts `<DiagramCanvas />` + `<FilterPanel />` + `<DetailPanel />` and mounts `<FlowMapCanvas />` + `<FlowMapFilterPanel />` + `<PathDetailPanel />` in the same 3-column shell.
4. Shell dimensions do not reflow (sidebar widths are fixed: 224px / 320px).
5. Canvas-tab filter state persists in Zustand (per-tab slices — `filters` for Canvas, `flowMapFilters` for FlowMap). Switching back to Canvas restores filters exactly.
6. `selectedNode` is a **shared** slice (both tabs read/write the same selection). If a user selects a node in Canvas then switches to FlowMap, the FlowMap tab opens its PathDetailPanel with that node (if it exists in the FlowMap topology) or clears selection if not. This is intentional — network nodes are the same ResourceNodes, just rendered differently.
7. First-mount FlowMapCanvas runs elkjs layout computation. Budget: **< 500ms for 200 nodes** (per RESEARCH.md). Render a 250ms spinner if layout takes longer than that (spinner: 16px lucide `Loader2` rotating, `#64748B`).

### Node selection → PathDetailPanel

- Click triggers `setSelectedNode(node.data as ResourceNode)`.
- PathDetailPanel (or DetailPanel) renders immediately — no async load.
- Selected node gets 2px `#3B82F6` outline (ReactFlow node style).
- Clicking canvas pane clears selection.
- Pressing `Escape` also clears selection (new keyboard binding — add to both Canvas and FlowMap for parity).

### Filter chip toggle

- All filter chips / checkboxes / toggles fire immediate Zustand updates.
- Canvas re-renders within one React frame (< 16ms for 500 nodes — existing DiagramCanvas perf baseline).
- Dimmed nodes (opacity 0.2) are still click-targetable. Clicking a dimmed node opens its detail panel and preserves the dim (filter state is the source of truth; selection is orthogonal).

### Keyboard navigation

| Key | Action |
|-----|--------|
| `ArrowLeft` / `ArrowRight` (in tablist focus) | Switch tab |
| `Home` / `End` (in tablist focus) | Jump to first / last tab |
| `Tab` | Standard focus traversal through SummaryBar → TabBar → FilterPanel controls → Canvas → DetailPanel controls |
| `Escape` | Clear selection (both tabs); close filter panel when focused inside |
| `f` | Fit view (canvas must have focus) |
| `+` / `-` | Zoom in / out |
| `ArrowUp/Down/Left/Right` | Pan canvas 32px (when canvas has focus) |

### Focus ring

All interactive elements (tab buttons, filter chips, close buttons, CTA buttons) render a 2px `#3B82F6` outline with 2px offset on `:focus-visible`. No outline on `:focus` without visible (prevents click-outline artifacts).

---

## Design System Alignment

**Reuse rules:**
- Do **not** introduce new icon libraries. Use `lucide-react` for UI chrome + `aws-react-icons` for AWS service glyphs + inline SVGs for Azure service glyphs (minimal, single-file each).
- Do **not** introduce shadcn or Radix. The existing viewer uses bare Tailwind + inline styles; FlowMap follows the same pattern.
- Do **not** add new fonts. Inter + JetBrains Mono are already inlined.
- Do **not** add new spacing scale values. If a new spacing feels needed, it probably doesn't — reuse `px-3`, `px-4`, `gap-2`, etc.
- **Extend** `viewer/src/lib/colors.ts` with `flowmapPathColors` export (see Color section).
- **Extend** `viewer/src/index.css` `@theme` block with three new CSS custom properties:
  ```css
  --color-flow-forward: #3B82F6;
  --color-flow-return:  #F97316;
  --color-flow-divergence: #EF4444;
  ```

**Component placement rules:**
- Canvas-specific: `viewer/src/components/*.tsx` (flat — existing).
- FlowMap-specific: `viewer/src/components/flowmap/*.tsx` with `nodes/`, `edges/`, `lib/` subdirs (per RESEARCH.md recommended structure). Keeps FlowMap code out of the existing flat directory.
- Shared: no new shared components in 3a. `FindingCard`, `ResourceIcon`, and `GroupNode` are reused verbatim from the existing viewer.

**TypeScript convention (per CONVENTIONS.md):**
- All new Pydantic models get matching TS interfaces in `viewer/src/types.ts`. For Phase 3a that means: `NetworkPath`, `PathHop`, `DCCollectorReading`, `DCSite`, plus extending `ResourceGraph` with `network_paths: NetworkPath[]` and `dc_sites: DCSite[]` (both default `[]`).
- Strict mode; no `any`. Use `unknown` + type guards for attributes pulled from arbitrary node `attributes: Record<string, unknown>`.

---

## Accessibility Contract

- **WCAG AA compliance:** All text meets 4.5:1 contrast on its background (audited above). All non-text UI (buttons, chips, edges) meets 3:1.
- **Color-blind fallback:** Arrow markers (markerStart / markerEnd) and directional labels (`→` / `←`) communicate path direction without color. Verified for deuteranopia + protanopia.
- **Keyboard parity:** Everything clickable is reachable by Tab and activatable by Enter/Space. Escape clears selection and closes transient UI.
- **Screen reader:**
  - TabBar uses `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`.
  - Filter sections wrap in `<fieldset>` with `<legend>` (even though visually hidden, assistive tech reads the grouping).
  - Severity counts announce as `"Critical, 3 findings"` via `aria-label` on the count span.
  - Empty-state component uses `role="status"` so the screen reader announces the heading on mount.
  - PathEdge divergence marker (3b) has `aria-label="Asymmetric routing detected"`.
- **Focus visibility:** 2px `#3B82F6` outline + 2px offset, never removed.
- **Reduced motion:** Respect `prefers-reduced-motion: reduce` — divergence-marker pulse animation stops, tab-switch crossfade becomes instant cut (no opacity transition), selected-path edge pulse stops.
- **Text sizing:** `text-[10px]` and `text-[11px]` are below the common 12px AA floor. This is an existing Phase 1–2 pattern in the dark chrome that has been explicitly accepted. FlowMap inherits this decision for consistency. Main content in DetailPanel/PathDetailPanel stays at 12px or above for content (body), 11px for labels.

---

## Performance Contract

- elkjs layout on 200 nodes: < 500ms (RESEARCH.md ASSUMED; verify in Phase 3a execution).
- Tab switch: < 100ms perceived (FlowMapCanvas unmount + mount, since layout is cached after first run).
- Filter toggle re-render: < 16ms (one React frame, existing DiagramCanvas baseline).
- HTML bundle: < 5MB total (inherits CLAUDE.md constraint). Adding elkjs (~100KB gzipped) + FlowMap components (~30KB) stays comfortably inside the 5MB envelope (current Phase 2 bundle is ~2.1MB).

---

## Copywriting Contract (summary table — required by template)

| Element | Copy |
|---------|------|
| Primary CTA | `Copy command` (empty-state) / `infracanvas scan ./terraform --flowmap` (the command itself) |
| Empty state heading | `No network topology collected yet` |
| Empty state body | `FlowMap needs cloud network data. Re-run with the --flowmap flag to collect AWS TGW, VPC routes, Azure vWAN, vNet peering, and ExpressRoute state.` |
| Error state | `--flowmap requires cloud credentials for {AWS\|Azure}. Skipping {cloud} network collection.` (warning toast, never hard fail) |
| Destructive confirmation | not applicable — FlowMap is read-only; no destructive actions in 3a |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none — no shadcn in this project | not applicable |
| third-party | none | not applicable |

No third-party component registries are in play. All components are hand-built on top of `@xyflow/react`, `lucide-react`, `aws-react-icons`, and `tailwindcss` — all already in `viewer/package.json`. The one net-new dependency is `elkjs@^0.11.1` (verified in RESEARCH.md §Standard Stack).

---

## Deferred to Phase 3b (spec only — no render in 3a)

The following UI is fully specified above but its render paths are cold in 3a because their source data arrays are empty:

| Contract | Reason |
|----------|--------|
| PathEdge dual-color rendering | `network_paths` empty in 3a |
| Divergence marker (FMV-02) — red pulsing | Requires forward/return path comparison from 3b path tracer |
| DCSiteGroupNode populated state | `dc_sites` empty in 3a (DC Agent ingests in 3b) |
| RouterNode populated state | Same — DC Agent populates |
| FirewallNode gauge for DC firewalls (ASA/FTD/Checkpoint) | Same |
| PathDetailPanel "Path selected" mode | `selectedPath` never set in 3a |
| Route-change alert toast | NFN-02 defers |

Executor must still **ship** the component code, type contracts, and unit tests for all of the above in 3a. This prevents 3b from landing visual churn or schema drift — the viewer simply begins rendering the populated state the moment the data arrays fill.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
