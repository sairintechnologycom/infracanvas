---
phase: 04-e2e-wiring-hardening
plan: 02
subsystem: drift
tags: [drift, summary, invariant, pydantic, census]

# Dependency graph
requires:
  - phase: v1.0 (03 Hybrid Cloud Intelligence)
    provides: DriftStatus StrEnum with all 5 values (unchanged/added/changed/deleted/shadow); GraphSummary.drift dict field; DriftAnalyzer.apply accumulator pattern
provides:
  - drift summary census invariant — sum(graph.summary.drift.values()) == len(graph.nodes) after DriftAnalyzer.apply()
  - GraphSummary.drift default_factory initialized with all 5 DriftStatus keys at zero
  - drift_counts accumulator literal in analyzer.py covers all 5 states (no silent dropping of unchanged/shadow nodes)
affects:
  - phase 04 plans 03 (property-test) and 04 (coverage) — will assert the census invariant
  - phase 06 SaaS API — dashboards consume summary.drift as authoritative state totals
  - phase 09 CostLens — shadow node counts drive unmanaged-spend roll-ups

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enum-census pattern: summary counter literals must enumerate every enum value to preserve sum-equals-count invariant"
    - "Default-factory completeness: Pydantic dict-field default_factory initializes all known keys so freshly constructed summaries are structurally consistent with post-analyzer output"

key-files:
  created: []
  modified:
    - cli/infracanvas/drift/analyzer.py
    - cli/infracanvas/graph/models.py

key-decisions:
  - "Extend drift_counts literal from 3 to 5 keys in analyzer.py rather than reshaping the accumulator loop — the existing `if node.drift in drift_counts` check opts unchanged/shadow nodes in automatically once the dict grows."
  - "Extend GraphSummary.drift default_factory in models.py to mirror the 5-key contract so freshly constructed summaries (pre-analyzer) have the same shape as post-analyzer summaries."
  - "Leave DriftStatus enum untouched — all 5 values already existed (lines 34–39 of models.py); no enum change was needed despite CONTEXT.md being conservative on that point."
  - "Do not introduce any orthogonal `is_shadow` flag on ResourceNode — the 5 drift states remain mutually exclusive per D-06."
  - "Defer any viewer FilterPanel / summary-badge changes per D-08 — this plan is a CLI summary fix only."

patterns-established:
  - "Drift-counter census: every enum-backed counter dict literal must list all enum values, even zero-valued ones, so downstream consumers can rely on `sum(counts.values()) == len(items)`."
  - "Default-factory/post-accumulator shape parity: the default_factory on a Pydantic dict field and the literal used to rebuild that dict inside an analyzer must carry identical keysets."

requirements-completed: [WRG-02]

# Metrics
duration: 7min
completed: 2026-04-20
---

# Phase 04 Plan 02: Drift summary census (WRG-02) Summary

**drift_counts literal and GraphSummary.drift default_factory both extended from 3 keys to 5; census invariant `sum(summary.drift.values()) == len(graph.nodes)` now holds after DriftAnalyzer.apply().**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-20T15:21:29Z
- **Completed:** 2026-04-20T15:28:21Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Closed WRG-02: `summary.drift` is now a complete census of all ResourceNode drift states (unchanged/added/changed/deleted/shadow), not just the three terraform-plan actions.
- Guaranteed post-condition of `DriftAnalyzer.apply()`: `sum(graph.summary.drift.values()) == len(graph.nodes)` — verified empirically with a mixed 5-node fixture (one of each state) returning `{'added': 1, 'changed': 1, 'deleted': 1, 'unchanged': 1, 'shadow': 1}`, sum == 5, nodes == 5.
- Freshly constructed `GraphSummary()` instances now expose all 5 keys at zero, matching the post-analyzer shape — eliminating the structural-divergence footgun where dashboards consuming a just-built summary would see a 3-key dict but consuming a post-analyzer summary would see a 5-key dict.

## Task Commits

Each task was committed atomically (commits on the worktree branch):

1. **Task 1: Extend drift_counts to 5 keys in both analyzer and models defaults** — `3e9924c` (fix)

_No separate metadata commit — SUMMARY.md is committed as part of plan wrap-up after all executor tasks (orchestrator owns STATE.md/ROADMAP.md writes in the wave-merge step)._

## Files Created/Modified

