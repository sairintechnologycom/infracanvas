# InfraCanvas — Build Roadmap v2.0 (TASKS.md)

## Sprint Structure
- Sprint length: 1 week
- Total timeline: 52 weeks (P0 to P5)
- Goal: Paying pre-sales before writing code, full enterprise platform by end of year

---

## Phase 0: Validate Before Building (Weeks 1–4)
> **Gate: 10 credit cards or 50 strong signals. Zero production code written until passed.**

### T-000: Fake demo + pre-sales (4 weeks)
- [ ] Build fake demo: Gruntwork Terraform repo → Excalidraw diagram with hand-placed security badges
- [ ] Write demo post copy (technical credibility from 20yr cloud background)
- [ ] Post across r/devops, r/Terraform, Terraform Discord, LinkedIn
- [ ] Set up Typeform: role, team size, current toolchain, willingness to pay
- [ ] Set up Stripe founding member page — $49/mo locked forever, ships in 60 days
- [ ] DM every positive responder; run 20 customer conversations minimum
- [ ] Lock buyer persona: Alex (Cloud Architect) buys, Priya (Platform Engineer) installs
- [ ] Document top 5 pain points from conversations — feed into MVP prioritisation
- [ ] Go/No-Go decision at Week 4

**Phase 0 deliverable**: Go/No-Go decision based on evidence, not assumption

---

## Phase 1: Canvas MVP (Weeks 5–10)
> **Goal: CLI v0.1 live, open-source, Show HN launch. AWS only, 3 module levels.**

### T-001: Project scaffolding (2h)
- [ ] Initialise Python project with `pyproject.toml` (Python 3.12+)
- [ ] Set up `typer` CLI skeleton with `scan`, `plan`, `score`, `export`, `serve` commands
- [ ] Configure `pytest`, `ruff`, `mypy`
- [ ] Initialise git repo, .gitignore, LICENSE (MIT for CLI core)
- [ ] Create Pydantic v2 models: `Resource`, `Edge`, `ResourceGraph`, `Finding`, `NetworkFinding`
- [ ] Set up GitHub Actions: lint + test on PR

### T-002: HCL Parser — basic resources (6h)
- [ ] Parse `.tf` files using `python-hcl2`
- [ ] Extract resource blocks: type, name, provider, attributes
- [ ] Support 15 AWS resource types at launch (see supported list below)
- [ ] Handle `variable`, `local`, `output`, `data` blocks
- [ ] Handle multiple `.tf` files in a directory
- [ ] Unit tests: parse 3 sample Terraform projects

**Supported AWS resource types at launch**: `aws_vpc`, `aws_subnet`, `aws_security_group`, `aws_instance`, `aws_s3_bucket`, `aws_rds_instance`, `aws_lb` (ALB), `aws_lambda_function`, `aws_iam_role`, `aws_iam_policy`, `aws_cloudtrail`, `aws_kms_key`, `aws_sqs_queue`, `aws_sns_topic`, `aws_dynamodb_table`

### T-003: HCL Parser — dependencies and modules (4h)
- [ ] Detect explicit dependencies (`depends_on`)
- [ ] Detect implicit dependencies (resource references like `aws_vpc.main.id`)
- [ ] Parse `module` blocks, resolve source paths (local modules only at launch)
- [ ] Build dependency edges in graph
- [ ] Module nesting: max 3 levels deep (hard limit at launch)
- [ ] Unit tests: verify correct edges for complex configs

### T-004: Terraform state reader (3h)
- [ ] Parse `.tfstate` JSON format v4
- [ ] Extract resources with full attributes
- [ ] Map state resources to HCL-declared resources (type.name format)
- [ ] Shadow infra flag: resources in state not matched to HCL
- [ ] Handle remote state (read from local file only for v1)
- [ ] Unit tests: parse sample tfstate files

### T-005: Resource graph builder (3h)
- [ ] Construct `networkx` directed graph from parsed resources
- [ ] Add resource metadata as node attributes
- [ ] Auto-group by VPC/subnet, module, region
- [ ] Export graph as JSON (matching ARCHITECTURE.md schema v2.0)
- [ ] Unit tests: verify graph structure and JSON roundtrip

### T-006: Rule engine framework (4h)
- [ ] YAML rule definition schema (id, title, severity, resource_types, condition, remediation)
- [ ] Rule loader (discover and parse all rules in `rules/` directory)
- [ ] Evaluation engine: match resource type → evaluate condition → emit finding
- [ ] Operators: `equals`, `not_equals`, `in`, `not_in`, `exists`, `not_exists`, `matches`, `gt`, `lt`
- [ ] Finding severity weighting for score calculation
- [ ] Unit tests: engine with 5 test rules

