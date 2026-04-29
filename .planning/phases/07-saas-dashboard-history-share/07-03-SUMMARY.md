---
phase: 07-saas-dashboard-history-share
plan: 3
subsystem: backend/scans
tags: [compare, diff, r2, asyncio, rls, pure-function]
requires: [07-01]
provides:
  - "GET /v1/scans/{scan_a_id}/compare/{scan_b_id} returning ResourceDiffResp (D-11)"
  - "compute_diff(graph_a, graph_b, scan_a_id, scan_b_id) pure function reusable by CLI infracanvas diff and v1.2 PR-bot"
  - "NodeDiff + ResourceDiffResp Pydantic schemas (kind ∈ added|removed|changed|unchanged, capped at 5000 nodes)"
affects:
  - "frontend dashboard /compare/{from}/{to} page (07-08) consumes the new endpoint"
  - "scan detail header 'Compare against…' button (07-07) calls this endpoint"
tech-stack:
  added:
    - "asyncio.gather for concurrent R2 reads"
  patterns:
    - "duck-typed edge_key — handles both dict edges (production) and SimpleNamespace edges (unit tests) without converting"
    - "team-scoped session with set_config('app.current_team_id', ...) — RLS makes cross-team rows invisible, missing rows surface as 404 (D-18: don't leak existence)"
    - "two-row SELECT inside a single team-scoped session (no parallel sessions); same-id optimisation collapses to one SELECT + one GET"
key-files:
  created:
    - backend/app/services/diff.py
    - backend/tests/test_scans_compare.py
    - .planning/phases/07-saas-dashboard-history-share/07-03-SUMMARY.md
  modified:
    - backend/app/schemas/scan.py        # +NodeDiff, +ResourceDiffResp; +Literal import
    - backend/app/routes/scans.py        # +asyncio import, +compute_diff/NodeDiff/ResourceDiffResp imports, +compare_scans handler
decisions:
  - "compute_diff lives in app/services/diff.py as a pure function — not bound to FastAPI — so future CLI infracanvas diff and the v1.2 PR-bot can import it without dragging in HTTP/DB dependencies (D-11 rationale)."
  - "Edge diff treats edges as set-keyed by (source, target, relationship) tuples; the helper reads from dict OR attribute access so the production ResourceGraph.edges shape (list[dict[str, str]] in cli/infracanvas/graph/models.py) and unit-test SimpleNamespace edges share one code path."
  - "Same-row optimisation: when scan_a_id == scan_b_id we issue one SELECT and one R2 GET, then reuse the parsed graph for both sides. Preserves all-unchanged semantics for the legitimate 'compare scan to itself' case the dashboard's deep-link will hit."
  - "Malformed R2 blob raises 500 scan_blob_invalid (not 422) — Phase 6 commit-time validation guarantees committed scans are valid; reaching this branch means the bytes were tampered with after commit, which is an internal failure, not a client error."
metrics:
  duration_minutes: 30
  tasks_completed: 2
  tasks_total: 2
  commits: 2
  tests_added: 9      # 4 unit + 5 integration
  tests_total_after: 86
  completed: 2026-04-28
---

# Phase 07 Plan 03: Server-side scan compare endpoint Summary

JWT-authenticated `GET /v1/scans/{a}/compare/{b}` server-side diff —
pure-function `compute_diff` powering the dashboard compare page, the
future CLI `infracanvas diff`, and the v1.2 PR-bot — backed by
concurrent R2 reads, RLS team-scoping for 404-on-cross-team (D-18), and
9 tests (full backend suite: 86 passed).

## What changed

**`backend/app/schemas/scan.py`**
- Added `Literal` to existing typing import.
- Added `NodeDiff` (kind: `added` | `removed` | `changed` | `unchanged`,
  with optional `before`/`after` and `changed_fields`) and
  `ResourceDiffResp` (scan IDs + nodes + edges_added + edges_removed +
  summary counts).

**`backend/app/services/diff.py` (new)**
- `compute_diff(graph_a, graph_b, scan_a_id, scan_b_id) -> ResourceDiffResp`
  — pure function, no DB / R2 / network. Outer-joins nodes by `id`,
  set-diffs edges by `(source, target, relationship)` tuple. Sorted
  output is deterministic (useful for caching + PR-bot digests).
- `_diff_attrs(attrs_a, attrs_b)` — returns sorted list of attribute
  keys whose values differ (D-12: any attribute differs ⇒ changed).
- `_edge_field(edge, field)` — reads from dict OR attribute access so
  the function works against both production `ResourceGraph.edges`
  (list of dicts) and unit-test `SimpleNamespace` stand-ins.
- `_MAX_NODES = 5000` cap on the returned nodes list (T-07-03-02).

