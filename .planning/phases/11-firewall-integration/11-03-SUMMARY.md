---
phase: 11
plan: 03
subsystem: firewall-integration
tags: [wave-2, backend, fastapi, push-handlers, rls, idempotent, site-token]
requires:
  - phase-11-plan-02-summary       # Pydantic schemas + ORM models + migration 011
  - phase-10-plan-02-summary       # require_site_token + DCSitePrincipal (Pattern A reuse)
provides:
  - firewall-push-handlers          # 3 new POST endpoints persisting parent + children
  - pattern-e-implementation        # ON CONFLICT DO NOTHING on snapshot_id (idempotent)
  - pattern-b-applied               # set_config('app.current_team_id', :t, true) per-handler
affects:
  - backend/app/routes/agent.py     # +3 handlers + 1 helper + new imports
tech-stack:
  added: []  # no new dependencies; uses existing sqlalchemy.dialects.postgresql.insert
  patterns:
    - "Phase 10 require_site_token + DCSitePrincipal reuse (Pattern A) — zero new auth code"
    - "Pattern B RLS GUC-set inside transaction (mirrors Phase 10 create_site)"
    - "Pattern E idempotent parent insert via pg_insert(...).on_conflict_do_nothing(index_elements=['snapshot_id'])"
    - "Shared _upsert_snapshot_parent helper avoids 3-way duplication of parent-insert logic"
    - "Bulk child insert via pg_insert(Model).values([dict, ...]) — asyncpg-friendly"
    - "Pattern G credential allowlist — handlers log only site_id/team_id/snapshot_id/firewall_id/vendor/source/count"
    - "ISO 8601 snapshot_ts parsed via datetime.fromisoformat with Z→+00:00 normalization"
    - "uuid.uuid4() for child PKs at insert time (no natural-key collision on retry — accepted residual T-11-03-04)"
key-files:
  created: []
  modified:
    - backend/app/routes/agent.py
decisions:
  - "Single shared helper _upsert_snapshot_parent over body-typed union (FirewallRulesPushBody | FirewallNATPushBody | FirewallObjectsPushBody) — the parent-snapshot envelope is the same shape across all three, and a helper keeps the on_conflict_do_nothing call site DRY (one source of truth for the Pattern E semantics, easier to evolve under future migration constraints)"
  - "snapshot_ts parsed inline via datetime.fromisoformat(body.snapshot_ts.replace('Z', '+00:00')) rather than upgrading the Pydantic schema to datetime — keeps the wire contract a string (D-15 Phase 12 forward-feed lock unchanged) and pushes the ISO parse to a single helper call. fromisoformat ('Z' → '+00:00') is sufficient because the agent only emits trailing-Z RFC3339"
  - "principal.team_id is a str on DCSitePrincipal (Phase 10 Pydantic shape), not a UUID — cast via uuid.UUID(...) once at the parent-insert call site rather than re-typing the principal. Avoids cross-phase ORM type churn"
  - "Child bulk insert uses pg_insert(...).values([dict, ...]) form rather than session.add_all(...) — keeps the same async dialect insert primitive as the parent and lets the SQL be a single round-trip (matches the existing Phase 10 create_site pattern where pg_insert + .values is the canonical async form)"
  - "uuid.uuid4() generated for rule_id/nat_id/object_id at handler call time rather than relying on the ORM default — explicit IDs in the bulk-values dict are required because pg_insert(...).values(list_of_dicts) does not consult ORM column defaults. T-11-03-04 residual (child re-insert on partial-fail retry may produce duplicate child rows) accepted per plan threat model"
  - "Three independent handlers (not a single dispatcher) — each endpoint is a distinct path with its own Pydantic body type, matching D-18 (three endpoints sharing one snapshot_id) and keeping the Pattern E ordering guarantee provable per-endpoint in tests"
metrics:
  duration_minutes: 12
  tasks_completed: 1
  files_created: 0
  files_modified: 1
  total_files: 1
  completed_date: "2026-05-12"
---

# Phase 11 Plan 03: Three Firewall Push Handlers (Pattern A + B + E) Summary

