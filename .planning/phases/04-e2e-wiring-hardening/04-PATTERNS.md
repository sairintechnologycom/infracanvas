# Phase 4: E2E Wiring Hardening — Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 8 files modified (no new files created)
**Analogs found:** 8 / 8 (every touched file has a strong in-file analog since Phase 4 is pure hardening of existing surfaces)

---

## File Classification

| Modified File | Role | Data Flow | Closest Analog (in-file or sibling) | Match Quality |
|---------------|------|-----------|-------------------------------------|---------------|
| `cli/infracanvas/main.py` (`export`, `scan`, `score`, `plan` bodies) | CLI command handler | request-response (stdin args → stdout/stderr) | `_run_scan()` error paths at `main.py:82-89` using `_ci_console` | exact (same file, extend pattern) |
| `cli/infracanvas/export/html.py` | exporter / utility | file-I/O (graph → HTML) | Existing `export_html()` signature already takes `gate_mode` — no change | n/a (no code change; call site in main.py) |
| `cli/infracanvas/drift/analyzer.py` | service (analyzer) | transform (graph → graph) | Lines 41-44 `drift_counts` init + accumulate | exact (extend dict literal + keep accumulator loop) |
| `cli/infracanvas/graph/models.py` (`DriftStatus`, `GraphSummary.drift`) | model (Pydantic) | n/a (data shape) | `DriftStatus` StrEnum already at lines 34-39 has all 5 values; `GraphSummary.drift` default at lines 73-75 | exact (defaults need extending only) |
| `viewer/src/App.tsx` (hash/shortcut wiring) | React root | event-driven (keyboard + hashchange listeners) | `FlowMapCanvas.tsx:205-214` (document `keydown` listener with cleanup) | exact (idiomatic useEffect + addEventListener pattern) |
| `viewer/src/components/TabBar.tsx` (disabled state + tooltip) | React component | event-driven (click, key, hover) | Same file lines 73-138 — extend per-tab rendering with disabled branch | exact (in-file extension) |
| `viewer/src/store.ts` (optional `hasFlowMap` derived) | state | n/a (store shape) | Existing `activeTab`/`setActiveTab` at lines 36, 50, 131, 135 | exact (additive) |
| `cli/tests/test_security.py` + `test_cost.py` + `test_drift.py` (parametrized rule coverage) | test suite | batch (parametrize → assert) | `cli/tests/test_flowmap_network_rules.py:116-133` (parametrize every rule × positive/negative fixture) | **exact** — Phase 4 replicates this exact pattern across all 51 rules |
| `cli/pyproject.toml` (coverage config) | build config | n/a | `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` at lines 61-80 | role-match (same `[tool.*]` convention) |

---

## Pattern Assignments

### `cli/infracanvas/main.py` — CLI error/exit contract (WRG-01)

**Analog:** same file — `_run_scan()` already mixes `console` and `_ci_console` by CI flag.

**Existing module-level consoles** (`main.py:39-40`):

```python
console = Console()
_ci_console = Console(stderr=True)  # for CI mode: diagnostics go to stderr
```

**Pattern to mirror for `_err_console`** — add a third console alongside the existing two, using the same `Console(stderr=True)` constructor. The `_ci_console` comment already sets the precedent that stderr is the structured-diagnostic channel. Phase 4 adds:

```python
_err_console = Console(stderr=True)  # for error messages (WRG-01 D-03)
```

**Existing CI-branched output pattern** (`main.py:82`, inside `_run_scan`):

```python
out = _ci_console if ci else console

try:
    parsed = parse_directory(directory)
except Exception as exc:
    out.print(f"[red]Error:[/red] Failed to parse Terraform files: {exc}")
    out.print("  Run with --verbose for details, or check that this is a valid Terraform directory.")
    raise typer.Exit(code=2)
```

**Call-sites needing migration** (grep `console.print(f"[red]Error:[/red]"` in `main.py`):

| Line | Current | New |
|------|---------|-----|
| 337-338 | `console.print(... Error ...); raise typer.Exit(code=2)` | `_err_console.print(...); raise typer.Exit(code=2)` |
| 464-465 | same (serve dir-check) | same migration |
| 565-566 | same (score dir-check) | same migration |
| 626-627 | same (plan dir-check) | same migration |
| 630-631 | same (plan planfile-missing) | `_err_console.print(...); raise typer.Exit(code=1)` |
| 751-752 | `console.print(... {report} not found); raise typer.Exit(code=1)` | `_err_console.print(...); raise typer.Exit(code=1)` |
| 758-759 | `console.print(... Invalid report file); raise typer.Exit(code=1)` | `_err_console.print(...); raise typer.Exit(code=2)` **(per D-02 — parse/validation is exit 2)** |

