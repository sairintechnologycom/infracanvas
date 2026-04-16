# Roadmap: InfraCanvas v2.0

## Overview

InfraCanvas v2.0 is built in 6 phases: validate demand before writing code (Phase 0), ship a CLI MVP with interactive diagrams and security scoring (Phase 1), harden the parser and expand to Azure with a full policy engine (Phase 2), ship the Go DC Agent and hybrid network path tracer with asymmetric routing detection (Phase 3), launch the FastAPI SaaS with CostLens shared cost allocation (Phase 4), then add Enterprise compliance, SSO, and self-hosted deployment (Phase 5). Each phase delivers a coherent, independently verifiable capability.

## Phases

- [ ] **Phase 0: Validation** - Pre-sales signal gathering to confirm demand before building
- [ ] **Phase 1: Canvas MVP** - CLI-first tool with HCL parsing, interactive diagram, security scoring, and PyPI release
- [ ] **Phase 2: Canvas v1.0** - Azure support, 30 AWS rules, drift + shadow infra, multi-region cost, policy engine
- [ ] **Phase 3: FlowMap v1.0** - Go DC Agent, hybrid network topology, path tracer, asymmetric routing detection
- [ ] **Phase 4: SaaS Dashboard + CostLens** - FastAPI backend, Next.js 15 dashboard, Neon/Clerk/Stripe, shared cost allocation
- [ ] **Phase 5: Enterprise** - Compliance engine, SSO, OPA/Rego policies, self-hosted, Zscaler, NMS, troubleshooting wizard

## Phase Details

### Phase 0: Validation
**Goal**: Confirm real demand and willingness to pay before building anything
**Depends on**: Nothing (first phase)
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05
**Success Criteria** (what must be TRUE):
  1. A fake demo (no real code) reaches r/devops, LinkedIn, and Terraform Discord and generates measurable engagement
  2. A Typeform captures role, team size, toolchain, and willingness to pay from interested visitors
  3. A Stripe founding-member page is live at $49/mo locked pricing
  4. 20 customer conversations are documented with specific pain points and tool names
  5. A Go/No-Go decision is made: 10 credit cards captured OR 50 strong signals recorded
**Plans:** 3 plans
Plans:
- [x] 00-01-PLAN.md — Landing page (Next.js static site at infracanvas.dev with Stripe + Typeform CTAs)
- [x] 00-02-PLAN.md — Validation content artifacts (post drafts, Typeform spec, tracker, demo script, Go/No-Go framework)
- [x] 00-03-PLAN.md — External service setup + outreach execution (Stripe, Typeform, Vercel deploy, community posts, customer conversations, Go/No-Go decision)

### Phase 1: Canvas MVP
**Goal**: Engineers can run one command against a Terraform directory and get an interactive, annotated infrastructure diagram with security scores
**Depends on**: Phase 0 (Go decision)
**Requirements**: CLI-01, CLI-02, PRS-01, PRS-02, PRS-03, PRS-04, PRS-05, GRF-01, GRF-02, GRF-03, SEC-01, SEC-02, SEC-03, SEC-04, SCR-01, SCR-02, SCR-03, VWR-01, VWR-02, VWR-03, VWR-04, VWR-05, VWR-06, EXP-01, EXP-02, REL-01, REL-02, REL-03, REL-04
**Success Criteria** (what must be TRUE):
  1. `infracanvas scan ./terraform` opens a browser with a zoomable, filterable diagram in under 10 seconds on a 500-resource project
  2. The diagram shows VPC/subnet grouping, resource icons, dependency edges, and security finding badges
  3. `infracanvas score` outputs a letter-grade (A-F) across Security, Encryption, IAM Hygiene, Cost Efficiency, and Tagging dimensions
  4. `pip install infracanvas` and `brew install infracanvas` both work; GitHub repo is public with MIT license
  5. The exported single-file HTML opens in any browser with zero dependencies and includes an upgrade CTA for blurred finding details
**Plans:** 7 plans
Plans:
- [x] 01-01-PLAN.md — Data layer: models, module parser, shadow flagging, JSON v2.0
- [x] 01-02-PLAN.md — Scorer dimension realignment + score card HTML redesign
- [x] 01-03-PLAN.md — Viewer: gate UI, search bar, shadow indicators, types
- [x] 01-04-PLAN.md — CLI: scan HTML default, CI detection, serve command
- [x] 01-05-PLAN.md — Resource types: layout tiers, icons, pipeline wiring, build verification
- [x] 01-06-PLAN.md — End-to-end integration + visual checkpoint
- [ ] 01-07-PLAN.md — Release: PyPI packaging, GHA workflow, Homebrew, README

### Phase 2: Canvas v1.0
**Goal**: The CLI handles Azure alongside AWS, detects drift and shadow infrastructure, enforces custom policies, and ships multi-region cost estimation — with the HCL parser hardened against silent failures first
**Depends on**: Phase 1
**Requirements**: PLN-01, PLN-02, PLN-03, SHD-01, SHD-02, CST-01, CST-02, CST-03, AZR-01, AZR-02, AZR-03, SEC-05, SEC-06, RST-01, RST-02, POL-01, POL-02, CLX-01, CLX-02, DST-01, DST-02
**Success Criteria** (what must be TRUE):
  1. `infracanvas scan` on an Azure Terraform directory produces a diagram with 10 Azure resource types, NSG rules, and AZ-001-AZ-010 security findings
  2. `infracanvas plan` overlays colour-coded drift (green/red/amber/grey) on the diagram and shows before/after attribute diffs
  3. Shadow infrastructure (live AWS API vs state) is flagged with dashed borders and estimated cost; no silent parse failures occur on complex modules
  4. All 30 AWS security rules and all 10 Azure rules carry compliance framework tags (CIS, NIST, SOC2, PCI-DSS) visible in findings output
  5. A `.infracanvas.yml` custom policy (required tags, allowed regions, naming patterns) causes `infracanvas scan --policy ./policies` to fail in CI with a non-zero exit code
