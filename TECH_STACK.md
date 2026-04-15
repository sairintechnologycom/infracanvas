# InfraCanvas — Tech Stack v2.0

## CLI & Core Engine

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Language** | Python 3.12+ | Fast iteration speed critical for MVP. HCL/JSON parsing libraries exist and are battle-tested. Excellent ecosystem (networkx, pydantic, typer, rich). |
| **HCL Parser** | `python-hcl2` | Pure Python HCL2 parser, handles most Terraform syntax. |
| **Graph Library** | `networkx` | Resource dependency graph construction, traversal, layout algorithms. |
| **CLI Framework** | `typer` + `rich` | Modern CLI with beautiful terminal output, auto-generated help, progress bars. |
| **Diagram Renderer** | Embedded React SPA (single-file HTML) | Zero-dependency output. Opens in any browser. Emails cleanly. Reaches Alex without Priya explaining how to open it. |
| **Data Models** | `pydantic` v2 | Type-safe resource graph model, JSON serialisation, validation. |
| **Packaging** | `pyinstaller` + `pip` | Distribute as pip package + standalone binary per platform. |
| **Testing** | `pytest` + `ruff` + `mypy` | Unit + integration tests. Type checking enforced from day one. |

### Why Python over Rust/Go for the CLI
- Speed of iteration > execution speed for MVP phase
- HCL parsing libraries already exist and are battle-tested
- If performance becomes critical at 500+ resources, rewrite the parser in Rust (the bottleneck will be rendering, not parsing)
- The domain logic is complex enough that Python's readability matters

---

## DC Collector Agent

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Language** | Go | Single binary with zero runtime dependencies — critical for DC deployment. Cross-compiled for Linux amd64, macOS arm64. Low memory footprint as a daemon. |
| **NETCONF Client** | `go-netconf` | Primary integration for Cisco IOS-XE 16.6+. Structured XML/JSON — no fragile CLI parsing. |
| **SSH Client** | `golang.org/x/crypto/ssh` | Fallback for older IOS versions. CLI output parser for `show ip route`, `show bgp neighbors`. |
| **NetFlow Collector** | `goflow2` | UDP listener for NetFlow v9 and IPFIX. Actual traffic ground truth. |
| **Config** | YAML + environment variables | Simple deployment configuration per DC site. |
| **Distribution** | GitHub Releases (pre-built binaries) | Single binary per platform. Deploy in <30 minutes per DC site. |

### DC Agent Integration Priority
1. **NETCONF/RESTCONF** (IOS-XE 16.6+): Structured data, preferred path
2. **SSH CLI parser** (older IOS): Fallback, fragile but necessary
3. **NetFlow collector**: Confirms actual traffic paths (ground truth vs routing table theory)
4. **Config file import**: Offline fallback — upload `show running-config` output

### Supported Devices at Launch
| Device | Integration Method | Priority |
|--------|------------------|----------|
| Cisco IOS-XE 16.6+ | NETCONF/RESTCONF | Primary |
| Cisco IOS (older) | SSH CLI parser | Fallback |
| Cisco ASA 9.3+ | REST API | Primary |
| Cisco ASA (older) | SSH CLI parser | Fallback |
| Cisco Firepower (FTD) | FMC REST API | Primary (single endpoint) |
| Checkpoint R80+ | Management API | No agent needed |
| Zscaler ZIA/ZPA/ZDX | Cloud API | No agent needed (Phase 5) |
| Palo Alto PAN-OS | REST API | Phase 5 |
| Fortinet FortiGate | REST API | Phase 5 |
| SolarWinds / PRTG / NetBrain | NMS API | Phase 5 |

---

## Security Rules Engine

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Rule format** | YAML definitions | Easy to write, community-contributable for open-source rules |
| **Evaluation** | Custom Python engine | Simple condition matching against resource attributes |
| **Custom policies** | YAML (v1) + OPA/Rego (v2, Phase 5) | YAML for common org standards, Rego for complex enterprise policies |
| **Output** | Pydantic models → JSON | Type-safe, serialisable findings |

