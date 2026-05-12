---
phase: 11
plan: 04
subsystem: firewall-integration
tags: [wave-2, backend, fastapi, clerk-jwt, rls, read-api]
requires:
  - phase-11-plan-02-summary       # Pydantic schemas + ORM models + migration 011
  - phase-11-plan-03-summary       # parent + child rows persisted; read has data to surface
  - phase-7.5-plan-04-summary      # routes/github.py — Pattern B canonical analog
provides:
  - firewall-read-endpoint          # GET /v1/sites/{site_id}/firewall-rules
  - pattern-b-applied-read-side     # set_config('app.current_team_id', :t, true) on read
  - distinct-on-firewall-id-query   # D-11 latest-per-device implementation
  - site-membership-probe-firewall  # 404 cross-team isolation pattern reused
affects:
  - backend/app/routes/firewalls.py   # NEW (1 router, 1 handler, 1 response model)
  - backend/app/main.py                # +2 lines (import + include_router)
  - backend/tests/conftest.py          # Rule 3 fix: firewall_snapshot fixture timestamptz cast
tech-stack:
  added: []  # zero new dependencies — uses existing FastAPI / SQLAlchemy / Pydantic / structlog
  patterns:
    - "Pattern B (Clerk JWT + Team-RLS): require_role(*_READ_ROLES) + resolve_team_from_clerk_org + set_config('app.current_team_id', :t, true) inside the read transaction"
    - "Pattern from github.py:144-152 (list_repos_endpoint): site-membership probe FIRST; cross-team site_id → 404 site_not_found_or_no_access (avoids existence-leak per T-11-04-01)"
    - "DISTINCT ON (firewall_id) ORDER BY firewall_id, snapshot_ts DESC against ix_fw_ruleset_latest (D-11)"
    - "N+0 child fetch — one IN-list query per kind (rules / nat_rules / objects), grouped by snapshot_id in Python"
    - "FirewallSnapshotResponse Pydantic envelope reuses FirewallRule / FirewallNATRule / FirewallObject inner models from app.schemas.firewall (zero schema duplication; push and read share the same shapes)"
    - "Pattern G logging allowlist: team_id / site_id / snapshot_count only — no rule contents"
    - "snapshot_ts ISO formatting with trailing-Z normalization (matches push-side wire contract)"
key-files:
  created:
    - backend/app/routes/firewalls.py
    - .planning/phases/11-firewall-integration/deferred-items.md
    - .planning/phases/11-firewall-integration/11-04-SUMMARY.md
  modified:
    - backend/app/main.py
    - backend/tests/conftest.py
decisions:
  - "Site-membership probe is the FIRST query inside the RLS transaction — running it before the snapshot DISTINCT ON means a cross-team site_id consumes one trivial index probe and returns 404 without scanning firewall_ruleset_snapshots at all. Mirrors github.py:144-152 verbatim so future readers immediately recognise the pattern."
  - "404 (not 403) on cross-team site_id — same posture as Phase 7.5 install/repo lookup. 403 would distinguish 'exists-elsewhere' from 'does-not-exist' and leak the boundary of foreign teams' site inventories; 404 keeps both branches indistinguishable to the caller."
  - "DISTINCT ON over a subquery aggregate — DISTINCT ON is the minimal SQL primitive that maps directly to the ix_fw_ruleset_latest composite index (site_id, firewall_id, snapshot_ts DESC) created in Plan 11-02. A window-function alternative (ROW_NUMBER() OVER (PARTITION BY firewall_id ORDER BY snapshot_ts DESC)) would scan every snapshot before filtering — same correctness, worse plan."
  - "Children fetched in 3 IN-list queries (N+0 not N+3) — one round-trip per kind covers every latest snapshot, grouped by snapshot_id on the Python side. Switching to a JOIN-based query was rejected because the Cartesian product of three child tables against the snapshot parent would explode the result set; per-kind queries each return ≤ 50000 rows per snapshot (T-11-02-01 bound) and groupby in Python is O(n) on a single-team result set."
  - "snapshot_ts emitted via `.isoformat().replace('+00:00', 'Z')` so the read response matches the agent's RFC3339-with-Z wire form (Plan 11-03 parses RFC3339-with-Z on the push side via `datetime.fromisoformat(s.replace('Z', '+00:00'))`). Round-trip equivalence: agent push string → DB timestamptz → read response string is byte-identical for the agent's emit format."
  - "FirewallSnapshotResponse is a local Pydantic model on the route (not promoted to app.schemas.firewall) because no other module reads firewall snapshots back today. Promotion is one Edit away if Phase 12 ever consumes the read API (it shouldn't — Phase 12 will query the DB directly per CONTEXT D-11)."
  - "Rule 3 deviation — fixed the firewall_snapshot fixture (Plan 11-01) which used ':ts::timestamptz'. SQLAlchemy's bindparam parser mis-tokenises the leading colon of '::' as a bindparam delimiter and asyncpg gets a malformed query. Switched to plain ':ts' binding plus a Python-side datetime.fromisoformat parse so asyncpg receives a real datetime for the timestamptz column. The fixture had never been exercised before Plan 11-04 (read tests were RED on the missing module), so this defect surfaced only now."
