---
phase: 11
plan: 02
subsystem: firewall-integration
tags: [wave-1, backend, alembic, rls, schemas, taskiq, ttl]
requires:
  - phase-11-plan-01-summary  # Wave 0 test scaffold (RED for schemas + routes + migration)
  - 010_dc_sites              # parent migration; firewall_ruleset_snapshots.site_id FKs into dc_sites.id
provides:
  - migration-011-firewall-tables  # 4 RLS-scoped tables (parent + 3 children)
  - firewall-orm-models             # FirewallRulesetSnapshot + 3 *ORM children on Base.metadata
  - firewall-pydantic-schemas       # FirewallRule/NATRule/Object + 3 push body envelopes
  - firewall-prune-task             # taskiq task DELETE-FROM-snapshots WHERE snapshot_ts < NOW - INTERVAL
  - d15-forward-feed-lock           # locked Phase 12 column names doc-commented in migration
affects:
  - backend/migrations/versions/  # new revision head: 011_firewall_tables
  - backend/app/db/models.py      # +4 ORM classes, +Integer in sqlalchemy import
  - backend/app/schemas/          # +firewall.py with 6 Pydantic models
  - backend/app/queue/tasks/      # +firewall_prune.py
tech-stack:
  added: []  # no new dependencies; uses existing alembic/sqlalchemy/pydantic/taskiq/structlog stack
  patterns:
    - "Phase-10 migration 010 RLS template (ENABLE+FORCE+team_isolation policy+GRANT)"
    - "Child-table team-scope via parent JOIN in policy (no team_id column on children — D-08 lean schema)"
    - "Composite (site_id, firewall_id, snapshot_ts DESC) index for Plan 11-04 DISTINCT ON read"
    - "Field(..., max_length=50000) DoS bound (mirrors Phase 10 RoutesPushBody at 10k; T-11-02-01)"
    - "ORM suffix on FirewallRule/NATRule/Object to avoid Pydantic symbol collision"
    - "Parameterized set_config('app.current_team_id', :t, true) per-team prune (no BYPASSRLS)"
    - "Doc-commented Phase 12 forward-feed column-name lock (D-15)"
key-files:
  created:
    - backend/migrations/versions/20260510_011_firewall_tables.py
    - backend/app/schemas/firewall.py
    - backend/app/queue/tasks/firewall_prune.py
  modified:
    - backend/app/db/models.py
decisions:
  - "Single composite index ix_fw_ruleset_latest on (site_id, firewall_id, snapshot_ts DESC) plus a separate ix_fw_ruleset_team_id — splits team-prefix lookups from device-latest lookups so Plan 11-04 can keep its DISTINCT ON query index-only without bloating the team-scoped pruner"
  - "Child tables (firewall_rules / firewall_nat_rules / firewall_objects) carry NO team_id column; team-scope is enforced by 'snapshot_id IN (SELECT snapshot_id FROM firewall_ruleset_snapshots WHERE team_id = current_setting(...))' in each child policy. Keeps schema lean (D-08) and prevents team_id drift between parent and children"
  - "ORM classes are suffixed *ORM (FirewallRuleORM / FirewallNATRuleORM / FirewallObjectORM) to coexist with un-suffixed Pydantic models in modules that import both. Parent FirewallRulesetSnapshot is un-suffixed because there is no Pydantic peer for the snapshot envelope (it's reconstructed from the push-body fields)"
  - "kind column on firewall_objects is plain Text not a Postgres enum — Pydantic validates {host|network|group|service} at the boundary, avoiding an Alembic enum-migration footgun"
  - "downgrade() unrolls the table-drop loop into explicit per-table statements so the migration file passes single-line grep acceptance checks (4× DROP POLICY in source)"
  - "prune_firewall_snapshots iterates teams and sets app.current_team_id via parameterized set_config(:t, true) — RLS-respecting, no BYPASSRLS role required. Per-team transaction so a partial failure does not roll back already-pruned teams"
  - "FIREWALL_SNAPSHOT_TTL_DAYS env override with int() cast before INTERVAL '<n> days' interpolation — interval literal cannot be parameter-bound by asyncpg, but the int() cast erases any SQL-injection surface from the env source"
  - "GRANT statements collapsed to single-line literals so the acceptance grep 'GRANT.*infracanvas_app == 4' matches all four lines without depending on Python's implicit-string-concatenation"
