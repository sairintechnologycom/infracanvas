---
phase: 12-path-asymmetric-routing
plan: 05
subsystem: security
tags: [path-compute, lpm, pytricia, asymmetric-routing, classifier, netflow, pure-functions, mypy-strict]

# Dependency graph
requires:
  - phase: 12-01
    provides: Wave 0 RED test scaffolds (test_lpm, test_forward, test_pair, test_correlate, test_asymmetry, test_classify, test_impact, test_net_010_detector); NetworkPath/PathHop/NetworkFinding model extensions
  - phase: 12-02
    provides: RouteRecord/NetFlowRecord/FirewallNATRule ORMs + pytricia listed in backend deps; v1.1 endpoint-only NetFlow schema (no exporter_interface column)
provides:
  - backend/app/security/pathcompute/ — 7 pure-compute modules (lpm, forward, pair, correlate, asymmetry, classify, impact), no I/O, no DB
  - Deterministic ECMP via lex-lowest (metric, next_hop) tiebreak in lpm.build_trie (Pitfall 3)
  - Hop-by-hop forward path expansion with max_hops=20 + visited-set loop detection (PTH-01)
  - Bidirectional pair builder (PTH-02) via compute_forward swap with direction='return' rewrite
  - v1.1 endpoint-only NetFlow correlation in correlate.matches with explicit TODO(v1.2) edge-hop marker (Warning 4)
  - emit_divergence() shaped for PathDivergenceFindingORM insert (D-07)
  - Symmetric-difference asymmetry detector (ASY-01)
  - Evidence-scored classifier with NAT>LEAK>LOCAL_PREF precedence + UNKNOWN fallback (ASY-02 D-08/D-09)
  - Two impact scalars per asymmetry finding — impact_bytes_per_sec + impact_firewall_count (ASY-03 D-10)
  - cli/infracanvas/security/network/net_010.py — Python detector emitting NetworkFinding(rule_id='NET-010', source='network') via existing aggregation pipeline (D-11)
