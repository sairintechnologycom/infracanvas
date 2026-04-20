---
phase: 04-e2e-wiring-hardening
plan: 01
subsystem: cli
tags:
  - cli
  - exit-codes
  - typer
  - stderr
  - gate-mode
requirements:
  - WRG-01
dependency_graph:
  requires:
    - "cli/infracanvas/main.py (existing Typer app with scan/score/plan/export commands)"
    - "cli/infracanvas/export/html.py (existing export_html(graph, output_path, gate_mode=True) signature)"
  provides:
    - "Uniform 0/1/2 exit-code contract across scan/score/plan/export"
    - "Module-level _err_console = Console(stderr=True) for error routing"
    - "--gate-mode/--no-gate-mode flag on `infracanvas export` (default True)"
    - "gate_mode value threaded from CLI layer into export_html()"
  affects:
    - "CI scripts consuming `infracanvas` exit codes (now deterministic)"
    - "Any test asserting score/export exit codes (test_cli.py::test_score_invalid_directory updated 1→2)"
tech_stack:
  added: []
  patterns:
    - "Stderr routing via dedicated Console(stderr=True) constant (mirrors existing _ci_console pattern)"
    - "Typer boolean negation flag pair `--gate-mode/--no-gate-mode` with Annotated + default True"
key_files:
  created: []
  modified:
    - cli/infracanvas/main.py
    - cli/tests/test_cli.py
decisions:
  - "D-01 applied: --gate-mode/--no-gate-mode added on export, gate_mode threaded to export_html()"
  - "D-02 applied: exit-code contract 0/1/2 (success / missing-input / parse-or-validation)"
  - "D-03 applied: _err_console = Console(stderr=True) introduced as module-level constant"
  - "D-04 applied: contract enforced uniformly across scan/score/plan/export (3 exit codes normalized 1→2)"
metrics:
  tasks_completed: 1
  tasks_total: 1
  commits: 1
  duration_minutes: 15
  files_created: 0
  files_modified: 2
  pytests_passing: 271
  completed_date: "2026-04-20"
---

# Phase 04 Plan 01: CLI Exit-Code + Stderr + --gate-mode (WRG-01) Summary

Normalize `infracanvas` CLI to a deterministic 0/1/2 exit-code contract with stderr-routed errors and a working `--gate-mode` flag on `export`, closing WRG-01 for Phase 4 hardening.

## What Was Done

Four concrete edits to `cli/infracanvas/main.py` plus one test expectation update:

1. **Added module-level `_err_console`** — `_err_console = Console(stderr=True)  # for error messages (WRG-01 D-03)` placed immediately after the existing `_ci_console`. The comment references WRG-01 D-03 so future readers can trace.

2. **Added `--gate-mode/--no-gate-mode` option to `export`** — new Typer parameter with `Annotated[bool, typer.Option("--gate-mode/--no-gate-mode", help=...)]` defaulting to `True`, inserted after the existing `format` parameter.

3. **Fixed export call site** — `export_html(graph, out_path)` → `export_html(graph, out_path, gate_mode=gate_mode)`. This was the literal bug WRG-01 pinpointed: the 4th (and only untested) call site was silently discarding the flag.

4. **Migrated 7 error-print sites from `console` → `_err_console`** with normalized exit codes per D-02/D-04:

| Site (post-edit line) | Command | Before           | After            | Change |
|-----------------------|---------|------------------|------------------|--------|
| 338–339               | scan    | console / code=2 | _err / code=2    | stderr routing only |
| 465–466               | serve   | console / code=2 | _err / code=2    | stderr routing only |
| 566–567               | score   | console / code=1 | _err / **code=2** | stderr + normalize (not-a-directory = parse/validation) |
| 627–628               | plan    | console / code=1 | _err / **code=2** | stderr + normalize (not-a-directory = parse/validation) |
| 631–632               | plan    | console / code=1 | _err / code=1    | stderr routing only (missing planfile = missing-input) |
| 759–760               | export  | console / code=1 | _err / code=1    | stderr routing only (missing report = missing-input) |
| 766–767               | export  | console / code=1 | _err / **code=2** | stderr + normalize (invalid JSON/Pydantic = parse/validation) |

The `_ci_console.print(...)` calls in `_run_scan()` were intentionally **not** migrated — those are CI-mode diagnostic routes per D-03's call-out, and stay on `_ci_console`. Success-path `console.print(...)` calls (tables, "Report saved to...", cyan status messages) also stay on stdout.

5. **Test update** — `tests/test_cli.py::TestScoreCommand::test_score_invalid_directory` asserted exit 1, now asserts exit 2 to match the normalized contract. Comment added referencing WRG-01 D-04.

## Exit-Code Contract (Post-Edit)

Uniform across `scan`, `score`, `plan`, `export`:

| Code | Meaning                                                     |
|------|-------------------------------------------------------------|
| 0    | Success                                                     |
| 1    | Missing input file (planfile/report literally doesn't exist)|
| 2    | Parse or validation error (incl. not-a-directory, invalid JSON, failed Pydantic validation, no .tf files found) |

## Verification Evidence

All acceptance criteria from the plan validated on post-edit `main.py`:

- `grep -c "_err_console = Console(stderr=True)" cli/infracanvas/main.py` → **1**
- `grep -c "WRG-01 D-03" cli/infracanvas/main.py` → **1**
- `grep -c '"--gate-mode/--no-gate-mode"' cli/infracanvas/main.py` → **1**
- `grep -c "export_html(graph, out_path, gate_mode=gate_mode)" cli/infracanvas/main.py` → **1**
- `grep -c "_err_console.print" cli/infracanvas/main.py` → **7**
- `python -m infracanvas.main export /nonexistent/file.json; echo $?` → **1** (missing file)
- `python -m infracanvas.main export <malformed-json>; echo $?` → **2** (parse error)
- `python -m infracanvas.main export /nonexistent/file.json >/dev/null 2>&1; echo $?` → **1** (exit propagates through stderr redirect)
- `python -m infracanvas.main export /nonexistent/file.json 2>&1 >/dev/null | grep -c Error` → **1** (error text reaches stderr, not stdout)
- `python -m infracanvas.main export --help | grep -E "gate-mode|no-gate-mode"` → shows `--gate-mode      --no-gate-mode          Enable free-tier resource gating  [default: gate-mode]`
- `pytest tests/` → **271 passed** (all pre-existing tests + the one updated assertion)
- `ruff check infracanvas/main.py` → 23 errors, **zero introduced by this plan** (baseline-matched via `git stash` comparison)
- `mypy infracanvas/main.py` → 7 errors, **zero introduced by this plan** (baseline-matched via `git stash` comparison; the 4 main.py errors just shifted line numbers by the number of lines added)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Updated `test_score_invalid_directory` expected exit code 1 → 2**
- **Found during:** Task 1 verification (first `pytest -x` run)
- **Issue:** `tests/test_cli.py::TestScoreCommand::test_score_invalid_directory` asserted `exit_code == 1`, which was the pre-WRG-01 behavior. The D-04 normalization mandates `score` not-a-directory → exit 2, so the existing test would block completion.
- **Fix:** Updated the assertion to `exit_code == 2` and added an inline comment referencing `WRG-01 D-04`.
- **Files modified:** `cli/tests/test_cli.py` (line 136)
- **Commit:** `3895694` (included in the main task commit; no separate commit since the fix is part of the atomic WRG-01 contract change)

### Out-of-Scope Deviations

None. Everything committed was mandated by the plan's 7-row migration table and acceptance criteria, with the sole addition of the required test assertion update.

### Out-of-Scope Discoveries (Not Fixed, Per Scope Boundary)

- `ruff check infracanvas/main.py` reports 23 pre-existing errors (14× `UP045` Optional→X|None, 3× `E501` line-too-long, 1× `UP037`, 1× `I001`, 1× `F821` ScoreCard, 2× `F401` unused imports). These predate this plan — baseline confirmed via `git stash` comparison. Not fixed. Should be addressed in a future code-hygiene plan.
- `mypy infracanvas/main.py` reports 4 pre-existing errors in `main.py` (2× unused-ignore, 1× Ellipsis-default-incompatible, 1× undefined ScoreCard) plus 3 errors in other modules. All predate this plan. Not fixed.

## CLAUDE.md Compliance

- Python 3.12 target preserved, snake_case conventions, 4-space indent, Ruff-compatible line length.
- `typer.Exit(code=N)` pattern preserved per project error-handling convention.
- Type annotations used on the new Typer `Annotated[bool, ...]` parameter, mandatory per MyPy strict mode.
- No new dependencies added; no new external trust boundaries.

## Threat Flags

None. Per the plan's `<threat_model>`, no new trust boundaries, no new auth paths, no new secrets. The `--gate-mode` flag is Typer-validated boolean input. T-04-01 (tampering on exit codes) and T-04-02 (info disclosure on stderr) are both `accept` dispositions — no mitigation needed.

## Known Stubs

None. All wiring is fully implemented end-to-end: CLI flag → command function parameter → `export_html()` call site → `gate_mode` consumed by the existing `export_html` body.

## TDD Gate Compliance

N/A — this plan is `type: execute` (not `type: tdd`). The approach was verify-after-edit, with the pytest suite and inline CLI invocations serving as regression guards. The updated test (`test_score_invalid_directory`) was a pre-existing test whose expectation needed to match the new normalized contract, not a new TDD RED gate.

## Files Touched

### Modified
- `cli/infracanvas/main.py` — +8 insertions / -7 deletions (net +1 new line for `_err_console` constant, plus +9 for the `gate_mode` Typer parameter block, minus the matching `console` → `_err_console` substitutions and 3 exit-code digit changes)
- `cli/tests/test_cli.py` — +1 / -1 (exit-code assertion 1 → 2 on one test)

## Commits

| Hash    | Message                                                                          |
|---------|----------------------------------------------------------------------------------|
| 3895694 | feat(04-01): normalize CLI exit codes, stderr routing, --gate-mode flag (WRG-01) |

## Self-Check: PASSED

Evidence:
- `cli/infracanvas/main.py` exists and contains all four required edits (verified via `grep` counts in Verification Evidence above).
- `cli/tests/test_cli.py` exists with updated assertion on line 136.
- Commit `3895694` exists in `git log` on branch `worktree-agent-abc6da51`.
- Full pytest suite passes (271/271).
- All acceptance criteria from `<acceptance_criteria>` confirmed true.
