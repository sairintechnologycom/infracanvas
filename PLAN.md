# InfraCanvas — Product Blueprint v2.0

## One-Liner
**Terraform scan to board-ready architecture diagram in 30 seconds — with every security risk highlighted.**

---

## What We're Building

InfraCanvas is a hybrid cloud intelligence platform that gives engineering and leadership teams a single visual pane of glass across AWS, Azure, and physical data centre infrastructure — showing configuration, security, network traffic paths, and cost in real time.

Not a diagramming tool. Not a security scanner. Not a network monitor. All four, unified, in one platform across three intelligence layers.

---

## Problem Statement

Cloud teams running production infrastructure across AWS and Azure cannot answer the question "Is our infrastructure in the state we think it is?" at any given moment — without days of manual audit work.

| Tool | What it does | What it misses |
|------|-------------|----------------|
| Cloudcraft / draw.io | Pretty diagrams | Always stale, manual |
| Checkov / tfsec | Security findings | No architectural context |
| Terraform plan | Drift detection | Unreadable to non-engineers |
| Infracost | Cost estimates | No visual context |
| GRC platforms | Compliance | $50k+/year, overkill |

**Specific pain points this product was built from:**
- Resources deployed manually, bypassing Terraform entirely (shadow infrastructure)
- Network changes made inconsistently across 2 regions
- Standards not followed despite Terraform being used — no enforcement
- Services never upgraded — Lambda on EOL runtimes, Azure Apps on old stacks
- Tags inconsistent — shared infrastructure cost invisible
- Resource locks missing or incorrectly configured
- Firewall rules approaching capacity exhaustion (no alert until it breaks)
- Asymmetric routing between AWS and Azure through physical data centres — forward and return paths diverge, stateful firewalls see only one direction, diagnosis takes hours
- No single view of what a packet path looks like from AWS Singapore to Azure Australia East through two data centre legs with BGP + static routing mixed

Nobody has connected all of these. We will.

---

## Three Products

### 1. Canvas — Infrastructure Intelligence
*"What exists, and is it configured correctly?"*

Parses Terraform code and live cloud APIs to generate interactive architecture diagrams. Detects drift, security misconfigurations, policy violations, shadow infrastructure, and runtime staleness. The entry point for every user.

### 2. FlowMap — Network Path Intelligence
*"What path does traffic actually take, and why?"*

Visualises complete hybrid network topology end-to-end: AWS Transit Gateway → physical data centres (Cisco routers, BGP + static routing) → Azure Secure Hub / vWAN. Detects asymmetric routing, monitors firewall capacity, alerts on route changes. The feature no competitor has attempted.

### 3. CostLens — FinOps Intelligence
*"What is shared infrastructure actually costing, and who is consuming it?"*

Allocates shared infrastructure costs (Transit Gateway, Secure Hub, ExpressRoute, Direct Connect, Azure Firewall throughput) by workload and team. Shows per-path data transfer costs and identifies optimisation opportunities. Opens the FinOps budget conversation.

---

## Target Users & Personas

### Primary Buyer: Cloud Architect ("Alex")
- Maintains architecture docs that are always 3 months stale
- Presents infrastructure state to leadership and auditors quarterly
- Signs or influences $200–999/month SaaS decisions
- **Job to be done**: "Give me a defensible, always-current architecture diagram I can put in front of a CISO without embarrassment"
- **Conversion path**: Priya installs → team sees value → Alex approves Team/Enterprise

### Primary User / Distribution Channel: Platform Engineer ("Priya")
- Reviews 10+ Terraform PRs/week
- Currently runs tfsec + terraform plan + manually pieces together the story
- Discovers InfraCanvas through open-source CLI, becomes internal champion
- **Job to be done**: "Show me what this PR actually changes, visually, with problems highlighted"
- **Conversion path**: Free CLI → Pro ($79/mo) → brings to team

### High-Value Expansion: Security / Network Engineer ("Sam")
- Gets the 2am call when something breaks
- Diagnoses asymmetric routing manually — correlating TGW route tables, Azure effective routes, DC BGP state, firewall logs across 4–5 systems
- Audits cloud environments for compliance
- **Job to be done**: "Show me every finding in context of the full architecture. Why can't X reach Y?"
- **Conversion path**: Team tier user → drives Enterprise conversation around compliance and troubleshooting wizard

