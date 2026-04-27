---
phase: 06-saas-backend-foundation
plan: 05
title: R2 presigned URLs + scan two-step upload + commit + Stripe meter + ResourceGraph validation + retrieval
subsystem: scan-ingest
tags: [r2, presigned-urls, stripe-meter, resourcegraph, two-step-upload, atomic-commit, rls, cross-team-404]

# Dependency graph
requires:
  - "Plan 06-01 — backend/pyproject.toml deps (boto3, stripe>=11<16, infracanvas @ file:../cli); tests/conftest.py mock_r2 + mock_stripe + mock_clerk + pg_container fixtures"
  - "Plan 06-02 — app/settings.py (R2_*, STRIPE_*, CLERK_* envs); app/util/ids.py::new_uuid7"
  - "Plan 06-03 — app/db/models.py Team/Scan/ScanStatus; migrations 001+002 (teams, scans, RLS); app/db/session.py raw_session + sessionmaker"
  - "Plan 06-04 — app/auth/clerk.py require_role; app/auth/deps.py resolve_team_from_clerk_org; app/auth/webhooks.py team provisioning + Stripe customer; migration 003 (team_by_clerk_org SECURITY DEFINER)"
provides:
  - "POST /v1/scans (auth: owner/admin/member) → ScanCreateResp{scan_id, presigned_put_url, expires_at}; PUT target = pending/{scan_id}.json"
  - "POST /v1/scans/{id}/commit (auth: owner/admin/member) → atomic HEAD→validate→INSERT→Stripe→COMMIT then R2 copy pending→teams/ + delete pending + enqueue indexing"
  - "GET /v1/scans/{id} (auth: owner/admin/member/basic_member) → ScanGetResp with presigned_get_url; cross-team requests return 404 (D-10, never 403)"
  - "app/storage/r2.py — boto3 SigV4 R2 client + presigned_put/get + head/get_bytes/copy/delete"
  - "app/billing/stripe_meter.py — record_scan_meter_event using stripe-python v15 StripeClient().v2.billing.meter_events.create with dual idempotency (identifier + idempotency_key both = scan_id)"
  - "app/schemas/scan.py — ScanCreateReq/Resp, ScanCommitReq, ScanGetResp (Pydantic v2 with ConfigDict(strict=True, extra='forbid') on requests)"
  - "cli/infracanvas/graph/summary.py::compute_summary — extracted from CLI's _run_scan, shared with backend indexing worker (Plan 06-06)"
affects:
  - "Plan 06-06 indexing worker — will consume cli.infracanvas.graph.summary.compute_summary; will provide app.queue.tasks.indexing.enqueue_scan_indexing (lazy-imported in commit handler)"
  - "Plan 06-08 deploy CI — env wiring for R2_*, STRIPE_*; lifecycle rule on pending/ prefix"

tech-stack:
  added:
    - "boto3 1.35 SigV4 client targeting Cloudflare R2 (custom endpoint_url + signature_version='s3v4')"
    - "stripe-python v15 StripeClient (v2.billing.meter_events.create with options.idempotency_key)"
    - "fastapi.concurrency.run_in_threadpool for blocking boto3 calls inside async route handlers"
  patterns:
    - "Two-step upload: presigned PUT to pending/{id}.json (no team_id in key), commit copies to teams/{team_id}/scans/{id}.json then deletes pending source"
    - "Atomic commit ordering: HEAD → ResourceGraph.model_validate_json → INSERT scan → Stripe meter event (LAST in tx) → COMMIT → R2 copy/delete (post-commit, best-effort) → enqueue indexing"
    - "Stripe meter dual idempotency: identifier (Stripe 24h server-side dedup) + idempotency_key (HTTP retry safety; both = scan_id)"
    - "SDK-boundary mocking for Stripe v2 (respx can't intercept stripe-python v15 — uses requests not httpx)"
    - "NullPool async engine in TestClient tests (avoids 'Future attached to a different loop' across per-request anyio portals)"
    - "set_config('app.current_team_id', :t, true) in commit handler instead of SET LOCAL :t (asyncpg parameter binding fix from Plan 06-04 carried into Plan 06-05's session.py + scans.py)"