metrics:
  duration_minutes: 14
  tasks_completed: 2
  files_created: 1   # backend/app/routes/firewalls.py
  files_modified: 2  # backend/app/main.py + backend/tests/conftest.py
  total_files: 3
  completed_date: "2026-05-12"
---

# Phase 11 Plan 04: Backend Firewall Read API (Pattern B + Site-Membership Probe) Summary

`GET /v1/sites/{site_id}/firewall-rules` lands — the read half of ROADMAP success criterion 4 ("All rule sets visible in cloud backend, tied to team + site"). Clerk-JWT-authenticated, RLS-scoped via `app.current_team_id` GUC (Pattern B), returns the latest snapshot per `firewall_id` (D-11) with attached rules + nat_rules + objects. Cross-team `site_id` returns 404 before any work happens (T-11-04-01 mitigation, mirrors `github.py:144-152` `list_repos_endpoint`).

## What Was Built

### Task 1 — `backend/app/routes/firewalls.py` (commit `dc87f5b`)

`backend/app/routes/firewalls.py` (227 lines, single new file):

| Symbol | Role |
| ------ | ---- |
| `router = APIRouter(prefix="/v1", tags=["firewalls"])` | New router; `{site_id}` path param means the prefix is just `/v1` |
| `_READ_ROLES = ("owner", "admin", "member", "basic_member")` | Read-role gate; verbatim copy of github.py value |
| `class FirewallSnapshotResponse(BaseModel)` | Per-device envelope: snapshot_id / site_id / firewall_id / vendor / source / snapshot_ts + `rules: list[FirewallRule]` + `nat_rules: list[FirewallNATRule]` + `objects: list[FirewallObject]` |
| `async def get_site_firewall_rules(site_id, principal, team)` | The single handler |

The handler flow inside `async with sm() as session, session.begin():`:

1. `set_config('app.current_team_id', :t, true)` (Pattern B — RLS GUC set as the first statement so every subsequent query is team-scoped).
2. Site-membership probe — `select(DCSite.id).where(DCSite.id == site_id)`. Under RLS, this resolves to None for any cross-team `site_id`. None → raise `HTTPException(404, "site_not_found_or_no_access")` (Pattern from `github.py:144-152`).
3. `DISTINCT ON (firewall_id) ORDER BY firewall_id, snapshot_ts DESC` text-SQL query against `firewall_ruleset_snapshots` filtered by `site_id`. Uses the `ix_fw_ruleset_latest (site_id, firewall_id, snapshot_ts DESC)` index from Plan 11-02 migration 011 — index-only DISTINCT ON.
4. Empty result → log `firewall_rules_listed` with `snapshot_count=0`, return `[]` (test_returns_latest_per_device covers this only indirectly; test_cross_team_isolation explicitly exercises it).
5. For each of the three child tables, one IN-list query against `snapshot_id` — `FirewallRuleORM` ordered by `(snapshot_id, position)`, `FirewallNATRuleORM` same, `FirewallObjectORM` by `(snapshot_id, kind, name)`. Three round-trips, not 3×N, so the read cost is O(snapshots + child-rows).
6. Children grouped into `dict[uuid.UUID, list[...]]` by `snapshot_id` on the Python side using `setdefault` for branch-free insertion.
7. Single `_log.info("firewall_rules_listed", team_id, site_id, snapshot_count)` — Pattern G allowlist; no rule contents.
8. Return list comprehension projecting each snapshot row into `FirewallSnapshotResponse(...)`. `snapshot_ts` emitted via `.isoformat().replace("+00:00", "Z")` so the response matches the agent's RFC3339-with-Z wire form (Plan 11-03's push side normalises the inverse).