affects: [12-03 read API consumers, 12-06 taskiq job glue, 12-07 viewer integration, future v1.2 edge-hop correlation upgrade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-compute modules: Pydantic objects in, Pydantic objects out — no httpx/sqlalchemy/psycopg imports"
    - "Protocol-based duck typing for ORM-row inputs (lpm._RouteRecordLike)"
    - "Module-level sys.modules indirection in classify.classify() so score_* functions can be monkeypatched per test without re-import dance"
    - "Per-rule try/except around ipaddress.ip_network at TB-2 boundary (Pitfall 8)"
    - "Env-var threshold tuning (CAUSE_THRESHOLD) loaded at module import"

key-files:
  created:
    - backend/app/security/__init__.py — backend security domain package marker
    - backend/app/security/pathcompute/__init__.py — Phase 12 pure-compute subpackage marker
    - backend/app/security/pathcompute/lpm.py — pytricia Patricia trie wrapper, build_trie + lookup, deterministic ECMP
    - backend/app/security/pathcompute/forward.py — compute_forward with LPM hop expansion + ingress device selection
    - backend/app/security/pathcompute/pair.py — compute_pair forward+return builder
    - backend/app/security/pathcompute/correlate.py — v1.1 endpoint-only matches() + emit_divergence(), TODO(v1.2) marker
    - backend/app/security/pathcompute/asymmetry.py — is_asymmetric + asymmetric_nodes via symdiff
    - backend/app/security/pathcompute/classify.py — score_nat/leak/local_pref + classify with NAT>LEAK>LOCAL_PREF tiebreak + UNKNOWN fallback
    - backend/app/security/pathcompute/impact.py — impact_bytes_per_sec + impact_firewall_count
    - cli/infracanvas/security/network/__init__.py — Python-detector subpackage marker
    - cli/infracanvas/security/network/net_010.py — NET-010 detect_stateful_firewall_asymmetry detector
  modified:
    - backend/pyproject.toml — extended mypy overrides to ignore missing stubs for pytricia + infracanvas.* (Rule 3 deviation; see below)
    - backend/tests/security/pathcompute/conftest.py — turned Wave 0 fixture stubs into real Pydantic builders (Rule 3 deviation; see below)
    - backend/tests/security/pathcompute/test_{lpm,forward,pair,correlate,asymmetry,classify,impact}.py — converted skip-stubs to real GREEN assertions per behavior contract
    - cli/tests/test_net_010_detector.py — converted skip-stubs to 4 real GREEN tests

key-decisions:
  - "Used module-level sys.modules indirection in classify.classify() (mod.score_nat etc.) so tests can monkeypatch the three score functions independently — avoids re-import gymnastics from CAUSE_THRESHOLD env override"
  - "Ingress device selection in forward.compute_forward picks the device whose trie covers src_ip with the longest matching prefix; on tie, lex-lowest host name (deterministic, mirrors Pitfall 3 spirit)"
  - "pair.compute_pair rewrites the return NetworkPath via reconstruction (not mutation) so Pydantic immutability holds; ret.evidence carries pair_src/pair_dst alongside the original src_cidr/dst_cidr from the swapped compute_forward call"
  - "emit_divergence() observed_path dict intentionally omits exporter_interface/exit_interface keys in v1.1 — Phase 10 agent doesn't emit them yet (Warning 4 deferred to v1.2)"
  - "impact_bytes_per_sec accepts both dict and Pydantic-object flow records via duck-typed bytes accessor — keeps the function callable from taskiq job (raw ORM rows) and from test fixtures (dicts)"

patterns-established:
  - "Pure-compute boundary: any I/O (DB fetch, http) lives in the taskiq job (Plan 12-06); compute modules accept already-fetched data structures only"
  - "Deterministic ECMP via lex-lowest tuple — pattern reusable for any future LPM-style routing decision"
  - "Evidence-scored classifier with explicit precedence dict + threshold env override — reusable shape for any future multi-cause root-cause logic"
  - "Python detector emits Finding via shared model + source discriminator — sits alongside YAML rule engine without expanding the YAML operator set (Pitfall 6/7 coexistence)"

requirements-completed: [PTH-01, PTH-02, PTH-03, ASY-01, ASY-02, ASY-03, NET-010]

# Metrics
duration: 15min
completed: 2026-05-17
---

# Phase 12 Plan 12-05: Pure-Compute Path Layer + NET-010 Detector Summary

**7 backend pure-compute modules (lpm/forward/pair/correlate/asymmetry/classify/impact) under `backend/app/security/pathcompute/` plus a CLI Python detector at `cli/infracanvas/security/network/net_010.py` — v1.1 endpoint-only NetFlow correlation, deterministic ECMP, NAT>LEAK>LOCAL_PREF tiebreak, all wired through the existing NetworkFinding pipeline.**

## Performance

- **Duration:** ~15 min (commit a7d3ff6 at 14:03:50 IST → commit 8da0270 at 14:18:58 IST)
- **Started:** 2026-05-17T08:33:50Z (14:03:50 IST)
- **Completed:** 2026-05-17T08:48:58Z (14:18:58 IST)
- **Tasks:** 2 (each TDD, RED → GREEN)
- **Files modified:** 21 (11 created, 10 modified)

## Accomplishments
- Full Phase 12 compute call surface ready: `lpm.build_trie / lpm.lookup / forward.compute_forward / pair.compute_pair / correlate.matches / correlate.emit_divergence / asymmetry.is_asymmetric / asymmetry.asymmetric_nodes / classify.score_nat / score_leak / score_local_pref / classify.classify / impact.impact_bytes_per_sec / impact.impact_firewall_count` — Plan 12-06 needs only glue, no compute logic.
- 21 Wave 0 backend pathcompute tests GREEN (plan baseline target was 10 — implementation overshot with full per-module suites for lpm/forward/pair/correlate/asymmetry/classify/impact).
- 4 cli NET-010 detector tests GREEN; YAML reservation test `test_net_010_reserved_for_phase_3b` and rules-count assertion both unaffected (Pitfall 6/7 YAML/Python coexistence preserved).
- ruff + mypy --strict clean across all 8 backend pathcompute files and all 2 cli network files.
- Warning 4 honored end-to-end: correlate.py is v1.1 endpoint-only with the literal `# TODO(v1.2): add edge-hop comparison once agent emits exporter_interface` marker comment; zero `exporter_interface`/`exit_interface` references in code outside that TODO comment block.

## Task Commits

Each task was committed atomically following the TDD RED → GREEN cycle:

1. **Task 1 RED — Wave 0 pathcompute tests:** `a7d3ff6` (test) — turned 7 backend pathcompute test files from skip-stubs into real failing assertions; updated conftest.py to ship real Pydantic builders.
2. **Task 1 GREEN — backend pathcompute package:** `68e4255` (feat) — landed 7 pure-compute modules under `backend/app/security/pathcompute/`. *Also extended mypy overrides in `backend/pyproject.toml` — see Deviations.*
3. **Task 2 RED — NET-010 detector tests:** `3fe7659` (test) — turned 4 cli NET-010 tests from skip-stubs into real failing assertions exercising the detector contract.
4. **Task 2 GREEN — NET-010 Python detector:** `8da0270` (feat) — landed `cli/infracanvas/security/network/net_010.py` plus subpackage marker; emits NetworkFinding(rule_id='NET-010', source='network').

**Plan metadata:** _to be appended by the docs commit that ships this SUMMARY._

## Acceptance Criteria — Evidence

Each must_have from PLAN.md frontmatter, with the evidence used to confirm it:

| # | must_have | Evidence |
|---|-----------|----------|
| 1 | 7 modules under `backend/app/security/pathcompute/` — lpm, forward, pair, correlate, asymmetry, classify, impact | `ls backend/app/security/pathcompute/{lpm,forward,pair,correlate,asymmetry,classify,impact}.py` → 7 files; package marker `__init__.py` present |
| 2 | LPM via pytricia==1.3.0 with deterministic ECMP via lex-lowest (metric, next_hop) | `grep -c 'import pytricia' lpm.py` = 1; `grep -c 'def build_trie\|def lookup' lpm.py` = 2; `grep -c '(r.metric, r.next_hop) < (ex_metric, ex_next)' lpm.py` = 1 (Pitfall 3) |
| 3 | compute_forward returns NetworkPath via hop-by-hop LPM with max_hops + loop detection (PTH-01) | `grep -c 'def compute_forward' forward.py` = 1; module contains `visited: set[str]`, `for _ in range(max_hops)`, `_select_ingress` helper |
| 4 | compute_pair returns (forward, return) with direction='return' on the second leg (PTH-02) | `grep -c 'def compute_pair' pair.py` = 1; constructs `NetworkPath(... direction="return", evidence={..., pair_src, pair_dst})` |
| 5 | v1.1 endpoint-only NetFlow correlation; TODO(v1.2) marker for code-review visibility (Warning 4) | `grep -c 'def matches\|def emit_divergence' correlate.py` = 2; `grep -c "TODO(v1.2)" correlate.py` = 1; `grep -v '^[[:space:]]*#' correlate.py \| grep -c 'exporter_interface\|exit_interface'` = 0 |
| 6 | Asymmetry detector via hop-node symmetric difference (ASY-01) | `grep -c 'def is_asymmetric\|def asymmetric_nodes' asymmetry.py` = 2; bodies use `{h.node_id for h in ...} ^ {...}` symdiff |
| 7 | classify() returns (cause, confidence, evidence) with NAT>LEAK>LOCAL_PREF tiebreak on ties ≥ 0.4; UNKNOWN fallback (D-08, D-09) | `grep -c 'def score_nat\|def score_leak\|def score_local_pref\|def classify' classify.py` = 4; precedence dict `_PRECEDENCE = {"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}` present at line 32; `UNKNOWN` fallback at line 142 |
| 8 | impact_bytes_per_sec + impact_firewall_count — two scalars per asymmetric finding (ASY-03 D-10) | `grep -c 'def impact_bytes_per_sec\|def impact_firewall_count' impact.py` = 2 |
| 9 | NET-010 Python detector emits NetworkFinding(rule_id='NET-010', source='network') (D-11) | `grep -c 'def detect_stateful_firewall_asymmetry'` = 1; `grep -c 'rule_id="NET-010"'` = 1; `grep -c 'source="network"'` = 1; `grep -c 'severity="high"'` = 1; `from infracanvas.graph.models import NetworkFinding, NetworkPath` present (Pitfall 9 — imports, does not redeclare); YAML catalog `grep -l 'NET-010' cli/infracanvas/security/rules/**/*.yaml` → 0 hits (NET-010 stays out of YAML per D-11) |
| 10 | All Wave 0 pathcompute + NET-010 tests GREEN | `cd backend && pytest tests/security/pathcompute/ --no-cov -q` → `21 passed, 1 skipped`; `cd cli && pytest tests/test_net_010_detector.py tests/test_flowmap_network_rules.py tests/test_security.py --no-cov -q` → `140 passed` (includes the 4 NET-010 tests + the YAML reservation regression test + the rules-count test). Plan baseline was 10 + 4 = 14; implementation exceeded the baseline with 21 + 4 = 25 GREEN. |

### Success-criteria block (additional checks)

- **No I/O in compute layer:** `grep -RE 'import httpx|import sqlalchemy|import psycopg|import asyncpg|from fastapi' backend/app/security/pathcompute/` → 0 hits. ✓
- **ruff clean (backend pathcompute):** `cd backend && ruff check app/security/pathcompute/` → `All checks passed!` ✓
- **mypy --strict clean (backend pathcompute):** `cd backend && mypy --strict app/security/pathcompute/` → `Success: no issues found in 8 source files` ✓
- **ruff clean (cli network):** `cd cli && ruff check infracanvas/security/network/` → `All checks passed!` ✓
- **mypy --strict clean (cli network):** `cd cli && mypy --strict infracanvas/security/network/` → `Success: no issues found in 2 source files` ✓
- **pytricia import works:** `cd backend && python -c "from app.security.pathcompute.lpm import build_trie, lookup; print('lpm-ok')"` → `lpm-ok` (verified at task commit time per 68e4255 message). ✓
- **NET-010 import works:** `cd cli && python -c "from infracanvas.security.network.net_010 import detect_stateful_firewall_asymmetry; print('ok')"` → `ok` (verified at task commit time per 8da0270 message). ✓

## Files Created/Modified

**Created (11):**
- `backend/app/security/__init__.py` — backend security domain package marker (one-line docstring)
- `backend/app/security/pathcompute/__init__.py` — Phase 12 pure-compute subpackage marker, docstring documents D-01 (no I/O contract)
- `backend/app/security/pathcompute/lpm.py` — pytricia.PyTricia(32) wrapper; build_trie + lookup; lex-lowest (metric, next_hop) ECMP tiebreak
- `backend/app/security/pathcompute/forward.py` — compute_forward + _select_ingress; hop-by-hop LPM with max_hops=20 + visited-set loop guard; returns evidence={src_cidr, dst_cidr, hop_count} or `reason: 'empty_snapshot' | 'no_ingress_device' | 'loop_detected'`
- `backend/app/security/pathcompute/pair.py` — compute_pair forward+return via swapped compute_forward; reconstructs ret with direction='return' + pair_src/pair_dst in evidence
- `backend/app/security/pathcompute/correlate.py` — matches() endpoint-only with TODO(v1.2) edge-hop marker; emit_divergence() returns dicts shaped for PathDivergenceFindingORM insert; _in_cidr() wraps ip_network() in try/except for Pitfall 8
- `backend/app/security/pathcompute/asymmetry.py` — is_asymmetric + asymmetric_nodes via `{h.node_id for h in ...} ^ {...}`
- `backend/app/security/pathcompute/classify.py` — three score_* fns + classify(); CAUSE_THRESHOLD env override; module-level sys.modules indirection for monkeypatch-friendly tests; precedence dict + UNKNOWN fallback
- `backend/app/security/pathcompute/impact.py` — impact_bytes_per_sec(window default 3600s); impact_firewall_count via symdiff ∩ stateful_firewalls
- `cli/infracanvas/security/network/__init__.py` — Python-detector subpackage docstring documenting D-11 + Pitfall 6/7 YAML coexistence
- `cli/infracanvas/security/network/net_010.py` — detect_stateful_firewall_asymmetry; emits one NetworkFinding per one-legged stateful firewall sorted by node_id; evidence carries forward_only + return_only + node_seen_on

**Modified (10):**
- `backend/pyproject.toml` — extended `[tool.mypy.overrides]` ignore_missing_imports list with `pytricia` and `infracanvas.*` (see Deviations §1)
- `backend/tests/security/pathcompute/conftest.py` — turned Wave 0 fixture stubs (mk_route_record / mk_flow / mk_path / mk_nat_rule) into real builders returning Pydantic NetworkPath/PathHop instances (see Deviations §2)
- `backend/tests/security/pathcompute/test_lpm.py` — 3 GREEN tests covering trie build + lookup + ECMP determinism
- `backend/tests/security/pathcompute/test_forward.py` — GREEN tests for hop expansion + loop guard + empty snapshot
- `backend/tests/security/pathcompute/test_pair.py` — GREEN tests for forward+return + direction rewrite + pair_src/pair_dst evidence
- `backend/tests/security/pathcompute/test_correlate.py` — GREEN tests for endpoint-only match + emit_divergence shape; xfail-style edge-hop test deferred to v1.2 per Warning 4
- `backend/tests/security/pathcompute/test_asymmetry.py` — GREEN tests for symdiff detector
- `backend/tests/security/pathcompute/test_classify.py` — GREEN tests for each score_* + classify + tiebreak + UNKNOWN
- `backend/tests/security/pathcompute/test_impact.py` — GREEN tests for both impact scalars
- `cli/tests/test_net_010_detector.py` — 4 GREEN tests covering symmetric (no findings), one-legged (1 finding), forward_only vs return_only, empty stateful_firewalls set (no findings)

## Decisions Made

See `key-decisions` frontmatter above. Plan-relative summary:
- Plan said "Edge-hop comparison deferred to v1.2 — marker comment in correlate.py for code-review visibility" — implemented as a 4-line comment block including a forward-looking integration note for the v1.2 author. The block is the only place in `correlate.py` where the words `exporter_interface` / `exit_interface` appear, so the acceptance grep `grep -v '^[[:space:]]*#' correlate.py | grep -c 'exporter_interface\|exit_interface'` = 0 passes.
- Plan recommended verbatim copy of RESEARCH §"Pattern 5: Evidence-scored classifier" — implemented with the addition of sys.modules indirection so monkeypatch in test_classify.py works without forcing test authors to re-import the module after each env-var override. This is the documented test-friendly variant; behavior identical to the reference implementation for production callers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Extended mypy `ignore_missing_imports` overrides in `backend/pyproject.toml`**
- **Found during:** Task 1 GREEN (commit 68e4255)
- **Issue:** Task 1 acceptance criterion requires `mypy --strict app/security/pathcompute/` to be error-free. Two transitive imports lack stub packages: `pytricia` (C extension; no public stubs published) and `infracanvas.*` (file-dep `infracanvas @ file:../cli` is installed but its mypy run is owned by the cli package, not the backend — backend mypy sees the imports as "no library stubs"). Without these overrides, mypy --strict fails with `Skipping analyzing "pytricia": module is installed, but missing library stubs or py.typed marker` and the equivalent for `infracanvas.graph.models`.
- **Fix:** Appended `"pytricia"` and `"infracanvas.*"` to the existing `[tool.mypy.overrides] module = [...]` list (extending the same override that already lives there for taskiq, svix, moto, testcontainers, etc.). +11 lines, all additive — no existing overrides removed or modified.
- **Files modified:** `backend/pyproject.toml` (lines 113-122; mypy override list reformatted from one-line to multi-line for readability)
- **Verification:**
  - `cd backend && mypy --strict app/security/pathcompute/` → `Success: no issues found in 8 source files`
  - The other backend tests that depend on the unchanged behavior (RouteRecordORM imports, etc.) continued to pass — no regression observed.
  - Classification rationale: this is **not** scope leak. It's the minimum config necessary for the new modules to satisfy the plan's existing mypy --strict acceptance criterion under `app/security/pathcompute/`. The classifier+forward+correlate code itself does not require any pyproject change; the override exists solely so `mypy` can read `import pytricia` / `from infracanvas.graph.models import NetworkPath` without breaking on missing third-party stubs. Pitfall 3 + Pitfall 9 in the plan implicitly required these imports.
- **Committed in:** `68e4255` (Task 1 GREEN; same commit as the 7 modules)

**2. [Rule 3 — Blocking] Turned `backend/tests/security/pathcompute/conftest.py` Wave 0 fixture stubs into real Pydantic builders**
- **Found during:** Task 1 RED (commit a7d3ff6)
- **Issue:** Plan 12-01 shipped Wave 0 conftest.py with skeleton helpers that produced dict-shaped stand-ins (acceptable when downstream tests were `pytest.importorskip + pytest.skip`-guarded). Turning the tests RED → GREEN required the helpers to return real `NetworkPath` / `PathHop` Pydantic instances so the assertions could exercise `compute_forward`, `compute_pair`, `is_asymmetric`, `classify` with real model objects (per Pitfall 9 — import models, do not redeclare).
- **Fix:** Replaced the stub bodies of `mk_route_record`, `mk_flow`, `mk_path`, `mk_nat_rule` with real builders. `mk_path` now returns `NetworkPath(...)` constructed from a list of `PathHop` dicts; `mk_route_record` returns a `SimpleNamespace`-like wrapper satisfying the `_RouteRecordLike` Protocol; `mk_nat_rule` returns a similar wrapper. Module docstring already anticipated this transition ("Pydantic schemas not yet authored at Wave 0; dict keeps stubs runnable" — Wave 2 promotes these to real instances).
- **Files modified:** `backend/tests/security/pathcompute/conftest.py`
- **Verification:** `cd backend && pytest tests/security/pathcompute/ --no-cov -q` → `21 passed, 1 skipped`. The 1 skipped test is the v1.2 edge-hop xfail marker preserved per Warning 4 — by design.
- **Committed in:** `a7d3ff6` (Task 1 RED)

### Deferred Items / Out-of-Scope

- **Per-module coverage gate failures in `backend/pyproject.toml` for unrelated modules** (`app/auth`, `app/routes`, `app/db`, `app/queue`, `app/billing`, `app/storage`, `app/obs`): the `D-15` coverage gate hook reports these as <80% line coverage. This is a pre-existing state of the backend test suite — those modules have no Phase 12 connection. The `pytest --no-cov` runs reported above bypass that gate to surface only Plan 12-05 test results. **Not fixed; not in scope** per the SCOPE BOUNDARY rule.
- **`cli/infracanvas/security` line+branch coverage gate** reports 50.4% line / 36.4% branch — also pre-existing and outside Plan 12-05's net new code (the new `cli/infracanvas/security/network/net_010.py` has 100% line coverage from the 4 new tests). **Not fixed; not in scope.**

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking config/fixture upgrades needed to satisfy plan acceptance criteria).
**Impact on plan:** Both auto-fixes are mechanical and infrastructural (pyproject mypy override + Wave 0 fixture bring-up). Neither changes the compute logic specified in the plan. No scope creep; no architectural surprises. The Threat Model trust boundaries TB-1/TB-2/TB-3 still hold — no new attack surface.

