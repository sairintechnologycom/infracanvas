# InfraCanvas

## What This Is

InfraCanvas is a hybrid cloud intelligence platform that gives engineering and leadership teams a single visual pane of glass across AWS, Azure, and physical data centre infrastructure — showing configuration, security, network traffic paths, and cost in real time. It combines three products: Canvas (infrastructure diagrams + security), FlowMap (hybrid network topology + asymmetric routing detection), and CostLens (shared infrastructure cost allocation). CLI-first, open-core, with a SaaS dashboard for teams.

**Shipped in v1.0:** CLI + single-file HTML viewer for AWS + Azure with Canvas (40 rules + drift/shadow/policy/cost) and FlowMap cloud-only (network topology + 11 NET-* rules). Phase 3b DC Agent, SaaS dashboard, CostLens, and Enterprise features follow in v1.1/v1.2.

## Current State

**Latest milestone:** v1.0 (shipped 2026-04-19) — Canvas + FlowMap v1.0 Hybrid Cloud Intelligence MVP
**Focus:** Planning v1.1 — SaaS Dashboard + CostLens (Phase 4) alongside FlowMap 3b (DC Agent, path computation, asymmetric routing)

## Core Value

One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres, so you never have to manually correlate 5 different tools to answer "is our infrastructure in the state we think it is?"

## Requirements

### Validated (v1.0)

- ✓ HCL parser — resources, variables, locals, outputs, modules, implicit/explicit dependencies (PRS-01..05, v1.0)
- ✓ NetworkX resource graph with VPC/subnet/module/region grouping (GRF-01..03, v1.0)
- ✓ Typer CLI — scan, score, plan, export, serve (CLI-01..02, v1.0)
- ✓ Pydantic v2 data model — ResourceGraph v2.1, Finding, NetworkFinding, NetworkPath, PathHop, DCSite (FDM-01..03, v1.0)
- ✓ 30 AWS security rules (SEC-001..030) + 10 Azure rules (AZ-001..010) — all carry CIS/NIST/SOC2/PCI-DSS framework_ids (SEC-01..06, AZR-03, v1.0)
- ✓ 0–100 infrastructure health score + letter grades A/B/C/D/F across 5 dimensions (SCR-01..03, v1.0)
- ✓ React 18 + @xyflow/react + Zustand viewer with Dagre layout, group containers, filter, search, detail panel, free-tier gate (VWR-01..06, v1.0)
- ✓ Single-file HTML export < 5MB, zero external dependencies, auto-browser-open (EXP-01..02, v1.0)
- ✓ Terraform plan JSON reader with colour-coded drift overlay + before/after attribute diffs (PLN-01..03, v1.0)
- ✓ Shadow infrastructure detection — live AWS API vs Terraform state, 6 resource types, boto3 optional (SHD-01..02, v1.0)
- ✓ Multi-region cost estimation — 15 region multipliers (AWS + Azure), group-level aggregation (CST-01..03 static, v1.0)
- ✓ Azure provider — 10 core resource types with location→region normalisation (AZR-01..02, v1.0)
- ✓ Runtime staleness checks — Lambda EOL, EKS/AKS version lag, resource locks (RST-01..02, v1.0)
- ✓ Custom policy engine v1 — YAML policies, `.infracanvas.yml` auto-discovery, `--policy` flag (POL-01..02, v1.0)
- ✓ CLI CI integration — `--ci --fail-on --quiet --ignore --severity --watch` (CLX-01..02, v1.0)
- ✓ Multi-platform distribution — Dockerfile (non-root), PyInstaller spec, 3-platform GHA release workflow, Homebrew formula (DST-01..02, v1.0)
- ✓ AWS network topology collection — TGW route tables + attachments, VPC routes + NACLs, Direct Connect, CloudWatch flow log metadata (AWS-01..03, v1.0)
- ✓ Azure network topology collection — vWAN hubs + connections, vNet peering, NSG effective rules, ExpressRoute + NSG flow logs (AZN-01..03, v1.0)
- ✓ 11 NET-* network security rules with positive/negative fixtures (NFN-01 partial — NET-010 reserved for 3b, v1.0)
- ✓ FlowMap viewer — TabBar + FlowMapCanvas (4 custom node types + dual-color PathEdge) + FilterPanel + PathDetailPanel + EmptyState (FMV-01, 03, 04, 05, v1.0)

### Active (v1.1 — SaaS Dashboard + FlowMap 3b)

#### SaaS Dashboard + CostLens (Phase 4)