> **Co-founder rule**: Priya installs it. Alex pays for it. Every product and marketing decision gets filtered through this lens.

---

## Open-Source Strategy

We open-source the CLI core. This is intentional and strategic — not a concession.

### What's Open-Source (MIT License)
- Terraform HCL parser → resource dependency graph
- Diagram layout engine (force-directed + hierarchical)
- AWS/Azure/GCP resource icon library
- JSON output schema and spec
- Basic HTML export renderer
- Top 10 security rules (enough to be useful, not enough to replace Pro)

### What Stays Closed (Commercial Only)
- Full security annotation engine (30+ rules, severity scoring, contextual findings)
- Drift detection and before/after diffing
- Cost estimation overlay
- FlowMap network intelligence engine
- DC collector agent
- SaaS dashboard, history, sharing
- Compliance framework mappings (SOC2, HIPAA, PCI)
- CI/CD webhook integrations

**Why this works**: HashiCorp proved this model with Terraform. Grafana proved it with dashboards. The open-source core gets us into every Terraform community on earth. The closed features are what enterprises need and what converts engineers into budget conversations with their managers.

**The fork risk**: If someone forks the core and adds security rules, we compete on depth, UX, and the SaaS layer. Our domain expertise means our security rules catch contextual blast radius, cross-resource relationship findings, and compliance-mapped annotations that a weekend fork won't produce correctly.

---

## Phase 0: Validate Before Building (Weeks 1–4)

**This is non-negotiable. No production code until we have evidence.**

### Week 1–2: The Fake Demo Test
- Take a real open-source Terraform repo (Gruntwork reference architecture)
- Manually build a diagram in Excalidraw with colour-coded security badges overlaid
- Post across r/devops, r/Terraform, Terraform Discord, LinkedIn
- Collect responses via Typeform: role, team size, current toolchain, willingness to pay

### Week 3–4: Pre-Sales
- DM every positive responder
- Offer founding member pricing — $49/month locked forever, paid now
- Set up Stripe. Count credit cards, not compliments.

**Go/No-Go Signal**: 10 paying pre-sales OR 50 genuine "I would pay" responses from target personas with contact details. If we can't hit that with our combined network and 20 years of cloud credibility, the GTM is wrong.

---

## Core Features — MVP (Canvas v0.1)

**Three features only. Nothing else.**

### F1: Terraform Parser + Resource Graph
- Parse `.tf` files and `.tfstate` — AWS only at launch
- Support flat configs + up to 3 levels of module nesting
- Extract resource types, names, dependencies, region, provider
- Hard scope: no Terragrunt, no workspaces

### F2: Interactive Architecture Diagram
- Auto-layout with AWS service icons
- Grouping by VPC, subnet, module
- Zoom, pan, search, filter by resource type
- Single-file HTML export (zero dependencies, emails cleanly, opens in any browser)

### F3: Security Annotation Engine (10 rules, closed-source)
1. S3 bucket publicly accessible (ACL)
2. Security group 0.0.0.0/0 ingress on sensitive ports
3. RDS publicly accessible
4. RDS no encryption
5. IAM policy with Action: "*"
6. IAM policy with Resource: "*"
7. Missing CloudTrail logging
8. VPC Flow Logs disabled
9. KMS key rotation disabled
10. Untagged resources (missing Name, Environment, Owner)

Free tier shows findings exist but hides details. That's the conversion moment.

---

## Full Feature Roadmap

### v0.1 — MVP (Month 1–2)
- Canvas: Terraform parser (AWS), interactive diagram, 10 security rules, HTML export
- `infracanvas score` — Report Card mechanic, shareable 0–100 score card
- Open-source repo public, pip + Homebrew

### v1.0 — Canvas Growth Release (Month 3–4)
- Drift detection (plan-based visual diff — green/red/amber)
- Cost estimation overlay (Infracost integration)
- Full CLI: scan, plan, score, export, serve
- 30 security rules (20 additional closed-source)
- Azure core resources (10 types)
- Runtime staleness checks (Lambda EOL, AKS/EKS version lag)
- Shadow infrastructure detection (live API vs Terraform state diff)
- Custom policy engine v1 (YAML — naming conventions, required tags, approved regions, approved instance types)
- Resource lock validation
- Tag compliance checking
- PNG, SVG, PDF export