```yaml
# Example security rule
- id: SEC-021
  title: "Lambda function running deprecated runtime"
  severity: high
  resource_types: ["aws_lambda_function"]
  condition:
    attribute: "runtime"
    operator: "in"
    values: ["python3.6", "python3.7", "python3.8", "nodejs12.x", "nodejs14.x", "java8"]
  remediation: |
    Update runtime to a supported version:
      runtime = "python3.12"

# Example network finding rule
- id: NET-001
  title: "Static route with no BGP failover"
  severity: critical
  resource_types: ["dc_router"]
  condition:
    type: "static_route_no_backup"
    requires: "dc_collector_data"
  remediation: "Add a floating static route with higher AD or configure BGP advertisement for this prefix as a failover path."
```

---

## Frontend — Diagram Viewer (Embedded in CLI HTML Output)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | React 18 | Component model, hooks, excellent TypeScript support. |
| **Diagram Library** | `@xyflow/react` (React Flow) | Purpose-built for node-edge diagrams. Built-in zoom, pan, minimap, node selection. Custom node components perfect for cloud resource cards. |
| **Network Topology View** | React Flow (custom edge types) | Dual-path rendering (forward + return) with custom edge colouring. |
| **Icons** | Custom SVG cloud resource icons | AWS, Azure service icons (open-source icon sets). |
| **Styling** | Tailwind CSS | Rapid styling, small bundle size. |
| **Bundler** | Vite + `vite-plugin-singlefile` | Fast builds. Single-file HTML output with all JS/CSS inlined. Zero runtime dependencies. |
| **State** | Zustand | Lightweight state management for filters, selections, active view (Canvas/FlowMap/CostLens), panel state. |
| **Layout** | `@dagrejs/dagre` | Hierarchical auto-layout for infrastructure diagrams. |

### View Architecture
The single HTML output contains three views (toggled via tab bar):
1. **Canvas**: Infrastructure diagram (React Flow, resource nodes, group containers)
2. **FlowMap**: Network topology (React Flow, path overlay, DC site containers, firewall nodes)
3. **CostLens**: Cost breakdown (Recharts, cost treemap, shared cost allocation table)

### Why React Flow over D3 directly
- Built-in zoom, pan, minimap, node selection — no reimplementation needed
- Custom node components perfect for cloud resource cards with severity badges
- Edge routing avoids overlaps out of the box
- Active maintenance, strong TypeScript support, excellent documentation

---

## SaaS Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | FastAPI (Python) | Same language as CLI. Async. Auto-generated OpenAPI docs. |
| **ORM** | SQLAlchemy 2.0 + Alembic | Mature async support, migration management. |
| **Database** | Neon PostgreSQL (serverless) | Scales to zero. Built-in connection pooling. Row-level security for team isolation. |
| **Auth** | Clerk | Managed auth, social login, SSO for Enterprise (SAML/OIDC). Generous free tier. |
| **Object Storage** | Cloudflare R2 | S3-compatible. Zero egress fees (critical — scan artifacts will be large). |
| **Cache** | Upstash Redis | Serverless Redis for session store, rate limiting, job queue. |
| **Background Jobs** | `arq` (Redis-based) | Lightweight async task queue for scan processing and webhook handling. |
| **Payments** | Stripe | Subscription billing, usage metering, Customer Portal for self-serve upgrade/downgrade. |
| **Policy Engine** | OPA (Open Policy Agent) | Rego policy evaluation for Enterprise custom policies (Phase 5). |
| **Compliance Mapping** | Internal JSON database | SOC2/HIPAA/PCI-DSS control → finding ID mappings (curated manually). |

---

## SaaS Frontend — Dashboard

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | Next.js 14 (App Router) | SSR for public share pages, RSC for dashboard performance. |
| **UI Library** | shadcn/ui + Tailwind CSS | Polished accessible components. Consistent design system. |
| **Charts** | Recharts | Scan history trends, cost allocation charts, compliance coverage charts. |
| **Diagram Viewer** | Shared React component from `viewer/` | Consistent Canvas + FlowMap + CostLens experience CLI ↔ dashboard. |
| **State** | TanStack Query v5 | Server state management, caching, background refetching. |
| **Forms** | React Hook Form + Zod | Type-safe form validation. |
| **Deployment** | Vercel | Zero-config Next.js hosting, edge functions for share page performance. |

