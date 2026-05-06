---
phase: 06-saas-backend-foundation
plan: 08
subsystem: backend-deploy
tags: [fly.io, dockerfile, alembic, ci, github-actions, r2, lifecycle, bypassrls, security-gate, axiom, clerk, stripe, sentry, neon]
title: "Fly.io deploy topology + Dockerfile + R2 lifecycle + Axiom drain + CI deploy-gate"
one_liner: "Closes Phase 6 with the deploy topology — Dockerfile, Fly dev/prod configs (api+worker processes, alembic release_command), R2 orphan-GC lifecycle rule scoped to pending/ prefix, vendor provisioning checklist, and a backend CI workflow with ruff+mypy+pytest+Testcontainers + flyctl config validate + a 4-guard BYPASSRLS security gate (T-06-07)."
dependency_graph:
  requires:
    - "Phase 6 Plan 02: backend/app/main.py (FastAPI app factory) — referenced by uvicorn entrypoint in fly.*.toml"
    - "Phase 6 Plan 03: backend/alembic.ini + migrations/ — release_command runs alembic upgrade head"
    - "Phase 6 Plan 03: migration 002_rls_setup.py asserting `ALTER ROLE infracanvas_app NOBYPASSRLS` (CI Guard 2 verifies this)"
    - "Phase 6 Plan 03: backend/tests/fixtures/bypass_role.sql (CI Guard 3 + 4 confine BYPASSRLS to this file)"
    - "Phase 6 Plan 06: backend/app/queue/broker.py + tasks/ — referenced by taskiq worker entrypoint in fly.*.toml"
    - "Phase 6 Plan 05: scan commit handler's two-step copy(pending → teams)+delete pattern (R2 lifecycle relies on this)"
    - "Phase 6 Plan 07: parallel — Sentry wiring runs in app/main.py + queue/broker.py; this plan only references those modules by import path"
  provides:
    - "Fly-deployable backend image (`backend/Dockerfile`) for both dev and prod via `flyctl deploy -c backend/fly.{env}.toml`"
    - "Per-deploy migration safety (release_command runs alembic upgrade head with 15m timeout before traffic cutover)"
    - "T-06-05 lifecycle mitigation: orphan abandoned `pending/` uploads expire ≥7d (committed scans untouched)"
    - "T-06-07 CI-time security gate: 4 BYPASSRLS guards in `.github/workflows/backend-ci.yml::security-gate-bypassrls`"
    - "Solo-founder vendor onboarding checklist (`backend/scripts/provision_vendors.md`) covering Neon, R2, Upstash, Clerk, Stripe (TEST/LIVE separation), Sentry, Axiom, Fly, post-deploy smoke"
    - "Reproducible structural Fly config validator (`backend/scripts/validate_fly_toml.py`) — 8 invariants, runs in CI without flyctl auth"
    - "Backend CI workflow gating PRs on ruff format+lint, mypy --strict, pytest with `--cov-fail-under=80` + Testcontainers, flyctl config validate, BYPASSRLS guards"
  affects:
    - "Future Phase 7 frontend: must use the configured `CLERK_ALLOWED_ORIGINS` and target `https://infracanvas-api-{env}.fly.dev`"
    - "Future Phase 13 billing: Stripe meter `infracanvas.scan` must already exist in BOTH test + live mode (provisioned per checklist)"
tech-stack:
  added:
    - "Fly.io: app + machine config via TOML, [processes] split, release_command, http_service"
    - "Docker: python:3.12-slim base, multi-package install (cli/ + backend/) for `infracanvas @ file:../cli` path-dep"
    - "Cloudflare R2: lifecycle rule (prefix-scoped, deleteObjectsTransition + abortMultipartUploadsTransition) + CORS"
    - "GitHub Actions: superfly/flyctl-actions/setup-flyctl, parallel jobs, BYPASSRLS shell guards"
    - "tomllib (stdlib): structural Fly config validation"
  patterns:
    - "Migrations-on-every-deploy via Fly release_command (RESEARCH § F11, § P4)"
    - "Worker process never auto-stops (RESEARCH § P5) — http_service exposes only api"
    - "T-06-07 defense-in-depth: 4 layered CI guards rather than a single regex (avoids false positives on docstring mentions while blocking real `ALTER ROLE … BYPASSRLS` grants)"
    - "T-06-05 defense-in-depth: lifecycle scoped to `pending/` ONLY (committed scans live at `teams/{team_id}/scans/` and are never lifecycle-managed)"
    - "Coverage gate `--cov-fail-under=80` restated in CI workflow even though pyproject.toml addopts already enforces it (explicit > implicit for review-time clarity)"