**`backend/app/routes/scans.py`**
- Added imports: `asyncio`, `NodeDiff`, `ResourceDiffResp`, `compute_diff`.
- New handler `compare_scans` (`GET /{scan_a_id}/compare/{scan_b_id}`):
  1. Team-scoped session with `set_config('app.current_team_id', ...)`.
  2. Look up both scan rows; missing → 404 `scan_not_found` (D-18).
  3. Capture `r2_key` before session closes.
  4. Concurrent R2 fetch via `asyncio.gather` (collapsed to one read
     when both scans point at the same key); `ClientError` 404 codes
     surface as 404 `object_not_found`.
  5. Pydantic-validate each blob to `ResourceGraph` (failure → 500
     `scan_blob_invalid`).
  6. Delegate to `compute_diff` and return.

**`backend/tests/test_scans_compare.py` (new)**
- 4 unit tests on `compute_diff` (CMP-001 identical, CMP-002 all-added,
  CMP-003 mixed, CMP-004 edges) — zero fixtures, `SimpleNamespace`
  graph stand-ins.
- 5 integration tests with TestClient + moto R2 + Clerk JWKS mock
  (CMP-005 same-team happy path, CMP-006 cross-team scan_a 404,
  CMP-007 cross-team scan_b 404, CMP-008 scan==scan all-unchanged,
  CMP-009 missing R2 blob → 404).
- Local fixtures mirror `test_scans_list.py`: autouse R2-to-moto
  wiring, Clerk JWKS patching, `app_client` TestClient on a
  `NullPool` async engine, `seed_scan_with_blob` factory that inserts
  a `Scan` row AND puts a matching object in moto.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Edge dict access vs attribute access**
- **Found during:** Task 2 first integration-test run (CMP-005 returned
  500 `scan_blob_invalid` even after fixing missing required node fields).
- **Issue:** The plan's `compute_diff` skeleton read `e.source`,
  `e.target`, `e.relationship`, but the real
  `cli/infracanvas/graph/models.py:176` defines
  `edges: list[dict[str, str]]` — production edges are dicts, not
  Pydantic objects. With my `compute_diff` reading attributes, real
  scans would have crashed with `AttributeError`.
- **Fix:** Added `_edge_field(edge, field)` helper that handles both
  dict access (production) and attribute access (unit-test
  `SimpleNamespace`). Edge-key tuples and the `edges_added` /
  `edges_removed` outputs both go through it.
- **Files modified:** `backend/app/services/diff.py`
- **Commit:** `18b9ce7`

**2. [Rule 3 — Blocking] ResourceNode required fields in test blobs**
- **Found during:** Task 2 first integration test run.
- **Issue:** The plan's `_valid_graph_blob` helper used minimal node
  shapes (`{"id": ..., "type": ..., "attributes": ..., "dependencies":
  None, "findings": None, "cost": None, "drift": None, "position":
  None}`), but `ResourceNode` (`cli/infracanvas/graph/models.py:49`)
  requires `name` and `provider` and rejects `None` for the
  default-factory list/dict fields. Pydantic returned a 500
  `scan_blob_invalid` because the test blobs failed validation.
- **Fix:** Removed all the explicit-`None` fields and added the two
  required string fields (`name`, `provider`). Defaults from the model
  fill the rest.
- **Files modified:** `backend/tests/test_scans_compare.py`
- **Commit:** `18b9ce7`

**3. [Rule 2 — Critical] Same-id optimisation**
- **Found during:** Task 2 implementation — CMP-008 (scan_a == scan_b)
  is a documented use case the dashboard will hit (deep-link to
  `/compare/X/X` after a refresh). The plan would run two identical
  SELECTs and two identical R2 GETs.
- **Fix:** When `scan_a_id == scan_b_id` we reuse the row from the
  first SELECT and the bytes from the first GET. Halves DB+R2 round
  trips for the self-compare case while keeping the diff output
  identical (all-unchanged).
- **Files modified:** `backend/app/routes/scans.py`
- **Commit:** `18b9ce7`

**4. [Rule 2 — Critical] Two extra tests beyond the plan's seven**
- **Found during:** Test design — the plan listed 7 tests; I added 2
  more for correctness.
- **Issue:** The plan didn't cover edge diff (only node diff was
  tested) nor the missing-R2-object 404 path.
- **Fix:** Added CMP-004 (edges added/removed/survived) and CMP-009
  (scan row exists but R2 object missing → 404 `object_not_found`).
- **Files modified:** `backend/tests/test_scans_compare.py`
- **Commit:** `18b9ce7`

### Plan-Driven Fixture Naming

The plan's test skeleton referred to fixtures `client`,
`auth_headers`, `seed_scan_factory`, `team_b_scan` — these don't exist
in the project's `conftest.py`. I used the actual project fixture
pattern (`app_client`, `auth_headers_factory`, `seed_scan_with_blob`,
`team_a` / `team_b`) cloned from `test_scans_list.py` — same approach
that plan already cites as the reference for local autouse hooks.
This isn't a deviation per se, just adapting the skeleton to what's
on disk.

