# Phase 3: FlowMap v1.0 (scope 3a) — Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 27 new/modified files
**Analogs found:** 25 / 27 (2 genuine-new patterns flagged)

## Project Constraint Reminders (from CLAUDE.md)

- **Python:** 4-space indent, line length 100 (Ruff), mypy strict, `from __future__ import annotations`, snake_case modules, PascalCase Pydantic models.
- **TypeScript:** 2-space indent, strict mode, no semicolons at EOL (idiomatic — existing viewer is mixed; DetailPanel/DiagramCanvas use semicolons; follow file-local style).
- **React:** PascalCase components, default function exports for pages / named exports for memoized children (`GroupNodeMemo`, `ResourceNodeMemo`), relative imports (no path aliases).
- **Schema versioning:** Additive JSON bump v2.0 → v2.1 on `ResourceGraph.version` — never break existing readers.
- **Pydantic ↔ TS mirror:** Every new Python model gets a matching TS interface in `viewer/src/types.ts`.
- **No new icon/font/component libraries.** Extend only.
- **Single-file HTML output:** All new viewer deps must inline cleanly via `vite-plugin-singlefile`.
- **HTML bundle budget:** < 5MB total (elkjs ~100KB gz is the only net-new).

---

## File Classification

### CLI (Python)

| File (new/modified) | Role | Data Flow | Closest Analog | Match |
|---------------------|------|-----------|----------------|-------|
| `cli/infracanvas/graph/models.py` | Pydantic model (modify) | transform | self — extend existing `ResourceGraph`, `NetworkFinding` | exact |
| `cli/infracanvas/flowmap/__init__.py` | Python package marker | — | `cli/infracanvas/shadow/__init__.py` | exact |
| `cli/infracanvas/flowmap/aws.py` | collector | request-response (AWS SDK) | `cli/infracanvas/shadow/detector.py` | exact |
| `cli/infracanvas/flowmap/azure.py` | collector | request-response (Azure SDK) | `cli/infracanvas/shadow/detector.py` | role-match (no Azure SDK analog) |
| `cli/infracanvas/flowmap/flow_logs.py` | collector (metadata only in 3a) | batch / metadata | `cli/infracanvas/shadow/detector.py` | role-match |
| `cli/infracanvas/flowmap/models_ext.py` | utility (SDK response → ResourceNode) | transform | `cli/infracanvas/shadow/detector.py` `_add_shadow_node` | role-match |
| `cli/infracanvas/security/rules/network/aws_tgw.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/aws/networking.yaml` | exact |
| `cli/infracanvas/security/rules/network/aws_vpc.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/aws/networking.yaml` | exact |
| `cli/infracanvas/security/rules/network/aws_dx.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/aws/networking.yaml` | exact |
| `cli/infracanvas/security/rules/network/azure_vwan.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/azure/network.yaml` | exact |
| `cli/infracanvas/security/rules/network/azure_vnet.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/azure/network.yaml` | exact |
| `cli/infracanvas/security/rules/network/azure_expressroute.yaml` | YAML rule | condition-check | `cli/infracanvas/security/rules/azure/network.yaml` | exact |
| `cli/infracanvas/main.py` | CLI entrypoint (modify) | request-response | self — `--shadow` flag block | exact |
| `cli/pyproject.toml` | config (modify) | — | self — `[project.optional-dependencies].shadow` | exact |
| `cli/tests/test_flowmap_aws.py` | test fixture | request-response | `cli/tests/test_shadow.py` | exact |
| `cli/tests/test_flowmap_azure.py` | test fixture | request-response | `cli/tests/test_shadow.py` | role-match |
| `cli/tests/test_flowmap_network_rules.py` | test fixture | condition-check | `cli/tests/test_security.py` | exact |
| `cli/tests/test_flowmap_integration.py` | test fixture | end-to-end | `cli/tests/test_integration.py` | role-match |

### Viewer (TypeScript/React)

| File (new/modified) | Role | Data Flow | Closest Analog | Match |
|---------------------|------|-----------|----------------|-------|
| `viewer/src/types.ts` | TS type mirror (modify) | — | self — existing interfaces | exact |
| `viewer/src/store.ts` | Zustand slice (modify) | event-driven | self — existing `filters`/`selectedNode` slices | exact |
| `viewer/src/App.tsx` | layout shell (modify) | — | self | exact |
| `viewer/src/lib/colors.ts` | constants (modify) | — | self — `severityColors`, `EDGE_STYLES` | exact |
| `viewer/src/components/TabBar.tsx` | React component | event-driven | ARIA tablist — no in-repo precedent; closest: `FilterPanel.tsx` header row | ANALOG: none — new pattern |
| `viewer/src/components/flowmap/FlowMapCanvas.tsx` | React component | transform (ReactFlow) | `viewer/src/components/DiagramCanvas.tsx` | exact |
| `viewer/src/components/flowmap/FlowMapFilterPanel.tsx` | React component | event-driven | `viewer/src/components/FilterPanel.tsx` | exact |
| `viewer/src/components/flowmap/PathDetailPanel.tsx` | React component | event-driven | `viewer/src/components/DetailPanel.tsx` | exact |
| `viewer/src/components/flowmap/FlowMapEmptyState.tsx` | React component | request-response (clipboard) | `DetailPanel.tsx` gated-findings empty card | role-match |
| `viewer/src/components/flowmap/edges/PathEdge.tsx` | React component (ReactFlow edge) | transform | `viewer/src/lib/colors.ts` `EDGE_STYLES` + ReactFlow BaseEdge | ANALOG: none — new pattern |
| `viewer/src/components/flowmap/nodes/DCSiteGroupNode.tsx` | React component (ReactFlow group) | transform | `viewer/src/components/GroupNode.tsx` | exact |
| `viewer/src/components/flowmap/nodes/RouterNode.tsx` | React component (ReactFlow node) | transform | `viewer/src/components/ResourceNode.tsx` | exact |
| `viewer/src/components/flowmap/nodes/FirewallNode.tsx` | React component (ReactFlow node) | transform | `viewer/src/components/ResourceNode.tsx` | role-match |
| `viewer/src/components/flowmap/nodes/CloudHubNode.tsx` | React component (ReactFlow node) | transform | `viewer/src/components/ResourceNode.tsx` | exact |
| `viewer/src/components/flowmap/lib/elkLayout.ts` | utility | transform | `viewer/src/lib/layout.ts` | role-match (dagre → elkjs) |
| `viewer/src/components/flowmap/lib/pathColors.ts` | constants | — | `viewer/src/lib/colors.ts` | exact |
| `viewer/src/__tests__/flowmap/FlowMapCanvas.test.tsx` | test | — | `viewer/src/__tests__/DetailPanel.test.tsx` | exact |
| `viewer/src/__tests__/flowmap/PathEdge.test.tsx` | test | — | `viewer/src/__tests__/DetailPanel.test.tsx` | role-match |
| `viewer/src/__tests__/flowmap/elkLayout.test.ts` | test | — | `viewer/src/__tests__/layout.test.ts` | exact |
| `viewer/src/__tests__/flowmap/tabBar.test.tsx` | test | — | `viewer/src/__tests__/DetailPanel.test.tsx` | role-match |
| `viewer/package.json` | config (modify) | — | self | exact |