---

## Cloud & Security API Integrations

### AWS
| API | Data Pulled | Used By |
|-----|------------|---------|
| AWS TGW API | Route tables, attachments, VPN connections | FlowMap topology |
| AWS VPC API | Route tables, NACLs, Security Groups, subnets | Canvas + FlowMap |
| AWS CloudWatch | VPC Flow Logs, TGW Flow Logs | Traffic confirmation |
| AWS Cost Explorer | Per-resource cost data with tags | CostLens |
| AWS IAM | Role and policy enumeration | Canvas security rules |
| AWS Lambda API | Function runtime versions | Runtime staleness check |
| AWS EKS API | Cluster versions | Runtime staleness check |

### Azure
| API | Data Pulled | Used By |
|-----|------------|---------|
| Azure vWAN REST API | Hubs, connections, effective routes | FlowMap topology |
| Azure Network Watcher | Effective security rules, next-hop | FlowMap path tracer |
| Azure Monitor | NSG flow logs | Traffic confirmation |
| Azure Cost Management | Per-resource cost with tags | CostLens |
| Azure Resource Manager | All resource enumeration | Canvas + shadow infra |

### Security Platforms (No Agent Required)
| Platform | API | Data Pulled |
|----------|-----|------------|
| Checkpoint R80+ | Management API | Full policy + hit counts, NAT rules, VPN communities |
| Cisco ASA | REST API | Access lists, connection counts, NAT, VPN sessions |
| Cisco FTD | FMC REST API | Policies for all managed devices (single endpoint) |
| Zscaler ZIA | ZIA API | Forwarding rules, traffic logs (Phase 5) |
| Zscaler ZPA | ZPA API | Connector topology, application segments (Phase 5) |
| Zscaler ZDX | ZDX API | Hop-by-hop path traces with backbone segments (Phase 5) |
| SolarWinds | Orion REST API | Network topology, device state (Phase 5) |
| PRTG | PRTG API | Device tree, sensor state (Phase 5) |
| NetBrain | NetBrain REST API | Topology diagrams, path analysis (Phase 5) |
| Palo Alto | PAN-OS REST API | Security policies, NAT rules (Phase 5) |
| Fortinet | FortiGate REST API | Firewall policies, VPN tunnels (Phase 5) |

---

## DevOps & Tooling

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD: CLI releases, DC agent releases, SaaS deployment |
| GitHub Releases | CLI and DC agent binary distribution (multi-platform) |
| PyPI | Python package distribution (`pip install infracanvas`) |
| Homebrew | macOS CLI installation |
| Docker | Local development, CLI container, SaaS self-hosted deployment |
| Helm | Kubernetes deployment chart for self-hosted Enterprise |
| Sentry | Error tracking (CLI + SaaS + DC agent) |
| PostHog | Product analytics (dashboard usage, feature adoption, CLI telemetry opt-in) |
| Plausible | Website analytics (landing page, docs) |

### CLI Telemetry (Opt-in, Anonymous)
- Opt-in on first run: "Help improve InfraCanvas? Share anonymous usage data."
- Tracks: command used, resource count range, provider (aws/azure/both), finding severity counts, output format
- Never tracks: file contents, resource names, attribute values, IP addresses

---

## Monorepo Structure v2.0