### T-007: AWS security rules — 10 rules for v0.1 (4h)
- [ ] SEC-001: S3 bucket public ACL (`acl` in `["public-read", "public-read-write"]`)
- [ ] SEC-002: Security group 0.0.0.0/0 ingress on port 22, 3389, or any
- [ ] SEC-003: RDS publicly accessible (`publicly_accessible = true`)
- [ ] SEC-004: RDS no encryption (`storage_encrypted = false`)
- [ ] SEC-005: IAM policy with `Action: "*"`
- [ ] SEC-006: IAM policy with `Resource: "*"`
- [ ] SEC-007: CloudTrail not enabled (resource missing)
- [ ] SEC-008: VPC Flow Logs disabled
- [ ] SEC-009: KMS key rotation disabled
- [ ] SEC-010: Untagged resources (missing Name, Environment, Owner)
- [ ] Unit tests per rule: positive and negative cases

### T-008: Score calculator (2h)
- [ ] Infrastructure health score 0–100
- [ ] Weighted penalties: Critical (-15), High (-8), Medium (-3), Info (-1)
- [ ] Score dimensions: Security, Encryption, IAM Hygiene, Cost Efficiency, Tagging
- [ ] Grade: A (90+), B (75+), C (60+), D (45+), F (<45)
- [ ] `infracanvas score ./terraform` → rich terminal output
- [ ] Shareable HTML score card — designed for LinkedIn/Slack sharing

### T-009: Annotate graph with findings (2h)
- [ ] Run rule engine against all resources in graph
- [ ] Attach findings to respective resource nodes
- [ ] Free tier gate: show finding count and severity, hide details/remediation
- [ ] Generate finding summary counts per severity
- [ ] Unit tests: end-to-end scan → annotated graph

### T-010: React viewer scaffolding (3h)
- [ ] Initialise Vite + React + TypeScript project in `viewer/`
- [ ] Install React Flow (`@xyflow/react`), Tailwind CSS, Zustand
- [ ] Configure `vite-plugin-singlefile` for zero-dependency HTML output
- [ ] Create data loading: read embedded JSON from `<script id="graph-data">` tag
- [ ] Set up Zustand store: filters, selections, panel state, active view (Canvas/FlowMap/CostLens)

### T-011: Resource node components (6h)
- [ ] Custom React Flow node: cloud provider icon + resource name + type label
- [ ] Finding severity badge overlay (red/orange/yellow/blue dot with count)
- [ ] Finding count tooltip on hover
- [ ] Drift indicator (green/red/amber border)
- [ ] Shadow infra indicator (dashed border, distinct visual)
- [ ] Runtime staleness indicator
- [ ] Cost label (if available)
- [ ] Selected state with highlight ring
- [ ] Pro-gate overlay on finding details (blurred with "Upgrade to Pro" CTA)

### T-012: Diagram layout and grouping (4h)
- [ ] Auto-layout: dagre hierarchical layout via `@dagrejs/dagre`
- [ ] Group nodes by VPC → subnet → resource (nested group nodes)
- [ ] Group background rectangles with labels (VPC, subnet, module, region)
- [ ] Module boundary indicators
- [ ] Edge rendering: smooth bezier curves, directional arrows
- [ ] Provider icon library (AWS icons for 15 supported types)

### T-013: Interaction panels (4h)
- [ ] Summary bar (top): total resources, findings by severity, cost total, score badge
- [ ] Filter panel (left): filter by resource type, severity, module, region, provider
- [ ] Detail panel (right): click resource → attributes, findings with remediation, cost
- [ ] Finding detail: description, evidence attribute, remediation code snippet
- [ ] Search: find resource by name/type
- [ ] Zoom controls, minimap, fit-to-screen button

### T-014: Build pipeline + CLI integration (3h)
- [ ] Vite build → single HTML file with all JS/CSS inlined
- [ ] `cli/infracanvas/export/html.py`: inject graph JSON into HTML template
- [ ] `infracanvas scan ./terraform` → opens browser with diagram
- [ ] `infracanvas scan ./terraform -o report.html` → saves HTML file
- [ ] Test end-to-end with 3 sample Terraform projects

### T-015: Open-source release + launch (4h)
- [ ] PyPI package: `pip install infracanvas`
- [ ] Homebrew formula for macOS
- [ ] GitHub repo public with MIT license (parser + viewer + icon library only)
- [ ] README.md: quick start, demo GIF, screenshots, comparison table
- [ ] CONTRIBUTING.md: how to add custom rules
- [ ] GitHub Actions: auto-publish to PyPI on semver tag
- [ ] Record terminal demo GIF with `asciinema`
- [ ] Write and post Show HN submission (lead with Report Card mechanic)