---

## Pattern Assignments

### `cli/infracanvas/graph/models.py` (Pydantic model — modify)

**Analog:** self (additive extension — `ResourceGraph`, `Severity`, `Finding` stay as-is)

**Imports + `from __future__` header pattern** (lines 1-8):
```python
"""Pydantic v2 models for InfraCanvas resource graph."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
```

**Model pattern** (lines 10-25 — for `NetworkPath`/`PathHop`/`DCCollectorReading`/`DCSite`):
```python
class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    info = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"           # "security" | "policy"
    framework_ids: list[str] = []      # ["CIS-2.1.5", "NIST-SC-7", "SOC2-CC6.1"]
```

**Field default pattern** (lines 49-63 — use `Field(default_factory=...)` for mutable defaults):
```python
class ResourceNode(BaseModel):
    id: str
    type: str
    ...
    findings: list[Finding] = Field(default_factory=list)
    cost: CostEstimate = Field(default_factory=CostEstimate)
    drift: DriftStatus = DriftStatus.unchanged
```

**Schema bump + extension pattern** (lines 112-117 — bump `version` from `"2.0"` → `"2.1"`, append `network_paths` and `dc_sites` as empty-list defaults):
```python
class ResourceGraph(BaseModel):
    version: str = "2.0"   # ← bump to "2.1"
    metadata: dict[str, object] = Field(default_factory=dict)
    nodes: list[ResourceNode] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    summary: GraphSummary = Field(default_factory=GraphSummary)
    # ADD:
    # network_paths: list[NetworkPath] = Field(default_factory=list)
    # dc_sites: list[DCSite] = Field(default_factory=list)
```

**Existing `NetworkFinding` caveat** (lines 97-109): Old `NetworkFinding` exists but is network-layer (ip/protocol/port). Phase 3a semantics are different (graph-level). Planner's call: either (a) repurpose/extend existing `NetworkFinding`, or (b) keep it and add `RouteFinding` / `TopologyFinding`. CONTEXT.md D-10 names it `NetworkFinding` — so (a) is the decision. Fields likely to add: `path_id: str = ""`, `hop_id: str = ""`, `framework_ids: list[str] = []`.

---

### `cli/infracanvas/flowmap/aws.py` (collector — new)

**Analog:** `cli/infracanvas/shadow/detector.py` (exact match — opt-in AWS collector)

**Module docstring + imports pattern** (lines 1-14):
```python
"""Shadow infrastructure detector — compare live AWS API vs Terraform graph."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from infracanvas.graph.models import (
    CostEstimate,
    DriftStatus,
    ResourceGraph,
    ResourceNode,
)

if TYPE_CHECKING:
    pass  # boto3 types would go here with boto3-stubs
```

**Class structure + constructor pattern** (lines 37-42):
```python
class ShadowDetector:
    """Compare live AWS API vs Terraform graph nodes; flag unmanaged resources."""

    def __init__(self, region: str) -> None:
        self._region = region
```

**Lazy boto3 import + credential guard** (lines 44-57 — MUST mirror for `FlowMapAwsCollector.collect`):
```python
def detect(self, graph: ResourceGraph) -> ResourceGraph:
    """Flag shadow resources. Raises RuntimeError on missing boto3/creds."""
    try:
        import boto3  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "boto3 not installed. Install with: pip install 'infracanvas[shadow]'"
        )

    session = boto3.Session()
    creds = session.get_credentials()
    if not creds:
        raise RuntimeError(
            "--shadow requires AWS credentials. Skipping shadow scan."
        )
```

**Per-API defensive wrapper pattern** (lines 104-135 — apply to every TGW / VPC / DX describe-* call):
```python
def _detect_ec2_instances(
    self,
    graph: ResourceGraph,
    ec2: Any,
    known_names: set[str],
) -> None:
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                ...
    except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
        pass  # Non-fatal: skip this resource type on API error
```

**Node injection pattern** (lines 80-102 — for adding `aws_ec2_transit_gateway`, `aws_ec2_transit_gateway_route_table`, etc. into `graph.nodes`):
```python
def _add_shadow_node(
    self,
    graph: ResourceGraph,
    resource_type: str,
    name: str,
    attrs: dict[str, Any],
) -> None:
    """Add a shadow node to the graph."""
    node = ResourceNode(
        id=f"{resource_type}.shadow_{name}",
        type=resource_type,
        name=f"shadow_{name}",
        provider="aws",
        region=self._region,
        attributes=attrs,
        drift=DriftStatus.shadow,
        cost=CostEstimate(monthly_usd=0.0, basis="shadow estimate"),
    )
    graph.nodes.append(node)
```

**Naming note for 3a:** drop `shadow_` prefix; collected TGW/VPC/DX resources are real infrastructure, not drift. Use `id=f"{resource_type}.{name}"`. Drift status stays `DriftStatus.unchanged` unless cross-referenced against Terraform state.

---

### `cli/infracanvas/flowmap/azure.py` (collector — new)

**Analog:** `cli/infracanvas/shadow/detector.py` (role-match — no existing Azure SDK collector in repo)

**Pattern:** Same structure as `aws.py`. Mirror the lazy-import + creds-guard idiom for `azure.identity.ClientSecretCredential` + `azure.mgmt.network.NetworkManagementClient`. Import inside `collect()`, not at module level, so the `[flowmap]` extra stays optional.

**Credential guard (Azure-specific, from CONTEXT.md D-05 + Phase 2 D-07):**
```python
# Pattern to implement (no direct analog in repo):
def collect(self, graph: ResourceGraph) -> ResourceGraph:
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.network import NetworkManagementClient
    except ImportError:
        raise RuntimeError(
            "azure-mgmt-network not installed. "
            "Install with: pip install 'infracanvas[flowmap]'"
        )

    required = ["ARM_CLIENT_ID", "ARM_CLIENT_SECRET", "ARM_TENANT_ID", "ARM_SUBSCRIPTION_ID"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"--flowmap requires Azure credentials: {', '.join(missing)} missing. "
            "Skipping Azure network collection."
        )
```

**Per-resource-group defensive wrapper:** Same `try: ... except Exception: pass` shape as `shadow/detector.py` lines 134-135. Azure SDK raises `HttpResponseError` / `ResourceNotFoundError` — the broad `except Exception` (with `# noqa: BLE001`) is already the repo convention.

