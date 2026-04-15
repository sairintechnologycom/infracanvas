# Stack Research

**Domain:** Developer Tools SaaS — Next.js frontend + FastAPI backend + Supabase
**Researched:** 2026-04-15
**Confidence:** MEDIUM (training data through Aug 2025; WebSearch/WebFetch unavailable for live verification)

---

## Context

This research covers the SaaS layer being added to an existing Python 3.12 CLI. The CLI stack (Typer, Pydantic, python-hcl2, NetworkX) is fixed. This document focuses exclusively on the SaaS additions.

**Constraints driving every recommendation:**
- Solo founder, <$100/mo hosting until revenue
- Next.js frontend on Vercel + FastAPI backend (decided, not up for debate)
- Supabase for Postgres + object storage (decided)
- Auth provider: needs comparison and recommendation
- Stripe for billing (decided)
- CLI must be able to authenticate and push scan results to the SaaS API

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 15.x (App Router) | SaaS frontend, dashboard, marketing pages | App Router is the settled default as of 2024+; server components reduce client JS bundle; Vercel deploys it for free tier |
| FastAPI | 0.111+ | Backend API — scan ingestion, project CRUD, webhook endpoints | Already in Python ecosystem; async-first; auto OpenAPI docs; Pydantic v2 integration is native |
| Pydantic | 2.7.1 | Request/response validation on FastAPI (already in CLI) | Version already used in CLI — share models between CLI and backend |
| Supabase | hosted (supabase.com) | PostgreSQL DB, object storage (scan JSON artifacts), row-level security | One platform covers DB + storage + potential auth; free tier: 500 MB DB + 1 GB storage, 2 projects |
| Stripe | via stripe-python + @stripe/stripe-js | Subscription billing, Pro ($49/mo) + Team ($199/mo) tiers | Industry standard; Customer Portal removes most billing UI work; webhooks for subscription state |
| Supabase Auth | hosted (supabase.com) | Authentication — email/password, magic link, OAuth (GitHub) | See auth comparison below — recommended over Clerk for this project |

### Frontend Libraries (Next.js)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @supabase/ssr | 0.5.x | Supabase client for Next.js App Router (server + client cookies) | Required for App Router — replaces deprecated `@supabase/auth-helpers-nextjs` |
| @supabase/supabase-js | 2.x | Supabase JS client for auth, DB queries, storage | All Supabase interactions from frontend |
| @stripe/stripe-js | 4.x | Stripe.js for payment UI (checkout redirect, customer portal) | Billing pages, upgrade flows |
| Tailwind CSS | 4.x | Styling (already used in viewer; consistency) | All UI; v4 is production-stable as of early 2025 |
| shadcn/ui | latest | Component library built on Radix UI + Tailwind | Dashboard UI components — not installed as a package, copied into repo; avoids bundle lock-in |
| Zustand | 5.0.5 | Client state (already in viewer; reuse knowledge) | Filter state, UI state in diagram viewer embedded in dashboard |
| @xyflow/react | 12.x | Diagram rendering in dashboard (same lib as CLI viewer) | Reuse existing diagram component; embed in Next.js page |
| React Query (TanStack Query) | 5.x | Server state, data fetching, cache invalidation | API calls from dashboard to FastAPI backend |
| next-themes | 0.3.x | Dark/light mode | Dashboard UX for developer tools audience expects dark mode |

### Backend Libraries (FastAPI)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supabase-py | 2.x | Supabase client for Python — DB, storage, auth admin | Backend interaction with Supabase (service role key) |
| python-jose[cryptography] | 3.3.x | JWT verification for API key + Supabase JWT auth | Validate tokens from CLI and frontend requests |
| stripe | 10.x | Stripe Python SDK — webhook handling, subscription checks | Billing endpoints, webhook receiver |
| python-multipart | 0.0.9+ | Form/multipart upload support for FastAPI | Scan artifact uploads from CLI |
| httpx | 0.27+ | Async HTTP client | Any outbound HTTP calls from backend |
| uvicorn[standard] | 0.30+ | ASGI server for FastAPI | Local dev and Vercel serverless deployment |
| slowapi | 0.1.9+ | Rate limiting for FastAPI (Starlette middleware) | Protect API endpoints, especially webhook and scan ingest |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Vercel CLI | Deploy frontend, run `vercel dev` locally | `experimentalServices` config routes Next.js + FastAPI via single local URL |
| vercel.json (services) | Multi-service config: Next.js at `/`, FastAPI at `/api` | Use `experimentalServices`; set Framework Preset to "Services" in Vercel dashboard |
| Ruff | Python linting/formatting (already configured) | Extend existing config to cover FastAPI backend |
| ESLint + Prettier | JS/TS linting and formatting | Use Next.js default ESLint config; add Prettier for consistency |
| Stripe CLI | Local webhook testing | `stripe listen --forward-to localhost:8000/api/webhooks/stripe` |
| Supabase CLI | Local Supabase stack, migrations | `supabase start` runs local Postgres + Auth + Storage; migrations tracked in `supabase/migrations/` |