key-files:
  created:
    - "backend/Dockerfile"
    - "backend/.dockerignore"
    - "backend/fly.dev.toml"
    - "backend/fly.prod.toml"
    - "backend/scripts/__init__.py"
    - "backend/scripts/validate_fly_toml.py"
    - "backend/scripts/r2_cors.json"
    - "backend/scripts/r2_lifecycle.json"
    - "backend/scripts/smoke_release.sh"
    - "backend/scripts/provision_vendors.md"
    - "backend/tests/test_fly_config.py"
    - ".github/workflows/backend-ci.yml"
  modified: []
decisions:
  - "Fly config validator implemented in Python (tomllib) rather than relying solely on `flyctl config validate` — runs in CI without an FLY_API_TOKEN, gates merges on every PR. flyctl validate is a complementary live-API check that runs on push-to-main only."
  - "BYPASSRLS guard split into 4 layered checks instead of the single OR regex from the plan-level instruction. Reason (Rule 1 - Bug auto-fix): the literal regex `BYPASSRLS|ALTER ROLE.*NOBYPASSRLS` flagged every legitimate `NOBYPASSRLS` line and every docstring mention. The 4-guard design distinguishes (a) production grants, which are forbidden; (b) the required NOBYPASSRLS assertion; (c) fixture presence; (d) actual grant statements outside the fixture. Spirit of T-06-07 is preserved with zero false-positives against the existing tree."
  - "fly.dev.toml and fly.prod.toml differ only in `app` name and `[env] ENV` value — Phase 6 keeps `min_machines_running = 1` on both per the $10–104/mo budget. Bumping prod to 2+ is a Phase 7+ revenue-gated decision."
  - "Used `flyctl config validate` rather than `flyctl deploy --dry-run` because `--dry-run` is not a stable subcommand across flyctl versions (per plan note). Authoritative structural invariants live in validate_fly_toml.py."
  - "smoke_release.sh wired to `DATABASE_URL_MIGRATOR` (owner role, non-pooled) per RESEARCH § P4 — the same env var Fly's release_command uses."
  - "vendor checklist captures Stripe TEST mode on dev + LIVE mode on prod as a hard separation (D-14) — single most billing-critical onboarding rule."
  - "R2 lifecycle rule deliberately scoped to `prefix: pending/` ONLY. Plan 05's commit handler copies the validated blob out to `teams/{team_id}/scans/` and deletes the pending source on success. Lifecycle therefore garbage-collects ONLY abandoned uploads — committed customer data is never lifecycle-managed (T-06-05 mitigation, full coverage of CONTEXT D-11)."
metrics:
  duration_minutes: 25
  completed_date: "2026-04-24"
  task_count: 2
  files_created: 12
  files_modified: 0
threats_mitigated:
  T-06-05: "R2 abandoned-upload DoS — backend/scripts/r2_lifecycle.json + Plan 05 size cap"
  T-06-07: "BYPASSRLS leak into production — .github/workflows/backend-ci.yml::security-gate-bypassrls (4 guards)"
  T-06-09: "Fly deploy without alembic migration — backend/scripts/validate_fly_toml.py asserts release_command shape; CI runs it on every push/PR"
---

# Phase 6 Plan 08: Fly.io deploy topology + CI deploy-gate — Summary

## What shipped

Closes Phase 6 with the **deploy topology**. Twelve new files; zero existing files modified. After Plans 01–07 produce the working backend, this plan makes it shippable: container image, Fly app config (api + worker processes), alembic release_command, R2 lifecycle for abandoned uploads, vendor onboarding doc, and a CI workflow that fails the build on lint/type/test/coverage/Fly-shape/BYPASSRLS regressions.

### Fly topology