## Issues Encountered

None during execution. All RED tests transitioned to GREEN on the first GREEN-phase commit per task.

Post-commit re-verification for this SUMMARY initially showed 6 collection errors when run with the system Python — root cause was `infracanvas` not installed in the system interpreter. Switching to the worktree's `.venv` (which has `pip install -e ../cli` from prior phase setup) resolved this. The 4 task commits were made with that venv active, so the GREEN claim in commit message `68e4255` is accurate; this was a self-check environment discrepancy, not a code defect.

## Threat Flags

None. All STRIDE entries from `<threat_model>` (T-12-05-01..T-12-05-07) are mitigated or explicitly accepted per the plan; no new threat surface introduced beyond what the plan enumerated.

## User Setup Required

None — no external service configuration. The new modules are pure compute and need no env vars beyond the optional `CAUSE_THRESHOLD` (defaults to 0.4 per D-08), no new dashboard config, no new secrets.

## Next Phase Readiness

- **Plan 12-06 (Wave 3 — taskiq job):** Ready to start. The full compute call surface is available at `backend.app.security.pathcompute.*`. The job needs only to: (a) fetch route_snapshots / flows / firewall rules / nat rules from Postgres (Plan 12-02 ORMs), (b) call `compute_pair → is_asymmetric → classify → impact_*` per pair, (c) persist results via Plan 12-02 ORMs, (d) emit findings via the cli NetworkFinding pipeline.
- **Plan 12-03 (Wave 2 — read API, parallel):** No conflict — that plan ships endpoints that read persisted output of the taskiq job; the compute layer is invisible to its scope.
- **Plan 12-04 (Wave 2 — Slack extraction, parallel):** No conflict — independent file paths.
- **Future v1.2 edge-hop work:** Single integration point in `correlate.matches()` flagged with `# TODO(v1.2): add edge-hop comparison once agent emits exporter_interface`. The v1.2 author also needs to extend `emit_divergence()` to include `exporter_interface` / `exit_interface` in the synthesized `observed_path` dict once the Go agent emits them and Plan 12-02's `netflow_records` migration is extended with those columns.

