# Architecture Patterns

**Project:** InfraCanvas
**Researched:** 2026-04-15
**Domain:** Hybrid Cloud Infrastructure Intelligence Platform (CLI + DC Agent + SaaS)
**Overall Confidence:** HIGH — patterns are well-established across CSPM, network observability, and multi-tenant SaaS domains

---

## System Overview

InfraCanvas spans three deployment contexts and five components. The binding constraint that shapes everything is the DC Agent's outbound-only, read-only access model.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Developer Workstation                                                        │
│                                                                              │
│  cli/ (Python 3.12)                                                          │
│  parser → graph → security → cost → drift → network → export                │
│       │                                          │                           │
│       │ builds                                   │ bundles                   │
│       ▼                                          ▼                           │
│  viewer/ (React 18)  ←──────────────────── viewer/ (React 18)               │
│  [lib mode → dashboard import]           [app mode → single HTML]           │
│       │                                                                      │
│       │ HTTPS (optional upload)                                              │
└───────┼──────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SaaS (Railway / Fly.io + Vercel)                                             │
│                                                                              │
│  api/ (FastAPI)  ←→  Neon PostgreSQL (RLS)                                  │
│                  ←→  Cloudflare R2   (scan artifacts)                       │
│                  ←→  Upstash Redis   (cache, arq queue)                     │
│                  ←→  Clerk           (auth, SSO)                             │
│       │                                                                      │
│       │ HTTPS                                                                │
│       ▼                                                                      │
│  dashboard/ (Next.js 14 on Vercel)                                          │
│  ← imports viewer/ components                                               │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ HTTPS outbound only (push topology snapshots)
        │
┌─────────────────────────────────────────────────────────────────────────────┐
│ Customer Data Centre                                                         │
│                                                                              │
│  dc-agent/ (Go binary)                                                       │
│  Cisco Router (NETCONF/SSH) ─┐                                               │
│  Cisco ASA/FTD  (REST)       ├─→ DCTopologySnapshot → HTTPS POST → api/    │
│  Cisco FMC      (REST)       │                                               │
│  NetFlow UDP listener ───────┘                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Language / Runtime |
|-----------|---------------|-------------------|--------------------|
| `cli/` | Parse Terraform HCL/JSON, build resource graph, run security/cost/drift rules, assemble FlowMap data, export HTML | `viewer/` (build-time); `api/` (optional HTTPS upload) | Python 3.12, Typer, Pydantic v2, NetworkX |
| `viewer/` | Render Canvas, FlowMap, CostLens interactively | CLI (receives JSON via `window.__GRAPH_DATA__`); `dashboard/` (via React import) | React 18, @xyflow/react, Zustand, Tailwind |
| `dc-agent/` | Collect Cisco device topology + NetFlow, push snapshot | `api/` (outbound HTTPS POST only) | Go, single binary |
| `api/` | Scan storage, project/team CRUD, auth validation, DC snapshot ingestion, async analysis, webhooks | `cli/`, `dc-agent/`, `dashboard/` | Python FastAPI, asyncpg, arq |
| `dashboard/` | Team views, scan history, billing UI, shared links | `api/` (REST); mounts `viewer/` components | Next.js 14 App Router, shadcn/ui, TanStack Query |

### Critical Boundary Rules

1. **DC Agent is outbound-only, read-only.** It pushes topology snapshots to `api/`. The API never initiates connections into customer DCs. No inbound firewall rules required on the customer side. No cloud credentials ever pass through dc-agent.

2. **CLI is offline-capable by default.** All analysis runs locally against `.tf` files and terraform plan output. API upload is optional. The CLI must remain pip-installable and fully functional with zero network access.

3. **Viewer is data-source-agnostic.** It receives a single JSON blob (`InfraGraph`). The delivery mechanism — embedded `<script>` in HTML or a fetch call from the dashboard — is decoupled from viewer internals via a data provider interface.

