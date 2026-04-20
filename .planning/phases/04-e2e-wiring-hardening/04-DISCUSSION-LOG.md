# Phase 4: E2E Wiring Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 04-e2e-wiring-hardening
**Areas discussed:** Export exit codes + gate_mode, Drift counts semantics, Canvas↔FlowMap tab UI, Test coverage enforcement

---

## Export exit codes + gate_mode (WRG-01)

| Option | Description | Selected |
|--------|-------------|----------|
| `--gate-mode` flag, default true | Explicit flag, escape hatch for CI | ✓ |
| Required arg, no default | Force explicit every invocation | |
| Always true, no flag | Hardcode gate_mode=True | |

**User's choice:** `--gate-mode` flag, default true.

| Option | Description | Selected |
|--------|-------------|----------|
| 0=success, 1=missing file, 2=parse error | Literal WRG-01 wording | ✓ |
| 0=success, 1=any error | Generic | |
| sysexits.h (64/65/66/70) | BSD standard | |

**User's choice:** 0/1/2 per WRG-01.

| Option | Description | Selected |
|--------|-------------|----------|
| Errors → stderr, output → stdout | Standard CLI contract; mirror `_ci_console` | ✓ |
| Everything to stdout | Keep current behavior | |

**User's choice:** Errors to stderr.

| Option | Description | Selected |
|--------|-------------|----------|
| Export only, audit others later | Minimum scope | |
| Apply uniformly across scan/score/plan/export | Consistent CLI surface | ✓ |

**User's choice:** Apply uniformly.

---

## Drift counts semantics (WRG-02)

| Option | Description | Selected |
|--------|-------------|----------|
| All 5 states sum to node_count | Invariant provable in tests | ✓ |
| Only drifted states, exclude unchanged | sum ≤ node_count | |
| Both: total + drifted_total | Extra field | |

**User's choice:** All 5 states sum to node_count.

| Option | Description | Selected |
|--------|-------------|----------|
| Shadow = in state/plan but not scan source (mutually exclusive drift value) | Matches test_shadow.py | ✓ |
| Shadow = orthogonal is_shadow flag | Separate boolean | |
| Shadow folded into `deleted` | Lose distinction | |

**User's choice:** Shadow as mutually-exclusive enum value.

| Option | Description | Selected |
|--------|-------------|----------|
| CLI summary only for Phase 4 | Tight blast radius | ✓ |
| Wire viewer filters to new states | Expose to users | |

**User's choice:** CLI summary only.

| Option | Description | Selected |
|--------|-------------|----------|
| Property test: `sum(drift_counts.values()) == len(nodes)` | Single invariant | ✓ |
| Per-state fixture tests | More verbose | |

**User's choice:** Property test.

---

## Canvas↔FlowMap tab UI (WRG-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Top-left segmented control in header | `[ Canvas | FlowMap ]` pill group next to logo | ✓ (preview confirmed) |
| Floating bottom-right pill | FAB-style | |
| Sidebar tabs at top of FilterPanel | Grouped with filters | |

**User's choice:** Top-left segmented control in app header.

| Option | Description | Selected |
|--------|-------------|----------|
| URL hash (#canvas / #flowmap) | Deep-linkable + shareable | ✓ |
| localStorage | Sticky per browser | |
| Both: hash wins, storage fallback | Hybrid | |
| Neither; always default Canvas | Simplest | |

**User's choice:** URL hash only.

| Option | Description | Selected |
|--------|-------------|----------|
| Cmd/Ctrl+\ toggles; 1/2 jumps | Power-user friendly | ✓ |
| No shortcut, mouse only | Defer a11y | |

**User's choice:** Cmd/Ctrl+\ toggle + 1/2 jumps.

| Option | Description | Selected |
|--------|-------------|----------|
| Disable tab with tooltip explaining why | Pre-empts confusion | ✓ |
| Tab clickable, inner empty-state | Dedicated empty screen | |
| Hide tab entirely | Cleanest look, most confusing | |

**User's choice:** Disable with tooltip.

---

## Test coverage enforcement (WRG-04)

| Option | Description | Selected |
|--------|-------------|----------|
| CI gate (`--cov-fail-under=80`) | Build fails below 80% | ✓ |
| Reported-only, gate later | Gentler landing | |
| Pre-commit gate, CI reports | Catch earlier, bypassable | |

**User's choice:** CI gate.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-module: security/cost/drift ≥ 80% each | Matches WRG-04 wording | ✓ |
| Global 80% across cli/infracanvas/ | Simpler, masks weak modules | |
| Tiered (security 90%, cost/drift 80%) | Extra protection for high-risk | |

**User's choice:** Per-module ≥ 80%.

| Option | Description | Selected |
|--------|-------------|----------|
| Parametrize each rule (positive + negative) | 51×2 = 102 cases | ✓ |
| Sample 10-15 rules + engine tests | Less exhaustive | |
| Engine only; schema validates rules | Fastest CI | |

**User's choice:** Parametrize all 51 rules with positive + negative fixtures.

| Option | Description | Selected |
|--------|-------------|----------|
| Line + branch (`branch = true`) | Catches untested else arms | ✓ |
| Line only | Faster, misses branches | |

**User's choice:** Line + branch.

---

## Claude's Discretion

- Exact `--gate-mode` / `--no-gate-mode` Typer ergonomics.
- `_err_console` definition location.
- `pyproject.toml` vs `.coveragerc` for coverage config (CONTEXT.md prefers pyproject.toml).
- How to signal "no flowmap data" in the viewer payload.
- Whether to use pytest-cov's `--cov-fail-under` or a helper for per-module enforcement.

## Deferred Ideas

- Viewer surfacing of `unchanged` and `shadow` drift states.
- Exit-code contract for future new commands (automatically covered by the pattern).
- Backwards-compat shim for 3-key `drift_counts` shape (none needed — additive change).
- Pre-commit coverage hook.
- sysexits.h exit codes.
- Global (vs per-module) coverage threshold.
