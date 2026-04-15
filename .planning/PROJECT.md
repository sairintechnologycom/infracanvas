# InfraCanvas

## What This Is

InfraCanvas is a hybrid cloud intelligence platform that gives engineering and leadership teams a single visual pane of glass across AWS, Azure, and physical data centre infrastructure — showing configuration, security, network traffic paths, and cost in real time. It combines three products: Canvas (infrastructure diagrams + security), FlowMap (hybrid network topology + asymmetric routing detection), and CostLens (shared infrastructure cost allocation). CLI-first, open-core, with a SaaS dashboard for teams.

## Core Value

One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres, so you never have to manually correlate 5 different tools to answer "is our infrastructure in the state we think it is?"

## Requirements

### Validated

- ✓ HCL parser extracts resources, dependencies, modules, variables from .tf files — existing
- ✓ Resource graph builder creates nodes/edges with VPC/subnet grouping — existing
- ✓ Interactive React/ReactFlow diagram with zoom, pan, search, filter — existing
- ✓ 10 security rules (S3, IAM, RDS, EC2, KMS, networking) with severity badges — existing
- ✓ Drift detection overlays terraform plan changes on diagram — existing
- ✓ Cost estimation per resource and per group (us-east-1) — existing
- ✓ Security score card with letter grades across categories — existing
- ✓ CLI commands: scan, score, plan, export, watch — existing
- ✓ Single-file HTML export with embedded graph data — existing
- ✓ CI/CD mode with exit codes and JSON output — existing
- ✓ .infracanvas.yml configuration file support — existing

### Active

#### Canvas v1.0 (Phase 2)
- [ ] Terraform plan reader (plan JSON diff)
- [ ] Shadow infrastructure detection (live AWS API vs Terraform state)
- [ ] AWS security rules expansion to 30 rules (SEC-011 through SEC-030)
- [ ] Azure parser — 10 core resource types
- [ ] Azure security rules (AZ-001 through AZ-010)
- [ ] Runtime staleness checks (Lambda EOL, EKS/AKS version lag)
- [ ] Custom policy engine v1 (YAML — naming, tags, regions, instance types)
- [ ] Resource lock validation
- [ ] Multi-region cost estimation
- [ ] CLI polish: --ci, --watch, --ignore, --severity, --quiet flags
- [ ] Docker image + multi-platform binary distribution

#### FlowMap v1.0 (Phase 3)
- [ ] FlowMap data model (NetworkPath, PathHop, DCCollectorReading, NetworkFinding)
- [ ] AWS network topology collection (TGW, VPC routes, NACLs, Direct Connect)
- [ ] Azure network topology collection (vWAN, Secure Hub, vNet peering, ExpressRoute)
- [ ] Checkpoint Management API integration (policies, NAT, VPN, hit counts)
- [ ] DC Collector Agent — Cisco Router (Go, NETCONF/RESTCONF, SSH fallback, NetFlow)
- [ ] DC Collector Agent — Cisco ASA + FTD (REST API, FMC API)
- [ ] Path tracer engine (forward + return path computation across hybrid topology)
- [ ] Asymmetric routing detector (divergence detection, root cause classification)
- [ ] FlowMap viewer components (dual-path rendering, DC site groups, firewall capacity)
- [ ] Network findings engine (NET-001 through NET-012)

#### SaaS Dashboard + CostLens (Phase 4)
- [ ] FastAPI backend (projects, scans, auth via Clerk, Neon PostgreSQL, R2 storage)
- [ ] Team features (roles, RLS, Stripe billing)
- [ ] Scan history + comparison
- [ ] Share link system (UUID + token, optional password, expiry)
- [ ] CI/CD webhook (auto-scan on push, Slack/Teams alerts)
- [ ] CostLens shared cost allocation (TGW, Secure Hub, ExpressRoute, Firewall throughput)
- [ ] Cross-cloud per-path cost analysis + optimisation recommendations
- [ ] Next.js dashboard (project views, scan detail, team management, billing)