Imports added:
- `uuid` (for the `site_id: uuid.UUID` path-param coercion)
- `structlog` (`_log = structlog.get_logger("app.firewalls")`)
- `fastapi.{APIRouter, Depends, HTTPException, status}`
- `pydantic.BaseModel`
- `sqlalchemy.{select, text}`
- `app.auth.clerk.{ClerkPrincipal, require_role}` (Pattern B)
- `app.auth.deps.resolve_team_from_clerk_org` (Pattern B)
- `app.db.models.{DCSite, FirewallNATRuleORM, FirewallObjectORM, FirewallRuleORM, Team}`
- `app.db.session.get_sessionmaker`
- `app.schemas.firewall.{FirewallNATRule, FirewallObject, FirewallRule}` (reused inner Pydantic shapes — zero duplication with the push side)

### Task 2 — Router wired into main.py + Rule 3 conftest fixture fix (commit `1b35a97`)

`backend/app/main.py` — exactly two new lines:

```python
from app.routes import firewalls as firewalls_routes  # in the imports block
...
    app.include_router(firewalls_routes.router)        # in create_app, after agent_routes
```

Placement follows PATTERNS.md §"backend/app/main.py" verbatim — import added in the alphabetical run of `from app.routes import ... as ..._routes` lines, `include_router` call appended after the existing `agent_routes` include.

`backend/tests/conftest.py` — Rule 3 deviation, see below.

**Wave 0 read tests turn GREEN:**

```
$ pytest tests/test_routes_firewall_read.py --no-cov -v
tests/test_routes_firewall_read.py::test_returns_latest_per_device PASSED [ 33%]
tests/test_routes_firewall_read.py::test_cross_team_isolation       PASSED [ 66%]
tests/test_routes_firewall_read.py::test_requires_clerk_jwt         PASSED [100%]
3 passed in 6.51s
```

Each test exercises one acceptance lever:

- **`test_returns_latest_per_device`** (D-11) — seeds two snapshots for `firewall_id=asa-edge-01` at `06:00Z` and `07:00Z`; asserts the read returns exactly one snapshot envelope for that device with `snapshot_ts == "2026-05-12T07:00:00Z"` and `len(rules) == 7` (the newer snapshot has 7 rules; the older had 5). DISTINCT ON wins; the older snapshot is correctly hidden.
- **`test_cross_team_isolation`** (T-11-04-01) — seeds a snapshot under Team B, queries the corresponding `site_id` with Team A's Clerk JWT, asserts response is either `404` or `[]` and never contains Team B's data. Handler returns `404 site_not_found_or_no_access` because RLS hides Team B's site from Team A's `DCSite` probe.
- **`test_requires_clerk_jwt`** (Pattern B) — unauthenticated `GET /v1/sites/{uuid}/firewall-rules` returns `401`. Previously returned `404 Not Found` because the route wasn't mounted; mounting the router in Task 2 surfaces the Clerk dependency's 401 response correctly.

## Decisions Made

Captured in frontmatter `decisions:`. Highlights:

