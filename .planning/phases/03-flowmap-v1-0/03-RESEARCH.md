# Phase 3: FlowMap v1.0 — Research (scope: 3a cloud-only foundation)

**Researched:** 2026-04-18
**Domain:** Python CLI extension (AWS network collection via boto3, Azure network collection via azure-mgmt-network) + React viewer extension (FlowMap tab, dual-color path edges, DC site group placeholder nodes) + additive Pydantic/JSON schema bump (v2.0 → v2.1) + YAML-driven NET-* findings through existing rule engine
**Confidence:** HIGH (codebase verified), HIGH (boto3 + Azure SDK APIs verified against live PyPI + official docs), MEDIUM (FlowMap layout — no in-repo precedent for path-flow diagrams), MEDIUM (fixture strategy — moto coverage gaps for newer TGW APIs likely exist but no blocking issue verified), LOW (NET-* rule catalogue — no prior network-layer rule set in repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (Phase 3a scope)

**Phase scope & split**
- **D-01:** Phase 3 splits into 3a (this phase) and 3b. 3a = collect + show cloud topology. 3b = DC Agent + path math + asymmetric detection + on-prem integrations. Roadmap update required post-CONTEXT: insert Phase 3b; update REQUIREMENTS.md phase mapping for deferred items.
- **D-02:** Tier gating (TIR-01, TIR-02) is removed from Phase 3 entirely and belongs in Phase 4. 3a ships with FlowMap open and unrestricted — "beta, free during preview."

**Cloud network collection architecture**
- **D-03:** CLI (Python) owns cloud collection; DC Agent (3b) owns on-prem. AWS TGW + VPC + Direct Connect + Azure vWAN + vNet + ExpressRoute collectors run inside the CLI Python process using boto3 + Azure SDK with customer's local credentials.
- **D-04:** CLI surface is `infracanvas scan ./terraform --flowmap`. Flag on the existing `scan` command triggers cloud network collectors alongside the resource scan, producing one HTML with both Canvas and FlowMap tabs. Mirrors `--shadow` UX.
- **D-05:** Credentials & error handling follow Phase 2 precedent:
  - AWS creds: standard chain (env vars → `~/.aws/credentials` → instance profile)
  - Azure creds: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID` env vars only
  - Missing creds: yellow warning + continue. Never hard-fail.
  - Region scope: infer from `.tf` files; single-region per cloud.

**Viewer integration**
- **D-06:** FlowMap renders as a **tab** inside the existing single-file HTML. Top-level toggle: `[Canvas | FlowMap]`. Same Zustand store extended with `activeTab`, `networkPaths`, `dcSites`, `flowMapFilters`, `selectedPath`. Same export pipeline. One HTML output.
- **D-07:** FlowMap owns its own **dedicated layout engine** (not the existing dagre/tier layout). FlowMapCanvas owns its own layout. Dual-color path rendering (blue forward, orange return) is a ReactFlow edge style — exact SVG approach is Claude's discretion.
- **D-08:** When a scan has no FlowMap data (user ran `scan` without `--flowmap`, or collection failed), FlowMap tab renders an empty state with explicit CTA: "No network topology collected. Re-run with `infracanvas scan ./terraform --flowmap` to populate." Tab visible but inactive. No hiding.

**Data model & JSON schema**
- **D-09:** Extend `ResourceGraph` Pydantic model with `network_paths: list[NetworkPath]` (empty in 3a) and `dc_sites: list[DCSite]` (empty in 3a). JSON schema bump v2.0 → **v2.1** (additive, backwards-compatible). Viewer reads both fields defensively.
- **D-10:** All four Pydantic models (`NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding`) land in 3a even though 3a does not populate `NetworkPath` / `PathHop` (3b populates via path tracer). Defines full schema so 3b can land populators without schema churn.

**Network findings scope (3a)**
- **D-11:** 3a ships only **cloud-only, path-independent** NET findings — rules that evaluate against single-resource state without comparing forward/return paths. Path-dependent findings defer to 3b. Exact NET-id assignment across 3a vs 3b is Claude's discretion based on rule path-dependency analysis.
- **D-12:** NET-* findings use the existing security rule YAML engine (`cli/infracanvas/security/engine.py`). The engine is generic; new YAML directory `cli/infracanvas/security/rules/network/` holds NET-* rules. Findings flow through the unified pipeline (security + policy + network).

### Claude's Discretion

- Exact AWS / Azure SDK calls and API batching strategy (boto3 paginators, async vs sync, retry/backoff)
- Flow-log ingestion approach (S3 pull vs CloudWatch Logs Insights query vs Azure Monitor query)
- FlowMapCanvas layout algorithm (custom vs elkjs vs hierarchical-with-fixed-ranks)
- Dual-color edge rendering technique (ReactFlow edge `markerEnd` + `strokeDasharray` vs custom SVG layer)
- Exact NET-id allocation across 3a vs 3b based on rule path-dependency
- Number of cloud-only NET rules to ship in 3a (minimum 4-6 meaningful rules per cloud — AWS and Azure)
- Test fixture strategy for AWS/Azure network collection (moto/placebo, hand-crafted JSON, or live-scan snapshots with sanitization)

### Deferred Ideas (OUT OF SCOPE for 3a)

**To Phase 3b (new phase inserted after Phase 3):**
- DC Collector Agent — Go scaffold, cobra CLI, daemon mode (**DCA-01**)
- NETCONF/RESTCONF Cisco IOS-XE client (**DCA-02**)
- SSH CLI fallback parser for older IOS (**DCA-03**)
- NetFlow v9 / IPFIX UDP collector (**DCA-04**)
- Encrypted API push (**DCA-05**)
- Daemon scheduling, config import, binary packaging, CAB packet (**DCA-06..09**)
- Cisco ASA REST + FMC REST + SSH fallback (**ASA-01..03**)
- Checkpoint Management API + object mapping (**CKP-01, CKP-02**)
- Forward/return path computation + NetFlow correlation (**PTH-01, PTH-02, PTH-03**)
- Asymmetric routing detector + root-cause classifier + impact assessment (**ASY-01, ASY-02, ASY-03**)
- Path-dependent NET-* findings + route change alerting (**NFN-01 full, NFN-02**)

**To Phase 4 (SaaS + billing):**
- Team-tier Stripe product at $299/mo (**TIR-02**)
- FlowMap tier gating (**TIR-01**)

**Not taken forward:** None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FDM-01 | Pydantic models for NetworkPath, PathHop, DCCollectorReading, NetworkFinding | Pydantic v2 already in use (pyproject.toml line 36); add to `cli/infracanvas/graph/models.py` alongside existing `ResourceNode`/`Finding` |
| FDM-02 | Extended ResourceGraph JSON schema with network_paths and dc_sites | Additive bump v2.0→v2.1 on existing `ResourceGraph.version` constant in `graph/models.py` line 113 |
| FDM-03 | NetworkFinding rule IDs NET-001 through NET-012 | Claude's discretion (D-11): 3a gets path-independent subset; planner allocates 3a vs 3b. Minimum 4-6 meaningful rules per cloud. |
| AWS-01 | TGW route tables, attachments, VPN connections | boto3 `ec2.describe_transit_gateways`, `describe_transit_gateway_route_tables`, `get_transit_gateway_route_table_associations`, `get_transit_gateway_route_table_propagations`, `search_transit_gateway_routes`, `describe_transit_gateway_attachments`, `describe_vpn_connections` |
| AWS-02 | VPC route tables, NACLs, Direct Connect virtual interfaces | boto3 `ec2.describe_route_tables`, `describe_network_acls`, `directconnect.describe_virtual_interfaces`, `describe_connections` |
| AWS-03 | CloudWatch VPC/TGW flow logs for traffic confirmation | 3a ships flow-log **metadata** (which logs exist, destination, format). Full log ingestion (CloudWatch Logs Insights or S3 pull) is optional in 3a — Claude's discretion. Populating log query results is path-dependent → most flow-log work defers to 3b. |
| AZN-01 | Azure vWAN hubs, connections, Secure Hub effective routes | azure-mgmt-network `NetworkManagementClient`: `virtual_wans.list`, `virtual_hubs.list`, `hub_virtual_network_connections.list`, `virtual_hubs.begin_get_effective_virtual_hub_routes` |
| AZN-02 | vNet peering topology, NSG effective rules per NIC/subnet | `virtual_networks.list`, `virtual_network_peerings.list`, `network_security_groups.list`, `network_interfaces.begin_get_effective_network_security_group_rules` (per NIC) |
| AZN-03 | ExpressRoute circuit state, Azure Monitor NSG flow logs | `express_route_circuits.list`, `express_route_circuit_peerings.list`; NSG flow log metadata via `flow_logs.list` (under `network_watchers`). Full ingestion deferred — see AWS-03 |
| FMV-01 | FlowMapCanvas.tsx with dual-colour path rendering (blue forward, orange return) | Custom ReactFlow `<Edge>` component with two SVG `<path>` elements; in 3a the `network_paths` array is empty — canvas renders topology without paths. Path rendering code ships in 3a so 3b populator can use it without viewer churn. |
| FMV-02 | Divergence point marker (red pulsing) with tooltip explanation | Defer render to 3b (requires path comparison); 3a ships the CSS/component scaffold |
| FMV-03 | DC site group nodes, router/firewall node types | 3a ships the node component types (`DCSiteGroup`, `RouterNode`, `FirewallNode`); `dc_sites` array empty in 3a → empty region displayed |
| FMV-04 | Firewall capacity gauge (mini progress bar on firewall nodes) | Component ready in 3a; data fed in 3b from DCCollectorReading |
| FMV-05 | FlowMap filter panel and network path detail panel | Mirror existing `FilterPanel.tsx` + `DetailPanel.tsx` patterns; new `FlowMapFilterPanel.tsx` + `PathDetailPanel.tsx`; 3a filters on topology-level (cloud, severity) not path-level |
| NFN-01 (partial) | Network findings engine: cloud-only path-independent NET rules | Reuse existing `security/engine.py` (verified at `cli/infracanvas/security/engine.py` lines 12-34); new YAML directory `cli/infracanvas/security/rules/network/` |
</phase_requirements>

---

## Summary

Phase 3a is a **cloud-data-collection + viewer-tab-addition** phase. It extends three established Phase 2 patterns without inventing new ones: (1) the `--shadow` opt-in cloud API pattern (mirrored directly for `--flowmap`), (2) the YAML-driven rule engine (new `rules/network/` directory, zero engine code changes), and (3) the additive JSON schema bump (v2.0 → v2.1, same mechanism as Phase 1→2). The viewer gets a top-level tab toggle, a new ReactFlow canvas sibling to `DiagramCanvas`, and two new panel components that mirror `FilterPanel`/`DetailPanel`.

The non-obvious architectural choice locked by D-10: all four Pydantic models (`NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding`) land in 3a even though three of them won't be populated until 3b. This avoids schema churn between phases and lets the viewer render from real shapes immediately. The planner should wire empty-array defaults on `network_paths` and `dc_sites` so the existing `export_html.py` → `window.__INFRACANVAS_DATA__` pipeline transparently picks them up without exporter changes.

The two real risks: (1) **boto3 TGW coverage in moto is incomplete** for some newer paginator/search APIs — a hybrid fixture strategy (placebo-recorded sanitized JSON + hand-crafted edge cases) beats a pure-moto approach; (2) **FlowMap layout is net-new** — there's no dagre/tier precedent to lean on for left-to-right path flow. The recommendation is **elkjs with `elk.algorithm: layered` + `elk.direction: RIGHT`** — it's the React Flow blessed approach for hierarchical left-to-right flows, ships as pure JS (no WASM), and integrates cleanly with the existing `@xyflow/react` 12.6.0 dependency.

**Primary recommendation:** Start with Pydantic models + schema bump (FDM-01/02/03) → AWS collector (AWS-01/02, defer AWS-03 deep ingest) → Azure collector (AZN-01/02, defer AZN-03 deep ingest) → `--flowmap` CLI flag mirror of `--shadow` → NET-* YAML rules (4-6 per cloud) → viewer tab toggle + FlowMapCanvas with elkjs layered layout → filter/detail panels → empty-state CTA. The viewer work can run in parallel with the collector work since the Pydantic schema and TypeScript mirror lock the contract early.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pydantic model schema (NetworkPath, PathHop, DCCollectorReading, NetworkFinding) | CLI / Graph | Viewer / Types | Defined Python-side, mirrored to TypeScript. Existing pattern: `models.py` ↔ `viewer/src/types.ts`. |
| AWS network collection (TGW, VPC, Direct Connect, flow-log metadata) | CLI / Collector | AWS API | boto3 read-only; mirrors `shadow/detector.py`. |
| Azure network collection (vWAN, vNet, NSG, ExpressRoute, flow-log metadata) | CLI / Collector | Azure API | azure-mgmt-network + azure-identity; `ARM_*` env-var auth. |
| NET-* rule YAML + evaluation | CLI / Security | — | Zero engine changes; new YAML dir; generic rule engine at `security/engine.py` handles it. |
| JSON schema bump (additive) | CLI / Graph | Export | `ResourceGraph.version = "2.1"`; existing `export_html.py` transparently passes through new fields. |
| `--flowmap` CLI flag | CLI / Main | — | `main.py` scan command; mirrors `--shadow` (line 306-309) exactly. |
| Viewer tab toggle `[Canvas | FlowMap]` | Viewer / App.tsx | Zustand store | `activeTab: 'canvas' | 'flowmap'` slice; top-level conditional render. |
| FlowMapCanvas (ReactFlow + elkjs layered layout) | Viewer / Components | elkjs, @xyflow/react | Sibling to `DiagramCanvas.tsx`; own layout; dual-color path edge component scaffold. |
| Dual-color path edges (blue forward / orange return) | Viewer / Components | @xyflow/react custom edges | Custom Edge component with two SVG `<path>` elements per `BiDirectionalEdge` pattern. |
| FlowMap empty-state CTA | Viewer / Components | — | Empty `graph.network_paths` + empty `graph.dc_sites` → render CTA panel with re-run instruction. |
| FlowMap filter + detail panels | Viewer / Components | Zustand | Mirror `FilterPanel.tsx` + `DetailPanel.tsx` verbatim. |

---

## Standard Stack

### Core — Python CLI (additions to existing dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `boto3` | `>=1.40,<2` | AWS TGW/VPC/Direct Connect + flow-log API client | Already in `[project.optional-dependencies] shadow`; extend to `[flowmap]` extra. Current PyPI latest: **1.42.91** [VERIFIED: `pip index versions boto3` 2026-04-18]. Phase 2 precedent uses `boto3>=1.34` (pyproject.toml line 42). Bump the floor to 1.40 so TGW route-table propagation + search APIs [VERIFIED: boto3 docs] are guaranteed present. |
| `azure-identity` | `>=1.20,<2` | Auth chain: `ClientSecretCredential` driven by `ARM_*` env vars, or `DefaultAzureCredential` fallback | Microsoft standard. Current PyPI latest: **1.25.3** [VERIFIED: `pip index versions azure-identity` 2026-04-18]. Python 3.12 supported [CITED: pypi.org/project/azure-identity]. |
| `azure-mgmt-network` | `>=28,<31` | VirtualWAN, VirtualHub, vNet peering, NSG effective rules, ExpressRoute, flow-log metadata | Current PyPI latest: **30.2.0** [VERIFIED: `pip index versions azure-mgmt-network` 2026-04-18]. Contains `begin_get_effective_network_security_group_rules` (NIC-level effective NSG) and `begin_get_effective_virtual_hub_routes` (vWAN) — both needed for AZN-01/AZN-02. Python 3.9+ required [CITED: learn.microsoft.com/python-mgmt-network-readme]. |
| `azure-mgmt-resource` | `>=23,<26` | Resource group enumeration for scoping Azure queries | Current PyPI latest: **25.0.0** [VERIFIED: `pip index versions azure-mgmt-resource` 2026-04-18]. Needed because most Azure SDK operations require `resource_group_name` — we infer it from the `.tf` files' `resource_group_name` attr or enumerate via `resource_groups.list`. |

### Core — Viewer (additions to existing dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `elkjs` | `^0.11.1` | Layered left-to-right layout for FlowMap paths | Current npm latest: **0.11.1** [VERIFIED: `npm view elkjs version` returned 0.11.1, modified 2026-03-03]. React Flow's [blessed layout option](https://reactflow.dev/examples/layout/elkjs) for hierarchical diagrams. Pure JS, no WASM, integrates cleanly with `@xyflow/react` 12.6.0 already in `viewer/package.json`. Documented example: `elk.algorithm: 'layered'` + `elk.direction: 'RIGHT'` produces left-to-right path flow [CITED: reactflow.dev/examples/layout/elkjs]. |

### Supporting — Python test fixtures

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `moto` | `>=5.1,<6` | In-process AWS API mocker for unit tests | Current PyPI latest: **5.1.22** [VERIFIED]. Use for **primary AWS unit tests** (VPC, NACL, security group — stable moto coverage). Add to `[project.optional-dependencies] dev` or `[test]`. |
| `placebo` | `^0.10.0` | Records and replays boto3 API responses from real calls | Current PyPI latest: **0.10.0** [VERIFIED]. Use for **TGW + Direct Connect fixture recording** where moto coverage may lag. One-time recording against a sanitized test account, checked-in JSON, replayed in CI without live AWS. |
| `botocore-stubs` | already present (`boto3-stubs[ec2,s3,rds]` in Phase 2) | Type stubs | Extend existing `boto3-stubs[ec2,s3,rds]` → `boto3-stubs[ec2,s3,rds,directconnect]` for DX. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **elkjs (layered)** | Custom dagre layout with `rankdir: 'LR'` | dagre already in `viewer/package.json`. But FlowMap needs more hop control (pinning hops to lanes, handling divergence) — elkjs has richer options [CITED: reactflow.dev]. Recommendation: **elkjs** for FlowMapCanvas; keep dagre for Canvas. |
| **elkjs** | Fixed-rank hierarchical layout (hand-coded) | Cheaper initial impl but brittle as path count grows. elkjs is proven for up to ~200 nodes at interactive performance [ASSUMED]. |
| **moto-only fixtures** | placebo-only fixtures | moto doesn't yet fully implement `search_transit_gateway_routes` + propagations [ASSUMED — moto's EC2 TGW surface is partial per maintainer guidance]; placebo-recorded fixtures against a one-time real account give exact production shapes. |
| **hand-crafted JSON fixtures** | placebo | Hand-crafted is faster for simple shapes but drifts from real API shape over time. Recommendation: **hybrid** — moto for coarse shapes, placebo-recorded JSON for TGW/DirectConnect/ExpressRoute response shapes. |
| **CloudWatch Logs Insights (3a)** | S3-based VPC flow log pull | Insights is cheaper for one-off queries; S3 pull is cheaper at scale. 3a defers deep ingestion — recommendation is to **collect flow-log metadata only in 3a** (which logs exist, destination bucket, log format) and defer query execution to 3b where path data makes the correlation meaningful. |
| **Custom SVG edge layer** | ReactFlow `<BaseEdge>` with two `<path>` children | Custom SVG overlay is more flexible but loses ReactFlow's marker, selection, and z-index handling. Recommendation: **custom Edge component** — two stacked SVG `<path>` elements at slight y-offset, blue `#3B82F6` stroke for forward and orange `#F97316` stroke for return, using the `BiDirectionalEdge` pattern from the [React Flow custom edges example](https://reactflow.dev/examples/edges/custom-edges). |

### Installation (pyproject.toml additions)

```toml
[project.optional-dependencies]
shadow = ["boto3>=1.40,<2", "boto3-stubs[ec2,s3,rds]>=1.40"]
flowmap = [
    "boto3>=1.40,<2",
    "boto3-stubs[ec2,s3,rds,directconnect]>=1.40",
    "azure-identity>=1.20,<2",
    "azure-mgmt-network>=28,<31",
    "azure-mgmt-resource>=23,<26",
]
test = ["moto>=5.1,<6", "placebo>=0.10"]
```

### Installation (viewer/package.json additions)

```json
"dependencies": {
  "elkjs": "^0.11.1"
}
```

**Version verification performed 2026-04-18:**
- `boto3`: latest 1.42.91 [VERIFIED: pip index]
- `azure-identity`: latest 1.25.3 [VERIFIED: pip index]
- `azure-mgmt-network`: latest 30.2.0 [VERIFIED: pip index]
- `azure-mgmt-resource`: latest 25.0.0 [VERIFIED: pip index]
- `azure-mgmt-monitor`: latest 7.0.0 [VERIFIED: pip index] — **only needed if 3a does deep flow-log ingestion; skip if deferring to 3b**
- `elkjs`: latest 0.11.1, published 2026-03-03 [VERIFIED: npm view]
- `moto`: latest 5.1.22 [VERIFIED: pip index]
- `placebo`: latest 0.10.0 [VERIFIED: pip index]

---

## Architecture Patterns

### System Architecture Diagram

```
                          infracanvas scan ./terraform --flowmap
                                          │
                                          ▼
                  ┌─────────────────────────────────────────────┐
                  │  main.py _run_scan(flowmap=True)            │
                  └─────────────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     ▼                                    ▼                                    ▼
┌──────────┐                    ┌──────────────────┐                 ┌─────────────────┐
│ parser/  │                    │ flowmap/aws.py   │                 │ flowmap/azure.py│
│ hcl.py   │                    │ (boto3 read)     │                 │ (az sdk read)   │
│(existing)│                    │                  │                 │                 │
└──────────┘                    │ describe_*_tgw_* │                 │ virtual_wans    │
     │                          │ describe_*_vpc_* │                 │ virtual_hubs    │
     │                          │ describe_*_dx_*  │                 │ vnet peerings   │
     │                          │ describe_nacls   │                 │ nsg effective   │
     │                          │ flow-log meta    │                 │ expressroute    │
     │                          └──────────────────┘                 └─────────────────┘
     │                                    │                                    │
     ▼                                    │                                    │
┌──────────────┐                          │                                    │
│ graph/       │                          │                                    │
│ builder.py   │                          │                                    │
│ → ResourceGr │                          │                                    │
└──────────────┘                          │                                    │
     │                                    │                                    │
     │      ┌─────────────────────────────┴────────────────────────────────────┘
     │      │  (network_paths empty in 3a; dc_sites empty in 3a;
     │      │   collectors populate network topology nodes/edges onto ResourceGraph
     ▼      ▼   directly as resource-typed nodes e.g. aws_ec2_transit_gateway, azurerm_virtual_hub)
┌────────────────────────────────────────────────────────────────────┐
│ security/engine.py evaluate_all()                                  │
│   - existing SEC-* / AZ-* rules (from rules/aws/, rules/azure/)    │
│   - NEW: NET-* rules (from rules/network/) — path-independent only │
└────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                            ┌────────────────────────────┐
                            │ ResourceGraph v2.1         │
                            │   + network_paths: []      │  ← empty in 3a
                            │   + dc_sites: []           │  ← empty in 3a
                            │   + findings[] per node    │
                            └────────────────────────────┘
                                          │
                                          ▼
                            ┌────────────────────────────┐
                            │ export/html.py             │
                            │   → window.__INFRACANVAS_  │
                            │     DATA__ injection       │
                            │   (no exporter changes)    │
                            └────────────────────────────┘
                                          │
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │  infracanvas-report.html (single file)  │
                     └─────────────────────────────────────────┘
                                          │
                                          ▼
                        ┌────────────────────────────────────────┐
                        │  App.tsx (viewer entry)                │
                        │    useEffect → setGraph(injected)      │
                        │    activeTab: 'canvas' | 'flowmap'     │
                        └────────────────────────────────────────┘
                                          │
                  ┌───────────────────────┴─────────────────────────┐
                  ▼                                                 ▼
        ┌─────────────────────┐                         ┌────────────────────────┐
        │ DiagramCanvas.tsx   │                         │ FlowMapCanvas.tsx      │
        │ (existing)          │                         │ (new — elkjs layered)  │
        │ dagre tier layout   │                         │ direction: RIGHT       │
        └─────────────────────┘                         │                        │
                  │                                     │ Nodes: cloud TGW, vWAN │
                  ▼                                     │   hubs, vNets, VPCs,   │
        ┌─────────────────────┐                         │   DCSiteGroup (empty), │
        │ FilterPanel.tsx     │                         │   RouterNode (empty),  │
        │ DetailPanel.tsx     │                         │   FirewallNode (empty) │
        └─────────────────────┘                         │                        │
                                                        │ Edges: path-hops dual- │
                                                        │   color (blue fwd /    │
                                                        │   orange ret) — empty  │
                                                        │   in 3a                │
                                                        └────────────────────────┘
                                                                  │
                                                  ┌───────────────┴────────────────┐
                                                  ▼                                ▼
                                        ┌────────────────────┐           ┌──────────────────┐
                                        │FlowMapFilterPanel  │           │ PathDetailPanel  │
                                        │.tsx (new)          │           │ .tsx (new)       │
                                        └────────────────────┘           └──────────────────┘

                                  3a Empty States:
                                    network_paths=[] → canvas shows cloud topology only
                                                       (no dual-color edges rendered)
                                    dc_sites=[]      → DC region of canvas shows empty
                                                       region with "Install DC Agent
                                                       (coming in 3b)" placeholder
                                    --flowmap not passed → tab visible but empty state
                                                       CTA: "Re-run with --flowmap"
```

### Recommended Project Structure

```
cli/
  infracanvas/
    flowmap/                          # NEW — sibling to shadow/
      __init__.py
      aws.py                          # AWS TGW + VPC + DX collectors (~400 lines expected)
      azure.py                        # Azure vWAN + vNet + NSG + ExpressRoute collectors
      flow_logs.py                    # Flow-log metadata collector (3a) / ingestion (3b)
      models_ext.py                   # Graph-building helpers (converts boto3/Azure responses → ResourceNode)
    graph/
      models.py                       # EXTEND: add NetworkPath, PathHop, DCCollectorReading,
                                      #   DCSite, NetworkFinding (network-aware), bump version to "2.1",
                                      #   add network_paths, dc_sites to ResourceGraph
    security/
      engine.py                       # NO CHANGE — generic engine handles NET-* natively
      rules/
        network/                      # NEW DIRECTORY
          aws_tgw.yaml                # NET-001..NET-00X (AWS TGW-scoped rules)
          aws_vpc.yaml                # AWS VPC route-table + NACL rules
          aws_dx.yaml                 # Direct Connect rules
          azure_vwan.yaml             # Azure vWAN hub rules
          azure_vnet.yaml             # Azure vNet peering + NSG rules
          azure_expressroute.yaml     # ExpressRoute rules
    main.py                           # EXTEND: add --flowmap flag to scan command (mirror --shadow)
  tests/
    fixtures/
      flowmap/                        # NEW
        aws/
          tgw_single_vpc/             # placebo-recorded responses for TGW + single VPC
          tgw_multi_vpc/              # placebo-recorded responses for realistic TGW hub+spoke
          dx_connection/              # Direct Connect fixtures
        azure/
          vwan_single_hub/            # recorded vWAN responses
          vnet_peering_mesh/          # hub+spoke vNet peering
          nsg_effective/              # NSG effective rules per NIC
    test_flowmap_aws.py               # AWS collector unit + integration tests
    test_flowmap_azure.py             # Azure collector unit + integration tests
    test_flowmap_network_rules.py     # NET-* rule evaluation tests
    test_flowmap_integration.py       # End-to-end --flowmap → ResourceGraph → JSON

viewer/
  src/
    store.ts                          # EXTEND: add activeTab, flowMapFilters, selectedPath slices
    types.ts                          # EXTEND: NetworkPath, PathHop, DCCollectorReading, DCSite,
                                      #   NetworkFinding TS mirrors
    App.tsx                           # EXTEND: add <TabBar /> + conditional render
    components/
      TabBar.tsx                      # NEW — [Canvas | FlowMap] top-level toggle
      flowmap/                        # NEW DIRECTORY
        FlowMapCanvas.tsx             # ReactFlow + elkjs layered layout
        FlowMapFilterPanel.tsx        # Mirror FilterPanel
        PathDetailPanel.tsx           # Mirror DetailPanel
        FlowMapEmptyState.tsx         # CTA when no --flowmap was run
        edges/
          PathEdge.tsx                # Custom dual-color edge (blue fwd + orange ret)
        nodes/
          DCSiteGroupNode.tsx         # Group node for DC sites
          RouterNode.tsx              # Router node type
          FirewallNode.tsx            # Firewall node with capacity gauge
          CloudHubNode.tsx            # TGW / vWAN hub rendering
        lib/
          elkLayout.ts                # elkjs config + conversion
          pathColors.ts               # Forward/return color constants
    lib/
      colors.ts                       # EXTEND: forward=#3B82F6, return=#F97316, divergence=#EF4444 (pulse)
    __tests__/
      flowmap/
        FlowMapCanvas.test.tsx
        PathEdge.test.tsx
        elkLayout.test.ts
        tabBar.test.tsx
```

### Pattern 1: Mirror `--shadow` for `--flowmap` flag plumbing (D-04)

**What:** Add a new boolean flag to the existing `scan` Typer command that conditionally invokes cloud collectors. No new subcommand.

**When to use:** Any phase adding opt-in cloud API collection. This is the established InfraCanvas UX pattern.

**Example (pulled from verified codebase — `cli/infracanvas/main.py` lines 306-309 + 117-129):**

```python
# main.py — existing --shadow flag pattern to mirror:
shadow: Annotated[
    bool,
    typer.Option("--shadow", help="Compare live AWS API vs Terraform state (requires boto3)"),
] = False,

# Inside _run_scan():
if shadow:
    try:
        from infracanvas.shadow.detector import ShadowDetector
        inferred_region = str(graph.metadata.get("region", "")) or "us-east-1"
        for node in graph.nodes:
            if node.region:
                inferred_region = node.region
                break
        detector = ShadowDetector(region=inferred_region)
        graph = detector.detect(graph)
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] {exc}. Skipping shadow scan.")
```

New `--flowmap` follows the same shape:

```python
flowmap: Annotated[
    bool,
    typer.Option("--flowmap", help="Collect cloud network topology (TGW/VPC/vWAN/NSG). Requires boto3 + azure-mgmt-network."),
] = False,

# Inside _run_scan():
if flowmap:
    aws_region = _infer_aws_region(graph)
    az_subscription = os.environ.get("ARM_SUBSCRIPTION_ID")
    try:
        from infracanvas.flowmap.aws import AwsNetworkCollector
        graph = AwsNetworkCollector(region=aws_region).collect(graph)
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] {exc}. Skipping AWS network collection.")
    try:
        from infracanvas.flowmap.azure import AzureNetworkCollector
        if az_subscription:
            graph = AzureNetworkCollector(subscription_id=az_subscription).collect(graph)
        else:
            out.print("[yellow]Warning:[/yellow] --flowmap requires ARM_SUBSCRIPTION_ID. Skipping Azure network collection.")
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] {exc}. Skipping Azure network collection.")
```

### Pattern 2: Yellow-warn-never-hard-fail on missing creds (D-05, Phase 2 D-02)

**What:** Missing boto3/Azure SDK or missing credentials emits a yellow warning and continues the rest of the scan. Verified from `shadow/detector.py` lines 45-57 and existing `main.py` wrap at lines 117-129.

**Example:**
```python
# In flowmap/aws.py
class AwsNetworkCollector:
    def collect(self, graph: ResourceGraph) -> ResourceGraph:
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 not installed. Install with: pip install 'infracanvas[flowmap]'")

        session = boto3.Session()
        if not session.get_credentials():
            raise RuntimeError("--flowmap requires AWS credentials. Skipping AWS network collection.")

        # proceed with collection…
```

The `main.py` wrapper catches `RuntimeError` and prints yellow. Never hard-fails.

### Pattern 3: NET-* YAML rules reuse existing engine (D-12)

**What:** The existing rule engine (`cli/infracanvas/security/engine.py` lines 12-34) already iterates `rules = load_rules()` and matches on `node.type in rule.resource_types`. Dropping new YAML files into `rules/network/` with new resource types (e.g., `aws_ec2_transit_gateway_route_table`, `azurerm_virtual_hub`) is sufficient — zero engine code changes. Verified by reading `engine.py` in full.

**Example NET-* YAML (following the verified `networking.yaml` schema — `rules/aws/networking.yaml` lines 1-10):**

```yaml
- id: NET-001
  title: "Transit Gateway route table has no associations"
  severity: medium
  resource_types: ["aws_ec2_transit_gateway_route_table"]
  framework_ids: ["CIS-4.1", "NIST-SC-7"]
  condition:
    attribute: "association_count"
    operator: "equals"
    value: 0
  remediation: "Associate the route table with at least one TGW attachment, or delete if unused."
  description: "A Transit Gateway route table exists with no attachments associated — likely orphaned, increasing blast radius confusion."

- id: NET-002
  title: "VPC route table routes 0.0.0.0/0 through TGW without egress filtering"
  severity: high
  resource_types: ["aws_route_table"]
  framework_ids: ["CIS-5.1", "NIST-SC-7", "SOC2-CC6.6"]
  condition:
    attribute: "default_route_target"
    operator: "contains"
    value: "tgw-"
  remediation: "Route default egress through a NAT Gateway + VPC endpoint, or insert an inspection VPC (GWLB)."
  description: "Default route to TGW bypasses any VPC-level egress filtering."
```

The engine's `_evaluate_rule` at `engine.py` lines 37-87 processes any `resource_types` list without modification.

### Pattern 4: Empty-state CTA when no `--flowmap` (D-08)

**What:** Viewer defensively reads `graph.network_paths` and `graph.dc_sites`. Both empty → show CTA panel inside the FlowMap tab. Mirrors the pattern already used in `DetailPanel.tsx` (`FindingsTab` at line 192: empty `node.findings` → dedicated empty state with icon + message).

**Example (based on verified DetailPanel.tsx lines 196-203):**
```tsx
// FlowMapEmptyState.tsx
export function FlowMapEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-8 text-center">
      <Network size={48} color="#64748B" />
      <div className="text-base font-semibold mt-4" style={{ color: '#e2e8f0' }}>
        No network topology collected
      </div>
      <div className="text-xs mt-2 max-w-md" style={{ color: '#94a3b8' }}>
        Re-run with <code className="bg-slate-800 px-1 py-0.5 rounded font-mono text-[11px]">
          infracanvas scan ./terraform --flowmap
        </code> to collect AWS TGW + Azure vWAN topology.
      </div>
      <div className="text-[10px] mt-3" style={{ color: '#4a5568' }}>
        FlowMap is in beta — free during preview.
      </div>
    </div>
  );
}
```

### Pattern 5: elkjs layered layout for left-to-right path flow (Claude's discretion — D-07)

**What:** elkjs (`elk.algorithm: 'layered'` + `elk.direction: 'RIGHT'`) converts a node+edge graph into positioned coordinates for ReactFlow. Asynchronous (`layout()` returns a Promise).

**Example (following [React Flow's elkjs example](https://reactflow.dev/examples/layout/elkjs) pattern):**

```typescript
// viewer/src/components/flowmap/lib/elkLayout.ts
import ELK from 'elkjs/lib/elk.bundled.js';
import type { Node, Edge } from '@xyflow/react';

const elk = new ELK();

const layoutOptions = {
  'elk.algorithm': 'layered',
  'elk.direction': 'RIGHT',
  'elk.spacing.nodeNode': '60',
  'elk.layered.spacing.nodeNodeBetweenLayers': '120',
  'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
};

export async function layoutFlowMap(nodes: Node[], edges: Edge[]): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const graph = {
    id: 'root',
    layoutOptions,
    children: nodes.map(n => ({ id: n.id, width: (n.style?.width as number) ?? 160, height: (n.style?.height as number) ?? 80 })),
    edges: edges.map(e => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };
  const out = await elk.layout(graph);
  const positioned = nodes.map(n => {
    const laid = out.children?.find(c => c.id === n.id);
    return laid ? { ...n, position: { x: laid.x ?? 0, y: laid.y ?? 0 } } : n;
  });
  return { nodes: positioned, edges };
}
```

### Pattern 6: Dual-color path edge (Claude's discretion — D-07)

**What:** Custom ReactFlow Edge component renders two SVG `<path>` elements at small y-offset — blue forward + orange return. Based on React Flow's `BiDirectionalEdge` pattern [CITED: reactflow.dev/examples/edges/custom-edges].

**Example:**
```tsx
// viewer/src/components/flowmap/edges/PathEdge.tsx
import { BaseEdge, getSmoothStepPath, type EdgeProps } from '@xyflow/react';

export function PathEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const [forwardPath] = getSmoothStepPath({ sourceX, sourceY: sourceY - 3, targetX, targetY: targetY - 3 });
  const [returnPath] = getSmoothStepPath({ sourceX, sourceY: sourceY + 3, targetX, targetY: targetY + 3 });
  const isDivergence = (data as { isDivergence?: boolean })?.isDivergence ?? false;

  return (
    <>
      <BaseEdge id={`${id}-fwd`} path={forwardPath} style={{ stroke: '#3B82F6', strokeWidth: 2 }} />
      <BaseEdge id={`${id}-ret`} path={returnPath} style={{ stroke: '#F97316', strokeWidth: 2 }} />
      {isDivergence && <DivergenceMarker x={(sourceX + targetX) / 2} y={(sourceY + targetY) / 2} />}
    </>
  );
}
```

### Anti-Patterns to Avoid

- **Don't invent a new CLI subcommand.** D-04 locks the UX — flag on existing `scan`. Users should not memorize `infracanvas flowmap` + `infracanvas scan`.
- **Don't hard-fail on missing creds.** D-05 + Phase 2 D-02 + verified precedent in `shadow/detector.py` line 56-57 and `main.py` line 128. Yellow warn + continue.
- **Don't bump schema to 3.0 for additive fields.** D-09 — v2.0 → v2.1 is additive. Breaking change would require migration code for existing HTML reports.
- **Don't populate `network_paths` / `dc_sites` in 3a.** D-10 — models land empty so viewer renders from real shapes immediately; 3b fills them. Don't fake data.
- **Don't modify `security/engine.py`.** D-12 + verified generic engine. If a NET-* rule needs a new operator, that's a scope decision for the planner — but the default is: add YAML, write no Python.
- **Don't apply dagre tier layout to FlowMap.** D-07. Dagre's tier assumption (Internet/Public/Private/Data) doesn't map to path flow.
- **Don't hide the FlowMap tab when empty.** D-08. Visible + CTA is the UX; hiding creates mystery.
- **Don't fetch flow-log contents in 3a.** Full VPC/NSG flow-log ingestion is expensive and only meaningful with path data. Ship metadata-only in 3a (which logs exist, where they go); the ingestion path lives in 3b next to PTH-03 NetFlow correlation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AWS API client + retry + auth | Custom `urllib` with SigV4 | **boto3** | Existing Phase 2 precedent (`shadow/detector.py`). SigV4, retry, auto-paginators, cred chain all solved. |
| Azure API client + auth | Raw `requests` against ARM REST | **azure-mgmt-network + azure-identity** | `ARM_*` env-var chain, retries, LRO handling, typed models all built-in. |
| Layered left-to-right layout | Hand-coded node positioning | **elkjs** with `layered` + `RIGHT` | Official React Flow example; hierarchical layout is a solved problem with 10+ years of research behind ELK. |
| Bidirectional dual-color edges | Custom SVG overlay component | **Custom `Edge` component with two `<BaseEdge>`** | Preserves React Flow selection, markers, z-index semantics. See `BiDirectionalEdge` in React Flow custom edges example. |
| Rule engine for NET-* findings | New Python evaluator | **Existing `security/engine.py`** | Verified generic; D-12. Zero engine code changes required. |
| Shadow-style opt-in flag | New `--network` / `--net` / `--topology` flag | **Mirror `--shadow` → `--flowmap`** | D-04; users already know `--shadow` pattern. |
| AWS response mocking | Hand-typed fake boto3 clients | **moto** for VPC/NACL/SG + **placebo** for TGW/DX | moto is the industry standard for in-process AWS mocking; placebo handles gaps where moto lags real-API shapes. |
| TypeScript type mirrors of Pydantic | Hand-maintained parallel types | **Hand-maintain with strict convention** — but lock PR review to reject drift. `viewer/src/types.ts` is the current pattern. Auto-generation (pydantic-to-typescript) is a Phase 4 improvement. |

**Key insight:** The Phase 2 codebase has already solved every piece of plumbing Phase 3a needs — cloud opt-in, creds chain, yellow-warn, generic rule engine, HTML injection, Zustand + filter panel + detail panel patterns. Phase 3a's novel work is narrow: (1) boto3/Azure API call mechanics, (2) left-to-right layout, (3) dual-color edges. Everything else is pattern mirroring.

---

## Runtime State Inventory

Phase 3a is a **pure additive feature phase**. It introduces new code paths and new data fields — it does not rename, refactor, or migrate any existing runtime state. The schema bump v2.0 → v2.1 is **additive** per D-09: existing HTML reports continue to render (new fields default to empty arrays in the Pydantic model).

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — verified by grepping for persistent stores. InfraCanvas is stateless per-scan. No database, no cache, no user_ids. | None |
| Live service config | None — 3a deploys no new services. No Railway/Fly.io/Neon/Clerk changes (Phase 4). | None |
| OS-registered state | None — no Task Scheduler, launchd, systemd, cron registration. CLI is invoked on demand. | None |
| Secrets/env vars | **New vars read but not renamed:** `ARM_*` env vars already established in Phase 2 D-07. No new vars introduced for AWS (uses existing boto3 chain). No existing var is renamed. | None — consuming code only |
| Build artifacts | **Potential egg-info staleness** after pyproject.toml `[project.optional-dependencies]` gains `flowmap` key. Requires `pip install -e '.[flowmap]'` rerun after pyproject edit — a normal dev-flow artifact, not a migration concern. | Document in Phase 3a README / plan verification: "after pyproject.toml change, reinstall dev env" |

**Canonical question:** After every file in the repo is updated, what runtime systems still have old state? **Answer:** None. No renames in 3a.

---

## Common Pitfalls

### Pitfall 1: boto3 TGW API surface has multiple paginator endpoints with subtle filter semantics
**What goes wrong:** `describe_transit_gateway_route_tables` returns TGW route tables but **not their routes**. Routes are fetched via `search_transit_gateway_routes` (requires a state filter) [VERIFIED: boto3 docs]. Many first-time implementations miss this and return empty routes.
**Why it happens:** AWS split the route-table metadata API from the route-content API because routes can number in the thousands.
**How to avoid:** Always use the pair: `describe_transit_gateway_route_tables` → for each RT, `search_transit_gateway_routes(TransitGatewayRouteTableId=..., Filters=[{"Name":"state","Values":["active","blackhole"]}])`. Propagations and associations are separate again: `get_transit_gateway_route_table_propagations`, `get_transit_gateway_route_table_associations`.
**Warning signs:** Tests pass with empty routes; live scans return TGWs with no hops. [VERIFIED: boto3 docs listing 5 distinct TGW route APIs]

### Pitfall 2: `describe_transit_gateway_attachments` status does not always reflect true association state
**What goes wrong:** The attachment `State` field can report `available` while the route table association is still `associating` or stale. [CITED: boto3 GitHub issue #3331]
**Why it happens:** Eventual consistency in the AWS control plane between attachment state and route-table state.
**How to avoid:** Cross-reference attachment state with `get_transit_gateway_route_table_associations` before asserting a hop exists in the graph.
**Warning signs:** Intermittent test flakes; scans occasionally report attachments that resolve to dead paths.

### Pitfall 3: Azure `begin_get_effective_network_security_group_rules` is per-NIC, not per-NSG
**What goes wrong:** Developers call `network_security_groups.list` and assume the rules returned are "effective." They're not — they're the defined rules, which may be overridden by subnet-level NSGs or Azure platform rules. [CITED: learn.microsoft.com Effective Security Rules docs]
**Why it happens:** Azure's defined-vs-effective NSG model is a common source of confusion. Effective rules require an LRO per NIC.
**How to avoid:** For NSG findings that claim "will block this traffic," iterate network interfaces and call `network_interfaces.begin_get_effective_network_security_group_rules(nic_name).result()`. Cache results per NIC — this is an expensive call. **In 3a, defined-rules are sufficient** for path-independent findings (e.g., "NSG not attached to subnet"); effective-rules analysis is path-dependent and defers to 3b.

### Pitfall 4: Azure `begin_*` methods return LROPoller, not the result directly
**What goes wrong:** Code calls `client.virtual_hubs.begin_get_effective_virtual_hub_routes(...)` and tries to iterate the return value. That's a poller, not a list. [CITED: learn.microsoft.com azure-sdk-python docs]
**Why it happens:** Azure SDK uses long-running operations (LROs) for any query that requires server-side evaluation.
**How to avoid:** Always `.result()` on `begin_*` methods. For progress reporting in long scans, use `poller.status()` in a loop.
**Warning signs:** Type errors in tests; empty route lists that shouldn't be empty.

### Pitfall 5: moto's TGW coverage lags real boto3 API
**What goes wrong:** Tests that mock via `@mock_aws` fail on newer TGW operations (e.g., route propagations API subtleties) because moto hasn't implemented them yet. [ASSUMED — based on general moto behavior with newer EC2 APIs]
**Why it happens:** moto is community-maintained; newer AWS APIs trail real AWS by weeks to months.
**How to avoid:** Use a **hybrid fixture strategy**: moto for stable, well-covered shapes (VPCs, NACLs, security groups, standard RTs); placebo-recorded JSON for TGW + Direct Connect + vWAN response shapes. Check in the placebo recordings under `tests/fixtures/flowmap/aws/*/`. Sanitize account IDs, ARNs, IPs before commit.
**Warning signs:** Tests pass locally with live creds but fail in CI with `NotImplementedError` or `MockNotImplementedError`.

### Pitfall 6: ReactFlow custom edges + elkjs async layout causes flash-of-unpositioned-nodes
**What goes wrong:** elkjs `layout()` is async; ReactFlow renders nodes immediately. First paint shows nodes at `{x:0, y:0}` stacked on top of each other, then repositioned after ~50-200ms.
**Why it happens:** elkjs runs JS algorithm synchronously but returns a Promise; ReactFlow's default behavior is to paint on state change.
**How to avoid:** Apply a loading state — e.g., `const [laidOut, setLaidOut] = useState(false);` render `<Loader />` until `layoutFlowMap(...)` resolves, then `setLaidOut(true)`. Or pre-compute layout in a `useMemo` with Suspense. The Phase 2 `DiagramCanvas.tsx` uses synchronous dagre — this pitfall is **new** to FlowMap.
**Warning signs:** Visible node jitter on tab switch; Vitest snapshots capture pre-layout state.

### Pitfall 7: Pydantic `model_dump_json` includes default empty arrays — verify viewer handles the "key exists with [] value" case
**What goes wrong:** `ResourceGraph(network_paths=[], dc_sites=[]).model_dump_json()` produces `{"network_paths":[], "dc_sites":[], ...}`. The viewer's defensive read needs to treat `[]` as empty — not just `undefined`. [VERIFIED: Pydantic v2 default behavior]
**Why it happens:** Pydantic v2 serializes default values by default (unlike `exclude_defaults=True`).
**How to avoid:** In `store.ts` / `App.tsx`, check `graph.network_paths && graph.network_paths.length > 0` — not just `if (graph.network_paths)`. This is a common JS gotcha where `[]` is truthy.
**Warning signs:** Empty-state CTA never renders even though no data was collected.

### Pitfall 8: Single HTML file size risk — 3a adds schema fields but few bytes; watch bundle size
**What goes wrong:** Adding elkjs (~150KB min+gzip) + new node/edge/panel components increases the single-file HTML payload. Project constraint from CLAUDE.md: "HTML < 5MB."
**Why it happens:** Vite bundles everything into one file via `vite-plugin-singlefile` — every new import ships.
**How to avoid:** Run `npm run build` after integration, measure `dist/index.html` size, target < 3MB pre-data-injection. elkjs has a tree-shakeable build at `elkjs/lib/elk.bundled.js` (the smaller bundle). Verify imports use it.
**Warning signs:** Build output > 4MB; vite warns about chunk size.

---

## Code Examples

Verified patterns from the existing codebase and official SDK docs:

### AWS TGW route table collection (boto3 paginator pattern)

```python
# cli/infracanvas/flowmap/aws.py
import boto3
from infracanvas.graph.models import ResourceGraph, ResourceNode

class AwsNetworkCollector:
    def __init__(self, region: str) -> None:
        self._region = region

    def collect(self, graph: ResourceGraph) -> ResourceGraph:
        try:
            import boto3  # noqa: PLC0415
        except ImportError:
            raise RuntimeError("boto3 not installed. Install with: pip install 'infracanvas[flowmap]'")
        session = boto3.Session()
        if not session.get_credentials():
            raise RuntimeError("--flowmap requires AWS credentials.")

        ec2 = session.client("ec2", region_name=self._region)

        # TGW route tables (paginated)
        paginator = ec2.get_paginator("describe_transit_gateway_route_tables")
        for page in paginator.paginate():
            for rt in page.get("TransitGatewayRouteTables", []):
                # Routes require a separate call with a state filter
                routes_resp = ec2.search_transit_gateway_routes(
                    TransitGatewayRouteTableId=rt["TransitGatewayRouteTableId"],
                    Filters=[{"Name": "state", "Values": ["active", "blackhole"]}],
                    MaxResults=1000,
                )
                rt_node = ResourceNode(
                    id=f"aws_ec2_transit_gateway_route_table.{rt['TransitGatewayRouteTableId']}",
                    type="aws_ec2_transit_gateway_route_table",
                    name=rt["TransitGatewayRouteTableId"],
                    provider="aws",
                    region=self._region,
                    attributes={
                        "state": rt["State"],
                        "default_association_route_table": rt.get("DefaultAssociationRouteTable", False),
                        "default_propagation_route_table": rt.get("DefaultPropagationRouteTable", False),
                        "routes": routes_resp.get("Routes", []),
                    },
                )
                graph.nodes.append(rt_node)
        # ... repeat for VPCs, NACLs, Direct Connect …
        return graph
```
Source: boto3 paginator pattern per `describe_transit_gateway_route_tables` and `search_transit_gateway_routes` official docs [CITED: boto3.amazonaws.com/.../describe_transit_gateway_route_tables.html].

### Azure vWAN + effective rules collection

```python
# cli/infracanvas/flowmap/azure.py
import os
from infracanvas.graph.models import ResourceGraph, ResourceNode

class AzureNetworkCollector:
    def __init__(self, subscription_id: str) -> None:
        self._subscription_id = subscription_id

    def collect(self, graph: ResourceGraph) -> ResourceGraph:
        try:
            from azure.identity import ClientSecretCredential, DefaultAzureCredential  # noqa: PLC0415
            from azure.mgmt.network import NetworkManagementClient  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                "azure-mgmt-network not installed. Install with: pip install 'infracanvas[flowmap]'"
            )

        if os.environ.get("ARM_CLIENT_SECRET"):
            cred = ClientSecretCredential(
                tenant_id=os.environ["ARM_TENANT_ID"],
                client_id=os.environ["ARM_CLIENT_ID"],
                client_secret=os.environ["ARM_CLIENT_SECRET"],
            )
        else:
            cred = DefaultAzureCredential()

        net = NetworkManagementClient(cred, self._subscription_id)

        # vWAN hubs
        for vwan in net.virtual_wans.list():
            graph.nodes.append(ResourceNode(
                id=f"azurerm_virtual_wan.{vwan.name}",
                type="azurerm_virtual_wan",
                name=vwan.name,
                provider="azurerm",
                attributes={"allow_branch_to_branch_traffic": vwan.allow_branch_to_branch_traffic},
            ))

        for hub in net.virtual_hubs.list():
            # Effective routes (LRO)
            poller = net.virtual_hubs.begin_get_effective_virtual_hub_routes(
                resource_group_name=_rg_from_id(hub.id),
                virtual_hub_name=hub.name,
            )
            # poller.result() returns the full routes list
            graph.nodes.append(ResourceNode(
                id=f"azurerm_virtual_hub.{hub.name}",
                type="azurerm_virtual_hub",
                name=hub.name,
                provider="azurerm",
                attributes={
                    "address_prefix": hub.address_prefix,
                    "sku": hub.sku,
                    "effective_routes": poller.result().value if poller else [],
                },
            ))
        return graph
```
Source: azure-mgmt-network Python SDK 30.2.0 API per Microsoft Learn docs [CITED: learn.microsoft.com/en-us/python/api/overview/azure/network].

### Zustand store extension for FlowMap tab

```typescript
// viewer/src/store.ts — additive extension (NOT a rewrite)
import type { NetworkPath, DCSite } from './types';

interface FlowMapFilters {
  severities: Severity[];
  clouds: ('aws' | 'azure')[];          // filter by cloud provider
  hopTypes: ('router' | 'firewall' | 'vpc' | 'hub')[];
}

interface StoreState {
  // existing fields unchanged …
  activeTab: 'canvas' | 'flowmap';
  flowMapFilters: FlowMapFilters;
  selectedPath: NetworkPath | null;
  setActiveTab: (tab: 'canvas' | 'flowmap') => void;
  setSelectedPath: (path: NetworkPath | null) => void;
  toggleCloudFilter: (cloud: 'aws' | 'azure') => void;
  toggleHopTypeFilter: (t: FlowMapFilters['hopTypes'][number]) => void;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-coded hierarchical layout algorithms | elkjs (ported ELK from Eclipse) | ELK 0.8+ (2023); elkjs 0.9+ (2024) | Official React Flow recommendation for layered diagrams [CITED: reactflow.dev/examples/layout/elkjs] |
| Boto3 manual pagination | `get_paginator().paginate()` | boto3 1.28+ (stable for years) | Avoids NextToken threading; 3a should use paginators everywhere |
| Azure SDK track-1 (`azure.mgmt.network.NetworkManagementClient` with subclient groups) | Track-2 SDK (same class, LRO + async, typed models) | azure-mgmt-network 19+ (2023) | All code samples should use track-2; track-1 docs on the internet are misleading |
| React Flow 11.x `reactflow` package | `@xyflow/react` 12.x (current) | Nov 2024 [CITED: xyflow.com blog react-flow-12-release] | Phase 2 already on 12.6.0 — correct. Custom edges API is stable. |
| `moto` v4 (decorators `@mock_ec2`) | `moto` v5 (single `@mock_aws`) | moto 5.0, Feb 2024 | 3a tests should use the v5 `@mock_aws` decorator; 5.1.22 is latest |

**Deprecated/outdated (do NOT use):**
- React Flow's old `reactflow` npm package (use `@xyflow/react` — already correct in repo)
- `boto3.Session().resource(...)` for EC2 — use `client()` instead; resource API is deprecated for network operations
- Azure "classic" SDK (pre-2020 `azure.mgmt.*` with different package shapes) — we're on track-2 throughout
- `az login` CLI-based auth in Python SDK contexts — Phase 2 D-07 locks us to env vars
- moto v4 per-service decorators (`@mock_ec2`) — use `@mock_aws` unified decorator

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.12+ | CLI runtime | ✓ | per pyproject.toml `requires-python = ">=3.12"` | — |
| `boto3` | AWS network collection | ✗ (not in current `.venv`) | 1.42.91 latest | Install via `pip install 'infracanvas[flowmap]'`. Without it, `--flowmap` with AWS resources prints yellow warning + skips. |
| `azure-identity` | Azure auth | ✗ (not installed) | 1.25.3 latest | Install via `pip install 'infracanvas[flowmap]'`. Without it, AZN-* collection skipped with yellow warning. |
| `azure-mgmt-network` | Azure network collection | ✗ (not installed) | 30.2.0 latest | Same install path. |
| `azure-mgmt-resource` | Resource group enumeration | ✗ (not installed) | 25.0.0 latest | Same install path. |
| `moto` | Test fixtures | ✗ (not installed) | 5.1.22 latest | Install in `[test]` extra or `dev-requirements`. CI needs it. |
| `placebo` | Test fixtures (TGW/DX/vWAN response recording) | ✗ (not installed) | 0.10.0 latest | Same install path. |
| `elkjs` | Viewer FlowMap layout | ✗ (not in `viewer/package.json`) | 0.11.1 latest | `npm install elkjs` during Phase 3a. |
| `@xyflow/react` | ReactFlow canvas | ✓ | 12.6.0 [VERIFIED: viewer/package.json line 18] | — |
| `zustand` | Viewer state | ✓ | 5.0.5 [VERIFIED: viewer/package.json line 24] | — |
| Node.js / npm | Viewer build | ✓ (presumed — Phase 1/2 shipped) | not pinned | — |
| AWS credentials | Live `--flowmap` scans against AWS | — (user-supplied at runtime) | — | Missing → yellow warn + skip AWS collection (D-05) |
| Azure credentials (`ARM_*`) | Live `--flowmap` scans against Azure | — (user-supplied) | — | Missing → yellow warn + skip Azure collection (D-05) |

**Missing dependencies with no fallback (block execution of `--flowmap`):**
- None at the Python level — every missing SDK is gated on the flag and warns gracefully.
- **elkjs is blocking for the viewer build** — without it, FlowMapCanvas won't compile. The planner must include `npm install elkjs` in the first viewer plan.

**Missing dependencies with fallback:**
- boto3 / azure-* SDKs → feature-gated; plain `scan` (without `--flowmap`) works fine without any of them. This is the `[project.optional-dependencies] flowmap` extra pattern.

---

## Validation Architecture

**Nyquist validation is enabled** (`.planning/config.json` → `workflow.nyquist_validation: true` verified 2026-04-18).

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest (configured in `cli/pyproject.toml` line 53-55) |
| Framework (TypeScript) | Vitest 4.1.4 |
| Config file (Python) | `cli/pyproject.toml` `[tool.pytest.ini_options]` |
| Config file (TS) | `viewer/vite.config.ts` (inline `test:` block, verified in `.planning/codebase/TESTING.md` line 301-307) |
| Quick run command (Python) | `cd cli && pytest tests/test_flowmap_*.py -x -q` |
| Quick run command (TS) | `cd viewer && npx vitest run src/__tests__/flowmap/` |
| Full suite command (Python) | `cd cli && pytest` |
| Full suite command (TS) | `cd viewer && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FDM-01 | Pydantic models (NetworkPath, PathHop, DCCollectorReading, NetworkFinding, DCSite) instantiate with defaults and validate | unit | `pytest cli/tests/test_flowmap_models.py -x` | ❌ Wave 0 |
| FDM-02 | `ResourceGraph.version` bumps to "2.1"; `network_paths` + `dc_sites` default to `[]`; JSON round-trip preserves shape | unit | `pytest cli/tests/test_flowmap_models.py::TestSchemaBump -x` | ❌ Wave 0 |
| FDM-02 (viewer side) | `ResourceGraph` TS type has optional `networkPaths` / `dcSites`; empty-array read doesn't crash `App.tsx` | unit | `npx vitest run viewer/src/__tests__/flowmap/types.test.ts` | ❌ Wave 0 |
| FDM-03 | NET-* YAML files load via existing `load_rules()` and evaluate against fixture ResourceGraph | unit + integration | `pytest cli/tests/test_flowmap_network_rules.py -x` | ❌ Wave 0 |
| AWS-01 | TGW route tables + attachments + VPN connections collected from boto3 mock → graph nodes with correct type + attributes | integration (moto + placebo) | `pytest cli/tests/test_flowmap_aws.py::TestTGW -x` | ❌ Wave 0 |
| AWS-02 | VPC RT + NACLs + Direct Connect VI collected from moto → graph nodes | integration (moto) | `pytest cli/tests/test_flowmap_aws.py::TestVPC -x` | ❌ Wave 0 |
| AWS-03 | Flow-log metadata (which flow logs exist, destination) collected; full log content NOT ingested in 3a | integration (moto) | `pytest cli/tests/test_flowmap_aws.py::TestFlowLogs -x` | ❌ Wave 0 |
| AZN-01 | vWAN + VirtualHubs + HubVirtualNetworkConnections + effective hub routes collected | integration (placebo-recorded responses) | `pytest cli/tests/test_flowmap_azure.py::TestVWAN -x` | ❌ Wave 0 |
| AZN-02 | vNet peerings + NSG (defined rules — effective rules defer to 3b) collected per resource group | integration (placebo) | `pytest cli/tests/test_flowmap_azure.py::TestVNet -x` | ❌ Wave 0 |
| AZN-03 | ExpressRoute circuits + NSG flow-log metadata collected | integration (placebo) | `pytest cli/tests/test_flowmap_azure.py::TestExpressRoute -x` | ❌ Wave 0 |
| FMV-01 | FlowMapCanvas renders with 0 paths → shows topology nodes only (no dual-color edges) | unit (Vitest + @testing-library/react) | `npx vitest run viewer/src/__tests__/flowmap/FlowMapCanvas.test.tsx` | ❌ Wave 0 |
| FMV-01 (layout) | elkjs layout produces deterministic node positions for a fixture graph (2 clouds, 5 hops) | unit | `npx vitest run viewer/src/__tests__/flowmap/elkLayout.test.ts` | ❌ Wave 0 |
| FMV-02 | Divergence marker CSS class + component renders (data-driven; in 3a renders only when `isDivergence=true` explicitly passed — real data in 3b) | unit | `npx vitest run viewer/src/__tests__/flowmap/PathEdge.test.tsx` | ❌ Wave 0 |
| FMV-03 | DCSiteGroup + RouterNode + FirewallNode + CloudHubNode components render without crash given empty props | unit | `npx vitest run viewer/src/__tests__/flowmap/nodes.test.tsx` | ❌ Wave 0 |
| FMV-04 | FirewallNode capacity gauge renders 0/50/100% states; capacity data comes from `DCCollectorReading.firewall_utilization` | unit | `npx vitest run viewer/src/__tests__/flowmap/FirewallNode.test.tsx` | ❌ Wave 0 |
| FMV-05 | FlowMapFilterPanel + PathDetailPanel render, respond to Zustand store changes | unit | `npx vitest run viewer/src/__tests__/flowmap/panels.test.tsx` | ❌ Wave 0 |
| NFN-01 (partial) | Cloud-only NET-* rules evaluate against fixture graph → expected finding count + severities | integration | `pytest cli/tests/test_flowmap_network_rules.py::TestNetworkRuleEvaluation -x` | ❌ Wave 0 |
| D-04 (CLI flag) | `infracanvas scan ./fixture --flowmap` runs end-to-end → ResourceGraph with network nodes + findings + HTML export | e2e (mocked cloud) | `pytest cli/tests/test_flowmap_integration.py::test_scan_flowmap_e2e -x` | ❌ Wave 0 |
| D-05 (missing creds) | `--flowmap` without creds prints yellow warning, exits 0, produces HTML with empty topology | integration | `pytest cli/tests/test_flowmap_integration.py::test_flowmap_no_creds_warns -x` | ❌ Wave 0 |
| D-06 (viewer tab) | `activeTab` toggle switches between DiagramCanvas and FlowMapCanvas; Zustand state persists selection | unit | `npx vitest run viewer/src/__tests__/flowmap/tabBar.test.tsx` | ❌ Wave 0 |
| D-08 (empty state) | `scan` without `--flowmap` → viewer FlowMap tab shows empty-state CTA with re-run instruction | unit | `npx vitest run viewer/src/__tests__/flowmap/FlowMapEmptyState.test.tsx` | ❌ Wave 0 |
| D-09 (schema bump) | JSON output of existing Phase-2 scan opens in Phase-3 viewer without errors (backwards-compat) | integration (golden file) | `pytest cli/tests/test_flowmap_integration.py::test_phase2_report_still_opens -x` | ❌ Wave 0 |
| D-12 (rule engine unchanged) | NET-* rules evaluate through `evaluate_all()` without passing a `policy_rules` arg (they load from `rules/network/` like `rules/aws/` does) | unit | `pytest cli/tests/test_flowmap_network_rules.py::test_engine_auto_loads_network_dir -x` | ❌ Wave 0 |

### Sample/fixture scale needed

**AWS TGW + Azure vWAN end-to-end fixture target:**
- **1 TGW** with 3 route tables (default assoc, default prop, custom)
- **3 VPCs** attached to TGW (us-east-1), each with 2 subnets + 2 route tables + 1 NACL
- **1 Direct Connect** connection with 2 virtual interfaces (private + transit)
- **2 VPC flow logs** pointing to S3 + CloudWatch Logs (metadata only)
- **1 Azure vWAN** with 2 virtual hubs
- **3 vNets** in one subscription across 2 resource groups, 4 peering relationships forming a partial mesh
- **2 NSGs** — one attached to subnet, one to NIC
- **1 ExpressRoute** circuit with 2 peerings (Azure private + Microsoft)
- **1 NSG flow log** (metadata only)

This scale exercises: (1) paginator correctness in boto3, (2) LRO handling in Azure SDK, (3) empty-result resilience (one fixture deliberately has no TGW attachments), (4) the elkjs layout with ~25 topology nodes and ~40 edges (all cloud-internal — no paths in 3a), (5) NET-* rule evaluation with at least 8 rules firing and 3 rules not firing.

### Viewer tab switching + empty-state fallback validation

- **Tab switch test** (`tabBar.test.tsx`): Render `<App />` with mock `graph` in Zustand. Initial state `activeTab === 'canvas'` → assert `DiagramCanvas` in DOM, `FlowMapCanvas` not. Call `setActiveTab('flowmap')` → assert reverse. Click on the tab UI element → assert Zustand state updated.
- **Empty-state fallback test** (`FlowMapEmptyState.test.tsx`): Render `FlowMapCanvas` with `graph = { ...base, network_paths: [], dc_sites: [] }`. Assert the CTA text "Re-run with `infracanvas scan ./terraform --flowmap`" is visible. Assert topology nodes (if any collected by a cloud resource scan) still render, only paths are absent.
- **Backward-compat test** (`test_phase2_report_still_opens`): Load a committed Phase 2 JSON report (`.planning/phases/02-canvas-v1-0/` artifacts — use Phase 2 fixture JSON if available, else a synthetic v2.0 report). `ResourceGraph.model_validate(...)` should succeed without errors; `network_paths` / `dc_sites` default to `[]`.

### Wave 0 Gaps (test files that must be created before implementation)

- [ ] `cli/tests/test_flowmap_models.py` — covers FDM-01, FDM-02 (Pydantic schema)
- [ ] `cli/tests/test_flowmap_aws.py` — covers AWS-01, AWS-02, AWS-03
- [ ] `cli/tests/test_flowmap_azure.py` — covers AZN-01, AZN-02, AZN-03
- [ ] `cli/tests/test_flowmap_network_rules.py` — covers FDM-03, NFN-01 (cloud-only subset), D-12
- [ ] `cli/tests/test_flowmap_integration.py` — covers D-04, D-05, D-09
- [ ] `cli/tests/fixtures/flowmap/aws/` and `cli/tests/fixtures/flowmap/azure/` — recorded fixtures (see fixture scale above)
- [ ] `cli/tests/conftest.py` — shared fixtures: `flowmap_aws_session`, `flowmap_azure_client`, `empty_resource_graph`, `populated_network_graph`
- [ ] `viewer/src/__tests__/flowmap/` — new directory with one test file per component listed in the Phase Requirements → Test Map
- [ ] Framework install: `pip install 'infracanvas[flowmap,test]'` + `npm install elkjs` (both must be first steps in Wave 0 / Plan 1)

*No existing test infrastructure covers FlowMap — all tests are new.*

---

## Project Constraints (from CLAUDE.md)

Extracted directives the planner MUST honor:

- **Solo founder, minimize ops complexity:** No separate infrastructure to maintain in 3a. ✓ (3a is CLI-only + static HTML; no services.)
- **Cost budget $10–104/mo until revenue:** No new paid services introduced by 3a. ✓
- **CLI stack: Python 3.12+, pip-installable + PyInstaller standalone binary:** 3a respects this — all additions are pip-installable Python. ✓
- **Frontend stack: ES2020+ modern browsers only:** elkjs 0.11.1 compiles to ES2020 [ASSUMED — verify at bundle time]. ✓
- **Performance: Parse 500 resources < 10s, FlowMap topology < 20s, HTML < 5MB:** 3a must profile collector runtime on a realistic fixture. elkjs layout on 50 nodes should complete < 500ms [ASSUMED based on ELK benchmarks]. Bundle size: elkjs is ~150KB gzipped — well within headroom.
- **Security: No cloud credentials stored. CLI scans are local-only:** ✓ (credentials read from env-var chain, used in-memory only, never persisted).
- **DC agent constraint:** `"Go, single binary, cross-compiled Linux amd64 + macOS arm64"` / `"DC agent read-only, outbound-only"` — **not relevant to 3a** (DC Agent is 3b). The `DCCollectorReading` Pydantic model in 3a only defines the schema the 3b agent will push into.
- **GSD workflow enforcement:** All edits go through GSD commands. ✓ (this phase is `/gsd-plan-phase` driven.)

---

## Security Domain

`security_enforcement` is the default (not explicitly disabled in config). Applicable ASVS categories for 3a:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes (consumes cloud creds) | boto3 default cred chain; `ClientSecretCredential` from azure-identity with `ARM_*` env vars. No secrets written to disk, no tokens cached by InfraCanvas. |
| V3 Session Management | no (stateless per-scan) | — |
| V4 Access Control | yes (cloud IAM for read-only scans) | Document minimum IAM policy — e.g., `ec2:Describe*`, `directconnect:Describe*`, `logs:DescribeLogGroups`; Azure `Network Reader` built-in role. No write permissions ever requested. |
| V5 Input Validation | yes (boto3/Azure SDK responses become Pydantic models → user-visible) | Pydantic v2 validates shape on `model_validate`; use strict types (no `dict[str, Any]` in public schema). `search_transit_gateway_routes` responses may include arbitrary user-tag values — treat as untrusted for rendering (no HTML injection via attribute values — viewer uses React which auto-escapes). |
| V6 Cryptography | no (no crypto operations in 3a) | — all TLS is SDK-managed. |
| V7 Error Handling & Logging | yes | Follow Phase 2 pattern: errors → Rich console, no sensitive values in logs. Never log credentials, ARNs with account IDs untruncated, or NSG rule details containing IPs of private resources. For placebo fixtures: **sanitize before commit**. |
| V9 Communications | yes | boto3 + azure SDK both enforce TLS 1.2+ by default [ASSUMED — verify SDK defaults]. No custom HTTP clients. |
| V10 Malicious Code | no (no untrusted code execution in 3a) | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Leaked credentials via error messages | Information disclosure | Catch `botocore.exceptions.ClientError` specifically; strip account IDs from messages before displaying; yellow warn pattern from Phase 2. |
| Privilege escalation via over-broad IAM policy | Elevation of privilege | Document minimum-read-only IAM in README + `scripts/aws_iam_policy.json`. Audit: only `Describe*`, `List*`, `Get*` calls — never `Create*`/`Modify*`/`Delete*`. |
| Untrusted resource tags rendered in viewer (XSS risk) | Tampering | React auto-escapes when values are rendered as children via `{value}` JSX syntax. Do not route tag values through any raw-HTML rendering path. Phase 2 already follows this. |
| HTTP response smuggling through proxy | Tampering | boto3 + azure-identity enforce HTTPS by default. |
| Committing real AWS account IDs / ARNs in test fixtures | Information disclosure | Sanitization script before `placebo` fixtures are committed; `scripts/sanitize_fixture.py` replaces account IDs with `123456789012` and IP ranges with RFC-5737 test nets. Add to the Wave 0 plan. |
| Azure subscription ID leakage in fixtures | Information disclosure | Same as above — replace with `00000000-0000-0000-0000-000000000000`. |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | moto 5.1.22 has incomplete coverage for newer TGW APIs (propagations, search_transit_gateway_routes) | Common Pitfalls → Pitfall 5; Supporting libs | Low — fallback is placebo-recorded fixtures; worst case planner shifts more fixtures to placebo. No blocking issue. |
| A2 | elkjs layered layout performs acceptably at ~50 topology nodes + ~80 edges (< 500ms) | Project Constraints | Medium — if slow, may need WASM variant or fallback to simpler fixed-rank. Verify in Wave 0 perf test. |
| A3 | boto3 + azure SDK both enforce TLS 1.2+ by default in current versions | Security Domain → V9 | Low — both SDKs have defaulted to TLS 1.2+ for years. Verify by inspecting SDK config docs before shipping. |
| A4 | elkjs 0.11.1 compiles cleanly to ES2020 and Vite tree-shakes `elk.bundled.js` | Project Constraints | Low — if bundle > 5MB, fall back to loading elkjs from CDN (violates single-file constraint — would require scope renegotiation). |
| A5 | Azure `begin_get_effective_network_security_group_rules` can be called per-NIC in bulk without rate limits blocking a medium scan | Pitfall 3 | Medium — if rate-limited, 3a should defer ALL effective-rules queries to 3b and use defined rules only. Measure in Wave 0. |
| A6 | Phase 2 viewer bundle has headroom for elkjs (~150KB gzipped) + ~1000 lines of new TSX | Pitfall 8 | Low — measure after integration. |
| A7 | Existing `security/engine.py` handles new `resource_types` values without any operator additions | Pattern 3 | Low — verified by reading engine.py. Risk is only if a NET-* rule needs CIDR-containment semantics not already in the 9 supported operators; planner should audit the proposed 8-12 NET-* rules against the operator list before committing. |
| A8 | `ResourceGraph.version = "2.1"` change is additive and does not break existing `export/html.py` injection | Pattern 6 → schema bump | Low — the string is informational metadata; viewer doesn't branch on version. Still, add a test for backward-compat. |

**If user-confirmation pass is run:** A2, A5, A7 are the three assumptions the planner should de-risk in Wave 0 spike-style tests before committing to the full plan structure.

---

## Open Questions

1. **How many NET-* rule IDs land in 3a vs 3b?** (D-11 explicitly defers this to planner + researcher.)
   - What we know: Rules must be path-independent to qualify for 3a. Good 3a candidates: orphaned route tables, default route to TGW without filtering, NSG 0.0.0.0/0 egress, unused DX/ExpressRoute circuit down, overlapping CIDR in route table, TGW attachment with no RT association.
   - What's unclear: Exact count — 4 per cloud (8 total)? 6 per cloud (12 total)? The CONTEXT.md says "minimum 4-6 per cloud" → recommend **6 AWS + 6 Azure = 12 NET rules in 3a**, numbered NET-001..NET-012 with NET-009..NET-012 reserved for Azure.
   - Recommendation: Planner allocates NET-001..NET-012 as 3a (6 AWS + 6 Azure path-independent); NET-013+ reserved for 3b path-dependent. Update REQUIREMENTS.md FDM-03 text to reflect split.

2. **Should 3a do any flow-log ingestion, or purely metadata?**
   - What we know: D-11 defers path-dependent rules to 3b. Flow logs are most useful for confirming paths — which is 3b work.
   - What's unclear: Whether collecting flow-log **destinations and formats** (not content) adds enough viewer value in 3a to warrant the code surface.
   - Recommendation: **Metadata only in 3a** — list flow logs, show which ones are configured, note destination. This is cheap, surfaces "flow logs disabled" as a NET-* finding, and avoids CloudWatch Logs / Azure Monitor query complexity until path work needs it.

3. **Should FlowMap render cloud resource topology when `network_paths = []`, or only when paths are present?**
   - What we know: D-08 says empty-state CTA when no `--flowmap` at all. But what if `--flowmap` ran and collected TGW/vWAN topology, but (of course) no paths since path-tracer is in 3b?
   - What's unclear: Does "FlowMap with topology only, no paths" feel useful in 3a, or does it over-promise?
   - Recommendation: **Yes — render topology without paths in 3a.** Cloud engineers can visually verify TGW+VPC+vWAN connectivity even without end-to-end paths. The dual-color edges simply don't render in 3a; hop nodes (router, firewall, DC site) show up as placeholders with "Configure DC Agent (3b)" tooltips. This matches "beta, free during preview" framing.

4. **TypeScript mirror maintenance — drift risk between Pydantic and `types.ts`?**
   - What we know: Phase 2 convention is hand-maintained (`viewer/src/types.ts` lines 1-94 mirrors `cli/infracanvas/graph/models.py` manually).
   - What's unclear: With 4+ new Pydantic models, drift likelihood goes up.
   - Recommendation: **Defer auto-generation to Phase 4.** In 3a, add a test (`test_pydantic_ts_mirror.py`) that hashes known-field names across both files — not a full schema check, but a tripwire. Or simpler: a manual PR-review checklist item.

---

## Sources

### Primary (HIGH confidence)

- **Existing codebase (verified via Read tool 2026-04-18):**
  - `cli/infracanvas/graph/models.py` (lines 1-118) — current schema to extend
  - `cli/infracanvas/security/engine.py` (lines 1-177) — generic rule engine, verified zero changes needed
  - `cli/infracanvas/shadow/detector.py` (lines 1-253) — direct precedent for `--flowmap` collector pattern
  - `cli/infracanvas/main.py` (lines 1-755) — scan command + `--shadow` flag wiring to mirror
  - `cli/infracanvas/security/rules/aws/networking.yaml` — NET-* YAML schema precedent
  - `viewer/src/store.ts`, `App.tsx`, `components/DiagramCanvas.tsx`, `FilterPanel.tsx`, `DetailPanel.tsx`, `lib/layout.ts`, `lib/colors.ts`, `types.ts` — viewer patterns to mirror
  - `cli/pyproject.toml` — dependency surface
  - `viewer/package.json` — verified `@xyflow/react` 12.6.0, zustand 5.0.5, react 18.3.1 present; elkjs absent
  - `cli/tests/test_shadow.py` — boto3 mocking test precedent (lines 1-80)
  - `.planning/phases/02-canvas-v1-0/02-CONTEXT.md` + `02-RESEARCH.md` — Phase 2 precedents carried forward

- **PyPI version verification (2026-04-18 via `pip index versions`):**
  - boto3 1.42.91 (latest); azure-identity 1.25.3; azure-mgmt-network 30.2.0; azure-mgmt-resource 25.0.0; azure-mgmt-monitor 7.0.0; moto 5.1.22; placebo 0.10.0; botocore-stubs 1.42.41

- **npm version verification (2026-04-18 via `npm view`):**
  - elkjs 0.11.1 (modified 2026-03-03)

- **Official docs (MEDIUM-HIGH — accessed via WebSearch 2026-04-18):**
  - [boto3 describe_transit_gateway_route_tables](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_transit_gateway_route_tables.html)
  - [boto3 search_transit_gateway_routes](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/search_transit_gateway_routes.html)
  - [boto3 describe_transit_gateway_attachments](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_transit_gateways.html) (paired with issue #3331 re: attachment state lag)
  - [Azure SDK for Python — Network](https://learn.microsoft.com/en-us/python/api/overview/azure/network?view=azure-python)
  - [Azure Network Interfaces Get Effective Route Table](https://learn.microsoft.com/en-us/rest/api/virtualnetwork/network-interfaces/get-effective-route-table)
  - [azure-mgmt-network PyPI](https://pypi.org/project/azure-mgmt-network/)
  - [React Flow — ELK.js example](https://reactflow.dev/examples/layout/elkjs)
  - [React Flow — Custom Edges example](https://reactflow.dev/examples/edges/custom-edges)
  - [React Flow 12 release notes](https://xyflow.com/blog/react-flow-12-release)

### Secondary (MEDIUM confidence)

- [boto3 issue #3331 — describe_transit_gateway_attachments state lag](https://github.com/boto/boto3/issues/3331) — surfaced Pitfall 2
- [Azure REST API issue #9589 — Effective Route Table misleading naming](https://github.com/Azure/azure-rest-api-specs/issues/9589) — surfaced Pitfall 3 LRO-returns-routes-not-table nuance
- [Medium article on React Flow + ELK.js mixed layouts](https://medium.com/@armanaryanpour/auto-layout-positioning-in-react-flow-using-elkjs-eclipse-layout-kernel-with-typescript-and-6389a2cc0119) — confirms layered + direction: RIGHT recipe

### Tertiary (LOW confidence, flagged)

- Assumption A1 (moto TGW coverage gap) — training-data informed; placebo fallback neutralizes risk
- Assumption A2 (elkjs perf at 50 nodes) — [ASSUMED]; Wave 0 benchmark required

---

## Metadata

**Confidence breakdown:**
- Standard stack (boto3, azure-mgmt-network, elkjs, moto, placebo): **HIGH** — versions verified against live PyPI/npm; API surface verified against official docs.
- Architecture patterns (mirror `--shadow`, mirror `FilterPanel`, reuse `engine.py`, additive schema bump): **HIGH** — every pattern read directly from existing codebase source.
- FlowMap layout + dual-color edges: **MEDIUM** — official React Flow examples exist; exact implementation details (e.g., two `<BaseEdge>` vs single custom SVG) left to planner discretion per D-07.
- NET-* rule catalogue + 3a/3b split: **MEDIUM** — the path-independent vs path-dependent split is defensible but Claude's discretion. Planner should validate with security domain knowledge.
- Common pitfalls: **HIGH** — 6 of 8 pitfalls verified via official docs, GitHub issues, or existing codebase; 2 marked [ASSUMED].
- Environment availability: **HIGH** — verified by actual `pip index versions` and `npm view` commands.
- Security (ASVS): **MEDIUM** — reasoning is sound; specific controls (e.g., exact minimum IAM policy) should be planner-verified.

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (30 days for stable SDKs; Azure SDK in particular sometimes ships breaking changes across major versions — pin carefully).

**Note on system-reminder-injected skills:** During research, two auto-suggested skills (`react-best-practices`, `vercel-services`) were injected via PreToolUse hooks. Neither had a corresponding `Skill` tool available in this agent's environment. `react-best-practices` is relevant to the viewer work but React API details are deferred to the planner/executor phase (research does not write React code). `vercel-services` is not relevant — Phase 3a has no Vercel services (D-02: all SaaS infrastructure deferred to Phase 4). These are flagged here for transparency only.

---

*Phase: 03-flowmap-v1-0*
*Research completed: 2026-04-18*