**Export command signature extension** (`main.py:735-748`), add `--gate-mode` option matching existing Typer `Annotated` idiom:

```python
# Existing pattern at main.py:744-747 for format flag:
format: Annotated[
    str,
    typer.Option("--format", "-f", help="Export format (json, html)"),
] = "html",
```

**New flag** (mirrors the boolean idiom used elsewhere — Typer auto-generates `--gate-mode / --no-gate-mode` from a `bool` annotation):

```python
gate_mode: Annotated[
    bool,
    typer.Option("--gate-mode/--no-gate-mode",
                 help="Enable free-tier resource gating (default: true)"),
] = True,
```

**Export call-site fix** (`main.py:763`) — currently:

```python
export_html(graph, out_path)  # missing gate_mode, takes default True
```

Becomes:

```python
export_html(graph, out_path, gate_mode=gate_mode)
```

**Exit-code contract to apply uniformly (D-02/D-04)** across `scan`/`score`/`plan`/`export`:

- `raise typer.Exit(code=0)` on success (explicit, like `main.py:366, 390`).
- `raise typer.Exit(code=1)` on missing input file (like `main.py:752`).
- `raise typer.Exit(code=2)` on parse / Pydantic validation error (like `main.py:89, 142, 338`).

Normalize `score` (line 566: currently `code=1` for not-a-dir — **change to `code=2`**) and `plan` (line 627: same fix).

---

### `cli/infracanvas/drift/analyzer.py` — 5-key drift counts (WRG-02)

**Analog:** same file, lines 41-44.

**Existing pattern**:

```python
# Update drift summary counts
drift_counts = {"added": 0, "changed": 0, "deleted": 0}
for node in graph.nodes:
    if node.drift in drift_counts:
        drift_counts[node.drift] += 1

graph.summary.drift = drift_counts
graph.summary.total_resources = len(graph.nodes)
```

**New pattern** — extend the literal to 5 keys so the `if node.drift in drift_counts` guard stops filtering out `unchanged` and `shadow`:

```python
drift_counts = {"added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0}
for node in graph.nodes:
    if node.drift in drift_counts:
        drift_counts[node.drift] += 1
```

**Invariant** (per D-05/D-09): `sum(drift_counts.values()) == len(graph.nodes)` after the loop — because every `ResourceNode.drift` is now one of the 5 enum values (and `DriftStatus.unchanged` is the Pydantic default at `models.py:61`).

---

### `cli/infracanvas/graph/models.py` — enum + summary default

**Analog:** same file.

**`DriftStatus` at lines 34-39** (already complete — 5 values present):

```python
class DriftStatus(StrEnum):
    unchanged = "unchanged"
    added = "added"
    changed = "changed"
    deleted = "deleted"
    shadow = "shadow"
```

No change needed — the canonical_refs note at CONTEXT.md line 64 was conservative; all 5 values already exist.

**`GraphSummary.drift` default at lines 73-75** (needs extension):

```python
drift: dict[str, int] = Field(
    default_factory=lambda: {"added": 0, "changed": 0, "deleted": 0}
)
```

**New default** — extend to match the new 5-key contract:

```python
drift: dict[str, int] = Field(
    default_factory=lambda: {
        "added": 0, "changed": 0, "deleted": 0, "unchanged": 0, "shadow": 0,
    }
)
```

---

### `viewer/src/App.tsx` — hash + global-shortcut wiring (WRG-03)

**Analog:** `viewer/src/components/flowmap/FlowMapCanvas.tsx:205-214` — established pattern for document-level keyboard listener with cleanup.

**Existing listener pattern** (verbatim from FlowMapCanvas):

```tsx
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      setSelectedNode(null)
      setSelectedPath(null)
    }
  }
  window.addEventListener('keydown', handler)
  return () => window.removeEventListener('keydown', handler)
}, [setSelectedNode, setSelectedPath])
```

