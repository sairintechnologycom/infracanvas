# Phase 3: FlowMap v1.0 - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning (scope reduced to 3a — see Phase Boundary)

<domain>
## Phase Boundary

**Original roadmap scope (v1.0):** Full hybrid network path tracing AWS → physical DC → Azure, asymmetric routing detection with root-cause classification, DC Collector Agent (Go), Cisco + Checkpoint integrations, and Team-tier gating.

**Revised scope (this phase — 3a):** Cloud-only FlowMap foundation.

Deliverables:
- FlowMap data model (NetworkPath, PathHop, DCCollectorReading, NetworkFinding) — FDM-01, FDM-02, FDM-03
- AWS network topology collection (TGW route tables, VPC routes, NACLs, Direct Connect, VPC/TGW flow logs) — AWS-01, AWS-02, AWS-03
- Azure network topology collection (vWAN hubs, vNet peering, NSG effective rules, ExpressRoute, NSG flow logs) — AZN-01, AZN-02, AZN-03
- FlowMap viewer tab (FlowMapCanvas, DC site group nodes, firewall capacity gauge, FlowMap filter+detail panels) — FMV-01, FMV-02, FMV-03, FMV-04, FMV-05
- Network findings engine — cloud-only subset of NET-001 through NET-012 (rules that do not require forward/return path comparison) — NFN-01 (partial)

**Explicitly deferred to Phase 3b (to be inserted after Phase 3):**
- DC Collector Agent — Go scaffold, NETCONF/RESTCONF, SSH fallback, NetFlow collector, daemon mode, API push, config import, binary packaging, CAB security packet (DCA-01..09)
- Cisco ASA REST + FMC REST + SSH fallback (ASA-01..03)
- Checkpoint Management API + object mapping (CKP-01, CKP-02)
- Forward/return path computation + NetFlow correlation (PTH-01, PTH-02, PTH-03)
- Asymmetric routing detector + root-cause classifier + impact assessment (ASY-01, ASY-02, ASY-03)
- Remaining NET-00x findings that depend on path comparison + route-change alerting (NFN-01 full, NFN-02)

**Explicitly deferred to Phase 4:**
- Tier gating (TIR-01, TIR-02) — requires SaaS + Clerk + Stripe webhook infrastructure. FlowMap ships open during 3a/3b beta to collect design-partner signal before paywalling.

**Not in 3a scope (but in roadmap):** FDM-* full coverage of network_paths field population (populated by path tracer in 3b — 3a only defines the schema and leaves it empty), dc_sites field population (DC Agent populates in 3b — 3a defines the schema only).

The phase delivers a usable cloud-only FlowMap: an engineer can run `infracanvas scan ./terraform --flowmap` and see AWS TGW + Azure vWAN topology rendered in a FlowMap tab with cloud-layer network findings, without installing any agent or configuring any DC hardware.

</domain>

<decisions>
## Implementation Decisions

### Phase scope & split

- **D-01:** Phase 3 splits into 3a (this phase) and 3b (to be inserted after Phase 3). 3a = collect + show for cloud topology. 3b = DC Agent + path math + asymmetric detection + on-prem integrations. Rationale: 37 reqs in one phase = months before any verification; splitting lets us ship a usable cloud-only FlowMap before sinking weeks into Go toolchain work and enables earlier design-partner feedback. **Roadmap update required after CONTEXT.md:** run `/gsd-insert-phase` or manually edit `.planning/ROADMAP.md` to introduce Phase 3b carrying the deferred requirements. Also update `.planning/REQUIREMENTS.md` phase mapping for the deferred items.

- **D-02:** Tier gating (TIR-01, TIR-02) is removed from Phase 3 entirely and belongs in Phase 4 alongside Stripe webhooks + Clerk team auth. Phase 3a and 3b both ship with FlowMap open and unrestricted, marketed as "beta, free during preview." Zero auth/billing code lives in Phase 3. Bonus: the beta window produces marketing signal and design-partner interviews before paywalling.

### Cloud network collection architecture

- **D-03:** **CLI owns cloud collection, DC Agent owns on-prem collection.** AWS TGW + VPC + Direct Connect collectors and Azure vWAN + vNet + ExpressRoute collectors run inside the CLI Python process using boto3 + Azure SDK with the customer's local credentials. DC Agent (3b) only collects from physical routers, ASAs, and Checkpoints — not cloud. Cloud-only customers get FlowMap with zero agent install. Mirrors the shadow-infra precedent from Phase 2.

- **D-04:** CLI surface is `infracanvas scan ./terraform --flowmap`. The `--flowmap` flag on the existing `scan` command triggers cloud network collectors alongside the resource scan, producing one HTML output with both Canvas and FlowMap tabs populated. No separate subcommand. Mirrors `--shadow` UX from Phase 2 (D-01).

