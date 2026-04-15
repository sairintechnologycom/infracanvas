# InfraCanvas — Architecture v2.0

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          CLI (infracanvas)                                │
│  scan │ plan │ score │ export │ serve │ login │ push                      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        DATA COLLECTION LAYER                              │
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │  IaC Sources     │  │  Cloud APIs       │  │  DC Collector Agent    │  │
│  │                  │  │                   │  │                        │  │
│  │  .tf files       │  │  AWS:             │  │  Cisco Routers:        │  │
│  │  .tfstate        │  │  TGW API          │  │  NETCONF/RESTCONF      │  │
│  │  tfvars          │  │  VPC API          │  │  (IOS-XE 16.6+)        │  │
│  │  plan JSON       │  │  Cost Explorer    │  │  SSH CLI fallback      │  │
│  │                  │  │  CloudWatch       │  │  NetFlow v9/IPFIX      │  │
│  │                  │  │  Network Firewall │  │                        │  │
│  │                  │  │                   │  │  Cisco ASA:            │  │
│  │                  │  │  Azure:           │  │  REST API (9.3+)       │  │
│  │                  │  │  vWAN API         │  │  SSH CLI fallback      │  │
│  │                  │  │  Network Watcher  │  │                        │  │
│  │                  │  │  Azure Monitor    │  │  Cisco FTD:            │  │
│  │                  │  │  Cost Management  │  │  FMC REST API          │  │
│  │                  │  │                   │  │  (single endpoint)     │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │              Security Platform APIs (no agent required)           │    │
│  │                                                                   │    │
│  │  Checkpoint R80+:              Zscaler (Phase 5 only):           │    │
│  │  Management API                ZIA: forwarding rules             │    │
│  │  Full policy + hit counts      ZPA: connector topology           │    │
│  │  NAT rules, VPN communities    ZDX: hop-by-hop path traces       │    │
│  │                                                                   │    │
│  │  NMS (Phase 5 Enterprise):                                        │    │
│  │  SolarWinds API / PRTG API / NetBrain API                        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      NORMALISATION ENGINE                                 │
│                                                                           │
│  Unified resource model across AWS + Azure + On-prem                      │
│  Resolves Terraform → actual resource mapping                             │
│  Correlates BGP routes with static routes per segment                     │
│  Timestamps all state for point-in-time queries                           │
│  Shadow infra: API-discovered resources not in Terraform                  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                       ┌───────────┼───────────┐
                       ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────────────┐
│ HCL Parser   │ │ State Reader │ │ Plan Reader                          │
│ (.tf files)  │ │ (.tfstate)   │ │ (terraform show -json)               │
└──────┬───────┘ └──────┬───────┘ └───────────────────────┬──────────────┘
       │                │                                  │
       └────────────────┴──────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       RESOURCE GRAPH BUILDER                              │
│  Nodes: resources, data sources, modules, DC router segments             │
│  Edges: dependencies, references, network paths, route adjacencies       │
│  Groups: VPC, subnet, module, region, DC site, security zone             │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
┌─────────────────┐   ┌───────────────────────┐   ┌─────────────────┐
│  CANVAS ENGINE  │   │  FLOWMAP ENGINE        │   │ COSTLENS ENGINE │
│                 │   │                        │   │                 │
│  Security rules │   │  Path tracer           │   │  Cost allocator │
│  Policy checker │   │  Asymmetry detector    │   │  Per-flow price │
│  Drift analyser │   │  BGP/static correlator │   │  Shared cost    │
│  Runtime checks │   │  Capacity monitor      │   │  split engine   │
│  Shadow infra   │   │  Route change alerter  │   │  Optimisation   │
│  Tag compliance │   │  Network findings      │   │  recommender    │
│  Lock validator │   │  Firewall rule analyser│   │                 │
└────────┬────────┘   └───────────┬────────────┘   └────────┬────────┘
         │                        │                          │
         └────────────────────────┼──────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    ANNOTATED GRAPH (unified model)                        │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                     ▼
     ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │ HTML Renderer  │  │  JSON Exporter  │  │  SVG/PNG Export │
     │ (React SPA)    │  │  (CI/CD)        │  │  (reports)      │
     └────────────────┘  └─────────────────┘  └─────────────────┘
                                   │
                         (optional: push to cloud)
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       SAAS BACKEND (FastAPI)                              │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │ Auth     │  │ Projects │  │ Scans    │  │ Sharing & Permissions  │   │
│  │ (Clerk)  │  │ API      │  │ History  │  │ (UUID + token + expiry)│   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  PostgreSQL (projects, scans, users, teams, webhooks)            │    │
│  │  Cloudflare R2 (scan artifacts: JSON, HTML, images)              │    │
│  │  Upstash Redis (session cache, rate limiting, job queue)         │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     SAAS FRONTEND (Next.js)                               │
│                                                                           │
│  Dashboard │ Project View │ Scan History │ Canvas Viewer                  │
│  FlowMap Viewer │ CostLens View │ Team Mgmt │ Share View                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## DC Collector Agent Architecture