```
infracanvas/
├── cli/                              # Python CLI + Core Engine
│   ├── infracanvas/
│   │   ├── main.py                   # Typer CLI entrypoint
│   │   ├── parser/
│   │   │   ├── hcl.py                # HCL parser (aws + azure resource types)
│   │   │   ├── references.py         # Implicit dependency detection
│   │   │   ├── state.py              # .tfstate reader
│   │   │   └── plan.py               # terraform plan JSON reader
│   │   ├── graph/
│   │   │   ├── builder.py            # NetworkX DiGraph construction
│   │   │   ├── models.py             # Pydantic v2 models (v2.0 schema)
│   │   │   └── layout.py             # Dagre + force-directed layout
│   │   ├── security/
│   │   │   ├── engine.py             # Rule evaluation engine
│   │   │   ├── loader.py             # YAML rule loader
│   │   │   ├── models.py             # Finding models
│   │   │   └── rules/
│   │   │       ├── aws/              # AWS security rules (YAML)
│   │   │       └── azure/            # Azure security rules (YAML)
│   │   ├── network/                  # FlowMap engine (CLOSED SOURCE)
│   │   │   ├── topology.py           # Hybrid topology builder
│   │   │   ├── path_tracer.py        # Forward/return path computation
│   │   │   ├── asymmetry.py          # Asymmetric routing detector
│   │   │   ├── capacity.py           # Firewall capacity monitor
│   │   │   ├── findings.py           # Network rule engine (NET-001..012)
│   │   │   └── models.py             # NetworkPath, PathHop, DCReading models
│   │   ├── cloud/                    # Live cloud API clients
│   │   │   ├── aws.py                # AWS boto3 wrappers (read-only)
│   │   │   └── azure.py              # Azure SDK wrappers (read-only)
│   │   ├── cost/
│   │   │   ├── estimator.py          # Per-resource cost estimation
│   │   │   ├── shared.py             # Shared infra cost allocation
│   │   │   └── pricing.py            # Infracost API + static pricing DB
│   │   ├── drift/
│   │   │   ├── analyzer.py           # Plan diff computation
│   │   │   └── shadow.py             # Shadow infra detection (API vs state)
│   │   ├── policy/
│   │   │   ├── engine.py             # YAML policy evaluation
│   │   │   └── rego.py               # OPA/Rego integration (Phase 5)
│   │   ├── runtime/
│   │   │   └── staleness.py          # Runtime EOL version checker
│   │   ├── export/
│   │   │   ├── html.py               # Embed React SPA with graph JSON
│   │   │   ├── json.py               # Raw JSON export
│   │   │   ├── svg.py                # SVG diagram export
│   │   │   └── png.py                # PNG export via headless Chrome
│   │   └── config.py                 # .infracanvas.yml loader
│   ├── tests/
│   │   ├── fixtures/                 # 5 sample Terraform projects (T-P1..T-P5)
│   │   ├── test_parser.py
│   │   ├── test_graph.py
│   │   ├── test_security.py
│   │   ├── test_network.py
│   │   └── test_cost.py
│   └── pyproject.toml
│
├── dc-agent/                         # DC Collector Agent (Go)
│   ├── collectors/
│   │   ├── cisco_netconf.go          # NETCONF/RESTCONF client (IOS-XE 16.6+)
│   │   ├── cisco_ssh.go              # SSH CLI parser fallback
│   │   ├── cisco_asa.go              # Cisco ASA REST API client
│   │   ├── cisco_fmc.go              # Cisco FMC REST API (FTD devices)
│   │   └── netflow.go                # NetFlow v9 / IPFIX collector
│   ├── models/                       # Go structs for DC data
│   ├── uploader/                     # Encrypted TLS push to InfraCanvas API
│   ├── config/                       # YAML config loader
│   ├── main.go                       # Daemon entrypoint
│   └── Makefile                      # Cross-compilation targets
│
├── viewer/                           # React diagram viewer (embedded in CLI HTML)
│   ├── src/
│   │   ├── App.tsx                   # Three-tab layout: Canvas / FlowMap / CostLens
│   │   ├── types.ts                  # TypeScript interfaces (v2.0 schema)
│   │   ├── store.ts                  # Zustand state management
│   │   ├── components/
│   │   │   ├── canvas/
│   │   │   │   ├── DiagramCanvas.tsx # React Flow canvas for infrastructure
│   │   │   │   ├── ResourceNode.tsx  # Custom node: icon + badges + labels
│   │   │   │   ├── GroupNode.tsx     # VPC/subnet container node
│   │   │   │   └── FindingBadge.tsx  # Severity badge overlay
│   │   │   ├── flowmap/
│   │   │   │   ├── FlowMapCanvas.tsx # React Flow canvas for network topology
│   │   │   │   ├── RouterNode.tsx    # DC router node type
│   │   │   │   ├── FirewallNode.tsx  # Firewall node with capacity gauge
│   │   │   │   ├── DCSiteGroup.tsx   # DC site container node
│   │   │   │   └── PathOverlay.tsx   # Dual-path forward/return rendering
│   │   │   ├── costlens/
│   │   │   │   └── CostLensView.tsx  # Cost breakdown + shared allocation table
│   │   │   └── shared/
│   │   │       ├── SummaryBar.tsx    # Top summary bar (all views)
│   │   │       ├── FilterPanel.tsx   # Left sidebar filters
│   │   │       └── DetailPanel.tsx   # Right sidebar resource detail
│   │   ├── icons/                    # AWS + Azure SVG resource icons
│   │   └── hooks/                    # Custom React hooks
│   ├── vite.config.ts
│   └── package.json
│
├── api/                              # FastAPI SaaS backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app + router registration
│   │   ├── routers/
│   │   │   ├── projects.py
│   │   │   ├── scans.py
│   │   │   ├── shares.py
│   │   │   ├── teams.py
│   │   │   ├── webhooks.py
│   │   │   └── dc_collector.py       # DC agent data ingestion
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── services/                 # Business logic
│   │   ├── middleware/               # Auth, rate limiting
│   │   └── dc_ingest/                # DC reading processing pipeline
│   ├── alembic/                      # Database migrations
│   ├── tests/
│   └── pyproject.toml
│
├── dashboard/                        # Next.js 14 SaaS frontend
│   ├── app/
│   │   ├── (auth)/                   # Sign in, sign up
│   │   ├── (dashboard)/              # Protected dashboard routes
│   │   │   ├── projects/
│   │   │   ├── scans/
│   │   │   │   └── [id]/             # Scan detail: Canvas / FlowMap / CostLens tabs
│   │   │   ├── team/
│   │   │   └── settings/
│   │   └── share/
│   │       └── [token]/              # Public share page (no auth, SSR)
│   ├── components/
│   │   ├── viewer/                   # Shared Canvas + FlowMap + CostLens viewer
│   │   └── ui/                       # shadcn/ui components
│   ├── lib/                          # API client, auth helpers
│   └── package.json
│
├── docs/                             # Product + architecture docs
│   ├── PLAN.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   └── TASKS.md
│
├── .github/workflows/
│   ├── cli-release.yml               # Multi-platform CLI binaries on semver tag
│   ├── dc-agent-release.yml          # Multi-platform DC agent binaries on semver tag
│   ├── api-deploy.yml                # FastAPI deploy (Railway/Fly.io)
│   └── dashboard-deploy.yml          # Next.js deploy (Vercel)
│
└── README.md
```