Backend ingest half of ROADMAP success criterion 4 ("All rule sets visible in cloud backend") lands. Three FastAPI handlers added to `backend/app/routes/agent.py` — `push_firewall_rules` / `push_firewall_nat` / `push_firewall_objects` — each reusing Phase 10 `require_site_token` (Pattern A), setting the `app.current_team_id` RLS GUC inside its transaction (Pattern B), and idempotently upserting the parent `FirewallRulesetSnapshot` row via `ON CONFLICT DO NOTHING` on `snapshot_id` (Pattern E). The plan's Wave 0 push tests flip from collection-clean / runtime-RED to fully GREEN; Phase 10 push handlers preserved verbatim.

## What Was Built

### Task 1 — Three push handlers + shared parent-upsert helper (commit `05f1158`)

`backend/app/routes/agent.py` extended by 216 lines (5 removed, 221 added — module docstring + import block + 3 handlers + 1 helper):

| Endpoint                          | Body                       | Children written           | Lines |
| --------------------------------- | -------------------------- | -------------------------- | ----- |
| `POST /v1/agent/firewall-rules`   | `FirewallRulesPushBody`    | `FirewallRuleORM`          | ~43   |
| `POST /v1/agent/firewall-nat`     | `FirewallNATPushBody`      | `FirewallNATRuleORM`       | ~40   |
| `POST /v1/agent/firewall-objects` | `FirewallObjectsPushBody`  | `FirewallObjectORM`        | ~38   |

Each handler opens `async with sm() as session, session.begin():`, sets the RLS GUC via parameterized `SELECT set_config('app.current_team_id', :t, true)`, calls the shared `_upsert_snapshot_parent` helper, then bulk-inserts the children via `pg_insert(<Model>).values([{...}, ...])`. Status code `202 Accepted` on success; FastAPI returns `422 Unprocessable Entity` on body-validation failure; `require_site_token` returns `401 missing_bearer` / `401 invalid_bearer` on auth failure.

The shared `_upsert_snapshot_parent(session, body, principal)` helper builds an idempotent parent insert. The body parameter type is the union `FirewallRulesPushBody | FirewallNATPushBody | FirewallObjectsPushBody` — all three carry the same parent-envelope fields (`site_id`, `snapshot_id`, `firewall_id`, `vendor`, `source`, `snapshot_ts`), so the helper is a single source of truth for the Pattern E semantics:

```python
stmt = (
    pg_insert(FirewallRulesetSnapshot)
    .values(
        snapshot_id=uuid.UUID(body.snapshot_id),
        team_id=uuid.UUID(principal.team_id),
        site_id=uuid.UUID(body.site_id),
        firewall_id=body.firewall_id,
        vendor=body.vendor,
        source=body.source,
        snapshot_ts=snapshot_ts,  # parsed via datetime.fromisoformat
    )
    .on_conflict_do_nothing(index_elements=["snapshot_id"])
)
await session.execute(stmt)
```

`snapshot_ts` is parsed inline via `datetime.fromisoformat(body.snapshot_ts.replace("Z", "+00:00"))` because the agent emits RFC3339-with-Z and Python's `fromisoformat` only accepts `+00:00` form pre-3.11. This is the only place an ISO parse happens for the firewall surface — child tables don't carry a snapshot_ts column.

Pattern G credential allowlist enforced at log sites: structlog fields are `site_id`, `team_id`, `snapshot_id`, `firewall_id`, `vendor`, `source`, `count` only. The handler bodies contain zero references to `password`, `\bsid\b`, or `\btoken\b` (grep-verified — see Verification §"Pattern G grep" below).

Module docstring (lines 1-21) extended with the three new endpoint paths in the route table + Phase 11 security-posture bullets (T-11-02-01 payload bound reminder + Pattern B/E inline references).

Imports extended with:
- `import uuid` + `from datetime import datetime` — for ID + timestamp work
- `from sqlalchemy.dialects.postgresql import insert as pg_insert` — async-friendly idempotent insert primitive
- `from sqlalchemy.ext.asyncio import AsyncSession` — type-hint for the helper's `session` parameter (mypy strict)
- 4 new ORM classes from `app.db.models` (`FirewallRulesetSnapshot`, `FirewallRuleORM`, `FirewallNATRuleORM`, `FirewallObjectORM`)
- 3 new push body schemas from `app.schemas.firewall`

Existing Phase 10 `create_site` / `push_routes` / `push_flows` handlers preserved verbatim — no edits, no reorderings.

## Decisions Made