4. **API enforces all multi-tenant isolation.** Neon RLS is the authoritative isolation boundary. FastAPI middleware sets the `app.current_tenant` Postgres session variable from the Clerk JWT on every connection checkout. SQLAlchemy never writes explicit `WHERE org_id =` on tenant-owned tables.

5. **No cloud credentials stored anywhere in SaaS.** CLI reads credentials from the local environment (AWS_PROFILE, AZURE credentials env vars). DC Agent uses device credentials from its local config file. Zero credential storage in Neon or R2.

---

## Data Flow

### Flow 1: Local CLI Scan (fully offline)

```
.tf files + optional plan.json
  ↓
cli/parser      (python-hcl2 → Pydantic InfraNode[], InfraEdge[])
  ↓
cli/graph       (NetworkX DiGraph: nodes=resources, edges=depends_on)
  ↓
cli/security    (rule engine: pure functions (InfraGraph) → Finding[])
cli/cost        (pricing tables → CostEstimate[] per node)
cli/drift       (plan JSON diff → DriftDelta[] overlaid on graph)
  ↓
cli/export      (Jinja2: inlines viewer bundle + JSON blob → report.html)
                 window.__GRAPH_DATA__ = { graph, findings, costs, drift }
```

Output: A self-contained HTML file. No server. No API calls. Viewer bootstraps from `window.__GRAPH_DATA__`.

### Flow 2: DC Agent Collection (customer data centre → SaaS)

```
Cisco devices in customer DC
  ↓
dc-agent/collector
  NETCONF <get> / <get-config> over SSH (Cisco IOS-XE, NX-OS)
  SSH fallback: parse "show" command output for older IOS
  ASA REST API: interface configs, NAT rules, ACLs
  FMC REST API: security policies, VPN, routing
  NetFlow UDP listener: passive flow records (5-tuple + byte counts)
  ↓
dc-agent/snapshot
  Assembles DCTopologySnapshot{
    site_id, collected_at,
    devices[]: DeviceNode{id, type, interfaces[], routes[], acls[]},
    flows[]:   FlowRecord{src, dst, proto, bytes, packets}
  }
  ↓
HTTPS POST /api/v1/dc-snapshots
  Auth: per-site API token (stored in agent config file)
  Retry: exponential backoff, local queue if API unreachable
  Idempotent: re-posting same snapshot overwrites, not appends
```

Agent runs inside customer DC on a lightweight VM or container. Default polling: topology every 5 min, NetFlow every 1 min.

### Flow 3: FlowMap Path Tracing

```
Inputs (already collected, no live API calls during trace):
  - AWS topology:   TGW route tables, VPC routes, NACLs, Direct Connect (from CLI aws-collector)
  - Azure topology: vWAN, Secure Hub, vNet peering, ExpressRoute (from CLI azure-collector)
  - DC snapshot:    from dc-agent push (stored in Neon/R2) or local file
  - Checkpoint data: optional (policies, NAT, VPN)

cli/network/graph_builder.py:
  Merges all topology into a single HybridGraph (NetworkX)
  Nodes: cloud resources + DC devices + cross-connect edges (DX, ExpressRoute)
  Edge weights: latency estimate, hop count, bandwidth cap

cli/network/path_tracer.py:
  Forward path:  Dijkstra source → destination on HybridGraph
  Return path:   same algorithm on reverse-direction edge weights
  Asymmetry:     compare forward hops vs return hops
                 classify root cause (NAT asymmetry, BGP preference, ECMP)
  Emit:          NetworkPath{ forward[], return[], asymmetric: bool, cause }
                 NetworkFinding[] (NET-001 through NET-012)
```

Path tracer is deterministic and offline-capable — it operates on the merged in-memory graph from collected snapshots.

### Flow 4: SaaS Scan Upload