**Plans**: TBD

### Phase 3: FlowMap v1.0
**Goal**: Engineers can visualise the full hybrid network path from AWS through a physical data centre to Azure, with asymmetric routing detected and root-cause classified
**Depends on**: Phase 2
**Requirements**: FDM-01, FDM-02, FDM-03, AWS-01, AWS-02, AWS-03, AZN-01, AZN-02, AZN-03, CKP-01, CKP-02, DCA-01, DCA-02, DCA-03, DCA-04, DCA-05, DCA-06, DCA-07, DCA-08, DCA-09, ASA-01, ASA-02, ASA-03, PTH-01, PTH-02, PTH-03, ASY-01, ASY-02, ASY-03, FMV-01, FMV-02, FMV-03, FMV-04, FMV-05, NFN-01, NFN-02, TIR-01, TIR-02
**Success Criteria** (what must be TRUE):
  1. The DC Collector Agent binary installs on a Linux server, connects to a Cisco IOS-XE router via NETCONF (or SSH fallback), and pushes route tables, BGP state, and NetFlow aggregates to the InfraCanvas API within 5 minutes of setup
  2. The FlowMap viewer shows a dual-colour path (blue forward, orange return) across AWS TGW -> data centre -> Azure vWAN, with Checkpoint and ASA/FTD firewall nodes displayed
  3. Asymmetric routing is detected with root cause classified (BGP_LOCAL_PREF vs ROUTE_LEAK vs NAT_ASYMMETRY) and a CRITICAL finding raised when a stateful firewall sits on only one path
  4. NET-001 through NET-012 network findings appear in the findings panel; route changes trigger alerts compared to the previous scan baseline
  5. FlowMap is accessible only on Team/Enterprise tier ($299/mo Stripe product); free/Pro users see a gated upgrade prompt
**Plans**: TBD

### Phase 4: SaaS Dashboard + CostLens
**Goal**: Teams can collaborate on infrastructure scans in a web dashboard, shared cost is allocated across workloads, and the full viewer (Canvas + FlowMap + CostLens) is embedded in Next.js — with the viewer extracted to a shared package before any dashboard work begins
**Depends on**: Phase 3
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, TMM-01, TMM-02, HST-01, HST-02, HST-03, SHR-01, SHR-02, WBH-01, WBH-02, WBH-03, CLA-01, CLA-02, CLA-03, CLA-04, CLA-05, CLA-06, CPC-01, CPC-02, CPC-03, DSH-01, DSH-02, DSH-03, DSH-04, DSH-05, DSH-06, OBS-01, OBS-02
**Success Criteria** (what must be TRUE):
  1. A user signs up via Clerk, creates a project, uploads a scan via CLI (`--api-key`), and views the full interactive Canvas + FlowMap + CostLens diagram in the Next.js dashboard within 60 seconds
  2. Team owners can invite members with role-based access (owner/admin/member/viewer); RLS enforces per-team data isolation with no row leakage across orgs
  3. A shared link (UUID + token, optional password, expiry) gives read-only public access to a scan without authentication
  4. A GitHub push webhook triggers an automatic scan, stores history in Neon + R2, and sends a Critical-findings Slack alert — all via taskiq background jobs
  5. The CostLens panel shows TGW/ExpressRoute/Azure Firewall shared costs split by workload tag, cross-cloud data transfer costs per FlowMap path, and idle/oversized resource recommendations
**Plans**: TBD

### Phase 5: Enterprise
**Goal**: Enterprise customers can map findings to SOC2/HIPAA/PCI-DSS controls, deploy InfraCanvas on-premises, enforce custom policies via OPA/Rego, and trace why two endpoints cannot communicate
**Depends on**: Phase 4
**Requirements**: CMP-01, CMP-02, CMP-03, SSO-01, SSO-02, SSO-03, REG-01, REG-02, SLF-01, SLF-02, SLF-03, PRB-01, PRB-02, NMS-01, NMS-02, NMS-03, NVA-01, NVA-02, ZSC-01, ZSC-02, ZSC-03, WIZ-01, WIZ-02, WIZ-03, ENT-01, ENT-02
**Success Criteria** (what must be TRUE):
  1. `infracanvas score --compliance=soc2` produces a control coverage report mapping findings to SOC2 controls, with an evidence export PDF ready for an auditor
  2. A SAML 2.0 SSO login works end-to-end; all API actions appear in the paginated audit log exportable as CSV/PDF
  3. `docker compose up` brings up the full self-hosted stack (api, dashboard, worker, postgres, redis) with no external API calls in air-gapped mode
  4. A GitHub PR against a Terraform repo triggers the GitHub App bot to post a diagram diff and security delta as a PR comment with a pass/fail status check
  5. `infracanvas trace --from=10.0.1.5 --to=10.2.3.8` identifies the blocking security group rule, NACL entry, or firewall policy and outputs the exact Terraform change needed to fix it
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 0 -> 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Validation | 0/3 | Planning complete | - |
| 1. Canvas MVP | 0/7 | Planning complete | - |
| 2. Canvas v1.0 | 0/TBD | Not started | - |
| 3. FlowMap v1.0 | 0/TBD | Not started | - |
| 4. SaaS Dashboard + CostLens | 0/TBD | Not started | - |
| 5. Enterprise | 0/TBD | Not started | - |