Captured in frontmatter `decisions:`. Highlights:

1. **One shared helper for parent upsert** — the snapshot envelope is identical across the three push bodies, so a single `_upsert_snapshot_parent(session, body, principal)` keeps the `on_conflict_do_nothing(index_elements=["snapshot_id"])` call DRY. Three callers, one Pattern E implementation. Easier to evolve if the parent contract changes (a future column addition is one edit, not three).
2. **Inline ISO 8601 parse** — `datetime.fromisoformat(body.snapshot_ts.replace("Z", "+00:00"))` rather than upgrading the Pydantic field to `datetime`. The wire contract stays a string (D-15 forward-feed lock unchanged) and the parse happens in one place. The `Z → +00:00` workaround is a known fromisoformat quirk on Python <3.11 and harmless on 3.12+.
3. **principal.team_id stays a str** — DCSitePrincipal was modeled in Phase 10 with `team_id: str`. Casting via `uuid.UUID(principal.team_id)` at the insert call site is the minimal change. Re-typing the principal would touch every Phase 10 consumer and isn't justified for the one new use site.
4. **Bulk child insert via `pg_insert(...).values([...])` not `session.add_all(...)`** — matches the existing Phase 10 `create_site` shape (`session.execute(insert(DCSite).values(...))`) and stays a single-round-trip SQL call. Explicit child IDs (`uuid.uuid4()` per dict) are required because `pg_insert + .values(list_of_dicts)` does not consult ORM column defaults.
5. **Three independent handlers, not one dispatcher** — D-18 explicitly defines three endpoints sharing one snapshot_id. A dispatcher with a `kind` query param would have collapsed three FastAPI routes into one, breaking the Pydantic-per-route discriminator and making the Pattern E ordering guarantee harder to assert in tests.

## Deviations from Plan

None — plan executed exactly as written.

The plan's `<action>` block prescribed the helper signature, the three handler shapes, and the import additions. All landed verbatim with one stylistic adaptation: the `pg_insert` call site is wrapped in a parenthesized chain (`stmt = (pg_insert(...).values(...).on_conflict_do_nothing(...))`) rather than a single long line, to keep line length under 100 columns per Ruff config. The SQL semantics are identical.

The plan's `<verify>` block called for `cd backend && pytest tests/test_routes_firewall.py -x -v 2>&1 | tail -25`. Executed verbatim; 5/5 tests pass.

## Authentication Gates

None encountered. The handlers themselves are auth-gated via `Depends(require_site_token)` — the Phase 10 dependency was already operational and required no new credentials for this plan to execute.

## Known Stubs

None. All three handlers are production-shape (parent + children persisted, logs emitted, 202 returned). No placeholder TODO/FIXME markers introduced.

## TDD Gate Compliance

This plan is `type=execute` with `tdd="true"` on its single task. The Wave 0 plan (11-01) committed the RED gate; this plan's commit (`05f1158`) is the GREEN gate. No REFACTOR commit was needed — the implementation matched the plan's prescribed shape on the first pass.

| Gate     | Commit       | Status |
| -------- | ------------ | ------ |
| RED      | `6a8a9d4` (Plan 11-01) | Pre-landed — `tests/test_routes_firewall.py` references three handlers that did not exist; Plan 11-02 made imports resolve but runtime stayed RED |
| GREEN    | `05f1158`    | 3 handlers + 1 helper added; 5/5 push tests pass; Phase 10 `test_agent.py` regression: 8 passed; ruff + mypy strict clean |
| REFACTOR | (none required) | No follow-up clean-up needed — helper extraction was part of the GREEN commit, not a post-GREEN refactor |

## Verification

### Automated checks performed

