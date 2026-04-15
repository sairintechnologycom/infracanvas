# Project Research Summary

**Project:** InfraCanvas v2.0 — Hybrid Cloud Infrastructure Intelligence Platform
**Domain:** IaC Visualization + Hybrid Network Topology + Shared Cost Allocation
**Researched:** 2026-04-15
**Confidence:** HIGH

## Executive Summary

InfraCanvas v2.0 occupies an unoccupied market intersection — IaC-first security visualization + hybrid network topology + shared cost allocation — at price points that undercut the nearest comparable tool (NetBrain, $100K+ ACV) by 100x. The recommended 5-phase approach follows a strict dependency chain: harden the CLI core and add Azure (Phase 2), ship the Go DC Collector Agent and FlowMap path tracer (Phase 3), launch the FastAPI SaaS with CostLens (Phase 4), then add Enterprise compliance and self-hosted deployment (Phase 5). The most dangerous risks are the pre-existing HCL parser silent failure pattern, multi-tenant RLS session leakage, viewer codebase divergence, and BGP false-positive asymmetry alerts — all must be architected out before their respective phases begin.

## Key Stack Corrections

1. **Replace `arq` with `taskiq`** — arq is maintenance-only (GitHub #437). taskiq + taskiq-redis is async-native, production-stable, same Redis broker.
2. **Next.js 15 not 14** — Stable, uncached-by-default behavior is correct for SaaS where stale scan data is a correctness bug.
3. **Stripe Billing Meters only** — Legacy `create_usage_record()` removed in API 2025-03-31. Must use Billing Meters from day one.
4. **goflow2 not goflow** — Cloudflare goflow was archived Feb 2025. Use `netsampler/goflow2/v2`.
5. **Add observability** — Sentry + Logfire (or similar) required before Phase 4 ships. Silent billing webhook failures are the most dangerous bug class.

## Table Stakes Features

**Canvas:** Interactive diagram, resource grouping, security findings, drift, score card, CI/CD mode, HTML export (already built). Azure parser, shadow infra detection, 30 AWS rules (Phase 2).

**FlowMap:** AWS + Azure network topology collection, DC site visualization via DC Agent, forward/return path tracing, asymmetric routing detection with root-cause classification, firewall capacity monitoring (Phase 3).

**CostLens:** Shared service cost identification (TGW, ExpressRoute, Firewall), showback reporting, cost trend (Phase 4). Per-path cost analysis is the unique differentiator (Phase 4).

## Differentiators

- Asymmetric routing detection at Team tier pricing ($299/mo vs NetBrain $100K+ ACV)
- Per-path cost analysis (FlowMap path x CostLens cost model — no competitor does this)
- PCI-DSS network segmentation verification via FlowMap (unique cross-product moat)
- Read-only stance eliminates credential storage, blast-radius liability, state locking complexity
- Open-core CLI drives PLG adoption; commercial FlowMap/CostLens/SaaS drives revenue

## Critical Pitfalls

1. **HCL parser silent failures** (blocking Phase 2) — python-hcl2 returns partial results on ~15% of complex modules. Fix before Azure parser.
2. **BGP asymmetry false positives** (Phase 3) — BGP asymmetry is intentional in enterprise networks. Must classify cause (BGP_LOCAL_PREF = expected vs ROUTE_LEAK = alert).
3. **DC Agent enterprise approval** (Phase 3) — 4-12 week CAB approval. Need security review packet, minimum-privilege design, SSH fallback.
4. **RLS session leakage** (Phase 4) — SET LOCAL can persist under PgBouncer transaction-mode. Use Neon session-mode pooler, dedicated app role with no BYPASSRLS.
5. **Viewer codebase divergence** (Phase 4) — Extract viewer to shared package before any Next.js work begins.
6. **Compliance framework tags** — Must embed CIS/NIST/SOC2/PCI-DSS metadata on security rules during Phase 2, not Phase 5.

## Architecture Approach

- **Viewer dual-build:** Single React package with two Vite configs — `vite-plugin-singlefile` for CLI HTML, `lib` mode for SaaS dashboard import.
- **DC Agent:** Outbound-only HTTP POST with JSON + pre-shared API key. Push-based snapshots (like Datadog/Grafana Agent pattern).
- **Multi-tenant:** RLS via `SET LOCAL app.current_org` on every connection checkout. Dedicated `infracanvas_app` role.
- **CLI to API shared models:** Monorepo path dependency — CLI Python modules importable by FastAPI directly.
- **Artifact storage:** Neon for scalars (scan metadata), R2 for blobs (scan JSON, HTML). Write Neon first, R2 second.

## Suggested Phase Structure

| # | Phase | Goal | Research Flag |
|---|-------|------|---------------|
| 2 | Canvas v1.0 | Azure + policy engine + 30 rules + shadow infra + cost | Skip research |
| 3 | FlowMap v1.0 | DC Agent + hybrid topology + asymmetric routing | Needs research (Cisco NETCONF compat) |
| 4 | SaaS + CostLens | FastAPI + Neon + Clerk + Stripe + shared cost allocation | Skip research |
| 5 | Enterprise | Compliance + SSO + self-hosted + OPA/Rego | Needs research (OPA integration, Helm) |

## Open Questions

1. Should CLI and FastAPI share a `infracanvas-core` PyPI package for Pydantic models?
2. DC Agent auth: pre-shared API key (v1) vs mTLS certificate (Phase 5 Enterprise)?
3. Logfire free tier limits — verify before committing as observability solution.
4. Security rule schema: add `framework_ids: list[str]` field before Phase 2 begins.

---
*Synthesized: 2026-04-15 from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