```
CLI: infracanvas push --project <id>
  ↓
POST /api/v1/scans  (multipart: scan JSON metadata + graph JSON artifact)
  Auth: Bearer CLI API token (issued via Clerk device flow)
  ↓
FastAPI /api/v1/scans:
  1. Validate Clerk JWT → extract org_id + user_id
  2. Verify project_id ∈ user's orgs
  3. generate scan_id (UUIDv7)
  4. Upload graph JSON → R2: scans/{org_id}/{project_id}/{scan_id}.json
  5. INSERT INTO scans (id, org_id, project_id, node_count, finding_count,
                         score, cost_monthly, storage_key, source, git_ref)
  6. Enqueue arq job: enrich_scan(scan_id)  [async: live pricing refresh, compliance mapping]
  7. Return 201 { scan_id, dashboard_url }
```

### Flow 5: Dashboard Diagram View

```
User navigates → /projects/{project_id}/scans/{scan_id}
  ↓
Next.js Server Component:
  Clerk session → org_id + user_id
  GET /api/v1/scans/{scan_id} → scan metadata (Neon, RLS enforced)
  ↓
Client Component:
  GET /api/v1/scans/{scan_id}/graph → R2 artifact (FastAPI proxies, adds Cache-Control)
  ↓
<InfraCanvasViewer data={graph} /> renders Canvas / FlowMap / CostLens tabs
```

### Flow 6: Multi-Tenant Isolation

```
Every FastAPI request:
  Clerk JWT middleware → extract org_id
  DB connection checkout:
    SET LOCAL app.current_org = '{org_id}'
  All queries on RLS-enabled tables execute with Neon enforcing:
    USING (org_id = current_setting('app.current_org')::uuid)
  FastAPI handlers write NO explicit org_id WHERE clauses on tenant tables.
  Migration user is postgres superuser (bypasses RLS).
  Application user is restricted role (RLS enforced, no BYPASSRLS).
```

---

## The Viewer Dual-Build Problem

The viewer must work in two radically different contexts:

| Context | Build Mode | Data Source | Auth | Routing |
|---------|------------|-------------|------|---------|
| CLI HTML export | `vite-plugin-singlefile` app build | `window.__GRAPH_DATA__` injected inline | None | None (static file) |
| SaaS Dashboard | Vite lib mode → ES module | `fetch('/api/v1/scans/{id}/graph')` via ApiDataProvider | Clerk session | Next.js App Router |

**Solution: Data Provider Abstraction + Dual Build Targets**

```
viewer/
  src/
    providers/
      StaticDataProvider.tsx     # reads window.__GRAPH_DATA__; used by CLI HTML
      ApiDataProvider.tsx        # fetches from URL prop; used by dashboard
    components/
      Canvas.tsx
      FlowMap.tsx
      CostLens.tsx
    InfraCanvasViewer.tsx        # root component; accepts dataProvider prop
    main.tsx                     # CLI entry: instantiates StaticDataProvider

  vite.config.app.ts             # singlefile build → report.html (used by CLI export)
  vite.config.lib.ts             # lib build → dist/index.js (used by dashboard import)
```

The CLI export injects `window.__GRAPH_DATA__` and uses `main.tsx`. The dashboard imports `InfraCanvasViewer` and passes `ApiDataProvider` as a prop. No code duplication. No two implementations to keep in sync.

---

## Recommended Monorepo Structure

