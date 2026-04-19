---
phase: 03-flowmap-v1-0
plan: 01
subsystem: infra
tags: [pydantic, schema, typescript, dependencies, flowmap, elkjs, boto3, azure-mgmt-network]

requires:
  - phase: 02-canvas-v1-0
    provides: ResourceGraph v2.0 (Pydantic + TypeScript mirror) and existing NetworkFinding/Finding shapes
provides:
  - NetworkPath, PathHop, DCCollectorReading, DCSite Pydantic models
  - Extended NetworkFinding (rule_id, source="network", framework_ids, path_id, hop_id)
  - ResourceGraph v2.1 — additive network_paths and dc_sites fields (default empty)
  - viewer/src/types.ts mirror of all five new shapes with field-name parity
  - cli/pyproject.toml [project.optional-dependencies].flowmap (boto3<2, azure-identity<2, azure-mgmt-network<31, azure-mgmt-resource<26, boto3-stubs[directconnect])
  - cli/pyproject.toml [project.optional-dependencies].test (moto, placebo)
  - viewer/package.json elkjs ^0.11.1
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08]

tech-stack:
  added: [elkjs@^0.11.1, boto3>=1.40, azure-identity>=1.20, azure-mgmt-network>=28, azure-mgmt-resource>=23, moto>=5.1, placebo>=0.10]
  patterns: [additive schema version bump, Pydantic→TS field-name-identical mirror, snake_case wire format]

key-files:
  created:
    - cli/tests/test_flowmap_models.py
  modified:
    - cli/infracanvas/graph/models.py
    - viewer/src/types.ts
    - viewer/src/sample-data.ts
    - viewer/src/__tests__/types.test.ts
    - viewer/src/__tests__/store.test.ts
    - cli/tests/test_graph.py
    - cli/tests/test_integration.py
    - cli/pyproject.toml
    - viewer/package.json

key-decisions:
  - "Schema bump v2.0 → v2.1 is strictly additive — no existing reader (export/html.py, DetailPanel, FindingCard) needs touching"
  - "Lock ALL four FlowMap Pydantic models in Phase 3a (not just NetworkPath/PathHop). DCCollectorReading + DCSite land unpopulated so Phase 3b adds populators without schema churn (CONTEXT D-10)"
  - "Extend NetworkFinding with rule_id/source/framework_ids so NFN-01 network rules in Plan 03-05 can reuse the existing rule engine (CONTEXT D-12)"
  - "Pin all new Python deps with upper bounds (<N+1) per ASVS L1 supply-chain guidance (T-03-01-01)"
  - "TypeScript NetworkFinding extensions are `?`-optional to preserve backwards compat with Phase 2 v2.0 JSON (mirrors Python default_factory behavior on wire)"

patterns-established:
  - "Additive schema bump: new models appended, existing classes extended with defaults, version string bumped — legacy fixtures still load via model_validate"
  - "Pydantic↔TypeScript field parity: every new Python model has a TS interface with snake_case field names matching exactly; direction/collector_type use literal unions in TS"

requirements-completed: [FDM-01, FDM-02]

duration: ~50 min (original executor) + ~15 min (continuation after rate-limit)
completed: 2026-04-19
---

# Phase 03-flowmap-v1-0 / Plan 01: FlowMap Schema Foundation

**Five new Pydantic models + extended NetworkFinding + ResourceGraph v2.1 additive bump, mirrored into viewer TS types, plus elkjs + Azure/boto3 optional-deps declared — load-bearing contract for every downstream Plan in Phase 3a.**

## Performance

- **Duration:** ~50 min (initial executor until Anthropic rate-limit) + ~15 min (continuation by orchestrator)
- **Started:** 2026-04-19 09:52 (worktree branch created)
- **Completed:** 2026-04-19 10:55
- **Tasks:** 3 (all completed)
- **Files modified:** 9 (4 commits)

