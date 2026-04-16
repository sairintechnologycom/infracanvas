# Phase 1: Canvas MVP - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 18 new/modified files
**Analogs found:** 16 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `cli/infracanvas/main.py` | controller | request-response | self (modify existing) | exact |
| `cli/infracanvas/parser/module.py` | utility | transform | `cli/infracanvas/parser/hcl.py` | role-match |
| `cli/infracanvas/parser/state.py` | utility | transform | self (extend existing) | exact |
| `cli/infracanvas/graph/models.py` | model | transform | self (extend existing) | exact |
| `cli/infracanvas/graph/builder.py` | utility | transform | self (extend existing) | exact |
| `cli/infracanvas/security/scorer.py` | service | transform | self (realign existing) | exact |
| `cli/infracanvas/export/html.py` | utility | file-I/O | self (extend existing) | exact |
| `cli/infracanvas/export/json.py` | utility | file-I/O | self (version bump) | exact |
| `cli/infracanvas/export/scorecard.py` | utility | file-I/O | self (redesign existing) | exact |
| `viewer/src/App.tsx` | component | request-response | self (extend existing) | exact |
| `viewer/src/store.ts` | store | event-driven | self (extend existing) | exact |
| `viewer/src/types.ts` | model | transform | self (extend existing) | exact |
| `viewer/src/components/DetailPanel.tsx` | component | event-driven | self (extend existing) | exact |
| `viewer/src/components/FindingCard.tsx` | component | request-response | `viewer/src/components/FindingCard.tsx` | exact |
| `viewer/src/components/ResourceNode.tsx` | component | event-driven | self (extend existing) | exact |
| `viewer/src/lib/layout.ts` | utility | transform | self (extend existing) | exact |
| `.github/workflows/publish.yml` | config | batch | `.github/workflows/cli-release.yml` | exact |
| `cli/tests/test_*.py` (new test classes) | test | request-response | `cli/tests/test_cli.py` | role-match |

---

## Pattern Assignments

### `cli/infracanvas/main.py` (controller, request-response) — MODIFY

**Analog:** self (existing file — modify in place)

**Current imports pattern** (lines 1–29):
```python
from __future__ import annotations

import json
import sys
import time
import uuid
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from infracanvas.config import InfraCanvasConfig, load_config
from infracanvas.cost.estimator import CostEstimator
# ... all existing imports stay; add `import os` for CI detection
```

**Add `serve` command pattern — copy `_run_watch()` structure** (lines 307–356):
```python
# _run_watch() shows the exact watchdog Observer + FileSystemEventHandler pattern to reuse.
# serve command adds http.server on top of the same watchdog loop.
# New function signature:
@app.command()
def serve(
    directory: Annotated[Path, typer.Argument(help="Directory containing Terraform files")],
    port: Annotated[int, typer.Option("--port", "-p", help="HTTP port")] = 8080,
) -> None:
    """Serve a live-reloading diagram on a local HTTP server."""
```

**Watchdog Observer pattern** (lines 317–356 of main.py):
```python
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class TfChangeHandler(FileSystemEventHandler):
    def on_modified(self, event) -> None:
        nonlocal last_trigger
        if event.is_directory or not event.src_path.endswith(".tf"):
            return
        now = time.time()
        if now - last_trigger < 0.5:   # debounce — reuse 0.5s
            return
        last_trigger = now
        # rescan and overwrite output file

observer = Observer()
observer.schedule(TfChangeHandler(), str(directory), recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

**CI detection + scan default change** (lines 286–303):
```python
# CURRENT (wrong for Phase 1 — must change):
format: str = "json",   # line 227 — change default to "html"

# CURRENT browser open (lines 291–293) — extend with CI guard:
if config.open_browser:
    webbrowser.open(out_path.resolve().as_uri())

# REQUIRED pattern (add _should_open_browser() above scan command):
import os

def _should_open_browser() -> bool:
    ci_env_vars = ["CI", "GITHUB_ACTIONS", "CIRCLECI", "TRAVIS", "JENKINS_URL"]
    if any(os.environ.get(v) for v in ci_env_vars):
        return False
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False
    return True
```

**Error handling pattern** (lines 70–76):
```python
try:
    parsed = parse_directory(directory)
except Exception as exc:
    out.print(f"[red]Error:[/red] Failed to parse Terraform files: {exc}")
    out.print("  Run with --verbose for details, or check that this is a valid Terraform directory.")
    raise typer.Exit(code=2)