## Tasks completed

| Task | Name                                              | Commit    | Files                                                                                   |
| ---- | ------------------------------------------------- | --------- | --------------------------------------------------------------------------------------- |
| 1    | Add diff schemas + pure diff service              | `3b405a2` | `backend/app/schemas/scan.py` (modified), `backend/app/services/diff.py` (new)          |
| 2    | Add compare_scans handler + integration tests     | `18b9ce7` | `backend/app/routes/scans.py` (modified), `backend/app/services/diff.py` (modified — _edge_field helper), `backend/tests/test_scans_compare.py` (new) |

## Verification

```bash
# Handler + service importable
$ env <stub-env-vars> python -c "from app.routes.scans import compare_scans; print(compare_scans.__name__)"
compare_scans

$ python -c "from app.services.diff import compute_diff; print('ok')"
ok

# Compare-only suite
$ python -m pytest tests/test_scans_compare.py -x -q --no-cov
9 passed in 10.43s

# Full backend regression
$ python -m pytest tests/ -x -q --no-cov
86 passed in 67.15s
```

## Acceptance criteria

- [x] `grep -n "class NodeDiff" backend/app/schemas/scan.py` matches one line
- [x] `grep -n "class ResourceDiffResp" backend/app/schemas/scan.py` matches one line
- [x] `backend/app/services/diff.py` exists
- [x] `grep -n "def compute_diff" backend/app/services/diff.py` matches one line
- [x] `grep -n "def _diff_attrs" backend/app/services/diff.py` matches one line
- [x] `grep -n "_MAX_NODES = 5000" backend/app/services/diff.py` matches one line
- [x] `grep -n "outer-join\|edge_key" backend/app/services/diff.py` matches at least two lines (7 total)
- [x] `grep -n "async def compare_scans" backend/app/routes/scans.py` matches one line
- [x] `grep -n "asyncio.gather" backend/app/routes/scans.py` matches at least one line (2 total)
- [x] `grep -n "compute_diff" backend/app/routes/scans.py` matches at least one line (4 total: import + call + 2 docstring refs)
- [x] `grep -n "ResourceDiffResp" backend/app/routes/scans.py` matches at least two lines (5 total)
- [x] `grep -n "HTTP_404_NOT_FOUND" backend/app/routes/scans.py` matches at least two lines (4 total)
- [x] `grep -c "def test_" backend/tests/test_scans_compare.py` = 9 (target was 7; +2 extra)
- [x] CMP-006 + CMP-007 cross-team test IDs present (4 occurrences via test bodies + docstrings)
- [x] `pytest tests/test_scans_compare.py` exits 0 with all tests passing
- [x] `pytest tests/` exits 0 (no regression — 86 passed)

## Validation checklist

- [x] `GET /v1/scans/{a}/compare/{b}` (same team) returns 200 with
      nodes/edges_added/edges_removed/summary
- [x] `GET /v1/scans/{team_b_scan}/{team_a_scan}` returns 404
      (cross-team isolation, both directions)
- [x] `GET /v1/scans/{same}/{same}` returns summary with added=0,
      removed=0, changed=0
- [x] `NodeDiff.kind == "changed"` entries include non-empty
      `changed_fields`
- [x] `NodeDiff.kind == "added"` entries have `before == None`
- [x] `NodeDiff.kind == "removed"` entries have `after == None`
- [x] `compute_diff` pure unit tests pass without any DB or HTTP fixture

## Threat surface

The plan's `<threat_model>` already documented:
- T-07-03-01 cross-team EoP — mitigated via team-scoped session + RLS
- T-07-03-02 DoS via large diff — mitigated via `_MAX_NODES = 5000`
- T-07-03-03 concurrent R2 fetch — accepted (≤50 MB peak)
- T-07-03-04 info disclosure — accepted (caller already has read access)
- T-07-03-05 malformed JSON — mitigated via Pydantic validation; raises
  500 `scan_blob_invalid` (Phase 6 prevents this in normal operation)

No new threats introduced beyond the register.

## Self-Check: PASSED

- File `backend/app/services/diff.py` — FOUND
- File `backend/tests/test_scans_compare.py` — FOUND
- File `backend/app/schemas/scan.py` — FOUND (modified, NodeDiff + ResourceDiffResp present)
- File `backend/app/routes/scans.py` — FOUND (modified, compare_scans present)
- Commit `3b405a2` — FOUND
- Commit `18b9ce7` — FOUND
- 07-02 `list_scans` handler still present in `backend/app/routes/scans.py`: FOUND
- Full backend suite green: 86 passed