**Phase 1 deliverable**: `infracanvas scan ./terraform` → interactive HTML. `infracanvas score` → shareable score card. Open-source repo live. Show HN launched.

---

## Phase 2: Canvas v1.0 (Weeks 11–18)
> **Goal: Drift, cost, Azure, shadow infra, runtime staleness, custom policies. Pro tier fully unlocked.**

### T-016: Terraform plan reader (4h)
- [ ] Parse `terraform show -json planfile` output
- [ ] Extract resource changes: create, update, delete, no-op
- [ ] Map changes to resource graph nodes
- [ ] Detect attribute-level changes (before/after values)
- [ ] Unit tests with sample plan JSON

### T-017: Drift visualisation (3h)
- [ ] Colour-code nodes: green (added), red (deleted), amber (changed), grey (unchanged)
- [ ] "Changes" panel listing all drifted resources with change summary
- [ ] Click changed resource → before/after attribute diff view
- [ ] Summary: "3 added, 1 changed, 0 deleted"
- [ ] `infracanvas plan ./terraform --planfile=plan.json`

### T-018: Shadow infrastructure detection (3h)
- [ ] Live AWS API read (with read-only IAM role)
- [ ] Compare API-discovered resources vs Terraform state
- [ ] Flag resources in cloud but not in Terraform as `is_shadow: true`
- [ ] Visual indicator: dashed border, "Shadow" badge on node
- [ ] Finding: shadow resource with resource type, ID, region, estimated cost
- [ ] `infracanvas scan ./terraform --live` flag to enable live API

### T-019: Cost estimator (4h)
- [ ] Infracost pricing API integration (free tier)
- [ ] Fallback: static pricing JSON for top 20 AWS resource types
- [ ] Estimate from resource type + key attributes (instance type, storage size, AZ count)
- [ ] Cost per resource, per group (VPC/subnet/module), total
- [ ] Cost delta on plan changes: "+$340/mo from these changes"
- [ ] Display on resource nodes and summary bar

### T-020: AWS security rules expansion (4h)
Rules 11–30 (closed-source, Pro tier):
- [ ] SEC-011: S3 bucket no server-side encryption
- [ ] SEC-012: S3 bucket no versioning
- [ ] SEC-013: ALB no WAF attached
- [ ] SEC-014: EC2 no IMDSv2 enforced
- [ ] SEC-015: SNS topic not encrypted
- [ ] SEC-016: SQS queue not encrypted
- [ ] SEC-017: EBS volume unencrypted
- [ ] SEC-018: RDS no automated backups
- [ ] SEC-019: RDS no Multi-AZ
- [ ] SEC-020: Lambda function no VPC
- [ ] SEC-021: Lambda function deprecated runtime (EOL)
- [ ] SEC-022: EKS cluster old version (< N-1 of current)
- [ ] SEC-023: CloudFront no WAF
- [ ] SEC-024: ALB no HTTPS listener
- [ ] SEC-025: IAM user with console access and no MFA
- [ ] SEC-026: Secrets Manager secret not rotated
- [ ] SEC-027: ECR repository no scanning on push
- [ ] SEC-028: ElasticSearch/OpenSearch public endpoint
- [ ] SEC-029: DynamoDB table no point-in-time recovery
- [ ] SEC-030: ACM certificate expiring within 30 days
- [ ] Unit tests per rule

### T-021: Azure parser — 10 core resource types (6h)
- [ ] `azurerm_virtual_network` (maps to aws_vpc)
- [ ] `azurerm_subnet` (maps to aws_subnet)
- [ ] `azurerm_network_security_group` (maps to aws_security_group)
- [ ] `azurerm_virtual_machine` / `azurerm_linux_virtual_machine`
- [ ] `azurerm_storage_account` (maps to aws_s3_bucket)
- [ ] `azurerm_kubernetes_cluster` (maps to aws_eks_cluster)
- [ ] `azurerm_app_service` / `azurerm_linux_web_app`
- [ ] `azurerm_sql_server` + `azurerm_mssql_database`
- [ ] `azurerm_key_vault`
- [ ] `azurerm_application_gateway` (maps to aws_lb)
- [ ] Azure resource icons in viewer
- [ ] Unit tests: parse Azure Terraform project

### T-022: Azure security rules (4h)
- [ ] AZ-001: Storage account public blob access enabled
- [ ] AZ-002: Storage account no HTTPS-only
- [ ] AZ-003: NSG allows any inbound (0.0.0.0/0 on sensitive ports)
- [ ] AZ-004: SQL server no Azure AD admin configured
- [ ] AZ-005: Key Vault no soft delete + purge protection
- [ ] AZ-006: AKS cluster old version
- [ ] AZ-007: App Service no HTTPS-only
- [ ] AZ-008: App Service no authentication enabled
- [ ] AZ-009: Storage account no encryption at rest
- [ ] AZ-010: VM no disk encryption