```
infracanvas/
  cli/                     # Python 3.12 package
    infracanvas/
      parser/              # HCL + plan JSON parsing
      graph/               # NetworkX graph builder
      security/            # rule engine (pure functions)
      cost/                # pricing tables + estimator
      drift/               # plan diff → DriftDelta
      network/             # FlowMap: collectors, path tracer, findings
      export/              # HTML template + Jinja2 + asset injection
      api_client.py        # HTTPS client for SaaS upload
    pyproject.toml

  viewer/                  # React 18 shared component library
    src/
    vite.config.app.ts     # → single HTML (CLI export)
    vite.config.lib.ts     # → ES module (dashboard import)
    package.json

  dc-agent/                # Go binary
    cmd/agent/main.go
    internal/
      collector/           # NETCONF, SSH, ASA REST, FMC REST
      netflow/             # UDP listener + flow aggregation
      snapshot/            # DCTopologySnapshot serialization
      push/                # HTTPS client with retry + local queue
    go.mod

  api/                     # FastAPI backend
    app/
      routers/             # scans, projects, teams, shares, webhooks, dc_snapshots
      models/              # Pydantic: ScanCreate, ScanResponse, DCSnapshot, ...
      middleware/          # Clerk JWT validation, tenant context
      services/            # R2 storage, arq tasks, Neon helpers
    migrations/            # Alembic
    pyproject.toml

  dashboard/               # Next.js 14 App Router (Vercel)
    app/
      (auth)/              # Clerk sign-in, sign-up
      (dashboard)/         # protected: projects, scans, teams, billing
        projects/
        scans/[id]/        # diagram view → imports viewer/
        settings/
      share/[slug]/        # public share page (no auth)
    components/
      viewer-wrapper/      # thin wrapper around viewer/ lib import
      ui/                  # shadcn/ui components, nav, tables
    package.json

  vercel.json              # experimentalServices (if using Vercel for both)
  .planning/
```

---

## Patterns to Follow

### Pattern 1: Rule Engine as Pure Functions

Security rules, network findings, and cost rules are pure functions: `(InfraGraph) → Finding[]`. No I/O. No side effects.

**Why:** Unit-testable without infrastructure. Safe to run in parallel (ThreadPoolExecutor). New rules added by adding a function — no registration, no plugin system needed at v1.

```python
def rule_s3_public_read(graph: InfraGraph) -> list[Finding]:
    return [
        Finding(rule="S3-001", severity="HIGH", resource=node.id,
                detail="Bucket ACL is public-read")
        for node in graph.nodes_by_type("aws_s3_bucket")
        if node.attrs.get("acl") == "public-read"
    ]
```

### Pattern 2: Push-Pull Topology Snapshot (no streaming in v1)

DC Agent pushes `DCTopologySnapshot` on a schedule. API stores it. CLI and path tracer read from stored snapshots — they do not make live device calls.

**Why:** Outbound-only constraint eliminates server-initiated push. 5-minute polling is sufficient for infrastructure topology change rates. Streaming (NETCONF event subscriptions, RFC 5277) is valid for v2/Enterprise but adds complexity and requires newer IOS versions.

### Pattern 3: Unified Graph Model

One canonical `InfraGraph` (NetworkX DiGraph) flows through the entire CLI pipeline. Each analysis module reads from it and writes to a separate `FindingsStore` — modules do not couple to each other.

```
InfraGraph
  nodes: InfraNode(id, type, provider, region, attrs: dict)
  edges: InfraEdge(source, target, relationship: str)

FindingsStore
  findings: list[Finding]
  by_resource: dict[node_id, list[Finding]]
  by_rule: dict[rule_id, list[Finding]]
```

For FlowMap, the DC topology is merged into a `HybridGraph` that extends `InfraGraph` with `DCDevice` nodes and cross-connect edges. The path tracer operates on `HybridGraph` only.

### Pattern 4: Arq Background Jobs for Async SaaS Work

Uploads trigger arq background jobs for work that must not block the API response: live pricing refresh, compliance mapping, FlowMap enrichment from DC snapshots.

**Why:** FastAPI handlers return 201/202 immediately. arq (asyncio task queue backed by Upstash Redis) processes enrichment asynchronously. Solo-founder constraint rules out separate worker infrastructure — arq runs as a subprocess alongside FastAPI on the same dyno.

### Pattern 5: Per-Site API Tokens for DC Agent Auth

Each DC site gets an API token issued from the dashboard (Settings → DC Sites → Add Site). Token is stored in the agent's config file. Token can be revoked from the dashboard. Tokens are scoped to a single `site_id` within the org's Neon partition.

**Why:** Long-lived agent connections cannot use browser session cookies. Short-lived OAuth tokens would require token refresh infrastructure inside the agent. Per-site tokens are simple, revocable, and match the pattern used by Datadog Agent, Grafana Agent, etc.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Cloud Credentials in SaaS