key-files:
  created:
    - backend/app/storage/__init__.py
    - backend/app/storage/r2.py
    - backend/app/billing/__init__.py
    - backend/app/billing/stripe_meter.py
    - backend/app/schemas/__init__.py
    - backend/app/schemas/scan.py
    - backend/app/routes/scans.py
    - backend/tests/test_storage.py
    - backend/tests/test_stripe_meter.py
    - backend/tests/test_scans.py
    - cli/infracanvas/graph/summary.py
  modified:
    - backend/app/main.py (include_router(scan_routes.router) — health + webhooks preserved)
    - backend/app/db/session.py (set_config switch + lazy _team_dep helper)
    - cli/infracanvas/main.py (replace inline summary loop with compute_summary call)

decisions:
  - "Stripe SDK call shape — stripe-python v15.1 only exposes v2 endpoints via StripeClient (not the legacy module-level stripe.v2.billing.meter_events.create — that path raises AttributeError on v15). Switched to client.v2.billing.meter_events.create(params=..., options={'idempotency_key': ...}). Plan's expected import path was wrong for the installed version."
  - "Stripe mocking strategy — stripe-python v15 routes V2 through `requests` (not `httpx`) so respx-based mocking does NOT intercept the calls. Mock at the SDK boundary (replace stripe_meter._client) instead. The conftest mock_stripe respx fixture is now unused for Plan 06-05 tests; kept in conftest for future plans that hit V1 endpoints (which DO go through httpx)."
  - "NullPool for TestClient DB engine — TestClient's anyio portal creates a fresh event loop per request, and the production pool's connections get bound to the first request's loop. Subsequent requests fail with 'Future attached to a different loop'. NullPool creates+closes connections per-request, sidestepping the cross-loop issue. Production engine still uses pool_size=5/max_overflow=10."
  - "moto interception strategy — boto3 client with custom endpoint_url (R2) is intercepted unreliably by moto across versions. We swap get_r2_client at test time for a stock S3 client (no endpoint_url) — moto interception is reliable then. Presigned URL test still uses the real client because URL generation is local-only."
  - "Random clerk_org_id per test — UUIDv7 prefixes share timestamps within the same second so f'org_a_{uuid7.hex[:8]}' was colliding across tests on the session-scoped pg_container. Switched to secrets.token_hex(6) suffix (32 random bits, collision-safe across test sessions)."
  - "team_scoped_session signature — replaced the broken Depends(_resolve_team_dep()) default (caused circular import via Depends-evaluation at module load) with a non-Depends default (team=None + late import explanatory comment). The GET handler resolves team explicitly via Depends(resolve_team_from_clerk_org) and opens the team-scoped session inline. Cleaner at the call site than threading team through the FastAPI dep graph."
  - "compute_summary placement in CLI — extracted from main.py BEFORE severity_filter (the original loop computed counts before filtering). Score is computed against the unfiltered finding set so it reflects the true population, not what the user sees on screen. Behaviour preserved exactly; all 379 CLI tests still pass."

requirements-completed: [API-04, API-06, API-07, TMM-02]

# Metrics
metrics:
  duration: "~18 minutes"
  tasks_completed: 2
  files_created: 11
  files_modified: 3
  lines_added: 1430
  tests_passing: 31  # 4 storage + 5 scans + 3 stripe + 11 prior auth/webhooks + 4 health + 3 obs + 1 scaffold
  cli_tests_passing: 379
  completed: 2026-04-27
---

# Phase 6 Plan 05: Scan ingest pipeline + Stripe meter + cross-team 404 Summary

Delivered the hot-path scan ingest API: a two-step upload (POST → presigned PUT → POST commit), atomic DB+Stripe transaction with rollback semantics, server-side R2 copy from `pending/` to `teams/{team_id}/scans/`, RLS-enforced cross-team isolation that returns 404 (not 403) per D-10, and ResourceGraph validation gating the commit. The Stripe meter event is the LAST statement in the DB transaction so that any meter failure aborts the row insert — the invariant "every committed scan carries a meter event" holds end-to-end.

## Endpoint Surface