The DC Collector Agent bridges the visibility gap between cloud APIs and physical data centre infrastructure. It is the piece every other tool is missing.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DC COLLECTOR AGENT                            │
│  Deployed once per data centre. Read-only. Outbound-only.       │
│  Target: <30 min deployment per DC site.                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               CISCO ROUTER INTEGRATION                   │   │
│  │                                                          │   │
│  │  Primary (IOS-XE 16.6+): NETCONF/RESTCONF               │   │
│  │  ├─ Full RIB (routing table) with next-hops             │   │
│  │  ├─ BGP peer state + advertised/received prefixes        │   │
│  │  ├─ VRF routing tables per VRF instance                 │   │
│  │  └─ Interface state and IP assignments                   │   │
│  │                                                          │   │
│  │  Fallback (older IOS): SSH + CLI Parser                  │   │
│  │  ├─ show ip route (static + BGP + connected)            │   │
│  │  ├─ show bgp neighbors (peer state + AS paths)          │   │
│  │  └─ show ip bgp (full BGP table)                         │   │
│  │                                                          │   │
│  │  Traffic (all versions): NetFlow v9 / IPFIX Collector    │   │
│  │  └─ Actual traffic flows per source/destination          │   │
│  │     (ground truth — confirms which path was actually     │   │
│  │      taken, not just which path route table says)        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              CISCO ASA INTEGRATION                       │   │
│  │                                                          │   │
│  │  Primary (ASA 9.3+): REST API                           │   │
│  │  ├─ Access lists with hit counts                        │   │
│  │  ├─ NAT rules and translations                          │   │
│  │  ├─ Current connection count vs. max                    │   │
│  │  └─ Active VPN sessions                                  │   │
│  │                                                          │   │
│  │  Event data (all versions): Syslog                      │   │
│  │  └─ Connection events for traffic path confirmation      │   │
│  │                                                          │   │
│  │  Advanced (ASP): show asp drop                          │   │
│  │  └─ Dropped packets by reason — gold for debugging      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          CISCO FIREPOWER (FTD via FMC) INTEGRATION       │   │
│  │                                                          │   │
│  │  Single FMC API endpoint manages all FTD devices:        │   │
│  │  ├─ Access control policies (including pre/post rules)  │   │
│  │  ├─ NAT policies                                        │   │
│  │  ├─ VPN topologies                                      │   │
│  │  └─ Connection events (traffic decisions)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  OUTPUT → InfraCanvas Cloud API (encrypted, outbound only)      │
│  ├─ Static route topology per router                            │
│  ├─ BGP peer adjacencies and prefix tables                      │
│  ├─ BGP/static boundary identification per path segment         │
│  ├─ Actual NetFlow traffic data (which path used in practice)   │
│  └─ Firewall policy + capacity + hit count data                 │
└─────────────────────────────────────────────────────────────────┘
```

### Config File Import (Fallback)
For environments where agent deployment isn't immediately possible:
- Upload router config files (Cisco IOS, Juniper, Fortinet formats)
- We parse static route tables, prefix lists, and route maps from config text
- Less real-time but gives us topology for visualisation at 80% of the value

---

## FlowMap — Asymmetric Routing Detection Logic

```
For every source-destination pair:

1. FORWARD PATH TRACE
   ├─ Start at AWS TGW route table (API)
   ├─ Follow longest-prefix match at each hop
   ├─ At BGP→Static boundary: record handoff prefix + DC entry point
   ├─ Across DC segment: follow static routes from collector agent data
   ├─ At Static→BGP boundary: record re-entry point
   ├─ Into Azure: follow vWAN effective routes (API)
   └─ Map complete forward path: Source A → ... → Destination B

2. RETURN PATH TRACE
   ├─ Start at Azure vWAN effective routes
   ├─ Follow longest-prefix match in reverse direction
   ├─ Note: BGP path attributes (AS path, MED, local preference) may
   │        cause different DC entry/exit vs forward path
   ├─ Follow DC segment routing (BGP or static — may differ from forward)
   └─ Map complete return path: Destination B → ... → Source A

3. SYMMETRY CHECK
   ├─ Compare forward and return paths hop by hop
   ├─ Flag divergence points: where does forward go left, return go right?
   ├─ Classify root cause:
   │   ├─ BGP attribute difference (AS path length, MED, local pref)
   │   ├─ Static route pointing different direction on return
   │   ├─ Zscaler interception on one direction only (Phase 5)
   │   └─ NAT asymmetry (Checkpoint NAT rule on one path only)
   └─ Identify divergence point with highest precision possible

4. IMPACT ASSESSMENT
   ├─ Is a stateful firewall on one path but not the other? → CRITICAL
   ├─ Is the asymmetry causing firewall inspection bypass? → CRITICAL
   ├─ What is the latency difference between paths?
   └─ Finding severity: Critical if firewall bypass, High if stateful inspection broken
```

### Visual Output
The diagram renders the full topology with:
- **Blue line**: forward traffic path
- **Orange line**: return traffic path
- **Red marker**: exact divergence point with root cause explanation
- **Annotation**: "Forward traffic intercepted by [device/service] at [hop]. Return traffic bypasses this. Stateful Checkpoint firewall in DC Singapore sees only forward direction — connections will drop intermittently."

---

## Network-Specific Finding Types

| Finding ID | Title | Severity | Detection Method |
|-----------|-------|----------|-----------------|
| NET-001 | Static route no failover | Critical | Route table: static with no BGP backup prefix |
| NET-002 | Stale static route | Critical | Static next-hop not reachable in cloud routing |
| NET-003 | Static/BGP asymmetry | High | Forward static, return BGP (or vice versa) |
| NET-004 | Undocumented static route | High | In router RIB but not in Terraform or any IaC |
| NET-005 | Static route redistributed into BGP | High | Route map or redistribute static found in BGP config |
| NET-006 | Static/BGP overlap | Medium | Both static and BGP exist for same prefix (static wins silently) |
| NET-007 | Firewall SNAT near capacity | High | Azure Firewall SNAT port utilisation > 85% |
| NET-008 | Firewall rule capacity critical | Critical | Checkpoint/ASA rule count > 95% of limit |
| NET-009 | Stale firewall rule | Info | Rule with zero hit count in 90 days |
| NET-010 | Asymmetric firewall inspection | Critical | Stateful firewall on forward path, bypassed on return |
| NET-011 | BGP route withdrawal | High | Previously advertised prefix withdrawn without planned change |
| NET-012 | Route table drift | High | Effective route table differs from Terraform-declared intent |

---

## Data Model

### Core Entities

```
Project
├── id: uuid
├── name: string
├── description: string
├── repo_url: string (optional)
├── providers: enum[] (aws, azure, gcp)
├── has_dc_sites: boolean
├── team_id: uuid (FK)
├── created_at: timestamp
└── updated_at: timestamp

Scan
├── id: uuid
├── project_id: uuid (FK)
├── trigger: enum (cli, webhook, manual)
├── status: enum (pending, running, completed, failed)
├── source_type: enum (terraform_dir, tfstate, plan_json, live_api)
├── resource_count: integer
├── finding_counts: jsonb {critical, high, medium, info}
├── network_finding_counts: jsonb {critical, high, medium, info}
├── estimated_monthly_cost: decimal
├── shared_cost_allocated: boolean
├── drift_summary: jsonb {added, changed, deleted, shadow}
├── score: integer (0-100)
├── artifact_url: string (R2 path)
├── created_at: timestamp
└── duration_ms: integer

