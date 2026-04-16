---
phase: 02-canvas-v1-0
plan: "01"
subsystem: data-models-security-pipeline
tags: [wave-1, models, parser, security-engine, python, typescript]
dependency_graph:
  requires: [02-00]
  provides: [finding-source-framework-ids, hcl-parse-errors, policy-loader]
  affects: [02-02, 02-03, 02-04, 02-05, 02-06, 02-07, 02-08]
tech_stack:
  added: []
  patterns: [pydantic-optional-fields-with-defaults, dataclass-field-default-factory, error-collection-not-silent-drop]
key_files:
  created: []
  modified:
    - cli/infracanvas/graph/models.py
    - cli/infracanvas/security/models.py
    - cli/infracanvas/parser/hcl.py
    - cli/infracanvas/security/loader.py
    - cli/infracanvas/security/engine.py
    - cli/infracanvas/main.py
    - viewer/src/types.ts
decisions:
  - "Finding.framework_ids uses list[str] field with [] default (not field_factory) — Pydantic v2 handles mutable defaults safely in BaseModel"
  - "Broad Exception catch in HCL parser is intentional — python-hcl2 raises varied types (LarkError, UnexpectedToken, bare Exception)"
  - "parse_errors placed after _raw_modules in dataclass to preserve field order without breaking existing positional instantiation"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-16T11:15:00Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 02 Plan 01: Data Model Extension and HCL Parser Hardening Summary

Extended Python models and TypeScript types to carry `source` and `framework_ids` through the full pipeline — Finding → SecurityRule → engine → viewer — and replaced the silent HCL parse failure with per-file error collection, unblocking Azure parser work.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend data models and harden HCL parser | 191736c | graph/models.py, security/models.py, parser/hcl.py, viewer/src/types.ts |
| 2 | Extend security engine and loader to propagate source and framework_ids | fe28632 | security/engine.py, security/loader.py, main.py |

## Verification Results

- Python: `162 passed, 27 skipped` — zero regressions after both tasks
- Backwards compatibility checks: Finding defaults (source="security", framework_ids=[]), SecurityRule defaults (framework_ids=[]), load_policy_rules non-existent dir returns [] — all passed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields are wired with real logic and backwards-compatible defaults.

## Threat Flags

None. The `load_policy_rules()` function introduced in this plan is within the threat model's scope (T-02-01). Mitigation is in place: `yaml.safe_load()` used (loader.py line 33), and `policy_dir.is_dir()` guard prevents rglob on non-directories. Parse error output (T-02-02) uses `path.name` only — no full paths or file contents exposed.

## Self-Check: PASSED

- [x] cli/infracanvas/graph/models.py contains `source: str = "security"`
- [x] cli/infracanvas/graph/models.py contains `framework_ids: list[str] = []`
- [x] cli/infracanvas/security/models.py contains `framework_ids: list[str] = field(default_factory=list)`
- [x] cli/infracanvas/parser/hcl.py contains `parse_errors: list[tuple[Path, str]]`
- [x] cli/infracanvas/parser/hcl.py contains `result.parse_errors.append((tf_file, str(exc)))`
- [x] cli/infracanvas/parser/hcl.py does NOT contain bare `except Exception:\n            return`
- [x] viewer/src/types.ts contains `source?: string`
- [x] viewer/src/types.ts contains `framework_ids?: string[]`
- [x] cli/infracanvas/security/loader.py contains `framework_ids=item.get("framework_ids", [])`
- [x] cli/infracanvas/security/loader.py contains `def load_policy_rules(policy_dir: Path)`
- [x] cli/infracanvas/security/engine.py contains `policy_rules: list[SecurityRule] | None = None`
- [x] cli/infracanvas/security/engine.py contains `source=source` in Finding creation
- [x] cli/infracanvas/security/engine.py contains `framework_ids=rule.framework_ids` in Finding creation
- [x] cli/infracanvas/security/engine.py `_evaluate_rule` contains `source: str = "security"`
- [x] cli/infracanvas/main.py contains `parsed.parse_errors` check with Rich warning output
- [x] Commit 191736c exists (Task 1)
- [x] Commit fe28632 exists (Task 2)