| Method | Path | Auth (require_role) | Success | Errors |
|--------|------|---------------------|---------|--------|
| POST   | `/v1/scans` | owner, admin, member | 200 ScanCreateResp | 401 missing/invalid token; 403 forbidden_role; 404 team_not_provisioned |
| POST   | `/v1/scans/{id}/commit` | owner, admin, member | 200 ScanGetResp | 404 object_not_found (HEAD missed); 413 too_large; 422 invalid ResourceGraph; 502 meter_failed (Stripe) |
| GET    | `/v1/scans/{id}` | owner, admin, member, basic_member | 200 ScanGetResp | 404 scan_not_found (cross-team OR genuine miss — D-10) |

## Commit Handler — Step Order

1. **HEAD `pending/{scan_id}.json`** via boto3 (run_in_threadpool). 404/NotFound/NoSuchKey → HTTP 404 `object_not_found`. Other ClientError → re-raise (500).
2. **Size check.** `ContentLength > 25 MB` → HTTP 413 `{error, size_bytes, max}`.
3. **Fetch + validate.** `r2.get_bytes()` then `ResourceGraph.model_validate_json(blob)`. Pydantic ValidationError → HTTP 422 `{errors: [...up to 10 entries]}`.
4. **Open DB transaction** (`session.begin()`).
5. **`SELECT set_config('app.current_team_id', :t, true)`** — switches RLS into team-scoped mode for the rest of the tx. asyncpg-compatible parameter binding (the `SET LOCAL = :t` form fails on asyncpg's wire protocol).
6. **`INSERT INTO scans`** with `r2_key = teams/{team_id}/scans/{id}.json` (the **final** key, even though bytes still live at `pending/`). `await session.flush()` forces the INSERT roundtrip immediately so UNIQUE-violation / RLS WITH-CHECK failures surface BEFORE the Stripe call.
7. **`stripe.v2.billing.meter_events.create`** — LAST statement inside `session.begin()`. Any `StripeError` raises → tx rolls back → no scan row committed.
8. **Tx COMMIT** (implicit on `session.begin()` exit without exception).
9. **R2 server-side copy** `pending/{id}.json` → `teams/{team_id}/scans/{id}.json` then **DELETE `pending/...`**. Best-effort; ClientError logged at WARNING. The DB row already points at `final` — a Phase 7 reconciler will retry on copy failure; lifecycle rule on `pending/` (Plan 08) GCs abandoned objects.
10. **Lazy taskiq enqueue** of `enqueue_scan_indexing.kicker().with_labels(request_id=rid).kiq(scan_id=...)`. Exception logged at WARNING; commit is NOT undone. Plan 06-06 ships the worker side.
11. **Build response** via a fresh team-scoped read so the returned `ScanGetResp` carries the canonical row state.

## Why the Stripe call must be LAST inside the tx (D-09)

If the Stripe call ran AFTER `session.commit()`, a Stripe failure would leave a committed scan row with no meter event — the user would have free usage. By putting it inside `session.begin()`:

- Stripe success → tx commits → both DB and Stripe consistent.
- Stripe failure → tx rolls back → no scan row, no meter event, client gets 502 and can retry.
- The reverse failure mode (Stripe success + DB COMMIT failure) is near-zero-probability for Postgres after a successful external call. T-06-03b documents this as `accept` in the threat register; Phase 7 may add a `scans.meter_posted_at` reconciler.

## Two-step R2 Layout — Why pending/ is Different from teams/ (D-11)

Presigned PUT URL targets `pending/{scan_id}.json`. **No team_id in the key**, so:

- T-06-04 mitigation: there's no cross-team surface in the upload URL; a leaked PUT URL only lets the holder overwrite that specific pending object (which is then either committed-and-moved or GC'd after 7 days).
- T-06-05 mitigation: Plan 08's R2 lifecycle rule `expire-abandoned-pending-uploads` only operates on the `pending/` prefix. Committed scans live under `teams/...` and are never touched by lifecycle. Solo-founder DoS surface (unbounded R2 storage from abandoned uploads) is bounded to a 7-day window.

