# Feature Landscape

**Domain:** Hybrid Cloud Infrastructure Intelligence Platform
**Researched:** 2026-04-15
**Confidence:** MEDIUM-HIGH — verified against competitor documentation, official cloud provider docs, and analyst sources. Prior Canvas-only research preserved in "Canvas SaaS" section; new sections cover FlowMap, CostLens, and Enterprise compliance.

---

## Competitive Landscape Context

InfraCanvas competes across three overlapping market segments simultaneously:

**IaC Visualization / SaaS layer**
- Brainboard — visual Terraform design + code generation. Bi-directional: diagram → HCL. Execution-capable. Checkov + TFSec + OPA embedded in CI pipeline.
- Pluralith — read-only Terraform plan visualization. PR comment diagrams with drift highlighting and Infracost cost data. No security rules; pure visualization.
- Hava.io — live cloud import (no IaC required), auto-generated diagrams from AWS/Azure/GCP APIs. Strong versioning. Security group visualization. No IaC-level rules.
- Cloudcraft — design-time diagram tool, AWS-focused. Manual. Better initial design UX than Hava. Limited security group visibility.

**Hybrid Network / NOC layer**
- NetBrain — enterprise network automation platform. Digital Twin (L2/L3/overlay/underlay). Path tracing with hop-by-hop visualization. Asymmetric routing detection via golden-path comparison. ITSM/NPM/SIEM data overlay on topology maps. $100K+ ACV.
- Tufin — firewall policy management + network topology. End-to-end path analysis across on-prem, hybrid, multi-cloud. Focus on security policy rather than architecture.
- Kentik — flow-based network observability. Strong BGP + hybrid cloud traffic analysis. Per-path cost insight exists but is secondary.

**CSPM / Compliance layer**
- Wiz (Google-acquired, 2025) — CNAPP. Agentless. Full graph-based cloud inventory with attack path analysis. Gold standard for security context graphs.
- Prisma Cloud (Palo Alto) — CSPM + IaC scanning. Compliance frameworks built in. Bridgecrew (now integrated) handles IaC gate.
- Prowler — open-source CSPM. 400+ AWS checks. CIS/NIST/SOC2/PCI-DSS mappings. Evidence export.

**Key positioning:** InfraCanvas occupies an unoccupied intersection: **IaC-first + hybrid topology + shared cost allocation** in a single CLI-driven tool at sub-$1K/month price points. NetBrain/Tufin require enterprise procurement. Wiz/Prisma require credential handover. Brainboard/Pluralith are IaC-only, no network layer.

---

## Feature Categories by Product

---