### T-023: Runtime staleness checks (3h)
- [ ] Maintain versioned "current supported runtimes" database (JSON, updated weekly)
- [ ] Lambda: Python, Node.js, Java, Go — flag EOL runtimes
- [ ] Azure Functions: Node.js, Python, .NET — flag EOL runtimes
- [ ] EKS: flag clusters running < N-2 of current Kubernetes version
- [ ] AKS: same as EKS
- [ ] Resource lock validation: check `azurerm_management_lock` and AWS resource policies for lock presence
- [ ] Visual indicator: orange warning badge on stale resources

### T-024: Custom policy engine v1 (4h)
- [ ] YAML policy definition schema (org-specific rules)
- [ ] Supported checks: required_tags, allowed_regions, allowed_instance_types, naming_pattern, required_attributes
- [ ] `.infracanvas.yml` config file at project root
- [ ] `--policy ./policies/` flag for external policy directory
- [ ] Finding type: POLICY-xxx (distinct from security SEC-xxx)
- [ ] Unit tests: 5 sample org policies

### T-025: CLI polish + CI mode (3h)
- [ ] `--ci` mode: JSON to stdout, exit code based on finding severity threshold (e.g. `--fail-on=critical`)
- [ ] `--watch` mode: re-scan on `.tf` file changes
- [ ] `--ignore` flag: skip specific rule IDs
- [ ] `--severity` flag: only show findings at or above threshold
- [ ] Progress bars and spinner with `rich`
- [ ] Error handling: helpful messages for missing `.tf` files, parse errors, API auth failures
- [ ] `--quiet` flag: JSON only, no terminal UI

### T-026: Docker image + distribution (2h)
- [ ] `Dockerfile` for CLI: `docker run infracanvas scan ./terraform`
- [ ] GitHub Releases: pre-built binaries (Linux amd64, macOS arm64, Windows x64) via PyInstaller
- [ ] GitHub Actions: `cli-release.yml` — build + publish on semver tag
- [ ] Update Homebrew formula for new version

### T-027: Documentation (3h)
- [ ] docs/: installation guide, CLI reference, all security rules, policy engine, configuration
- [ ] Update README: Azure support, shadow infra, runtime checks, cost overlay
- [ ] Record updated demo GIF showing v1.0 features
- [ ] Publish "Terraform Anti-Patterns #1" blog post using InfraCanvas diagram as visual

**Phase 2 deliverable**: Full Canvas with AWS + Azure, drift, cost, shadow infra, runtime staleness, custom policies. Pro tier ($79/mo) fully unlocked.

---

## Phase 3: FlowMap v1.0 (Weeks 19–28)
> **Goal: Hybrid network topology + asymmetric routing detector + DC collector agent. Team tier unlocked.**

### T-028: FlowMap data model (3h)
- [ ] Pydantic models: `NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding`
- [ ] Extend `ResourceGraph` JSON schema: `network_paths`, `dc_sites`
- [ ] NetworkFinding rule IDs: NET-001 through NET-012
- [ ] Path hop types: tgw, vpc, customer_gateway, dc_router, azure_hub, azure_vnet, firewall
- [ ] Unit tests: model serialisation roundtrip

### T-029: AWS network topology collection (5h)
- [ ] AWS TGW route tables (all route domains) via `describe-transit-gateway-route-tables`
- [ ] TGW attachments (VPC, VPN, Direct Connect) via `describe-transit-gateway-attachments`
- [ ] Customer Gateway configurations and VPN connections
- [ ] VPC route tables and routes (all route tables per VPC)
- [ ] AWS Network ACLs (inbound + outbound rules per subnet)
- [ ] Direct Connect virtual interfaces and connection state
- [ ] CloudWatch: VPC Flow Logs, TGW flow logs (for traffic confirmation)
- [ ] Unit tests: mock AWS responses → topology model

### T-030: Azure network topology collection (5h)
- [ ] Azure Virtual WAN hubs and connections via REST API
- [ ] Azure Secure Hub effective routes (all route tables)
- [ ] vNet peering topology
- [ ] Azure Network Watcher: effective security rules, next-hop computation
- [ ] NSG effective rules per NIC and subnet
- [ ] ExpressRoute circuit and connection state
- [ ] Azure Monitor: NSG flow logs (for traffic confirmation)
- [ ] Unit tests: mock Azure responses → topology model