### v1.5 — FlowMap Release (Month 5–7)
- Hybrid network topology visualisation (AWS TGW → DC → Azure Secure Hub)
- BGP + static routing correlation
- Asymmetric routing detector (forward path + return path simultaneously)
- Firewall capacity monitoring (Azure Firewall, Checkpoint R80+, Cisco ASA/FTD)
- Stale firewall rule detection (zero hit count in 90 days)
- Route change alerting (BGP withdrawal, static route modification)
- DC Collector Agent (Cisco NETCONF/RESTCONF primary, SSH CLI fallback, NetFlow v9/IPFIX)
- Checkpoint Management API integration (no agent required)
- Cisco ASA REST API + Cisco FMC single-endpoint for FTD devices
- ZIA forwarding rule visualisation (Zscaler internet-bound traffic interception)
- Network-specific findings: static route no failover, static/BGP asymmetry, undocumented static (shadow config), stale static route
- Team tier ($299/mo) unlocked

### v2.0 — SaaS Dashboard + CostLens (Month 8–10)
- SaaS Dashboard:
  - Project management, repo connections
  - Scan history and point-in-time snapshots
  - Shareable links (public/private/password-protected, no login required)
  - Team workspace, role-based access (owner/admin/member/viewer), 15 users
  - CI/CD webhook (push to main → auto-scan → Slack alert)
  - Historical comparison (any two scans side-by-side)
- CostLens:
  - TGW attachment cost split by workload/team
  - Azure Secure Hub data processing fees by source
  - ExpressRoute/Direct Connect port fees allocated per consumer
  - Azure Firewall per-GB throughput cost overlaid on FlowMap traffic
  - Cross-cloud data transfer costs by workload and flow
  - Per-path cost comparison with optimisation recommendations
  - Idle resource detection (running, zero traffic 30 days)

### v3.0 — Enterprise Moat (Month 10–12)
- Compliance frameworks: SOC2, HIPAA, PCI-DSS mapped to findings, auto-generated evidence reports
- SSO (SAML/OIDC via Clerk Enterprise) + full audit logs
- Custom policy engine v2 (Rego + YAML, team-namespaced policy sets)
- Self-hosted deployment (Docker Compose + Helm chart, air-gapped support)
- GitHub PR Bot — diagram diff + security delta posted as PR comment
- NMS integrations: SolarWinds, PRTG, NetBrain API pull (avoids agent where NMS exists)
- Palo Alto / Fortinet NVA support (firewall rule API integrations)
- Zscaler ZPA topology: connector topology inside AWS + Azure mapped on diagram
- Zscaler ZDX: hop-by-hop path traces including backbone segments
- Network troubleshooting wizard: "Why can't X reach Y?" traces SGs, NACLs, route tables, firewall rules in sequence
- Network path analyser (all possible paths between two resources)
- SG rule visualiser as diagram edges
- Route table + NACL overlay on subnet diagram
- Enterprise tier ($999+/mo)

### v4.0 — Horizon (Year 2)
- Live cloud import (no Terraform required — direct AWS/Azure API)
- AI natural language queries ("What's my blast radius if us-east-1 goes down?")
- Pulumi / CDK / Bicep support
- SBOM integration (software dependencies mapped to infrastructure)
- GCP support

---

## CLI Design

```bash
# Core commands
infracanvas scan ./terraform              # Scan + diagram + security findings
infracanvas plan ./terraform              # Scan + show plan diff
infracanvas export ./terraform --format=html|json|svg|png
infracanvas serve ./terraform             # Local web viewer
infracanvas score ./terraform             # Infrastructure Report Card (viral mechanic)

# CI/CD
infracanvas scan ./terraform --ci --severity=high  # Exit code based on findings
infracanvas scan ./terraform --quiet               # JSON only to stdout
infracanvas scan ./terraform --ignore=SEC-018      # Skip specific rules
```

Output is always a single self-contained HTML file. Zero dependencies. Opens in any browser. Emails cleanly. This matters because the diagram needs to reach Alex without Priya having to explain how to open it.

---

## Pricing