- [ ] FastAPI backend — Clerk auth, Neon PostgreSQL (session-mode pooler, dedicated infracanvas_app role, no BYPASSRLS), R2 object storage, taskiq job queue (API-01..07)
- [ ] Team features — roles (owner/admin/member/viewer), RLS-enforced per-team data isolation, Stripe billing meters (TMM-01..02)
- [ ] Scan history + comparison (HST-01..03)
- [ ] Share link system — UUID + token, optional password, expiry (SHR-01..02)
- [ ] GitHub push webhook — auto-scan, history in Neon + R2, Critical-findings Slack alert via taskiq (WBH-01..03)
- [ ] CostLens — TGW/ExpressRoute/Azure Firewall shared cost split by workload tag, cross-cloud per-path data transfer cost, idle/oversized recommendations (CLA-01..06, CPC-01..03)
- [ ] Next.js 15 dashboard — uncached-by-default; extract viewer to shared dual-build package BEFORE any dashboard work (DSH-01..06)
- [ ] Observability — logs, traces, error tracking (OBS-01..02)

#### FlowMap 3b (DC Agent + Asymmetric Routing)

- [ ] Go DC Agent scaffold (cobra CLI, daemon mode, single binary Linux amd64 + macOS arm64) (DCA-01, DCA-08)
- [ ] NETCONF/RESTCONF client for Cisco IOS-XE; SSH CLI fallback; config file import fallback (DCA-02..03, DCA-07)
- [ ] NetFlow v9/IPFIX UDP collector via netsampler/goflow2/v2 (DCA-04)
- [ ] Encrypted API push to cloud, daemon timing (routes 5m / BGP 1m / NetFlow 30s) (DCA-05..06)
- [ ] DC Agent enterprise CAB security-review packet (DCA-09)
- [ ] Cisco ASA REST API + FMC REST API + SSH fallback (ASA-01..03)
- [ ] Checkpoint Management API integration (CKP-01..02)
- [ ] Path computation — forward + return + NetFlow correlation (PTH-01..03)
- [ ] Asymmetric routing detector + root cause classifier (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY) + impact (ASY-01..03, NET-010)
- [ ] FMV-02 divergence marker; NFN-02 route-change alerting
- [ ] TIR-01..02 — Team-tier gating + $299/mo Stripe product

### Active (v1.2 — Enterprise)

- [ ] Compliance framework engine — SOC2/HIPAA/PCI-DSS control mapping, evidence-export PDF (CMP-01..03)
- [ ] SSO (SAML 2.0 via Clerk Enterprise) + audit logs (paginated, CSV/PDF export) (SSO-01..03)
- [ ] Custom policy engine v2 — OPA/Rego (REG-01..02)
- [ ] Self-hosted deployment (Docker Compose + Helm, air-gapped mode) (SLF-01..03)
- [ ] GitHub PR Bot — diagram diff + security delta as PR comment with status check (PRB-01..02)
- [ ] NMS integrations (SolarWinds, PRTG, NetBrain) (NMS-01..03)
- [ ] Palo Alto + Fortinet NVA support (NVA-01..02)
- [ ] Zscaler ZPA + ZDX integration (ZSC-01..03)
- [ ] Network troubleshooting wizard — `infracanvas trace --from X --to Y` (WIZ-01..03)

### Pre-release for v1.0

- [ ] REL-01..04 — First PyPI publish, Homebrew tap, GHA auto-publish validation, Show HN submission (configured but unexecuted)
- [ ] VAL-01..05 — Phase 0 human campaign: Stripe product setup, Typeform survey live, Reddit/LinkedIn/Discord warm-up + posts, 20 customer conversations, Go/No-Go decision

### Out of Scope

- GCP support — defer to v4.0 (Year 2), AWS + Azure covers target market
- Pulumi / CDK / Bicep support — defer to v4.0, Terraform-only for now
- Live cloud import (no Terraform required) — defer to v4.0
- AI natural language queries — defer to v4.0
- SBOM integration — defer to v4.0
- Terragrunt / workspaces — not supported at launch, expand based on demand
- Mobile app — web-first, CLI-first

## Context

- **v1.0 shipped**: ~14,065 LOC across Python (cli/) + TypeScript/TSX (viewer/, landing/). 32 plans delivered over 6 days.
- **CLI core**: Python 3.12, Typer, Pydantic v2, python-hcl2, NetworkX — mature, tested (204+ Python tests, 79 Vitest). HCL parser silent-failure hardening completed in Phase 2.
- **Viewer**: React 18 + @xyflow/react + Zustand + Tailwind; single-file HTML via Vite + vite-plugin-singlefile; bundle size 3.5 MB. Canvas and FlowMap tabs swap via React.lazy.
- **Rule inventory**: 51 rules total (30 AWS + 10 Azure + 11 NET). NET-010 reserved for 3b path-dependent detection. All rules carry `framework_ids` for CIS/NIST/SOC2/PCI-DSS.
- **Distribution**: Dockerfile + PyInstaller spec + 3-platform GHA release workflow + Homebrew formula all configured; first PyPI release execution pending.
- **Planned stacks** (v1.1+): DC Agent — Go single binary; SaaS Backend — FastAPI on Railway/Fly.io; SaaS Frontend — Next.js 15 on Vercel; DB — Neon PostgreSQL (session-mode pooler, dedicated infracanvas_app role, no BYPASSRLS); Auth — Clerk; Storage — R2; Queue — taskiq; Payments — Stripe Billing Meters.
- **Revenue target**: 200 Pro ($79/mo) + 50 Team ($299/mo) = $30,750 MRR within 12 months
- **Pricing tiers**: Free ($0), Pro ($79/mo), Team ($299/mo), Enterprise ($999+/mo)
- **Open-source strategy**: CLI core (parser, layout, icons, basic HTML export, JSON schema) is MIT. Security engine, FlowMap, DC agent, CostLens, SaaS are commercial.
- **Target personas**: Priya (Platform Engineer, installs CLI) → Alex (Cloud Architect, pays) → Sam (Security/Network Engineer, drives Enterprise)