## CANVAS — IaC Visualization + Security

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Interactive diagram from IaC (pan, zoom, search, filter) | Every diagram tool provides this; static output is not a product | LOW | Already exists in ReactFlow viewer |
| Resource grouping (VPC, subnet, region, module) | Flat resource lists are unreadable at 50+ resources; grouping is expected | MEDIUM | Already implemented |
| Security findings with severity badges on diagram nodes | Overlaying findings on the diagram rather than a separate list is the core UX; users expect annotation directly on the resource | LOW | Already implemented |
| Drift detection overlay (plan diff visualization) | "What will change?" is the #1 question before `terraform apply`; visual diff is table stakes | MEDIUM | Already implemented via plan JSON |
| Shadow infrastructure detection (live AWS vs IaC state) | CSPM tools have normalized this expectation; un-managed resources are a security risk | HIGH | Active in Phase 2 |
| Per-resource cost estimation | Infracost has made inline cost annotation expected; cloud architects need budget context during planning | MEDIUM | Already implemented (us-east-1); multi-region in Phase 2 |
| Multi-region cost estimation | Single-region cost display is obviously incomplete for real infra | MEDIUM | Active in Phase 2 |
| Security score card with category grades | Score cards create accountability; letter grades communicate posture to non-technical stakeholders | LOW | Already implemented |
| CI/CD mode (exit codes, JSON output) | If a tool can't integrate with GitHub Actions, it doesn't exist for modern teams | LOW | Already implemented |
| Azure support alongside AWS | Target market is hybrid; AWS-only reads as incomplete | HIGH | Active in Phase 2 |
| Single-file HTML export (shareable, embeddable) | Email-safe sharing of infra diagrams is a real workflow need | LOW | Already implemented |
| Persistent shareable diagram links (SaaS) | Ad-hoc share via email is insufficient; teams need persistent, access-controlled URLs | MEDIUM | Phase 4 SaaS |
| Scan history with timeline (SaaS) | Without history, the SaaS is a file viewer; users expect to replay past states | MEDIUM | Phase 4 SaaS |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side scan comparison (visual diff) | Text diffs of `terraform plan` are unreadable; visual side-by-side diff of two diagram states is unique among competitors | HIGH | Requires 2+ stored scans; Phase 4 |
| Custom policy engine (YAML v1, OPA/Rego v2) | Teams have naming conventions, tag requirements, and regional restrictions that built-in rules can't cover | HIGH | YAML v1 in Phase 2; OPA v2 in Phase 5 |
| Runtime staleness checks (Lambda EOL, EKS version lag) | Runtime hygiene misses are a real enterprise pain; no competitor does IaC-layer runtime version checking | MEDIUM | Active in Phase 2 |
| Security trend over time (score history chart) | "Are we getting more secure?" — security managers track this; competitors show point-in-time snapshots only | MEDIUM | Phase 4 SaaS |
| PR bot (diagram diff + security delta as PR comment) | Pluralith does diagram in PR; adding security delta (new findings, resolved findings, score change) is a clear differentiator | HIGH | Phase 5 — requires GitHub App |
| Resource lock validation | Protecting critical resources from accidental deletion is a compliance requirement; not offered by visualization competitors | LOW | Phase 2 |
| CIS/NIST/SOC2 rule tag mapping (compliance annotations) | Security engineers need to map findings to audit frameworks; competitors charge enterprise pricing for this | HIGH | Phase 5 |

### Anti-Features

| Anti-Feature | Why Requested | Why to Avoid | What to Do Instead |
|--------------|---------------|--------------|-------------------|
| Terraform plan execution in SaaS | "Just run apply for me" | State locking, blast-radius, approval workflows — months of work; Terraform Cloud / Spacelift do this better | Stay read-only; link to execution tools |
| Live cloud import without IaC | "Show me what's actually running" | Requires credential storage in SaaS, IAM role per customer, massive security liability | Shadow detection via plan JSON covers the gap |
| GCP support | "We use Google Cloud too" | Different resource models, security rule set, pricing API — triples maintenance burden | Defer to v4.0 Year 2 |
| Pulumi / CDK / Bicep support | "We don't use Terraform" | Different ASTs, different semantics — separate parsers | Terraform-only at launch; Pulumi in v4 |
| AI "fix my infra" code generation | "Tell me how to remediate with AI" | LLM costs at scale, hallucinated Terraform is dangerous, prompt injection with HCL | Deterministic `Finding.remediation` is safer and free |
| Terragrunt / multi-workspace support | Power user need | Complex DRY abstractions require separate resolution layer | Not at launch; expand post-demand |

---