**Copy this structure** for global `Cmd/Ctrl+\`, `1`, `2` shortcuts in `App.tsx`. Suppression rule per UI-SPEC §Interaction Contract — early return when `document.activeElement` is INPUT/TEXTAREA/SELECT or has `contentEditable === 'true'`.

**Existing App.tsx useEffect structure** (lines 29-35) to extend:

```tsx
useEffect(() => {
  const injected = window.__INFRACANVAS_DATA__;
  const data: ResourceGraph = injected ?? sampleData;
  setGraph(data);
  const gateMode = window.__INFRACANVAS_GATE__ ?? true;
  setGateMode(gateMode);
}, [setGraph, setGateMode]);
```

**New useEffects (pattern-matched on above + FlowMapCanvas)** — add three:

1. Hash init on mount + `hashchange` listener that calls `setActiveTab`.
2. `activeTab` observer that calls `history.replaceState(null, '', '#' + activeTab)`.
3. Global `keydown` listener for `Cmd/Ctrl+\`, `1`, `2`, scoped to reject when focus is in text inputs.

Each follows the `addEventListener` → return `removeEventListener` cleanup idiom from FlowMapCanvas.

---

### `viewer/src/components/TabBar.tsx` — disabled FlowMap tab (WRG-03)

**Analog:** same file, lines 73-138.

**Existing per-tab render** (abbreviated from lines 73-137):

```tsx
{TABS.map((tab, index) => {
  const isActive = activeTab === tab.id;
  return (
    <button
      key={tab.id}
      ref={(el) => { refs.current[tab.id] = el; }}
      role="tab"
      aria-selected={isActive}
      aria-controls={`panel-${tab.id}`}
      id={`tab-${tab.id}`}
      tabIndex={isActive ? 0 : -1}
      title={tab.tooltip}
      onClick={() => setActiveTab(tab.id)}
      onKeyDown={(e) => handleKey(e, index)}
      style={{
        minWidth: 120,
        padding: '0 16px',
        // ... existing style
        color: isActive ? '#F1F5F9' : '#64748B',
        borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
      }}
      onMouseEnter={(e) => { if (!isActive) { /* hover styles */ } }}
      onMouseLeave={(e) => { if (!isActive) { /* reset */ } }}
    >
      {tab.label}
      {tab.beta && ( <span /* BETA pill */ /> )}
    </button>
  );
})}
```

**Extend with disabled branch** — compute `const isDisabled = tab.id === 'flowmap' && !hasFlowMap;` and:

- Add `aria-disabled={isDisabled || undefined}`.
- Set `tabIndex={isDisabled ? -1 : (isActive ? 0 : -1)}`.
- Skip `setActiveTab` in `onClick` when disabled (or guard with `if (isDisabled) return`).
- Style color `#475569`, `cursor: 'not-allowed'`, no hover background (per UI-SPEC §Color disabled row).
- Swap `title` to the disabled copy: `"No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable."`
- Add `aria-describedby="flowmap-disabled-tooltip"` on the button and an off-screen `<span role="tooltip" id="flowmap-disabled-tooltip">` with the same copy (per UI-SPEC §Accessibility).

**`hasFlowMap` detection** — derive from `window.__INFRACANVAS_DATA__?.flowmap` at mount (App.tsx sets it via store or passes via prop — discretion per CONTEXT.md).

---

### `viewer/src/store.ts` — optional `hasFlowMap` slice

**Analog:** same file — `activeTab` / `setActiveTab` already at lines 36, 50, 131, 135.

**Existing pattern for a boolean toggle + setter** (lines 33, 47, 78, 127):

```ts
// interface
gateMode: boolean;
setGateMode: (gateMode: boolean) => void;

// initial state
gateMode: true,

// action
setGateMode: (gateMode) => set({ gateMode }),
```

**Follow this idiom if `hasFlowMap` is promoted to a store slice** (otherwise derive in-component):

```ts
hasFlowMap: boolean;
setHasFlowMap: (v: boolean) => void;

hasFlowMap: false,
setHasFlowMap: (hasFlowMap) => set({ hasFlowMap }),
```

---

### `cli/tests/test_security.py` — parametrized rule coverage (WRG-04 D-16)

**Analog:** `cli/tests/test_flowmap_network_rules.py:116-133` — already does exactly the positive + negative parametrization Phase 4 requires, just for NET-* rules.

**Existing pattern to copy** (verbatim):