**What goes wrong:** AWS/Azure credentials stored in Neon or R2 to enable server-side cloud API calls.
**Consequences:** Credential breach is existential for a security-focused product. Target persona (Platform Engineers) will not adopt.
**Instead:** CLI reads credentials from local environment. DC Agent uses local device credentials. No cloud credentials ever leave the user's environment.

### Anti-Pattern 2: Two Separate Viewer Codebases

**What goes wrong:** One React app for CLI HTML export, a second implementation inside Next.js.
**Consequences:** Feature parity diverges immediately. Bug fixed in one, missed in the other. Double test surface.
**Instead:** Single viewer package with dual Vite build targets + swappable data providers (see Viewer section above).

### Anti-Pattern 3: Tenant Filtering in FastAPI Handlers

**What goes wrong:** `WHERE org_id = current_user.org_id` written in every SQLAlchemy query.
**Consequences:** Any missed clause causes cross-tenant data leak. At scale, human error is guaranteed.
**Instead:** SET LOCAL Postgres session variable on every connection checkout. Enable RLS on all tenant-owned tables. Neon enforces isolation regardless of query code.

### Anti-Pattern 4: Storing Full InfraGraph JSON in Neon

**What goes wrong:** `JSONB` column on the `scans` table holds the full graph.
**Consequences:** 500KB-2MB blobs bloat Neon rows. List queries on `scans` slow dramatically. Backup size balloons.
**Instead:** Scalar summary fields in Neon (`node_count`, `finding_count`, `score`, `cost_monthly`). Full graph JSON stored as a flat object in Cloudflare R2. Dashboard fetches R2 artifact only for diagram view.

### Anti-Pattern 5: Re-implementing CLI Analysis in FastAPI

**What goes wrong:** The parser, security rules, and cost estimation are re-implemented inside FastAPI for the CI/CD webhook flow.
**Consequences:** Two implementations diverge. Rules added to CLI don't appear in SaaS webhook scans.
**Instead:** `api/` imports `cli/infracanvas/` as a local package (monorepo path dependency). arq background jobs call the same Python analysis modules.

### Anti-Pattern 6: NETCONF Event Streaming in DC Agent v1

**What goes wrong:** Using NETCONF subscription streams (RFC 5277) for real-time updates.
**Consequences:** Not universally supported across Cisco IOS versions. Significantly increases agent complexity. Streaming adds no value over 5-min polling for infrastructure topology.
**Instead:** Periodic `<get>` / `<get-config>` RPC calls. SSH `show` command fallback for older IOS. Streaming deferred to Enterprise phase.

---

## Database Schema (Core Tables)