1. **Site-membership probe FIRST inside the RLS transaction** — runs before the snapshot scan. Cross-team `site_id` consumes one trivial index probe and returns 404 without touching `firewall_ruleset_snapshots`. Mirrors `github.py:144-152` so the pattern is immediately recognisable.
2. **404 not 403 on cross-team** — same posture as Phase 7.5. 403 would leak the existence boundary of foreign teams' site inventories.
3. **DISTINCT ON over window-function** — DISTINCT ON maps directly to the `ix_fw_ruleset_latest` composite index Plan 11-02 created. A `ROW_NUMBER() OVER (PARTITION BY firewall_id ORDER BY snapshot_ts DESC)` alternative would scan every snapshot before filtering.
4. **N+0 children via three IN-list queries** — one round-trip per kind. A JOIN against three child tables in one query would Cartesian-product the result.
5. **snapshot_ts emitted as RFC3339-with-Z** — `.isoformat().replace("+00:00", "Z")`. Round-trip equivalence with the agent push side preserved.
6. **FirewallSnapshotResponse stays local to the route** — no other module reads firewall snapshots today. Promotion to `schemas/firewall.py` is one Edit away if Phase 12 ever needs it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Fixed `firewall_snapshot` fixture timestamptz binding**

- **Found during:** Task 2 verification — `pytest tests/test_routes_firewall_read.py` first run, after main.py was wired.
- **Issue:** The `firewall_snapshot` fixture from Plan 11-01 used `:ts::timestamptz` in a raw SQL string. SQLAlchemy's bindparam parser mis-tokenises the leading colon of the `::` PostgreSQL cast operator as a bindparam delimiter, so asyncpg receives a malformed query (`"... VALUES (..., :ts::timestamptz)"` with `:ts` bound but `::timestamptz` left as literal-with-stray-colon). Error: `asyncpg.exceptions.PostgresSyntaxError: syntax error at or near ":"`. After fixing the cast syntax, a second error surfaced: `asyncpg.exceptions.DataError: invalid input for query argument $5: '2026-05-12T07:00:00Z' (expected a datetime.date or datetime.datetime instance, got 'str')` — asyncpg requires a real `datetime` for a timestamptz column, not a string.
- **Why it surfaced now:** The fixture was authored under Plan 11-01 as Wave 0 RED scaffolding. The two tests that exercise it (`test_returns_latest_per_device`, `test_cross_team_isolation`) were collection-RED on `app.routes.firewalls` not existing until Plan 11-04 Task 1, so the fixture body was never run end-to-end. Plan 11-04 Task 2 is the first invocation.
- **Fix (two-step):**
  1. Replaced `:ts::timestamptz` with plain `:ts` binding (no Postgres cast in the SQL).
  2. Added `from datetime import datetime as _datetime` import and changed the parameter dict to bind `"ts": _datetime.fromisoformat(snap["snapshot_ts"].replace("Z", "+00:00"))` — Python-side ISO parse with the Phase 11-03 `Z → +00:00` normalisation.
- **Files modified:** `backend/tests/conftest.py` (one import + one fixture body edit).
- **Commit:** `1b35a97` (bundled with the main.py router wiring — both edits are part of "make Wave 0 read tests GREEN").
- **Rule classification:** Rule 3 (auto-fix blocking issue). The fixture is test infrastructure created by an earlier plan, exercised for the first time by this plan; the fix is required to satisfy Plan 11-04's own Wave 0 verification.

No other deviations.

## Authentication Gates

None encountered. The route is auth-gated via `Depends(require_role(*_READ_ROLES))` — Phase 4 / Phase 7.5 had already operationalised Clerk JWT verification; Plan 11-04 reuses the dependency verbatim.

## Known Stubs

None. The handler is production-shape — returns real DB rows, real per-device latest-snapshot semantics, real RLS isolation. No placeholder TODO / FIXME markers introduced.

## TDD Gate Compliance

This plan is `type=execute` with `tdd="true"` on both tasks. Wave 0 plan 11-01 committed the RED gate (`6a8a9d4` — `tests/test_routes_firewall_read.py` references `app.routes.firewalls` which did not exist; collection-RED). Plan 11-04 closes the GREEN gate.