```python
AWS_NET_IDS = ["NET-001", "NET-002", "NET-003", "NET-004", "NET-005", "NET-006"]

def _node_from_fixture(data: dict) -> ResourceNode:
    return ResourceNode(**data)

def _evaluate_single(node: ResourceNode) -> ResourceNode:
    """Run all security rules against a one-node graph and return the node."""
    graph = ResourceGraph(nodes=[node])
    graph = evaluate_all(graph)
    return graph.nodes[0]

class TestNetworkRuleEvaluation:
    @pytest.mark.parametrize("rule_id", AWS_NET_IDS)
    def test_aws_rule_fires_on_positive(self, rule_id: str):
        fixture = AWS_FIX[f"{rule_id}_positive"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert findings, f"{rule_id} did not fire on positive fixture"
        assert findings[0].source == "security"
        assert findings[0].framework_ids

    @pytest.mark.parametrize("rule_id", AWS_NET_IDS)
    def test_aws_rule_silent_on_negative(self, rule_id: str):
        fixture = AWS_FIX[f"{rule_id}_negative"]
        node = _evaluate_single(_node_from_fixture(fixture))
        findings = [f for f in node.findings if f.rule_id == rule_id]
        assert not findings, (
            f"{rule_id} fired on negative fixture (false positive): "
            f"{[f.evidence for f in findings]}"
        )
```

**Fixture-loading pattern** (from same file, lines 26-31):

```python
FIXTURES = Path(__file__).parent / "fixtures" / "flowmap" / "rules"

with open(FIXTURES / "aws_net_fixtures.json") as _f:
    AWS_FIX = json.load(_f)
with open(FIXTURES / "azure_net_fixtures.json") as _f:
    AZ_FIX = json.load(_f)
```

**Phase 4 replication** — enumerate `SEC-*` and `AZ-*` rule IDs via `load_rules()` at collection time (or hard-list for reviewability), create `tests/fixtures/rules/sec_fixtures.json` + `az_fixtures.json` with `{rule_id}_positive` / `{rule_id}_negative` keys matching the NET-* convention, and write twin parametrized test classes under `TestSEC_RuleEvaluation` and `TestAZ_RuleEvaluation` inside `test_security.py`.

Per-test docstring convention (per CONTEXT.md §Established Patterns — "Test IDs in docstrings"): use `SEC-R{rule_id}-POS` / `SEC-R{rule_id}-NEG` test IDs in docstrings.

**Rule count (D-16):** `ls cli/infracanvas/security/rules/{aws,azure,network}/*.yaml | wc -l` = **27 YAML files** containing the 51 rules (one YAML holds multiple rules). Phase 4 parametrizes over the 51 rule IDs, not the 27 files.

---

### `cli/tests/test_drift.py` — drift invariant property test (WRG-02 D-09)

**Analog:** same file, lines 13-33 — existing helpers `_make_graph` + `_make_change`.

**Existing pattern** (verbatim):

```python
def _make_graph(node_ids: list[str]) -> ResourceGraph:
    nodes = [
        ResourceNode(id=nid, type=nid.split(".")[0], name=nid.split(".")[1],
                     provider="aws")
        for nid in node_ids
    ]
    return ResourceGraph(nodes=nodes, summary=GraphSummary(total_resources=len(nodes)))

def _make_change(addr: str, action: DriftStatus) -> PlanChange:
    parts = addr.split(".")
    return PlanChange(resource_address=addr, resource_type=parts[0],
                      resource_name=parts[1], action=action)
```

**New property test** — add parametrized drift-mix fixtures that assert the invariant. Follow the existing `TestDriftAnalyzer` class convention (`test_drift.py:36`):

```python
@pytest.mark.parametrize("mix", [
    [],
    [("aws_instance.a", DriftStatus.changed)],
    [("aws_instance.a", DriftStatus.changed),
     ("aws_s3_bucket.b", DriftStatus.deleted),
     ("aws_nat_gateway.new", DriftStatus.added)],
    # ... add shadow-mix scenarios
])
def test_drift_counts_sum_to_node_count(mix):
    """DFT-INV-01: sum(drift_counts.values()) == len(graph.nodes) across all mixes."""
    # arrange
    graph = _make_graph(["aws_instance.a", "aws_s3_bucket.b"])
    changes = [_make_change(addr, action) for addr, action in mix]
    # act
    graph = DriftAnalyzer().apply(graph, changes)
    # assert invariant
    assert sum(graph.summary.drift.values()) == len(graph.nodes)
```

**Existing count assertions at `test_drift.py:53-73` will need updating** to also check the `unchanged` and `shadow` keys after the dict literal grows from 3 → 5.

---

### `cli/tests/test_cost.py` — baseline (no structural change, just coverage fill)

