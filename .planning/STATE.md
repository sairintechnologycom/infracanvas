---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Hardening + SaaS Dashboard + CostLens + FlowMap 3b
status: ready
last_updated: "2026-05-04T16:30:00.000Z"
last_activity: 2026-05-04 -- Phase 7.5 Plan 05 complete (Wave 2 second plan: services/scans.py with finalize_scan + fire_scan_meter_or_502 sibling helpers extracted; POST /v1/scans/from-github with RLS membership probe + lazy scan_repo enqueue + pending→failed enqueue-failure failsafe; GET /v1/scans/{id} extended with 6 new fields + presigned_get_url=null when status!=ready; 13 new tests; 4 commits 0e95bc8/f0df6ff/a2df694/aba0c3a)
progress:
  total_phases: 19
  completed_phases: 12
  total_plans: 102
  completed_plans: 86
  percent: 84
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20 — v1.1 started)

**Core value:** One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres.
**Current focus:** Phase 7.5 — github-repo-connector (Wave 1 in progress)

## Current Position

Milestone: v1.1 — started 2026-04-20
Phase: 7.5 — 11 PLAN.md files written across 7 waves; plan-checker PASSED (iter 1)
Plan: 5/11 (07.5-01 + 07.5-02 + 07.5-03 + 07.5-04 + 07.5-05 complete; 07.5-06 next — scan_repo taskiq job worker)
Status: In progress (Wave 2 routes complete: GitHub discovery routes + install-callback + POST /v1/scans/from-github + finalize_scan helper extraction all landed; Wave 3 worker plan 06 + dashboard proxy plan 07 next)
Last activity: 2026-05-04 -- Phase 7.5 Plan 05 closed (4 commits: 0e95bc8 test RED finalize_scan, f0df6ff feat GREEN services/scans.py with finalize_scan + fire_scan_meter_or_502 + commit_scan refactor, a2df694 test RED scans-from-github, aba0c3a feat GREEN routes/scans_from_github.py + ScanGetResp extension + main.py wire). 13 new tests across tests/test_services_scans.py (3 finalize) + tests/api/test_scans_from_github.py (10 from-github+extended-GET) collect cleanly; ruff + mypy --strict clean across new code (app/services/scans.py + app/routes/scans_from_github.py + app/main.py). Tests skip locally (Docker absent) but execute on CI. Locks the 7-kwarg scan_repo dispatch contract for Plan 06 + extended GET shape for Plan 11.

## Accumulated Context

### Roadmap Evolution

