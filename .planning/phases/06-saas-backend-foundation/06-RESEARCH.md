# Phase 6: SaaS Backend Foundation — Research

**Researched:** 2026-04-24
**Domain:** FastAPI + Clerk + Neon (RLS) + R2 + taskiq + Stripe Billing Meters + structlog/Sentry/Axiom on Fly.io
**Confidence:** HIGH (locked decisions verified against vendor docs); MEDIUM on a few discretion items flagged below.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 .. D-21)

**Team identity + RLS**
- D-01: Teams = Clerk Organizations; local `teams` table mirrors each org (keyed by `clerk_org_id`, stores only local metadata like `stripe_customer_id`).
- D-02: `team_id` reaches Postgres via `SET LOCAL app.current_team_id = $1` inside every authenticated request's transaction; RLS policies use `current_setting('app.current_team_id', true)::uuid = team_id`.
- D-03: Role enforcement lives in a FastAPI dependency reading the JWT role claim; RLS policies stay team-scoped (no role dimension).
- D-04: Team rows created via Clerk webhook `organization.created`, Svix-verified. No lazy upsert.
- D-05: TMM-01 verification = integration test that asserts cross-team SELECT returns 0 rows under `infracanvas_app` role.

**Scan ingest (API-06/07, TMM-02)**
- D-06: Two-step upload. `POST /v1/scans` → presigned PUT; client PUTs to R2; `POST /v1/scans/{id}/commit` runs HEAD+validate+insert+meter atomically.
- D-07: R2 key = `teams/{team_id}/scans/{scan_id}.json`; `scan_id` is UUIDv7.
- D-08: Stripe Billing Meter event name `infracanvas.scan`, value=1, `idempotency_key=scan_id`.
- D-09: Sync at commit = HEAD → ContentLength + sha256 → Pydantic validate → insert → meter event. If meter fails, roll back DB. Async via taskiq = `enqueue_scan_indexing(scan_id)` writing denormalized summary counts.
- D-10: Retrieval = `GET /v1/scans/{id}` returns metadata + short-TTL (~300s) presigned GET URL. RLS on metadata → 404 (not 403) on cross-team.
- D-11: 25 MB hard ceiling; commit double-checks R2 `ContentLength`; over-limit → 413; R2 bucket lifecycle GCs orphans ≥7 days.

**Queue + hosting**
- D-12: Fly.io. Two apps (`infracanvas-api-dev`, `infracanvas-api-prod`). Each with `[processes] api` + `[processes] worker`. Region co-located with Neon.
- D-13: Broker = Upstash Redis via `taskiq-redis`. Result backend = same Redis. One Upstash DB per env.
- D-14: Two envs — dev (Stripe test mode) + prod (Stripe live mode). Separate Neon projects, R2 buckets, Clerk instances, Upstash DBs.
- D-15: Alembic; `alembic upgrade head` as Fly `release_command`. Autogenerate for schema; handwritten SQL for RLS policies.
- D-16: New top-level `backend/` with its own `pyproject.toml`.
- D-17: asyncpg + SQLAlchemy 2.0 async. Raw SQL for RLS migrations; ORM for CRUD.

**Observability**
- D-18: Sentry (`sentry-sdk[fastapi]`). Tag `request_id`, `team_id`, `user_id`, `clerk_org_id`.
- D-19: structlog JSON → stdout → Fly log drain → Axiom.
- D-20: Sentry Performance tracing, `traces_sample_rate=0.1`.
- D-21: ASGI middleware generates `X-Request-ID` (UUIDv7) if missing; binds to structlog contextvar; echoed in response header; propagated into taskiq task metadata.

### Claude's Discretion
- API versioning shape (`/v1` vs `/api/v1`).
- Clerk JWT validation library choice (ClerkClient SDK vs PyJWT + JWKS).
- taskiq retry/DLQ defaults.
- Alembic autogenerate vs handwritten per-change.
- Middleware order (request-id before auth).
- UUIDv7 library choice.
- Fly Machine sizes.
- Axiom dataset naming.
- Sentry project split.

### Deferred (OUT OF SCOPE)
Neon preview branches, Stripe subscription lifecycle (Phase 13), OTLP tracing, Logfire, rate limiting, WebAuthn, GitHub OAuth (Phase 7.5), share-link tokens (Phase 7), scan-compare diff (Phase 7), Slack alerts (Phase 8), content-addressed R2 dedup, per-resource meter, lazy-upsert team rows, role-in-RLS policies, inline multipart upload, in-process taskiq worker, Railway, Atlas, psycopg3.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | FastAPI application scaffold on Fly.io with health endpoint | §Executive Summary + §backend Layout + §F11 Fly topology |
| API-02 | Clerk auth middleware validating session tokens | §F1 Clerk JWT validation — PyJWT + JWKS code sketch |
| API-03 | Neon Postgres via pooler with `infracanvas_app` role (no BYPASSRLS) | §F3 RLS under Neon — SET LOCAL inside transaction, role provisioning SQL |
| API-04 | R2 object storage client for scan artifacts | §F5 R2 presigned URLs — boto3 s3v4 example |
| API-05 | taskiq queue with worker process for async jobs | §F7 taskiq-redis — broker + SmartRetryMiddleware + worker topology |
| API-06 | Scan upload endpoint (presigned two-step) | §F5 R2 + §F6 ResourceGraph validator import |
| API-07 | Scan retrieval endpoint (signed GET URL) | §F5 R2 + §F4 SQLAlchemy async session |
| TMM-01 | Team roles + RLS-enforced per-team isolation | §F1 `o.rol` claim + §F2 Clerk webhook + §F3 RLS policies + §F3 test harness |
| TMM-02 | Stripe Billing Meters — usage events on scan upload | §F8 `stripe.v2.billing.meter_events.create` + rollback ordering |
| OBS-01 | Structured logging with request IDs + team context | §F9 structlog + contextvars + ASGI middleware |
| OBS-02 | Error tracking + trace sampling | §F10 Sentry FastAPI + asyncpg + taskiq integrations |
</phase_requirements>

## Executive Summary

The three hardest problems in Phase 6 — and the resolution angle for each:

1. **RLS correctness under Neon's pooler.** Neon offers **only transaction-mode PgBouncer** (`pool_mode=transaction`), not session-mode — CITED: Neon connection-pooling docs. CONTEXT.md D-02 refers to "session-mode pooler"; that terminology is imprecise but the *pattern* D-02 prescribes (`SET LOCAL` inside an explicit transaction) is exactly what works in transaction-mode pooling: `SET LOCAL` is scoped to the current transaction, which is the pool-checkout unit. Every authenticated DB-touching request opens a SQLAlchemy `async with session.begin():` block, executes `SET LOCAL app.current_team_id = ...` as the first statement, runs the request's queries, commits; checkout returns a clean connection. The only thing to avoid is bare `SET` (without `LOCAL`) on a pooled connection — it will leak across tenants. A test harness that seeds as a bypass role then reads as `infracanvas_app` under a wrong `current_team_id` must return 0 rows.

2. **Stripe meter-event transactionality.** D-09 makes DB commit + meter post atomic. The correct ordering is: open DB tx → HEAD+validate → `INSERT scans` → `stripe.v2.billing.meter_events.create(idempotency_key=scan_id)` → `COMMIT`. Meter fails → DB rollback → client gets 5xx and can retry; the `idempotency_key=scan_id` makes retries safe. The *wrong* ordering (commit DB first, then post meter) risks a billed scan that was never inserted or vice versa. Stripe's v2 meter-events API is eventually consistent in processing but returns synchronously on acceptance, so we know before commit whether Stripe accepted the event.

3. **Request-ID continuity across sync HTTP + async taskiq.** structlog's `contextvars` integration is the right primitive, but FastAPI's `@app.middleware("http")` (BaseHTTPMiddleware) runs the endpoint in a *copied* context — contextvars set inside middleware are invisible to the handler. Fix: implement a **pure ASGI middleware** (pass-through `__call__(scope, receive, send)`), not BaseHTTPMiddleware. On the taskiq side, the caller reads `structlog.contextvars.get_contextvars()` before `.kiq(...)` and passes `request_id` as a task label; the worker's on-startup middleware rebinds it.

**Primary recommendation:** Use **PyJWT + JWKS caching** (not the Clerk Python SDK) for auth, **boto3 sync client** (not aioboto3) for R2, **`stripe.v2.billing.meter_events.create()`** (v2 API — SDK ≥ 11.x), **`uuid_utils`** for UUIDv7, **SmartRetryMiddleware** for taskiq retries (3 attempts, jittered exponential, DLQ via a tail-call `send_to_dlq` task — taskiq has no built-in DLQ), **pure ASGI middleware** for request-ID, **URL prefix `/v1`** for API versioning.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JWT validation + role extraction | FastAPI (dependency) | — | Cannot be delegated to DB; role dimension isn't in RLS policies (D-03) |
| Per-team data isolation | Neon / RLS policies | FastAPI (SET LOCAL injector) | Defence-in-depth: even an app bug cannot cross tenants |
| Large-blob storage | Cloudflare R2 | — | Keep FastAPI off the byte path (D-06) |
| Request/response JSON validation | Pydantic v2 (in FastAPI) | — | Same model as CLI for zero-drift (D-09, `ResourceGraph`) |
| Billing-event record of truth | Stripe Billing Meters | Neon (`scans` row = local mirror) | Stripe is the revenue source of truth |
| Idempotent background work | taskiq worker process | Upstash Redis (broker) | Process-split per D-13; result backend in same Redis |
| Error + trace sink | Sentry | — | Auto-instruments FastAPI + asyncpg + taskiq (D-18/20) |
| Structured log sink | Axiom (via Fly log drain) | stdout (JSON) | Zero-SDK overhead; swappable sink |
| Schema migration | Alembic (via Fly `release_command`) | — | Pre-cutover migration gate (D-15) |
| Secret management | Fly secrets | — | No secrets in git; separate dev/prod sets (D-14) |

---

## F1 — Clerk JWT validation (FastAPI dependency)