---

### `cli/infracanvas/flowmap/__init__.py` (package marker — new)

**Analog:** `cli/infracanvas/shadow/__init__.py` (0 bytes — empty file)

**Pattern:** Empty file. No re-exports.

---

### `cli/infracanvas/security/rules/network/aws_tgw.yaml` (YAML rule — new; same for the other 5 NET-* YAML files)

**Analog:** `cli/infracanvas/security/rules/aws/networking.yaml`

**YAML rule pattern** (lines 1-11 — replicate verbatim for each NET-* rule):
```yaml
- id: SEC-003
  title: "Security Group Allows SSH/RDP from Internet"
  severity: critical
  resource_types: ["aws_security_group"]
  framework_ids: ["CIS-5.2", "NIST-AC-17", "SOC2-CC6.6", "PCI-DSS-1.2"]
  condition:
    attribute: "ingress.cidr_blocks"
    operator: "list_contains_cidr"
    values: ["0.0.0.0/0"]
  remediation: "Restrict SSH (22) and RDP (3389) access to specific IP ranges"
  description: "Security group allows inbound SSH or RDP access from 0.0.0.0/0"
```

**Azure YAML variant** (from `cli/infracanvas/security/rules/azure/network.yaml` lines 1-11 — use for `azure_vwan.yaml`, `azure_vnet.yaml`, `azure_expressroute.yaml`):
```yaml
- id: AZ-001
  title: "NSG Allows Unrestricted Inbound Access"
  severity: critical
  resource_types: ["azurerm_network_security_group"]
  framework_ids: ["CIS-6.1", "NIST-SC-7", "SOC2-CC6.6"]
  condition:
    attribute: "security_rule.source_address_prefix"
    operator: "equals"
    value: "*"
  remediation: "Replace wildcard source with specific IP ranges or service tags"
  description: "NSG rule allows inbound access from any source address"
```

**Operators available** (from `security/engine.py` lines 49-75 — use one of these, do not invent new ones):
`equals`, `not_equals`, `in`, `not_in`, `exists`, `not_exists`, `contains`, `matches_cidr`, `list_contains_cidr`, `any_equals`.

**ID prefix for Phase 3a NET-* rules:** Use `NET-001` … `NET-012` (CONTEXT.md D-11; planner allocates path-independent subset to 3a).

**Loader discovery** (from `security/loader.py` lines 13-27): `load_rules()` uses `base_dir.rglob("*.yaml")` — any YAML file dropped into `security/rules/network/` is picked up automatically. No engine registration needed.

---

### `cli/infracanvas/main.py` (CLI entrypoint — modify)

**Analog:** self — `--shadow` flag at lines 306-309 and handler at lines 117-129

**Typer flag pattern** (lines 306-309 — add `--flowmap` immediately after `--shadow`):
```python
shadow: Annotated[
    bool,
    typer.Option("--shadow", help="Compare live AWS API vs Terraform state (requires boto3)"),
] = False,
# ADD:
# flowmap: Annotated[
#     bool,
#     typer.Option("--flowmap", help="Collect cloud network topology (AWS TGW + Azure vWAN). Beta, free during preview."),
# ] = False,
```

**Collector invocation + warn-on-fail pattern** (lines 116-129 inside `_run_scan` — mirror for `if flowmap:`):
```python
# SHD-01: Live AWS API shadow detection (opt-in)
if shadow:
    try:
        from infracanvas.shadow.detector import ShadowDetector
        inferred_region = str(graph.metadata.get("region", "")) or "us-east-1"
        # D-05: infer region from provider block in graph metadata
        for node in graph.nodes:
            if node.region:
                inferred_region = node.region
                break
        detector = ShadowDetector(region=inferred_region)
        graph = detector.detect(graph)
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] {exc}. Skipping shadow scan.")
```

**Signature update** (line 70-79 — add `flowmap: bool = False` kwarg-only param after `shadow`):
```python
def _run_scan(
    directory: Path,
    severity_filter: Optional[str] = None,
    ignore_rules: Optional[list[str]] = None,
    *,
    allow_empty: bool = False,
    ci: bool = False,
    shadow: bool = False,
    # ADD: flowmap: bool = False,
    policy: Optional[Path] = None,
) -> ResourceGraph:
```

**Pass-through wiring** (line 333-335 — add `flowmap=flowmap` to the `_run_scan()` call in the `scan` command body).

---

### `cli/tests/test_flowmap_aws.py` (pytest — new)

**Analog:** `cli/tests/test_shadow.py`

**Test header + fixtures pattern** (lines 1-17):
```python
"""Tests for shadow infrastructure detector (SHD-01, SHD-02)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode


def _node(resource_type: str, name: str = "test") -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes={},
    )
```

**Missing-SDK and missing-creds assertion pattern** (lines 20-41 — replicate for boto3 AND azure-identity in flowmap tests):
```python
class TestShadowDetectorImport:
    def test_missing_boto3_raises_runtime_error(self):
        """SHD-001-A: RuntimeError when boto3 not installed."""
        from infracanvas.shadow.detector import ShadowDetector
        with patch.dict("sys.modules", {"boto3": None}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[_node("aws_instance", "web")])
            with pytest.raises(RuntimeError, match="boto3 not installed"):
                detector.detect(graph)

    def test_no_credentials_raises_runtime_error(self):
        """SHD-001-B: RuntimeError when no AWS credentials."""
        ...
        mock_session.get_credentials.return_value = None
        ...
        with pytest.raises(RuntimeError, match="AWS credentials"):
            detector.detect(graph)
```

**Mock session helper pattern** (lines 44-72 — replicate for boto3 EC2 TGW + DX clients):
```python
def _mock_boto3_session(self):
    """Create a mock boto3 session with empty API responses."""
    mock_boto3 = MagicMock()
    mock_session = MagicMock()
    mock_creds = MagicMock()
    mock_session.get_credentials.return_value = mock_creds
    mock_boto3.Session.return_value = mock_session
    ...
    mock_session.client.side_effect = lambda svc, **kw: {
        "ec2": mock_ec2, "s3": mock_s3, "rds": mock_rds,
    }.get(svc, MagicMock())
    return mock_boto3, mock_ec2, mock_s3, mock_rds
```

**Fixture strategy note (RESEARCH.md §Standard Stack):** Use hybrid `moto` + `placebo` per the researcher's recommendation. moto for stable shapes, placebo-recorded JSON for TGW `search_transit_gateway_routes` + Direct Connect where moto coverage lags.

---

### `cli/tests/test_flowmap_network_rules.py` (pytest — new)

**Analog:** `cli/tests/test_security.py`

