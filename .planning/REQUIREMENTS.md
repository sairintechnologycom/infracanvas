# Requirements — InfraCanvas v1.1

**Milestone:** v1.1 Hardening + SaaS Dashboard + CostLens + FlowMap 3b
**Started:** 2026-04-20
**Status:** Defining

## Goal

Close E2E wiring gaps surfaced by v1.0 post-ship review, then deliver team SaaS dashboard, shared-cost allocation (CostLens), and DC Agent with asymmetric routing detection.

---

## v1.1 Requirements

### Category 1 — E2E Wiring Hardening (NEW this milestone)

Source: v1.0 post-ship E2E wiring review (2026-04-20). Blocks clean handoff to SaaS work.

- [ ] **WRG-01** CLI `export` command passes explicit `gate_mode` to `export_html()` and raises `typer.Exit()` with deterministic exit codes (0 on success, 1 on missing file, 2 on parse error)
- [ ] **WRG-02** `DriftAnalyzer` summary counts include `unchanged` and `shadow` drift statuses; `summary.drift_counts` totals match the node count for all drift states
- [ ] **WRG-03** Viewer exposes Canvas ↔ FlowMap tab toggle tied to `activeTab` store state; tab switch is reachable from the UI without editing code or URL params
- [ ] **WRG-04** Python pytest suites for `cli/infracanvas/security/` (rule engine + all 51 rules), `cli/infracanvas/cost/` (estimator + region multipliers + delta), and `cli/infracanvas/drift/` (analyzer with added/changed/deleted/unchanged/shadow) — positive + negative fixtures for each

### Category 2 — SaaS Backend (API)

- [ ] **API-01** FastAPI application scaffold on Railway or Fly.io with health endpoint
- [ ] **API-02** Clerk authentication middleware validating session tokens on protected routes
- [ ] **API-03** Neon PostgreSQL via session-mode pooler with dedicated `infracanvas_app` role (no BYPASSRLS)
- [x] **API-04
** R2 object storage client for scan artifact uploads
- [ ] **API-05** taskiq job queue with worker process for async jobs
- [x] **API-06
** Scan upload endpoint — multipart form, stores JSON in R2 + metadata in Neon
- [x] **API-07
** Scan retrieval endpoint — returns signed R2 URL + Neon metadata

### Category 3 — Team Management (TMM)

- [ ] **TMM-01** Team roles (owner/admin/member/viewer) with RLS-enforced per-team data isolation in Neon
- [x] **TMM-02
** Stripe Billing Meters integration — usage events posted on scan upload

### Category 4 — Scan History (HST)

- [ ] **HST-01** List scans endpoint with pagination, filtered by team
- [ ] **HST-02** Compare two scans — diff view (resources added/removed/changed) exposed via API
- [ ] **HST-03** Dashboard scan-list UI showing timestamp, commit SHA, score, critical count

### Category 5 — Share Links (SHR)

- [ ] **SHR-01** Generate share link with UUID + token, optional password, configurable expiry
- [ ] **SHR-02** Public share-link landing page rendering the scan viewer without auth

### Category 6 — GitHub Integration (WBH)

- [x] **WBH-01** GitHub push webhook endpoint — verifies signature, enqueues scan job (Validated in Phase 8: GitHub Webhook + Auto-scan)
- [x] **WBH-02** Auto-scan worker — clones repo, runs `infracanvas scan`, stores result in Neon + R2 (Validated in Phase 8: GitHub Webhook + Auto-scan)
- [x] **WBH-03** Slack alert on Critical findings (team-configured webhook URL) (Validated in Phase 8: GitHub Webhook + Auto-scan)

### Category 7 — CostLens Shared Cost (CLA / CPC)

- [x] **CLA-01** TGW attachment cost split by workload tag (resources attached to the TGW)
- [x] **CLA-02** ExpressRoute circuit cost split by connected vNet workload tag
- [x] **CLA-03** Azure Firewall cost split by route-table-referenced workloads
- [x] **CLA-04** Shared NAT Gateway + VPC Endpoint cost split by traffic share
- [x] **CLA-05** Idle/oversized resource recommendations
- [x] **CLA-06** CostLens dashboard panel showing allocated vs shared cost per workload
- [x] **CPC-01** Per-path cross-cloud data transfer cost computation
- [ ] **CPC-02** Flow-log-driven data transfer attribution
- [x] **CPC-03** Cost-aware path ranking in FlowMap viewer

### Category 8 — Dashboard UI (DSH)