#### Enterprise (Phase 5)
- [ ] Compliance framework engine (SOC2, HIPAA, PCI-DSS mapping + evidence export)
- [ ] SSO (SAML/OIDC via Clerk Enterprise) + audit logs
- [ ] Custom policy engine v2 (OPA/Rego)
- [ ] Self-hosted deployment (Docker Compose + Helm)
- [ ] GitHub PR Bot (diagram diff + security delta as PR comment)
- [ ] NMS integrations (SolarWinds, PRTG, NetBrain)
- [ ] Palo Alto + Fortinet NVA support
- [ ] Zscaler ZPA + ZDX integration
- [ ] Network troubleshooting wizard ("Why can't X reach Y?")

### Out of Scope

- GCP support — defer to v4.0 (Year 2), AWS + Azure covers target market
- Pulumi / CDK / Bicep support — defer to v4.0, Terraform-only for now
- Live cloud import (no Terraform required) — defer to v4.0
- AI natural language queries — defer to v4.0
- SBOM integration — defer to v4.0
- Terragrunt / workspaces — not supported at launch, expand based on demand
- Mobile app — web-first, CLI-first

## Context

- **CLI core**: Python 3.12, Typer, Pydantic v2, python-hcl2, NetworkX. Mature and working.
- **Viewer**: React 18 + @xyflow/react + Zustand + Tailwind, built as single-file HTML via Vite + vite-plugin-singlefile
- **DC Agent**: Go — single binary, zero runtime deps, NETCONF/SSH/NetFlow
- **SaaS Backend**: FastAPI (Python) — same language as CLI
- **SaaS Frontend**: Next.js 14 (App Router) + shadcn/ui + TanStack Query
- **Database**: Neon PostgreSQL (serverless, scales to zero, RLS)
- **Auth**: Clerk (managed auth, SSO for Enterprise)
- **Object Storage**: Cloudflare R2 (zero egress fees — critical for scan artifacts)
- **Cache/Queue**: Upstash Redis (session, rate limiting, arq job queue)
- **Payments**: Stripe (subscriptions, usage metering)
- **Target personas**: Priya (Platform Engineer, installs CLI) → Alex (Cloud Architect, pays) → Sam (Security/Network Engineer, drives Enterprise)
- **Revenue target**: 200 Pro ($79/mo) + 50 Team ($299/mo) = $30,750 MRR within 12 months
- **Pricing tiers**: Free ($0), Pro ($79/mo), Team ($299/mo), Enterprise ($999+/mo)
- **Open-source strategy**: CLI core (parser, layout, icons, basic HTML export, JSON schema) is MIT. Security engine, FlowMap, DC agent, CostLens, SaaS are commercial.
- **Codebase concerns**: silent parse failures, hardcoded us-east-1 pricing, no rule schema validation, graph layout O(n²) for large projects

## Constraints

- **Solo founder**: Must minimize operational complexity — no separate infrastructure to maintain
- **Cost**: SaaS hosting budget $10–104/mo until revenue (Railway/Fly.io + Vercel + Neon + R2 + Upstash + Clerk)
- **CLI stack**: Python 3.12+, pip-installable + PyInstaller standalone binary
- **DC Agent stack**: Go, single binary, cross-compiled Linux amd64 + macOS arm64
- **Frontend stack**: Next.js 14 App Router on Vercel
- **Backend stack**: FastAPI on Railway or Fly.io
- **Browser**: Modern browsers only (ES2020+), no IE support
- **Performance**: Parse 500 resources < 10s, FlowMap topology < 20s, HTML < 5MB
- **Security**: No cloud credentials stored. CLI scans are local-only. DC agent read-only, outbound-only.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python CLI + Go DC Agent | Python for fast iteration on domain logic; Go for zero-dep DC binary | — Pending |
| Neon PostgreSQL over Supabase | Serverless, scales to zero, built-in connection pooling, RLS | — Pending |
| Clerk over Supabase Auth | Managed auth with SSO/SAML for Enterprise tier, generous free tier | — Pending |
| Cloudflare R2 over Supabase Storage | Zero egress fees critical for large scan artifacts | — Pending |
| React Flow over D3 | Built-in zoom/pan/minimap, custom nodes, edge routing, TypeScript | — Pending |
| Open-source CLI core (MIT) | PLG strategy — HashiCorp/Grafana model, drives adoption | — Pending |
| Three-product architecture (Canvas/FlowMap/CostLens) | Different buyer conversations, progressive tier unlock | — Pending |
| FlowMap as moat | No competitor does hybrid topology + asymmetric routing at this price point | — Pending |

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
*Last updated: 2026-04-15 after v2.0 reinitialize*