### T-031: Checkpoint Management API integration (4h)
- [ ] Authenticate: `POST /web_api/login` → session token
- [ ] Pull full access rule base with hit counts: `show-access-rulebase`
- [ ] Pull NAT rule base: `show-nat-rulebase`
- [ ] Pull VPN communities: `show-vpn-communities`
- [ ] Pull network objects: `show-network-objects`
- [ ] Map Checkpoint objects to FlowMap topology nodes
- [ ] NET-007, NET-008, NET-009 findings from Checkpoint data
- [ ] Unit tests: mock API responses → findings

### T-032: DC Collector Agent — Cisco Router (10h)
- [ ] Go project scaffold with `cobra` CLI and daemon mode
- [ ] NETCONF/RESTCONF client (`go-netconf` library) for IOS-XE 16.6+
  - [ ] Pull full RIB: static + BGP + connected routes
  - [ ] Pull BGP neighbor state and advertised/received prefixes
  - [ ] Pull VRF route tables per VRF instance
  - [ ] Pull interface state and IP assignments
- [ ] SSH CLI fallback parser for older IOS
  - [ ] `show ip route` → static and connected routes
  - [ ] `show bgp neighbors` → peer state + AS paths
  - [ ] `show ip bgp` → full BGP table
- [ ] NetFlow v9 / IPFIX collector (UDP listener)
  - [ ] Parse flow records: src/dst IP, bytes, packets, protocol
  - [ ] Aggregate by source-destination pair per 30s window
- [ ] Encrypted API push to InfraCanvas cloud (`/api/v1/dc-collector/readings`)
- [ ] Daemon mode: route tables every 5min, BGP every 1min, NetFlow every 30s
- [ ] Config file import fallback: parse Cisco IOS `show running-config` for static routes
- [ ] Single binary output (Linux amd64 primary, macOS arm64 secondary)
- [ ] Unit tests: mock NETCONF responses, SSH CLI output parsing

### T-033: DC Collector Agent — Cisco ASA + FTD (6h)
- [ ] ASA REST API client (ASA 9.3+)
  - [ ] Access lists with hit counts
  - [ ] NAT rules and translations
  - [ ] Connection count (current vs max) → NET-007 capacity finding
  - [ ] Active VPN sessions
  - [ ] `show asp drop` data (dropped packets by reason)
- [ ] Cisco FMC REST API client
  - [ ] Authenticate and enumerate managed FTD devices
  - [ ] Pull access control policies per device
  - [ ] Pull NAT policies
  - [ ] Pull connection events (last 24h)
- [ ] SSH CLI fallback for ASA (older versions without REST API)
- [ ] Unit tests: mock API responses → findings

### T-034: Path tracer engine (6h)
- [ ] Forward path computation: start at AWS TGW → follow LPM at each hop → traverse DC (via collector agent data) → arrive Azure
- [ ] Return path computation: start at Azure vWAN → follow LPM → traverse DC → arrive AWS
- [ ] BGP/static boundary identification: mark each hop as `bgp` or `static` routing type
- [ ] NetFlow correlation: confirm paths with actual traffic data from collector agent
- [ ] Zscaler ZIA stub: mark traffic matching ZIA forwarding rules as "intercepted"
- [ ] Unit tests: known topology → expected forward/return path

### T-035: Asymmetric routing detector (5h)
- [ ] Compare forward and return path hop-by-hop
- [ ] Divergence detection: first hop where paths differ
- [ ] Root cause classifier:
  - [ ] BGP attribute difference: AS path length, MED, local preference
  - [ ] Static route mismatch: same prefix, different next-hop
  - [ ] NAT asymmetry: NAT on forward path, not on return
- [ ] Impact assessment: stateful firewall on one path only → CRITICAL finding (NET-010)
- [ ] Finding generation: NET-001 through NET-006 from path analysis
- [ ] Unit tests: asymmetric topology → correct divergence point + root cause

### T-036: FlowMap viewer components (6h)
- [ ] `FlowMapCanvas.tsx`: dedicated network topology view (separate tab in viewer)
- [ ] `NetworkPathOverlay.tsx`: dual-colour path rendering (blue = forward, orange = return)
- [ ] Divergence point marker: red pulsing indicator with tooltip explanation
- [ ] DC site group nodes: dashed border containers for physical DC nodes
- [ ] Router node type: distinct icon for Cisco router vs firewall vs cloud gateway
- [ ] Firewall capacity gauge: mini progress bar on firewall nodes (capacity %)
- [ ] Stale rule badge: grey indicator on firewalls with stale rules
- [ ] FlowMap-specific filter panel: filter by routing type, path health, finding type
- [ ] Network path detail panel: step-by-step hop list with routing type per hop

### T-037: FlowMap-specific network findings (3h)
- [ ] NET-001 through NET-012 rule engine
- [ ] Static route no failover detection logic
- [ ] Stale static route: cross-reference next-hop against cloud routing state
- [ ] Undocumented static: cross-reference DC router routes against Terraform state
- [ ] Route change alerting: compare current route tables to last scan baseline
- [ ] BGP withdrawal detection: peer state change + prefix withdrawal
- [ ] Unit tests per finding type

