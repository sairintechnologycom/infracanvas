# Technology Stack

**Project:** InfraCanvas v2.0 — Hybrid Cloud Intelligence Platform
**Researched:** 2026-04-15
**Confidence:** HIGH (all critical choices verified against official docs, PyPI, npm April 2026)

---

## Validation Summary

The stack proposed in PROJECT.md is sound with three corrections:

1. **arq is in maintenance-only mode** — replace with taskiq before writing any queue code
2. **Next.js 14 should be Next.js 15** — 15 is stable, Vercel-recommended, caching defaults are better for SaaS
3. **Stripe legacy usage records API removed** — must use Billing Meters API (breaking change in Stripe 2025-03-31.basil)

Additionally, the original stack has no observability layer — add Sentry + Logfire before Phase 4.

---

## Recommended Stack

### CLI (Existing — Validated)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12 | CLI runtime | FastAPI 0.130+ dropped Python 3.9; 3.12 is the safe floor and current production LTS |
| Typer | 0.12+ | CLI framework | Type-hint-driven, Click-based; already in use and working |
| Pydantic v2 | 2.x | Data validation + schema | v2 is 5-17x faster than v1 via Rust core; already in use; share models with backend |
| python-hcl2 | 4.x | HCL/Terraform parser | Only maintained HCL2 parser for Python; no alternative |
| NetworkX | 3.x | Graph algorithms | Topology traversal, path computation; mature and well-tested |
| PyInstaller | 6.x | Standalone binary packaging | Cross-platform `--onefile` build; required for CLI distribution alongside pip install |

**Confidence: HIGH** — All verified on PyPI April 2026. No changes needed to existing CLI stack.

---

### DC Collector Agent (Go — New)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Go | 1.22+ | Agent runtime | Single-binary cross-compilation for Linux amd64 + macOS arm64; zero runtime deps; correct choice for a daemon running on-prem |
| nemith/netconf | latest | NETCONF protocol client | Most complete, actively maintained Go NETCONF library. Use this over `Juniper/go-netconf` (less active) and `netascode/go-netconf` (adds scrapligo dependency unnecessarily) |
| scrapli/scrapligo | latest | SSH CLI fallback | Robust SSH + NETCONF transport for devices without proper NETCONF support (older Cisco IOS) |
| netsampler/goflow2 | v2 | NetFlow / IPFIX / sFlow collection | **CRITICAL: use goflow2, NOT cloudflare/goflow.** The original Cloudflare goflow was archived February 19, 2025. goflow2 is the active community fork with ongoing maintenance |
| cobra | 1.8+ | Agent CLI flags | Standard Go CLI; consistent with Go ecosystem conventions |
| encoding/xml | stdlib | NETCONF XML parsing | Standard library is sufficient; no third-party XML dep needed |

**Confidence: HIGH** — goflow archive date verified on GitHub. nemith/netconf confirmed active with recent commits. goflow2 confirmed on pkg.go.dev.

**Gap — Agent-to-SaaS transport:** The PROJECT.md does not specify how the DC agent ships data to the SaaS backend. Recommendation: HTTP POST with JSON payload to a FastAPI `/v1/ingest/flows` endpoint secured with mTLS or a pre-shared API key. Avoid gRPC for v1 (complexity not justified); upgrade in Phase 5 if throughput demands it.

---