Resource (stored in scan artifact JSON)
├── id: string (terraform resource address)
├── type: string (aws_instance, aws_s3_bucket, etc.)
├── name: string
├── provider: string (aws, azure, on-prem)
├── module: string (optional)
├── region: string
├── dc_site: string (optional — for physical DC resources)
├── attributes: jsonb
├── dependencies: string[]
├── findings: Finding[]
├── network_findings: NetworkFinding[]
├── cost_estimate: CostEstimate
├── drift_status: enum (unchanged, added, changed, deleted, shadow)
└── is_shadow: boolean (true if not in Terraform)

NetworkFinding
├── rule_id: string (NET-001..NET-012)
├── severity: enum (critical, high, medium, info)
├── title: string
├── description: string
├── remediation: string
├── affected_path: PathSegment[]
├── divergence_point: string (optional — for asymmetric routing findings)
└── evidence: jsonb

NetworkPath
├── id: string
├── scan_id: uuid
├── source: string (resource address or CIDR)
├── destination: string
├── forward_path: PathHop[]
├── return_path: PathHop[]
├── is_symmetric: boolean
├── divergence_at: PathHop (optional)
└── divergence_reason: string (optional)

PathHop
├── sequence: integer
├── device_type: enum (tgw, vpc, customer_gateway, dc_router, azure_hub, azure_vnet, firewall, zscaler_pop)
├── device_id: string
├── routing_type: enum (bgp, static, managed)
├── next_hop: string
└── notes: string (optional)

DCCollectorReading
├── id: uuid
├── dc_site: string
├── device_id: string
├── device_type: enum (cisco_router, cisco_asa, cisco_ftd)
├── reading_type: enum (route_table, bgp_peers, netflow, firewall_policy)
├── data: jsonb
├── collected_at: timestamp
└── agent_version: string
```

### Resource Graph JSON Schema

```json
{
  "version": "2.0",
  "metadata": {
    "scan_id": "uuid",
    "project": "my-infra",
    "providers": ["aws", "azure"],
    "has_dc_sites": true,
    "dc_sites": ["dc-singapore", "dc-sydney"],
    "scanned_at": "2026-04-15T10:00:00Z",
    "terraform_version": "1.8.0"
  },
  "nodes": [
    {
      "id": "aws_vpc.main",
      "type": "aws_vpc",
      "name": "main",
      "provider": "aws",
      "module": "",
      "region": "ap-southeast-1",
      "group": "vpc-12345",
      "attributes": { "cidr_block": "10.0.0.0/16" },
      "position": { "x": 0, "y": 0 },
      "findings": [],
      "network_findings": [],
      "cost": { "monthly": 0, "currency": "USD" },
      "drift": "unchanged",
      "is_shadow": false
    },
    {
      "id": "dc-router.singapore-core-01",
      "type": "dc_router",
      "name": "singapore-core-01",
      "provider": "on-prem",
      "dc_site": "dc-singapore",
      "routing_type": "bgp_and_static",
      "attributes": {
        "ios_version": "16.9.4",
        "bgp_as": "65001",
        "static_routes": 12,
        "bgp_peers": 3
      },
      "network_findings": [
        {
          "rule_id": "NET-001",
          "severity": "critical",
          "title": "Static route with no BGP failover",
          "evidence": { "prefix": "10.100.0.0/16", "next_hop": "172.16.0.1" }
        }
      ]
    }
  ],
  "edges": [
    {
      "source": "aws_subnet.public",
      "target": "aws_vpc.main",
      "type": "dependency"
    },
    {
      "source": "aws_customer_gateway.dc_sg",
      "target": "dc-router.singapore-core-01",
      "type": "network_path",
      "routing_type": "bgp"
    }
  ],
  "network_paths": [
    {
      "id": "path-sg-to-ause",
      "source": "aws_vpc.main (ap-southeast-1)",
      "destination": "azurerm_virtual_network.prod (australiaeast)",
      "is_symmetric": false,
      "divergence_at": {
        "sequence": 3,
        "device_id": "dc-router.singapore-core-01",
        "routing_type": "static"
      },
      "divergence_reason": "Forward path uses static route 10.200.0.0/16 → 172.16.0.1 (dc-sydney). Return BGP selected different AS path through dc-melbourne."
    }
  ],
  "summary": {
    "total_resources": 47,
    "shadow_resources": 3,
    "findings": { "critical": 2, "high": 5, "medium": 12, "info": 8 },
    "network_findings": { "critical": 1, "high": 2, "medium": 1, "info": 0 },
    "estimated_monthly_cost": 2847.50,
    "shared_cost_allocated": true,
    "score": 68,
    "drift": { "added": 3, "changed": 1, "deleted": 0, "shadow": 3 }
  }
}
```

---

## API Contracts

### CLI → SaaS API

```
POST   /api/v1/scans                    Upload scan result
GET    /api/v1/scans/:id                Get scan details
GET    /api/v1/scans/:id/network-paths  Get network path analysis
POST   /api/v1/projects                 Create project
GET    /api/v1/projects/:id/scans       List scans for project
GET    /api/v1/projects/:id/compare     Compare two scans
POST   /api/v1/shares                   Create share link
GET    /api/v1/shares/:token            Get shared scan (public, no auth)
POST   /api/v1/dc-collector/readings    DC agent telemetry ingest