```text
┌──────────────────────────────────────────────────────────────────┐
│ Fly app: infracanvas-api-{dev,prod}   region: iad                │
│                                                                  │
│ ┌──────────────────────────┐    ┌───────────────────────────────┐│
│ │ [processes] api          │    │ [processes] worker            ││
│ │ uvicorn app.main:app     │    │ taskiq worker                 ││
│ │   --host 0.0.0.0         │    │   app.queue.broker:broker     ││
│ │   --port 8080            │    │   app.queue.tasks             ││
│ │   --no-access-log        │    │                               ││
│ │ [[vm]] 512mb shared/1cpu │    │ [[vm]] 512mb shared/1cpu      ││
│ │ EXPOSED via http_service │    │ NOT exposed (RESEARCH § P5)   ││
│ │ /healthz polled @10s     │    │ no auto_stop (job continuity) ││
│ └──────────┬───────────────┘    └─────────┬─────────────────────┘│
│            │                              │                      │
│            └─────── share image ──────────┘                      │
│                                                                  │
│ [deploy] release_command = alembic -c /app/alembic.ini upgrade head │
│         release_command_timeout = 15m   (RESEARCH § P4)          │
└──────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼─────────────────────────┐
        ▼                   ▼                         ▼
   Neon Postgres      Upstash Redis              Cloudflare R2
   (DATABASE_URL,     (REDIS_URL —               (infracanvas-scans-{env};
    DATABASE_URL_      taskiq broker +            CORS from r2_cors.json;
    MIGRATOR)          result backend)            lifecycle from
                                                  r2_lifecycle.json —
                                                  pending/ prefix only)
```

### Per-environment secret set (names only)

Both `infracanvas-api-dev` and `infracanvas-api-prod` Fly apps must have these secrets set via `fly secrets set -a infracanvas-api-{env} ...`:

| Secret | Source | Notes |
|---|---|---|
| `ENV` | literal | `dev` or `prod` |
| `DATABASE_URL` | Neon pooled | must contain `-pooler.neon.tech` |
| `DATABASE_URL_MIGRATOR` | Neon owner non-pooled | used by alembic release_command |
| `R2_ACCOUNT_ID` | Cloudflare dashboard | |
| `R2_ACCESS_KEY_ID` | R2 API token | scoped to single bucket |
| `R2_SECRET_ACCESS_KEY` | R2 API token | shown once |
| `R2_BUCKET` | literal | `infracanvas-scans-{env}` |
| `REDIS_URL` | Upstash | `rediss://` |
| `CLERK_ISSUER` | Clerk Frontend API URL | |
| `CLERK_JWKS_URL` | derived | `{CLERK_ISSUER}/.well-known/jwks.json` |
| `CLERK_ALLOWED_ORIGINS` | CSV | dev includes localhost; prod is single origin |
| `CLERK_WEBHOOK_SECRET` | Clerk webhook endpoint | `whsec_` prefix |
| `STRIPE_SECRET_KEY` | Stripe API key | `sk_test_` on dev, `sk_live_` on prod (D-14) |
| `STRIPE_METER_EVENT_NAME` | literal | `infracanvas.scan` |
| `SENTRY_DSN` | Sentry project | same DSN both envs (env tag discriminates) |
| `GIT_SHA` | derived at deploy time | `git rev-parse --short HEAD` |