---

## Auth Provider Comparison: Clerk vs Supabase Auth vs Auth.js

This is the highest-stakes undecided question. All three are viable; the recommendation is **Supabase Auth**.

### Comparison Matrix

| Criterion | Clerk | Supabase Auth | Auth.js (v5) |
|-----------|-------|---------------|--------------|
| **Hosting** | Fully managed (Clerk cloud) | Fully managed (Supabase cloud) | Self-hosted only — you run the DB adapter |
| **Free tier** | 10,000 MAU free (as of 2024) | 50,000 MAU free (Supabase free tier) | Free (you pay infra only) |
| **Pricing at scale** | $0.02/MAU beyond free tier | Included in Supabase Pro ($25/mo) | Infra cost only |
| **Next.js integration** | First-class (`@clerk/nextjs`) | Good (`@supabase/ssr`) | First-class (designed for Next.js) |
| **FastAPI/backend integration** | JWT verification (JWKS endpoint) | JWT verification (Supabase JWT secret) | JWT verification (custom adapter) |
| **API key auth (CLI)** | Not native — must build custom table | Not native — must build custom table | Not native — must build custom table |
| **Database user table** | Clerk manages users; must sync to own DB | Users live in `auth.users` — queryable | Users in your DB directly |
| **Supabase RLS** | Requires JWT template mapping | Native — JWT matches RLS policies directly | Requires custom JWT config for RLS |
| **OAuth providers** | 20+ providers, zero config | 20+ providers | 50+ providers (community adapters) |
| **Magic links** | Yes | Yes | Yes (Email provider) |
| **Org/team management** | First-class (Clerk Organizations) | DIY — build `teams` table + RLS | DIY |
| **UI components** | Pre-built (`<SignIn />`, `<UserButton />`) | None — bring your own UI | None — bring your own UI |
| **Operational overhead** | Near zero | Near zero | Low (just runs on your server) |
| **Vendor lock-in** | High — Clerk-specific APIs throughout | Medium — Supabase ecosystem | Low — open source, portable |

### Why NOT Clerk

- **Cost trajectory:** At 5,000 paying users, Clerk costs ~$900/mo on top of everything else. Supabase Auth is included in the $25/mo Pro plan regardless of user count (up to 100k MAU).
- **User table sync pain:** Clerk stores users in Clerk's DB. To join user data with projects/scans in Postgres, you must either sync via webhooks (fragile) or store duplicate data. Supabase Auth stores users in `auth.users` in your own Postgres instance — no sync needed.
- **Supabase RLS mismatch:** If using Supabase RLS (which you should for multi-tenant data isolation), Clerk JWTs require a custom JWT template configuration that maps Clerk claims to Supabase's expected format. Supabase Auth JWTs work with RLS natively.
- **When Clerk is better:** If team management (Orgs), enterprise SSO, and polished pre-built auth UI are top priorities and MAU count stays under 10k. For this project, team management can be built with a `teams` table, and the user count target doesn't justify Clerk's cost cliff.

### Why NOT Auth.js

- **Self-hosted only:** Auth.js manages sessions in your own database. That's fine, but it adds an adapter layer (you need `@auth/supabase-adapter` or similar) and puts session management responsibility on you.
- **No admin SDK:** No programmatic user management from the backend (e.g., "disable user", "list all users for team"). You'd query your own DB directly, which is workable but requires more code.
- **FastAPI integration is manual:** Auth.js is a Next.js library. For FastAPI to validate Auth.js sessions, you need to share a JWT secret and manually verify. Supabase Auth provides a standard JWKS endpoint making this straightforward.
- **When Auth.js is better:** Greenfield project where you want zero vendor dependency and full control over session storage. Not ideal here because Supabase is already in the stack.

### Recommendation: Supabase Auth

**Use Supabase Auth** because:
1. Users live in your Postgres instance (`auth.users`) — no sync, join directly with `projects` and `scans` tables
2. RLS policies using `auth.uid()` work out of the box for multi-tenant isolation
3. Included free in Supabase free tier (50k MAU); $25/mo Pro covers up to 100k MAU
4. OAuth (GitHub is the primary provider for developer tools audience) works with zero config
5. JWTs are verifiable in FastAPI using the Supabase JWT secret (one env var)
6. Magic link + email/password covered; social login covered
7. Teams/orgs are DIY (build a `teams` table) — acceptable for v1 scope