```bash
# Acceptance criterion greps — all match planned values
F=backend/app/routes/agent.py
grep -c 'async def push_firewall_rules\|async def push_firewall_nat\|async def push_firewall_objects' $F  # 3 (expect == 3)
grep -c '/agent/firewall-rules\|/agent/firewall-nat\|/agent/firewall-objects' $F                          # 6 (expect >= 3 — path literals appear in @router.post + docstring routes)
grep -c 'Depends(require_site_token)' $F                                                                  # 5 (expect >= 5 — existing 2 + new 3)
grep -c 'on_conflict_do_nothing' $F                                                                       # 1 (expect >= 1 — Pattern E one site, used by helper)
grep -c "set_config('app.current_team_id'" $F                                                             # 4 (expect >= 3 — Phase 10 create_site + 3 new handlers)
grep -c 'def push_routes\|def push_flows' $F                                                              # 2 (expect >= 2 — Phase 10 handlers preserved)

# Pattern G grep — no credential field names inside firewall handler bodies
for handler in push_firewall_rules push_firewall_nat push_firewall_objects; do
  awk "/^async def $handler/,/^@router\.post|^async def [^_]/" $F | grep -cE 'password|\bsid\b|\btoken\b'
done
# 0
# 0
# 0

# Push-test suite — full GREEN
cd backend && PATH=.venv/bin:$PATH .venv/bin/python -m pytest tests/test_routes_firewall.py --no-cov
# 5 passed in 7.09s
#  - test_push_rejects_missing_bearer       (Pattern A reuse — 401 missing_bearer)
#  - test_push_firewall_rules_writes_snapshot_and_rules  (D-08/D-18 — parent + child written)
#  - test_idempotent_snapshot_id            (Pattern E — second push noop on parent)
#  - test_three_endpoints_share_snapshot_id (D-18 — any-order, parent once across 3 pushes)
#  - test_push_firewall_objects_persists    (D-09 — kind + value JSONB round-trip)

# Phase 10 regression — Phase 10 push handlers untouched
cd backend && PATH=.venv/bin:$PATH .venv/bin/python -m pytest tests/test_agent.py --no-cov
# 8 passed in 7.35s

# Lint + mypy strict
cd backend && .venv/bin/ruff check app/routes/agent.py
# All checks passed!
cd backend && .venv/bin/mypy app/routes/agent.py
# Success: no issues found in 1 source file
```

All acceptance-criterion greps match planned values. All 5 Wave 0 push tests turned GREEN. No Phase 10 regression.

### Environment notes

Tests require Python 3.12 (project floor); the system `python` is 3.11 and pre-existing — execution used the project's `.venv` (Python 3.12.13) with `PATH=.venv/bin:$PATH` so testcontainers' `alembic` invocation resolves correctly. The pg_container fixture pulled `postgres:16-alpine` + `testcontainers/ryuk:0.8.1` and exercised migration `011_firewall_tables` end-to-end for the first time — RLS GUC-set + ON CONFLICT DO NOTHING both worked first-pass against the live Postgres, validating the Plan 11-02 migration shape.

## Commits

| Commit    | Type | Summary                                                                       | Files |
| --------- | ---- | ----------------------------------------------------------------------------- | ----- |
| `05f1158` | feat | 3 firewall push handlers reusing Phase 10 site-token auth + Pattern B + E    | 1     |

## Self-Check: PASSED

- `backend/app/routes/agent.py` modified (`05f1158`) ✓
- `git log --oneline | grep 05f1158` returns the commit ✓
- 3 new `async def push_firewall_*` handlers present (grep == 3) ✓
- Pattern A reused — `Depends(require_site_token)` on each new handler (grep == 5 total, +3 from baseline 2) ✓
- Pattern E applied — `on_conflict_do_nothing` present (grep >= 1) ✓
- Pattern B applied — `set_config('app.current_team_id'` on each new handler (grep == 4 total, +3 from baseline 1) ✓
- Pattern G enforced — handler bodies contain 0 references to `password|sid|token` ✓
- Phase 10 `push_routes` + `push_flows` preserved verbatim (grep == 2) ✓
- `tests/test_routes_firewall.py` 5/5 GREEN ✓
- Phase 10 `tests/test_agent.py` 8/8 GREEN (no regression) ✓
- `ruff check` + `mypy --strict` clean on the modified file ✓
- All acceptance-criterion grep counts match planned values ✓

## Next Plan

`11-04-PLAN.md` — Backend read API (`GET /v1/sites/{site_id}/firewall-rules`, Clerk JWT). With the push half landed and the migration exercised against a live Postgres for the first time, the read half can be implemented against the same RLS GUC pattern (Pattern B) with confidence that the storage shape is correct. After 11-04 closes, Plan 11-07 (4th agent ticker + Pusher interface extension + collectAndPushFirewall stub) becomes the Wave 2 sibling that lets Wave 3 per-vendor collectors land in parallel.