## Constraints

- **Solo founder**: Must minimize operational complexity — no separate infrastructure to maintain
- **Cost**: SaaS hosting budget $10–104/mo until revenue (Railway/Fly.io + Vercel + Neon + R2 + Upstash + Clerk)
- **CLI stack**: Python 3.12+, pip-installable + PyInstaller standalone binary
- **DC Agent stack**: Go, single binary, cross-compiled Linux amd64 + macOS arm64
- **Frontend stack**: Next.js 15 App Router on Vercel (was 14 pre-v1.1 planning; uncached-by-default is correct for SaaS)
- **Backend stack**: FastAPI on Railway or Fly.io
- **Browser**: Modern browsers only (ES2020+), no IE support
- **Performance**: Parse 500 resources < 10s, FlowMap topology < 20s, HTML < 5MB (all met in v1.0)
- **Security**: No cloud credentials stored. CLI scans are local-only. DC agent read-only, outbound-only.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python CLI + Go DC Agent | Python for fast iteration on domain logic; Go for zero-dep DC binary | ✓ Good (Python CLI shipped v1.0; Go DC Agent in v1.1 3b) |
| Fix HCL parser silent failures BEFORE Azure parser | python-hcl2 returns partial results on ~15% of complex modules; silent failures would block debugging Azure issues | ✓ Good (02-01 added parse_errors collection; surfaced as warnings) |
| Add compliance framework tags in Phase 2, not Phase 5 | Selling point for Pro tier; easier to bake into rule schema early than retrofit | ✓ Good (all 40 v1.0 rules carry framework_ids; used by FindingCard UI) |
| FlowMap cloud-only in v1.0; DC Agent to 3b | DC Agent CAB approval takes 4–12 weeks; cloud-only is shippable in v1.0 timeline | ✓ Good (24 reqs cleanly deferred with explicit scope note; no orphans) |
| NET-010 reserved for 3b | Stateful-firewall asymmetry detection requires path computation (ASY-03) which lands in 3b | ✓ Good (placeholder + test_net_010_reserved_for_phase_3b guard) |
| Infracost API deferred to Phase 4 | Static region multipliers cover v1.0 CST-01..03; API integration belongs with SaaS backend credentials | ✓ Good (Phase 2 shipped static pricing; no user complaints yet) |
| Single-file HTML export via vite-plugin-singlefile | Zero runtime deps; HTML distributes via email/Slack; CLI-first UX | ✓ Good (421KB for MVP, 3.5 MB with FlowMap; all targets met) |
| Neon session-mode pooler + dedicated infracanvas_app role (no BYPASSRLS) | Prevents RLS leakage across teams — known Supabase/Neon footgun | — Pending (Phase 4) |
| taskiq over arq | arq is maintenance-only | — Pending (Phase 4) |
| Next.js 15 over Next.js 14 | Uncached-by-default is correct for SaaS dashboards with per-user data | — Pending (Phase 4) |
| Stripe Billing Meters only | Legacy create_usage_record() removed 2025-03-31 | — Pending (Phase 4) |
| netsampler/goflow2/v2 over goflow | Original goflow archived Feb 2025 | — Pending (Phase 3b) |
| Extract viewer to shared dual-build package BEFORE any Next.js dashboard work | Divergence between CLI viewer and dashboard viewer creates long-term maintenance liability | — Pending (Phase 4 gate) |
| Cisco NETCONF compatibility research BEFORE DCA-02 planning | Compatibility matrix unknown; research → planning order | — Pending (Phase 3b gate) |
| Retroactive VERIFICATION.md (Phase 3.5) | Closing audit gaps post-hoc is cheaper than re-running phases; SUMMARYs/UATs/SECURITYs already carry the evidence | ✓ Good (3 documents authored; Nyquist 0/4 → 3/4; no code changes needed) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-19 after v1.0 milestone*