```

---

### `cli/infracanvas/parser/module.py` (utility, transform) — NEW FILE

**Analog:** `cli/infracanvas/parser/hcl.py`

**Imports pattern** (lines 1–12 of hcl.py):
```python
"""Recursive Terraform module resolution."""

from __future__ import annotations

from pathlib import Path

from infracanvas.parser.hcl import parse_directory, ParsedTerraform
```

**Module structure pattern — copy `_parse_file()` structure** (lines 86–99 of hcl.py):
```python
# hcl.py uses _parse_file(tf_file, result) that mutates a ParsedTerraform in place.
# module.py follows the same mutation-in-place pattern:
def resolve_modules(directory: Path, parsed: ParsedTerraform, depth: int = 0) -> None:
    """Recursively resolve local module sources into parsed. Max depth 3."""
    if depth >= 3:
        return
    # Only follow ./relative or ../relative sources — skip registry/git
    # Tag sub-resources with module path using res.module field
    # (ParsedResource.module is already defined on line 21 of hcl.py)
```

**Error handling pattern** (lines 89–91 of hcl.py):
```python
try:
    parsed = hcl2.load(f)
except Exception:
    return  # silent skip on parse error — same pattern for missing module dirs
```

**Depth guard** — no analog, use PRS-04 spec pattern from RESEARCH.md lines 323–340.

---

### `cli/infracanvas/parser/state.py` (utility, transform) — EXTEND

**Analog:** self (existing file)

**Current structure** (state.py lines 29–72): `parse_state_file()` returns `ParsedState` with `resources: list[StateResource]`. Shadow flagging requires diffing `ParsedState.resources` against the `ResourceGraph.nodes` id set.

**Pattern for shadow detection — copy drift analyzer pattern:**
```python
# cli/infracanvas/drift/analyzer.py uses graph.nodes by id — same approach for shadow:
state_ids = {r.address for r in state.resources}
graph_ids = {n.id for n in graph.nodes}
shadow_ids = state_ids - graph_ids  # in state but not in HCL → shadow infra
```

---

### `cli/infracanvas/graph/models.py` (model, transform) — EXTEND

**Analog:** self (existing file)

**Existing Pydantic model pattern** (lines 1–99):
```python
from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field

class SomeModel(BaseModel):
    field: str
    optional_field: str = ""
    list_field: list[str] = Field(default_factory=list)
    dict_field: dict[str, object] = {}
```

**Changes needed:**
1. Add `NetworkFinding` class — copy `Finding` model structure (lines 17–23), add `source_ip`, `dest_ip`, `protocol` fields.
2. Bump `ResourceGraph.version` default from `"1.0"` to `"2.0"` (line 95).
3. Add `shadow` value to `DriftStatus` StrEnum (lines 32–36) — copy existing enum pattern.

---

### `cli/infracanvas/security/scorer.py` (service, transform) — MODIFY

**Analog:** self (existing file)

**`CATEGORY_RULES` realignment** (lines 28–34):
```python
# CURRENT (wrong categories — must change):
CATEGORY_RULES: dict[str, set[str]] = {
    "Security":   {"SEC-001", "SEC-003", "SEC-004", "SEC-005", "SEC-007", "SEC-008"},
    "Encryption": {"SEC-002", "SEC-006", "SEC-009"},
    "Networking": {"SEC-010", "SEC-011", "SEC-012", "SEC-013", "SEC-014"},
    "IAM":        {"SEC-007", "SEC-008", "SEC-015", "SEC-016"},
    "Tagging":    {"SEC-010"},
}

# REQUIRED (SCR-02):
CATEGORY_RULES: dict[str, set[str]] = {
    "Security":        {"SEC-001", "SEC-003", "SEC-004", "SEC-005"},
    "Encryption":      {"SEC-002", "SEC-006", "SEC-009"},
    "IAM Hygiene":     {"SEC-007", "SEC-008"},
    "Cost Efficiency": set(),   # no rule-based findings in Phase 1; score is 100 by default
    "Tagging":         {"SEC-010"},
}
```

**`_grade()` and `Scorer.build()` patterns are correct** — copy as-is (lines 37–97). No structural changes needed.

---

### `cli/infracanvas/export/html.py` (utility, file-I/O) — EXTEND

**Analog:** self (existing file)

**Current injection pattern** (lines 9–28):
```python
TEMPLATE_PATH = Path(__file__).parent / "viewer_template.html"
PLACEHOLDER = "window.__INFRACANVAS_DATA__ = null;"