---

## Performance Targets

| Scenario | Target |
|----------|--------|
| Parse + graph + security scan: 100 resources | < 3s |
| Parse + graph + security scan: 500 resources | < 10s |
| FlowMap topology build (cloud APIs only) | < 15s |
| FlowMap with DC agent data | < 20s |
| HTML file size (single-file export) | < 5MB |
| Dashboard scan list load | < 500ms |
| Share page first load (SSR) | < 1s |

---

## Security Architecture Summary

| Concern | Approach |
|---------|---------|
| CLI scan data | Local only. Nothing leaves the machine unless `infracanvas push` is explicit. |
| Cloud credentials | Never stored by InfraCanvas. User provides read-only IAM role/service principal. |
| DC agent communication | Read-only from network. Outbound-only TLS 1.3 push to InfraCanvas API. No inbound ports. |
| DC agent API keys | Per-site scoped keys, separate namespace from project API keys. Stored hashed (SHA-256). |
| SaaS data isolation | Row-level security in PostgreSQL per team. No cross-team data access possible at DB level. |
| Scan artifacts | Encrypted at rest in Cloudflare R2. Signed URLs with short TTL for access. |
| Share links | UUID + random token (32 bytes). Optional bcrypt password. Configurable expiry. |
| Enterprise data residency | Scan artifacts stored in customer-specified R2 bucket (their account). |
| Compliance evidence | Stored encrypted, access audit-logged per control view. |