```sql
-- Neon PostgreSQL (serverless, scales to zero)
-- Application role: restricted (RLS enforced)
-- Migration role:   postgres superuser (bypasses RLS)

organizations
  id           UUID PRIMARY KEY
  name         TEXT
  slug         TEXT UNIQUE
  plan         TEXT    -- free | pro | team | enterprise
  created_at   TIMESTAMPTZ

-- RLS: visible only to members
CREATE POLICY "org_isolation" ON projects
  USING (org_id = current_setting('app.current_org')::uuid);

projects
  id           UUID PRIMARY KEY
  org_id       UUID REFERENCES organizations  -- RLS tenant key
  name         TEXT
  slug         TEXT
  created_at   TIMESTAMPTZ

scans
  id           UUID PRIMARY KEY  -- UUIDv7 (sortable by time)
  org_id       UUID REFERENCES organizations  -- RLS tenant key
  project_id   UUID REFERENCES projects
  created_at   TIMESTAMPTZ
  source       TEXT    -- cli | ci | webhook
  node_count   INT
  finding_count INT
  score        NUMERIC(4,2)
  cost_monthly NUMERIC(10,2)
  storage_key  TEXT    -- R2 path: scans/{org_id}/{project_id}/{scan_id}.json
  git_ref      TEXT NULL

dc_snapshots
  id           UUID PRIMARY KEY
  org_id       UUID REFERENCES organizations  -- RLS tenant key
  site_id      UUID REFERENCES dc_sites
  collected_at TIMESTAMPTZ
  storage_key  TEXT    -- R2 path: dc-snapshots/{org_id}/{site_id}/{ts}.json
  device_count INT
  flow_count   INT

dc_sites
  id           UUID PRIMARY KEY
  org_id       UUID REFERENCES organizations  -- RLS tenant key
  name         TEXT
  token_hash   TEXT UNIQUE  -- SHA-256 of API token; never store plaintext

shares
  id           UUID PRIMARY KEY
  org_id       UUID REFERENCES organizations  -- RLS tenant key
  scan_id      UUID REFERENCES scans
  slug         TEXT UNIQUE  -- 8-char nanoid
  is_public    BOOLEAN DEFAULT true
  password_hash TEXT NULL
  expires_at   TIMESTAMPTZ NULL
  created_at   TIMESTAMPTZ

api_tokens                    -- CLI + CI tokens (not DC agent tokens)
  id           UUID PRIMARY KEY
  org_id       UUID REFERENCES organizations
  user_id      UUID           -- Clerk user ID
  token_hash   TEXT UNIQUE
  label        TEXT
  last_used_at TIMESTAMPTZ NULL
  created_at   TIMESTAMPTZ
```

---

## Build Order (Component Dependency Chain)

Components have strict build dependencies. Building out of order creates integration dead ends.

```
Tier 0 — Shared Contracts (no dependencies)
  cli/infracanvas/models.py     InfraGraph, InfraNode, Finding, NetworkPath (Pydantic)
  JSON schema for InfraGraph    shared between Python and TypeScript

Tier 1 — Core Data Producers (depend only on Tier 0)
  cli/parser                    HCL → InfraGraph
  cli/security                  InfraGraph → Finding[]
  cli/cost                      InfraGraph → CostEstimate[]
  cli/drift                     plan JSON + InfraGraph → DriftDelta[]

Tier 2 — Viewer (depends on Tier 0 JSON schema for fixture data)
  viewer/                       Can be built and tested with fixture JSON
                                Dual build targets established here

Tier 3 — CLI Export (depends on Tier 1 + Tier 2)
  cli/export                    Bundles viewer app build + graph JSON → report.html
                                End-to-end CLI flow fully working at this tier

Tier 4 — Network Layer (extends Tier 0 + Tier 1)
  cli/network                   FlowMap data model, AWS/Azure collectors, path tracer
  dc-agent/                     Go binary: NETCONF, SSH, ASA REST, FMC REST, NetFlow push

Tier 5 — SaaS API (depends on Tier 0 data models for DB schema)
  api/                          FastAPI, Neon, R2, Clerk, arq
                                DC snapshot ingestion endpoint needed before DC agent can be tested end-to-end

Tier 6 — SaaS Dashboard (depends on Tier 2 viewer + Tier 5 API)
  dashboard/                    Next.js 14, imports viewer/ lib build, calls api/

Tier 7 — Advanced SaaS Features (stable Tier 5 + Tier 6 required)
  CostLens cross-cloud cost allocation
  Compliance framework engine
  CI/CD webhook + Slack alerts
  Share link system
  Scan history + comparison
```

**Critical path for MVP:** Tier 0 → Tier 1 → Tier 2 → Tier 3 (CLI self-contained) → Tier 5 → Tier 6 (SaaS).

**Tier 4 (DC Agent + Network Layer)** is independent of Tier 5/6 for data collection; it requires Tier 5 for end-to-end push. DC Agent can be developed in parallel with Tier 5 if the snapshot API contract is agreed first.

**Key implication:** Viewer (Tier 2) must be a standalone dual-build package from the start, even before the SaaS dashboard exists. Retrofitting this later requires significant refactoring.

---

## Integration Points and Risks