**Test scaffold pattern** (lines 1-20):
```python
"""Tests for the security rules engine (Suite C)."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import Finding, ResourceGraph, ResourceNode, Severity
from infracanvas.parser.hcl import parse_directory
from infracanvas.security.engine import _evaluate_rule, evaluate_all
from infracanvas.security.loader import load_rules
from infracanvas.security.models import RuleCondition, SecurityRule

FIXTURES = Path(__file__).parent / "fixtures"


def _scan_fixture(name: str):
    """Helper: parse → build → evaluate a fixture."""
    parsed = parse_directory(FIXTURES / name)
    graph = build_graph(parsed)
    return evaluate_all(graph)
```

**Rule count / ID / severity assertions pattern** (lines 22-48 — for NET-001..NET-0NN):
```python
class TestRuleLoader:
    def test_loads_all_rules(self):
        rules = load_rules()
        assert len(rules) == 40   # update count when NET-* added

    def test_rule_ids(self):
        rules = load_rules()
        rule_ids = {r.id for r in rules}
        for i in range(1, 11):
            assert f"SEC-{i:03d}" in rule_ids
        # ADD: for i in range(1, NET_3A_COUNT + 1): assert f"NET-{i:03d}" in rule_ids
```

---

### `cli/tests/test_flowmap_integration.py` (pytest — new)

**Analog:** `cli/tests/test_integration.py` (role-match — existing is end-to-end parse → build → evaluate → export). Reuse the FIXTURES pattern and add a fixture that exercises `_run_scan(flowmap=True)` with a mocked `FlowMapAwsCollector`.

---

### `cli/pyproject.toml` (config — modify)

**Analog:** self — existing `[project.optional-dependencies]` block

**Extras pattern to extend** (from RESEARCH.md §Installation — verified against pyproject.toml structure):
```toml
[project.optional-dependencies]
shadow = ["boto3>=1.40,<2", "boto3-stubs[ec2,s3,rds]>=1.40"]
flowmap = [
    "boto3>=1.40,<2",
    "boto3-stubs[ec2,s3,rds,directconnect]>=1.40",
    "azure-identity>=1.20,<2",
    "azure-mgmt-network>=28,<31",
    "azure-mgmt-resource>=23,<26",
]
test = ["moto>=5.1,<6", "placebo>=0.10"]
```

---

### `viewer/src/types.ts` (TS type mirror — modify)

**Analog:** self (additive)

**Existing interface style to mirror** (lines 5-26 — `Finding` and `NetworkFinding`):
```typescript
export interface Finding {
  rule_id: string;
  severity: Severity;
  title: string;
  description: string;
  remediation: string;
  evidence: Record<string, unknown>;
  source?: string;              // 'security' | 'policy'
  framework_ids?: string[];     // ['CIS-2.1.5', 'NIST-SC-7']
}

export interface NetworkFinding {
  source_ip: string;
  dest_ip: string;
  protocol: string;
  port: number;
  severity: Severity;
  title: string;
  description: string;
  remediation?: string;
  evidence?: Record<string, unknown>;
}
```

**ResourceGraph extension pattern** (lines 80-86 — add `network_paths` and `dc_sites` as required fields with default `[]` semantics, matching the Python model):
```typescript
export interface ResourceGraph {
  version: string;
  metadata: GraphMetadata;
  nodes: ResourceNode[];
  edges: GraphEdge[];
  summary: GraphSummary;
  // ADD:
  // network_paths: NetworkPath[];
  // dc_sites: DCSite[];
}
```

**TS convention for string union + Record** (line 1, 66): use literal union types (`'critical' | 'high' | 'medium' | 'info'`) and `Record<string, unknown>` for arbitrary attribute blobs.

---

### `viewer/src/store.ts` (Zustand slice — modify)

**Analog:** self (existing Filters/selectedNode slice)

**Slice definition pattern** (lines 1-28):
```typescript
import { create } from 'zustand';
import type { DriftStatus, ResourceGraph, ResourceNode, Severity } from './types';

interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
  sources: string[];
}

interface StoreState {
  graph: ResourceGraph | null;
  selectedNode: ResourceNode | null;
  filterPanelOpen: boolean;
  filters: Filters;
  gateMode: boolean;
  searchQuery: string;
  setGraph: (graph: ResourceGraph) => void;
  setSelectedNode: (node: ResourceNode | null) => void;
  toggleFilterPanel: () => void;
  toggleSeverityFilter: (sev: Severity) => void;
  ...
}
```

**Toggle action pattern** (lines 49-57 — immutable array update; replicate for each new `flowMapFilters` section):
```typescript
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

**Clear-all pattern** (lines 30-35, 89 — use `emptyFilters` object + `set({ filters: { ...emptyFilters } })`):
```typescript
const emptyFilters: Filters = { severities: [], resourceTypes: [], driftStatuses: [], sources: [] };
...
clearFilters: () => set({ filters: { ...emptyFilters } }),
```

**New slices to add (per CONTEXT.md D-06 + UI-SPEC §Interaction Contracts):**
- `activeTab: 'canvas' | 'flowmap'` (default `'canvas'`)
- `setActiveTab: (tab: 'canvas' | 'flowmap') => void`
- `flowMapFilters: { severities: Severity[]; cloud: 'aws'|'azure'|'both'; nodeTypes: string[]; hasFlowLogs: boolean }`
- `toggleFlowMapSeverity`, `setFlowMapCloud`, `toggleFlowMapNodeType`, `toggleFlowMapFlowLogs`, `clearFlowMapFilters`
- `selectedPath: NetworkPath | null` (cold in 3a)
- `setSelectedPath: (p: NetworkPath | null) => void`

---

### `viewer/src/App.tsx` (layout shell — modify)

**Analog:** self

**Injection + conditional render pattern** (lines 11-37):
```tsx
export default function App() {
  const setGraph = useStore(s => s.setGraph);
  const setGateMode = useStore(s => s.setGateMode);

  useEffect(() => {
    const injected = window.__INFRACANVAS_DATA__;
    const data: ResourceGraph = injected ?? sampleData;
    setGraph(data);
    const gateMode = window.__INFRACANVAS_GATE__ ?? true;
    setGateMode(gateMode);
  }, [setGraph, setGateMode]);

  return (
    <ReactFlowProvider>
      <div className="flex flex-col h-screen w-screen" style={{ background: '#f8fafc' }}>
        <SummaryBar />
        <div className="flex flex-1 min-h-0">
          <FilterPanel />
          <div className="flex-1 min-w-0">
            <DiagramCanvas />
          </div>
          <DetailPanel />
        </div>
      </div>
    </ReactFlowProvider>
  );
}
```

**Modification pattern:** Insert `<TabBar />` between `<SummaryBar />` and the 3-column `<div className="flex flex-1 min-h-0">`. Inside that div, conditionally swap `<DiagramCanvas />` for `<FlowMapCanvas />` and `<FilterPanel />` for `<FlowMapFilterPanel />` and `<DetailPanel />` for `<PathDetailPanel />` based on `activeTab` from the store. Fixed sidebar widths (224px + 320px) must be preserved to prevent reflow (UI-SPEC D-06 §Interaction Contracts step 4).

---

### `viewer/src/components/flowmap/FlowMapCanvas.tsx` (React component — new)

**Analog:** `viewer/src/components/DiagramCanvas.tsx` (exact)

**Component scaffold pattern** (lines 1-32):
```tsx
import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  BackgroundVariant,
  type NodeTypes,
  type NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { ResourceNodeMemo } from './ResourceNode';
