---
phase: 02-canvas-v1-0
plan: "04"
subsystem: shadow-detection
tags: [wave-2, shadow, boto3, aws-api, drift, python]

requires:
  - phase: 02-01
    provides: DriftStatus.shadow enum value, ResourceNode, CostEstimate models
  - phase: 02-00
    provides: base graph models and test infrastructure

provides:
  - ShadowDetector class with 6-type AWS API coverage (EC2, SG, VPC, subnet, S3, RDS)
  - boto3 optional dependency group in pyproject.toml
  - RuntimeError guards for missing boto3 and missing credentials
  - Shadow nodes with DriftStatus.shadow and estimated monthly cost

affects: [02-06, 02-07, 02-08, main-cli-shadow-flag]

tech-stack:
  added: [boto3>=1.34 (optional), boto3-stubs[ec2,s3,rds]>=1.34 (optional)]
  patterns:
    - optional-import-inside-function (boto3 imported only at detect() call site)
    - non-fatal-api-errors (bare except per service, skip and continue)
    - shadow-cost-estimates (flat monthly estimates per resource type)

key-files:
  created:
    - cli/infracanvas/shadow/__init__.py
    - cli/infracanvas/shadow/detector.py
    - cli/tests/test_shadow.py
  modified:
    - cli/pyproject.toml

key-decisions:
  - "boto3 imported inside detect() not at module level — users without --shadow get no boto3 overhead"
  - "Per-service API errors caught with bare except and silently skipped — non-fatal by design (D-02)"
  - "Flat SHADOW_COST_ESTIMATES dict used instead of calling CostEstimator — shadow nodes don't have full attribute sets"
  - "boto3-stubs added to shadow optional group for type checking during development"

patterns-established:
  - "Optional heavy dependency pattern: import inside function, RuntimeError with install hint on ImportError"
  - "Shadow detection match logic: Name tag first, then resource ID, skip default security groups"

requirements-completed: [SHD-01, SHD-02]

duration: 12min
completed: "2026-04-16"
---

# Phase 02 Plan 04: Shadow Infrastructure Detection Summary

**ShadowDetector comparing live AWS describe_* API against Terraform graph nodes across 6 resource types, with boto3 as an optional dependency and non-fatal credential error handling**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-16T11:30:00Z
- **Completed:** 2026-04-16T11:42:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- ShadowDetector class with 6 supported AWS resource types (aws_instance, aws_security_group, aws_vpc, aws_subnet, aws_s3_bucket, aws_db_instance)
- boto3 imported only inside `detect()` — users without `--shadow` never pay the import cost
- RuntimeError with clear messages for missing boto3 (install hint) and missing credentials (per D-02)
- Shadow nodes flagged with `DriftStatus.shadow` and flat monthly cost estimates
- 5 unit tests with fully mocked boto3 covering all error and detection scenarios
- Optional dependency group `[shadow]` added to pyproject.toml

## Task Commits

Each task was committed atomically:

1. **Task 1: Shadow detector module with boto3 optional import** - `c5389cc` (feat)
2. **Task 2: Shadow detector unit tests with mocked boto3** - `a1e6e22` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `cli/infracanvas/shadow/__init__.py` - Empty package marker
- `cli/infracanvas/shadow/detector.py` - ShadowDetector class with 6-type coverage
- `cli/tests/test_shadow.py` - 5 tests replacing Wave 0 stubs (fully implemented)
- `cli/pyproject.toml` - Added `[project.optional-dependencies]` shadow group

## Decisions Made

- boto3 imported inside `detect()` not at module level — protects users who never use `--shadow` from importing a heavy AWS SDK
- Per-service API errors caught with bare `except Exception: pass` — each service is independent, one failure shouldn't block others (aligns with D-02)
- Used flat `SHADOW_COST_ESTIMATES` dict instead of calling `CostEstimator._estimate_resource()` — shadow nodes lack full attribute sets needed for accurate cost estimation
- Added `boto3-stubs[ec2,s3,rds]` to shadow optional group to support type checking during development

## Deviations from Plan

None — plan executed exactly as written. The stub test file (`test_shadow.py`) pre-existed from Wave 0 scaffolding; replaced with full implementation as planned.

## Issues Encountered

- Python environment: project uses `.venv/bin/python` (Python 3.14.3) not system Python — verified via virtualenv, all tests pass correctly.

## User Setup Required

None — shadow detection is opt-in via `--shadow` flag. Users who want it run: `pip install 'infracanvas[shadow]'`

## Known Stubs

None — ShadowDetector is fully wired. The `--shadow` CLI flag integration is handled in a separate plan (main CLI plan).

## Threat Flags

None. boto3 credential access follows the plan threat model:
- T-02-08 mitigated: RuntimeError messages use generic text, never expose credential values
- T-02-09 mitigated: region parameter passed explicitly, no multi-region scanning
- T-02-10 accepted: read-only describe_* APIs only, no write operations

## Next Phase Readiness

- ShadowDetector is ready for integration into the `scan` CLI command via `--shadow` flag
- The module is importable without boto3 installed (lazy import pattern)
- All 5 tests pass; module-level import verified without boto3

---
*Phase: 02-canvas-v1-0*
*Completed: 2026-04-16*
