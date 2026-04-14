# InfraCanvas — Product Blueprint

## One-Liner
**One command. Full picture. Every blind spot visible.**

InfraCanvas parses Terraform code and imports live cloud resources to generate interactive architecture diagrams annotated with security findings, drift markers, cost estimates, and compliance flags.

---

## Problem Statement

Cloud engineers and architects today juggle 4–5 disconnected tools:
- **Diagramming**: Cloudcraft, Lucidchart, draw.io (manual, always outdated)
- **Security scanning**: Checkov, tfsec, Snyk IaC (CLI output, no visual context)
- **Drift detection**: Terraform plan, Firefly, env0 (text-based, hard to communicate)
- **Cost estimation**: Infracost (numbers without architecture context)
- **Compliance**: Manual checklists or expensive GRC platforms

**The pain**: No single tool answers "Is this infrastructure healthy?" visually. Security findings lack architecture context. Diagrams are always stale. Communicating infrastructure state to leadership or auditors requires hours of manual work.

**Who feels this most**:
1. Platform/DevOps engineers reviewing PRs with IaC changes
2. Cloud architects presenting infrastructure to stakeholders
3. Security engineers auditing cloud environments
4. CTOs/VPs who need infrastructure visibility without reading HCL

---

## Target Users & Personas

### Primary: Platform Engineer ("Priya")
- Reviews 10+ Terraform PRs/week
- Needs to spot security gaps and architectural regressions fast
- Currently runs tfsec + terraform plan + manually draws changes
- **Job to be done**: "Show me what this PR actually changes, visually, with any problems highlighted"

### Secondary: Cloud Architect ("Alex")
- Maintains architecture documentation (always outdated)
- Presents infrastructure state to leadership quarterly
- **Job to be done**: "Give me an always-current, shareable architecture diagram"

### Tertiary: Security Engineer ("Sam")
- Audits cloud environments for compliance
- Needs to trace blast radius of misconfigurations
- **Job to be done**: "Show me every security finding in context of the full architecture"

---

## Core Features (MVP — v1.0)

### F1: Terraform Parser & Resource Graph
- Parse HCL files (`.tf`, `.tfvars`) into a resource dependency graph
- Support Terraform state files (`.tfstate`) for live resource import
- Extract: resource types, names, dependencies, provider, region
- Handle modules, data sources, locals, variables

### F2: Interactive Architecture Diagram
- Auto-layout using force-directed + hierarchical algorithms
- Cloud provider icons (AWS, Azure, GCP — start with AWS)
- Grouping by: VPC/VNET, subnet, region, module, resource type
- Zoom, pan, search, filter by resource type
- Export as PNG, SVG, PDF

### F3: Security Annotation Engine
- 30 high-impact rules at launch:
  - Public S3 buckets / storage accounts
  - Security groups with 0.0.0.0/0 ingress
  - Unencrypted databases, volumes, buckets
  - IAM policies with * actions or * resources
  - Missing logging (CloudTrail, VPC Flow Logs)
  - Untagged resources
  - Publicly accessible RDS/databases
  - Missing WAF on ALB/CloudFront
  - Root account usage indicators
  - KMS key rotation disabled
- Severity levels: Critical / High / Medium / Info
- Visual overlay: color-coded badges on affected resources
- Click-to-expand finding detail + remediation suggestion

### F4: Drift Detection (v1 — Plan-based)
- Compare `terraform plan` output against current diagram
- Highlight: additions (green), deletions (red), modifications (amber)
- Show before/after for modified resources
- "What changed" summary panel

### F5: Cost Estimation Overlay
- Integrate with Infracost pricing data (or build lightweight estimator)
- Show estimated monthly cost per resource and per group
- Total infrastructure cost visible on diagram
- Cost delta on drift/changes

### F6: CLI Tool
- `infracanvas scan ./terraform` — scan local Terraform directory
- `infracanvas plan ./terraform` — scan + show plan diff
- `infracanvas export ./terraform --format=html|json|svg|png`
- `infracanvas serve` — local web viewer
- Output: interactive HTML report (single file, zero dependencies)
- JSON output for CI/CD integration

### F7: SaaS Dashboard (v1)
- Project management (connect repos, upload state files)
- History: diagram snapshots over time
- Sharing: public/private links with optional password
- Team workspace with role-based access
- Webhook for CI/CD triggers (push to main → auto-scan)

---

## Features Deferred (v2+)

- **Multi-cloud support**: Azure, GCP resource parsing
- **PR Review Bot**: GitHub/GitLab bot that posts diagram diff as PR comment
- **Compliance frameworks**: SOC2, HIPAA, PCI-DSS mapped to findings
- **Custom policy engine**: Write custom rules in Rego/YAML
- **Pulumi/CDK support**: Parse other IaC frameworks
- **Live cloud import**: Direct AWS/Azure/GCP API import (no Terraform required)
- **Slack/Teams integration**: Alert on new critical findings
- **SBOM integration**: Map software dependencies to infrastructure
- **AI insights**: Natural language queries ("What's my blast radius if us-east-1 goes down?")

---

## User Stories & Acceptance Criteria

### US-1: Scan Terraform Directory
**As a** platform engineer
**I want to** run a single CLI command against my Terraform directory
**So that** I get an interactive architecture diagram without manual setup

**Acceptance Criteria**:
- [ ] `infracanvas scan ./infra` produces an HTML file
- [ ] All resource types in supported providers are rendered
- [ ] Module references are resolved and shown
- [ ] Runs in < 10 seconds for projects with < 500 resources
- [ ] Exit code 0 on success, non-zero with descriptive error on failure

### US-2: View Security Findings in Context
**As a** security engineer
**I want to** see security findings overlaid on the architecture diagram
**So that** I understand the blast radius and context of each finding