import { GroupNodeMemo } from './GroupNode';
import { buildFlowElements } from '../lib/layout';
import { useStore } from '../store';
import type { ResourceNode } from '../types';

const nodeTypes: NodeTypes = {
  resource: ResourceNodeMemo,
  group: GroupNodeMemo,
};

export function DiagramCanvas() {
  const graph = useStore(s => s.graph);
  ...
  const { fitView } = useReactFlow();
```

**Layout memo + graph change effect** (lines 34-48 — replace `buildFlowElements` with `elkLayout` for FlowMap):
```tsx
const { initialNodes, initialEdges } = useMemo(() => {
  if (!graph) return { initialNodes: [], initialEdges: [] };
  const { nodes, edges } = buildFlowElements(graph);
  return { initialNodes: nodes, initialEdges: edges };
}, [graph]);

const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

// Recompute when graph changes
useEffect(() => {
  setNodes(initialNodes);
  setEdges(initialEdges);
  setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 100);
}, [initialNodes, initialEdges, setNodes, setEdges, fitView]);
```

**Filter dimming pattern** (lines 51-71 — reuse verbatim with `flowMapFilters` as input):
```tsx
useEffect(() => {
  const query = searchQuery.toLowerCase().trim();
  setNodes(nds =>
    nds.map(node => {
      if (node.type !== 'resource') return node;
      const data = node.data as unknown as ResourceNode;
      const visible = isNodeVisible(data, filters);
      const matchesSearch = query === '' ||
        data.name.toLowerCase().includes(query) ||
        data.type.toLowerCase().includes(query);
      return {
        ...node,
        style: {
          ...node.style,
          opacity: visible && matchesSearch ? 1 : 0.2,
          transition: 'opacity 0.2s',
        },
      };
    })
  );
}, [filters, searchQuery, setNodes]);
```

**ReactFlow render pattern** (lines 87-131 — reuse `Background`/`Controls`/`MiniMap` configuration exactly; UI-SPEC mandates visual parity):
```tsx
<ReactFlow
  nodes={nodes}
  edges={edges}
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
  onNodeClick={onNodeClick}
  onPaneClick={onPaneClick}
  nodeTypes={nodeTypes}
  defaultEdgeOptions={{ type: 'smoothstep' }}
  connectionLineStyle={{ stroke: '#94A3B8', strokeWidth: 1 }}
  fitView
  fitViewOptions={{ padding: 0.15 }}
  minZoom={0.2}
  maxZoom={2}
  proOptions={{ hideAttribution: true }}
>
  <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#DDE2E8" />
  <Controls position="bottom-left" showInteractive={false} />
  <MiniMap
    position="bottom-right"
    nodeColor={(node) => { ... }}
    maskColor="rgba(255,255,255,0.6)"
    pannable
    zoomable
  />
</ReactFlow>
```

**FlowMap-specific overrides:**
- `nodeTypes` map adds `cloudHub`, `router`, `firewall`, `dcSiteGroup` (see node components below).
- `defaultEdgeOptions` keeps `type: 'smoothstep'` but `edgeTypes` map adds `path: PathEdge`.
- `MiniMap.nodeColor` per UI-SPEC §FlowMapCanvas: AWS `#FF9900`, Azure `#0078D4`, DC `#64748B`, firewall `#DD344C`.

---

### `viewer/src/components/flowmap/FlowMapFilterPanel.tsx` (React component — new)

**Analog:** `viewer/src/components/FilterPanel.tsx` (exact)

**Panel shell pattern** (lines 30-55 — reuse verbatim; this is the locked visual contract per UI-SPEC D4/D5 sign-off):
```tsx
if (!filterPanelOpen || !graph) return null;
...
return (
  <div
    className="w-56 shrink-0 overflow-y-auto z-10"
    style={{
      background: '#161b27',
      borderRight: '1px solid #252d3d',
    }}
  >
    {/* Header */}
    <div className="flex items-center justify-between p-3" style={{ borderBottom: '1px solid #252d3d' }}>
      <span className="text-xs font-semibold" style={{ color: '#e2e8f0' }}>Filters</span>
      <div className="flex items-center gap-2">
        {hasActiveFilters && (
          <button onClick={clearFilters} ...>Clear</button>
        )}
        <button onClick={toggleFilterPanel} ...>
          <X size={14} />
        </button>
      </div>
    </div>
```

**Section block pattern** (lines 57-87 — replicate 4 times for Severity / Cloud / Node Type / Has Flow Logs):
```tsx
<div className="p-3" style={{ borderBottom: '1px solid #252d3d' }}>
  <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: '#4a5568' }}>
    Severity
  </div>
  <div className="flex flex-col gap-1">
    {severities.map(sev => {
      const isActive = filters.severities.includes(sev);
      const count = graph.nodes.reduce((acc, n) =>
        acc + n.findings.filter(f => f.severity === sev).length, 0
      );
      return (
        <label key={sev} className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5" ...>
          <input type="checkbox" checked={isActive} onChange={() => toggleSeverityFilter(sev)} ... />
          <span className="flex-1 capitalize">{sev}</span>
          <span className="text-[10px]" style={{ color: '#374151' }}>{count}</span>
        </label>
      );
    })}
  </div>
</div>
```

**Cloud tri-state radio pills (UI-SPEC §FlowMapFilterPanel) — no in-repo analog; nearest reference is the severity chip idiom. Model as checkbox list with mutually-exclusive click handler in the store action.**

---

### `viewer/src/components/flowmap/PathDetailPanel.tsx` (React component — new)

**Analog:** `viewer/src/components/DetailPanel.tsx` (exact)