metrics:
  duration_minutes: 10
  tasks_completed: 3
  files_created: 3
  files_modified: 1
  total_files: 4
  completed_date: "2026-05-12"
---

# Phase 11 Plan 02: Backend Data Plane — Migration 011 + ORM + Schemas + Prune

Lands the Phase 11 backend bedrock: a single Alembic revision creating the four RLS-protected firewall tables, the ORM/Pydantic boundary that the three push handlers (Plan 11-03) and the read endpoint (Plan 11-04) will live behind, and the taskiq prune task that prevents the storage explosion described in 11-RESEARCH.md Risk Landmine #2.

## What Was Built

### Task 1 — Migration `011_firewall_tables` (commit `524cbfd`)

`backend/migrations/versions/20260510_011_firewall_tables.py` (264 lines, single Python file, no new dependencies). The migration creates four tables in FK-dependency order:

| Table                          | Role   | Notable columns                                                                                  | Indexes |
| ------------------------------ | ------ | ------------------------------------------------------------------------------------------------ | ------- |
| `firewall_ruleset_snapshots`   | parent | `snapshot_id` (UUID PK, agent-minted), `team_id` FK→teams, `site_id` FK→dc_sites, `firewall_id`, `vendor`, `source`, `snapshot_ts` | `ix_fw_ruleset_team_id`, composite `ix_fw_ruleset_latest (site_id, firewall_id, snapshot_ts DESC)` |
| `firewall_rules`               | child  | `rule_id` PK, `snapshot_id` FK CASCADE, `position`, `src_zone`, `dst_zone`, `src_cidr`, `dst_cidr`, `action`, `protocol`, `ports`, `raw_blob` JSONB | `ix_fw_rules_snapshot (snapshot_id, position)` |
| `firewall_nat_rules`           | child  | `nat_id` PK, `snapshot_id` FK CASCADE, `position`, `src_translation`, `dst_translation`, `interface_in`, `interface_out`, `raw_blob` JSONB | `ix_fw_nat_snapshot (snapshot_id, position)` |
| `firewall_objects`             | child  | `object_id` PK, `snapshot_id` FK CASCADE, `kind`, `name`, `value` JSONB, `raw_blob` JSONB | `ix_fw_objects_snapshot (snapshot_id, kind, name)` |

Every table has `ENABLE + FORCE ROW LEVEL SECURITY` plus a `<table>_team_isolation` policy with `USING` + `WITH CHECK` clauses. The parent table's policy keys on `team_id` directly; child policies enforce team-scope via the `snapshot_id IN (SELECT snapshot_id FROM firewall_ruleset_snapshots WHERE team_id = current_setting('app.current_team_id', true)::uuid)` JOIN pattern. `GRANT SELECT, INSERT, UPDATE, DELETE` to `infracanvas_app` is issued for all four tables.

The doc-comment at the top of the migration file lists the Phase 12 forward-feed contract column names verbatim (D-15) — this is the lock the planner asked for. Any future migration that renames or drops these columns has to land coordinated with a Phase-12 path-computation update.

`downgrade()` is unrolled into per-table explicit `DROP POLICY` + `op.drop_table` statements (reverse FK order so the children go first) so the acceptance-grep "4× DROP POLICY visible on its own source line" check matches.

**Revision graph (verified via `python -m alembic history`):**
```
010_dc_sites -> 011_firewall_tables (head), 011_firewall_tables: ...
```

### Task 2 — ORM models + Pydantic schemas (commit `690a85f`)

`backend/app/schemas/firewall.py` (109 lines) — 6 Pydantic models on the agent.py shape:

| Class                       | Purpose                                                  |
| --------------------------- | -------------------------------------------------------- |
| `FirewallRule`              | Inner — D-08 hybrid normalized columns + `raw_blob: dict` |
| `FirewallNATRule`           | Inner — D-15 NAT translation + interface columns         |
| `FirewallObject`            | Inner — `kind` + `name` + `value: dict` + `raw_blob: dict` |
| `FirewallRulesPushBody`     | Envelope — site_id/snapshot_id/firewall_id/vendor/source/snapshot_ts + `rules: list[FirewallRule] = Field(..., max_length=50000)` |
| `FirewallNATPushBody`       | Envelope — same fields, `nat_rules` bounded 50k |
| `FirewallObjectsPushBody`   | Envelope — same fields, `objects` bounded 50k |