## Self-Check: PASSED

**File-existence verification:**
- `backend/app/security/pathcompute/{__init__,lpm,forward,pair,correlate,asymmetry,classify,impact}.py` → all 8 files present.
- `backend/app/security/__init__.py` → present.
- `cli/infracanvas/security/network/{__init__,net_010}.py` → both present.

**Commit verification (all 4 in `git log` on `worktree-agent-a7b1b08895c3c2af6`):**
- `a7d3ff6 test(12-05): turn Wave 0 pathcompute tests RED with real assertions` → FOUND
- `68e4255 feat(12-05): land backend pathcompute package — 7 pure-compute modules` → FOUND
- `3fe7659 test(12-05): turn Wave 0 NET-010 detector tests RED with real assertions` → FOUND
- `8da0270 feat(12-05): land NET-010 Python detector for asymmetric stateful firewalls` → FOUND

**Test verification (via worktree `.venv`):**
- `cd backend && pytest tests/security/pathcompute/ --no-cov -q` → `21 passed, 1 skipped` ✓
- `cd cli && pytest tests/test_net_010_detector.py tests/test_flowmap_network_rules.py tests/test_security.py --no-cov -q` → `140 passed` (includes 4 NET-010 + YAML reservation + rules-count tests) ✓

**Lint/type verification:**
- backend ruff `app/security/pathcompute/` → `All checks passed!` ✓
- backend mypy --strict `app/security/pathcompute/` → `Success: no issues found in 8 source files` ✓
- cli ruff `infracanvas/security/network/` → `All checks passed!` ✓
- cli mypy --strict `infracanvas/security/network/` → `Success: no issues found in 2 source files` ✓

All acceptance criteria from PLAN.md `must_haves` confirmed with grep + test + lint evidence. No items missing.

---
*Phase: 12-path-asymmetric-routing*
*Plan: 12-05*
*Branch: worktree-agent-a7b1b08895c3c2af6*
*Completed: 2026-05-17*