### T-038: SaaS backend — Phase 3 additions (4h)
- [ ] DC Collector Agent API endpoints (`/api/v1/dc-collector/readings`)
- [ ] Per-DC-site API key management (separate namespace from project keys)
- [ ] DC reading storage in PostgreSQL with time-series indexing
- [ ] Network path storage in scan artifacts (R2)
- [ ] Route change alerting: compare to previous scan baseline
- [ ] Webhook: send alert to Slack/Teams on NET-001, NET-010 (critical network findings)

### T-039: Team tier launch (2h)
- [ ] Feature gating: FlowMap behind Team/Enterprise tier check
- [ ] Team tier Stripe product + price ($299/mo)
- [ ] Upgrade CTA in viewer: "FlowMap requires Team tier"
- [ ] Update landing page + pricing page

**Phase 3 deliverable**: FlowMap live. Hybrid topology + asymmetric routing detection + firewall capacity. DC Collector Agent distributed as binary. Team tier ($299/mo) unlocked. Hero scenario: Singapore–Australia East diagnosis in 30s.

---

## Phase 4: SaaS Dashboard + CostLens (Weeks 29–38)
> **Goal: Team workspace, scan history, shareable links, shared infra cost allocation. $19,750 MRR target.**

### T-040: FastAPI backend — core SaaS (6h)
- [ ] Project CRUD: create, list, update, archive
- [ ] Scan upload and retrieval
- [ ] Clerk auth integration (JWT validation middleware)
- [ ] Neon PostgreSQL + Alembic migrations
- [ ] Cloudflare R2 artifact storage (scan JSON + HTML upload/download)
- [ ] API key management: create, list, revoke (scoped per project)
- [ ] Rate limiting via Upstash Redis

### T-041: FastAPI backend — team features (4h)
- [ ] Team CRUD: create team, invite members (email invite via Clerk)
- [ ] Role-based access: owner, admin, member, viewer
- [ ] Team resource isolation: row-level security in PostgreSQL
- [ ] Subscription status check via Stripe webhooks

### T-042: Scan history + comparison (3h)
- [ ] Scan timeline per project (list with metadata: score, resource count, finding counts, cost, date)
- [ ] Point-in-time scan retrieval (load any historical scan artifact)
- [ ] Side-by-side comparison: two scans → diff of findings, resources, cost
- [ ] PDF export of comparison report

### T-043: Share link system (3h)
- [ ] Share link creation: UUID + random token, optional password, configurable expiry
- [ ] Public share endpoint (no auth required): `GET /api/v1/shares/:token`
- [ ] Password-protected share: bcrypt hash comparison
- [ ] Embedded viewer: full Canvas + FlowMap + CostLens (read-only, no login)
- [ ] Share link management (list, revoke)

### T-044: CI/CD webhook (3h)
- [ ] Webhook endpoint: `POST /api/v1/webhooks/scan`
- [ ] Support: GitHub, GitLab, Bitbucket push events
- [ ] Trigger auto-scan on push to configured branch
- [ ] Background job processing via `arq` (Redis-based queue)
- [ ] Slack/Teams notification on new Critical findings
- [ ] Scan status badge endpoint for README

### T-045: CostLens — shared infrastructure cost allocation (6h)
- [ ] AWS Cost Explorer API integration: per-resource cost data with tags
- [ ] Azure Cost Management API integration: per-resource cost data
- [ ] TGW attachment cost attribution: map attachment ARN → workload → team via resource tags
- [ ] Azure Secure Hub data processing cost: attribute by source CIDR/workload
- [ ] ExpressRoute / Direct Connect port fees: split by connected VNet/VPC count
- [ ] Azure Firewall throughput cost: overlay on FlowMap traffic volumes from collector agent
- [ ] Unit tests: cost attribution logic

### T-046: CostLens — cross-cloud and per-path cost (4h)
- [ ] AWS → Azure data transfer cost: match flow data from NetFlow to AWS Cost Explorer egress line items
- [ ] Per-path cost comparison: calculate cost of forward path vs alternative paths
- [ ] "Rerouting saves $X/month" recommendation engine
- [ ] Idle resource detection: resources with no traffic in 30 days (from Flow Logs / NetFlow)
- [ ] Oversized instance recommendations: utilisation < 20% for 14 days

### T-047: Next.js dashboard — layout and navigation (4h)
- [ ] App Router structure: `/dashboard`, `/projects/:id`, `/scans/:id`, `/team`, `/settings`
- [ ] Sidebar navigation: Projects, Scans, Team, Settings, Billing
- [ ] Project list view with last scan summary cards
- [ ] Clerk authentication integration (sign-in, sign-up, session management)
- [ ] Dark/light mode toggle

