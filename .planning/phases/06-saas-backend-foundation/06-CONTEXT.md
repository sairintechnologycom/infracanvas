# Phase 6: SaaS Backend Foundation - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the team-aware FastAPI backend that the rest of v1.1 SaaS work (Phase 7 dashboard, Phase 7.5 GitHub connector, Phase 8 webhooks, Phase 9 CostLens, Phase 13 billing) depends on. Scope is the foundation — auth, storage, queue, billing plumbing, observability — not user-facing surfaces.

**In scope (API-01..07, TMM-01..02, OBS-01..02):**
- FastAPI app scaffold with health endpoint, deployable
- Clerk auth middleware validating JWTs on protected routes
- Neon Postgres via session-mode pooler under a dedicated `infracanvas_app` role with NO BYPASSRLS
- R2 object storage client + bucket layout for scan artifacts
- taskiq async queue with a worker process that runs a real post-upload job end-to-end
- Scan upload + retrieval endpoints (presigned two-step)
- Team model backed by Clerk Organizations, mirrored locally, with RLS-enforced per-team isolation
- Stripe Billing Meters posting one usage event per successful scan upload
- Structured logs + request-ID propagation + error tracking + trace sampling

**Out of scope (belongs in later phases):**
- Dashboard UI → Phase 7 (DSH-02..06)
- Scan list/compare UI → Phase 7 (HST-01..03)
- Share links → Phase 7 (SHR-01..02)
- GitHub OAuth / repo browser → Phase 7.5
- Push webhooks, auto-scan worker, Slack alerts → Phase 8 (WBH-01..03)
- CostLens allocation logic → Phase 9
- FlowMap 3b / DC Agent endpoints → Phase 10+
- Team-tier Stripe product + feature gating → Phase 13 (TIR-01..02)

</domain>

<decisions>
## Implementation Decisions

### Team identity + RLS (TMM-01, TMM-02 prereqs)
- **D-01:** Teams = Clerk Organizations. A local `teams` table mirrors each org, keyed by `clerk_org_id`, holding local metadata only (`stripe_customer_id`, `created_at`, display/billing fields). Clerk is the source of truth for membership and roles (owner/admin/member/viewer). Rationale: no duplicate invite flow, TMM-01 roles already supplied via Clerk JWT — solo-founder ops minimization.
- **D-02:** `team_id` reaches Postgres via `SET LOCAL app.current_team_id = $1` on every authenticated request inside an opened transaction. RLS policies use `current_setting('app.current_team_id', true)::uuid = team_id`. This is the Neon-documented RLS pattern under a session-mode pooler and fits the `infracanvas_app` no-BYPASSRLS role cleanly.
- **D-03:** Role enforcement lives in a FastAPI dependency (`require_role('admin')` style) that reads the role claim from the Clerk JWT's active-org membership. RLS policies stay team-scoped (no role dimension in policies) — simpler policy surface, clearer "can see row" vs "can mutate row" separation.
- **D-04:** Team rows are created via a Clerk webhook handler on `organization.created`, which upserts a `teams` row. The webhook endpoint verifies Clerk signatures (Svix). No lazy-upsert on first request — Clerk webhook delivery is reliable enough; Phase 6 does not add a self-heal fallback.
- **D-05:** TMM-01 verification = integration test. Seed a row into team A (via a fixture-only bypass role), open a connection as `infracanvas_app` with `app.current_team_id` set to team B, SELECT the scan — must return 0 rows. Same test asserts the team-A context DOES see the row. One concrete test per table that carries team-scoped data.