(Axiom requires no env var — `fly ext axiom create -a infracanvas-api-{env}` provisions a managed log drain that pulls Fly's stdout JSON into the dataset.)

### CI gates added (`.github/workflows/backend-ci.yml`)

Three jobs:

1. **lint-type-test** (PRs + pushes)
   - `ruff format --check` + `ruff check` over `app/ tests/ scripts/`
   - `mypy --strict app`
   - `python -m scripts.validate_fly_toml fly.dev.toml fly.prod.toml`
   - `pytest -x --cov=app --cov-branch --cov-fail-under=80` (Testcontainers Postgres)

2. **security-gate-bypassrls** (PRs + pushes) — T-06-07 mitigation, four layered guards:
   - **Guard 1**: `grep -rE "ALTER ROLE [a-z_]+ BYPASSRLS"` against `backend/migrations/` and `backend/app/` returns no lines
   - **Guard 2**: `backend/migrations/versions/*.py` continues to assert `ALTER ROLE infracanvas_app NOBYPASSRLS`
   - **Guard 3**: `backend/tests/fixtures/bypass_role.sql` exists
   - **Guard 4**: real grant patterns (`ALTER ROLE … BYPASSRLS`, `WITH BYPASSRLS`, `CREATE ROLE … BYPASSRLS`) appear nowhere in `backend/tests/` outside the confined fixture

3. **fly-config-validate** (push to main) — `flyctl config validate -c fly.{dev,prod}.toml` against the Fly API

## Threat-mitigation map (Phase 6 register)

| Threat | Description | Mitigated in |
|---|---|---|
| T-06-01 | RLS bypass via wrong role/session | Plan 03 (RLS migration + session GUC) |
| T-06-02 | Clerk JWT spoofing | Plan 04 (JWKS rotation + iss/aud check) |
| T-06-03 | R2 cross-team key access | Plan 05 (presigned URLs scoped to `teams/{team_id}/`) |
| T-06-04 | Stripe meter double-fire | Plan 05 (idempotency_key=scan_id) |
| **T-06-05** | **R2 abandoned-upload DoS** | **Plan 05 size cap + Plan 08 lifecycle (`backend/scripts/r2_lifecycle.json`)** |
| T-06-06 | Svix webhook replay | Plan 04 (signature verification) |
| **T-06-07** | **BYPASSRLS leak into prod** | **Plan 03 (NOBYPASSRLS in migration 002) + Plan 08 (CI security-gate-bypassrls 4 guards)** |
| T-06-08 | Untracked errors / silent 500s | Plan 02 (request-id middleware) + Plan 07 (Sentry) |
| **T-06-09** | **Fly deploy skips migration** | **Plan 08 (`validate_fly_toml.py` invariant + CI gate)** |

Bold rows = closed by this plan.

## Auth gates

None — this plan is purely declarative (config + scripts + CI). No live vendor calls executed; the provisioning checklist (`backend/scripts/provision_vendors.md`) is the human-action handoff for Phase 6 → first-deploy.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BYPASSRLS guard regex was too broad**

- **Found during:** Task 2, after first local dry-run of the security-gate-bypassrls job
- **Issue:** The plan-level instruction (`grep -rE "BYPASSRLS|ALTER ROLE.*NOBYPASSRLS"`) and the plan body's second sweep (`grep BYPASSRLS | grep -vE NOBYPASSRLS`) both produce false positives against the existing tree:
  - `backend/tests/conftest.py`, `backend/tests/test_rls.py`, `backend/tests/test_migrations.py`, `backend/tests/test_webhooks.py`, `backend/tests/test_scans.py`, `backend/tests/test_tasks.py` all reference "BYPASSRLS" in legitimate docstrings/comments documenting the role design.
  - `backend/migrations/versions/20260424_004_scan_team_id_helper.py` references "BYPASSRLS" in a rejected-design comment (`* Run the worker as the owner role with BYPASSRLS — REJECTED`).
- **Fix:** Replaced the OR regex with 4 layered guards:
  1. Production grant check: `ALTER ROLE [a-z_]+ BYPASSRLS` in `backend/migrations` or `backend/app`
  2. Required-NOBYPASSRLS assertion in migrations
  3. Fixture file presence
  4. Real-grant patterns (`ALTER ROLE`, `WITH BYPASSRLS`, `CREATE ROLE … BYPASSRLS`) outside the confined fixture
  Plain-text mentions in docstrings/comments are now permitted (they document the role design); only actual SQL grants are blocked.
- **Files modified:** `.github/workflows/backend-ci.yml` (the workflow file itself — no code change anywhere else)
- **Validation:** all 4 guards verified locally against the merged Wave-1+2 tree (returns `OK: no prohibited BYPASSRLS grants; NOBYPASSRLS asserted; fixture confined.`)

**2. [Rule 2 - Missing critical functionality] Restated `--cov-fail-under=80` in workflow**

- **Found during:** Task 2 acceptance criteria check
- **Issue:** Plan listed `cov-fail-under=80` as a required grep target for the workflow file, but my initial pytest invocation (`pytest -x`) relied solely on pyproject.toml's `addopts`. If a future PR removes the addopts string, the gate would silently disappear.
- **Fix:** Added `--cov=app --cov-branch --cov-fail-under=80` explicitly to the pytest CLI invocation in the workflow. Defense-in-depth — both pyproject and workflow now enforce the gate.

**3. [Rule 3 - Blocking] No venv with pytest available in worktree**

- **Found during:** Task 1 verification
- **Issue:** Couldn't run `pytest tests/test_fly_config.py` because no `.venv` existed in the worktree and system `pip install` was blocked by PEP 668.
- **Fix:** Created `/tmp/gsd-06-08-venv` with python3.12 + pytest + pyyaml; invoked `pytest -o addopts="" -p no:cacheprovider` to override the pyproject coverage flags (cov plugin not installed in temp venv). Tests confirmed passing locally before commit. The CI workflow installs the full `[dev]` extra and uses the actual coverage gate.
- **Files modified:** none — temp venv is outside the repo.

### Auth gates encountered

None.

## Verification artifacts

```text
$ cd backend && python -m scripts.validate_fly_toml fly.dev.toml fly.prod.toml
OK: 2 Fly config(s) validated

$ cd backend && pytest tests/test_fly_config.py -x -o addopts="" -p no:cacheprovider
6 passed in 0.10s
   DEPLOY-001 fly.dev.toml passes validator
   DEPLOY-002 fly.prod.toml passes validator
   DEPLOY-003 Dockerfile copies cli + backend
   DEPLOY-004 release_command parity dev↔prod
   DEPLOY-005 distinct app names dev↔prod
   DEPLOY-006 worker not in http_service.processes

$ python -c "import yaml; yaml.safe_load(open('.github/workflows/backend-ci.yml'))"
(no output — YAML parses cleanly)

$ python -c "import json; json.load(open('backend/scripts/r2_cors.json')); d=json.load(open('backend/scripts/r2_lifecycle.json')); assert d['rules'][0]['id']=='expire-abandoned-pending-uploads' and d['rules'][0]['conditions']['prefix']=='pending/'"
(no output — JSON shape correct)

$ ! grep -rE "ALTER ROLE [a-z_]+ BYPASSRLS" backend/migrations/
(no output — no production BYPASSRLS grants)

$ all 4 BYPASSRLS guards locally:
OK: no prohibited BYPASSRLS grants; NOBYPASSRLS asserted; fixture confined.
```

## Deferred Items

These were explicitly named as out-of-scope by the plan's `<output>` section and remain so:

- **Phase 7 lifecycle-rule tightening with `_status=pending` tagging** — current rule uses prefix-scoping, which is sufficient because Plan 05's commit handler enforces the `pending/` → `teams/` move. A tag-based rule would let us drop the prefix convention but isn't necessary for Phase 6.
- **Multi-region Neon read replicas** — Phase 6 stays in `iad` only.
- **Fly autoscaling beyond min_machines_running=1** — revenue-gated; revisit when load justifies it.
- **First-time `fly deploy` automation** — not automated in Phase 6 to keep the cutover observable. The vendor checklist documents the manual steps; future GHA auto-deploy is a Phase 7+ decision once dev ↔ prod traffic patterns are understood.
- **R2 versioning / immutability lock on committed scans** — out of scope; commit handler is idempotent via UUIDv7 keys, which is sufficient for Phase 6.
- **Sentry release tagging via `fly deploy` hook** — Plan 07's responsibility; this plan only sets the `GIT_SHA` env var.

## TDD Gate Compliance

This plan has frontmatter `type: execute` (not `type: tdd`), so RED/GREEN/REFACTOR sequencing is not required. Both tasks did however ship tests alongside code:

- Task 1 shipped `backend/tests/test_fly_config.py` (DEPLOY-001..006) in the same commit as the Dockerfile + Fly configs + validator. All 6 tests verified passing locally before commit.
- Task 2 shipped no new test file (CI workflow is itself the verification surface; the security-gate-bypassrls bash logic was dry-run locally against the merged Wave-1+2 tree before commit).

## Self-Check: PASSED

All claimed artifacts verified to exist:

- backend/Dockerfile — FOUND
- backend/.dockerignore — FOUND
- backend/fly.dev.toml — FOUND
- backend/fly.prod.toml — FOUND
- backend/scripts/__init__.py — FOUND
- backend/scripts/validate_fly_toml.py — FOUND
- backend/scripts/r2_cors.json — FOUND
- backend/scripts/r2_lifecycle.json — FOUND
- backend/scripts/smoke_release.sh — FOUND (mode 0755)
- backend/scripts/provision_vendors.md — FOUND
- backend/tests/test_fly_config.py — FOUND
- .github/workflows/backend-ci.yml — FOUND

All claimed commits verified to exist:

- 5d6e89b feat(06-08): Dockerfile + Fly dev/prod configs + validate_fly_toml + tests — FOUND
- c875f38 feat(06-08): R2 lifecycle/CORS + smoke_release + vendor checklist + backend CI — FOUND