- [x] **DSH-01** Extract viewer to shared dual-build npm package BEFORE any dashboard work (Phase 5, 2026-04-21)
- [ ] **DSH-02** Next.js 15 App Router scaffold on Vercel (uncached-by-default)
- [ ] **DSH-03** Dashboard auth flow via Clerk with team context
- [ ] **DSH-04** Scan list page + detail page embedding the shared viewer
- [ ] **DSH-05** Settings page — team members, billing, integrations
- [ ] **DSH-06** Responsive layout works on 1440p and 1080p viewports

### Category 9 — Observability (OBS)

- [ ] **OBS-01** Structured logging with request IDs + team context
- [ ] **OBS-02** Error tracking (Sentry or equivalent) + trace sampling

### Category 10 — DC Agent Core (DCA)

- [ ] **DCA-01** Go DC Agent scaffold — cobra CLI, daemon mode, single binary Linux amd64 + macOS arm64
- [ ] **DCA-02** Cisco NETCONF/RESTCONF client for IOS-XE
- [ ] **DCA-03** SSH CLI fallback for NETCONF-unsupported devices
- [ ] **DCA-04** NetFlow v9/IPFIX UDP collector via netsampler/goflow2/v2
- [ ] **DCA-05** Encrypted API push to cloud backend
- [ ] **DCA-06** Daemon timing — routes 5 min, BGP 1 min, NetFlow 30 s
- [ ] **DCA-07** Config file import fallback mode (no network access)
- [ ] **DCA-08** Cross-compiled binaries + GHA release workflow
- [ ] **DCA-09** Enterprise CAB security-review packet (architecture, data flow, threat model)

### Category 11 — Firewall / Security Device Integration

- [ ] **ASA-01** Cisco ASA REST API client
- [ ] **ASA-02** Cisco FMC REST API client
- [ ] **ASA-03** Cisco ASA SSH fallback
- [ ] **CKP-01** Checkpoint Management API integration
- [ ] **CKP-02** Checkpoint rule-base export parser

### Category 12 — Path Computation + Asymmetric Routing (PTH / ASY)

- [ ] **PTH-01** Forward-path computation from route + policy data
- [ ] **PTH-02** Return-path computation
- [ ] **PTH-03** NetFlow correlation validating computed paths against observed flows
- [ ] **ASY-01** Asymmetric routing detector — compares forward vs return paths
- [ ] **ASY-02** Root-cause classifier (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY)
- [ ] **ASY-03** Impact scoring — which flows affected, which firewalls see asymmetric state
- [ ] **NET-010** Stateful-firewall asymmetry rule (reserved in v1.0, activated in 3b)

### Category 13 — FlowMap Viewer Additions

- [ ] **FMV-02** Path divergence marker in FlowMap viewer
- [ ] **NFN-02** Route-change alerting on DC-agent-detected route churn

### Category 14 — Team Tier Gating (TIR)

- [ ] **TIR-01** Team-tier feature gate on FlowMap 3b + CostLens features
- [ ] **TIR-02** Stripe product for Team tier at $299/mo with FlowMap 3b + CostLens included

---

## Future Requirements (deferred beyond v1.1)

- v1.2 Enterprise: SOC2/HIPAA/PCI-DSS compliance framework + SSO + OPA/Rego (CMP-01..03, SSO-01..03, REG-01..02, SLF-01..03, PRB-01..02, NMS-01..03, NVA-01..02, ZSC-01..03, WIZ-01..03)

## Out of Scope

- GCP support — Year 2
- Pulumi / CDK / Bicep — Year 2
- Live cloud import (no Terraform) — Year 2
- AI natural language queries — Year 2
- SBOM integration — Year 2
- Terragrunt / workspaces — not supported at launch
- Mobile app — web-first, CLI-first

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| WRG-01..04 | 4 | TBD | Not planned |
| DSH-01 | 5 | 05-01..03 | ✓ Validated (2026-04-21) |
| API-01..07, TMM-01..02, OBS-01..02 | 6 | TBD | Not planned |
| DSH-02..06, HST-01..03, SHR-01..02 | 7 | TBD | Not planned |
| WBH-01..03 | 8 | 2026-05-05 | Complete |
| CLA-01..06, CPC-01, CPC-03 | 9 | 7/7 | Complete 2026-05-06 |
| DCA-01..09 | 10 | TBD | Not planned |
| ASA-01..03, CKP-01..02 | 11 | TBD | Not planned |
| PTH-01..03, ASY-01..03, NET-010, FMV-02, NFN-02 | 12 | TBD | Not planned |
| TIR-01..02 | 13 | TBD | Not planned |
