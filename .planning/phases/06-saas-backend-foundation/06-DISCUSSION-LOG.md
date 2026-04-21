# Phase 6: SaaS Backend Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 06-saas-backend-foundation
**Areas discussed:** Team identity + RLS, Scan ingest pipeline, Queue + hosting topology, Observability stack

---

## Team identity + RLS

| Option | Description | Selected |
|--------|-------------|----------|
| Clerk Organizations | Use Clerk orgs + memberships + roles; local teams table mirrors clerk_org_id | ✓ |
| Custom teams table + Clerk users only | Rebuild invites, role mgmt, org switching UI ourselves | |
| Hybrid: Clerk Orgs + local roles override | Extra complexity; only if Clerk roles prove too coarse | |

| Option | Description | Selected |
|--------|-------------|----------|
| SET LOCAL app.current_team_id per request | policies use current_setting('app.current_team_id', true)::uuid = team_id | ✓ |
| Neon JWT RLS (auth.user_id() native) | policies read auth.jwt() ->> 'org_id' directly | |
| App-side filter + RLS as belt-and-braces | Every query adds WHERE team_id AND RLS enforces it | |

| Option | Description | Selected |
|--------|-------------|----------|
| Integration test: cross-team cross-read returns 0 rows | as infracanvas_app with team B context, SELECT team A row = 0 | ✓ |
| Policy inventory + coverage lint | iterate tables, assert RLS enabled | |
| Both: inventory lint + cross-read integration | Most thorough | |

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI dependency reads role from JWT claim | require_role('admin') pulls from Clerk JWT org membership | ✓ |
| RLS policies encode role too | adds role dimension to every policy | |
| Mix: RLS for reads, app for writes | effectively same as option 1 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Clerk webhook → upsert team on organization.created | Svix signature-verified endpoint | ✓ |
| Lazy on first authed request | upsert when JWT org_id unknown | |
| Both: webhook primary + lazy fallback | slightly more code, slightly more robust | |

---

## Scan ingest pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Two-step: presigned PUT + commit | Client POSTs metadata, PUTs directly to R2, POSTs commit with sha256 | ✓ |
| Single-step: multipart POST through API | Every byte transits Fly ingress | |
| Two-step but base64 in JSON | Payload inflation | |

| Option | Description | Selected |
|--------|-------------|----------|
| teams/{team_id}/scans/{scan_id}.json | UUIDv7 scan_id; prefix matches RLS boundary | ✓ |
| Content-addressed sha256 | dedupes but breaks RLS blast-radius bounding | |
| teams/{team_id}/{YYYY}/{MM}/{scan_id}.json | UUIDv7 already sorts chronologically | |

| Option | Description | Selected |
|--------|-------------|----------|
| 1 event per successful commit, unit=scans | infracanvas.scan, value=1, idempotency_key=scan_id | ✓ |
| Per-resource meter (value=resource_count) | Premature for Phase 6 | |
| Per-MB size meter | Wrong abstraction | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sync: validate + meter; Async: fan-out (enqueue_scan_indexing) | Real worker job with production value | ✓ |
| Everything sync in Phase 6 | Worker scaffolding unexercised | |
| Everything async including meter | Billing consistency risk | |

| Option | Description | Selected |
|--------|-------------|----------|
| GET /scans/{id} → signed GET URL + metadata | ~300s TTL presigned URL + scans row | ✓ |
| GET /scans/{id} → inline JSON through API | Every byte transits backend | |
| GET /scans/{id}/download and /scans/{id} separate | Extra round-trip | |

| Option | Description | Selected |
|--------|-------------|----------|
| 25 MB hard limit + Content-Length check on presign | 7x headroom over 3.5MB bundle baseline | ✓ |
| 5 MB hard limit | Tight | |
| No hard limit yet | Risky | |

---

## Queue + hosting topology

| Option | Description | Selected |
|--------|-------------|----------|
| Fly.io | Process-group model; region-colocate Neon; $5-15/mo idle | ✓ |
| Railway | Simpler UX, fewer regions, cold starts on hobby tier | |
| Both with env split | Doubles ops surface | |