## FLOWMAP — Hybrid Network Topology

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AWS network topology collection (TGW, VPC routes, NACLs, Direct Connect) | AWS-native networking is minimum viable for hybrid topology; without TGW support the map is incomplete | HIGH | Phase 3 |
| Azure network topology collection (vWAN, Secure Hub, ExpressRoute, vNet peering) | AWS + Azure is the target market's actual hybrid reality; Azure-only gaps kill enterprise sales | HIGH | Phase 3 |
| Physical DC site visualization (routers, firewalls as nodes) | Hybrid means on-prem; without DC representation the "hybrid" claim is hollow | HIGH | Phase 3 + DC Agent |
| Forward path tracing (src → dst hop-by-hop) | Path tracing is the primary network troubleshooting primitive; expected by any network engineer | HIGH | Phase 3 |
| Return path tracing (dst → src) | Forward-path-only is table stakes for Layer 3 but return path is required for asymmetric detection | HIGH | Phase 3 |
| Firewall rule hit count visualization | Network engineers need to see which firewall rules are actually firing; hit counts on policy nodes | MEDIUM | Phase 3 via Checkpoint/ASA APIs |
| Basic topology auto-discovery (NETCONF/SSH) | Manual topology entry doesn't scale past 5 devices; auto-discovery is expected | HIGH | DC Agent Phase 3 |
| VPN tunnel status (up/down) | VPN health is a constant operational concern in hybrid environments | MEDIUM | Phase 3 |
| Network findings with severity (NET-001 through NET-012) | Findings without a structured code system don't integrate with ticket systems | MEDIUM | Phase 3 |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Asymmetric routing detection with root-cause classification | NetBrain does this at $100K ACV; InfraCanvas does it at $999/mo Enterprise — clear price-point disruption | HIGH | Phase 3 — core FlowMap moat |
| Dual-path rendering (forward + return on same diagram) | Visualizing both paths simultaneously makes asymmetry immediately visible; no competing tool at this price does this | HIGH | Phase 3 FlowMap viewer |
| Cross-cloud path tracing (AWS TGW → DC → Azure vWAN) | Multi-cloud paths are the #1 unresolved visibility gap for hybrid platform teams; NetBrain requires per-domain licenses | HIGH | Phase 3 — the uniquely hard part |
| Firewall capacity monitoring (throughput utilization) | Capacity-based firewall failure is a silent risk; seeing "this firewall is at 87% throughput" is operationally critical | MEDIUM | Phase 3 via SNMP/API |
| "Why can't X reach Y?" troubleshooting wizard | Guided path analysis with policy context is what network engineers actually do during incidents; tooled guidance dramatically reduces MTTR | HIGH | Phase 5 |
| Zscaler ZPA + ZDX integration | Zero-trust overlay is increasingly part of hybrid paths; ignoring ZPA makes hybrid maps incomplete for ZTNA-adopting enterprises | HIGH | Phase 5 |
| NMS data overlay (SolarWinds, PRTG import) | Network teams already have NPM data; overlaying ITSM/NPM on the topology map avoids "yet another tool" resistance | HIGH | Phase 5 |
| Historical path snapshots (playback topology over time) | "What did the network look like when the outage happened?" — forensic analysis need; NetBrain's Digital Twin does this at enterprise pricing | HIGH | Phase 5+ |

### Anti-Features

| Anti-Feature | Why Requested | Why to Avoid | What to Do Instead |
|--------------|---------------|--------------|-------------------|
| Full NPM (SNMP polling, dashboards, alerting) | "Replace our PRTG" | Full NPM is a decade-long investment; OpManager, PRTG, SolarWinds own this market | Read-only topology integration; overlay their NPM data |
| Packet capture / deep packet inspection | "Show me the actual traffic" | Requires agent deployment on every node; security and privacy implications; Wireshark/Kentik own this | NetFlow summary data is sufficient for path analysis |
| BGP route table management | "Let me push route changes" | Write access to network devices is a configuration management product; not an intelligence platform | Read-only routing table visualization only |
| SD-WAN full integration (Meraki, Viptela) | "We use Meraki" | SD-WAN APIs vary wildly; each vendor is a separate integration | Cisco ASA/FTD + Checkpoint first; SD-WAN in Enterprise roadmap |
| Real-time packet-level latency (< 1ms) | "I need per-millisecond latency" | NetFlow provides flow-level granularity; packet-level requires TAP or SPAN infrastructure | Flow-level latency and path health checks |

---