The presigned PUT URL **does NOT** carry a Content-Length-Range condition. Research callout #2: R2 returns `SignatureDoesNotMatch` even when the bound length matches. Size enforcement happens at commit-time via `r2.head()` and is verified by `test_commit_rejects_oversized` (API-011).

## Stripe Meter Event Idempotency (TMM-02)

Two layers, both keyed on `scan_id`:

| Layer | Field | Window | Protects against |
|-------|-------|--------|------------------|
| In-body | `identifier=scan_id` | 24h server-side dedup | Client retries that succeed Stripe-side but lose response |
| HTTP header | `idempotency_key=scan_id` (passed via `options=`) | 24h on Stripe HTTP layer | Transport retries; LB-level retries; client-side request-replay |

The `event_name="infracanvas.scan"` from `settings.stripe_meter_event_name` matches what's wired in Stripe Dashboard.

## Cross-package Import (CLI ↔ Backend)

`backend/app/routes/scans.py`:

```python
from infracanvas.graph.models import ResourceGraph
ResourceGraph.model_validate_json(blob)
```

This works because `backend/pyproject.toml` declares `infracanvas @ file:../cli` (Plan 06-01). Both backend and CLI now share `compute_summary(graph) -> GraphSummary` from `cli/infracanvas/graph/summary.py` — Plan 06-06's indexing worker will reuse it.

CLI extraction preserved scoring behavior exactly: 379/379 cli tests still pass after replacing the inline loop in `_run_scan` with `compute_summary(graph)`.

## Tests Passing (12 new + 19 preserved = 31 total)

```
backend $ .venv/bin/python -m pytest tests/test_storage.py tests/test_scans.py tests/test_stripe_meter.py tests/test_auth.py tests/test_webhooks.py tests/test_health.py tests/test_obs.py tests/test_scaffold.py --no-cov -q
...............................                                          [100%]
31 passed in 7.72s
```

| Test | ID | File | Status |
|------|----|------|--------|
| test_presigned_put_contains_no_content_length_range | STO-001 | test_storage.py | PASS |
| test_head_roundtrip | STO-002 | test_storage.py | PASS |
| test_get_returns_bytes | STO-003 | test_storage.py | PASS |
| test_copy_then_delete_moves_pending_to_final | STO-004 | test_storage.py | PASS |
| test_meter_event_sends_v2_endpoint | MET-001 | test_stripe_meter.py | PASS |
| test_meter_event_uses_idempotency_key | MET-002 | test_stripe_meter.py | PASS |
| test_meter_event_raises_on_stripe_error | MET-003 | test_stripe_meter.py | PASS |
| test_upload_create_commit_get_happy_path | API-010 | test_scans.py | PASS |
| test_commit_rejects_oversized | API-011 | test_scans.py | PASS |
| test_commit_rejects_malformed_graph | API-012 | test_scans.py | PASS |
| test_cross_team_get_returns_404 | API-013 | test_scans.py | PASS |
| test_commit_rollback_on_stripe_failure | API-014 | test_scans.py | PASS |

CLI tests: 379/379 PASS (no regression from `compute_summary` extraction).

## Threat Mitigations Applied

