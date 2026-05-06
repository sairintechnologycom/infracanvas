---
phase: 01-canvas-mvp
plan: "01"
subsystem: cli-data-layer
tags: [python, pydantic, parser, models, graph, drift, module-resolution]
dependency_graph:
  requires: []
  provides:
    - NetworkFinding model (CLI-02)
    - DriftStatus.shadow value (PRS-05)
    - ResourceGraph v2.0 schema (GRF-03)
    - resolve_modules() recursive module parser (PRS-04)
    - flag_shadow_resources() state shadow flagging (PRS-05)
    - module/region grouping in builder (GRF-02)
  affects:
    - cli/infracanvas/graph/models.py
    - cli/infracanvas/graph/builder.py
    - cli/infracanvas/parser/hcl.py
    - cli/infracanvas/parser/state.py
    - cli/infracanvas/parser/module.py (new)
    - cli/infracanvas/export/json.py (no change needed)
tech_stack:
  added:
    - parser/module.py — new module for recursive local module resolution
  patterns:
    - TDD RED/GREEN with Wave 0 Nyquist stubs committed before implementation
    - Pydantic v2 BaseModel for NetworkFinding
    - StrEnum extension (shadow added to DriftStatus)
    - Circular reference detection via resolved-path visited set
key_files:
  created:
    - cli/infracanvas/parser/module.py
  modified:
    - cli/infracanvas/graph/models.py
    - cli/infracanvas/graph/builder.py
    - cli/infracanvas/parser/hcl.py
    - cli/infracanvas/parser/state.py
    - cli/tests/test_graph.py
    - cli/tests/test_integration.py
decisions:
  - "Module grouping uses module: prefix; region: prefix used when no vpc/subnet/module — consistent with existing vpc:/subnet: pattern"
  - "Circular reference detection added proactively (T-01-02 mitigate) — visited set passed through recursion"
  - "flag_shadow_resources appends nodes to existing graph rather than returning new graph — avoids copying large node lists"
metrics:
  duration_seconds: 215
  completed_at: "2026-04-16T04:59:49Z"
  tasks_completed: 2
  files_changed: 7
---

# Phase 01 Plan 01: CLI Data Layer Extensions Summary

**One-liner:** Python data layer extended with NetworkFinding Pydantic model, DriftStatus.shadow, recursive local module parser (depth-3 limit + circular detection), shadow infrastructure flagging from .tfstate, module/region grouping in builder, and v2.0 JSON schema.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Wave 0 — TestNetworkFinding RED stubs | 09464dd | cli/tests/test_graph.py |
| 1 | Extend models + module parser + shadow flagging (GREEN) | dbdbf82 | models.py, builder.py, hcl.py, state.py, module.py (new), test_integration.py |

## What Was Built

### NetworkFinding model (CLI-02)
New `NetworkFinding(BaseModel)` in `cli/infracanvas/graph/models.py` with fields: `resource_id`, `protocol`, `source_cidr`, `dest_cidr`, `finding_type`, `severity`, `title`, `description`, `remediation`, `evidence`. Supports FlowMap network-level security findings separate from configuration findings.

### DriftStatus.shadow (PRS-05)
`shadow = "shadow"` added to `DriftStatus` StrEnum. Used to mark resources found in `.tfstate` but absent from HCL (unmanaged/orphaned resources).

### ResourceGraph v2.0 schema (GRF-03)
`ResourceGraph.version` default changed from `"1.0"` to `"2.0"`. JSON export via `model_dump_json()` automatically emits the new version — no change required in `export/json.py`.

### Recursive module parser (PRS-04)
New `cli/infracanvas/parser/module.py` with `resolve_modules(directory, parsed, depth, _visited)`:
- Follows only `./` or `../` relative source paths (T-01-01 mitigate)
- Hard depth limit of 3 (T-01-02 mitigate)
- Circular reference detection via resolved-path visited set (T-01-02 mitigate)
- Child resources tagged with `module.{name}` prefix
- `ParsedTerraform._raw_modules` added to hcl.py dataclass; populated by new `_extract_modules()` function

### Shadow infrastructure flagging (PRS-05)
`flag_shadow_resources(graph, state)` added to `cli/infracanvas/parser/state.py`. Appends `ResourceNode` entries with `drift=DriftStatus.shadow` for any state resource address not present in the graph.

### Module/region grouping (GRF-02)
`_determine_group()` in `builder.py` extended with `module` and `region` parameters. Priority: vpc_id > subnet_id > module > region > empty. `_create_nodes()` now reads `region` from resource attributes and passes both to `_determine_group()`.

## Verification

```
cd cli && .venv/bin/python -m pytest tests/ -x -q
# 128 passed in 7.03s

python -c "from infracanvas.graph.models import DriftStatus; print(DriftStatus.shadow)"
# shadow

python -c "from infracanvas.graph.models import ResourceGraph; print(ResourceGraph().version)"
# 2.0

python -c "from infracanvas.parser.module import resolve_modules; print('OK')"
# OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hardcoded version string in integration test**
- **Found during:** Task 1 GREEN verification
- **Issue:** `test_integration.py` line 49 asserted `graph.version == "1.0"` — broke after model default changed to 2.0
- **Fix:** Updated assertion to `graph.version == "2.0"`
- **Files modified:** `cli/tests/test_integration.py`
- **Commit:** dbdbf82

**2. [Rule 2 - Missing critical functionality] Added circular reference detection to resolve_modules**
- **Found during:** Task 1 implementation — threat model T-01-02 required mitigate disposition
- **Issue:** Plan code sketch lacked circular reference guard; recursive module symlinks could cause infinite recursion
- **Fix:** Added `_visited: set[Path]` parameter tracking resolved module directories; skip if already visited
- **Files modified:** `cli/infracanvas/parser/module.py`
- **Commit:** dbdbf82

**3. [Rule 2 - Missing critical functionality] Added `_raw_modules` to ParsedTerraform and `_extract_modules()` to hcl.py**
- **Found during:** Task 1 implementation — `resolve_modules()` requires `parsed._raw_modules` but field was not in existing ParsedTerraform dataclass
- **Fix:** Added `_raw_modules: list[dict[str, Any]]` field to `ParsedTerraform` and `_extract_modules()` function that extracts module blocks from parsed HCL
- **Files modified:** `cli/infracanvas/parser/hcl.py`
- **Commit:** dbdbf82

## Known Stubs

None — all implemented functionality is fully wired. `NetworkFinding` is a new model stub in the sense that no code yet produces `NetworkFinding` instances (that is FlowMap work, Phase 3), but the model itself is complete and validates correctly. This is intentional per the plan scope.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at additional trust boundaries beyond what the plan's threat model documents (T-01-01 through T-01-04).

## Self-Check

Checking created files exist:
- cli/infracanvas/parser/module.py — created in commit dbdbf82
- cli/infracanvas/graph/models.py — modified, class NetworkFinding at line 95
- cli/infracanvas/parser/state.py — modified, flag_shadow_resources at line 77
- cli/infracanvas/graph/builder.py — modified, module: grouping at line 97

Checking commits exist:
- 09464dd — test(01-01): add failing TestNetworkFinding stubs
- dbdbf82 — feat(01-01): extend data layer

## Self-Check: PASSED