### SaaS Backend (FastAPI — New)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.128+ | API framework | Latest stable as of February 2026 (0.128.0 on PyPI); Python 3.12 required from 0.130+; async-first; native Pydantic v2 integration; auto OpenAPI docs |
| Uvicorn + Gunicorn | 0.30+ | ASGI server | Uvicorn as worker; Gunicorn as process manager in production Docker container |
| SQLAlchemy | 2.0+ | ORM + async DB access | 2.0 async engine is production-standard; use `NullPool` when connecting through Neon's built-in pgBouncer to avoid double-pooling |
| asyncpg | 0.29+ | Async PostgreSQL driver | Fastest async Postgres driver; required by SQLAlchemy async engine |
| Alembic | 1.13+ | Database migrations | Standard SQLAlchemy migration tool; track migration files in version control |
| Pydantic v2 | 2.x | Request/response models | Same version as CLI — share schemas between CLI and backend via a shared `infracanvas-core` package |
| clerk-backend-api | latest | JWT verification + user management | Official Clerk Python SDK; use `AuthenticateRequest` to verify JWTs in FastAPI middleware; handles JWKS caching and rotation automatically |
| boto3 | 1.34+ | Cloudflare R2 / S3 object storage | R2 is S3-compatible; configure with `endpoint_url=https://<account>.r2.cloudflarestorage.com`; use presigned URLs for scan artifact upload/download; **set `signature_version='s3v4'` explicitly** |
| stripe | 10.x | Billing | Official Stripe Python SDK; **BREAKING: use Billing Meters API from day one**; legacy `create_usage_record()` removed in Stripe API version 2025-03-31.basil |
| taskiq | 0.11+ | Async background job queue | **Replaces arq** — arq is maintenance-only (confirmed on GitHub issue #437); taskiq is actively developed, async-native, has first-class FastAPI integration via `taskiq-fastapi` |
| taskiq-redis | latest | Redis broker for taskiq | `RedisStreamBroker` connects to Upstash Redis; `RedisAsyncResultBackend` for job result storage |
| taskiq-fastapi | latest | FastAPI dependency injection in tasks | Enables reuse of FastAPI dependencies (DB sessions, config) inside taskiq task functions |
| httpx | 0.27+ | Async HTTP client | Outbound calls: Slack/Teams webhooks, AWS/Azure APIs, Clerk webhook delivery |
| slowapi | 0.1.9+ | Rate limiting | Starlette-based middleware; protect scan ingest, webhook, and billing endpoints |
| passlib[bcrypt] | 1.7+ | API key hashing | Hash CLI API keys before storing in DB; `secrets.token_urlsafe(32)` for key generation |

**Confidence: HIGH** — FastAPI 0.128 on PyPI confirmed. arq maintenance-only confirmed GitHub issue #437. taskiq production-stable on PyPI. Stripe breaking change in official docs.

**Connection pooling pattern for Neon:** Use Neon's pgBouncer connection string (port 6432, not 5432), set SQLAlchemy to `NullPool`, and add `prepared_statement_cache_size=0` to connection args. This prevents two pooling mechanisms competing and resolves the intermittent prepared-statement errors common with pgBouncer in transaction mode.

---

### SaaS Frontend (Next.js — New)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | **15** (upgrade from 14) | React framework + SaaS dashboard | 15 is stable and production-ready; Vercel's own products run on 15; uncached-by-default behavior is correct for a data-heavy SaaS where stale scan data is a bug |
| React | **19** | UI runtime | Required by Next.js 15; React 19 includes Actions, improved Suspense, and `use()` hook; backwards compatible for Pages Router with React 18 |
| shadcn/ui | latest | Component library | Updated for Tailwind v4 + React 19 (confirmed October 2025); installed via shadcn CLI (copy-paste into repo, not a package dependency); zero bundle lock-in |
| Tailwind CSS | **v4** | Styling | shadcn/ui has moved to Tailwind v4; CSS-first config (no `tailwind.config.js`); start on v4 to avoid migration debt later |
| @xyflow/react | 12.x | Infrastructure diagrams | Updated to React 19 + Tailwind v4 in October 2025; React Flow UI now ships pre-built diagram components styled with shadcn; use `@xyflow/react` (new package name, not `reactflow`) |
| @dagrejs/dagre | 1.x | Graph auto-layout | Fast directed graph layout; sufficient for 500-node infra graphs; **upgrade to elkjs for FlowMap Phase 3** where hybrid topology graphs may exceed 1000 nodes and require async layout |
| TanStack Query | v5 | Server state + data fetching | v5 is current; use `HydrationBoundary` + `dehydrate` pattern for App Router Server Component prefetching; eliminates request waterfalls |
| Zustand | 4.x | Client-side state | Already in viewer; keep for diagram interaction state (selection, filters, layout mode); do not use for server state |
| @clerk/nextjs | 6.x | Auth frontend | Native App Router + middleware support; `ClerkProvider` wraps app; SSO/SAML for Enterprise tier; 3 enterprise SSO connections on Free plan |
| @stripe/stripe-js + @stripe/react-stripe-js | latest | Payment frontend | Use Stripe hosted Checkout + Customer Portal; avoids building PCI-compliant payment forms; `stripe.redirectToCheckout()` for upgrades |
| next-themes | latest | Dark mode | Standard pattern for Next.js + shadcn dark mode |
| Zod | 3.x | Schema validation | Pairs with shadcn form components and react-hook-form; share schemas with FastAPI Pydantic models where possible |
| react-hook-form | 7.x | Form state management | Default shadcn form library; pairs with Zod via `@hookform/resolvers` |
| @sentry/nextjs | latest | Error tracking | Add on day 1 of Phase 4; captures unhandled errors with full context |

**Confidence: HIGH** — Next.js 15 stable confirmed on nextjs.org. shadcn Tailwind v4 support confirmed on ui.shadcn.com. @xyflow/react React 19 update confirmed on reactflow.dev.

**Why upgrade to Next.js 15 now:** Next.js 14 is still supported but 15 is where Vercel ships updates. The caching behavior change (opt-in caching vs opt-out) means scan data will not be incorrectly served stale by default — this is the right default for InfraCanvas. Migration from 14 to 15 takes 4-8 hours for a medium app using the provided codemod. Do it before the SaaS frontend has substantial code.

---

### Database

| Technology | Purpose | Why |
|------------|---------|-----|
| Neon PostgreSQL (Scale plan) | Primary datastore | Serverless scales to zero (critical for $10-104/mo bootstrap budget); built-in pgBouncer handles up to 10,000 connections; **pricing improved significantly after Databricks acquisition in May 2025**: storage dropped from $1.75 → $0.35/GB-month; 99.95% SLA on Scale plan; native Row-Level Security for multi-tenant isolation |
| PostgreSQL Row-Level Security | Multi-tenant data isolation | Enforce per-organization isolation at the DB layer, not the app layer; use `auth.uid()` from Clerk JWT claims in RLS policies |

**Confidence: HIGH** — Neon pricing confirmed on neon.com/pricing April 2026.

---

### Auth

| Technology | Purpose | Why |
|------------|---------|-----|
| Clerk (Pro plan) | Managed auth for all tiers | $25/mo for 50K MAU; MFA + passkeys included; 1 enterprise SSO connection included in Pro; SAML/OIDC for Azure AD, Google Workspace, Okta in Enterprise tier; official Python SDK for FastAPI JWT verification; official Next.js SDK with App Router middleware; 30-minute integration time |

**CLI auth flow:** `infracanvas login` opens browser → Clerk hosted login → JWT returned → stored in `~/.infracanvas/credentials`. For CI/CD, generate opaque API keys stored hashed (`passlib[bcrypt]`) in an `api_keys` table linked to `user_id`.

**Confidence: HIGH** — Clerk pricing and SSO features verified on clerk.com April 2026.

---

### Object Storage

| Technology | Purpose | Why |
|------------|---------|-----|
| Cloudflare R2 | Scan artifacts, HTML exports, FlowMap topology snapshots | Zero egress fees — critical when exports are 1-5MB each and CLI users download them frequently; S3-compatible API means boto3 works unchanged with `endpoint_url` override; presigned URLs for direct browser upload/download without proxying through FastAPI |

**boto3 gotcha:** Set `config=Config(signature_version='s3v4')` explicitly in the boto3 client constructor. Default signature version causes `SignatureDoesNotMatch` errors with R2 presigned URLs.

**Confidence: HIGH** — Official R2 boto3 docs at developers.cloudflare.com confirmed.

---

### Cache and Queue

| Technology | Purpose | Why |
|------------|---------|-----|
| Upstash Redis (Serverless plan) | Session cache, rate limiting, job queue broker | Pay-per-request; scales to zero; HTTP-based client (no persistent TCP connection) works from serverless/edge environments; free tier is generous for bootstrap |
| taskiq + taskiq-redis | Async background job processing | Scan processing, webhook delivery, Slack/Teams alerts, billing meter events; `RedisStreamBroker` with Upstash Redis as backend; **replaces arq which is maintenance-only** |

**Confidence: HIGH** — Upstash confirmed operational. taskiq-redis confirmed compatible with Upstash Redis HTTP endpoint.

---

### Payments

| Technology | Purpose | Why |
|------------|---------|-----|
| Stripe (Python SDK 10.x + Stripe.js) | Subscription billing + usage metering | Industry standard; Customer Portal removes billing UI work; **BREAKING CHANGE**: legacy usage records API removed in Stripe API version 2025-03-31.basil; use Billing Meters from day one for scan count and DC agent seats |

**Billing meter setup:** Create two meters — `scan_count` (sum aggregation) and `dc_agent_seats` (last aggregation). Link to subscription items. This enables Pro/Team/Enterprise tier gates and future usage overages without schema changes.

**Confidence: HIGH** — Stripe breaking change confirmed in official Stripe docs.

---

### Infrastructure and Deployment

| Technology | Purpose | Why |
|------------|---------|-----|
| Vercel | Next.js frontend hosting | Native Next.js 15 support; edge CDN; Hobby free → Pro $20/mo |
| Railway (Hobby plan) | FastAPI backend hosting | $5/mo included usage; no cold starts (unlike serverless); GitHub auto-deploy; simpler than Fly.io for solo founder — Fly.io is the fallback if multi-region is needed in Phase 5 |
| Docker (multi-stage build) | FastAPI containerization | Railway deploys from Dockerfile; multi-stage build (build stage → slim python:3.12-slim runtime) keeps image under 200MB |
| GitHub Actions | CI/CD | Free for public repos; CLI tests → PyInstaller binary → Docker build → push to Railway |

**Confidence: HIGH** — Railway pricing confirmed on railway.com April 2026.

---

### Observability (Gap — Not in Original Stack)

The PROJECT.md has no observability layer. Silent failures in scan processing or Stripe webhooks are the most dangerous class of bug for a SaaS. Add before Phase 4 ships.

| Technology | Purpose | Why |
|------------|---------|-----|
| Sentry (Python + Next.js SDKs) | Error tracking | Free tier (5K errors/mo); one-line FastAPI + Next.js integration; captures unhandled exceptions with full request context |
| Logfire (Pydantic team) | Structured logging + OpenTelemetry tracing | Built by the Pydantic team; native FastAPI + Pydantic v2 integration; OpenTelemetry-based; generous free tier |

**Confidence: MEDIUM** — Sentry is established. Logfire launched 2024; verify current free tier limits at logfire.pydantic.dev before committing.

---

## Alternatives Rejected

| Category | Recommended | Rejected | Reason for Rejection |
|----------|-------------|----------|----------------------|
| Task queue | taskiq | arq | arq is maintenance-only (confirmed GitHub issue #437, 2025) |
| Task queue | taskiq | Celery | Celery is sync-first; requires threading bridge with asyncio; heavier operational overhead |
| Frontend | Next.js 15 | Next.js 14 | 14 not EOL but stale caching defaults cause subtle SaaS bugs; migrate before codebase is large |
| DB | Neon PostgreSQL | Supabase | Supabase bundles auth + storage that are replaced by Clerk + R2; Neon is pure Postgres with better serverless scaling |
| DB | Neon PostgreSQL | PlanetScale | Removed free tier 2024; MySQL not Postgres |
| Auth | Clerk | Supabase Auth | Supabase Auth lacks SAML/SSO for Enterprise tier; Clerk has it on Pro plan |
| Auth | Clerk | Auth0 | Auth0 is 40-60% more expensive than Clerk at under 50K MAU |
| Graph layout | dagre (Phase 1-2) | ELK.js | ELK is more powerful but async-only, far more complex to configure; overkill for Canvas; plan ELK adoption for FlowMap Phase 3 (large hybrid topology graphs) |
| NetFlow (Go) | goflow2 | cloudflare/goflow | Original goflow archived February 2025; goflow2 is active fork |
| NETCONF (Go) | nemith/netconf | Juniper/go-netconf | nemith is more actively maintained, cleaner API, no extra deps |
| Backend hosting | Railway | Render | Render has slower cold starts; free tier limitations stricter |
| Styling | Tailwind v4 | Tailwind v3 | shadcn/ui has moved to v4; starting on v3 creates migration debt |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `reactflow` (old package name) | Renamed to `@xyflow/react`; old package may lag on updates | `@xyflow/react` |
| arq | Maintenance-only as of 2025 | taskiq |
| Stripe `create_usage_record()` | Removed in Stripe API 2025-03-31.basil | Billing Meters API |
| cloudflare/goflow | Archived February 2025 | netsampler/goflow2 |
| Juniper/go-netconf | Less maintained, older API | nemith/netconf |
| SQLAlchemy `QueuePool` with Neon | Conflicts with Neon's pgBouncer; causes connection errors | `NullPool` + Neon pgBouncer connection string |
| JWT stored in localStorage | XSS vulnerability | httpOnly cookies (Clerk SDK handles automatically) |
| Docker for Vercel Next.js deployment | Vercel builds Next.js natively; Docker adds complexity | Standard Vercel deployment |
| Prisma on the FastAPI/Python side | Prisma is a Node.js ORM; using from Python requires a separate Node process | SQLAlchemy 2.0 async |

---

## Installation Reference

### Backend (Python)
```bash
# Core framework
pip install "fastapi>=0.128" "uvicorn[standard]>=0.30" gunicorn

# Database
pip install "sqlalchemy[asyncio]>=2.0" asyncpg alembic

# Auth, storage, billing
pip install clerk-backend-api boto3 stripe

# Queue
pip install taskiq taskiq-redis taskiq-fastapi

# Utilities
pip install "pydantic[email]>=2.0" httpx slowapi passlib[bcrypt] python-multipart

# CLI (existing + shared)
pip install "pydantic[email]>=2.0" typer[all] python-hcl2 networkx pyinstaller

# Dev
pip install pytest pytest-asyncio coverage ruff mypy sentry-sdk logfire
```

### Frontend (Node)
```bash
npx create-next-app@latest --typescript --tailwind --app
npx shadcn@latest init

npm install @xyflow/react @dagrejs/dagre zustand
npm install @tanstack/react-query @clerk/nextjs
npm install @stripe/stripe-js @stripe/react-stripe-js
npm install next-themes zod react-hook-form @hookform/resolvers
npm install -D @sentry/nextjs
```

### DC Agent (Go)
```bash
go get github.com/nemith/netconf
go get github.com/scrapli/scrapligo
go get github.com/netsampler/goflow2/v2
go get github.com/spf13/cobra
```

---

## Pre-Phase-4 Stack Checklist

- [ ] Replace all arq references with taskiq in planning docs and code
- [ ] Target Next.js 15 + React 19 from project init (run Next.js 15 codemod if upgrading existing code)
- [ ] Initialize Stripe with Billing Meters, not legacy usage records
- [ ] Use Neon pgBouncer connection string (port 6432) with SQLAlchemy NullPool
- [ ] Add `prepared_statement_cache_size=0` to asyncpg connection args
- [ ] Set `signature_version='s3v4'` in boto3 R2 client config
- [ ] Use `@xyflow/react` not `reactflow`
- [ ] Use `netsampler/goflow2/v2` not `cloudflare/goflow`
- [ ] Use `nemith/netconf` not `Juniper/go-netconf`
- [ ] Add Sentry to FastAPI and Next.js on Phase 4 day 1

---

## Sources

- FastAPI 0.128 release: https://pypi.org/project/fastapi/
- arq maintenance-only: https://github.com/python-arq/arq/issues/437
- taskiq production stable: https://pypi.org/project/taskiq/
- Next.js 15 stable: https://nextjs.org/blog/next-15
- shadcn Tailwind v4 support: https://ui.shadcn.com/docs/tailwind-v4
- @xyflow/react React 19 update: https://reactflow.dev/whats-new/2025-10-28
- Neon pricing (post-Databricks): https://neon.com/pricing
- Neon pgBouncer + SQLAlchemy NullPool pattern: https://neon.com/guides/fastapi-async
- Clerk pricing + SSO: https://clerk.com/docs
- Clerk Python SDK: https://github.com/clerk/clerk-sdk-python
- goflow archived February 2025: https://github.com/cloudflare/goflow
- goflow2 active fork: https://github.com/netsampler/goflow2
- Stripe Billing Meters (breaking change): https://docs.stripe.com/billing/subscriptions/usage-based
- R2 boto3 docs: https://developers.cloudflare.com/r2/examples/aws/boto3/
- Railway vs Fly.io: https://docs.railway.com/platform/compare-to-fly
- TanStack Query v5 App Router SSR: https://tanstack.com/query/v5/docs/framework/react/guides/advanced-ssr

---

*Researched: 2026-04-15 | Replaces prior Supabase-based STACK.md which reflected a different architecture*