| Integration | Pattern | Risk | Mitigation |
|-------------|---------|------|------------|
| Viewer dual-build (HTML + lib) | Two Vite configs, shared src/ | Vite lib mode and app mode may conflict on globals | Separate config files; E2E test for both CLI HTML export and dashboard render as CI gates |
| DC Agent → API auth | Per-site long-lived API token | Token compromise gives DC topology read access | Scope tokens to single site_id; revocation via dashboard; tokens stored as SHA-256 hash in Neon |
| NETCONF on older Cisco IOS | `<get>` RPC over SSH | IOS < 15.x has inconsistent or absent NETCONF | SSH + `show` command parser as mandatory fallback; detect NETCONF capability via hello exchange |
| Neon serverless cold start | ~500ms on first connection after idle | Cold starts visible in CLI upload + webhook flows | Upstash Redis session ping as keep-alive; connection pool pre-warm on FastAPI startup |
| RLS bypass via migration user | Alembic runs as superuser | Migration bugs could create data accessible without RLS | App connection role has no BYPASSRLS; separate CI check verifies RLS policies exist on all tenant tables |
| R2 + Neon consistency | R2 upload succeeds, Neon INSERT fails | Orphaned R2 objects with no scan record | Write Neon record first; R2 upload second; schedule periodic R2 orphan cleanup job |
| CLI imports from api/ (monorepo) | Path dependency in pyproject.toml | Import path breaks in PyInstaller standalone binary | Test PyInstaller build in CI; shared models extracted to a third `infracanvas-models` package if needed |

---

## Scalability Considerations

| Concern | MVP (0–200 users) | Growth (200–2000) | Scale (2000+) |
|---------|------------------|-------------------|----------------|
| DB connections | Neon built-in pooler | Neon pooler sufficient | PgBouncer if > 1000 concurrent |
| Scan artifact storage | R2 flat objects, no prefix index | R2 + Neon metadata index | R2 lifecycle policy to archive scans > 90 days |
| Background processing | arq workers co-located with API | arq workers on separate dyno | Horizontal arq worker scale-out |
| DC Agent throughput | 1 agent per site, 5-min polling | Same | Same — agent is stateless; horizontal by site |
| Viewer render performance | ReactFlow with cached layout positions | Same | Web Worker for layout; canvas fallback > 2000 nodes |
| API hosting | Railway Starter ($5/mo) | Railway Pro or Fly.io | Fly.io multi-region |

---

## Sources

- [Hybrid Multi-cloud Network Observability Reference Architecture — Datadog](https://www.datadoghq.com/architecture/hybrid-cloud-network-observability/)
- [FastAPI Multi-Tenant SaaS: Row-Level Security Without Pain](https://medium.com/@hjparmar1944/fastapi-multi-tenant-saas-row-level-security-without-pain-9ef960085bf4)
- [Multi-tenant data isolation with PostgreSQL Row Level Security — AWS Blog](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)
- [Shipping multi-tenant SaaS using Postgres Row-Level Security — Nile](https://www.thenile.dev/blog/multi-tenant-rls)
- [vite-plugin-singlefile](https://github.com/richardtallent/vite-plugin-singlefile)
- [Infrastructure Drift Detection — Spacelift](https://spacelift.io/blog/drift-detection)
- [Juniper go-netconf: NETCONF implementation in Go](https://github.com/Juniper/go-netconf)
- [Cisco NX-OS Programmability Guide: NETCONF Agent](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/93x/progammability/guide/b-cisco-nexus-9000-series-nx-os-programmability-guide-93x/)
- [Asymmetric routing detection and traceroute analysis — Obkio](https://obkio.com/blog/traceroutes-internet-traffic-is-asymmetrical/)
- [Cloud Security Posture Management Architecture — Security Boulevard](https://securityboulevard.com/2026/03/cloud-security-posture-management-in-2026/)

---
*Researched: 2026-04-15 | InfraCanvas hybrid cloud intelligence platform — Architecture dimension*