## Accomplishments
- Pydantic v2 models NetworkPath, PathHop, DCCollectorReading, DCSite land in cli/infracanvas/graph/models.py with Field(default_factory=list/dict) defaults consistent with the existing ResourceNode idiom
- NetworkFinding extended additively: rule_id, source="network", framework_ids, path_id, hop_id — now rule-engine-compatible for Plan 03-05 NFN-01 reuse
- ResourceGraph bumped to version="2.1" with network_paths and dc_sites defaulting to [] — backwards-compatible with v2.0 fixtures via model_validate
- viewer/src/types.ts mirrors all five shapes with identical field names (snake_case wire format); literal unions for direction and collector_type
- cli/pyproject.toml declares [project.optional-dependencies].flowmap with pinned upper bounds per ASVS L1 (boto3<2, azure-identity<2, azure-mgmt-network<31, azure-mgmt-resource<26) plus test extras (moto, placebo)
- viewer/package.json adds elkjs ^0.11.1
- All 204 Python tests pass including 11 new test_flowmap_models tests; ruff + mypy --strict clean on models.py
- TypeScript tsc --noEmit clean; new types.test.ts (6 FlowMap type tests) + store.test.ts updated

## Task Commits

1. **Task 1 (TDD red):** `e106a1f` — test(03-01): add failing tests for FlowMap Pydantic models
2. **Task 1 (TDD green):** `2030a67` — feat(03-01): add FlowMap Pydantic models + bump ResourceGraph schema v2.0→v2.1
3. **Task 2:** `e6d7d80` — feat(03-01): mirror FlowMap models into viewer/src/types.ts + sample-data
4. **Task 3:** `048bc8b` — feat(03-01): add flowmap + test extras to pyproject.toml, elkjs to package.json

## Files Created/Modified
- `cli/infracanvas/graph/models.py` — Four new models + extended NetworkFinding + ResourceGraph v2.1
- `cli/tests/test_flowmap_models.py` — 11 model validation tests (new file)
- `cli/tests/test_graph.py`, `cli/tests/test_integration.py` — updated ResourceGraph fixture expectations for new fields
- `viewer/src/types.ts` — Five new interfaces + NetworkFinding extensions + ResourceGraph fields
- `viewer/src/__tests__/types.test.ts` — 6 FlowMap type compilation/shape tests
- `viewer/src/sample-data.ts` — Added empty network_paths + dc_sites arrays
- `viewer/src/__tests__/store.test.ts` — Updated mockGraph with new required fields
- `cli/pyproject.toml` — flowmap + test optional-dependencies groups
- `viewer/package.json` — elkjs ^0.11.1 dependency

## Decisions Made
- All four FlowMap models land in Phase 3a even though DC-related ones stay unpopulated until Phase 3b (honors CONTEXT D-10 to prevent schema churn across the cloud-only → full-hybrid transition)
- NetworkFinding extensions use defaults for all new fields so existing constructors don't break
- TS NetworkFinding additions are all optional (`?`) so legacy v2.0 JSON deserialises cleanly into the new interface without a migration step

## Deviations from Plan
None — plan executed as specified. Only notable event was an Anthropic usage-limit interruption mid-Task-2 on the initial executor agent; the orchestrator verified the in-worktree WIP (uncommitted types.ts/sample-data.ts/test files), confirmed the TS work was complete and correct, and finished Tasks 2 + 3 inline.

## Issues Encountered
- Initial executor subagent hit Anthropic rate limit after completing 2 commits (Task 1 red + green). Four files had uncommitted-but-correct WIP for Task 2. Orchestrator verified WIP compiled, committed it, then completed Task 3 (deps) + SUMMARY inline.
- Pre-existing test failures on `main` in `src/__tests__/colors.test.ts` (2 cases) and `src/__tests__/ResourceNode.test.tsx` (1 case) — unrelated to Plan 03-01 (none of those files were touched). Confirmed by running the same tests on main: same 3 failures. Not a regression introduced by this plan.

## User Setup Required
None — this plan only declares dependencies in manifest files. `pip install -e '.[flowmap]'` and `npm install` run in the normal developer workflow; no external service configuration needed.

## Next Phase Readiness
- **Plan 03-02** (CLI --flowmap flag) can compile against `infracanvas.graph.models.NetworkPath/DCSite` now
- **Plan 03-03** (AWS collector) and **03-04** (Azure collector) can import `boto3` / `azure-mgmt-network` / `azure-mgmt-resource` via the flowmap extras; tests can use moto + placebo from the test extras
- **Plan 03-05** (NET security rules) can rely on extended NetworkFinding with rule_id/framework_ids for rule-engine reuse
- **Plan 03-06 / 03-07 / 03-08** (viewer FlowMap UI) can import NetworkPath/PathHop/DCSite from `types.ts` and use `elkjs` for layered layout

---
*Phase: 03-flowmap-v1-0*
*Completed: 2026-04-19*