**Analog:** same file, lines 25-80 — existing `TestCostEstimator` class with `_node` helper.

**Existing pattern** (`test_cost.py:15-22`):

```python
def _node(resource_type: str, name: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}", type=resource_type, name=name,
        provider="aws", attributes=attrs,
    )
```

Coverage gap fill should follow the same `TestCostEstimator.test_<case_name>` idiom. No new structural pattern — just more of the same tests targeted at uncovered branches (use `pytest --cov=infracanvas.cost --cov-report=term-missing` to enumerate).

---

### `cli/pyproject.toml` — coverage config (WRG-04 D-14/D-15/D-17)

**Analog:** same file — `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]` at lines 61-80.

**Existing convention** (verbatim):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**New sections to add** — follow the same `[tool.<x>]` style, matching CONTEXT.md D-17 + D-15:

```toml
[tool.coverage.run]
branch = true
source = ["infracanvas"]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false
```

**Per-module enforcement (D-15)** — pytest-cov's `--cov-fail-under` is global; per-module gating requires either (a) a conftest helper that reads `coverage.json` and asserts per-path or (b) three separate `pytest --cov=infracanvas.security ...` invocations in CI. Planner's discretion per CONTEXT.md §Claude's Discretion.

**Add `pytest-cov` to `[project.optional-dependencies]`** — existing `test = ["moto>=5.1,<6", "placebo>=0.10"]` at line 50 is the slot:

```toml
test = ["moto>=5.1,<6", "placebo>=0.10", "pytest-cov>=5,<6"]
```

---

## Shared Patterns

### Stderr Routing

**Source:** `cli/infracanvas/main.py:40` (`_ci_console`)
**Apply to:** all `main.py` error-path `console.print(...)` sites that precede a `typer.Exit(code>=1)`.

```python
_err_console = Console(stderr=True)
# ...
_err_console.print(f"[red]Error:[/red] {msg}")
raise typer.Exit(code=2)
```

Established precedent: stderr = diagnostics channel. New precedent (Phase 4): stderr also = error messages, stdout stays clean for JSON / paths.

### Exit-Code Triplet

**Source:** WRG-01 + D-02, reified by existing `main.py:89, 142, 338, 366, 390, 752`.
**Apply to:** `scan`, `score`, `plan`, `export` command bodies uniformly.

| Exit | Meaning | Existing site |
|------|---------|---------------|
| 0 | success | `main.py:366, 390` |
| 1 | missing input file | `main.py:752, 630` |
| 2 | parse / validation error | `main.py:89, 142, 338` |

### Document-level Keyboard Listener + Cleanup (viewer)

**Source:** `viewer/src/components/flowmap/FlowMapCanvas.tsx:205-214`
**Apply to:** new `useEffect` in `App.tsx` for global `Cmd/Ctrl+\`, `1`, `2` shortcuts.

```tsx
useEffect(() => {
  const handler = (e: KeyboardEvent) => { /* ... */ }
  window.addEventListener('keydown', handler)
  return () => window.removeEventListener('keydown', handler)
}, [/* deps */])
```

### Parametrized rule coverage (pytest)

**Source:** `cli/tests/test_flowmap_network_rules.py:116-133` (+ fixture JSON at lines 26-31)
**Apply to:** `test_security.py` new classes for SEC-* and AZ-* rule IDs (51 total × 2 fixtures = 102 test cases).

### Test ID docstring convention

**Source:** CONTEXT.md §Established Patterns; real examples in `test_drift.py:54`, `test_security.py:67` (`"""C-001+: ..."""`).
**Apply to:** every new parametrized case (`SEC-R{rule_id}-POS`, `SEC-R{rule_id}-NEG`, `DFT-INV-01`).

---

## No Analog Found

None. Phase 4 is pure hardening — every touched surface has an existing analog in-file or in a sibling file.

---

## Metadata

**Analog search scope:**
- `cli/infracanvas/` (main.py, drift/, graph/, export/, security/, cost/)
- `cli/tests/` (test_security.py, test_drift.py, test_cost.py, test_flowmap_network_rules.py, test_shadow.py)
- `viewer/src/` (App.tsx, store.ts, components/TabBar.tsx, components/flowmap/FlowMapCanvas.tsx)
- `cli/pyproject.toml`

**Files scanned:** 14
**Pattern extraction date:** 2026-04-20
**Phase:** 04-e2e-wiring-hardening