**Confidence:** MEDIUM. Supabase Auth free tier limits are based on training data through Aug 2025. Verify current limits at supabase.com/pricing before launch.

---

## CLI-to-SaaS Connectivity

The CLI needs to authenticate users and push scan results. This is not covered by the auth provider directly — it's an API key system built on top.

### Recommended Approach: API Keys stored in Supabase

```
CLI login flow:
1. `infracanvas login` opens browser → Supabase Auth OAuth/magic link
2. On success, Supabase returns JWT → CLI stores in ~/.infracanvas/credentials
3. CLI uses JWT as Bearer token for all API calls

CLI push flow:
infracanvas push → POST /api/scans with Authorization: Bearer <jwt>
FastAPI validates JWT against Supabase JWT secret
Associates scan with user from JWT sub claim
```

**Alternative — API Key tokens:**
Generate opaque API keys (stored hashed in `api_keys` table, linked to `user_id`). Better for CI/CD use where interactive OAuth is not possible. Implement both: JWT for interactive CLI, API key for CI.

| Token Type | Use Case | Storage |
|------------|----------|---------|
| Supabase JWT | `infracanvas login` interactive | `~/.infracanvas/credentials` |
| API Key (opaque) | CI/CD, `INFRACANVAS_API_KEY` env var | `api_keys` table, hashed with bcrypt |

Libraries for this:
- `python-jose[cryptography]` on FastAPI for JWT verification
- `secrets.token_urlsafe(32)` for API key generation
- `passlib[bcrypt]` for API key hashing

---

## Deployment Architecture

### Vercel Multi-Service Setup (recommended)

```json
{
  "experimentalServices": {
    "web": {
      "entrypoint": "apps/web",
      "routePrefix": "/"
    },
    "api": {
      "entrypoint": "apps/api/main.py",
      "routePrefix": "/api"
    }
  }
}
```

- Next.js at `/` on Vercel free tier (no cost until 100GB bandwidth/mo)
- FastAPI at `/api` as Vercel serverless function (Python runtime) — free tier: 100GB bandwidth, 100k function invocations/mo
- Single domain, no CORS configuration needed between frontend and backend
- Set Framework Preset to "Services" in Vercel dashboard

**Cost at <$100/mo target:**
| Service | Free Tier | Paid |
|---------|-----------|------|
| Vercel (Next.js + FastAPI) | Free (hobby limits) | $20/mo Pro if needed |
| Supabase (Postgres + Storage + Auth) | Free (500MB DB, 1GB storage, 50k MAU) | $25/mo Pro |
| Stripe | Free (2.9% + 30¢ per transaction) | No fixed cost |
| Total fixed cost | $0 | $45/mo (Vercel Pro + Supabase Pro) |

Well under $100/mo constraint until revenue arrives.

---

## Installation