| Tier | Price | What You Get | Target |
|------|-------|-------------|--------|
| **Free** | $0 | CLI forever, 1 project, full diagram, 5 security finding teasers | Individual devs, trial |
| **Pro** | $79/mo | Unlimited projects, all 30+ security rules, drift, cost overlay, shadow infra, runtime staleness, custom policies, all export formats | Solo engineers, freelancers |
| **Team** | $299/mo | Everything in Pro + FlowMap (hybrid topology, asymmetric routing, firewall capacity), SaaS dashboard, 15 users, scan history, sharing, CostLens (shared infra cost allocation), CI/CD webhook | Platform teams |
| **Enterprise** | $999+/mo | Everything in Team + compliance frameworks, SSO, Zscaler ZPA/ZDX, NMS integrations, network troubleshooting wizard, self-hosted, SLA, priority support | Mid-market and up |

**Conversion mechanic**: Free tier shows a banner on every scan: *"3 critical findings hidden. Your infrastructure may be exposed. Upgrade to Pro to view."*

**Revenue target**: 200 Pro + 50 Team = $30,750 MRR within 12 months

---

## Go-to-Market Strategy

### Phase 0: Validate (Month 0 — Right Now)
- Fake demo post across communities
- 10 pre-sales at founding member pricing ($49/mo locked)
- 20 customer conversations minimum

### Phase 1: CLI Launch (Month 1–3)
- Open-source core to GitHub → pip, Homebrew
- **Lead with Infrastructure Report Card** — not the diagram
  - `infracanvas score ./infra` → shareable score card
  - "My infrastructure scored 71/100" designed for LinkedIn + Twitter
- Show HN launch timed to open-source release
- Target: 2,000 CLI installs, 200 GitHub stars, 50 free signups

### Phase 2: Content Engine (Month 3–6)
- Weekly "Terraform Anti-Patterns" series — each post uses InfraCanvas diagrams
- "AWS Architecture Reviews" — submit your Terraform, reviewed live with the tool
- YouTube: "terraform security" + "aws architecture diagram" keywords
- Target: 8,000 CLI installs, 500 free signups, 50 Pro subscribers

### Phase 3: Team Conversion (Month 6–12)
- Team dashboard launch + FlowMap release (the category-defining feature)
- GitHub Marketplace listing
- Direct outreach to platform teams at Series A–C startups
- Case studies from Pro users
- Target: 200 Pro, 50 Team, $30,750 MRR

---

## Competitive Position

| Feature | InfraCanvas | Brainboard | Pluralith | Hava.io | Cloudcraft | NetBrain |
|---------|-------------|------------|-----------|---------|------------|---------|
| Terraform parsing | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Security findings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Drift detection | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Cost overlay | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| CLI-first | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Open-source core | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Hybrid network topology | ✅ | ❌ | ❌ | ❌ | ❌ | Partial |
| Asymmetric routing detect | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| DC collector agent | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Firewall capacity monitor | ✅ | ❌ | ❌ | ❌ | ❌ | Partial |
| Shared cost allocation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Defensible moat**: The combination of visual architecture + security + hybrid network intelligence + cost in a CLI-first, open-core package with a DC collector agent for physical infrastructure. No competitor does all of this. The asymmetric routing detector and Cisco/Checkpoint/Zscaler integrations are things no one has built at this price point.

---

## Key Metrics

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|
| CLI installs | 2,000 | 8,000 | 25,000 |
| GitHub stars | 200 | 800 | 3,000 |
| Free signups | 50 | 500 | 2,500 |
| Pro subscribers | 10 | 50 | 200 |
| Team subscribers | 0 | 10 | 50 |
| MRR | $790 | $6,950 | $30,750 |
| Free → Pro conversion | — | 10% | 12% |

---

## Risks & Mitigations

| Risk | Our Response |
|------|-------------|
| Terraform parsing complexity (modules, workspaces) | Hard scope at launch: AWS only, 3 module levels, no Terragrunt. Expand based on customer demand. |
| Fork risk on open-source | Compete on depth and UX, not rule count. 20yr domain expertise is the moat. |
| Engineer ≠ buyer problem | Build for Alex (buyer), distribute through Priya (user). Every feature asks "how does Alex see this?" |
| Conversion free → paid | Security teaser gate is the primary mechanism. Report Card virality drives top of funnel. |
| DC agent adoption (enterprise) | Config file import fallback for offline topology. NETCONF removes fragility for modern IOS-XE. |
| Zscaler interception invisible | ZDX API gives hop-by-hop path traces including Zscaler backbone — complete picture only at Enterprise tier. |
| Parsing BGP + static mixed topologies | Start with cloud API segments (clean data). DC agent adds physical legs. Static routes parsed from router configs. |