**Panel shell + tabs pattern** (lines 32-96):
```tsx
return (
  <div
    className="w-80 shrink-0 flex flex-col overflow-hidden z-10"
    style={{ background: '#161b27', borderLeft: '1px solid #252d3d' }}
  >
    {/* Header */}
    <div className="p-4" style={{ borderBottom: '1px solid #252d3d' }}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <ResourceIcon resourceType={node.type} size={28} />
          <div>
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                  style={{ background: `${color}20`, color }}>
              {typeLabel}
            </span>
          </div>
        </div>
        <button onClick={() => setSelectedNode(null)} ...><X size={16} /></button>
      </div>
      <div className="font-semibold text-sm" style={{ color: '#e2e8f0' }}>{node.name}</div>
      <div className="text-[11px] font-mono mt-0.5" style={{ color: '#4a5568' }}>{node.id}</div>
    </div>

    {/* Tabs */}
    <div className="flex" style={{ borderBottom: '1px solid #252d3d' }}>
      {tabs.map(tab => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center gap-1 px-3 py-2 text-[11px] font-medium cursor-pointer transition-colors flex-1 justify-center"
            style={{
              color: isActive ? '#e2e8f0' : '#4a5568',
              borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
              background: isActive ? `${color}10` : 'transparent',
            }}
          >
            <Icon size={12} />
            {tab.label}
          </button>
        );
      })}
    </div>
```

**Tabs list pattern** (lines 23-30 — pattern to add the new `Routes` tab when node is TGW / VPC / vWAN hub):
```tsx
const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
  { id: 'attributes', label: 'Attributes', icon: Code },
  ...(driftChanges.length > 0
    ? [{ id: 'changes' as const, label: `Changes (${driftChanges.length})`, icon: GitCompare }]
    : []),
];
```

**FindingsTab reuse note:** `FindingCard` (lines 192-252 of DetailPanel.tsx) is reused **verbatim** per UI-SPEC §PathDetailPanel — NET-* findings are shape-compatible with the `Finding` interface. Do not fork.

---

### `viewer/src/components/flowmap/FlowMapEmptyState.tsx` (React component — new)

**Analog:** `DetailPanel.tsx` gated-findings empty card (lines 205-242 — similar centered empty-state card with CTA button)

**Centered card + CTA pattern:**
```tsx
return (
  <div className="flex flex-col items-center gap-2 py-4 px-3">
    <Shield size={16} style={{ color: '#4a5568' }} />
    <div className="text-xs font-semibold" style={{ color: '#e2e8f0' }}>
      {node.findings.length} finding{node.findings.length !== 1 ? 's' : ''}
    </div>
    <a
      href="..."
      className="text-xs font-semibold px-4 py-2 rounded-md mt-1 inline-block"
      style={{ background: '#3b82f620', border: '1px solid #3b82f6', color: '#60a5fa' }}
    >
      Unlock details — founding member $49/mo
    </a>
  </div>
);
```

**FlowMap empty-state specifics:** UI-SPEC §FlowMapEmptyState locks the exact copy (`No network topology collected yet`), the CLI command block styling (`#0F172A` bg, mono 12px, Copy button), and the `Beta · free during preview` pill. Use `navigator.clipboard.writeText` with a 2s morph to `Copied ✓` for the Copy button.

---

### `viewer/src/components/flowmap/edges/PathEdge.tsx` (ReactFlow edge — new)

**ANALOG: none — new pattern** (no custom ReactFlow edge exists in repo). Closest conceptual neighbour: `viewer/src/lib/colors.ts` `EDGE_STYLES` object (lines 28-54) which defines edge stroke/dash/marker conventions as static objects — PathEdge extends this into a full BaseEdge component.

**Existing edge-style convention to match** (`colors.ts` lines 28-54):
```typescript
export const EDGE_STYLES: Record<EdgeRelationship, null | {
  style: Record<string, unknown>;
  markerEnd?: { type: MarkerType; color: string };
  animated: boolean;
  labelStyle?: Record<string, unknown>;
}> = {
  containment: null,
  attachment: {
    style: { stroke: 'rgba(71,85,105,0.6)', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(71,85,105,0.6)' },
    animated: false,
  },
  ...
};
```

**Implementation contract (from RESEARCH.md + UI-SPEC §PathEdge):** Two stacked `<BaseEdge>` children using ReactFlow 12's `getSmoothStepPath` helper. Forward path translates `-3px` Y, return path translates `+3px` Y (6px perpendicular separation). Forward stroke `#3B82F6` + `markerEnd` arrow; return stroke `#F97316` + `markerStart` arrow. In 3a `network_paths` is empty so this component is cold-path but still ships with unit tests against synthetic fixtures.

---

### `viewer/src/components/flowmap/nodes/DCSiteGroupNode.tsx` (ReactFlow group — new)

**Analog:** `viewer/src/components/GroupNode.tsx` (exact)

**Group-node structural pattern** (lines 1-27):
```tsx
import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ZONE_COLORS, type ZoneType } from '../lib/colors';
import type { Provider } from '../lib/providerTheme';

type GroupNodeProps = NodeProps & {
  data: {
    label: string;
    zoneType: ZoneType;
    chip?: string;
    cidr?: string;
    provider?: Provider;
  };
};

function GroupNodeComponent({ data }: GroupNodeProps) {
  const baseZone = ZONE_COLORS[data.zoneType] ?? ZONE_COLORS.regional;
  const isCloud = data.zoneType === 'cloud';
  ...
}

export const GroupNodeMemo = memo(GroupNodeComponent);
```

**Outer rectangle + label-tab pattern** (lines 40-83 — the "dashed border + label-tab at top-left" pattern is exactly the DCSite outer shell spec in UI-SPEC §DCSiteGroupNode):
```tsx
return (
  <div
    style={{
      width: '100%',
      height: '100%',
      background: 'transparent',
      border: `${baseZone.borderWidth} ${baseZone.borderStyle} ${borderColor}`,
      borderRadius: isCategory ? 6 : isCloud ? 14 : 10,
      position: 'relative',
      boxSizing: 'border-box',
    }}
  >
    {/* Label tab — anchored straddling the top-left border like AWS ref diagrams */}
    <div style={{ position: 'absolute', top: -10, left: 14, display: 'flex', gap: 5 }}>
      <span
        style={{
          fontSize: tabFontSize,
          fontWeight: 600,
          fontFamily: 'ui-monospace, ...',
          color: labelColor,
          background: '#FFFFFF',
          border: `1px solid ${borderColor}`,
          padding: tabPadding,
          ...
        }}
      >
        {data.label}
      </span>
    </div>
```

**Memoization + default export pattern** (line 124): Export as `GroupNodeMemo` via `memo(GroupNodeComponent)`. DCSiteGroupNode follows the same `DCSiteGroupNodeMemo` convention.

---

### `viewer/src/components/flowmap/nodes/RouterNode.tsx`, `FirewallNode.tsx`, `CloudHubNode.tsx` (ReactFlow nodes — new)