| Option | Description | Selected |
|--------|-------------|----------|
| Upstash Redis (taskiq-redis) | Serverless, generous free tier | ✓ |
| Postgres broker via taskiq-postgres | Lower throughput ceiling, row-lock contention | |
| In-process worker, no broker | Fails success criterion #5 in spirit | |

| Option | Description | Selected |
|--------|-------------|----------|
| Two envs: dev + prod separate Neon + R2 + Stripe test vs live | Clean blast-radius separation | ✓ |
| Single prod env + Neon branch for previews | Defer GHA wiring to Phase 7 | |
| One env only | Would bill dev testing to live meter | |

| Option | Description | Selected |
|--------|-------------|----------|
| Alembic | Standard Python + SQLAlchemy | ✓ |
| Atlas (declarative HCL) | Overkill for Phase 6 scale | |
| Raw SQL + Python runner | Forever-manual | |

| Option | Description | Selected |
|--------|-------------|----------|
| New top-level backend/ | Separate pyproject.toml from cli/ and viewer/ | ✓ |
| Under cli/ as submodule | Bloats CLI install footprint | |
| Separate repo | Rejects monorepo bet | |

| Option | Description | Selected |
|--------|-------------|----------|
| asyncpg + SQLAlchemy 2.0 async | Fastest Python Postgres driver + mature async ORM | ✓ |
| asyncpg + plain SQL | Solo-founder velocity hit | |
| Psycopg3 async + SQLAlchemy | asyncpg has perf + ecosystem edge | |

---

## Observability stack

| Option | Description | Selected |
|--------|-------------|----------|
| Sentry | Industry default; sentry-sdk[fastapi] auto-instrument | ✓ |
| Logfire (Pydantic) | Tight OTLP; less mature ecosystem | |
| Better Stack (Telemetry) | Log+error+uptime combined | |

| Option | Description | Selected |
|--------|-------------|----------|
| structlog → JSON stdout → Fly drain → Axiom | Generous free tier, swappable sink | ✓ |
| Logfire (same vendor as error tracking) | Single pane only if Logfire picked for errors | |
| structlog → stdout only (Fly native logs) | ~7d retention, no search | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sentry Performance traces @ 10% sample | Piggybacks on existing Sentry SDK | ✓ |
| Full OTEL → Grafana Cloud / Honeycomb | Overkill for pre-revenue | |
| Skip tracing in Phase 6 | Risk when perf issue lands | |

| Option | Description | Selected |
|--------|-------------|----------|
| Middleware generates X-Request-ID (UUIDv7) + contextvar | Task metadata carries it into worker logs | ✓ |
| Starlette built-in + Sentry-generated span IDs | Couples log correlation to Sentry | |

---

## Claude's Discretion

- API versioning prefix shape (`/v1` vs `/api/v1` vs header-based)
- Clerk SDK vs raw PyJWT + JWKS for JWT validation
- taskiq retry policy + result expiry TTL
- SQLAlchemy autogenerate vs handwritten-only per-migration
- Middleware ordering (X-Request-ID before or after Clerk auth — likely before)
- UUIDv7 library choice
- Fly Machine sizes
- Axiom dataset naming + Sentry project split conventions

## Deferred Ideas

- Neon-branch-per-PR preview envs — Phase 7
- Stripe subscription lifecycle — Phase 13
- OTLP → Grafana/Honeycomb — revisit post-Sentry
- Logfire single pane — revisit later
- API rate limiting — Phase 8
- GitHub OAuth + repo picker — Phase 7.5
- Share-link token system — Phase 7
- Scan compare diff endpoint — Phase 7
- Slack alert webhook — Phase 8
- Content-addressed R2 dedup — rejected for blast-radius bounding
- Per-resource / per-MB Stripe meter — rejected for Phase 6
- Lazy-upsert team row — rejected; webhook reliable enough
- Role dimension in RLS — rejected; stays in FastAPI dep
- Multipart-through-API upload — rejected for bandwidth cost
- In-process taskiq worker — rejected in spirit of success criterion #5
- Railway — rejected in favor of Fly
- Atlas migrations — rejected for Alembic
- Psycopg3 — rejected for asyncpg