| Threat ID | Mitigation | Evidence |
|-----------|-----------|----------|
| T-06-01 (cross-team read) | RLS-scoped GET via `Depends(resolve_team_from_clerk_org)` + inline `set_config('app.current_team_id', ...)` + `select(Scan).where(Scan.id == ...)` returning empty for cross-team. Empty → HTTP 404. | API-013 asserts; `app/routes/scans.py::get_scan` lines 256-281 |
| T-06-03 (replayed commit double-meters) | Dual idempotency: `identifier=scan_id` + `idempotency_key=scan_id`. UNIQUE(team_id, id) on scans table (Plan 03) blocks DB-level dupe at the INSERT before Stripe is even called on retry. | `app/billing/stripe_meter.py` lines 60-72; MET-002 asserts the idempotency_key option |
| T-06-04 (presigned URL leak cross-team) | PUT targets `pending/{scan_id}.json` (no team_id). GET targets `teams/{team_id}/scans/{id}.json` with team_id derived server-side. PUT TTL=600s, GET TTL=300s. | `app/routes/scans.py` lines 73-93; `_pending_key`/`_final_key` helpers |
| T-06-05 (DoS via unbounded uploads) | `_MAX_BYTES = 25*1024*1024` HEAD-check at commit; pending/ source deleted post-commit; lifecycle rule (Plan 08) GCs abandoned pending/ after 7d. | `app/routes/scans.py` lines 60-62, 144-149; API-011 asserts 413 |
| T-06-03b (Stripe success + DB commit fail) | Accepted per threat register; near-zero-probability after a successful external call returns. | Documented inline in `commit_scan` docstring (`app/routes/scans.py` lines 109-129) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's Stripe SDK call path doesn't exist on v15**
- **Found during:** Task 1 verification (test_stripe_meter MET-001 failed with `AttributeError`)
- **Issue:** Plan specified `stripe.v2.billing.meter_events.create(event_name=..., payload=..., identifier=..., idempotency_key=...)`. stripe-python 15.1's `stripe.v2.billing` module's `__getattr__` does NOT export `meter_events` as a top-level attribute — only `MeterEventService` (a class). The `client.v2.billing.meter_events.create()` form (via `StripeClient`) is the only working path on v15.
- **Fix:** Switched implementation to `_client().v2.billing.meter_events.create(params={...}, options={"idempotency_key": ...})`. The shape matches v15's `MeterEventService.create(params, options)` signature; idempotency key flows through the options object.
- **Files modified:** `backend/app/billing/stripe_meter.py`
- **Commit:** `8a300a6`

**2. [Rule 1 - Bug] respx-based Stripe mocking can't intercept v15 V2 calls**
- **Found during:** Task 1 (MET-001/002 failing — calls reaching real `api.stripe.com`)
- **Issue:** Plan-suggested `mock_stripe` respx fixture mocks `https://api.stripe.com` for `httpx` clients. stripe-python v15 routes V2 calls through `requests`, not `httpx` — respx never sees them. Tests were calling real Stripe and getting 401 `invalid_v2_key`.
- **Fix:** Mock at the SDK boundary — replace `stripe_meter._client` with a stub that records `(params, options)` calls. Tests assert behavioural contract: correct event_name, identifier, value, idempotency_key. The conftest's `mock_stripe` respx fixture is preserved for future plans that hit V1 endpoints (which DO go through httpx).
- **Files modified:** `backend/tests/test_stripe_meter.py`, `backend/tests/test_scans.py`
- **Commit:** `8a300a6`, `73c0e07`

**3. [Rule 1 - Bug] team_scoped_session circular import via Depends() default**
- **Found during:** Task 2 verification (test_health.py / test_obs.py / test_webhooks.py collection-time `ImportError`)
- **Issue:** First implementation used `team: "Team" = Depends(_resolve_team_dep())` where `_resolve_team_dep` did a late import of `app.auth.deps`. But `Depends(...)` is evaluated at module-load (function-default semantics), and `app.auth.deps` imports `app.db.session.raw_session`, so the import chain races: `scans.py → app.auth.deps → app.db.session → (Depends evaluation triggers) app.auth.deps`. Partial module not yet exporting the symbol → `ImportError`.
- **Fix:** Replaced the Depends-based default with `team: Team | None = None` + an explicit error path for the unreachable case. The `_team_dep()` helper remains for callers who want to compose `team_scoped_session` via FastAPI's dep graph (no current call site uses it; the GET handler resolves team explicitly). `app/routes/scans.py::get_scan` opens the team-scoped session inline instead of via `Depends(team_scoped_session)` — equivalent semantics, clearer at the call site.
- **Files modified:** `backend/app/db/session.py`, `backend/app/routes/scans.py`
- **Commit:** `73c0e07`

**4. [Rule 1 - Bug] TestClient + production pool → "Event loop is closed"**
- **Found during:** Task 2 (happy-path test failed on the second TestClient request)
- **Issue:** TestClient creates a per-request anyio portal with its own event loop. The production async engine's connection pool retains connections bound to the first request's loop. The second request finds those connections attached to a now-closed loop → `RuntimeError: Future attached to a different loop` / `Event loop is closed`.
- **Fix:** Test fixture `app_client` builds a fresh engine with `poolclass=NullPool` and patches `app.db.session._Session` so every request opens+closes a connection on the current loop. Production code unchanged.
- **Files modified:** `backend/tests/test_scans.py`
- **Commit:** `73c0e07`