**Acceptance Criteria**:
- [ ] Each finding is a clickable badge on the affected resource
- [ ] Badge color reflects severity
- [ ] Click opens detail panel with description, impact, remediation
- [ ] Filter/sort by severity level
- [ ] Summary count of findings by severity visible at all times

### US-3: Visualize Terraform Plan Changes
**As a** platform engineer reviewing a PR
**I want to** see what infrastructure changes a Terraform plan introduces
**So that** I can approve/reject with visual understanding

**Acceptance Criteria**:
- [ ] `infracanvas plan ./infra` reads `terraform show -json plan.out`
- [ ] Additions shown in green, deletions in red, changes in amber
- [ ] Changed resources show before/after diff on click
- [ ] Summary panel shows total adds/changes/deletes

### US-4: Share Diagram with Stakeholders
**As a** cloud architect
**I want to** share a live architecture diagram via link
**So that** leadership can see current infrastructure without Terraform knowledge

**Acceptance Criteria**:
- [ ] Generate shareable link from dashboard
- [ ] Link opens interactive diagram (zoom, pan, filter)
- [ ] Optional password protection
- [ ] Viewer does not require login
- [ ] Diagram reflects latest scan

### US-5: Track Infrastructure Changes Over Time
**As a** platform team lead
**I want to** see how infrastructure has evolved over time
**So that** I can audit changes and understand architectural drift

**Acceptance Criteria**:
- [ ] Dashboard shows timeline of scans per project
- [ ] Click any historical scan to view that point-in-time diagram
- [ ] Compare any two scans side-by-side
- [ ] Export change history as PDF report

---

## Pricing & Revenue Model

| Tier | Price | Limits | Target |
|------|-------|--------|--------|
| **Free** | $0 | CLI only, 3 projects, basic diagrams, no security | Individual devs, trial |
| **Pro** | $49/mo | Unlimited projects, security annotations, drift, cost overlay, HTML export | Solo engineers, freelancers |
| **Team** | $199/mo | Dashboard, 10 users, history, sharing, CI/CD webhook, PR bot (v2) | Platform teams (5-15 people) |
| **Enterprise** | $499+/mo | SSO, compliance frameworks, custom policies, SLA, priority support | Mid-market companies |

**Revenue target**: 200 Pro + 50 Team = $19,750 MRR within 12 months

---

## Go-to-Market Strategy

### Phase 1: Developer Adoption (Month 1-3)
- Open-source the CLI core (diagram generation only)
- Publish to npm/pip, Homebrew
- "Show HN" launch + dev.to/medium technical posts
- Target: 1,000 CLI installs, 100 GitHub stars

### Phase 2: Content-Led Growth (Month 3-6)
- "Infrastructure Report Card" — viral mechanic:
  - Run `infracanvas score ./infra` → generates a shareable score card
  - Security score, cost efficiency score, compliance readiness
  - Social sharing ("My infrastructure scored 72/100")
- Weekly blog: "Terraform Anti-Patterns" series using InfraCanvas diagrams
- Target: 5,000 CLI installs, 500 free signups

### Phase 3: Team Conversion (Month 6-12)
- Launch Team tier with dashboard
- GitHub Marketplace listing
- Case studies from early Pro users
- Target: 200 Pro, 50 Team subscribers

### Distribution Channels (PLG)
1. **CLI → SaaS upgrade**: Free CLI includes "upgrade for security insights" CTA
2. **GitHub Marketplace**: One-click install for org-wide scanning
3. **Content marketing**: Terraform tutorials, architecture review content
4. **Community**: Discord for users, Terraform community engagement
5. **Partnerships**: DevOps tool directories (StackShare, AlternativeTo)

---

## Competitive Analysis

| Feature | InfraCanvas | Brainboard | Pluralith | Hava.io | Cloudcraft |
|---------|-------------|------------|-----------|---------|------------|
| Terraform parsing | ✅ | ✅ | ✅ | ❌ | ❌ |
| Live cloud import | v2 | ✅ | ❌ | ✅ | ✅ |
| Security findings | ✅ | ❌ | ❌ | ❌ | ❌ |
| Drift detection | ✅ | ❌ | ✅ | ❌ | ❌ |
| Cost overlay | ✅ | ❌ | ✅ | ❌ | ✅ |
| CLI-first | ✅ | ❌ | ✅ | ❌ | ❌ |
| Open-source core | ✅ | ❌ | ❌ | ❌ | ❌ |
| PR integration | v2 | ❌ | ✅ | ❌ | ❌ |
| Self-hosted option | v2 | ❌ | ❌ | ❌ | ❌ |

**Defensible moat**: The combination of visual architecture + security + drift + cost in a CLI-first, open-source-core package. No one does all four.

---

## Key Metrics

| Metric | Target (6 months) | Target (12 months) |
|--------|-------------------|---------------------|
| CLI installs | 5,000 | 20,000 |
| GitHub stars | 500 | 2,000 |
| Free signups | 500 | 2,000 |
| Pro subscribers | 50 | 200 |
| Team subscribers | 10 | 50 |
| MRR | $4,450 | $19,750 |
| NPS | 40+ | 50+ |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Terraform parsing complexity (modules, workspaces) | MVP delay | Start with flat configs, add module support iteratively |
| Security rules quality vs. Checkov/tfsec | Credibility | Focus on visual context as differentiator, not rule count |
| Low conversion free→paid | Revenue | Gate security insights (highest value) behind Pro |
| Cloud provider API changes | Maintenance | Abstract provider layer, community-contributed icons |
| Solo founder bandwidth | Everything | Ruthless MVP scoping, open-source for community contributions |