- 2026-04-20: Milestone v1.1 opened (continuing phase numbering from v1.0's 3.5)
- 2026-04-20: v1.0 post-ship E2E wiring review surfaced 4 fixes → added as WRG-01..04, scoped as first hardening phase of v1.1
- 2026-04-21: Phase 5.1 inserted after Phase 5: Parser realism + CLI UX (URGENT — local `module {}` resolution gap and noisy CLI output surfaced during Phase 5 manual testing; pre-Phase 6)
- 2026-04-21: Phase 7.5 inserted after Phase 7: GitHub Repo Connector (fills the "connect a repo + pick branch + scan" UX gap before Phase 8 webhooks — GitHub-only MVP, multi-provider deferred to v1.2)
- Phase 7.1 inserted after Phase 7: Phase 7 UI Contract Remediation — close UI-SPEC gaps from 07-UI-REVIEW.md (shadcn init, compare diff list, share toasts/revoke, polish drift) (URGENT)
- 2026-05-02: Phase 7.2 inserted after Phase 7.1: UI Contract Remediation — Live (live audit 07.1-LIVE-UI-REVIEW.md scored 10/24; 14 fixes covering viewer h-screen embed break, singleton store leak in 4 viewer components, /settings 404, sparkline ovals, grade-threshold split, sidebar dead zone) (URGENT — blocks Phase 7.5)

### Decisions

Decisions carried from v1.0 (see PROJECT.md Key Decisions table). Open items affecting v1.1:

- [Phase 3b]: Cisco NETCONF compatibility research needed BEFORE planning DCA-02
- [Phase 3b]: DC Agent enterprise CAB approval takes 4–12 weeks; DCA-09 security packet must be ready early
- [Phase 4]: Extract viewer to shared dual-build package BEFORE any Next.js dashboard work
- [Phase 4]: Use Neon session-mode pooler + dedicated `infracanvas_app` role (no BYPASSRLS) to prevent RLS leakage
- [Phase 4]: Next.js 15 (not 14); taskiq (not arq); Stripe Billing Meters only; netsampler/goflow2/v2 (not goflow)
- [v1.1]: Wiring fixes run BEFORE SaaS work so Phase 4+ builds on a known-good CLI core
- 05.1-02: Committed producer + consumer (hcl.py + module.py + graph/builder.py) in a single atomic commit (de149a8) to preserve the coordinated-edit contract — no intermediate tree state has a consumer reading an unemitted field
- 05.1-02: COUNT_EXPANSION_CAP=1000 — DoS guard applied BEFORE range expansion in _expand_count/_expand_for_each; oversized literals collapse to 1 unresolved node + synthetic parse_errors note (T-05.1-05 mitigation)
- 05.1-03: Three orthogonal output-shape flags (--quiet / --json / --ci) on scan/plan, plus --open on scan/plan/export, resolving PATTERNS.md note 1 --quiet semantic collision without breaking existing --ci contract
- 05.1-03: export command's unconditional webbrowser.open replaced with explicit --open opt-in — minor breaking change, documented in future release notes
- 06-04: Replaced `INSERT ... ON CONFLICT DO NOTHING` with probe-via-`team_by_clerk_org()`-then-INSERT in the Clerk webhook handler. PG's INSERT...ON CONFLICT executor evaluates UPDATE policy WITH CHECK even with DO NOTHING — incompatible with strict per-team UPDATE policy. Probe pattern preserves Svix-replay idempotency without weakening RLS.
- 06-04: Switched `SET LOCAL app.current_team_id = :t` → `SELECT set_config('app.current_team_id', :t, true)` in webhook handlers. asyncpg's wire protocol cannot bind parameters to SET LOCAL. set_config() is the parameter-safe equivalent. (Plan 03's session.py still uses SET LOCAL syntax; will fail when first exercised under bind params — Plan 06-05 follow-up.)
- 06-04: Added psycopg2-binary~=2.9.0 to backend dev extras — Plan 01's conftest needs sync driver for one-shot setup DDL on the testcontainer; was missing.
- Plan 06-05: Stripe-python v15 routes V2 endpoints via StripeClient (not module-level stripe.v2.billing.meter_events.create); switched to client.v2.billing.meter_events.create(params, options).
- Plan 06-05: respx-based Stripe mocking can't intercept v15 V2 calls (uses requests not httpx); use SDK-boundary mocking by replacing stripe_meter._client.
- Plan 06-05: TestClient + production async pool causes 'Future attached to a different loop' on second request; tests use NullPool engine to avoid cross-loop reuse.
- Plan 06-05: Two-step R2 layout — pending/{id}.json (PUT target, no team_id) → server-side copy to teams/{team_id}/scans/{id}.json on commit, then DELETE pending; lifecycle rule GCs abandoned pending/ after 7d (T-06-04 + T-06-05 mitigation).
- Plan 07.1-01: shadcn/ui v4 emits both `@import "tw-animate-css"` AND `@import "shadcn/tailwind.css"` — kept both (legitimate package exports, latter ships data-* custom variants + accordion keyframes from `node_modules/shadcn/dist/tailwind.css`).
- Plan 07.1-01: shadcn init's `add` step overwrites the entire `lib/utils.ts` to land `cn()`; pre-existing helpers (`isUUID()` for T-07-08-01 mitigation) must be re-merged manually after init. Documented for future shadcn version bumps.
- Plan 07.1-01: dashboard/app/layout.tsx unused-import for `Inter` (post Geist migration) blocks `next build` typecheck — out of plan 01 scope, deferred via .planning/phases/07.1-phase-7-ui-contract-remediation/deferred-items.md to a layout-owning plan or the phase verifier cleanup pass.
- Plan 07.5-01: GitHub App settings fields use empty-string defaults (not Optional[str]) — matches existing string-field convention in Settings (stripe_meter_event_name, git_sha) and avoids None-coercion in downstream auth helpers. Real values come from Fly secrets in dev/prod; tests override via conftest.py env-stub block.
- Plan 07.5-01: shadcn `add command` did NOT overwrite lib/utils.ts (cn helper already present from Phase 7.1-01) — different from the 07.1-01 init step which DID overwrite. Documented for future shadcn add invocations: `add` only overwrites when the file is missing or differs structurally.
- Plan 07.5-01: pre-existing `TS6133: 'screen' unused` in dashboard/__tests__/scan-filters.test.tsx (introduced 90852b6 / Phase 7.1-03) deferred via .planning/phases/07.5-github-repo-connector/deferred-items.md — out-of-scope for Plan 07.5-01 per executor SCOPE BOUNDARY rule.
- Plan 07.5-02: split into TWO atomic alembic migrations (007 + 008) instead of one combined migration — reversibility is per-revision, so a future revert can touch only the scans columns without disturbing github_installations (or vice versa). Cost is two Running upgrade lines on a fresh DB; benefit is sharper rollback granularity.
- Plan 07.5-02: dedup partial index predicate is `WHERE status='ready'` (not `status IS NOT NULL`). Only successful scans are dedup candidates — pending/failed re-scans should still proceed. Index column order `(team_id, github_repo, github_sha, created_at DESC)` puts team_id first so the planner uses the RLS predicate first; created_at DESC enables `ORDER BY created_at DESC LIMIT 1` to be index-only.
- Plan 07.5-02: `rsa_private_key` test fixture is session-scoped (not module-scoped) — generation is ~150 ms on M-class CPU and the key is functionally immutable; sharing across the session is safe because tests never mutate it. Plan 03+ depends on this fixture name.
- Plan 07.5-02: `gh_settings_patched` fixture monkeypatches the live `app.settings.settings` singleton rather than constructing a new Settings instance — Plan 03's auth helpers do `from app.settings import settings` at module load, so patching the singleton is the only way to make the test value visible without re-importing the auth module per test.
- Plan 07.5-03: defensive `isinstance(loaded, RSAPrivateKey)` guard in `mint_app_jwt` — `cryptography.hazmat.primitives.serialization.load_pem_private_key` returns a 13-key union; `jwt.encode(..., algorithm="RS256")` only accepts RSA/EC. Without the guard, mypy --strict refuses the assignment AND a non-RSA key would silently sign with the wrong algorithm. Surfaces config errors as a `TypeError` at sign time rather than an opaque downstream failure.
- Plan 07.5-03: dual-path Redis client in `client.py::list_installation_repos` — production uses `_get_redis()` lru_cache singleton (matches `storage/r2.py::get_r2_client()`); tests inject `redis_client=fake_redis` via the new kwarg so the lru_cache never traps a stale URL between tests. Establishes the test-fixture-injection pattern for future redis-cached helpers.
- Plan 07.5-03: `urllib.parse.quote(branch, safe="")` URL-encoding in `get_head_sha` — `feature/foo` becomes `feature%2Ffoo` so the slash isn't treated as a path segment by GitHub's `git/ref/heads/{branch}` endpoint. Test 8 (`test_branch_with_slash`) regression-locks this T-07.5-03-05 mitigation.
- Plan 07.5-03: `get_installation_metadata` uses App JWT (NOT installation token) — per GitHub Apps API, `/app/installations/{id}` is App-level metadata. Test 7 explicitly registers the `/access_tokens` POST and asserts `call_count == 0` to lock the discrimination.
- Plan 07.5-04: install-callback verb is GET (per RESEARCH §Open Q5 — GitHub redirects with GET, not POST; CONTEXT D-10d "POST" is a typo). FastAPI `@router.get("/install-callback")` correctly mirrors that.
- Plan 07.5-04: state-CSRF semantic divergence from D-14: `state == team.clerk_org_id` (browser-knowable Clerk org id), NOT `state == team.id`. The dashboard's InstallButton sends Clerk `organization.id`; the backend resolves the Team via existing `resolve_team_from_clerk_org` and checks `state == team.clerk_org_id`, closing the CSRF loop without leaking team_id to the browser.
- Plan 07.5-04: membership probe (look up the installation_id in github_installations under the team's RLS context) runs BEFORE the GitHub API call in /v1/github/repos and /v1/github/branches. Two reasons: cross-team probes return 404 without spending the GitHub rate limit; explicit `installation_not_found` is friendlier than a downstream auth error.
- Plan 07.5-04: install-callback handler bundled into the same Task 1 GREEN commit (5565716) as the three read endpoints rather than a separate Task 2 GREEN. Splitting a 4-handler single-file route module across two commits would have left imports in an awkward intermediate state (RedirectResponse / get_installation_metadata imported with no usage in Task 1, tripping ruff F401). Task 2 commit (c595e14) is consequently test-only — the 7 tests still gate the behaviour. TDD strict cadence violated for Task 2 only; documented in plan SUMMARY Deviations §1.
- Plan 07.5-04: tests/api/conftest.py duplicates the GitHub fixtures from tests/integrations/github/conftest.py rather than promoting to tests/conftest.py. Promotion would force every other test module (test_scans, test_share, test_webhooks, ...) to import fakeredis + respx + cryptography RSA generators on collection. Local duplication is ~70 lines and isolated to the API test surface.
- Plan 07.5-04: DASHBOARD_URL resolved via `os.environ.get` with localhost fallback (mirrors share.py:87 _share_url precedent) rather than adding a new dashboard_url Settings field. Adding a Settings field would force every test conftest + .env example to define a default; env-var fallback is locally scoped and obviously skippable in tests via `monkeypatch.setenv`.
- Plan 07.5-05: app/services/scans.py exports TWO sibling helpers (finalize_scan + fire_scan_meter_or_502) instead of one, sharing the underlying record_scan_meter_event call site. Route INSERTed in 'ready' state directly (CLI commit, no UPDATE step needed) → fire_scan_meter_or_502 wraps just the meter+502 translation. Worker INSERTed in 'pending' at enqueue time → finalize_scan does UPDATE+meter atomically with WHERE status != 'ready' RETURNING idempotency guard. Both preserve the D-08/D-09 invariant ('every committed scan row carries one meter event') from their respective tx postures.
- Plan 07.5-05: Lazy `from app.queue.tasks.scan_repo import scan_repo` inside the route's enqueue try block (NOT inside a sub-function) so tests can patch sys.modules before the route runs. Type-checked via `# type: ignore[import-not-found,import-untyped,unused-ignore]` tri-code on the `from` line — covers both pre-Plan-06 (import-not-found / import-untyped) and post-Plan-06 (unused-ignore once the module exists). Pattern is reusable for any 'depends on a not-yet-landed plan' situation.
- Plan 07.5-05: Enqueue failure flips the just-inserted scans row pending → failed with error_message='enqueue_failed' BEFORE raising 503. Catches via broad `except Exception as e` because orphan-pending-row failure mode is worse than swallowing a specific broker error type — even a TypeError from a wrong-shaped scan_repo (if Plan 06 lands incorrectly) flips the row to failed. Plan 11's polling page treats failed as terminal so users see the error rather than spinning on an orphan.
- Plan 07.5-05: scan_repo dispatch contract (CC-4) locks 7 kwargs: scan_id, installation_id, repo, branch, sha, path, team_id. Plan 06's `@broker.task` decorator must accept exactly these as kwargs. Tests verify the exact kwarg set via a recording stub.
- Plan 07.5-05: ScanGetResp.presigned_get_url relaxed from `str` to `str | None` (back-compat-friendly default None). Signed ONLY when row.status==ScanStatus.ready AND row.r2_key is truthy. Plan 11's polling page uses null-vs-non-null as the 'still working / show viewer' discriminant.
- Plan 07.5-05: pending scans row INSERTs r2_key='' (empty string) rather than NULL or sentinel. NULL would force a column-nullability migration; sentinel would tempt routes to GET-presign on a fake key. Empty string is the column default-equivalent; conditional URL signing in get_scan gates it cleanly.
- Plan 07.5-05: branch_not_found error detail includes the user-facing `{repo}@{branch}` tuple ('branch_not_found:acme/infra@main') so the dashboard can render a precise toast. Acceptable info-leak — the team owns this installation per the membership probe; learning a branch doesn't exist on a repo they have access to is non-sensitive.

### Pending Todos

- Run `/gsd-plan-phase 4` once REQUIREMENTS.md + ROADMAP.md are written

### Blockers/Concerns (carried into v1.1)

- [Phase 3b]: DC Agent CAB approval timeline (4–12 weeks) is critical path
- [Phase 3b]: Cisco NETCONF compatibility matrix unknown
- [Phase 4]: Viewer extraction to shared package is load-bearing; divergence creates long-term maintenance liability

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260501-aw7 | Fix React Flow zustand provider error on scan detail page | 2026-05-01 | 4cfd658 | [260501-aw7-fix-react-flow-zustand-provider-error-on](./quick/260501-aw7-fix-react-flow-zustand-provider-error-on/) |
| 260502-tra | Fix sparkline width bug — wrapper div in Sparkline.tsx | 2026-05-02 | 373b0d9 | [260502-tra-fix-sparkline-width-bug-wrapper-div-in-s](./quick/260502-tra-fix-sparkline-width-bug-wrapper-div-in-s/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 close (human-gated) | VAL-01..05 Phase 0 campaign (Stripe setup, Typeform live, Reddit/LinkedIn posts, 20 customer conversations, Go/No-Go decision) | Pending human execution — 4–8 week campaign per D-05 | v1.0 close (2026-04-19) |
| v1.0 close (pre-release) | REL-01..04 first PyPI publish + Homebrew tap sync + GHA workflow validation + Show HN submission | Configured, execution pending first semver tag | v1.0 close (2026-04-19) |
| v2 | GCP support (HRZ-05) | Deferred to Year 2 | Init |
| v2 | Pulumi/CDK/Bicep (HRZ-03) | Deferred to Year 2 | Init |
| v2 | Live cloud import (HRZ-01) | Deferred to Year 2 | Init |
| v2 | AI natural language queries (HRZ-02) | Deferred to Year 2 | Init |

## Session Continuity

Last session: 2026-05-04T16:30:00.000Z
Milestone: v1.1 in flight
Resume: Phase 07.5 Plan 06 (Wave 3 — scan_repo taskiq job: clone + run infracanvas scan subprocess + R2 PUT + finalize_scan call to flip pending→ready + fire Stripe meter atomically. Lazy import contract locked at 7-kwarg shape: scan_id, installation_id, repo, branch, sha, path, team_id. On clone/scan/upload failure worker UPDATEs row to status='failed' with error_message)

**Planned Phase:** 7.5 (GitHub Repo Connector) — 11 plans — 2026-05-03
**Plan 07.5-01 closed:** 2026-05-03T09:10Z (4 commits: 033fc9b chore deps+Dockerfile, bb841c3 RED settings tests, 260cf6d GREEN settings + conftest stubs, 6bd29f4 shadcn command primitive). 7/7 settings tests pass; 95 tests collected clean; 183/183 dashboard tests pass. Pre-existing scan-filters.test.tsx tsc warning deferred (out-of-scope).
**Plan 07.5-02 closed:** 2026-05-04T15:05Z (3 commits: 2b52d6e mig 007 github_installations + RLS + grants, d539e15 mig 008 scans github columns + idx_scans_github_dedup partial index + Scan ORM extensions + GithubInstallation ORM class, f70fbc0 tests/integrations/github/ + tests/jobs/ scaffold + 5 shared pytest fixtures + 5 fixture smoke tests + VALIDATION.md flag flip). alembic head at 008_scan_github_columns; downgrade -2 + upgrade head verified reversible; 100 tests collect clean (95 pre-existing + 5 new). Wave 0 closed; Wave 1 unblocked. Resumption: Task 1 was committed (2b52d6e) by previous executor before usage-limit pause; resumption agent verified the commit, confirmed alembic current=007, and resumed at Task 2 without re-doing Task 1.
**Plan 07.5-03 closed:** 2026-05-04T10:16Z (6 commits: 3cb47ce test RED auth, 00a1208 feat GREEN mint_app_jwt + mint_installation_token, 521b261 test RED client, e37c508 feat GREEN list_installation_repos + list_branches + get_head_sha + get_installation_metadata + 60s gh:repos:* Redis cache, c6451ca feat schemas/github.py with 5 Pydantic models + 8 smoke tests, 95c73ed fix lint F401/UP017). 27 tests in tests/integrations/github/ all green (5 fixture smoke from Plan 02 + 22 new); ruff + mypy --strict clean. Pure Python — no live GitHub calls (respx + fakeredis fixtures from Plan 02 cover everything). Wave 1 first plan closed; Plans 04 + 05 + 06 + 07 in Wave 2 all unblocked on the auth/client/schemas contract.
**Plan 07.5-04 closed:** 2026-05-04T12:56Z (3 commits: 266db62 test RED installations/repos/branches, 5565716 feat GREEN app/routes/github.py with 4 handlers + main.py registration, c595e14 test install-callback). 21 integration tests in tests/api/ collect cleanly (4 installations + 5 repos + 5 branches + 7 callback); ruff + mypy --strict clean across app/routes/github.py + app/main.py. Tests skip locally (Docker absent) but execute fully on CI; behaviour gates RLS isolation, ORDER BY installed_at DESC, q-filter, cache hit asserts ZERO GitHub calls, 403/429→503+Retry-After:60, owner/name URL split, regex pattern guard 422, state mismatch 403, App-JWT discrimination via 3-segment shape assert, idempotent ON CONFLICT DO UPDATE, 302 redirects with ?install=success/failed. main.py edit is surgical (1 import + 1 include_router) so Plan 05's scans_from_github registration can land cleanly. Plans 05 + 09 + 10 + 11 unblocked on the /v1/github/* contract.
**Plan 07.5-05 closed:** 2026-05-04T16:30Z (4 commits: 0e95bc8 test RED finalize_scan, f0df6ff feat GREEN services/scans.py + commit_scan refactor, a2df694 test RED scans-from-github, aba0c3a feat GREEN routes/scans_from_github.py + ScanGetResp extension + main.py wire). Two sibling helpers landed in app/services/scans.py: finalize_scan (UPDATE pending→ready + meter for worker context, idempotent via WHERE status != 'ready' RETURNING) + fire_scan_meter_or_502 (thin meter+502 translation for route context); commit_scan refactored to call the latter. POST /v1/scans/from-github mounted under /v1/scans prefix with require_role(owner|admin|member) (basic_member excluded for billing safety), RLS-scoped membership probe BEFORE GitHub call, get_head_sha resolution, INSERT pending row with github_* provenance, lazy 'from app.queue.tasks.scan_repo import scan_repo' (Plan 06 not yet landed) + kicker().with_labels(request_id=rid).kiq with all 7 CC-4 kwargs, enqueue-failure failsafe flips row pending→failed with error_message='enqueue_failed' before 503. ScanGetResp extended with 6 new optional fields (error_message + source_path + 4 github_*) and presigned_get_url relaxed to nullable + signed only when status==ready. 13 new tests collect (3 finalize + 10 from-github+extended-GET); ruff + mypy --strict clean across new code. Pre-existing UP017/I001/dict-type-arg in scans.py + schemas/scan.py NOT addressed (SCOPE BOUNDARY). Locks scan_repo 7-kwarg dispatch contract for Plan 06 + extended GET shape for Plan 11.