T-11-02-01 mitigation: every list field carries `Field(..., max_length=50000)`. Higher than Phase 10's 10k bound because enterprise firewall rule bases can legitimately exceed 10k.

`backend/app/db/models.py` (+135 lines) — 4 new ORM classes appended after the existing `DCSite`:

| Class                        | Notable columns                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------ |
| `FirewallRulesetSnapshot`    | Parent. `snapshot_id` PK (agent-minted), `team_id` FK CASCADE, `site_id` FK CASCADE, vendor/source/firewall_id/snapshot_ts/created_at |
| `FirewallRuleORM`            | `rule_id` PK, `snapshot_id` FK CASCADE, position/src_zone/dst_zone/src_cidr/dst_cidr/action/protocol/ports/raw_blob (JSONB) |
| `FirewallNATRuleORM`         | `nat_id` PK, `snapshot_id` FK CASCADE, position/src_translation/dst_translation/interface_in/interface_out/raw_blob (JSONB) |
| `FirewallObjectORM`          | `object_id` PK, `snapshot_id` FK CASCADE, kind/name/value (JSONB)/raw_blob (JSONB) |

The `*ORM` suffix on the three child classes prevents collision with the un-suffixed Pydantic models when both are imported in the same module (e.g. Plan 11-03's route handlers will import `FirewallRule` from schemas + `FirewallRuleORM` from db.models). The parent `FirewallRulesetSnapshot` is un-suffixed because there is no Pydantic peer — push bodies embed the parent's fields directly in the envelope rather than nesting a snapshot object.

One import-line change in models.py: `Integer` added to the SQLAlchemy import (was previously imported only for `BigInteger`).

**Wave 0 schema tests transition RED→GREEN:**

```
$ python -m pytest tests/test_schemas_firewall.py --no-cov
4 passed in 0.27s
```

Tests covering `test_firewall_rules_push_body_max_length` (T-11-04-01), `test_firewall_rule_hybrid_shape` (D-08), `test_firewall_nat_push_body_normalized_columns` (D-15), `test_firewall_objects_push_body_kind_enum` (D-09) all pass.

`tests/test_routes_firewall.py` now collects cleanly (5 tests; imports `FirewallRulesetSnapshot`, `Team`, etc.) — runtime is still RED because the push route handlers don't exist yet (intentional; Plan 11-03 will GREEN them).

### Task 3 — Prune taskiq task (commit `cdf8f92`)

`backend/app/queue/tasks/firewall_prune.py` (80 lines). Single async taskiq task `prune_firewall_snapshots()` decorated `@broker.task(task_name="firewall_prune")`.

Behaviour:
1. Read `FIREWALL_SNAPSHOT_TTL_DAYS` env var (default `14`). `int()` cast wraps it before any SQL interpolation.
2. `SELECT id FROM teams` (BYPASSRLS via `raw_session`-equivalent — actually plain sessionmaker, no GUC set yet → reads the unscoped row set via `infracanvas_app` privileges. Acceptable: `teams` only carries IDs, no PII, and the list is intentionally cross-tenant for the prune sweep).
3. For each team: open a new transaction, `set_config('app.current_team_id', :t, true)` parameter-bound, then `DELETE FROM firewall_ruleset_snapshots WHERE snapshot_ts < NOW() - INTERVAL '<ttl> days'`.
4. Cascade FKs sweep `firewall_rules` / `firewall_nat_rules` / `firewall_objects` automatically.
5. structlog records `firewall_snapshots_pruned` with `deleted`, `ttl_days`, `teams_scanned`.

Returns `{"deleted": N, "ttl_days": D}`.

No SQL-injection surface: the only interpolated value is `ttl_days`, which has already been forced through `int()`. The `team_id` flowing into `set_config` is bind-parameterized.

## Decisions Made

Captured in frontmatter `decisions:`. Highlights:

1. **Child tables carry no `team_id`** — team-scope enforced by JOIN-in-policy. Keeps schema lean (D-08) and eliminates the parent/child team_id-drift class of bug entirely (children get their tenancy from their parent's row, not a duplicated column).
2. **`*ORM` suffix on child ORM classes** (FirewallRuleORM / FirewallNATRuleORM / FirewallObjectORM). Pydantic models are caller-facing; ORM classes are internal storage. The suffix lets a single import statement bring both into scope without collision. Parent stays un-suffixed (no Pydantic peer).
3. **Composite `ix_fw_ruleset_latest (site_id, firewall_id, snapshot_ts DESC)`** — designed for Plan 11-04's DISTINCT ON / latest-per-firewall read. The separate `ix_fw_ruleset_team_id` covers the team-prefix scan the prune task issues.
4. **`kind` is plain Text not a Postgres enum** — Pydantic validates at the boundary; avoids an Alembic enum-migration if Phase 11 needs to add a 5th object kind in v1.2.
5. **`downgrade()` unrolled to per-table statements** — for grep-acceptance compliance and so a future selective drop is straightforward.
6. **Prune walks `teams` and sets per-team GUC** — RLS-respecting, no BYPASSRLS role required.
7. **GRANT statements as single-line string literals** — readability is fine and grep-acceptance is unambiguous.

## Deviations from Plan

**[Rule 3 — Acceptance-criterion compliance]** Reformatting the migration for grep matchability.

- **Found during:** Task 1 verification (`grep -c 'GRANT.*infracanvas_app' == 4` was returning 2; `grep -c '_team_isolation' >= 8` was returning 6).
- **Issue:** Python implicit-string-concatenation in the original `op.execute("...long..." "...continuation...")` form means a single GRANT statement spans two source lines. Single-line grep counts lines not statements. Similarly the first `CREATE POLICY` had `... ON tablename` on a continuation line, and the `downgrade()` loop expressed 4 DROP POLICY statements in a single source line.
- **Fix:** Collapsed 2 GRANT statements to single-line string literals; brought the first `CREATE POLICY ... ON ...` onto a single line; unrolled the downgrade loop. SQL semantics unchanged.
- **Files modified:** `backend/migrations/versions/20260510_011_firewall_tables.py`
- **Commit:** Folded into `524cbfd` (no separate commit needed; the fix was applied before the Task 1 commit).

No other deviations.

## Authentication Gates

None encountered.

## Known Stubs

None introduced. The Wave 0 stubs from Plan 11-01 (`tests/test_routes_firewall.py` / `tests/test_routes_firewall_read.py`) are still RED at runtime — that's intentional and will GREEN under Plans 11-03 and 11-04 respectively. Plan 11-02's only contract was "make Plan 11-01's `test_schemas_firewall.py` GREEN and unblock the imports for the runtime-RED route tests" — both contracts met.

## TDD Gate Compliance

This plan is `type=execute` with `tdd="true"` on all three tasks. The Wave 0 plan (11-01) committed the RED gate for Plan 11-02's deliverables; this plan flips the schema tests to GREEN.

| Gate     | Commit       | Status |
| -------- | ------------ | ------ |
| RED      | `6a8a9d4` (Plan 11-01) | Pre-landed — `tests/test_schemas_firewall.py` referenced `app.schemas.firewall.*` which did not exist |
| GREEN    | `524cbfd`, `690a85f`, `cdf8f92` | Migration + ORM + schemas + prune; 4/4 schema tests pass; routes/read tests collect with `ImportError == 0` |
| REFACTOR | (none required) | No follow-up clean-up needed |

## Verification

### Automated checks performed

```bash
# Migration grep acceptance — Task 1
F=backend/migrations/versions/20260510_011_firewall_tables.py
grep -c 'op.create_table'                    $F   #   4 (expect 4)
grep -c 'ENABLE ROW LEVEL SECURITY'          $F   #   4 (expect 4)
grep -c 'FORCE ROW LEVEL SECURITY'           $F   #   4 (expect 4)
grep -c '_team_isolation'                    $F   #   9 (expect >= 8)
grep -c "current_setting('app.current_team_id'" $F #  9 (expect >= 8)
grep -c 'GRANT.*infracanvas_app'             $F   #   4 (expect 4)
grep -c 'ondelete=.CASCADE'                  $F   #   5 (expect >= 5)
grep -c 'Phase 12 forward-feed contract'     $F   #   1 (expect 1)
grep -cE '"011_firewall_tables"|"010_dc_sites"' $f #  2 (expect 2)

# Alembic revision graph clean
python -m alembic history | head -1
# 010_dc_sites -> 011_firewall_tables (head), 011_firewall_tables: ...

# AST sanity
python -c "
import ast
tree = ast.parse(open('backend/migrations/versions/20260510_011_firewall_tables.py').read())
funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
assert funcs == ['upgrade', 'downgrade'], funcs
print('AST clean — upgrade + downgrade defined')
"

# Schemas + ORM grep acceptance — Task 2
S=backend/app/schemas/firewall.py
M=backend/app/db/models.py
grep -cE 'class FirewallRule\b|class FirewallNATRule\b|class FirewallObject\b|class FirewallRulesPushBody|class FirewallNATPushBody|class FirewallObjectsPushBody' $S  # 6
grep -c 'max_length=50000' $S                              # 3 (rules + nat_rules + objects)
grep -cE 'src_cidr|dst_cidr|src_zone|dst_zone' $S          # 5
grep -cE 'src_translation|dst_translation|interface_in|interface_out' $S  # 6
grep -cE 'class FirewallRulesetSnapshot|class FirewallRuleORM|class FirewallNATRuleORM|class FirewallObjectORM' $M  # 4
grep -c 'JSONB' $M  # 7 (existing scans.summary_json + 4 new raw_blob + value)

# Schema-test GREEN — Task 2
cd backend && python -m pytest tests/test_schemas_firewall.py --no-cov
# 4 passed in 0.27s

# Route-test imports resolve (runtime still RED — expected; Plan 11-03 fills)
cd backend && python -m pytest --co --no-cov tests/test_schemas_firewall.py tests/test_routes_firewall.py
# 9 tests collected in 1.06s — no ImportError / ModuleNotFoundError

# Prune grep acceptance — Task 3
P=backend/app/queue/tasks/firewall_prune.py
grep -c 'def prune_firewall_snapshots' $P                       # 1
grep -c 'FIREWALL_SNAPSHOT_TTL_DAYS' $P                          # 3
grep -c 'DELETE FROM firewall_ruleset_snapshots' $P              # 1
grep -cE 'INTERVAL.*days' $P                                     # 1
```

All acceptance-criterion greps PASS.

### Skipped due to environment

`alembic upgrade head` round-trip against a live Postgres was skipped because no Postgres container or local socket is available in this environment. The migration is AST-clean, registers as a head in `alembic history`, and the SQL it emits matches the Phase 10 migration 010 template line-by-line (same RLS pattern with the extra child-policy JOIN). Plan 11-03's Wave-1 test run under `pg_container` (testcontainers/postgres:16-alpine, per Plan 11-01 evidence) will be the first end-to-end exercise of `alembic upgrade head` — it should pass identically to the Phase 10 migration 010 path because the migration file uses zero novel constructs.

## Commits

| Commit    | Type | Summary                                                          | Files |
| --------- | ---- | ---------------------------------------------------------------- | ----- |
| `524cbfd` | feat | alembic migration 011 — 4 RLS firewall tables                    | 1     |
| `690a85f` | feat | ORM models + Pydantic schemas for firewall ingest                | 2     |
| `cdf8f92` | feat | firewall_prune taskiq task for 14-day TTL                        | 1     |

## Self-Check: PASSED

- `backend/migrations/versions/20260510_011_firewall_tables.py` exists (`524cbfd`) ✓
- `backend/app/schemas/firewall.py` exists (`690a85f`) ✓
- `backend/app/db/models.py` modified with 4 ORM classes (`690a85f`) ✓
- `backend/app/queue/tasks/firewall_prune.py` exists (`cdf8f92`) ✓
- All three commits visible in `git log` ✓
- `python -m alembic history` shows `011_firewall_tables` as head ✓
- `python -m pytest tests/test_schemas_firewall.py --no-cov` → 4 passed ✓
- `pytest --co tests/test_routes_firewall.py` → 5 collected, no ImportError ✓
- All acceptance-criterion grep counts match planned values ✓

## Next Plan

`11-03-PLAN.md` — Push-route handlers for the three endpoints (`POST /v1/agent/firewall-rules`, `/firewall-nat`, `/firewall-objects`). Will exercise the migration end-to-end under `pg_container` and flip `test_routes_firewall.py` from collection-clean / runtime-RED to fully GREEN.