## COSTLENS — Shared Infrastructure Cost Allocation

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-resource cost estimation from IaC | Infracost has made inline cost annotation standard practice | LOW | Already in Canvas |
| Shared service cost identification (TGW, ExpressRoute, Firewall) | Shared networking costs are the #1 FinOps blind spot; un-attributed shared costs cause budget disputes | HIGH | Phase 4 CostLens |
| Cost allocation by attachment/spoke (TGW flexible cost allocation) | AWS now provides flexible cost allocation on TGW natively; the platform should expose this | MEDIUM | Phase 4; AWS launched FCA for TGW Nov 2025 |
| Showback reporting (visibility without billing consequences) | FinOps best practice: show teams their share before moving to chargeback; 72% of orgs start here | MEDIUM | Phase 4 |
| Multi-region cost normalization | Teams deploy in multiple regions; single-region cost display is not representative | MEDIUM | Phase 2 for Canvas; Phase 4 for shared services |
| Cost trend over time (is shared infra growing?) | Point-in-time cost snapshots have limited FinOps value; trend lines enable forecasting | MEDIUM | Phase 4 with scan history |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-path cost analysis (cost of this network path) | No competitor maps network path traversal to cost attribution; "this application's TGW + Firewall share costs $X/month" is novel | HIGH | Phase 4 — requires FlowMap path data + cost model |
| Cross-cloud cost correlation (AWS + Azure shared infra) | Multi-cloud shared costs (ExpressRoute + TGW + Secure Hub together) are impossible to see in AWS Cost Explorer or Azure Cost Management alone | HIGH | Phase 4 |
| Cost optimization recommendations (oversized shared services) | Identifying that a TGW attachment is unused or a Secure Hub is overprovisioned is actionable; cost tools generally report, not advise | HIGH | Phase 4 |
| Chargeback model generation (from showback to chargeback) | Organizations start with showback and mature to chargeback; helping them build the allocation model is high-value consulting-in-software | HIGH | Phase 4/5 |
| Firewall throughput cost per application team | Attributing firewall throughput cost (inspect bytes × $/GB) to application owners creates accountability for chatty applications | MEDIUM | Phase 4 via FlowMap throughput data |

### Anti-Features

| Anti-Feature | Why Requested | Why to Avoid | What to Do Instead |
|--------------|---------------|--------------|-------------------|
| Full FinOps platform (reserved instance optimization, savings plans) | "Replace our CloudHealth" | CloudHealth, CloudZero, Spot.io own cost optimization at scale; deep discounting logic is complex | Shared infrastructure allocation is the niche; link to FinOps tools for reserved capacity |
| Real-time billing API integration (AWS Cost Explorer polling) | "Show me today's spend" | AWS Cost Explorer API has 24-48h lag; real-time is marketing fiction | Use IaC-estimated costs + scan history for trend; flag actual billing lag |
| GCP shared cost allocation | "We use GCP too" | Different billing model, different shared service types | Defer to v4.0 with GCP support |
| Budget alerts and anomaly detection | "Alert me when costs spike" | AWS Cost Anomaly Detection and CloudZero do this natively; high false positive management burden | Link to AWS Cost Anomaly Detection; focus on attribution not alerting |

---

## ENTERPRISE — Compliance + SSO + Self-Hosted

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SOC 2 Type II control mapping | Enterprise security teams require framework mapping before approving vendor spend; this is a procurement gate | HIGH | Phase 5 |
| SSO / SAML via managed IdP | Every enterprise IT policy requires SSO; without it the tool can't be deployed to >50 users | MEDIUM | Phase 5 via Clerk Enterprise SAML |
| Audit logs (who ran what scan, when, what changed) | Compliance and security teams need audit trails for change tracking | MEDIUM | Phase 5 |
| Self-hosted deployment option (Docker Compose / Helm) | Regulated industries (financial services, healthcare, government) cannot send IaC state to cloud SaaS | HIGH | Phase 5 |
| RBAC with granular permissions | Enterprise teams have complex permission hierarchies; view-only access for auditors, edit for platform team | MEDIUM | Phase 5 (basic RBAC in Phase 4) |
| Evidence export (framework-mapped, auditor-ready) | SOC 2 auditors require evidence packages; manual screenshot collection is the status quo pain point | HIGH | Phase 5 |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| PCI-DSS network segmentation verification (via FlowMap) | PCI-DSS requirement 1 (network segmentation) can be validated using FlowMap path data; no tool does automated PCI network segmentation evidence | HIGH | Phase 5 — unique to having both Canvas + FlowMap |
| HIPAA + SOC2 cross-framework mapping | Cross-framework overlap detection reduces audit effort; Vanta/Drata handle GRC process but not IaC/network layer evidence | HIGH | Phase 5 |
| OPA/Rego custom policy engine | Enterprise security teams want codified organizational policies that go beyond built-in rules | HIGH | Phase 5 |
| Palo Alto + Fortinet NVA support | Enterprise deployments use PAN-OS and FortiGate; Checkpoint-only limits enterprise selling | HIGH | Phase 5 |