def export_html(graph: ResourceGraph, output_path: Path) -> None:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(...)
    template = TEMPLATE_PATH.read_text()
    graph_json = graph.model_dump_json()
    injected = template.replace(
        PLACEHOLDER,
        f"window.__INFRACANVAS_DATA__ = {graph_json};",
    )
    output_path.write_text(injected)
```

**Required extension — add `gate_mode` parameter:**
```python
# Add gate_mode: bool = True parameter
# Extend the replacement to also inject window.__INFRACANVAS_GATE__:
injected = template.replace(
    PLACEHOLDER,
    f"window.__INFRACANVAS_DATA__ = {graph_json}; "
    f"window.__INFRACANVAS_GATE__ = {'true' if gate_mode else 'false'};",
)
```

**Error handling pattern** (lines 17–20): `raise FileNotFoundError(...)` — keep as-is.

---

### `cli/infracanvas/export/scorecard.py` (utility, file-I/O) — REDESIGN

**Analog:** self (existing file — full rewrite of `export_scorecard()`)

**Structural HTML template pattern** (lines 57–136): The existing file already shows the self-contained HTML approach with inline `<style>` and f-string interpolation. Keep this exact approach.

**Color helper pattern** (lines 10–15):
```python
def _score_color(score: int) -> str:
    if score >= 80:
        return "#06d6a0"
    if score >= 60:
        return "#f59e0b"
    return "#ef4444"
```

**Category progress bar HTML pattern** (lines 33–45): The `cat-row` / `cat-bar-bg` / `cat-bar` structure is correct for D-08 horizontal bars. Keep this CSS. The redesign changes only the **header section** — replace the `<svg>` circle with a large letter-grade display:
```html
<!-- CURRENT: SVG circle at lines 108-116 — REPLACE with: -->
<div class="grade-block">
  <span class="grade-letter">{card.overall_grade}</span>
  <span class="numeric-score">{card.overall}/100</span>
</div>
```

**OG meta tags pattern** (lines 62–64): Keep `og:title` / `og:description` / `og:type` for social sharing (SCR-03). Add `og:image` stub.

**Footer attribution pattern** (lines 129–131): Extend existing CTA section with "Generated by InfraCanvas · infracanvas.dev" per D-09. Change CTA href to founding member Stripe page per D-02.

---

### `viewer/src/App.tsx` (component, request-response) — EXTEND

**Analog:** self (existing file)

**Data injection read pattern** (lines 11–18):
```tsx
useEffect(() => {
  const injected = window.__INFRACANVAS_DATA__;
  const data: ResourceGraph = injected ?? sampleData;
  setGraph(data);
}, [setGraph]);
```

**Required extension — read `window.__INFRACANVAS_GATE__`:**
```tsx
useEffect(() => {
  const injected = window.__INFRACANVAS_DATA__;
  const gateMode = window.__INFRACANVAS_GATE__ ?? true;  // default true (safe)
  const data: ResourceGraph = injected ?? sampleData;
  setGraph(data);
  setGateMode(gateMode);  // new store action
}, [setGraph, setGateMode]);
```

**Layout pattern** (lines 21–33): `ReactFlowProvider` wrapper + `flex flex-col h-screen w-screen` — copy exactly.

---

### `viewer/src/store.ts` (store, event-driven) — EXTEND

**Analog:** self (existing file)

**StoreState interface pattern** (lines 4–22):
```typescript
interface StoreState {
  graph: ResourceGraph | null;
  selectedNode: ResourceNode | null;
  filterPanelOpen: boolean;
  filters: Filters;
  // ADD:
  gateMode: boolean;
  // ... existing actions stay
  setGateMode: (gateMode: boolean) => void;
}
```

**Action pattern** (lines 36–38):
```typescript
// Copy this exact pattern for the new setGateMode action:
setGraph: (graph) => set({ graph }),
setSelectedNode: (node) => set({ selectedNode: node }),
// New:
setGateMode: (gateMode) => set({ gateMode }),
```

**Toggle action pattern** (lines 40–48):
```typescript
// Copy spread-merge pattern for filter toggles if adding any new filter:
toggleSeverityFilter: (sev) =>
  set((s) => ({
    filters: {
      ...s.filters,
      severities: s.filters.severities.includes(sev)
        ? s.filters.severities.filter((x) => x !== sev)
        : [...s.filters.severities, sev],
    },
  })),