| Gate     | Commit       | Status |
| -------- | ------------ | ------ |
| RED      | `6a8a9d4` (Plan 11-01) | Pre-landed — module + route missing; tests collection-RED |
| GREEN    | `dc87f5b`, `1b35a97` | Task 1 lands the handler; Task 2 wires the router AND fixes the Wave 0 fixture so all 3 read tests pass |
| REFACTOR | (none required) | No follow-up clean-up needed — Task 1 wrote the handler in its final shape |

The strict gate ordering is preserved: Task 1's commit (`dc87f5b`) added a handler that was correct but unreachable (no router include); Task 2's commit (`1b35a97`) wired the router AND ran the suite GREEN. The fixture fix is bundled into Task 2's GREEN commit because it is a prerequisite for the Wave 0 tests passing — splitting it out would have left a state where Task 1's handler was correct but the tests still failed for an unrelated infrastructure reason.

## Verification

### Automated checks performed

```bash
# Task 1 acceptance greps — all match planned values
F=backend/app/routes/firewalls.py
grep -c 'async def get_site_firewall_rules' $F                # 1 (expect 1)
grep -c '/sites/{site_id}/firewall-rules' $F                  # 2 — handler decorator + docstring (expect >= 1)
grep -c 'Depends(require_role' $F                              # 2 — handler + docstring (expect 1)
grep -c 'resolve_team_from_clerk_org' $F                       # 3 — import + dep + docstring (expect >= 1)
grep -cF "set_config('app.current_team_id'" $F                 # 2 — code + docstring (expect 1)
grep -c 'site_not_found_or_no_access' $F                       # 3 — code + 2 docstrings (expect 1)
grep -c 'DISTINCT ON' $F                                       # 3 — SQL + 2 docstrings (expect 1)
grep -c 'class FirewallSnapshotResponse' $F                    # 1 (expect 1)

# Task 2 acceptance greps
grep -c 'from app.routes import firewalls as firewalls_routes' backend/app/main.py  # 1 (expect 1)
grep -c 'app.include_router(firewalls_routes.router)' backend/app/main.py           # 1 (expect 1)

# Router shape sanity
python -c "from app.routes.firewalls import router; print(router.routes[0].path)"
# /v1/sites/{site_id}/firewall-rules

# Wave 0 read-test suite — full GREEN
cd backend && PATH=.venv/bin:$PATH .venv/bin/python -m pytest \
  tests/test_routes_firewall_read.py --no-cov -v
# 3 passed in 6.51s

# Phase 11 + Phase 10 push-side regression
cd backend && PATH=.venv/bin:$PATH .venv/bin/python -m pytest \
  tests/test_routes_firewall.py tests/test_agent.py --no-cov
# 13 passed in 8.14s

# Full backend suite — 203 passed, 4 deselected (all pre-existing — see "Deferred Issues" below)
cd backend && PATH=.venv/bin:$PATH .venv/bin/python -m pytest --no-cov \
  --deselect tests/jobs/test_scan_repo.py::test_scan_rc1_treated_as_success \
  --deselect tests/test_services_scans.py::test_finalize_scan_updates_pending_to_ready_and_fires_meter \
  --deselect tests/test_services_scans.py::test_finalize_scan_idempotent_when_already_ready \
  --deselect tests/test_services_scans.py::test_finalize_scan_propagates_stripe_error
# 203 passed, 4 deselected

# Lint + mypy strict
cd backend && PATH=.venv/bin:$PATH .venv/bin/ruff check app/routes/firewalls.py app/main.py tests/conftest.py
# All checks passed!
cd backend && PATH=.venv/bin:$PATH .venv/bin/mypy app/routes/firewalls.py app/main.py
# Success: no issues found in 2 source files
```

All acceptance-criterion greps match planned values. All 3 Wave 0 read tests turned GREEN. No NEW regression — the 4 deselected failures all pre-exist on parent commit `dc87f5b` (verified via `git stash && pytest <failing-test>`); documented under "Deferred Issues" below.