### T-048: Next.js dashboard — project and scan views (4h)
- [ ] Project view: scan history timeline, last scan summary, quick stats
- [ ] Scan detail view: embedded Canvas viewer (shared React component from `viewer/`)
- [ ] FlowMap tab in scan detail view
- [ ] CostLens tab in scan detail view (cost breakdown + shared cost allocation table)
- [ ] Scan comparison view (two-scan diff)

### T-049: Next.js dashboard — team management (3h)
- [ ] Team settings: name, plan badge, usage summary (scan count, project count)
- [ ] Member management: invite (email), list, change role, remove
- [ ] API key management UI (create, copy, revoke)
- [ ] Billing: current plan, usage, upgrade flow (Stripe Customer Portal)

**Phase 4 deliverable**: Full SaaS platform. Team workspace + CostLens shared cost allocation + scan history + shareable links. $30,750 MRR target becomes achievable.

---

## Phase 5: Enterprise Moat (Weeks 39–52)
> **Goal: Compliance, Zscaler ZPA/ZDX, NMS integrations, self-hosted, troubleshooting wizard. $999+/mo Enterprise tier.**

### T-050: Compliance framework engine (8h)
- [ ] Compliance mapping database: SOC2, HIPAA, PCI-DSS controls → InfraCanvas finding IDs
- [ ] Compliance scan mode: `infracanvas score --compliance=soc2`
- [ ] Control coverage report: which controls are satisfied, which have gaps
- [ ] Evidence export: PDF report with finding evidence per control (for auditor submission)
- [ ] Remediation roadmap: prioritised list of fixes to achieve compliance target
- [ ] Unit tests: control mapping accuracy

### T-051: SSO + audit logs (4h)
- [ ] Clerk Enterprise: SAML 2.0 + OIDC provider configuration
- [ ] Audit log table: all actions logged with user, timestamp, IP, action, resource
- [ ] Audit log API: paginated retrieval, filtering by user/action/date
- [ ] Audit log export (CSV, PDF)
- [ ] Data residency: scan artifact storage in customer-specified region (R2 custom bucket)

### T-052: Custom policy engine v2 — Rego (5h)
- [ ] OPA (Open Policy Agent) integration for Rego policy evaluation
- [ ] Policy bundle upload: `.rego` files packaged as policy bundles
- [ ] Team-namespaced policy sets (different policies per team or environment)
- [ ] Policy test framework: unit tests against sample resources
- [ ] Policy violation finding type: CUSTOM-xxx (distinct namespace)

### T-053: Self-hosted deployment (5h)
- [ ] Docker Compose file: all services (api, dashboard, worker, postgres, redis)
- [ ] Helm chart for Kubernetes deployment
- [ ] Environment variable configuration (no hardcoded values)
- [ ] Air-gapped mode: offline pricing DB, no external API calls except to customer cloud accounts
- [ ] Migration guide: cloud-hosted → self-hosted
- [ ] Health check endpoints for all services

### T-054: GitHub PR Bot (5h)
- [ ] GitHub App registration and OAuth
- [ ] Webhook receiver: `pull_request` events (opened, synchronize)
- [ ] PR scan trigger: clone branch, run `infracanvas plan`, compare to base
- [ ] PR comment: diagram diff preview (PNG), security finding delta, cost delta
- [ ] Status check: block merge if Critical findings introduced
- [ ] GitHub Marketplace listing

### T-055: NMS integrations (6h)
- [ ] SolarWinds API: pull network topology, device list, interface state
- [ ] PRTG API: pull device tree, sensor state, network topology
- [ ] NetBrain API: pull topology diagrams, device data, path analysis
- [ ] NMS data → DC topology model (avoids agent deployment where NMS exists)
- [ ] Fallback priority: NMS > DC Agent > Config file import

### T-056: Palo Alto and Fortinet NVA support (4h)
- [ ] Palo Alto PAN-OS REST API: security policies, NAT rules, threat profiles
- [ ] Fortinet FortiGate REST API: firewall policies, VPN tunnels, interfaces
- [ ] Map NVA rules to NET-007, NET-008, NET-009 capacity findings
- [ ] VPN tunnel topology for both vendors

### T-057: Zscaler ZPA + ZDX integration (6h)
- [ ] ZPA API: connector topology, application segments, policy rules
- [ ] Map ZPA connectors inside AWS/Azure to diagram nodes
- [ ] ZPA policy: which application segments route through which connectors
- [ ] ZDX API: hop-by-hop path traces for active sessions
- [ ] Integrate ZDX data into FlowMap path tracer (adds Zscaler backbone hops)
- [ ] Asymmetric routing detector: Zscaler interception as a new divergence root cause type
- [ ] Finding: "Forward traffic intercepted by ZPA connector in ap-southeast-1, exiting via Tokyo PoP; return traffic bypassed ZPA entirely via direct BGP path"
- [ ] Unit tests: ZPA topology → path model, ZDX trace → hop model