```

---

### `viewer/src/types.ts` (model, transform) — EXTEND

**Analog:** self (existing file)

**Type declaration pattern** (lines 1–78):
```typescript
// All types are plain interfaces or literal union types — no classes.
// Copy this pattern for NetworkFinding:
export interface NetworkFinding {
  source_ip: string;
  dest_ip: string;
  protocol: string;
  port: number;
  severity: Severity;
  title: string;
  description: string;
}
```

**Global window declaration pattern** (lines 74–78):
```typescript
declare global {
  interface Window {
    __INFRACANVAS_DATA__: ResourceGraph | null;
    // ADD:
    __INFRACANVAS_GATE__: boolean | undefined;
  }
}
```

---

### `viewer/src/components/DetailPanel.tsx` (component, event-driven) — EXTEND

**Analog:** self (existing file)

**Store selector pattern** (lines 13–14):
```tsx
const selectedNode = useStore(s => s.selectedNode);
const setSelectedNode = useStore(s => s.setSelectedNode);
// ADD:
const gateMode = useStore(s => s.gateMode);
```

**Conditional render / early return pattern** (line 16):
```tsx
if (!selectedNode) return null;
```

**Tab sub-component pattern** (lines 192–210 — `FindingsTab`):
```tsx
// FindingsTab is a named function inside the same file.
// Gate UI is added here — follow the same pattern as the "empty state":
function FindingsTab({ node, gateMode }: { node: Pick<ResourceNodeType, 'findings'>; gateMode: boolean }) {
  if (node.findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <Shield size={24} color="#22c55e" />
        <div className="text-xs mt-2" style={{ color: '#22c55e' }}>No findings</div>
      </div>
    );
  }
  // ADD gate branch BEFORE rendering FindingCards:
  if (gateMode) {
    return (
      <GateOverlay findings={node.findings} />   // new sub-component
    );
  }
  return (
    <div>
      {node.findings.map((finding, i) => (
        <FindingCard key={`${finding.rule_id}-${i}`} finding={finding} />
      ))}
    </div>
  );
}
```

**Severity badge pattern** (lines 172–183 of DetailPanel — OverviewTab findings summary):
```tsx
// Reuse this exact badge rendering for the GateOverlay severity count display:
{(['critical', 'high', 'medium', 'info'] as const).map(sev => {
  const count = node.findings.filter(f => f.severity === sev).length;
  if (count === 0) return null;
  return (
    <span
      key={sev}
      className="text-[10px] font-medium px-1.5 py-0.5 rounded"
      style={{ background: `${severityColors[sev]}20`, color: severityColors[sev] }}
    >
      {count} {sev}
    </span>
  );
})}
```

**Inline style pattern** (throughout DetailPanel): All styles use object notation with hex color literals from `colors.ts`. No Tailwind color classes for brand colors — copy this convention.

---

### `viewer/src/components/FindingCard.tsx` (component, request-response) — GATE-AWARE EXTEND

**Analog:** self (existing file)

**Current render structure** (lines 16–73): Icon + severity badge + rule_id header, then title, description, evidence pre block, remediation.

**Gate-aware change**: The gate is applied at the `FindingsTab` level (in `DetailPanel.tsx`) — `FindingCard` itself does NOT need a gate prop. It renders fully when called. The gate simply replaces the entire list with `GateOverlay` before `FindingCard` instances are ever rendered. No change needed to `FindingCard.tsx` itself unless the planner decides severity-badge-only mode lives here.

---

### `viewer/src/components/ResourceNode.tsx` (component, event-driven) — EXTEND

**Analog:** self (existing file)

**Current icon + badge pattern** (lines 43–54):
```tsx
{findingCount > 0 && highestSev && (
  <div
    className="absolute -top-2 -right-2 flex items-center justify-center rounded-full text-[10px] font-bold text-white"
    style={{
      width: 20, height: 20,
      background: severityColors[highestSev],
      boxShadow: `0 0 6px ${severityColors[highestSev]}80`,
    }}
  >
    {findingCount}
  </div>
)}
```

**Border/drift pattern** (line 17):
```tsx
const borderColor = data.drift !== 'unchanged' ? driftColors[data.drift] : (selected ? '#60a5fa' : '#1e293b');
```

**Shadow indicator extension** — copy the drift opacity pattern (line 39):
```tsx
// Current drift=deleted uses opacity 0.5:
opacity: data.drift === 'deleted' ? 0.5 : 1,
// Shadow indicator (dashed border) copies the drift border pattern with a new color:
// if data.shadow === true: use dashed border style
border: `1.5px ${data.shadow ? 'dashed' : 'solid'} ${borderColor}`,
```

**Generic fallback node (D-06) pattern** — copy the existing AwsIcon + typeLabel structure (lines 56–77):
```tsx
// Current: always renders <AwsIcon resourceType={data.type} size={28} />
// Required: fall back gracefully when icon is unknown.
// ResourceIcon.tsx already has fallback logic — check viewer/src/components/icons/ResourceIcon.tsx
// pattern: if AwsIcon returns null/placeholder, render typeLabel text instead.
```

---

### `viewer/src/lib/layout.ts` (utility, transform) — EXTEND

**Analog:** self (existing file)

**`RESOURCE_TIER` map pattern** (lines 21–61):
```typescript
// Current: Record<string, Tier> mapping — recognised types only.
// D-06 requires unrecognised types to render (not be suppressed).
// The fallback already exists at line 99:
return RESOURCE_TIER[node.type] ?? 'private';
// This is correct — unrecognised types fall to 'private' tier. No change needed here.
```

**`SUPPRESS_AS_NODE` set pattern** (lines 64–72):
```typescript
// Structural-only types suppressed as nodes (rendered as zone containers instead).
// The final 15 resource types from RESEARCH.md must NOT be in this set.
// Verify: aws_lambda_function, aws_eks_cluster, aws_elasticache_cluster, aws_nat_gateway,
//         aws_lb, aws_db_instance, aws_kms_key, aws_cloudwatch_log_group, aws_iam_policy
//         are all absent from SUPPRESS_AS_NODE (they are — no change needed).
```

**`getResourceTier()` extension for `aws_lambda_function`** (lines 93–98):
```typescript
// Current lambda vpc-check pattern — correct as-is:
if (node.type === 'aws_lambda_function') {
  const vpc = node.attributes?.vpc_config;
  const hasVpcConfig = vpc && typeof vpc === 'object' && Object.keys(vpc as object).length > 0;
  return hasVpcConfig ? 'private' : 'regional';
}
```

---

### `.github/workflows/publish.yml` (config, batch) — NEW FILE

**Analog:** `.github/workflows/cli-release.yml` (exact match — extend, don't replace)

**Existing release workflow pattern** (cli-release.yml lines 1–46):
```yaml
name: Release CLI
on:
  push:
    tags:
      - 'v*'
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write   # required for Trusted Publisher PyPI upload
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Build viewer
        run: |
          cd viewer && npm ci && npm run build
          mkdir -p ../cli/infracanvas/export
          cp dist/index.html ../cli/infracanvas/export/viewer_template.html
      - name: Build Python package
        run: |
          cd cli
          pip install hatchling
          python -m hatchling build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: cli/dist/
      - uses: softprops/action-gh-release@v2
        with:
          files: cli/dist/*
          generate_release_notes: true
```

The `cli-release.yml` file already covers REL-03. Verify it uses semver tag trigger (`v*`) — it does (line 6). The `publish.yml` referenced in RESEARCH.md is functionally identical to the existing `cli-release.yml`. **The planner should confirm `cli-release.yml` satisfies REL-03** rather than creating a duplicate. If a separate `publish.yml` is needed, copy `cli-release.yml` exactly and rename.

---

### New Test Files (test, request-response)

**Analog:** `cli/tests/test_cli.py` and `cli/tests/test_parser.py`

**Test class + runner pattern** (test_cli.py lines 1–14):
```python
"""Tests for [feature description]."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from infracanvas.main import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


class TestServeCommand:
    def test_serve_...(self):
        """B-001: [description]."""
```

**Pytest class pattern** (test_parser.py lines 14–26):
```python
class TestModuleResolution:
    """PRS-04: Module resolution tests."""

    def test_resolves_local_module(self, tmp_path):
        """[test ID]: [description]."""
        # arrange
        # act
        # assert
```

**Fixture path pattern** (all test files):
```python
FIXTURES = Path(__file__).parent / "fixtures"
# Use tmp_path pytest fixture for writable test directories
```

**Vitest test pattern** (viewer/src/__tests__/store.test.ts lines 1–50):
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';

describe('ComponentName', () => {
  beforeEach(() => {
    useStore.setState({ /* reset state */ });
  });

  it('does expected behavior', () => {
    // arrange
    // act
    // assert
    expect(...).toBe(...);
  });
});
```

---

## Shared Patterns

### Rich Console Logging
**Source:** `cli/infracanvas/main.py` lines 38–39, 72–75
**Apply to:** All CLI Python files that produce terminal output
```python
console = Console()
_ci_console = Console(stderr=True)  # diagnostics to stderr in CI mode