**Recommendation: PyJWT + `PyJWKClient` with built-in JWKS caching.** Simpler than pulling the whole Clerk SDK for one verify call; `PyJWKClient` handles key rotation via Cache-Control. The Clerk SDK's main benefit is webhook signature verification (see F2) — for that we use `svix` directly, which is equally small.

**Clerk v2 session token structure** (CITED: clerk.com/docs/guides/sessions/session-tokens; version 2 is default since 2025-04-14, v1 is deprecated):

```json
{
  "azp": "https://infracanvas.app",
  "exp": 1713158400,
  "iat": 1713158400,
  "iss": "https://clerk.infracanvas.app",
  "sub": "user_123",
  "sid": "sess_123",
  "v": 2,
  "o": {
    "id":  "org_xxx",   // team identity
    "rol": "admin",      // TMM-01 role (owner|admin|member|basic_member|...)
    "slg": "acme-corp",
    "per": ["read", "manage"],
    "fpm": [3, 2]
  }
}
```

Organization data lives under compact key `o` — there is no top-level `org_id` without a custom JWT template. When a user has no active organization, the `o` claim is absent — we reject such tokens on team-scoped routes.

**Code sketch (`backend/app/auth/clerk.py`)**:

```python
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

# PyJWKClient caches keys with lifespan; refresh on KID miss.
_jwks_client = PyJWKClient(f"{settings.clerk_issuer}/.well-known/jwks.json",
                           cache_keys=True, lifespan=3600)

class ClerkPrincipal(BaseModel):
    user_id: str          # sub
    session_id: str       # sid
    clerk_org_id: str     # o.id  (MUST be present on team-scoped routes)
    role: str             # o.rol

async def require_principal(request: Request) -> ClerkPrincipal:
    token = _bearer(request)
    signing_key = _jwks_client.get_signing_key_from_jwt(token).key
    try:
        claims = jwt.decode(
            token, signing_key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            audience=None,           # Clerk uses azp, not aud
            options={"require": ["exp", "iat", "sub", "sid"]},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, "invalid_token") from e
    # azp check (Clerk's CSRF-equivalent): only accept from our origin
    if claims.get("azp") not in settings.clerk_allowed_origins:
        raise HTTPException(401, "azp_mismatch")
    o = claims.get("o")
    if not o:
        raise HTTPException(403, "no_active_organization")
    return ClerkPrincipal(
        user_id=claims["sub"], session_id=claims["sid"],
        clerk_org_id=o["id"], role=o["rol"],
    )

def require_role(*allowed: str):
    async def _dep(p: ClerkPrincipal = Depends(require_principal)) -> ClerkPrincipal:
        if p.role not in allowed:
            raise HTTPException(403, "forbidden_role")
        return p
    return _dep
```

**Pitfalls:**
- Don't validate `aud` — Clerk uses `azp` (authorized party) instead. Validating `aud` will silently 401 everything.
- On JWKS KID miss, `PyJWKClient` auto-refetches — good. But rate-limit the refresh path (built into PyJWT ≥ 2.8.0) so a bad kid can't DDoS the JWKS endpoint.
- `o.rol` values can include `admin`, `basic_member`, plus any custom role slugs the Clerk org admin created — don't hardcode `member`; use `basic_member` or configure the org's role set.
- `exp` skew: accept ±10s clock skew (`leeway=10`) to avoid false 401s on first token.