Headers:
  Authorization: Bearer <api-key>
  Content-Type: application/json
```

### DC Collector Agent → SaaS API

```
POST /api/v1/dc-collector/readings
Body: {
  "dc_site": "dc-singapore",
  "device_id": "core-router-01",
  "device_type": "cisco_router",
  "reading_type": "route_table",
  "data": { ... },
  "agent_version": "0.3.1"
}

Authentication: Per-site API key (scoped, rotatable)
Transport: TLS 1.3, outbound only from DC
Frequency: Route tables every 5 min, BGP state every 1 min, NetFlow every 30s
```

### Webhook Endpoint

```
POST /api/v1/webhooks/scan
Body: {
  "project_id": "uuid",
  "source": "github|gitlab|bitbucket",
  "ref": "main",
  "commit_sha": "abc123",
  "terraform_dir": "./infra"
}
```

---

## Security Architecture

- **Auth**: Clerk (managed auth, SSO for Enterprise via SAML/OIDC)
- **API keys**: Scoped per project, rotatable, stored hashed (SHA-256)
- **DC Agent keys**: Scoped per DC site, separate key namespace, rotatable
- **Data isolation**: Row-level security in PostgreSQL per team
- **Scan artifacts**: Encrypted at rest in Cloudflare R2, signed URLs for access
- **No cloud credentials stored**: InfraCanvas never sees AWS/Azure credentials — reads local files and cloud APIs only with read-only IAM roles
- **CLI scans are local**: Nothing leaves the machine unless `infracanvas push` is explicitly run
- **DC agent**: Read-only, outbound-only, no inbound ports opened, no persistent connection
- **Share links**: UUID + random token, optional password, configurable expiry
- **Compliance data**: Scan artifacts containing compliance evidence stored in customer-specified region (Enterprise)

---

## Infrastructure (SaaS Hosting)

### Cost-Optimised Stack

| Component | Choice | Monthly Cost |
|-----------|--------|-------------|
| Backend | Railway or Fly.io (FastAPI) | $10–25 |
| Frontend | Vercel (Next.js) | $0–20 |
| Database | Neon PostgreSQL (serverless) | $0–19 |
| Object Storage | Cloudflare R2 | $0–5 |
| Cache | Upstash Redis | $0–10 |
| Auth | Clerk (free tier → paid at scale) | $0–25 |
| CDN | Cloudflare | $0 |
| **Total** | | **$10–104/mo** |

### CI/CD
- GitHub Actions for CLI releases (multi-platform: Linux amd64, macOS arm64, Windows x64)
- GitHub Actions for SaaS deployment (Railway/Vercel auto-deploy on merge to main)
- Release channels: stable, beta
- DC Collector Agent: distributed as standalone binary per platform

---

## Monorepo Structure

```
infracanvas/
├── cli/                              # Python CLI + Core Engine
│   ├── infracanvas/
│   │   ├── main.py                   # Typer CLI entrypoint
│   │   ├── parser/
│   │   │   ├── hcl.py                # HCL parser (aws + azure)
│   │   │   ├── state.py              # .tfstate reader
│   │   │   ├── plan.py               # terraform plan JSON reader
│   │   │   └── references.py         # implicit dependency detection
│   │   ├── graph/
│   │   │   ├── builder.py            # NetworkX DiGraph construction
│   │   │   ├── models.py             # Pydantic models v2
│   │   │   └── layout.py             # Auto-layout algorithms
│   │   ├── security/
│   │   │   ├── engine.py             # Rule evaluation engine
│   │   │   └── rules/aws/ + azure/   # YAML rule definitions
│   │   ├── network/                  # FlowMap engine (closed-source)
│   │   │   ├── topology.py           # Hybrid topology builder
│   │   │   ├── path_tracer.py        # Forward/return path computation
│   │   │   ├── asymmetry.py          # Asymmetric routing detector
│   │   │   ├── capacity.py           # Firewall capacity monitor
│   │   │   └── findings.py           # Network-specific rule engine
│   │   ├── cost/
│   │   │   ├── estimator.py          # Per-resource cost estimation
│   │   │   ├── shared.py             # Shared infra cost allocation
│   │   │   └── pricing.py            # Infracost + static pricing DB
│   │   ├── drift/
│   │   │   └── analyzer.py           # Plan diff + shadow infra
│   │   ├── policy/
│   │   │   └── engine.py             # Custom YAML policy checker
│   │   ├── cloud/                    # Live cloud API clients
│   │   │   ├── aws.py                # AWS API wrappers
│   │   │   └── azure.py              # Azure API wrappers
│   │   └── export/
│   │       ├── html.py               # Embed React SPA with graph data
│   │       ├── json.py
│   │       ├── svg.py
│   │       └── png.py
│   └── tests/
│
├── dc-agent/                         # DC Collector Agent (Go)
│   ├── collectors/
│   │   ├── cisco_netconf.go          # NETCONF/RESTCONF client
│   │   ├── cisco_ssh.go              # SSH CLI fallback parser
│   │   ├── cisco_asa.go              # ASA REST API client
│   │   ├── cisco_fmc.go              # FMC REST API client
│   │   └── netflow.go                # NetFlow v9/IPFIX collector
│   ├── uploader/                     # Encrypted API push
│   └── main.go
│
├── viewer/                           # React diagram viewer (embedded in CLI HTML)
│   └── src/components/
│       ├── DiagramCanvas.tsx         # Canvas view (React Flow)
│       ├── FlowMapCanvas.tsx         # Network topology view
│       ├── CostLensView.tsx          # Cost breakdown view
│       ├── ResourceNode.tsx
│       ├── NetworkPathOverlay.tsx    # Asymmetric path rendering
│       ├── FindingBadge.tsx
│       └── DetailPanel.tsx
│
├── api/                              # FastAPI SaaS backend
│   └── app/
│       ├── routers/                  # Projects, scans, sharing, webhooks
│       ├── services/                 # Business logic
│       └── dc_ingest/                # DC agent data ingestion pipeline
│
├── dashboard/                        # Next.js SaaS frontend
│   └── app/
│       ├── (canvas)/                 # Infrastructure diagram views
│       ├── (flowmap)/                # Network topology views
│       └── (costlens)/               # FinOps views
│
└── .github/workflows/
    ├── cli-release.yml               # Multi-platform CLI binaries
    ├── dc-agent-release.yml          # DC agent binaries
    ├── api-deploy.yml
    └── dashboard-deploy.yml
```

---

## Technology Decision Notes

### DC Agent Language: Go
- Single binary with zero runtime dependencies — critical for DC deployment
- Cross-compiled easily for Linux amd64 (most DC servers)
- Excellent NETCONF library support (`go-netconf`)
- Low memory footprint running as a daemon

### CLI Language: Python
- Fast iteration speed — critical for MVP phase
- HCL parsing libraries exist and are battle-tested
- Rich ecosystem (networkx, pydantic, typer, rich)
- If performance becomes an issue with 500+ resources, the parser can be rewritten in Rust later (the bottleneck will be rendering, not parsing)

### Why React Flow over D3 directly
- Built-in zoom, pan, minimap, node selection
- Custom node components (perfect for cloud resource cards with severity badges)
- Edge routing that avoids overlaps
- Active maintenance and excellent TypeScript support