```bash
# Frontend (Next.js) — apps/web/
npm install @supabase/ssr @supabase/supabase-js
npm install @stripe/stripe-js
npm install @tanstack/react-query
npm install next-themes
npm install zustand
npm install @xyflow/react

# shadcn/ui — not installed via npm, initialized via CLI
npx shadcn@latest init

# Dev dependencies (frontend)
npm install -D tailwindcss @tailwindcss/vite prettier eslint-config-next

# Backend (FastAPI) — apps/api/
pip install fastapi uvicorn[standard]
pip install supabase  # supabase-py
pip install stripe
pip install python-jose[cryptography]
pip install python-multipart
pip install httpx
pip install slowapi
pip install passlib[bcrypt]

# Dev tools
pip install ruff mypy  # already in CLI, extend to backend
npm install -D vercel  # Vercel CLI
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Supabase Auth | Clerk | MAU < 10k forever, team org features are critical, willing to pay $20-100+/mo for polished UI components |
| Supabase Auth | Auth.js v5 | Zero vendor dependency is required; all auth must be open source |
| Vercel services | Separate backend hosting (Railway, Render, Fly.io) | FastAPI has long-running processes (>900s), needs persistent connections (WebSockets), or CPU-bound workloads that don't fit serverless |
| shadcn/ui | Mantine, Chakra UI, MUI | Team prefers a traditional npm component library; shadcn ownership-of-code model is unfamiliar |
| TanStack Query | SWR | SWR is fine; TanStack Query preferred for mutation + optimistic update patterns common in dashboards |
| supabase-py | SQLAlchemy + asyncpg | Need complex ORM queries, migrations beyond Supabase's tooling, or want to self-host DB eventually |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@supabase/auth-helpers-nextjs` | Deprecated as of 2024; replaced by `@supabase/ssr` | `@supabase/ssr` 0.5.x |
| NextAuth.js v4 | Legacy package name; v5 is Auth.js and still unstable for production in some adapters | If you must use Auth.js, use v5 beta explicitly |
| `pages/api` routes for all backend logic | App Router and Server Actions are the modern pattern; also the FastAPI backend exists for Python logic | Use FastAPI for backend logic; Next.js Server Actions only for lightweight form handling |
| Prisma on the FastAPI side | Prisma is a Node.js ORM; using it from Python requires a separate Node process — nonsensical | Use `supabase-py` or raw SQL via `asyncpg` |
| JWT stored in localStorage | XSS vulnerability; standard attack vector | `httpOnly` cookies (Supabase SSR handles this automatically) |
| Stripe Checkout (legacy) | The newer Stripe Checkout (hosted) and Billing Portal are simpler to integrate and PCI-compliant | Use Stripe's hosted Checkout + Customer Portal; avoids building payment forms entirely |
| Docker for Vercel deployment | Vercel builds Python serverless functions natively; Docker adds unnecessary complexity | Use `requirements.txt` or `pyproject.toml` in the service directory; Vercel detects FastAPI automatically |

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Next.js 15 | React 19 | Next.js 15 works with both React 18 and 19; React 19 is stable but has breaking changes from 18 — test carefully if mixing with existing React 18 components from the viewer |
| @supabase/ssr 0.5.x | Next.js 14+ App Router | Does NOT work with Pages Router; if any pages/ routes exist, use `createPagesServerClient` from deprecated package or migrate to App Router |
| Tailwind CSS 4.x | PostCSS 8+ | v4 changes config format significantly (CSS-first config, no `tailwind.config.js`); incompatible with shadcn/ui versions that assume v3 config — check shadcn release notes |
| Pydantic 2.7.1 | FastAPI 0.111+ | FastAPI 0.111+ requires Pydantic v2; already on 2.7.1 in CLI — consistent |
| supabase-py 2.x | Python 3.10+ | Python 3.12 in use — compatible |
| stripe 10.x | Python 3.8+ | Compatible |

---

## Stack Patterns by Variant

**If FastAPI cold start latency is a problem on Vercel:**
- Use `uvicorn` with the `--workers 1` flag; Vercel Python serverless has ~200-500ms cold starts
- Cache frequently-read data (user subscription status) in Supabase itself to avoid DB round-trips on every request
- Consider moving to Vercel Pro ($20/mo) for fluid compute if cold starts affect UX

**If Supabase free tier storage is exhausted:**
- Compress scan JSON before storing (scan graphs can be large for big Terraform projects)
- Add a `retention_days` column and a cron job to prune old scan artifacts
- Free tier is 1GB storage; a typical scan JSON for a 50-resource Terraform project is ~50-200KB, so free tier covers ~5,000-20,000 scans before upgrade needed

**If team billing becomes complex:**
- Add a `teams` table with `owner_user_id`, `plan`, `stripe_customer_id`
- Add `team_members` junction table with `role` (owner/member)
- RLS policies scope all data to `team_id` for team tier users
- Stripe Billing for teams: one Stripe Customer per team, not per user

---

## Sources

All findings based on training data (knowledge cutoff August 2025). WebSearch and WebFetch were unavailable during this research session.

- Supabase Auth documentation — MEDIUM confidence; verify current MAU limits at supabase.com/pricing
- Clerk pricing — MEDIUM confidence; the free tier MAU limit (10,000) was accurate as of mid-2025 but Clerk has historically adjusted pricing. Verify at clerk.com/pricing before making auth decision.
- Vercel `experimentalServices` — MEDIUM confidence; this feature was in beta as of mid-2025. See Vercel docs and skill context provided in this session for current status.
- FastAPI 0.111, Pydantic v2 compatibility — HIGH confidence; stable API, well-documented
- Stripe integration patterns — HIGH confidence; Stripe's API and SDK are stable
- `@supabase/auth-helpers-nextjs` deprecation — HIGH confidence; confirmed in Supabase migration guide (mid-2024); `@supabase/ssr` is the current package

---

*Stack research for: InfraCanvas SaaS layer — developer tools SaaS, Next.js + FastAPI + Supabase*
*Researched: 2026-04-15*