### Scan ingest pipeline (API-06, API-07, TMM-02)
- **D-06:** Upload is two-step. `POST /v1/scans` returns `{scan_id, presigned_put_url, expires_at}`; client PUTs the JSON directly to R2; client calls `POST /v1/scans/{id}/commit` with the sha256 it computed locally. Commit handler HEADs the R2 object, verifies `Content-Length` ≤ 25 MB and ETag/sha256, validates the JSON against the `ResourceGraph` Pydantic model (cheap — it's already a structured graph), flips `scans.status = 'ready'`, fires the Stripe meter event. Keeps FastAPI off the byte path and matches Cloudflare R2 / Fly bandwidth best practice.
- **D-07:** R2 object key = `teams/{team_id}/scans/{scan_id}.json`. `scan_id` is a UUIDv7 (lexical order ≈ chronological). Rationale: the key prefix matches the RLS blast-radius boundary — any bucket mis-config cannot cross-contaminate teams; mass-ops per team is trivial; no content-addressed dedupe complications.
- **D-08:** Stripe Billing Meter fires exactly once per successful commit: event name `infracanvas.scan`, value=1, `idempotency_key=scan_id`. Scan-count is the pricing unit downstream (Pro $79 / Team $299 tiers key off scan counts). Idempotency_key makes commit-retry safe. Per-resource / per-MB metering is premature for Phase 6.
- **D-09:** Sync vs async split at commit:
  - **Sync (blocks the response):** R2 HEAD → ContentLength + sha256 check → Pydantic validate → `scans` row insert → Stripe meter event. All four must succeed before returning 200. If meter post fails, roll back the DB commit and return 5xx — billing consistency is load-bearing.
  - **Async (taskiq):** `enqueue_scan_indexing(scan_id)` writes denormalized summary counts (critical/high finding counts, resource count, score) onto the `scans` row so list views don't re-parse the JSON. This is real work — it also fulfills Phase 6 success criterion #5 ("taskiq worker processes an enqueued job end-to-end") with a job that has actual production value, not a hello-world smoke job.
- **D-10:** Retrieval (API-07) = `GET /v1/scans/{id}` returns metadata + a presigned GET URL with a ~300s TTL. Dashboard / CLI fetches the JSON blob directly from R2. RLS on the metadata query ensures cross-team GETs return 404, not 403 (don't leak existence).
- **D-11:** Size ceiling = 25 MB hard. Presigned PUT carries `Content-Length-Range` condition 1..25MB. Commit double-checks R2 `ContentLength`. Over-limit → reject commit, return 413; R2 bucket lifecycle rule garbage-collects unreferenced objects (≥7 days without a matching `scans` row) — configured as part of Phase 6 infrastructure.

### Queue + hosting topology (API-01, API-05)
- **D-12:** Hosting = Fly.io. `infracanvas-api-dev` + `infracanvas-api-prod` Fly apps, each with a separate `[processes] worker` block so the taskiq worker runs as its own Machine (can scale independently of the HTTP frontend). Region co-located with Neon. Rationale: Fly's process model maps cleanly to API+worker split; WireGuard available for future private Neon networking; pricing stays inside the $10–104/mo ceiling.
- **D-13:** Broker = Upstash Redis via `taskiq-redis`. Result backend = same Redis. Already within PROJECT.md's budget-acceptable vendor list; serverless (no idle cost); handles Phase 8 webhook load without rework. One Upstash DB per env (dev + prod).
- **D-14:** Env topology = **two full envs** — dev + prod. Separate Neon projects (each with their own `infracanvas_app` role + migrations history), separate R2 buckets (`infracanvas-scans-dev`, `infracanvas-scans-prod`), separate Clerk instances (dev/prod keys), separate Upstash Redis DBs, **Stripe test mode on dev, live mode on prod** (critical — prevents dev testing from polluting the live Billing Meter). Neon-branch-per-PR preview envs deferred until Phase 7 has frontend PR velocity to justify the GHA wiring.
- **D-15:** Migrations = Alembic. `alembic upgrade head` runs as the Fly `release_command` so every deploy migrates before switching traffic. `alembic revision --autogenerate` for schema changes; RLS policies + GUCs go in hand-written SQL migrations (autogenerate can't express them).
- **D-16:** Repo layout = new top-level `backend/` directory alongside `cli/` and `viewer/`, with its own `pyproject.toml`. Keeps CLI's `pip install infracanvas` footprint free of FastAPI / SQLAlchemy / boto3 bloat while sharing the monorepo (data-model cross-references to `cli/infracanvas/graph/models.py` — the `ResourceGraph` schema — stay possible).
- **D-17:** DB driver + ORM = `asyncpg` + SQLAlchemy 2.0 async. Raw SQL for RLS-policy migrations; ORM for CRUD. asyncpg supports `SET LOCAL` without surprises (SQLAlchemy wraps it via `connection.execute(text('SET LOCAL ...'))` inside a session's `begin()`).

### Observability (OBS-01, OBS-02)
- **D-18:** Error tracking = Sentry. `sentry-sdk[fastapi]` auto-instruments FastAPI + asyncpg + taskiq. Tags every event with `request_id`, `team_id`, `user_id`, `clerk_org_id` via `sentry_sdk.set_tag` from the auth dependency. Free tier (5k errors/mo) covers pre-revenue.
- **D-19:** Structured logs = `structlog` → JSON to stdout → Fly log drain → Axiom. `structlog` configured with a JSON renderer, bound context (`request_id`, `team_id`, `user_id`) via contextvars. Fly ships stdout to Axiom via the `fly logs -j` / log-shipper integration. Axiom free tier (0.5 TB ingest/mo) is plenty. Zero in-app SDK overhead; sink is swappable via one env var.
- **D-20:** Tracing = Sentry Performance with `traces_sample_rate=0.1`. Piggybacks on the Sentry SDK we already ship for errors; auto-instruments the FastAPI → asyncpg → taskiq call chain. OTLP → Grafana Cloud migration available later if we outgrow Sentry's tracing.
- **D-21:** Request-ID strategy = custom ASGI middleware generates `X-Request-ID` (UUIDv7) if the incoming request doesn't carry one, binds it to a structlog contextvar, echoes it in the response header. taskiq jobs accept `request_id` in task metadata (callers pass their current request_id when enqueuing) and re-bind it in the worker's log context — so an upload commit + its background `enqueue_scan_indexing` job share one trace ID in both Sentry and Axiom.

### Claude's Discretion
- Exact API versioning prefix shape (`/v1` vs `/api/v1` vs header-based) — pick whichever Next.js 15 consumes cleanly.
- Whether to use Clerk's `ClerkClient` Python SDK or validate JWTs directly via `PyJWT` + JWKS — whichever has simpler webhook signature verification + JWT validation ergonomics.
- Exact taskiq Redis key prefixing, result expiry TTL, retry policy (sensible defaults: 3 retries with exponential backoff, DLQ via Redis list).
- SQLAlchemy model-to-migration autogeneration vs handwritten-only — Claude picks based on what Alembic produces cleanly for each change.
- Whether `X-Request-ID` generation middleware runs before or after Clerk auth middleware — likely before, so auth-failure logs still carry a request_id.
- Exact UUIDv7 library choice (`uuid_utils` vs `uuid6` vs native 3.13 — we're on 3.12, so a backport library).
- Fly Machine sizes for API + worker processes (smallest that doesn't OOM — likely `shared-cpu-1x 256mb` to start).
- Axiom dataset naming convention (one per env vs one shared with env tag).
- Sentry project split (one project with environment tag vs separate dev/prod projects).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` § Phase 6 — goal, 5 success criteria, Depends on: Phase 4 (flagged: Phase 4 is not yet executed; Phase 6 planning may need to treat Phase 4 wiring changes as parallel rather than prerequisite)
- `.planning/REQUIREMENTS.md` API-01..07 — FastAPI scaffold + auth + DB + R2 + taskiq + upload/retrieval endpoints
- `.planning/REQUIREMENTS.md` TMM-01..02 — team roles + RLS-enforced isolation + Stripe Billing Meters
- `.planning/REQUIREMENTS.md` OBS-01..02 — structured logging + error tracking with request ID + team context
- `.planning/PROJECT.md` § Key Decisions — Neon session-mode pooler + `infracanvas_app` role + no BYPASSRLS; taskiq over arq; Stripe Billing Meters only (legacy `create_usage_record()` removed 2025-03-31); Next.js 15 for Phase 7 consumer
- `.planning/PROJECT.md` § Constraints — solo founder (minimize ops surface), $10–104/mo budget, FastAPI on Railway/Fly (locked to Fly per D-12), no cloud credentials stored

### Vendor choices (decided — reference docs to read during planning)
- Clerk Organizations: https://clerk.com/docs/organizations/overview (roles, JWT claims, webhooks)
- Clerk Webhooks: https://clerk.com/docs/webhooks/overview (Svix signature verification)
- Neon RLS under session-mode pooler: https://neon.tech/docs/guides/row-level-security
- Cloudflare R2 presigned URLs: https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- taskiq + Redis broker: https://taskiq-python.github.io/guide/brokers.html
- Stripe Billing Meters: https://docs.stripe.com/billing/subscriptions/usage-based/recording-usage
- Alembic async: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- SQLAlchemy 2.0 async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Sentry FastAPI integration: https://docs.sentry.io/platforms/python/integrations/fastapi/
- structlog + JSON: https://www.structlog.org/en/stable/logging-best-practices.html
- Axiom log ingestion from Fly: https://axiom.co/docs/send-data/fly
- Fly.io process groups: https://fly.io/docs/reference/configuration/#the-processes-section

### Prior-phase constraints (carry forward)
- `.planning/phases/04-e2e-wiring-hardening/04-CONTEXT.md` D-01..D-04 — CLI exit code + stderr contract (0/1/2) — any backend-consumed CLI output must honor it
- `.planning/phases/04-e2e-wiring-hardening/04-CONTEXT.md` D-14..D-17 — Python pytest coverage gate (line + branch ≥80% per module) — backend should adopt a parallel coverage posture (scoped to `backend/`)
- `.planning/phases/05-viewer-extraction/05-CONTEXT.md` D-02 — monorepo bet (workspaces/file: link); adds `backend/` as a third top-level package alongside `cli/` and `viewer/`
- `.planning/phases/05.1-parser-realism-cli-ux/05.1-CONTEXT.md` — CLI UX decisions that may shape how CLI interacts with the backend later (not a Phase 6 dependency, but informs Phase 7.5 / 8 connector design)

### Cross-package integration points (read-only from backend perspective)
- `cli/infracanvas/graph/models.py` — `ResourceGraph` Pydantic v2 schema that uploaded scan JSONs conform to (backend re-validates on commit per D-09)
- `cli/pyproject.toml` — Python version floor (3.12+); backend should match for single-version ops footprint
- `cli/infracanvas/main.py` — reference for Rich/stderr error routing patterns (not directly used, but informs CLI-facing error ergonomics when Phase 7.5 wires CLI-to-backend uploads)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/infracanvas/graph/models.py` defines `ResourceGraph`, `ResourceNode`, `Finding`, `GraphSummary` as Pydantic v2 models — the backend's upload-validator re-uses these (either by importing `infracanvas.graph.models` cross-package or by pinning a published schema snapshot). Importing wins for Phase 6 — one source of truth; solo-founder ergonomics.
- Python 3.12 toolchain already standardized (Ruff 100-col, MyPy strict, StrEnum, Pydantic v2) — `backend/pyproject.toml` mirrors the style config, just swaps the dependency set.
- The monorepo/workspace pattern is established by Phase 5's `@infracanvas/viewer` — adding `backend/` as a third top-level package is a natural extension, not a new invention.
- Rich-style error formatting patterns from `cli/infracanvas/main.py` translate to structlog-rendered errors in the backend (same semantic categories: user error vs system error vs validation error).

### Established Patterns
- Python: Ruff rules `E F I N W UP`, line 100, MyPy strict mode, snake_case modules.
- Test IDs in docstrings (`B-001`, `E-002` from CLI) — adopt parallel `API-*`, `RLS-*`, `JOB-*` IDs in backend tests.
- Pydantic v2 for all request/response bodies (already the CLI norm).
- Per-module coverage threshold (Phase 4 D-15) — replicate for `backend/` with separate `pyproject.toml` [tool.coverage] block.

### Integration Points
- **Scan JSON schema = `ResourceGraph` Pydantic model** (D-09 validation step). Backend imports `infracanvas.graph.models` or pins the schema via JSON-Schema export from the CLI. Choose at planning — both are viable; importing keeps drift to zero.
- **Fly release_command** = `alembic upgrade head` (D-15). Runs before traffic cutover so every deploy is migration-safe.
- **Clerk webhook endpoint** = `POST /v1/webhooks/clerk` (D-04). Signature-verified via Svix; upserts teams on `organization.created`; returns 200 fast so Clerk doesn't retry.
- **Stripe webhook endpoint** = not in Phase 6 scope (subscription events belong to Phase 13 / TIR-01..02). Phase 6 only outbound-sends meter events.
- **R2 bucket lifecycle rule** for orphaned uploads (D-11) is infrastructure config, not code — documented in the Phase 6 plan but provisioned via `wrangler` or R2 dashboard.

</code_context>

<specifics>
## Specific Ideas

- **"Billing consistency is load-bearing"** (D-09): if the Stripe meter event fails after the DB commit, the user was served but not billed. The sync boundary is drawn at commit success = meter success; both land together or neither does. No "best-effort meter" — it's transactional with the DB row.
- **"Key prefix matches the RLS blast-radius boundary"** (D-07): a single flat `scans/{sha256}` layout would let a mis-configured bucket policy expose every team's scans at once. `teams/{team_id}/...` caps any mistake to one team.
- **"Real worker job, not a smoke job"** (D-09): `enqueue_scan_indexing` writes denormalized summary counts to the `scans` row — useful for Phase 7's scan-list UI. Satisfies success criterion #5 with production value, not a hello-world test that gets deleted later.
- **"Two envs with Stripe test mode vs live mode"** (D-14): this is the specific failure mode to prevent. Dev testing on the live meter would bill us real money and pollute the prod customer's usage numbers.
- **Request ID shared across sync + async** (D-21): one scan upload's log trail spans the HTTP commit + the background indexing job. If something goes wrong in indexing, `request_id=<uuid>` in Axiom finds both log streams. Worth the small amount of metadata plumbing.

</specifics>

<deferred>
## Deferred Ideas

- **Neon-branch-per-PR preview envs** — deferred to Phase 7 when there's frontend PR velocity to justify the GHA wiring. Reviewed, not rejected.
- **Stripe subscription lifecycle (checkout sessions, customer portal, webhook handlers)** — belongs to Phase 13 / TIR-01..02. Phase 6 only plumbs the outbound meter event.
- **OTLP → Grafana Cloud / Honeycomb tracing** — reviewed, deferred. Sentry Performance covers Phase 6 needs; revisit when we outgrow it.
- **Logfire as single pane (errors + logs + traces)** — reviewed, deferred. Sentry is the safer boring pick right now; Logfire revisit when its ecosystem matures.
- **API rate limiting** — reviewed, deferred. Cloudflare in front of Fly handles bulk abuse; app-layer per-team throttling can be a Phase 8 concern once webhook-driven load is real.
- **WebAuthn / passkey login** — out of scope; Clerk handles auth methods.
- **GitHub OAuth / repo picker** — Phase 7.5.
- **Share-link token system (SHR-01..02)** — Phase 7.
- **Scan compare diff endpoint (HST-02)** — Phase 7.
- **Slack alert webhook on critical findings (WBH-03)** — Phase 8.
- **Content-addressed R2 dedup across teams** — rejected in D-07 in favor of team-prefixed layout; blast-radius bounding wins over dedup savings.
- **Per-resource or per-MB Stripe meter** — rejected in D-08; per-scan is the right pricing unit for Phase 6.
- **Lazy-upsert team row on first API request** — rejected in D-04; webhook alone is reliable enough; revisit only if we see dropped `organization.created` events.
- **RLS policies encoding role dimension** — rejected in D-03; role check stays in FastAPI dependency, policies stay team-scoped.
- **Inline multipart scan upload through FastAPI** — rejected in D-06; presigned two-step wins on bandwidth cost and ops simplicity.
- **In-process taskiq worker (no separate process)** — rejected in D-13; fails the "worker processes an enqueued job end-to-end" success criterion in spirit.
- **Railway** — reviewed (PROJECT.md offered it as an alternative); rejected in D-12 in favor of Fly for the process-model fit.
- **Atlas migrations** — reviewed, rejected in D-15 in favor of Alembic for ecosystem fit.
- **Psycopg3** — reviewed, rejected in D-17 in favor of asyncpg for performance + ecosystem.
- **API versioning via header instead of URL prefix** — left to Claude's discretion; default to URL prefix (`/v1`) unless planning surfaces a reason.

</deferred>

---

*Phase: 06-saas-backend-foundation*
*Context gathered: 2026-04-21*