### Anti-Features

| Anti-Feature | Why Requested | Why to Avoid | What to Do Instead |
|--------------|---------------|--------------|-------------------|
| Full GRC platform (risk register, vendor questionnaires) | "Be our Vanta" | GRC is a separate product category; Vanta/Drata/Dex are purpose-built | Provide evidence exports that feed into GRC tools; partner not compete |
| SIEM integration (Splunk, Sentinel ingest) | "Send our findings to Splunk" | SIEM schemas are complex; normalization is an integration product | Provide structured JSON export; let SIEM teams write their own ingest |
| FedRAMP compliance | Government market | FedRAMP authorization is a 12-18 month process costing $500K+; not viable solo | Note as Year 3 if revenue supports it |
| Vulnerability scanner (CVE detection) | "Scan my container images too" | Container/OS CVE scanning is Snyk/Grype territory; different data model | Stay at IaC config layer; link to container scanners |

---

## Feature Dependencies (Cross-Product)

```
[DC Collector Agent] (Go binary, Phase 3)
    └──enables──> [FlowMap topology collection]
    └──enables──> [Asymmetric routing detection]
    └──enables──> [Firewall capacity monitoring]
    └──enables──> [CostLens firewall throughput cost]

[FlowMap path data]
    └──requires──> [DC Collector Agent deployed]
    └──requires──> [AWS network topology collection]
    └──requires──> [Azure network topology collection]
    └──enables──> [Per-path cost analysis in CostLens]
    └──enables──> [PCI network segmentation validation in Enterprise]
    └──enables──> ["Why can't X reach Y?" wizard in Phase 5]

[Canvas scan history (SaaS Phase 4)]
    └──requires──> [FastAPI backend + Neon DB]
    └──requires──> [Cloudflare R2 artifact storage]
    └──enables──> [Scan comparison diff view]
    └──enables──> [Security score trend charts]
    └──enables──> [CostLens cost trend]

[Auth system (Clerk)]
    └──enables──> [Team roles + RLS]
    └──enables──> [Billing gate logic]
    └──enables──> [SSO/SAML (Phase 5 Clerk Enterprise)]
    └──enables──> [Audit logs]

[Security rules (30 AWS + 10 Azure)]
    └──required for──> [Security score card]
    └──required for──> [Compliance framework mapping]
    └──enables──> [OPA/Rego custom policy (Phase 5) — rules become the baseline]

[SaaS backend (FastAPI, Phase 4)]
    └──required for──> [All SaaS features]
    └──required for──> [CI/CD webhook auto-scan]
    └──required for──> [Scan history + comparison]
    └──required for──> [CostLens allocation reports]

[CLI push command]
    └──requires──> [CLI login (Clerk device auth or API key)]
    └──requires──> [SaaS backend running]
    └──enables──> [All SaaS scan-based features]
```

### Critical Dependency Notes

- **FlowMap requires DC Agent + cloud API collection both working**: Path tracing is only meaningful when both sides of a hybrid path are populated. Partial topology produces misleading paths. Build both cloud collection and DC agent before enabling path tracing.
- **CostLens per-path cost requires FlowMap path data**: CostLens shared service allocation is valuable standalone, but per-path cost analysis (the differentiator) cannot be built until FlowMap produces path records.
- **Compliance evidence requires 30+ rules with framework tags**: Compliance mapping in Phase 5 requires the rule expansion from Phase 2 to be complete and the rules to carry CIS/NIST/SOC2 metadata tags from the start.
- **Auth is the root SaaS dependency**: All Phase 4 SaaS features require Clerk auth working first.
- **Canvas security rules must carry framework tags from Phase 2**: Retrofitting framework metadata onto rules after the fact is expensive. Tag rules with CIS/NIST/SOC2/PCI-DSS identifiers during the Phase 2 expansion.