**Analog:** `viewer/src/components/ResourceNode.tsx` (exact for RouterNode and CloudHubNode, role-match for FirewallNode with added capacity gauge)

**Node scaffold pattern** (lines 1-22):
```tsx
import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { detectProvider } from '../lib/providerTheme';
import { ServiceIcon } from './icons/ServiceIcon';
import { useStore } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

// Must match layout.ts NODE_W / NODE_H so the layout math is truthful.
const NODE_W = 120;
const NODE_H = 90;
const ICON_SIZE = 40;

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useStore(s => s.setSelectedNode);
  ...
```

**Selection ring pattern** (lines 74-81 — reuse for all FlowMap nodes; UI-SPEC locks the 2px `#3B82F6` selected outline):
```tsx
boxShadow: selected
  ? '0 0 0 2px #3B82F6, 0 0 0 5px rgba(59,130,246,0.18)'
  : driftTint
  ? `0 0 0 2px ${driftTint}`
  : 'none',
```

**Severity badge pattern** (lines 120-143 — floating top-right badge with count — reuse verbatim; NET-* findings use the same Finding shape so this works):
```tsx
{findingCount > 0 && highestSev && (
  <div
    style={{
      position: 'absolute',
      top: -4,
      right: 22,
      minWidth: 18,
      height: 18,
      padding: '0 5px',
      borderRadius: 9,
      background: severityColors[highestSev],
      color: '#ffffff',
      fontSize: 10,
      fontWeight: 800,
      ...
      boxShadow: `0 1px 3px ${severityColors[highestSev]}66, 0 0 0 2px #FFFFFF`,
    }}
  >
    {findingCount}
  </div>
)}
```

**Handles pattern** (lines 59-63, 145-149 — top-target + bottom-source handles for ReactFlow connection):
```tsx
<Handle type="target" position={Position.Top} className="!bg-slate-400 !border-slate-500 !w-2 !h-2" />
...
<Handle type="source" position={Position.Bottom} className="!bg-slate-400 !border-slate-500 !w-2 !h-2" />
```

**FirewallNode-specific addition (UI-SPEC §FirewallNode, FMV-04):** Mini progress bar 140×6 with three-band fill (`#22C55E` / `#F59E0B` / `#EF4444`). No existing analog — hand-build inside the bottom row of the card. Hide below zoom 0.7x (tracked in `flow.getZoom()` or via `useStore` custom subscription).

---

### `viewer/src/components/flowmap/lib/elkLayout.ts` (utility — new)

**Analog:** `viewer/src/lib/layout.ts` (role-match — existing file computes dagre-like tier layout; 675 lines of `buildFlowElements`)

**Constants header pattern** (`layout.ts` lines 1-35):
```typescript
import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { ResourceGraph, ResourceNode as ResourceNodeData, GraphEdge } from '../types';
import type { ZoneType } from './colors';
import { detectProvider, PROVIDER_THEMES, type Provider } from './providerTheme';

// Layout constants — must match ResourceNode.tsx NODE_W / NODE_H exactly.
const NODE_W = 120;
const NODE_H = 90;
const NODE_GAP = 28;
...
```

**Pattern for elkLayout.ts:** Export a single async function `layoutFlowMap(graph: ResourceGraph) => Promise<{ nodes: Node[]; edges: Edge[] }>` that calls elkjs and returns ReactFlow-shaped `Node`/`Edge` arrays. Per RESEARCH.md, config is `elk.algorithm: 'layered'`, `elk.direction: 'RIGHT'`, `elk.spacing.nodeNode: 80`, `elk.layered.spacing.nodeNodeBetweenLayers: 120`. Budget < 500ms for 200 nodes.

---

### `viewer/src/components/flowmap/lib/pathColors.ts` (constants — new)

**Analog:** `viewer/src/lib/colors.ts` (exact — same `as const` export idiom)

**Export pattern** (per UI-SPEC §Color):
```typescript
// Add to colors.ts or new pathColors.ts
export const flowmapPathColors = {
  forward:    '#3B82F6',
  return:     '#F97316',
  divergence: '#EF4444',
  flowOk:     '#22C55E',
  flowStale:  '#94A3B8',
} as const
```

**Existing `severityColors` shape to mirror** (lines 4-10):
```typescript
export const severityColors: Record<Severity | 'clean', string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  info: '#3b82f6',
  clean: '#22c55e',
};
```

---

### `viewer/src/components/TabBar.tsx` (React component — new)

**ANALOG: none — new pattern** (no ARIA tablist component exists in repo). Closest conceptual neighbours:

1. **`FilterPanel.tsx` header row** (lines 38-55) — dark chrome with button styling idioms. Reuse background `#161b27`, border `#252d3d`, text `#e2e8f0` tokens.
2. **`DetailPanel.tsx` tabs** (lines 66-87) — in-panel tab strip with active-underline + light background. Reuse the "2px solid underline + background tint" active-state pattern:

```tsx
<button
  onClick={() => setActiveTab(tab.id)}
  className="flex items-center gap-1 px-3 py-2 text-[11px] font-medium cursor-pointer transition-colors flex-1 justify-center"
  style={{
    color: isActive ? '#e2e8f0' : '#4a5568',
    borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
    background: isActive ? `${color}10` : 'transparent',
  }}
>
```