## Deferred Issues

Out-of-scope failures that pre-existed on parent commit `dc87f5b`, surfaced during the Plan 11-04 full-suite regression sweep, and are NOT introduced by Plan 11-04 changes. Logged in `.planning/phases/11-firewall-integration/deferred-items.md`:

- **DEF-11-04-01** — `tests/jobs/test_scan_repo.py::test_scan_rc1_treated_as_success` fails with `AttributeError: 'str' object has no attribute 'get'` inside `app.queue.tasks.scan_repo` (Phase 6/7 module untouched by Plan 11-04). Verified pre-existing on parent commit.
- **DEF-11-04-02** — `tests/test_services_scans.py` finalize_scan trio (3 tests) fails. `app.services.scans` is a Phase 7 module untouched by Plan 11-04. Verified pre-existing on parent commit.

Per executor SCOPE BOUNDARY rule, only auto-fix issues directly caused by the current task's changes. Both failures are in unrelated Phase 6/7 modules; deferred to the next plan that touches those modules.

## Commits

| Commit    | Type | Summary                                                                       | Files |
| --------- | ---- | ----------------------------------------------------------------------------- | ----- |
| `dc87f5b` | feat | add GET /v1/sites/{site_id}/firewall-rules read API (new routes/firewalls.py) | 1     |
| `1b35a97` | feat | wire firewalls router into main.py + fix Wave 0 firewall_snapshot fixture     | 2     |

## Self-Check: PASSED

- `backend/app/routes/firewalls.py` exists (`dc87f5b`) ✓
- `backend/app/main.py` modified (`1b35a97`) ✓
- `backend/tests/conftest.py` modified (`1b35a97`) ✓
- `git log --oneline | grep -E 'dc87f5b|1b35a97'` returns both commits ✓
- `async def get_site_firewall_rules` present (grep == 1) ✓
- `Depends(require_role(*_READ_ROLES))` on the handler (Pattern B) ✓
- `set_config('app.current_team_id'` inside the read transaction (Pattern B) ✓
- Site-membership probe runs FIRST (Pattern from github.py:144-152) ✓
- `site_not_found_or_no_access` 404 reason emitted (T-11-04-01) ✓
- `DISTINCT ON` query against `firewall_ruleset_snapshots` (D-11) ✓
- `class FirewallSnapshotResponse` envelope with rules + nat_rules + objects (D-11) ✓
- `app.include_router(firewalls_routes.router)` in main.py ✓
- 3/3 Wave 0 read tests GREEN ✓
- Phase 11 push-side (5/5) + Phase 10 agent (8/8) regression GREEN ✓
- 203 / 203 non-deselected tests GREEN in full backend suite ✓
- `ruff check` + `mypy --strict` clean on all touched files ✓

## Next Plan

Wave 2 has one plan remaining: **11-07** (4th agent ticker `Firewall: 1*time.Hour` + `Pusher` interface extension + `collectAndPushFirewall` stub). With Plan 11-04 closed:

- Backend ingest (Plans 11-02 + 11-03) and backend read (Plan 11-04) are both operational against live Postgres — the backend slice of Phase 11 is **feature-complete** for the rule-base data path.
- Plan 11-07 is the last Wave 2 prerequisite for Wave 3 per-vendor collectors (`asa.RESTCollector`, `asa.SSHCollector`, `fmc.Collector`, `checkpoint.LiveCollector`).
- ROADMAP success criterion 4 ("All rule sets visible in cloud backend, tied to team + site") is **demonstrable** today via:
  1. Agent pushes a snapshot (Plan 11-03 endpoints) with site-token Bearer.
  2. Dashboard / operator GETs `/v1/sites/{site_id}/firewall-rules` (Plan 11-04 endpoint) with a Clerk JWT.
  3. The snapshot appears, scoped to the caller's team, with rules + nat_rules + objects.

Wave 3 collectors (11-08..11-11) unblock as soon as 11-07 lands the agent-side dispatch surface.