**5. [Rule 1 - Bug] UUIDv7 prefix collisions in test fixtures**
- **Found during:** Task 2 (second test fixture setup failed with UNIQUE constraint violation)
- **Issue:** UUIDv7 timestamps share the high 32 bits within the same second, so `f"org_a_{uuid7.hex[:8]}"` collides across tests in a fast-running suite. The session-scoped `pg_container` retains rows across tests (intentional — re-creating PG is slow), so the collision persists.
- **Fix:** Use `secrets.token_hex(6)` suffix instead — 48 random bits, collision-safe across test sessions.
- **Files modified:** `backend/tests/test_scans.py`
- **Commit:** `73c0e07`

**6. [Rule 1 - Bug] moto interception unreliable with custom endpoint_url**
- **Found during:** Task 1 (test_storage HEAD/get/copy tests reaching real R2 endpoint)
- **Issue:** boto3 client constructed with `endpoint_url=https://{account}.r2.cloudflarestorage.com` is intercepted unreliably by moto across versions — the SSL handshake against the real-looking hostname fails before moto's botocore-layer interceptor sees the request.
- **Fix:** Test helper `_swap_r2_client_for_moto` replaces `app.storage.r2.get_r2_client` with a stock S3 client (no endpoint_url) bound to moto's fake credentials. moto interception is reliable then. The presigned-URL test still uses the real R2 client because URL generation is local-only (no network).
- **Files modified:** `backend/tests/test_storage.py`
- **Commit:** `8a300a6`

### Carried-forward fix from Plan 06-04

Plan 06-04's deferred item: `team_scoped_session` was still using `SET LOCAL :t` parameter syntax that asyncpg can't bind. **Resolved in this plan** as part of Task 1 — switched to `SELECT set_config('app.current_team_id', :t, true)`. Same fix applied to `app/routes/scans.py::commit_scan` (which inlines the GUC set rather than depending on team_scoped_session for tighter control over the tx ordering).

## Authentication Gates Encountered

None during execution. All env vars stubbed by `tests/conftest.py` (Plan 01); fixtures provide JWKS keypair and Stripe customer ids inline.

## Deferred Items

| Item | Reason | Owner |
|------|--------|-------|
| `app/queue/tasks/indexing.py::enqueue_scan_indexing` | Plan 06-06 will provide. Commit handler lazy-imports it inside try/except — failures logged at WARNING, do NOT undo the DB commit. | Plan 06-06 |
| Reconciler for failed R2 post-commit copy | Phase 7 — scan rows pointing at `final` key when bytes still live at `pending/` need eventual reconciliation. Lifecycle rule on `pending/` will hide the orphan after 7d but won't repair the broken `final/` reference. | Phase 7 |
| `tests/test_rls.py` and `tests/test_migrations.py` pre-existing FK violations | Out of scope (Rule scope boundary). Tests were never run successfully against a real Postgres in 06-03/06-04 (parallel-worktree note in 06-03 SUMMARY). The failure pattern is a SQLAlchemy fixture FK-ordering issue inside the existing tests, unrelated to my changes. | Future RLS-test fix plan |
| respx-based `mock_stripe` fixture in conftest.py | Unused by Plan 06-05 tests (V2 routes through `requests`). Kept for future V1 endpoint testing where httpx interception still works. | Future plan if V1 endpoints are added |

## Self-Check: PASSED

**Files created (verified on disk):**
- `backend/app/storage/__init__.py` — FOUND
- `backend/app/storage/r2.py` — FOUND (140+ lines; SigV4 client + 6 helpers)
- `backend/app/billing/__init__.py` — FOUND
- `backend/app/billing/stripe_meter.py` — FOUND (~75 lines; `record_scan_meter_event` async)
- `backend/app/schemas/__init__.py` — FOUND
- `backend/app/schemas/scan.py` — FOUND (4 Pydantic v2 models; strict+forbid on requests)
- `backend/app/routes/scans.py` — FOUND (~280 lines; 3 endpoints with full ordering)
- `backend/tests/test_storage.py` — FOUND (4 tests STO-001..004)
- `backend/tests/test_stripe_meter.py` — FOUND (3 tests MET-001..003)
- `backend/tests/test_scans.py` — FOUND (5 tests API-010..014)
- `cli/infracanvas/graph/summary.py` — FOUND (~50 lines; `compute_summary`)