**Net-new requirements (UI-SPEC §TabBar):** `role="tablist"`, `role="tab"`, `aria-selected`, Arrow-Left/Arrow-Right keyboard nav, `BETA` pill on the FlowMap tab. Use accent `#3B82F6` for the active underline (UI-SPEC §Color accent reservation #2).

---

### `viewer/src/__tests__/flowmap/*.test.tsx` (tests — new)

**Analog:** `viewer/src/__tests__/DetailPanel.test.tsx`

**Test scaffold pattern** (lines 1-6, 28-37):
```tsx
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { Finding } from '../types'

import { FindingCard } from '../components/FindingCard'

describe('DetailPanel ChangesTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders Changes tab alongside Findings tab', () => {
    ...
  })
})
```

**Assertion idioms to reuse:**
- `expect(screen.getByText('POLICY')).toBeInTheDocument()` (presence)
- `expect(screen.queryByText('POLICY')).not.toBeInTheDocument()` (absence)
- `render(<Component prop={value} />)` (no provider wrapping needed because components that consume Zustand reach it via `useStore` directly).

---

### `viewer/src/lib/colors.ts` (constants — modify)

**Analog:** self

**Extension pattern** (add at end of file, keep existing exports untouched):
```typescript
// FlowMap Phase 3a additions
export const flowmapPathColors = {
  forward:    '#3B82F6',
  return:     '#F97316',
  divergence: '#EF4444',
  flowOk:     '#22C55E',
  flowStale:  '#94A3B8',
} as const
```

**`viewer/src/index.css` @theme block extension (UI-SPEC §Design System Alignment):**
```css
--color-flow-forward: #3B82F6;
--color-flow-return:  #F97316;
--color-flow-divergence: #EF4444;
```

---

### `viewer/package.json` (config — modify)

**Analog:** self

**Pattern:** Add single dep `"elkjs": "^0.11.1"` to `dependencies`. No devDeps change needed (vitest / @testing-library already present).

---

## Shared Patterns (Cross-Cutting)

### Opt-in cloud collection + warn-on-missing

**Source:** `cli/infracanvas/main.py` lines 117-129 + `cli/infracanvas/shadow/detector.py` lines 44-57

**Apply to:** Every cloud collector in `cli/infracanvas/flowmap/` and the `--flowmap` flag handler in `main.py`

**Contract:**
1. Lazy-import SDK inside function body (not module-level).
2. Raise `RuntimeError` on missing SDK with install instruction referencing the extras group: `pip install 'infracanvas[flowmap]'`.
3. Raise `RuntimeError` on missing credentials.
4. Top-level `main.py` catches `RuntimeError` and prints `[yellow]Warning:[/yellow] {exc}. Skipping flowmap collection.` — **never hard-fail**.

### Defensive API wrapper

**Source:** `cli/infracanvas/shadow/detector.py` lines 104-135, 137-155, etc.

**Apply to:** Every individual AWS / Azure SDK call inside `flowmap/aws.py` and `flowmap/azure.py`.

**Contract:**
```python
try:
    response = client.describe_thing()
    for item in response.get("Things", []):
        ...
except Exception:  # noqa: BLE001 — SDK raises varied exceptions per service
    pass  # Non-fatal: skip this resource type on API error
```

One `describe_*` failure must not kill the whole scan. Use `noqa: BLE001` comment verbatim.

### YAML rule conventions

**Source:** `cli/infracanvas/security/rules/aws/networking.yaml` + `azure/network.yaml`

**Apply to:** All 6 new NET-* YAML files in `security/rules/network/`

**Contract:**
- One rule per YAML list item, starting with `- id:`.
- Required fields: `id`, `title`, `severity`, `resource_types`, `condition`, `remediation`, `description`.
- Optional: `framework_ids` (list of compliance strings like `"CIS-6.1"`, `"NIST-SC-7"`, `"SOC2-CC6.6"`).
- `condition.operator` must be one of: `equals`, `not_equals`, `in`, `not_in`, `exists`, `not_exists`, `contains`, `matches_cidr`, `list_contains_cidr`, `any_equals` (from `security/engine.py` lines 49-75).
- Rule ID format: `NET-001` through `NET-012` (CONTEXT.md D-11, FDM-03).

### TS ↔ Pydantic mirror

**Source:** `viewer/src/types.ts` (entirety) and `cli/infracanvas/graph/models.py` (entirety)

**Apply to:** Every new Pydantic model (`NetworkPath`, `PathHop`, `DCCollectorReading`, `DCSite`).

**Contract:** Field names identical (snake_case on both sides — TypeScript follows the JSON wire format). Union types mirrored as TS string literal unions. Mutable defaults: Python `Field(default_factory=list)`, TS `field: Type[] = []` or optional `field?: Type[]` with `??  []` at read site.

### Dark chrome panel shell

**Source:** `FilterPanel.tsx` lines 31-55 and `DetailPanel.tsx` lines 32-64

**Apply to:** `FlowMapFilterPanel.tsx`, `PathDetailPanel.tsx`

**Contract:**
- Background `#161b27`, border `#252d3d`.
- Fixed widths: filter `w-56` (224px), detail `w-80` (320px) — UI-SPEC forbids reflow on tab switch.
- Header row: 48px tall via `p-3`, bottom border `#252d3d`.
- Section block: `p-3`, bottom border `#252d3d`, eyebrow `text-[10px] uppercase tracking-wider font-semibold` `#4a5568`.
- Font sizes `text-[10px]` / `text-[11px]` are UI-SPEC-approved AA exceptions — use verbatim.

### Zustand toggle action

**Source:** `viewer/src/store.ts` lines 49-87

**Apply to:** All new `flowMapFilters` section actions (severity, cloud, nodeType, hasFlowLogs).

**Contract:** Immutable spread update. Arrays: `includes` + `filter` vs `[...arr, x]`. Whole-slice clears: spread from a named `emptyFilters`/`emptyFlowMapFilters` constant.

### Pytest fixture scaffold

**Source:** `cli/tests/test_shadow.py` lines 1-72 + `cli/tests/test_security.py` lines 1-20

**Apply to:** All 4 new `test_flowmap_*.py` files.

**Contract:**
- Header: `"""Tests for ..."""` docstring + `from __future__ import annotations` + stdlib `pytest` + `from unittest.mock import MagicMock, patch`.
- `FIXTURES = Path(__file__).parent / "fixtures"` constant at module top for parsing-based tests.
- `_node(...)` local helper to build minimal `ResourceNode` instances.
- `_mock_boto3_session(self)` helper on the test class for AWS-collector tests.
- `with patch.dict("sys.modules", {"boto3": None}):` idiom for missing-SDK paths.
- `with pytest.raises(RuntimeError, match="..."):` for creds / SDK guards.

---

## No Analog Found

Files with no close match in the codebase — planner should derive directly from UI-SPEC + RESEARCH.md:

| File | Role | Data Flow | Reason | Nearest Reference |
|------|------|-----------|--------|-------------------|
| `viewer/src/components/TabBar.tsx` | ARIA tablist | event-driven | No tablist component exists; DetailPanel tabs are in-panel, not top-level | UI-SPEC §TabBar + `DetailPanel.tsx` lines 66-87 tab-strip idiom |
| `viewer/src/components/flowmap/edges/PathEdge.tsx` | custom ReactFlow edge | transform | No `<BaseEdge>`-based custom edge exists; viewer uses `defaultEdgeOptions` + static `EDGE_STYLES` constants only | UI-SPEC §PathEdge (contract locked) + RESEARCH.md two-stacked-BaseEdge-children recipe |

Both new-pattern files have a fully specified contract in UI-SPEC (dimension D4/D5/D6 approved) and RESEARCH.md (verified library versions + reactflow.dev citation). No ambiguity for the planner.

---

## Metadata

**Analog search scope:** `cli/infracanvas/`, `cli/tests/`, `viewer/src/`, `viewer/src/__tests__/`
**Files scanned:** 47
**Pattern extraction date:** 2026-04-18
**Version references:** Pydantic v2, boto3 ≥1.40, azure-mgmt-network ≥28, ReactFlow (@xyflow/react) 12.6.0, elkjs ^0.11.1, Vitest 4.1.4