---

## MVP Per Phase

### Phase 2 (Canvas v1.0) MVP
Must ship: Azure parser + 10 AZ rules, 30 AWS rules, shadow infra detection, custom YAML policies, multi-region cost, runtime staleness checks.
Differentiator to validate: Custom policy engine — if platform engineers adopt it, it justifies the commercial tier.

### Phase 3 (FlowMap v1.0) MVP
Must ship: AWS + Azure network topology collection, DC Agent (Cisco router + ASA), path tracer, asymmetric routing detector, FlowMap viewer.
Differentiator to validate: Asymmetric routing detection — if network engineers use this to close tickets, it justifies the Enterprise tier price.

### Phase 4 (SaaS + CostLens) MVP
Must ship: FastAPI backend, Clerk auth, Neon DB + R2, CLI push, project dashboard, scan history, shareable links, Stripe billing, CostLens shared service allocation.
Differentiator to validate: Per-path cost analysis — if cloud architects use this in budget conversations, it justifies $299/mo Team tier.

### Phase 5 (Enterprise) MVP
Must ship: SSO/SAML, SOC2/PCI-DSS mapping, evidence export, self-hosted Docker + Helm, OPA/Rego v2, audit logs.
Differentiator to validate: PCI network segmentation evidence via FlowMap — unique cross-product capability that no competitor can replicate at this price point.

---

## Competitor Feature Gap Matrix

| Feature | Brainboard | Pluralith | Hava.io | NetBrain | InfraCanvas |
|---------|-----------|-----------|---------|---------|-------------|
| IaC visualization (Terraform) | Yes (bidirectional) | Yes (read-only) | No (live cloud only) | No | Yes (read-only) |
| Security findings on diagram | Checkov/TFSec via CI | No | VPC security groups | No | Native 30+ rules |
| Drift detection | Via CI pipeline | Yes (visual plan diff) | Versioning (live) | Change/drift detection | Yes (plan overlay) |
| Custom policy engine | OPA in CI | No | No | Compliance checks | YAML v1 → OPA v2 |
| Hybrid network topology | No | No | No | Yes (Digital Twin) | Yes (FlowMap) |
| Asymmetric routing detection | No | No | No | Yes ($100K ACV) | Yes (Phase 3) |
| Cross-cloud path tracing | No | No | No | Partial (domain licenses) | Yes (Phase 3) |
| Shared cost allocation | No | Infracost in PR | Basic monthly cost | No | Yes (CostLens Phase 4) |
| Per-path cost analysis | No | No | No | No | Yes (Phase 4, unique) |
| Compliance framework mapping | No | No | No | Compliance checks | Phase 5 |
| Self-hosted | No | No | No | Yes | Phase 5 |
| Price point | ~$299/mo | ~$99/mo | ~$299/mo | $100K+ ACV | $0-$999+/mo |

---

## Sources

- Competitor feature research: Brainboard.co, Hava.io (Cloudcraft vs Hava comparison), Pluralith YC launch + docs, NetBrain hybrid visibility page — MEDIUM-HIGH confidence (verified against official documentation)
- CSPM/Security: CSPM guide 2026 (securityboulevard.com), IaC security trends (fidelissecurity.com) — MEDIUM confidence
- Cost allocation: AWS blog on TGW Flexible Cost Allocation (Nov 2025), CloudZero showback/chargeback guides, Hykell FinOps guides — HIGH confidence (official AWS source)
- Network topology: NetBrain hybrid visibility page, Kentik hybrid cloud networking guide, Datadog hybrid multi-cloud observability reference — MEDIUM-HIGH confidence
- Compliance: deepstrike.io cloud security compliance 2026, Vanta SOC2/HIPAA/PCI reference — MEDIUM confidence
- PROJECT.md: InfraCanvas requirements, personas, out-of-scope decisions, constraints
- Platform engineering pain points: Platform Engineering 2025 survey (518 engineers, 75% tool fragmentation), Stack Overflow 2025 — MEDIUM confidence (survey methodology not fully verified)