# Info messages:
console.print("[cyan]Watching for changes...[/cyan]")
# Errors:
console.print(f"[red]Error:[/red] {message}")
# Warnings:
console.print(f"[yellow]Warning:[/yellow] {message}")
```

### CLI Error Exit Pattern
**Source:** `cli/infracanvas/main.py` lines 73–75, 254–255
**Apply to:** All Typer command functions
```python
if not directory.is_dir():
    console.print(f"[red]Error:[/red] {directory} is not a directory")
    raise typer.Exit(code=2)    # code=2 for user error; code=1 for findings threshold
```

### Python Module Docstring Convention
**Source:** `cli/infracanvas/export/html.py` line 1, `cli/infracanvas/parser/hcl.py` line 1
**Apply to:** All new Python files
```python
"""One-line description of what this module does."""

from __future__ import annotations
```

### Pydantic Model Pattern
**Source:** `cli/infracanvas/graph/models.py` lines 46–60
**Apply to:** Any new Python data model
```python
class NewModel(BaseModel):
    required_str: str
    optional_str: str = ""
    list_field: list[str] = Field(default_factory=list)
    dict_field: dict[str, object] = {}
    nested: OtherModel = Field(default_factory=OtherModel)
```

### Zustand Selector Pattern
**Source:** `viewer/src/components/DetailPanel.tsx` lines 13–14, `viewer/src/components/ResourceNode.tsx` line 13
**Apply to:** All React components that read store state
```typescript
// Arrow function selectors — one per value, not whole store:
const selectedNode = useStore(s => s.selectedNode);
const setSelectedNode = useStore(s => s.setSelectedNode);
```

### React Component Export Pattern
**Source:** `viewer/src/components/FindingCard.tsx` line 16, `viewer/src/components/DetailPanel.tsx` line 11
**Apply to:** All new React components
```typescript
// Named export, not default export:
export function ComponentName({ prop }: { prop: Type }) {
  // ...
  return (...);
}
// Exception: App.tsx uses default export — keep as-is
```

### Inline Style Color Convention
**Source:** `viewer/src/components/DetailPanel.tsx` lines 41–44, `viewer/src/components/FindingCard.tsx` lines 22–26
**Apply to:** All React components with brand/severity colors
```tsx
// Use style={{ }} with hex literals from colors.ts for semantic colors:
style={{ background: `${severityColors[sev]}20`, color: severityColors[sev] }}
// Use Tailwind utility classes for layout (flex, gap, padding, rounded, text size):
className="flex items-center gap-2 px-3 py-2 text-[11px] font-medium"
// Never mix: don't use Tailwind color classes like bg-red-500 for severity colors
```

### Self-Contained HTML Export Pattern
**Source:** `cli/infracanvas/export/scorecard.py` lines 57–136, `cli/infracanvas/export/html.py` lines 14–28
**Apply to:** Any new standalone HTML output file
```python
# scorecard.py pattern: build HTML string with f-string interpolation
# Include inline <style> — no external CSS dependencies
# Include OG meta tags for social sharing
# Single output_path.write_text(html) call at end of function
```

### TypeScript Type Union Pattern
**Source:** `viewer/src/types.ts` lines 1–3, 29
**Apply to:** All new TypeScript discriminated unions / enum-like types
```typescript
// Prefer literal union types over enums:
export type Severity = 'critical' | 'high' | 'medium' | 'info';
export type DriftStatus = 'unchanged' | 'added' | 'changed' | 'deleted';
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `viewer/src/components/SearchBar.tsx` | component | request-response | No search component exists anywhere in the codebase; use FilterPanel.tsx layout patterns for the input element styling only |

**Note on `SearchBar.tsx`:** VWR-05 requires a search component. The closest analog for layout/styling is `FilterPanel.tsx` (input-like toggle buttons) but there is no text input component to copy. The planner should use the established inline-style + Tailwind convention and the store selector pattern, but there is no structural analog to copy for the search interaction logic.

---

## Metadata

**Analog search scope:** `cli/infracanvas/`, `viewer/src/`, `.github/workflows/`, `cli/tests/`
**Files scanned:** 32 source files read directly
**Pattern extraction date:** 2026-04-16
