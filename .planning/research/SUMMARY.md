# Project Research Summary

**Project:** InfraCanvas
**Domain:** IaC Visualization and Security SaaS — CLI-to-SaaS transition
**Researched:** 2026-04-15
**Confidence:** MEDIUM-HIGH

## Executive Summary

InfraCanvas occupies a clear niche: no major competitor combines interactive visualization + native security scoring + cost estimation + visual scan comparison in a read-only SaaS. The "no execution" positioning is a deliberate advantage — eliminates compliance and blast-radius concerns that make Terraform Cloud/Spacelift complex.

**Recommended stack:** Next.js 15 (App Router) + FastAPI 0.111+ deployed as Vercel Services under one domain. Supabase for Postgres, object storage, and auth. Stripe for billing.

**Key auth decision:** Supabase Auth over Clerk — users live in the same Postgres instance, RLS works natively with `auth.uid()`, included in $25/mo Pro plan regardless of MAU. Clerk charges per MAU with steep cliff above 10k.

**Critical build order:** Database schema → FastAPI auth → CLI push → Dashboard → Sharing + Billing → Teams + Webhooks. Nothing is buildable until the first three links in this chain exist.

## Key Findings

### Stack
- **Supabase Auth over Clerk**: Same-database users, native RLS, included in Supabase pricing
- **Auth.js is not a fit**: No admin SDK, no FastAPI integration, adds complexity without benefit
- **Vercel Services**: Next.js at `/` + FastAPI at `/api` via `experimentalServices` — no CORS, atomic deploys
- **Full hosting under $45/mo**: Vercel Pro $20 + Supabase Pro $25 covers early growth
- **Dual CLI tokens**: Supabase JWT for interactive login, opaque API keys for CI/CD
- **`@supabase/auth-helpers-nextjs` is deprecated** — must use `@supabase/ssr` 0.5.x

### Features
- **Auth + scan storage are root dependencies** — nothing SaaS works without them
- **ReactFlow viewer adaptation is highest-complexity task** — from `window.__INFRACANVAS_DATA__` to React props
- **Scan comparison diff is strongest differentiator** — no competitor offers it
- **Five anti-features to resist**: Terraform execution, PR bot, custom policy engine, multi-cloud, AI suggestions

### Architecture
- **Split scan storage**: Metadata in Postgres (fast queries), full ResourceGraph blob in Supabase Storage
- **CLI analysis modules import directly into FastAPI** — no reimplementation needed
- **Viewer needs one refactor**: Export `<InfraCanvasViewer data={graph} />` as shared component
- **Build order is strict**: Schema → Auth → CLI push → Dashboard diagram view

### Pitfalls
1. **Viewer divergence (BLOCKING)**: Extract shared component before any SaaS frontend work
2. **Silent parse failures (BLOCKING)**: Fix before first SaaS scan — trust-destroying in multi-tenant context
3. **Stripe webhooks incomplete**: Build `payment_failed` + `subscription.deleted` handlers as billing acceptance criteria
4. **CLI push API unversioned**: Ship as `/api/v1/scans` from day one with `cli_version` in request
5. **Auth header not propagated**: Next.js server components calling FastAPI must forward JWT — invisible in isolated testing

## Roadmap Implications

| Phase | Focus | Rationale |
|-------|-------|-----------|
| 0 | Pre-SaaS CLI hardening | Silent failures become trust failures in SaaS context |
| 1 | Foundation: Schema + Auth + Shared Viewer | Root dependencies — everything gates on this |
| 2 | CLI Bridge: login + push | Only ingest path — validates entire data pipeline before UI work |
| 3 | Core Dashboard: Projects + History + Diagram | Minimum viable product experience |
| 4 | Sharing + Billing | Launch gates — viral loop + revenue |
| 5 | Team Tier + CI/CD Webhooks | Monetization expansion + friction reduction |
| 6 | Analytics + Comparison | Requires accumulated user data; strongest differentiator |

## Research Flags

**Needs verification before implementation:**
- Vercel `experimentalServices` production status (was beta mid-2025)
- Supabase Auth MAU limits and current Pro pricing
- `supabase-py` async support status
- Tailwind v4 + shadcn/ui compatibility

**Standard patterns (skip phase research):**
- Phase 1: Supabase Auth + Next.js via `@supabase/ssr` — well-documented
- Phase 3: Next.js dashboard + TanStack Query — established pattern
- Phase 6: ReactFlow diff rendering — builds on existing models

---
*Research completed: 2026-04-15*
*Ready for roadmap: yes*