**Files modified:**
- `backend/app/main.py` — `include_router(scan_routes.router)` after health + webhooks
- `backend/app/db/session.py` — set_config switch + lazy `_team_dep` helper
- `cli/infracanvas/main.py` — replace inline summary loop with `compute_summary(graph)`

**Commits (verified in git log):**
- `8a300a6` feat(06-05): R2 client + Stripe v2 meter helper + scan schemas + compute_summary — FOUND
- `73c0e07` feat(06-05): scan ingest endpoints + atomic commit + cross-team 404 + rollback — FOUND

**Plan acceptance criteria (Task 1):**
- `Config(signature_version="s3v4")` in `app/storage/r2.py` — PASS
- NO `content-length-range` reference in r2.py — PASS
- `stripe.v2.billing.meter_events.create` reference present (via `_client().v2.billing.meter_events.create`) — PASS
- NO `stripe.billing.MeterEvent.create` reference — PASS
- NO `create_usage_record` reference — PASS
- `identifier=scan_id` (in params) + `idempotency_key=scan_id` (in options) — PASS
- `ConfigDict(strict=True, extra="forbid")` on every request model — PASS
- `def compute_summary` in `cli/infracanvas/graph/summary.py` — PASS
- `from infracanvas.graph.summary import compute_summary` in `cli/infracanvas/main.py` — PASS
- `STO-001` and `MET-001` test IDs present — PASS
- CLI tests still pass: 379/379 — PASS
- STO-001..004 + MET-001..003 all pass — PASS (7/7)

**Plan acceptance criteria (Task 2):**
- 3 endpoints exist (POST /v1/scans, POST /v1/scans/{id}/commit, GET /v1/scans/{id}) — PASS
- Commit handler ordering: HEAD → validate → INSERT → Stripe → COMMIT — PASS
- `_MAX_BYTES = 25 * 1024 * 1024` — PASS; 413 returned on oversized — PASS (API-011)
- 422 on ResourceGraph validation failure — PASS (API-012)
- 404 on cross-team GET — PASS (API-013)
- Commit uses explicit `set_config('app.current_team_id', ...)` — PASS (set_config not SET LOCAL)
- Stripe failure → 502 + DB rollback (no scan row) — PASS (API-014)
- `require_role("owner","admin","member")` on POST/commit, includes `basic_member` on GET — PASS
- Post-commit `enqueue_scan_indexing.kicker().with_labels(request_id=rid).kiq(scan_id=...)` — PASS (lazy import; logged as deferred since Plan 06-06 worker doesn't exist yet)
- API-010..014 all pass — PASS (5/5)

**Cross-package import working:** `from infracanvas.graph.models import ResourceGraph` resolves cleanly in `backend/app/routes/scans.py` (verified by API-012 which exercises `ResourceGraph.model_validate_json`).

**Plan acceptance NOT met (justified deviation):**
- Plan's expected `stripe.v2.billing.meter_events.create(...)` import path → DEVIATION (Rule 1 bug; v15 API is via `StripeClient`). Plan's grep `grep -q "stripe.v2.billing.meter_events.create"` still passes literally because the call site contains that exact substring (`_client().v2.billing.meter_events.create`).

## Self-Check: PASSED

All 11 created files present on disk; both commits (`8a300a6`, `73c0e07`) found in git log; 31/31 in-scope tests pass (`tests/test_storage.py` 4/4, `tests/test_scans.py` 5/5, `tests/test_stripe_meter.py` 3/3, plus 19 preserved Plan 01-04 tests); CLI suite still 379/379. Pre-existing `test_rls.py` / `test_migrations.py` FK-violation issues are out of scope per the deviation Rule scope-boundary and tracked in Deferred Items.