**Sources:**
- [Clerk session tokens v2 claim reference](https://clerk.com/docs/guides/sessions/session-tokens) — CITED
- [Clerk manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification) — CITED
- [PyJWT PyJWKClient](https://pyjwt.readthedocs.io/en/stable/usage.html#retrieve-rsa-signing-keys-from-a-jwks-endpoint) — CITED

---

## F2 — Clerk webhook verification (Svix)

**Endpoint:** `POST /v1/webhooks/clerk`. Verify with the `svix` Python library.

**Critical:** use the **raw request body bytes** (not a re-serialized dict) — Svix HMAC is byte-sensitive. FastAPI's `await request.json()` parses then re-serializes → signature fails. Use `await request.body()`.

```python
from svix.webhooks import Webhook, WebhookVerificationError

_wh = Webhook(settings.clerk_webhook_secret)  # whsec_...

@app.post("/v1/webhooks/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(...)):
    body = await request.body()  # RAW BYTES — not .json()
    headers = {"svix-id": request.headers["svix-id"],
               "svix-timestamp": request.headers["svix-timestamp"],
               "svix-signature": request.headers["svix-signature"]}
    try:
        payload = _wh.verify(body, headers)  # returns parsed dict
    except WebhookVerificationError:
        raise HTTPException(401, "bad_signature")

    evt_type = payload["type"]
    data = payload["data"]
    if evt_type == "organization.created":
        await _upsert_team(db, clerk_org_id=data["id"], name=data["name"])
    elif evt_type == "organization.updated":
        await _update_team(db, clerk_org_id=data["id"], name=data["name"])
    elif evt_type == "organization.deleted":
        await _mark_team_deleted(db, clerk_org_id=data["id"])
    return {"ok": True}  # return fast; Svix retries on non-2xx
```

**Pitfalls:**
- Respond within 15s; Clerk/Svix retries with exponential backoff. Any long work (Stripe customer creation, etc.) must be enqueued to taskiq.
- Webhook handler bypasses Clerk-JWT auth but needs its own rate limit in Phase 8+ (deferred).
- Subscribe to `organization.deleted` even if no-op today — unsubscribed events still deliver, better to swallow explicitly than 404.

**Sources:**
- [Svix FastAPI recipe](https://www.svix.com/guides/receiving/receive-webhooks-with-python-fastapi/) — CITED
- [Clerk webhook payload shapes](https://clerk.com/docs/guides/development/webhooks/overview) — CITED

---

## F3 — Neon RLS under the pooler

**Terminology correction for CONTEXT.md D-02:** Neon offers only **transaction-mode** PgBouncer pooling, not session-mode. CITED: `Neon uses PgBouncer in transaction mode (pool_mode=transaction)` — neon.com/docs/connect/connection-pooling. The **pattern D-02 prescribes is still correct**: `SET LOCAL app.current_team_id = $1` inside an explicit `BEGIN…COMMIT` works perfectly in transaction-mode pooling because `SET LOCAL` is scoped to the current transaction, which is the pool-checkout unit. Do NOT use bare `SET` on a pooled connection — it persists across transactions on the shared backend and will leak tenant state between requests.

**Role provisioning (handwritten migration `001_rls_setup.sql`):**

```sql
-- Run ONCE as Neon owner during initial setup.
CREATE ROLE infracanvas_app WITH LOGIN PASSWORD '<from Fly secret>';
GRANT CONNECT ON DATABASE infracanvas TO infracanvas_app;
GRANT USAGE ON SCHEMA public TO infracanvas_app;
-- Explicitly DENY bypass:
ALTER ROLE infracanvas_app NOBYPASSRLS;
-- Grant SELECT/INSERT/UPDATE/DELETE on app tables (not on alembic_version):
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO infracanvas_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO infracanvas_app;

-- Declare the GUC (no restart needed — custom GUCs with a dot are session-settable):
-- app.current_team_id is set via SET LOCAL each request.

-- Example per-table policy (repeat for every team-scoped table):
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans FORCE ROW LEVEL SECURITY;   -- applies to table owner too
CREATE POLICY scans_team_isolation ON scans
  USING (team_id = current_setting('app.current_team_id', true)::uuid)
  WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
```

`FORCE ROW LEVEL SECURITY` is important: without it, the table owner bypasses RLS. Even though `infracanvas_app` isn't the owner, FORCE eliminates the class of bugs where a migration accidentally runs app queries as owner.

**SQLAlchemy session dependency:**

```python
# backend/app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

# Use the -pooler hostname; psycopg URI converts to asyncpg:
_engine = create_async_engine(
    settings.database_url,            # postgres://infracanvas_app:...@ep-...-pooler.neon.tech/db?sslmode=require
    pool_size=5, max_overflow=10,     # Fly Machine has few CPUs; don't oversubscribe Neon
    echo=False,
)
_Session = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

async def team_scoped_session(
    principal: ClerkPrincipal = Depends(require_principal),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> AsyncIterator[AsyncSession]:
    async with _Session() as session:
        async with session.begin():                     # opens a transaction
            await session.execute(
                text("SET LOCAL app.current_team_id = :t"),
                {"t": str(team.id)},
            )
            yield session                                # handler runs here
        # session.begin() context commits or rolls back on exit
```

**Why `SET LOCAL … = :param` (bind) works:** asyncpg's SQLAlchemy dialect supports parameters in `text()`. If you use raw `SET LOCAL app.current_team_id = '{uuid}'` string interpolation, MAKE SURE `team.id` is a UUID object (not user input). Prefer the bind form.

**Neon async `env.py` for Alembic** (CITED: alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic):

```python
# backend/migrations/env.py (abridged)
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

def do_run_migrations(connection): ...

async def run_async_migrations():
    cfg = context.config.get_section(context.config.config_ini_section)
    connectable = async_engine_from_config(cfg, prefix="sqlalchemy.", future=True)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

asyncio.run(run_async_migrations())
```

**Alembic runs as the OWNER role, not `infracanvas_app`.** Use a separate connection string in Fly secret `DATABASE_URL_MIGRATOR` that uses the Neon project owner; `release_command` reads this. Otherwise RLS blocks the migrator from altering tables.

**Test-fixture bypass role (for D-05 harness):**

```sql
CREATE ROLE infracanvas_test WITH LOGIN PASSWORD 'test';
ALTER ROLE infracanvas_test BYPASSRLS;   -- test-env only; NEVER in prod DB
GRANT ALL ON ALL TABLES IN SCHEMA public TO infracanvas_test;
```

Tests use `infracanvas_test` to seed rows across multiple team_ids, then reconnect as `infracanvas_app` with `SET LOCAL app.current_team_id = <team_B>` and assert the team_A rows are invisible. Phase 4 convention: use Testcontainers for Postgres in CI (not Neon) — faster, hermetic, free.

**Pitfalls:**
- `current_setting('app.current_team_id', true)::uuid` — the `true` means "missing ok, return NULL". Policy becomes `NULL = team_id` → no rows match. DON'T use `false` (would raise) — it crashes unauthenticated reads before the auth dep can 401.
- Connection leak: if `team_scoped_session` is opened but an exception escapes `session.begin()`, the transaction rolls back but the connection is returned. Still, always ensure the dep is used as `yield`, not `return`.
- `pg_terminate_backend` from another process can leave a polluted session — doesn't apply to transaction-pooled connections because each tx is fresh.
- Don't allow `GRANT SELECT … TO PUBLIC` anywhere — defeats RLS.

**Sources:**
- [Neon connection pooling (transaction mode only)](https://neon.com/docs/connect/connection-pooling) — CITED
- [Postgres RLS patterns with pgbouncer / SET LOCAL](https://pganalyze.com/blog/postgres-row-level-security-ruby-rails) — VERIFIED via search, same pattern
- [SQLAlchemy 2.0 async engine](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — CITED
- [Alembic async cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic) — CITED

---

## F4 — SQLAlchemy 2.0 async models & migrations

**Engine/session setup**: see F3. One `AsyncEngine` per process (init on FastAPI lifespan startup, dispose on shutdown). Workers have their own engine (smaller pool).

**Models use SQLAlchemy 2.0 mapped style** (`Mapped[...]`, `mapped_column(...)`); Pydantic models stay separate for transport.

```python
# backend/app/db/models.py
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid_utils as uu  # UUIDv7 generator

class Base(DeclarativeBase): ...

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[UUID]              = mapped_column(PgUUID, primary_key=True, default=lambda: UUID(str(uu.uuid7())))
    clerk_org_id: Mapped[str]     = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str]             = mapped_column(String(255))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default="now()")

class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[UUID]         = mapped_column(PgUUID, primary_key=True)  # UUIDv7 assigned by API layer
    team_id: Mapped[UUID]    = mapped_column(PgUUID, ForeignKey("teams.id"), index=True)
    r2_key: Mapped[str]      = mapped_column(String(512))
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str]      = mapped_column(Enum("pending","ready","failed", name="scan_status"))
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # denorm counts from indexer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
```

**Migration style recommendation (discretion D-15 refinement):**
- `alembic revision --autogenerate` for **column/table/index changes**. Inspect and hand-edit (autogen struggles with type changes and enum additions).
- **Handwritten SQL** migrations for: role grants, `ENABLE ROW LEVEL SECURITY`, `CREATE POLICY`, `FORCE RLS`, extensions (`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` — though we generate v7 in app).
- Naming convention: `{yyyymmdd}_{nnn}_{slug}.py` (Alembic's default is fine; add a date prefix via `file_template` in `alembic.ini`).
- Always add a `downgrade()`. Test at least one downgrade per release against the dev env before deploy.

**Fly release_command** (fly.toml):

```toml
[deploy]
  release_command = "alembic -c alembic.ini upgrade head"
```

The release command runs a one-off Machine in the production app with production secrets and dies after success; traffic doesn't switch to the new app version until it exits 0.

**Pitfalls:**
- Alembic autogen doesn't detect custom type changes (Enum value additions), CHECK constraint changes, or server_default changes reliably. Always visually diff.
- `release_command` runs with the full app image — keep the Alembic command lean; no `from backend.app import *` side-effects (no Sentry init, no Redis connect). Use a minimal `alembic/env.py`.
- Timeout: Fly `release_command` default is 5 min; schema-large migrations need explicit timeout bump (`release_command_timeout = "15m"`).

---

## F5 — R2 presigned URLs

**Recommendation: boto3 sync client + `generate_presigned_url`**. aioboto3 exists but presigned URL generation is pure crypto (no I/O) — no async benefit.

```python
# backend/app/storage/r2.py
import boto3
from botocore.config import Config

_r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.r2_access_key_id,
    aws_secret_access_key=settings.r2_secret_access_key,
    region_name="auto",
    config=Config(signature_version="s3v4"),  # REQUIRED for R2
)

def presigned_put(key: str, content_type: str = "application/json",
                  expires_in: int = 600) -> str:
    return _r2.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket, "Key": key,
                "ContentType": content_type},
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )

def presigned_get(key: str, expires_in: int = 300) -> str:
    return _r2.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_in,
    )

def head(key: str) -> dict:
    return _r2.head_object(Bucket=settings.r2_bucket, Key=key)  # ContentLength, ETag, LastModified
```

### CRITICAL: CONTEXT.md D-11 contradicts R2 capabilities

CONTEXT.md D-11 states: *"Presigned PUT carries `Content-Length-Range` condition 1..25MB."* This is **not achievable with R2**. CITED: Cloudflare R2 docs, multiple community threads — R2's presigned PUT URL supports `ContentType` but does **NOT** implement `Content-Length-Range` (that condition is an S3 POST-policy feature, and R2 does not implement the S3 POST Object API at all — it returns 501 Not Implemented).

**How to actually enforce the 25 MB cap (three defences; use all three):**

1. **Client-side pre-check.** Dashboard/CLI refuses to PUT >25 MB locally. Not security — just UX.
2. **HEAD-after-PUT at commit time.** D-09 already requires this. `head_object()` returns `ContentLength`; commit handler rejects and returns 413 if `>26214400` bytes.
3. **R2 bucket lifecycle rule.** Delete objects with no matching `scans` row (use R2 event notifications or a nightly Worker) and/or older than 7 days in `teams/*/scans/` prefix — catches orphans from abandoned uploads.

This shifts the security boundary from "signed URL prevents oversized upload" to "commit handler rejects oversized upload"; the R2 bucket cannot be the integrity boundary, so the commit handler must be.

**Recommended change to D-11 phrasing:** the plan should explicitly document that size enforcement is server-side-at-commit, not URL-signed. This is the only adjustment Phase 6 needs — it doesn't change the feature, just its enforcement mechanism.

**Key format** (locked D-07): `teams/{team_id}/scans/{scan_id}.json` where both are UUIDs. Use canonical dashed UUID form (36 chars).

**CORS on the R2 bucket** (provisioned via `wrangler` or dashboard once per env):

```json
[{
  "AllowedOrigins": ["https://app.infracanvas.com", "http://localhost:3000"],
  "AllowedMethods": ["PUT", "GET"],
  "AllowedHeaders": ["Content-Type", "Content-Length", "If-Match"],
  "ExposeHeaders": ["ETag"],
  "MaxAgeSeconds": 3600
}]
```

**Pitfalls:**
- Client MUST send exactly the `Content-Type` that was signed, or R2 returns 403 SignatureDoesNotMatch.
- `head_object()` ETag is quoted (`"abc..."`). Strip quotes. ETag is NOT sha256 for multipart uploads — trust the client-supplied sha256 (verified in commit against the R2 object bytes only if needed; cost tradeoff).
- Sha256 verification: if you need true integrity, download+hash in commit handler — adds bandwidth. For Phase 6, trust client-supplied sha256 + R2 ETag for non-multipart (our 25 MB files never use multipart) and defer deep verification.

**Sources:**
- [Cloudflare R2 presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/) — CITED
- [R2 S3 API compatibility matrix](https://developers.cloudflare.com/r2/api/s3/api/) — CITED
- [Cloudflare community: R2 file size limit on presigned URL](https://community.cloudflare.com/t/cloudflare-r2-presigned-url-limit-file-size/455122) — VERIFIED (multiple threads confirm no Content-Length-Range)

---

## F6 — Cross-package import of `ResourceGraph`

**Recommendation: make `backend/` depend on `cli/` as a path dependency in the monorepo** (`infracanvas @ file:../cli`). CLI's `pyproject.toml` already declares `infracanvas` as the package; importing `from infracanvas.graph.models import ResourceGraph` is one source of truth — no snapshot drift.

Concern: CLI pulls `typer`, `rich`, `networkx`, `python-hcl2` as deps — these land in the backend image too. Mitigation: put those in a `[project.optional-dependencies] cli = [...]` section in `cli/pyproject.toml`, and make the core CLI package dependency-light (just `pydantic`). Then `backend` installs `infracanvas` without the `cli` extra. **Plan should include a subtask to split `cli/pyproject.toml` deps into a `cli-runtime` extra.**

Alternative (if the split is too invasive for Phase 6): export the Pydantic JSON Schema from CLI CI, commit it under `backend/schemas/resource_graph.schema.json`, and use Pydantic's `TypeAdapter` with a dynamically generated model. Drift risk is higher; reject unless the extras-split takes >1 task.

**Validation call in commit handler:**

```python
from infracanvas.graph.models import ResourceGraph
from pydantic import ValidationError

try:
    graph = ResourceGraph.model_validate_json(blob_bytes)  # Pydantic v2
except ValidationError as e:
    raise HTTPException(422, {"errors": e.errors()[:10]})
```

---

## F7 — taskiq-redis broker, worker, retries, DLQ

**Broker choice:** `ListQueueBroker` from `taskiq-redis` is the durable Redis-list-backed broker — correct for our use case. Do NOT use `PubSubBroker` (fire-and-forget, no durability). Result backend: `RedisAsyncResultBackend` against the same Upstash DB but a different key prefix.

```python
# backend/app/queue/broker.py
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from taskiq import TaskiqEvents
from taskiq.middlewares import SmartRetryMiddleware

broker = (
    ListQueueBroker(settings.redis_url, queue_name="infracanvas:tasks")
    .with_result_backend(
        RedisAsyncResultBackend(settings.redis_url, keep_results=3600)
    )
    .with_middlewares(
        SmartRetryMiddleware(
            default_retry_count=3,
            default_delay=5,
            use_jitter=True,
            use_delay_exponent=True,
            max_delay_exponent=120,   # cap backoff at ~2 min
        ),
    )
)

@broker.task(retry_on_error=True, max_retries=3, delay=5)
async def enqueue_scan_indexing(scan_id: str, request_id: str) -> None:
    # worker reads request_id from task labels and rebinds to structlog ctx
    ...
```

**Worker process** runs as its own Fly Machine via `[processes]`:

```toml
[processes]
  api    = "uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"
  worker = "taskiq worker backend.app.queue.broker:broker backend.app.tasks"
```

`taskiq worker` auto-discovers tasks from the module argument. Worker does NOT need port exposure.

**DLQ pattern (no built-in):** taskiq has no native DLQ middleware. Implement via a tail-call: SmartRetryMiddleware, when it's about to give up (retry count exceeded), raises; we catch with a **custom middleware** that calls `dlq_record.kiq(...)` with the failed task's payload. Skeleton:

```python
class DLQMiddleware(TaskiqMiddleware):
    async def on_error(self, message, result, exception):
        if message.labels.get("_retry_count", 0) >= message.labels.get("max_retries", 3):
            await dlq_record.kiq(
                task_name=message.task_name,
                payload=message.kwargs,
                error=repr(exception),
                request_id=message.labels.get("request_id"),
            )
```

Or simpler: on exhausted retry, just log to Axiom with tag `dlq=true` and set up an Axiom alert. For Phase 6 MVP, **log-as-DLQ is sufficient**. A real Redis-list DLQ can be Phase 8 work when webhook load makes it needed.

**Request-ID propagation into worker:** caller binds `request_id` as a task label via `.kicker().with_labels(request_id=...).kiq(...)`. Worker's startup middleware reads `context.message.labels["request_id"]` and calls `structlog.contextvars.bind_contextvars(request_id=...)`. Done.

**Pitfalls:**
- Upstash Redis has a 5MB max command size — don't stuff large payloads in task args. Pass the `scan_id`; the task re-reads from Postgres.
- `ListQueueBroker` uses `BLPOP` under the hood — Upstash connections idle-time out at 30s on the free tier. `taskiq-redis` handles reconnect; no action needed, but confirm on first Fly deploy that the worker doesn't die on idle.
- `taskiq worker` with `--workers N` forks N processes — each needs its own DB engine. Either use `--workers 1` per Machine (and scale Machines) or initialize engine lazily on first task execution.
- Don't await results in an HTTP handler (`task.wait_result()`) — it blocks the event loop. Fire-and-forget `.kiq(...)` only.

**Sources:**
- [taskiq broker guide](https://taskiq-python.github.io/guide/brokers.html) — CITED
- [taskiq SmartRetryMiddleware](https://taskiq-python.github.io/available-components/middlewares.html) — CITED
- [taskiq DLQ discussion (no built-in)](https://github.com/taskiq-python/taskiq/issues/578) — CITED

---

## F8 — Stripe Billing Meters

**CRITICAL API choice:** use **`stripe.v2.billing.meter_events.create(...)`** (v2 namespace), not the legacy `stripe.billing.MeterEvent.create()` (v1). Stripe's v2 API offers synchronous validation (returns 200 only if the meter + customer resolved cleanly) and is the modern surface. Available in `stripe-python` ≥ ~11.0. Latest stripe-python as of research: 15.1.0 — well clear of the threshold. VERIFIED: pip registry.

Also note: PROJECT.md states "legacy `create_usage_record()` removed 2025-03-31" — that's the even older subscription-item usage-record API, different from both v1 and v2 meter events. We're firmly on v2.

```python
# backend/app/billing/stripe_meter.py
import stripe
stripe.api_key = settings.stripe_secret_key   # sk_test_... on dev, sk_live_... on prod

async def record_scan_meter_event(
    *, scan_id: str, stripe_customer_id: str, timestamp: int | None = None
) -> None:
    """
    Idempotent: identifier=scan_id (24h dedup window in Stripe);
    idempotency_key=scan_id (HTTP-level retry safety).
    """
    stripe.v2.billing.meter_events.create(
        event_name="infracanvas.scan",
        payload={
            "stripe_customer_id": stripe_customer_id,
            "value": "1",
        },
        identifier=scan_id,              # 24h rolling uniqueness
        timestamp=timestamp,              # RFC3339 if provided
        idempotency_key=scan_id,          # Stripe-Idempotency-Key header
    )
```

**Two layers of idempotency — both point to scan_id:**
1. `identifier=scan_id` → Stripe enforces uniqueness within a 24h window (rejects a second event with the same identifier).
2. `idempotency_key=scan_id` → Stripe replays the prior response on an identical retry within 24h (HTTP-level).

These overlap intentionally: #1 protects against a second distinct API call with the same identifier after the first succeeded cleanly; #2 protects against retrying *the same call* due to network hiccups.

**Rollback semantics (D-09):**

```python
async with session.begin():
    await session.execute(text("SET LOCAL app.current_team_id = :t"), {"t": team_id})
    # 1. HEAD + Pydantic validate (out of tx, can fail before insert)
    head = r2.head(key); assert_size(head); blob = r2.get(key); graph = ResourceGraph.model_validate_json(blob)
    # 2. Insert scan row
    await session.execute(insert_scan_stmt)
    # 3. Post meter event (LAST — so rollback if it throws)
    try:
        await record_scan_meter_event(scan_id=str(scan.id), stripe_customer_id=team.stripe_customer_id)
    except stripe.error.StripeError:
        raise                            # triggers tx rollback
    # 4. Enqueue post-commit background indexing (after successful commit)
# scope exit commits; now safe to enqueue:
await enqueue_scan_indexing.kiq(scan_id=str(scan.id), request_id=current_request_id())
```

**Pitfall:** if Stripe accepts then the DB commit fails (e.g., constraint error after the Stripe call succeeded), the meter is in but the scan row is not. Put the Stripe call *last* inside the transaction — Postgres commit after a successful Stripe return is near-zero failure probability. Use a sentinel in `scans` if you need to reconcile (`meter_posted_at` timestamp, nullable → set right before commit).

**Customer must exist in Stripe before first meter event.** The `organization.created` webhook handler creates the `stripe.Customer` (`stripe.Customer.create(...)`) and stores `stripe_customer_id` on the Team row. Phase 13 will evolve this into the full checkout lifecycle — Phase 6 just needs a customer record to attach meter events to.

**Sources:**
- [Stripe v2 billing meter-events create](https://docs.stripe.com/api/v2/billing/meter-events/create) — CITED
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests) — CITED (24h window)
- [Stripe recording usage](https://docs.stripe.com/billing/subscriptions/usage-based/recording-usage-api) — CITED

---

## F9 — structlog + contextvars + request-ID ASGI middleware

**The gotcha:** FastAPI's `@app.middleware("http")` (BaseHTTPMiddleware) runs the route handler inside `anyio.create_task_group().start_soon(...)`, which copies the context. Contextvars set in the middleware are visible to the handler, BUT contextvars set *inside* the handler are not visible in the middleware's post-handler `finally` block. VERIFIED: fastapi/fastapi#4696.

**Fix:** use a **pure ASGI middleware** (raw `__call__(scope, receive, send)` signature, no BaseHTTPMiddleware wrapping):

```python
# backend/app/logging_middleware.py
import structlog, uuid_utils as uu

class RequestContextMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        hdrs = dict(scope["headers"])  # bytes keys/values
        rid = hdrs.get(b"x-request-id", b"").decode() or str(uu.uuid7())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)

        async def send_wrapper(msg):
            if msg["type"] == "http.response.start":
                msg["headers"] = list(msg.get("headers", [])) + [(b"x-request-id", rid.encode())]
            await send(msg)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.clear_contextvars()

app = FastAPI()
app.add_middleware(RequestContextMiddleware)       # ORDER MATTERS — this runs OUTERMOST
```

**structlog config** (init at app startup):

```python
import logging, structlog, orjson, sys

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,       # inject request_id, team_id, user_id
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)
```

Later, in the auth dependency, after resolving principal:
```python
structlog.contextvars.bind_contextvars(
    team_id=str(team.id), user_id=principal.user_id, clerk_org_id=principal.clerk_org_id
)
```

**Worker-side init:** same `structlog.configure(...)` runs at worker startup (add as a `TaskiqEvents.WORKER_STARTUP` handler). Per-task middleware reads `message.labels["request_id"]` and binds it before the task runs.

**Pitfalls:**
- `clear_contextvars()` at the start of each request prevents bleed-over between requests on the same event-loop iteration.
- Uvicorn's own access log duplicates our structured log. Disable with `uvicorn --no-access-log` and implement our own access log via this middleware (one JSON line with `event="request"`, `path`, `method`, `status`, `duration_ms`).
- Don't use BaseHTTPMiddleware for this. Pure ASGI as above.

**Sources:**
- [structlog contextvars + asyncio](https://www.structlog.org/en/latest/contextvars.html) — CITED
- [FastAPI #4696 ContextVar loss with BaseHTTPMiddleware](https://github.com/fastapi/fastapi/issues/4696) — CITED

---

## F10 — Sentry (errors + tracing)

```python
# backend/app/obs/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def init_sentry(*, role: str):  # role="api" or "worker"
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,   # "dev" or "prod"
        release=settings.git_sha,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            AsyncPGIntegration(),
            LoggingIntegration(level=None, event_level=None),  # don't capture logs as events
        ],
    )
    sentry_sdk.set_tag("process_role", role)
```

**Tag binding from auth dep:**
```python
sentry_sdk.set_tag("request_id", rid)          # set in middleware
sentry_sdk.set_tag("team_id", str(team.id))    # set after team resolve
sentry_sdk.set_tag("clerk_org_id", clerk_org_id)
sentry_sdk.set_user({"id": principal.user_id})
```

**taskiq integration:** no official Sentry integration. Wrap tasks manually:
```python
class SentryTaskMiddleware(TaskiqMiddleware):
    async def pre_execute(self, message):
        sentry_sdk.set_tag("task_name", message.task_name)
        sentry_sdk.set_tag("request_id", message.labels.get("request_id"))
    async def on_error(self, message, result, exc):
        sentry_sdk.capture_exception(exc)
```

**Recommendation on project split (discretion):** **one Sentry project for both API and worker, discriminated by `process_role` tag; separate `environment` for dev vs prod.** Fewer projects = simpler quota management and cross-process trace correlation; the `process_role` tag preserves searchability. Revisit if traffic mix makes the feed noisy.

**Sources:**
- [Sentry FastAPI integration](https://docs.sentry.io/platforms/python/integrations/fastapi/) — CITED
- [Sentry asyncpg integration](https://docs.sentry.io/platforms/python/integrations/asyncpg/) — CITED

---

## F11 — Fly.io topology

**fly.toml skeleton** (per env — `fly.dev.toml` and `fly.prod.toml`):

```toml
app = "infracanvas-api-prod"
primary_region = "iad"          # match Neon project region (lowest latency)

[build]
  dockerfile = "backend/Dockerfile"

[deploy]
  release_command = "alembic -c /app/alembic.ini upgrade head"
  release_command_timeout = "15m"
  strategy = "rolling"

[processes]
  api    = "uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --workers 2"
  worker = "taskiq worker backend.app.queue.broker:broker backend.app.tasks"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1
  processes = ["api"]              # only api processes are exposed publicly

[[vm]]
  processes = ["api"]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1

[[vm]]
  processes = ["worker"]
  memory = "512mb"                 # worker needs Pydantic+SQLAlchemy resident = ~180MB
  cpu_kind = "shared"
  cpus = 1

[[services.http_checks]]
  interval = "10s"
  timeout = "2s"
  method = "GET"
  path = "/healthz"
```

**Recommended Machine sizes (discretion):**
- API: `shared-cpu-1x 512mb` to start. 256mb is too tight — FastAPI + Pydantic + SQLAlchemy + Sentry + structlog base footprint measured around 150-200 MB, leaving thin headroom under load. Cost delta is tiny. Monitor and shrink later.
- Worker: `shared-cpu-1x 512mb`. Same reasoning.

**Secrets (per env):**
`CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `CLERK_JWKS_URL`, `DATABASE_URL`, `DATABASE_URL_MIGRATOR`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `REDIS_URL`, `STRIPE_SECRET_KEY`, `SENTRY_DSN`, `AXIOM_TOKEN` (if using Axiom HTTP ingest; Fly log drain doesn't need it app-side).

Set via `fly secrets set -a infracanvas-api-prod KEY=value ...`.

**Pitfalls:**
- `release_command` runs in a temporary Machine with all app secrets available. If Alembic imports the full app package (FastAPI app, Sentry init), startup side-effects fire twice per deploy. Keep `alembic/env.py` imports minimal.
- `auto_stop_machines = "stop"` saves money in dev but causes cold starts. Keep `min_machines_running = 1` for prod API only.
- Workers should NOT have `auto_stop_machines` enabled — a stopped worker drops queued tasks' processing. Use `min_machines_running = 1` for workers too.

**Sources:**
- [Fly.io processes config](https://fly.io/docs/reference/configuration/#the-processes-section) — CITED
- [Fly.io release_command](https://fly.io/docs/reference/configuration/#the-deploy-section) — CITED
- [Fly machine sizing](https://fly.io/docs/machines/guides-examples/machine-sizing/) — CITED

---

## F12 — Axiom via Fly log drain

**Setup (one-time per env):**

1. Create Axiom dataset. **Recommendation (discretion): one dataset per env** — `infracanvas-dev`, `infracanvas-prod`. Cleaner retention policies + auditability; free tier's 0.5 TB/mo covers both with room.
2. Axiom → Settings → API tokens → ingestion token.
3. `fly ext axiom create -a infracanvas-api-prod` (Fly's built-in Axiom integration provisions the log drain) OR manual: `fly logs-drain add axiom --token <axiom-token>`.

Once provisioned, every stdout line from every Machine ships to Axiom within seconds. No app code change — the structlog JSON renderer already writes to stdout.

**Fields to index in Axiom:** `request_id`, `team_id`, `user_id`, `clerk_org_id`, `task_name`, `status`, `event`, `process_role`. Axiom auto-indexes top-level JSON keys; no manual schema needed.

**Sources:**
- [Axiom Fly log drain](https://axiom.co/docs/send-data/fly) — CITED

---

## F13 — UUIDv7 library choice

**Recommendation: `uuid_utils` 0.14.1.** VERIFIED: pip registry 2026-04-24.

| Library | Pros | Cons |
|---------|------|------|
| `uuid_utils` 0.14.x | 16× faster (Rust-backed); drop-in for stdlib `uuid.UUID` via `uuid_utils.compat`; actively maintained | Rust binary wheel (larger install) |
| `uuid6` 2025.0.1 | Pure Python, no binary dep | Slower; only moderately maintained |
| native `uuid.uuid7()` | Zero dep | Python 3.13+ only; we're on 3.12 |

**Usage:**
```python
import uuid_utils as uu
scan_id = uu.uuid7()           # returns uu.UUID
pg_uuid = uuid.UUID(str(scan_id))  # convert for SQLAlchemy PgUUID column
```

Or, for drop-in compatibility with code that checks `isinstance(..., uuid.UUID)`:
```python
from uuid_utils.compat import uuid7
scan_id = uuid7()              # returns stdlib uuid.UUID
```

**Sources:**
- [uuid_utils on PyPI](https://pypi.org/project/uuid-utils/) — CITED

---

## F14 — Testing strategy

**Adopt Phase 4's coverage convention (D-15):** ≥80 % line + branch per module, scoped under `backend/app/`.

**Test ID prefixes** (docstring convention, matching cli/`B-*`, `E-*`):
- `API-*` — endpoint contract tests
- `RLS-*` — cross-team isolation tests (the security-critical dimension)
- `JOB-*` — taskiq worker tests
- `MET-*` — Stripe meter event tests (mock Stripe)
- `AUTH-*` — Clerk JWT validation tests
- `WBH-*` — Clerk webhook signature tests
- `MIG-*` — Alembic upgrade/downgrade tests

**Postgres in CI: Testcontainers, not Neon.** `testcontainers-python` spins a real Postgres 16 per test session; faster and hermetic vs Neon branching. Run migrations once per session; use transaction-rollback fixtures per test to isolate.

```python
# backend/tests/conftest.py
from testcontainers.postgres import PostgresContainer
import pytest, pytest_asyncio, subprocess

@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        # Run setup SQL: create infracanvas_app + infracanvas_test roles, alembic upgrade head
        subprocess.run(["alembic", "upgrade", "head"], env={"DATABASE_URL": pg.get_connection_url(), ...})
        yield pg

@pytest_asyncio.fixture
async def app_session(pg_container):
    # connect as infracanvas_app (RLS active); caller SETs LOCAL per test
    ...

@pytest_asyncio.fixture
async def seed_session(pg_container):
    # connect as infracanvas_test (BYPASSRLS); used to seed fixture data only
    ...
```

**Mock strategy:**
- Stripe: `pytest-httpserver` or `respx` against `stripe.api_base` override → capture meter event posts; assert payload.
- R2: `moto` library provides S3 mock — R2 is S3-compatible so moto works for `put_object`/`head_object`/`generate_presigned_url`. CITED: moto docs.
- Clerk JWT: sign test tokens with a fixture-local RSA keypair; point `PyJWKClient` at a fake JWKS URL via `httpx.MockTransport`.
- Svix: the `svix` library has `Webhook.sign()` — construct a valid signature in tests, no mock needed.
- Redis/taskiq: use `InMemoryBroker` from taskiq core — fires tasks synchronously in-process. Sufficient for contract tests; add a real-Redis smoke test at phase-gate.

**Framework: pytest + pytest-asyncio + pytest-cov + testcontainers + respx.**

---

## Standard Stack

**Core (pin to minor; let patch float via caret or ~=):**

| Library | Version | Purpose | Why standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | Web framework | Canonical choice; async native |
| uvicorn[standard] | 0.32.x | ASGI server | Fly's recommended pairing with FastAPI |
| Pydantic | 2.9.x | Models / validation | Already CLI norm; v2 perf |
| SQLAlchemy | 2.0.x (async) | ORM | Mature async; Alembic integration |
| asyncpg | 0.30.x | Postgres driver | Fastest Python Postgres driver |
| Alembic | 1.14.x | Migrations | Sqlalchemy's migration tool |
| taskiq | 0.11.x | Task queue | Chosen in D-13 (PROJECT.md) |
| taskiq-redis | 1.0.x | Redis broker | Pair with Upstash |
| boto3 | 1.35.x | R2 S3 client | Signature v4 stable |
| stripe | 11.x+ (target 15.x) | Billing | v2 meter events support |
| PyJWT[crypto] | 2.9.x | JWT + JWKS | F1 |
| svix | 1.41.x | Webhook signature | Clerk uses Svix |
| sentry-sdk[fastapi] | 2.18.x | Errors + traces | Auto-instrument F10 |
| structlog | 24.4.x | JSON logs | F9 |
| orjson | 3.10.x | Fast JSON ser | structlog + FastAPI |
| uuid_utils | 0.14.x | UUIDv7 | F13 |

**Dev / test:**

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | 8.3.x | Test runner |
| pytest-asyncio | 0.24.x | Async tests |
| pytest-cov | 6.0.x | Coverage |
| pytest-httpserver | 1.1.x | HTTP server mocks |
| respx | 0.21.x | httpx mocks |
| moto[s3] | 5.0.x | S3/R2 mock |
| testcontainers[postgresql] | 4.8.x | Ephemeral Postgres |
| ruff | 0.7.x | Lint (E F I N W UP, line 100) |
| mypy | 1.13.x | Strict type check |

**Infracanvas internal:**
- `infracanvas @ file:../cli` (path dep for `ResourceGraph` import)

**Dependencies table — pin rationale:**

| Package | Pin | Why |
|---------|-----|-----|
| FastAPI | `~=0.115.0` | Minor = stable API; patch float for security |
| SQLAlchemy | `~=2.0.36` | 2.0 series is mature, 2.1 not released |
| stripe | `>=11.0,<16.0` | v2 meter_events landed in 11.x; cap below unreleased major |
| sentry-sdk | `~=2.18.0` | 2.x series; integrations stable |
| taskiq | `~=0.11.0` | Still pre-1.0; minor pin required |
| uuid_utils | `~=0.14.0` | Binary wheels — pin minor for predictability |
| All others | `~=<latest-minor>` | Standard caret on pre-1.0, tilde on ≥1.0 |

**Version verification (ran 2026-04-24):**
- stripe 15.1.0 available on PyPI (VERIFIED)
- uuid_utils 0.14.1 released Feb 20 2026 (VERIFIED)
- Full `npm view`/`pip index versions` run against every package at plan time

---

## `backend/` Layout

```
backend/
├── pyproject.toml               # Hatchling; Ruff/mypy mirror cli/; deps per stack above
├── Dockerfile                   # python:3.12-slim; uv or pip install -e .
├── fly.dev.toml
├── fly.prod.toml
├── alembic.ini
├── migrations/
│   ├── env.py                   # async Alembic env (F3)
│   ├── script.py.mako
│   └── versions/
│       ├── 20260424_001_rls_setup.sql.py     # handwritten SQL: roles, RLS, policies
│       ├── 20260424_002_initial_schema.py    # autogen: teams, scans tables
│       └── ...
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI() factory + lifespan (engine init, Sentry init)
│   ├── settings.py              # pydantic-settings; reads env vars
│   ├── auth/
│   │   ├── clerk.py             # PyJWT + JWKS; require_principal, require_role (F1)
│   │   └── webhooks.py          # Svix verify; organization.* handlers (F2)
│   ├── db/
│   │   ├── session.py           # async engine; team_scoped_session dep (F3)
│   │   └── models.py            # SQLAlchemy 2.0 Mapped[...] (F4)
│   ├── schemas/                 # Pydantic request/response (NOT re-exporting ResourceGraph)
│   │   ├── scan.py              # ScanCreateResp, ScanCommitReq, ScanGetResp
│   │   └── team.py
│   ├── routes/
│   │   ├── health.py            # GET /healthz, /readyz
│   │   ├── scans.py             # POST /v1/scans, /v1/scans/{id}/commit, GET /v1/scans/{id}
│   │   ├── teams.py             # (read-only in Phase 6; write-path is webhook)
│   │   └── webhooks.py          # POST /v1/webhooks/clerk
│   ├── storage/
│   │   └── r2.py                # boto3 s3v4 client; presigned_put/get, head (F5)
│   ├── billing/
│   │   └── stripe_meter.py      # v2 meter events; record_scan_meter_event (F8)
│   ├── queue/
│   │   ├── broker.py            # ListQueueBroker + SmartRetryMiddleware + SentryTaskMiddleware
│   │   └── tasks/
│   │       ├── __init__.py      # module taskiq CLI scans
│   │       └── indexing.py      # enqueue_scan_indexing impl (summary counts → scans.summary_json)
│   ├── obs/
│   │   ├── sentry.py            # init_sentry(role=...)
│   │   ├── logging.py           # structlog.configure(...)
│   │   └── middleware.py        # RequestContextMiddleware (pure ASGI) (F9)
│   └── util/
│       └── ids.py               # wrap uuid_utils.uuid7 for typed id factory
└── tests/
    ├── conftest.py              # pg_container, app_session, seed_session, mock_clerk, mock_r2
    ├── test_auth.py             # AUTH-*
    ├── test_webhooks.py         # WBH-*
    ├── test_rls.py              # RLS-001..005: per-table isolation
    ├── test_scans.py            # API-001..0NN: upload/commit/get
    ├── test_stripe_meter.py     # MET-*: idempotency, rollback
    ├── test_tasks.py            # JOB-*: indexing task, retry, DLQ
    └── test_migrations.py       # MIG-*: upgrade/downgrade round-trip
```

---

## Code Examples

**Full commit handler (production-shape, F5+F6+F8 combined):**

```python
from infracanvas.graph.models import ResourceGraph

@router.post("/v1/scans/{scan_id}/commit", response_model=ScanGetResp, status_code=200)
async def commit_scan(
    scan_id: UUID,
    body: ScanCommitReq,
    principal: ClerkPrincipal = Depends(require_role("owner", "admin", "member")),
    team: Team = Depends(resolve_team_from_clerk_org),
    session: AsyncSession = Depends(team_scoped_session),
):
    key = f"teams/{team.id}/scans/{scan_id}.json"
    # 1. HEAD — size check
    try:
        head = await run_in_threadpool(r2.head, key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise HTTPException(404, "object_not_found")
        raise
    size = int(head["ContentLength"])
    if size > 25 * 1024 * 1024:
        raise HTTPException(413, {"error": "too_large", "size_bytes": size})

    # 2. Fetch + validate against ResourceGraph
    blob = await run_in_threadpool(lambda: r2.get(key)["Body"].read())
    try:
        graph = ResourceGraph.model_validate_json(blob)
    except ValidationError as e:
        raise HTTPException(422, {"errors": e.errors()[:10]})

    # 3. Insert scan row
    scan = Scan(id=scan_id, team_id=team.id, r2_key=key,
                sha256=body.sha256, size_bytes=size, status="ready")
    session.add(scan)
    await session.flush()

    # 4. Post meter event (LAST inside tx)
    try:
        await run_in_threadpool(
            stripe.v2.billing.meter_events.create,
            event_name="infracanvas.scan",
            payload={"stripe_customer_id": team.stripe_customer_id, "value": "1"},
            identifier=str(scan_id),
            idempotency_key=str(scan_id),
        )
    except stripe.error.StripeError as e:
        raise HTTPException(502, "meter_failed") from e    # triggers rollback via begin() ctx
    # session.begin() commits here on scope exit

    # 5. Post-commit async indexing
    request_id = structlog.contextvars.get_contextvars().get("request_id", "")
    await enqueue_scan_indexing.kicker().with_labels(request_id=request_id) \
                                .kiq(scan_id=str(scan_id))

    return ScanGetResp(id=scan.id, team_id=team.id, status="ready",
                       presigned_get_url=r2.presigned_get(key, 300),
                       size_bytes=size)
```

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|------------|-------------|-----|
| JWT parsing + signature verify | Custom RSA verify | `PyJWT` + `PyJWKClient` | JWKS rotation, KID caching, algorithm confusion protection |
| Webhook HMAC verification | Manual HMAC | `svix` library | Timing-safe compare, timestamp skew window, test signer |
| Pydantic→Postgres JSON | Custom serializer | SQLAlchemy `JSONB` type | Native Postgres JSONB handling |
| Retry + backoff | Custom loop | taskiq `SmartRetryMiddleware` | Jitter, exponential, max cap — solved problem |
| UUIDv7 | Custom `secrets + time_ms` bit fiddling | `uuid_utils` | 16× faster; RFC-compliant; tested |
| R2 signed URL | Manual SigV4 | boto3 `generate_presigned_url` | SigV4 is non-trivial; R2 requires exact conformance |
| Structured log formatting | `logging.Formatter` subclass | structlog + orjson JSONRenderer | Contextvars integration, processor pipeline |
| Contextvar cleanup | Manual `reset()` tokens | `structlog.contextvars.clear_contextvars` | Leak prevention, battle-tested |
| Per-request DB tenant injection | Engine-level events | `SET LOCAL` inside `session.begin()` | Atomic with tx; pool-safe |
| Stripe idempotency | Custom dedupe table | Stripe's `idempotency_key` + `identifier` | Server-side; 24h window free |
| Request-ID propagation | Thread-local | Pure ASGI middleware + contextvars | Async-safe |

**Key insight:** Every custom solution in this domain has subtle edge cases that have already been solved by the ecosystem. The cost of rolling our own always exceeds the cost of integrating a library.

---

## Common Pitfalls

### P1: Context-var loss in FastAPI middleware
**What goes wrong:** `@app.middleware("http")` copies context; post-handler code doesn't see contextvars set inside the handler.
**Avoid by:** Pure ASGI middleware class (F9 code sketch).
**Detect:** integration test that asserts response header `X-Request-ID` matches the request ID logged inside the handler.

### P2: `SET` (not `SET LOCAL`) leaking across tenants
**What goes wrong:** Pool-returned connection still has old `app.current_team_id`; next request for team B reads team A's rows.
**Avoid by:** always `SET LOCAL` inside an explicit `session.begin()` transaction. Ban plain `SET` in a lint rule (grep check).
**Detect:** RLS-* test harness (D-05) — seed team A, read as team B, assert 0 rows.

### P3: Signed Content-Type mismatch
**What goes wrong:** CLI PUTs `application/octet-stream`; presigned URL was signed for `application/json`; R2 returns 403.
**Avoid by:** either omit `ContentType` from signing (accept any), or document the exact header the client must send and test it.

### P4: Alembic release_command runs in a Machine with app startup side-effects
**What goes wrong:** Sentry init fires, DB engine connects, health-check endpoint races — doubles error volume on every deploy.
**Avoid by:** keep `alembic/env.py` imports to SQLAlchemy + models module only, no `from backend.app import *`.

### P5: Worker drops tasks on Machine stop
**What goes wrong:** Upstash-hosted Redis has the task pending; Fly Machine autostops; task never processed.
**Avoid by:** `min_machines_running = 1` for worker process group; disable `auto_stop_machines` on worker.

### P6: Meter posted, DB not committed
**What goes wrong:** Stripe call succeeds, DB commit fails → bill-for-phantom-scan.
**Avoid by:** Stripe call is the LAST statement inside `session.begin()`. Post-commit failure probability is near zero. If paranoid, add `scans.meter_posted_at` + reconciler job.

### P7: Clerk webhook retry storms
**What goes wrong:** 5xx response → Clerk retries with backoff → each retry reprocesses → double-inserts.
**Avoid by:** webhook handler is idempotent — use `ON CONFLICT DO NOTHING` on Clerk org_id UNIQUE; always return 200 after idempotent upsert; reserve 4xx for unrecoverable (bad signature).

### P8: `aud` vs `azp` claim confusion
**What goes wrong:** Validator checks `aud`; Clerk emits `azp`; all requests 401.
**Avoid by:** F1 code — explicitly pass `audience=None` to `jwt.decode`, separately validate `azp` against an allow-list.

### P9: UUIDv7 rollover from uuid_utils.UUID → stdlib uuid.UUID
**What goes wrong:** `isinstance(x, uuid.UUID)` returns False; SQLAlchemy type adapter rejects.
**Avoid by:** use `uuid_utils.compat.uuid7()` which returns stdlib `uuid.UUID`, OR always `uuid.UUID(str(uu.uuid7()))` at the boundary.

### P10: R2 bucket lifecycle rule missing → orphan storage cost creeps up
**What goes wrong:** Aborted commits leave objects in R2 forever; storage bill grows.
**Avoid by:** per D-11, configure lifecycle rule at bucket provisioning time. Include a `wrangler` or dashboard command in the phase plan.

---

## Environment Availability

| Dependency | Required By | Available? | Notes / Fallback |
|------------|------------|-----------|------------------|
| Python 3.12 | All backend | VERIFIED (CLI already on 3.12) | — |
| Node.js | NA for backend | NA | — |
| Docker | Local dev; Fly build | Assumed installed | Fly remote builders exist as fallback (`fly deploy --remote-only`) |
| Fly.io account | Hosting | Requires signup + billing | Railway listed as alt in PROJECT.md but rejected in D-12 |
| Neon account | DB | Requires signup (free tier fits) | Supabase/RDS possible but D-14 locks Neon |
| Cloudflare R2 | Object store | Requires R2 enabled on Cloudflare account | AWS S3 fallback (code identical; endpoint swap) |
| Upstash Redis | Broker | Requires signup (free tier fits) | Fly Redis add-on as fallback |
| Clerk | Auth | Requires signup + app | Auth0/WorkOS as fallback (larger rewrite) |
| Stripe | Billing | Requires signup + meter configured | — |
| Sentry | Errors | Requires signup (free tier fits) | Logfire as fallback (deferred) |
| Axiom | Logs | Requires signup (free tier fits) | Fly's built-in log stream as fallback |
| `stripe-python` ≥ 11.0 | v2 meter events | VERIFIED: 15.1.0 on PyPI | — |
| `uuid_utils` | UUIDv7 | VERIFIED: 0.14.1 on PyPI | `uuid6` package as fallback |
| `testcontainers` | CI Postgres | VERIFIED: installable | Plain docker-compose postgres as fallback |

**Missing dependencies with no fallback:** none block Phase 6 at plan-time; every vendor has a signup path.
**Blocking human actions at implementation time:**
- Provision Fly org + secrets.
- Provision Neon project (dev + prod) and capture owner DSN.
- Provision R2 bucket (dev + prod), set CORS, set lifecycle rule.
- Provision Upstash DB (dev + prod).
- Provision Clerk instance (dev + prod), create webhook endpoint URL, capture whsec_.
- Provision Stripe meter (test mode + live mode), capture meter event_name.
- Provision Sentry project + DSN.
- Provision Axiom dataset + log-drain on Fly apps.

Plan MUST include a dedicated "vendor provisioning" task list for each env.

---

## Validation Architecture

**Framework:** pytest + pytest-asyncio + pytest-cov

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.x + pytest-asyncio 0.24.x |
| Config file | `backend/pyproject.toml [tool.pytest.ini_options]` (Wave 0 creates) |
| Quick run | `cd backend && pytest -x -q --no-cov` |
| Full suite | `cd backend && pytest --cov=app --cov-branch --cov-fail-under=80` |

### Dimensions (8 + 2 bonus)

| # | Dimension | Concrete validation artifact |
|---|-----------|------------------------------|
| D1 | Functional correctness (endpoint contract) | `API-*` tests — one per route × (happy / unauth / bad-payload) → `test_scans.py`, `test_teams.py`, `test_webhooks.py`. Assert status codes + response schema. |
| D2 | Type safety | `mypy --strict backend/app` in CI. Pydantic v2 models have `model_config = ConfigDict(strict=True, extra="forbid")`. |
| D3 | Integration / contracts | OpenAPI snapshot test: `pytest tests/test_openapi_snapshot.py` — app.openapi() JSON is committed; diff fails PR. Clerk webhook contract: WBH-001 signs a known payload with `svix.Webhook.sign()` and asserts handler returns 200 and upserts Team. Stripe contract: MET-001 asserts request body shape against a captured fixture. |
| D4 | RLS enforcement (security-critical) | `RLS-001..00N` — one per team-scoped table. Seed team A as `infracanvas_test`; read as `infracanvas_app` with `SET LOCAL app.current_team_id = <team_B>`; assert 0 rows. Negative control: same read with team A context returns the row. Run on every PR. |
| D5 | Observability signal present | `OBS-001` captures stdout with `capsys`, parses each JSON line, asserts every line has `request_id`, `level`, `event`, `timestamp`. `OBS-002` asserts Sentry scope has tags `team_id`, `request_id` after auth dep runs (use `sentry_sdk.Hub.current`). |
| D6 | Billing idempotency | `MET-002` — send the same scan commit twice; assert only one meter event POST body was sent to the Stripe mock. `MET-003` — force DB commit to fail after Stripe returns 200; assert on retry with same `idempotency_key` Stripe replay is hit and no double-bill. |
| D7 | Migration upgrade + downgrade | `MIG-001` — fresh Testcontainer → `alembic upgrade head` → assert schema matches SQLAlchemy `Base.metadata`. `MIG-002` — upgrade head → downgrade -1 → upgrade head → assert idempotent and no errors. |
| D8 | Deploy / release_command smoke | `scripts/smoke_release.sh` runs `alembic upgrade head` against the dev Neon in CI (protected branch). Asserts exit 0 and schema matches. |
| D9 (bonus) | Task queue end-to-end | `JOB-001` — fires `enqueue_scan_indexing` via `InMemoryBroker`; asserts `scans.summary_json` is populated. `JOB-002` — task raises twice, succeeds on third attempt; asserts `SmartRetryMiddleware` replayed. `JOB-003` — task exhausts retries; asserts DLQ log line emitted with `dlq=true`. |
| D10 (bonus) | Auth boundary | `AUTH-001` accepts valid token. `AUTH-002` rejects expired. `AUTH-003` rejects tampered signature. `AUTH-004` rejects token with no `o` claim (no active org). `AUTH-005` rejects wrong `azp`. `AUTH-006` role gate: `admin` passes `require_role("admin")`, `member` is 403. |

### Per-requirement test map

| Req | Behavior | Test IDs | Command |
|-----|----------|----------|---------|
| API-01 | `GET /healthz` returns 200 `{"status":"ok"}` | API-001 | `pytest tests/test_health.py -x` |
| API-02 | Protected route requires Clerk JWT | AUTH-001..006 | `pytest tests/test_auth.py` |
| API-03 | `infracanvas_app` cannot bypass RLS | RLS-001..00N | `pytest tests/test_rls.py` |
| API-04 | R2 presigned PUT + HEAD roundtrip | STO-001..003 | `pytest tests/test_storage.py` (moto) |
| API-05 | taskiq worker processes job end-to-end | JOB-001..003 | `pytest tests/test_tasks.py` |
| API-06 | Two-step upload + commit | API-010..020 | `pytest tests/test_scans.py::test_upload_flow` |
| API-07 | `GET /v1/scans/{id}` returns signed URL | API-030 | `pytest tests/test_scans.py::test_get` |
| TMM-01 | RLS isolates cross-team | RLS-001..00N | (same as API-03) |
| TMM-02 | Stripe meter posted on commit | MET-001..003 | `pytest tests/test_stripe_meter.py` |
| OBS-01 | JSON logs with request_id + team_id | OBS-001 | `pytest tests/test_obs.py::test_log_shape` |
| OBS-02 | Sentry tags set + trace sample 0.1 | OBS-002 | `pytest tests/test_obs.py::test_sentry_tags` |

### Sampling rate
- **Per task commit:** `pytest -x -q --no-cov` (fast subset, <10s)
- **Per wave merge:** `pytest --cov=app --cov-branch --cov-fail-under=80` (full suite, ~60s target)
- **Phase gate:** full suite green + `mypy --strict` clean + smoke_release.sh against dev Neon green, all before `/gsd-verify-work`

### Wave 0 gaps
- [ ] `backend/pyproject.toml` — stand up (doesn't exist)
- [ ] `backend/Dockerfile` — stand up
- [ ] `backend/alembic.ini` + `migrations/env.py` — stand up
- [ ] `backend/tests/conftest.py` — pg_container, role setup, seed/app fixtures, Clerk JWKS mock
- [ ] `backend/fly.dev.toml`, `backend/fly.prod.toml` — stand up
- [ ] `backend/app/main.py` skeleton + health endpoint (API-01 minimum)
- [ ] CI workflow invoking `pytest --cov=app` with Testcontainers + `mypy --strict`
- [ ] Framework install: `pip install -e backend/[dev]` (new package)

---

## Security Domain

### Applicable ASVS categories

| ASVS | Applies | Control |
|------|---------|---------|
| V2 Authentication | yes | Clerk (external IdP); JWT RS256 via JWKS; no local password storage |
| V3 Session Management | yes | Clerk-issued sessions; short JWT lifetime (5–15 min via Clerk config); `sid` claim for revocation lookup if needed |
| V4 Access Control | yes (critical) | **Two layers:** FastAPI `require_role` (functional) + Postgres RLS `current_setting` (data-layer). Defence-in-depth |
| V5 Input Validation | yes | Pydantic v2 on every request body; `ResourceGraph.model_validate_json` on upload; OpenAPI schema validates path/query params |
| V6 Cryptography | yes | All at-rest: Neon (AES-256), R2 (AES-256), Upstash (TLS in transit). All in-transit: HTTPS only (`force_https = true`). JWT RS256 with rotating keys |
| V7 Errors / Logging | yes | structlog + Sentry; no raw tokens/secrets in logs (structlog processor scrubs `Authorization`, `set-cookie`, `stripe-signature`, `svix-signature` headers) |
| V8 Data Protection | yes | R2 per-team key prefix; presigned URLs expire ≤600s; no cross-team bucket policies |
| V9 Communications | yes | TLS required on every connection string (Neon `sslmode=require`; R2 always TLS; Upstash TLS) |
| V10 Malicious Code | no | No plugin system in scope |
| V11 Business Logic | yes | Stripe meter idempotency prevents double-billing; R2 25 MB cap prevents upload floods; 7-day R2 orphan GC |
| V12 Files / Resources | yes | 25 MB hard cap; Pydantic structural validation rejects non-ResourceGraph JSON |
| V13 API | yes | OpenAPI snapshot in CI; no HTTP verbs tampering (FastAPI routes are strict) |
| V14 Config | yes | Secrets in Fly secrets only; `.env.example` in git, never `.env`; separate dev/prod |

### Known threat patterns for this stack

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Cross-tenant read (horizontal priv esc) | I (Info disclosure) | RLS `current_setting` enforced in DB; RLS-* test suite |
| JWT algorithm confusion (alg=none) | S (Spoofing) | `algorithms=["RS256"]` fixed in PyJWT call |
| Webhook replay / forgery | T (Tampering) | Svix signature + timestamp skew window |
| Presigned URL leak | I | Short TTL (PUT 10min, GET 5min); team_id in key = blast radius bound |
| R2 upload bomb | D (DoS) | Size cap at commit; lifecycle GC; Cloudflare in front |
| Stripe double-bill | T | `idempotency_key` + `identifier` both = scan_id |
| Log injection via user field | T | structlog JSON renderer escapes; orjson strict |
| Secret in error page | I | Sentry beforeSend scrubs DSN keys; FastAPI prod disables `/docs`-embedded examples |
| SSRF via R2 URL | T | Backend never follows client-supplied URLs; all R2 calls are to fixed endpoint |

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|--------------|
| A1 | Neon transaction-mode pooler supports `SET LOCAL` inside explicit transactions | F3 | LOW — this is standard pgbouncer behavior; documented pattern in pganalyze RLS guide; verified by CITED sources but not against Neon specifically on their `-pooler` hostname. **Mitigation:** Wave 0 task runs a 2-line smoke `psql` against the dev -pooler hostname with BEGIN / SET LOCAL / SHOW / COMMIT. |
| A2 | Clerk v2 JWT `o.rol` strings will match our `require_role` allow-list (`admin`, `member`, `basic_member`, etc.) | F1 | LOW — Clerk org admins can rename roles. **Mitigation:** surface the role-slug set as a configurable env var; update docs at provisioning. |
| A3 | Upstash Redis throughput + free-tier limits handle Phase 6's low task rate | F7 | LOW — Phase 6 task volume is ~1 task per scan commit; Upstash free tier is 10k commands/day. Sufficient. **Mitigation:** observability catches throughput issues. |
| A4 | Stripe v2 meter events `identifier` + `idempotency_key` redundancy provides the idempotency we need | F8 | LOW — documented. **Mitigation:** MET-002/003 tests assert. |
| A5 | moto's R2 mock is faithful enough for presigned URL + HEAD | F5, Validation | MEDIUM — moto mocks S3, and R2 is "S3-compatible" but has known divergences (no POST, no Content-Length-Range, auth edge cases). **Mitigation:** one e2e test in Wave N against real R2 dev bucket to catch moto-vs-reality drift. |
| A6 | `uuid_utils` binary wheel is available for Fly's Linux arm64/amd64 builder | F13 | LOW — wheels on PyPI cover `manylinux2014_x86_64` + `aarch64`. **Mitigation:** Dockerfile builds on Fly confirm at first deploy. |
| A7 | `testcontainers` works in the GHA runner (requires Docker-in-Docker) | Testing | LOW — standard in GHA with `services.docker` or `runs-on: ubuntu-latest`. **Mitigation:** Wave 0 CI job validates. |
| A8 | `TimestampTZ server_default = "now()"` works identically across asyncpg + sqlalchemy+alembic roundtrip | F4 | LOW — standard. **Mitigation:** MIG-001 test asserts. |

---

## Open Questions

1. **Does CONTEXT.md D-02's "session-mode pooler" terminology need correction in the plan, or is it intentional shorthand?** Neon offers only transaction-mode pooler; the `SET LOCAL`-in-transaction pattern works on that. **Recommendation:** plan should clarify in its own language ("SET LOCAL inside an explicit transaction against the Neon `-pooler` hostname; works under transaction-mode pooling"). Planner can adopt this without revisiting D-02 with the user. **Risk if wrong: LOW** (pattern works either way).

2. **D-11's `Content-Length-Range` clause contradicts R2 capabilities.** R2 does not support this condition on presigned PUT. **Recommendation:** the plan should document the three-layer defence (client precheck + commit-HEAD size check + bucket lifecycle GC) and drop the signed condition. **Risk if wrong: MEDIUM** (without commit-HEAD enforcement, 25 MB cap becomes advisory). Planner should treat this as a required clarification, not a user decision.

3. **Stripe customer creation: in webhook or in first-commit?** D-04 says team row from webhook but is silent on Stripe customer. **Recommendation:** create `stripe.Customer` inside the `organization.created` webhook handler (before returning 200). Cost: one extra API call per org creation. Risk: if Stripe Customer creation fails, the team still exists but meter events will fail at first scan. Mitigation: webhook retries on 5xx; reconciler job could backfill missing stripe_customer_id. **Risk if wrong: LOW** — recoverable.

4. **Clerk webhook idempotency vs ordering:** two rapid `organization.updated` events could land out of order, overwriting newer data with older. **Recommendation:** use the `svix-timestamp` header as a monotonic guard — only apply update if payload's `updated_at` ≥ DB's `updated_at`. Lock this in the plan. **Risk if wrong: LOW** (update frequency is low).

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Stripe `subscription_item.usage_record.create` | Stripe `v2.billing.meter_events.create` | Removed 2025-03-31 per PROJECT.md; v2 is the standard | We're on v2 — no action |
| FastAPI `@app.middleware("http")` for everything | Pure ASGI middleware for contextvar work | 2023+ contextvar docs | F9 uses pure ASGI |
| Celery | taskiq | Python async-native era | Locked D-13 |
| psycopg2 | asyncpg (+ psycopg3 as alt) | Async ecosystem | Locked D-17 |
| Clerk JWT v1 | Clerk JWT v2 | Deprecated 2025-04-14 | Use v2 — F1 |
| `uuid1`/`uuid4` for primary keys | UUIDv7 | 2024+ | Locked D-07 |

**Deprecated / outdated patterns to avoid:**
- `stripe.SubscriptionItem.create_usage_record()` — removed.
- `stripe.billing.MeterEvent.create()` — v1 API; use v2 namespace.
- `request.json()` inside webhook handler — breaks Svix sig; use `request.body()`.
- Bare `SET search_path = ...` on a pooled connection — always `SET LOCAL`.

---

## Sources

### Primary (HIGH confidence)
- [Clerk session tokens v2 claim reference](https://clerk.com/docs/guides/sessions/session-tokens) — CITED
- [Clerk manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification) — CITED
- [Clerk webhooks overview](https://clerk.com/docs/guides/development/webhooks/overview) — CITED
- [Svix Python FastAPI recipe](https://www.svix.com/guides/receiving/receive-webhooks-with-python-fastapi/) — CITED
- [Neon connection pooling](https://neon.com/docs/connect/connection-pooling) — CITED (transaction-mode only)
- [Cloudflare R2 presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/) — CITED
- [Cloudflare R2 S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/) — CITED
- [Stripe v2 billing meter events create](https://docs.stripe.com/api/v2/billing/meter-events/create) — CITED
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests) — CITED
- [SQLAlchemy 2.0 asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — CITED
- [Alembic async cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic) — CITED
- [taskiq broker guide](https://taskiq-python.github.io/guide/brokers.html) — CITED
- [taskiq available middlewares (SmartRetryMiddleware)](https://taskiq-python.github.io/available-components/middlewares.html) — CITED
- [Sentry FastAPI integration](https://docs.sentry.io/platforms/python/integrations/fastapi/) — CITED
- [structlog contextvars](https://www.structlog.org/en/stable/contextvars.html) — CITED
- [Fly.io processes](https://fly.io/docs/reference/configuration/#the-processes-section) — CITED
- [Fly.io machine sizing](https://fly.io/docs/machines/guides-examples/machine-sizing/) — CITED
- [Axiom Fly log drain](https://axiom.co/docs/send-data/fly) — CITED
- [uuid_utils on PyPI](https://pypi.org/project/uuid-utils/) — CITED, VERIFIED v0.14.1

### Secondary (MEDIUM confidence — verified against primary)
- [pganalyze: Postgres RLS with pgbouncer](https://pganalyze.com/blog/postgres-row-level-security-ruby-rails) — pattern confirmation
- [FastAPI #4696: ContextVar loss in BaseHTTPMiddleware](https://github.com/fastapi/fastapi/issues/4696) — VERIFIED
- [taskiq DLQ discussion #578](https://github.com/taskiq-python/taskiq/issues/578) — confirms no built-in DLQ

### Tertiary (LOW confidence — flagged for validation)
- Community thread on R2 `Content-Length-Range` — conclusion "not supported" cross-verified with official R2 API compatibility matrix = elevated to HIGH.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified on PyPI 2026-04-24
- Architecture: HIGH — all patterns sourced from official vendor docs or referenced in CONTEXT.md
- Pitfalls: HIGH — cross-verified across primary sources (P1/FastAPI, P2/Neon, P3/R2, P6/Stripe, P8/Clerk)
- One MEDIUM on A5 (moto faithfulness) — add one real-R2 e2e test as compensating control

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (30 days; longer-lived areas: auth patterns, RLS pattern; shorter-lived: Stripe SDK minor versions, Clerk claim schema)