- `cli/infracanvas/drift/analyzer.py` — extended the `drift_counts` dict literal at line 41 from 3 keys to 5 (`{"added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0}`); the existing `if node.drift in drift_counts` accumulator loop body is unchanged — growing the dict automatically opts unchanged+shadow nodes into counting.
- `cli/infracanvas/graph/models.py` — extended `GraphSummary.drift` `default_factory` at lines 73–77 from 3 keys to 5 (keeps the trailing-comma 4-line form consistent with project style); `DriftStatus` enum (lines 34–39) untouched.

## Decisions Made

See frontmatter `key-decisions`. Summary:
1. Mechanical dict-literal extension in both files — simplest change that satisfies the invariant without rewriting the accumulator or introducing a new code path.
2. Enum untouched — all 5 values already existed; the plan's CONTEXT.md was conservative about this but PATTERNS.md confirmed completeness, and direct inspection at lines 34–39 verified it.
3. No orthogonal `is_shadow` flag on `ResourceNode` — the 5 drift states remain mutually exclusive (D-06); shadow is a drift state, not a cross-cutting attribute.
4. Viewer/FilterPanel deferred per D-08 — this plan is a CLI summary fix only.

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing `test_drift.py` and `test_shadow.py` suites had no `len(drift) == 3` assertions, so no in-place test update was required (the plan's acceptance criteria anticipated this possibility; it did not arise).

## Issues Encountered

**Environmental — disk space exhaustion on host data volume.** During verification, `/private/tmp` reached 100% full, blocking the Bash tool's output capture (unable to write even small stdout files). Resolved mid-plan by clearing `~/.cache` (freed ~1.4 GB). This was a host-environment artefact unrelated to the code change; no task logic was affected, and all verification steps were re-run successfully after cleanup:
- `ruff check` — clean
- `mypy` strict — `Success: no issues found in 2 source files`
- `pytest tests/test_drift.py tests/test_shadow.py -x` — `9 passed in 0.22s`
- Default-factory invariant one-liner — prints `OK`
- Empirical post-analyzer invariant check on a mixed 5-state graph — `sum=5`, `nodes=5`, invariant holds.

## User Setup Required

None — no external service configuration required.

## Acceptance Criteria — All Pass

- `grep '"added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0' cli/infracanvas/drift/analyzer.py` → **1 match** (line 41)
- `grep '"unchanged": 0' cli/infracanvas/graph/models.py` → **1 match** (line 75, inside GraphSummary.drift default_factory)
- `grep '"shadow": 0' cli/infracanvas/graph/models.py` → **1 match** (line 75, inside GraphSummary.drift default_factory)
- `grep -c 'class DriftStatus' cli/infracanvas/graph/models.py` → **1** (enum untouched)
- `grep -E 'is_shadow' cli/infracanvas/graph/models.py` → **no matches** (no orthogonal flag introduced)
- `ruff check` → **all checks passed**
- `mypy --strict` → **no issues in 2 source files**
- `pytest tests/test_drift.py tests/test_shadow.py -x` → **9 passed**
- Default-factory one-liner assertion → **OK**
- Post-analyzer invariant on mixed 5-state graph → **sum == len(nodes) == 5**

## Threat Flags

None — the change does not introduce any new trust boundary, input channel, or schema-at-trust-boundary. The added `shadow` key surfaces information already present as a per-node enum value; T-04-04 (information disclosure) was already accepted in the plan's threat register.

## Self-Check: PASSED

- **File check:** `cli/infracanvas/drift/analyzer.py` — FOUND (modified, 5-key literal at line 41)
- **File check:** `cli/infracanvas/graph/models.py` — FOUND (modified, 5-key default_factory at lines 73–77)
- **Commit check:** `3e9924c` — FOUND in `git log` on the worktree branch (`3e9924c fix(04-02): include unchanged + shadow in drift summary counts`)
- **Deletion check:** `git diff --diff-filter=D HEAD~1 HEAD` returned no files — no unintended deletions.

## Next Phase Readiness

- WRG-02 closed; the census invariant is now mechanical and testable.
- Phase 04 Plan 03 (if it lands a property test for the invariant) can assert `sum(graph.summary.drift.values()) == len(graph.nodes)` over Hypothesis-generated graphs with any mix of drift states — the post-condition will hold.
- Phase 04 Plan 04 (per-module coverage gate) can now include drift analyzer census logic in its coverage scope without hitting the silent-drop-of-unchanged/shadow bug that previously would have required either a test-side workaround or an assertion that the totals were partial.
- Phase 06 (SaaS API) and Phase 09 (CostLens) can treat `summary.drift` as authoritative for total-state roll-ups without a frontend-side guard against missing keys.

---
*Phase: 04-e2e-wiring-hardening*
*Plan: 02*
*Completed: 2026-04-20*