### T-058: Network troubleshooting wizard (6h)
- [ ] UI: "Why can't X reach Y?" interactive prompt in FlowMap view
- [ ] Source/destination selector: pick any two resources from diagram
- [ ] Trace engine sequence: Security Groups → NACLs → Route Tables → Firewall Rules (Checkpoint/ASA/FTD) → ZPA policies
- [ ] Blocker identification: first rule/hop that would block the traffic
- [ ] Explanation: "Traffic from aws_instance.web to azurerm_sql_server.prod is blocked at Step 3: Security Group sg-abc123 has no outbound rule for port 1433 to 10.200.0.0/16"
- [ ] Remediation suggestion: specific Terraform change to fix the blocker
- [ ] `infracanvas trace --from=aws_instance.web --to=azurerm_sql_server.prod`

### T-059: Enterprise tier launch (2h)
- [ ] Enterprise Stripe product + price ($999+/mo — custom negotiated)
- [ ] Enterprise feature gating (compliance, SSO, Zscaler, NMS, self-hosted, troubleshooting wizard)
- [ ] SLA documentation (4hr response, named contact)
- [ ] Enterprise inquiry form on landing page

**Phase 5 deliverable**: Enterprise tier live. Compliance evidence generation. Zscaler ZPA/ZDX complete picture. Network troubleshooting wizard. Self-hosted option. The moat is built.

---

## Parallel Track: 5 Sample Terraform Projects (Weeks 5–8)

Used for testing, documentation, and demo purposes throughout all phases.

### T-P1: Simple VPC (Week 5)
- VPC, 2 subnets, security group, EC2 instance, RDS, S3 bucket
- Intentionally includes: public S3 ACL, open SG port 22, unencrypted RDS
- Expected: 3 Critical, 2 High findings

### T-P2: Multi-tier web app (Week 6)
- VPC, public/private subnets, ALB, 2 EC2 instances, RDS Multi-AZ, ElasticCache, S3
- Modules: networking, compute, database
- Expected: 1 Critical, 4 High, 8 Medium

### T-P3: Microservices on EKS (Week 7)
- VPC, EKS cluster, ECR repos, RDS, ElasticSearch, SQS, SNS, Lambda functions
- Multiple modules, 3 levels deep
- Expected: 2 Critical, 6 High, 15 Medium

### T-P4: Multi-region active-passive (Week 8)
- 2 regions, TGW, VPN connections, Route53 failover, S3 replication
- Tests: cross-region dependency detection, TGW topology
- Expected: Full FlowMap topology rendered

### T-P5: AWS + Azure hybrid (Week 19)
- AWS VPC (ap-southeast-1) + Azure VNet (australiaeast)
- TGW, Customer Gateway, vWAN, Secure Hub
- Intentionally asymmetric routing to test FlowMap
- Expected: NET-003 finding (static/BGP asymmetry), full hybrid topology

---

## Priority Matrix

| Task | Impact | Effort | Phase | Priority |
|------|--------|--------|-------|---------|
| Pre-sales validation | Critical | Low | P0 | P0 |
| HCL Parser | Critical | Medium | P1 | P0 |
| Security Rules Engine | Critical | Medium | P1 | P0 |
| Diagram Viewer | Critical | High | P1 | P0 |
| Report Card (viral) | High | Low | P1 | P0 |
| Drift Detection | High | Medium | P2 | P1 |
| Azure Parser | High | Medium | P2 | P1 |
| Shadow Infra Detection | High | Medium | P2 | P1 |
| Custom Policy Engine | Medium | Medium | P2 | P1 |
| FlowMap Topology | Critical | High | P3 | P1 |
| Asymmetric Routing Detector | Critical | High | P3 | P1 |
| DC Collector Agent (Cisco) | Critical | High | P3 | P1 |
| Checkpoint API Integration | High | Medium | P3 | P1 |
| SaaS Dashboard | High | High | P4 | P2 |
| CostLens Shared Cost | High | Medium | P4 | P2 |
| Compliance Frameworks | High | High | P5 | P2 |
| Zscaler ZPA/ZDX | High | Medium | P5 | P2 |
| Troubleshooting Wizard | High | High | P5 | P2 |
| NMS Integrations | Medium | Medium | P5 | P3 |
| Self-hosted Deployment | Medium | High | P5 | P3 |
| PR Bot | Medium | Medium | P5 | P3 |