- **D-05:** Credentials & error handling follow Phase 2 precedent:
  - AWS creds: standard chain (env vars → `~/.aws/credentials` → instance profile) — Phase 2 D-01.
  - Azure creds: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID` env vars only — Phase 2 D-07.
  - Missing creds with `--flowmap` set: print yellow warning ("`--flowmap` requires cloud credentials for X cloud. Skipping X network collection.") and continue. Never hard-fail. Phase 2 D-02 pattern.
  - Region scope: infer from `.tf` files (provider + resource attributes); single-region per cloud. No multi-region sweep by default. Phase 2 D-05 pattern.

### Viewer integration

- **D-06:** FlowMap renders as a **tab inside the existing single-file HTML**, not as a separate HTML file or a layer overlay on Canvas. The existing viewer gets a top-level toggle: `[Canvas | FlowMap]`. Selecting FlowMap swaps DiagramCanvas for FlowMapCanvas. Same Zustand store (extended with `networkPaths`, `dcSites`, `flowMapFilters`, `selectedPath`), same export pipeline, same single-file HTML output. One file to share, one URL to open.

- **D-07:** FlowMap layout uses a **dedicated layout engine**, not the existing dagre tier layout. Path-flow diagrams are fundamentally different from resource-tier diagrams (left-to-right hop sequence vs. tier hierarchy). FlowMapCanvas owns its own layout logic. Dual-color path rendering (blue forward, orange return) is implemented as a ReactFlow edge style (Claude's discretion on exact SVG approach — planner picks).

- **D-08:** When a scan has no FlowMap data (user ran `scan` without `--flowmap`, or collection failed), the FlowMap tab renders an empty state: "No network topology collected. Re-run with `infracanvas scan ./terraform --flowmap` to populate." Tab is visible but inactive. No hiding, no surprising UX.

### Data model & JSON schema

- **D-09:** Extend the existing `ResourceGraph` Pydantic model (`cli/infracanvas/graph/models.py`) with two new fields: `network_paths: list[NetworkPath]` (empty in 3a — populated by 3b path tracer) and `dc_sites: list[DCSite]` (empty in 3a — populated by 3b DC Agent ingest). JSON schema bumps from v2.0 to **v2.1** (additive, backwards-compatible). Downstream viewer reads both fields defensively (empty list → empty state). 3b does not need another schema bump — it only populates existing fields.

- **D-10:** `NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding` Pydantic models land in this phase even though 3a does not populate `NetworkPath` / `PathHop` (those require path tracing from 3b). Rationale: defining the full schema in 3a lets Phase 3b land populators without schema churn, and lets the viewer render from real shapes immediately.

### Network findings scope (3a)

- **D-11:** 3a ships only **cloud-only, path-independent** NET findings — rules that evaluate against single-resource state without comparing forward/return paths. Examples: overlapping route table destinations, missing NACL/NSG on critical path, open egress to 0.0.0.0/0 through TGW, ExpressRoute/Direct Connect circuit in down state, unused attachments, orphaned peerings. **Path-dependent findings defer to 3b:** stateful firewall on only one path (NET-010), asymmetric routing impact, NetFlow-vs-topology mismatch. Exact NET-id assignment is Claude's discretion — planner + researcher allocate ids across 3a vs 3b based on rule dependency analysis.

- **D-12:** NET-* findings use the existing security rule YAML engine (`cli/infracanvas/security/engine.py`). The engine is generic — condition/operator/value — and works over arbitrary Pydantic models. New YAML directory `cli/infracanvas/security/rules/network/` holds NET-* rules. Findings flow through the same unified pipeline as security and policy findings (Phase 2 D-09).

### Claude's Discretion

Planner / researcher decide:
- Exact AWS / Azure SDK calls and API batching strategy (boto3 paginators, async vs sync, retry/backoff)
- Flow-log ingestion approach (S3 pull vs CloudWatch Logs Insights query vs Azure Monitor query)
- FlowMapCanvas layout algorithm (custom vs elkjs vs hierarchical-with-fixed-ranks)
- Dual-color edge rendering technique (ReactFlow edge markerEnd + stroke-dasharray vs custom SVG layer)
- Exact NET-id allocation across 3a vs 3b based on rule path-dependency
- Number of cloud-only NET rules to ship in 3a (minimum 4-6 meaningful rules per cloud — AWS and Azure)
- Test fixture strategy for AWS/Azure network collection (recorded responses via moto/placebo, hand-crafted JSON, or live-scan snapshots with sanitization)

### Folded Todos

None — no pending todos matched Phase 3 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §"Phase 3: FlowMap v1.0" — original phase scope, success criteria, dependency on Phase 2
- `.planning/REQUIREMENTS.md` §"FlowMap v1.0 (Phase 3)" — 37 requirement IDs with descriptions; 3a vs 3b allocation per decisions D-01

### Project-level
- `.planning/PROJECT.md` §"Context" — stack (Go + Python + React), pricing tiers, personas (Sam = Security/Network Engineer drives FlowMap adoption)
- `.planning/PROJECT.md` §"FlowMap v1.0 (Phase 3)" — persona-level value description
- `/Users/bhushan/Documents/Projects/Infracanvas/CLAUDE.md` §"Constraints" — DC agent constraint: "Go, single binary, cross-compiled Linux amd64 + macOS arm64"; "DC agent read-only, outbound-only"

### Prior CONTEXT.md decisions carried forward
- `.planning/phases/02-canvas-v1-0/02-CONTEXT.md` §"Implementation Decisions":
  - D-01/D-02 — opt-in cloud flag + warn-on-missing-creds (mirror for `--flowmap`)
  - D-05 — region inference from `.tf` files, single-region per cloud
  - D-07 — Azure creds via `ARM_*` env vars only
  - D-09 — unified findings pipeline (policy/security findings share engine; NET-* extends this)
- `.planning/phases/01-canvas-mvp/01-CONTEXT.md` — VWR-06 free-tier gate pattern (kept as reference for Phase 4 TIR-01/02, not used in Phase 3)

### Codebase maps
- `.planning/codebase/STRUCTURE.md` §"Directory Layout" — CLI and viewer layout; where to add `cli/infracanvas/flowmap/` and `viewer/src/components/flowmap/`
- `.planning/codebase/ARCHITECTURE.md` — data flow from CLI parse → graph → findings → HTML
- `.planning/codebase/STACK.md` — versions of boto3, Pydantic, ReactFlow, Zustand
- `.planning/codebase/TESTING.md` — Python + Vitest test patterns, fixture conventions
- `.planning/codebase/CONVENTIONS.md` — naming (snake_case Python / camelCase TS / PascalCase components)

### Source files to extend
- `cli/infracanvas/graph/models.py` — add `network_paths`, `dc_sites` to `ResourceGraph`; new `NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding` models (D-09, D-10)
- `cli/infracanvas/security/engine.py` — reuse generic rule engine for NET-* findings (D-12)
- `cli/infracanvas/main.py` — add `--flowmap` flag to `scan` command (D-04)
- `viewer/src/store.ts` — extend Zustand with `networkPaths`, `dcSites`, `flowMapFilters`, `selectedPath` (D-06)
- `viewer/src/App.tsx` — add `[Canvas | FlowMap]` top-level toggle (D-06)
- `viewer/src/types.ts` — TypeScript mirror of new Pydantic models (matches-backend-models convention)

### External references
- AWS SDK: TGW describe-route-tables, describe-transit-gateway-attachments, VPC describe-route-tables, describe-network-acls, Direct Connect describe-virtual-interfaces, VPC Flow Logs, CloudWatch Logs Insights
- Azure SDK: `azure-mgmt-network` (VirtualWAN, VirtualHub, VnetConnection, NSG, ExpressRoute), `azure-mgmt-monitor` for flow logs
- No external ADR docs referenced by user during discussion.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`cli/infracanvas/security/engine.py`** — Generic rule engine with 8 operators. Works over any Pydantic model. Reuse directly for NET-* network findings by dropping new YAML files into `cli/infracanvas/security/rules/network/`. No engine changes expected.
- **`cli/infracanvas/graph/models.py`** — `ResourceGraph` is the central model. Additive extension (new optional fields) keeps all existing readers backwards-compatible. v2.0 → v2.1 schema bump is additive.
- **`cli/infracanvas/security/scorer.py`** — Score card calculation. Network findings can feed a new "Network" dimension in the existing score card (planner's call on whether to expand scorer in 3a).
- **`viewer/src/components/DiagramCanvas.tsx`** — Sibling pattern for `FlowMapCanvas.tsx`. Reuse ReactFlow setup, zoom/pan, minimap, selection model.
- **`viewer/src/components/FilterPanel.tsx` + `DetailPanel.tsx`** — Sibling pattern for FlowMap filter/detail panels (FMV-05). Reuse severity filter chip + expandable card conventions.
- **`viewer/src/store.ts`** — Zustand store. Add new slice for FlowMap state alongside existing graph/filters/selection.
- **`viewer/src/lib/colors.ts`** — Extend with forward/return path colors (blue/orange per spec) and divergence marker color (red pulsing).
- **`cli/infracanvas/export/html.py`** — Template injection (`window.__INFRACANVAS_DATA__`) already embeds arbitrary ResourceGraph JSON. Will transparently pick up new fields — no exporter changes needed.

### Established Patterns

- **Opt-in cloud API with env-var creds + warn-on-missing** — Phase 2 `--shadow` precedent applies directly to `--flowmap`. Do not invent a new credential pattern.
- **Unified findings pipeline** — All findings (security, policy, network) flow through `security/engine.py` and surface in the same DetailPanel. Phase 2 D-09.
- **YAML rule files with condition/operator/value** — NET-* rules use the same schema as SEC-* rules; new directory only.
- **Additive JSON schema bumps** — Phase 2 bumped v1.x → v2.0 additively; this phase bumps v2.0 → v2.1 additively. No breaking changes.
- **Pydantic models ↔ TypeScript interfaces mirror** — Every new Python model requires a matching TS interface in `viewer/src/types.ts`. Convention is strict.

### Integration Points

- New CLI flag: `infracanvas scan ./tf --flowmap` in `cli/infracanvas/main.py`
- New Python module tree: `cli/infracanvas/flowmap/` (collectors, path-stubs, tests)
  - `cli/infracanvas/flowmap/aws.py` — TGW + VPC + Direct Connect collectors
  - `cli/infracanvas/flowmap/azure.py` — vWAN + vNet + ExpressRoute collectors
  - `cli/infracanvas/flowmap/flow_logs.py` — VPC + Azure Monitor flow-log ingestion
- New rule directory: `cli/infracanvas/security/rules/network/` (NET-* YAML)
- New viewer module tree: `viewer/src/components/flowmap/`
  - `viewer/src/components/flowmap/FlowMapCanvas.tsx`
  - `viewer/src/components/flowmap/FlowMapFilterPanel.tsx`
  - `viewer/src/components/flowmap/PathDetailPanel.tsx`
  - `viewer/src/components/flowmap/nodes/` (DCSiteGroup, RouterNode, FirewallNode with capacity gauge)
- Viewer top-level toggle lives in `viewer/src/App.tsx`. Toggle state lives in `store.ts` (`activeTab: 'canvas' | 'flowmap'`).
- HTML export path (`cli/infracanvas/export/html.py`) is untouched — it serialises the full ResourceGraph including the new fields.

</code_context>

<specifics>
## Specific Ideas

- **`--flowmap` is a flag on `scan`, not a new subcommand.** One command, one HTML, one file to share. UX parity with `--shadow`.
- **Viewer tab label: "FlowMap"** (not "Network Paths" or similar). The product name is FlowMap; the tab mirrors the brand.
- **Empty state in FlowMap tab** when no `--flowmap` was passed: explicit CTA pointing to the flag, not a generic "no data" message.
- **"Beta, free during preview"** is the marketing frame for FlowMap through 3a + 3b. Use it in CLI help text, viewer empty state, and release-note copy to set expectations that paywalling lands in Phase 4.

</specifics>

<deferred>
## Deferred Ideas

### To Phase 3b (new phase to be inserted after Phase 3)
- DC Collector Agent — Go scaffold, cobra CLI, daemon mode — **DCA-01**
- NETCONF/RESTCONF Cisco IOS-XE client — **DCA-02**
- SSH CLI fallback parser for older IOS — **DCA-03**
- NetFlow v9 / IPFIX UDP collector with 30s aggregation — **DCA-04**
- Encrypted API push to InfraCanvas cloud — **DCA-05** (requires stubbed endpoint; real endpoint in Phase 4)
- Daemon mode scheduling (routes 5min / BGP 1min / NetFlow 30s) — **DCA-06**
- Config file import fallback — **DCA-07**
- Single binary packaging (Linux amd64 primary, macOS arm64 secondary) — **DCA-08**
- Security review packet for CAB approval — **DCA-09**
- Cisco ASA REST API client — **ASA-01**
- Cisco FMC REST API client — **ASA-02**
- ASA SSH CLI fallback — **ASA-03**
- Checkpoint Management API (access rules, NAT, VPN) — **CKP-01**
- Checkpoint object mapping to FlowMap topology — **CKP-02**
- Forward path computation — **PTH-01**
- Return path computation with BGP/static boundary — **PTH-02**
- NetFlow correlation to confirm paths — **PTH-03**
- Asymmetric routing detector — **ASY-01**
- Root-cause classifier (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY) — **ASY-02**
- Stateful-firewall-on-one-path CRITICAL finding (NET-010) — **ASY-03**
- NET-* path-dependent findings (remaining NET-001..012 after 3a allocation) — **NFN-01 (full)**
- Route change alerting vs last scan baseline — **NFN-02**

### To Phase 4 (SaaS + billing infrastructure phase)
- Team-tier Stripe product at $299/mo — **TIR-02**
- FlowMap tier gating (Team/Enterprise check) — **TIR-01**

### Not taken forward
None — no scope-creep ideas came up during discussion.

### Reviewed Todos (not folded)
None — no todos reviewed.

</deferred>

---

*Phase: 03-flowmap-v1-0*
*Context gathered: 2026-04-18*
