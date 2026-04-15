# InfraCanvas

## What This Is

InfraCanvas is a CLI tool and SaaS platform that parses Terraform code to generate interactive architecture diagrams annotated with security findings, drift markers, cost estimates, and compliance scores. It targets platform engineers, cloud architects, and security engineers who need visual infrastructure understanding without manual diagramming.

## Core Value

One command gives you a complete, annotated picture of your infrastructure — security blind spots, drift, and cost — so you never have to manually assemble that picture from 5 different tools again.

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

- [ ] SaaS dashboard with Next.js frontend
- [ ] FastAPI backend with API for scans, projects, sharing
- [ ] Authentication (provider TBD — research Clerk, Supabase Auth, Auth.js)
- [ ] Supabase PostgreSQL for projects, scans, users, teams
- [ ] Shareable diagram links (public/private, optional password)
- [ ] Scan history timeline with point-in-time diagram viewing
- [ ] Scan comparison (side-by-side diff of two scans)
- [ ] CI/CD webhook endpoint (auto-scan on push to main)
- [ ] CLI `login` command for SaaS authentication
- [ ] CLI `push` command to upload scan results to SaaS
- [ ] Expand security rules from 10 to 30 (per PLAN.md targets)
- [ ] Fix silent HCL parse failures (log warnings, report skipped files)
- [ ] Multi-region cost estimation (detect region from resource attributes)
- [ ] YAML rule schema validation (fail fast on malformed rules)
- [ ] Pro tier billing (Stripe integration, $49/mo)
- [ ] Team tier billing ($199/mo, up to 10 users)

### Out of Scope

- Multi-cloud support (Azure, GCP) — defer to v2, AWS-first for MVP
- PR review bot (GitHub/GitLab) — defer to v2, manual sharing sufficient for now
- Custom policy engine (Rego/YAML) — defer to v2, 30 built-in rules sufficient
- Pulumi/CDK support — defer to v2, Terraform-only for now
- Live cloud import (direct AWS API) — defer to v2, Terraform files sufficient
- Slack/Teams integration — defer to v2, webhook + sharing covers notification needs
- AI insights / natural language queries — defer to v2+
- Self-hosted option — defer to v2, SaaS-first
- SSO/SAML (Enterprise tier) — defer post-MVP, Supabase/Clerk SSO can be added later

## Context

- CLI core is mature: Python 3.12, Typer, Pydantic, python-hcl2, NetworkX
- Viewer is React 18 + ReactFlow + Zustand + Tailwind, built as single-file HTML via Vite
- SaaS will be two services: Next.js frontend (Vercel) + FastAPI backend
- Supabase for database (PostgreSQL), object storage (scan artifacts), potentially auth
- Target: 200 Pro + 50 Team subscribers = $19,750 MRR within 12 months
- Solo founder — cost efficiency and operational simplicity are critical
- Open-source CLI core is part of GTM strategy (npm/pip, Homebrew, Show HN)
- Codebase has known concerns: silent parse failures, hardcoded us-east-1 pricing, no rule schema validation, graph layout O(n²) for large projects

## Constraints

- **Solo founder**: Must minimize operational complexity — no separate infrastructure to maintain
- **Cost**: SaaS hosting budget <$100/mo until revenue covers it
- **Stack**: Next.js frontend + FastAPI backend (decided), Supabase for database
- **Auth**: TBD — research will compare Clerk, Supabase Auth, Auth.js
- **CLI compatibility**: Python 3.12+, must remain pip-installable
- **Browser**: Modern browsers only (ES2020+), no IE support

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Next.js + FastAPI (two services) | Keep Python ecosystem for Terraform parsing logic, Next.js for modern frontend | — Pending |
| Supabase over Neon | Postgres + storage + potential auth in one platform, reduces vendor count | — Pending |
| Auth provider | Research needed — Clerk (managed), Supabase Auth (integrated), Auth.js (self-hosted) | — Pending |
| Open-source CLI core | PLG strategy — free CLI drives adoption, SaaS upsell for security + sharing | — Pending |
| AWS-only for v1 | Reduces scope dramatically, covers largest IaC market segment | — Pending |

---
*Last updated: 2026-04-15 after initialization*
