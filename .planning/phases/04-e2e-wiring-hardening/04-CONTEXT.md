# Phase 4: E2E Wiring Hardening - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Close 4 concrete wiring gaps (WRG-01..04) surfaced by the v1.0 post-ship review, so Phase 5+ (Viewer Extraction, SaaS Dashboard, CostLens) builds on a known-good CLI core. No new capabilities — this is pure hardening of existing surfaces: the `export` command, `DriftAnalyzer` summary, the viewer tab state, and pytest coverage for security/cost/drift modules.

</domain>

<decisions>
## Implementation Decisions

### WRG-01 — `export` command exit codes + `gate_mode`
- **D-01:** Add `--gate-mode / --no-gate-mode` flag to `infracanvas export`, default `true`. Matches existing scan/score call sites (`main.py` passes `gate_mode=True` in 3 of 4 call sites today; the `export` command at `main.py:763` doesn't pass it at all — this closes the gap).
- **D-02:** Exit code contract: `0` = success, `1` = missing input file, `2` = parse/validation error (invalid JSON, failed Pydantic validation). Matches WRG-01 literally.
- **D-03:** Errors go to **stderr**; JSON/HTML output paths and structured output go to **stdout**. Introduce a module-level `_err_console = Console(stderr=True)` mirroring the existing `_ci_console` pattern. All `console.print(f"[red]Error:[/red]...")` calls for error paths switch to `_err_console.print(...)`.
- **D-04:** Apply the exit-code + stderr contract **uniformly across all commands** (`scan`, `score`, `plan`, `export`), not just `export`. Consistent CLI surface — one contract devs/CI can rely on.

### WRG-02 — Drift counts semantics
- **D-05:** `summary.drift_counts` has **5 keys**: `added`, `changed`, `deleted`, `unchanged`, `shadow`. All five sum to `len(graph.nodes)` — the invariant is testable and mechanical.
- **D-06:** `DriftStatus` enum in `graph/models.py:34` is extended with `unchanged` (already the default per `graph/models.py:61`) and `shadow`. Drift states are **mutually exclusive** on a given `ResourceNode` — a node is exactly one of the 5 states. No orthogonal `is_shadow` flag.
- **D-07:** `shadow` means "resource exists in plan/state but not in the current scan source." Keep the semantic already implied by the existing `test_shadow.py` test file.
- **D-08:** Viewer filter/badge changes are **out of scope** for Phase 4. WRG-02 is a CLI summary fix; expanding FilterPanel/summary badges to surface `unchanged`/`shadow` is deferred to a later UI phase if needed.
- **D-09:** Invariant is expressed as a **property test**: `sum(graph.summary.drift.values()) == len(graph.nodes)` across parametrized drift-mix fixtures. One concise assertion, easy to reason about.

### WRG-03 — Canvas ↔ FlowMap tab UI
- **D-10:** Toggle lives as a **segmented control in the app header**, top-left, next to logo/title. Pattern: `[ Canvas | FlowMap ]` pill group. Always visible; doesn't compete with FilterPanel; familiar pattern (Linear, GitHub project views).
- **D-11:** Selection **persists via URL hash** (`#canvas`, `#flowmap`). Deep-linkable + shareable + reload-safe, no `localStorage` required. On mount, `activeTab` initializes from hash; switching updates hash.
- **D-12:** Keyboard shortcuts: **`Cmd/Ctrl+\`** toggles between views; **`1`** jumps to Canvas, **`2`** jumps to FlowMap. Tooltip on the tabs documents the shortcuts. Shortcuts are view-level (not swallowed inside input/select elements).
- **D-13:** When a view has no data (e.g., FlowMap tab clicked but payload has no flowmap section), **disable the tab with a tooltip**: "No FlowMap data — re-run with `infracanvas scan --with-flowmap`." Requires detecting absence of `flowmap` key in `window.__INFRACANVAS_DATA__` at mount.

### WRG-04 — Test coverage for security/cost/drift
- **D-14:** ≥80% coverage is a **CI gate** (`pytest --cov-fail-under=80`). Without enforcement, coverage erodes silently — and this phase is the gate for downstream phases treating the CLI core as stable.
- **D-15:** Thresholds are **per-module**: `security/` ≥ 80%, `cost/` ≥ 80%, `drift/` ≥ 80%, each enforced independently so a dip in one isn't masked by another's strength. Configure via `[tool.coverage.report]` paths-based thresholds (or `coverage-threshold`/conftest helper).
- **D-16:** Security test suite **parametrizes every rule** — 51 rules × (positive fixture, negative fixture) = 102 parametrized cases — so any YAML rule regression surfaces immediately. Rule-engine internals get their own unit tests separately.
- **D-17:** Coverage is **line + branch** (`[tool.coverage.run] branch = true`). Line-only would miss untested `else` arms in the drift classifier, which is exactly the kind of silent gap this phase exists to close.

### Claude's Discretion
- Exact Typer flag ergonomics for `--gate-mode` vs `--no-gate-mode` (naming, help text formatting).
- Where `_err_console` module is defined (likely `main.py` module level alongside `_ci_console`).
- How to expose "no flowmap data" — could be a boolean on `window.__INFRACANVAS_DATA__` or inferred from absence of a key. Pick whichever the viewer consumes most naturally.
- Exact location of coverage config (`pyproject.toml` under `[tool.coverage.*]` preferred over a separate `.coveragerc`, matching existing Ruff/MyPy config convention).
- Whether to use pytest-cov's `--cov-fail-under` or a standalone threshold helper for per-module enforcement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` (§ Phase 4) — goal, success criteria, dependencies
- `.planning/REQUIREMENTS.md` (WRG-01..04) — exact requirement wording
- `.planning/PROJECT.md` — v1.1 milestone context, constraints

### CLI surfaces touched by this phase
- `cli/infracanvas/main.py` (`export()` at line 735, `scan`/`score`/`plan` above) — command bodies that need exit-code + stderr updates
- `cli/infracanvas/export/html.py` (`export_html(graph, output_path, gate_mode=True)`) — existing signature, no change needed; only the call site in `main.py:763` changes
- `cli/infracanvas/drift/analyzer.py` (`drift_counts` init at line 41) — expand to 5 keys
- `cli/infracanvas/graph/models.py` (`DriftStatus` enum at line 34, `ResourceNode.drift` at line 61) — add `unchanged` (already default) and `shadow`

### Viewer surfaces touched by this phase
- `viewer/src/App.tsx` (lines 27, 37–54 — `activeTab` consumer) — header-level tab control wires here
- `viewer/src/store/useStore.ts` — `activeTab` state already exists; add hash sync + keyboard handlers
- `viewer/src/components/DetailPanel.tsx` (line 14 `activeTab`) and `viewer/src/components/flowmap/PathDetailPanel.tsx` (line 18 `activeTab`) — these are **local** component state, unrelated to the top-level tab. Do not confuse.

### Test surfaces
- `cli/tests/test_security.py`, `cli/tests/test_cost.py`, `cli/tests/test_drift.py` — existing suites to extend
- `cli/tests/test_shadow.py`, `cli/tests/test_staleness.py` — shadow drift test scaffolding already in place
- `cli/pyproject.toml` — where `[tool.coverage.run]`, `[tool.coverage.report]`, and `[tool.pytest.ini_options]` get added/updated

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ci_console = Console(stderr=True)` already exists in `main.py` for CI diagnostic routing — extend/mirror the pattern for `_err_console`.
- `export_html()` at `cli/infracanvas/export/html.py` already accepts `gate_mode: bool = True` — no signature change, only call-site fix at `main.py:763`.
- `DriftStatus(StrEnum)` at `graph/models.py:34` — extensible in place; Pydantic validation on `ResourceNode.drift` handles new variants automatically.
- Zustand `useStore` already exposes `activeTab` — hash sync and keyboard handlers attach at `App.tsx` mount, no store refactor.
- `test_shadow.py` and `test_staleness.py` exist — templates for shadow-drift test fixtures are already established.

### Established Patterns
- Python: Ruff line 100, MyPy strict, snake_case modules, `typer.Exit(code=N)` for error exits.
- TypeScript: strict mode, no semicolons, 2-space indent, Zustand for state, Tailwind for styling.
- Test IDs in docstrings (e.g., `B-001`, `E-002`) — continue for new parametrized rule tests (e.g., `SEC-R{rule_id}-POS` / `SEC-R{rule_id}-NEG`).
- Pydantic v2 `model_validate` for ingest, `StrEnum` for discriminants.

### Integration Points
- **New exit-code contract** replaces existing `console.print()` + `typer.Exit()` combos at ~10 sites across `main.py`. Grep for `raise typer.Exit` to enumerate.
- **Drift counts** lives inside `GraphSummary.drift` (dict). Viewer currently consumes only 3 keys — adding 2 keys is additive; the viewer's `FilterPanel`/summary widgets ignore unknown keys today (behavior to confirm in Phase 4 execution, not re-scope).
- **Tab control** hooks `App.tsx` header rendering. The existing `isFlowMap = activeTab === 'flowmap'` check at `App.tsx:37` needs zero change — only a new header component drives the setter.
- **Coverage config** plugs into existing `pyproject.toml` (Hatchling project) — no new tooling, just pytest-cov dependency + config.

</code_context>

<specifics>
## Specific Ideas

- The `[ Canvas | FlowMap ]` segmented control is the one UI mockup confirmed via preview selection — implement it as the header pill group, not a dropdown or sidebar affordance.
- The exit-code triplet (0/1/2) is quoted verbatim in WRG-01 — preserve exact semantics; don't introduce sysexits.h codes.
- Parametrized positive+negative fixtures for **every** security rule (51 × 2 = 102 cases) — this is a deliberate scope choice to prevent regressions when someone edits YAML.

</specifics>

<deferred>
## Deferred Ideas

- **Viewer surfacing of `unchanged` and `shadow` drift states** in FilterPanel/summary badges. Out of scope for Phase 4 (WRG-02 is CLI-only); revisit during a dedicated UI polish phase if user feedback requests it.
- **Exit-code audit of legacy commands** beyond scan/score/plan/export (e.g., a hypothetical future `watch` or `validate` command) — the contract is set uniformly; any future command adopts it automatically by following the pattern.
- **Backwards-compat shim for the 3-key `drift_counts` shape** in downstream consumers (e.g., external dashboards reading the JSON). Phase 4 is additive (new keys), not renaming — no shim needed, but note it for the Phase 6 API contract discussion.
- **Pre-commit hook for coverage gating** — reviewed, deferred. CI gate is authoritative; local pre-commit is nice-to-have, not on the critical path for Phase 4.
- **sysexits.h-style exit codes** — reviewed, rejected in favor of the simpler 0/1/2 per WRG-01.
- **Global (vs per-module) coverage threshold** — reviewed, rejected in favor of per-module gating.

</deferred>

---

*Phase: 04-e2e-wiring-hardening*
*Context gathered: 2026-04-20*
