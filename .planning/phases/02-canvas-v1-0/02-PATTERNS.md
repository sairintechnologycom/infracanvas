# Phase 2: Canvas v1.0 - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 20 new/modified files
**Analogs found:** 18 / 20

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `cli/infracanvas/parser/hcl.py` | parser | transform | self (harden in place) | self |
| `cli/infracanvas/parser/azure.py` | parser | transform | `cli/infracanvas/parser/hcl.py` | exact |
| `cli/infracanvas/shadow/detector.py` | service | request-response | `cli/infracanvas/drift/analyzer.py` | role-match |
| `cli/infracanvas/security/staleness.py` | service | transform | `cli/infracanvas/security/engine.py` | role-match |
| `cli/infracanvas/security/models.py` | model | — | self (extend in place) | self |
| `cli/infracanvas/security/loader.py` | utility | transform | self (extend in place) | self |
| `cli/infracanvas/security/engine.py` | service | transform | self (extend in place) | self |
| `cli/infracanvas/security/rules/aws/*.yaml` (20 new) | config | — | `cli/infracanvas/security/rules/aws/s3.yaml` | exact |
| `cli/infracanvas/security/rules/azure/*.yaml` (10 new) | config | — | `cli/infracanvas/security/rules/aws/s3.yaml` | exact |
| `cli/infracanvas/cost/estimator.py` | service | transform | self (extend in place) | self |
| `cli/infracanvas/graph/models.py` | model | — | self (extend in place) | self |
| `cli/infracanvas/main.py` | controller | request-response | self (extend in place) | self |
| `viewer/src/icons/azureServiceConfig.ts` | utility | — | `viewer/src/icons/awsServiceConfig.ts` | exact |
| `viewer/src/types.ts` | model | — | self (extend in place) | self |
| `viewer/src/store.ts` | store | event-driven | self (extend in place) | self |
| `viewer/src/components/FindingCard.tsx` | component | request-response | self (extend in place) | self |
| `viewer/src/components/FilterPanel.tsx` | component | event-driven | self (extend in place) | self |
| `viewer/src/components/ResourceNode.tsx` | component | event-driven | self (extend in place) | self |
| `cli/tests/test_azure_parser.py` | test | — | `cli/tests/test_parser.py` | exact |
| `cli/tests/test_shadow.py` | test | — | `cli/tests/test_cost.py` | role-match |
| `cli/tests/test_staleness.py` | test | — | `cli/tests/test_security.py` | exact |
| `cli/tests/test_policy.py` | test | — | `cli/tests/test_security.py` | exact |
| `viewer/src/__tests__/ResourceNode.test.tsx` | test | — | `viewer/src/__tests__/store.test.ts` | role-match |

---

## Pattern Assignments

### `cli/infracanvas/parser/hcl.py` — HARDEN IN PLACE (parser, transform)

**Analog:** self — modify `_parse_file()` and `ParsedTerraform`

**Current silent-failure pattern to replace** (lines 87–93):
```python
def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    """Parse a single .tf file and append results."""
    with open(tf_file) as f:
        try:
            parsed = hcl2.load(f)
        except Exception:
            return  # ← REPLACE THIS: silent drop
```

**Hardened pattern — add `parse_errors` field to dataclass** (lines 31–38):
```python
@dataclass
class ParsedTerraform:
    resources: list[ParsedResource] = field(default_factory=list)
    variables: list[ParsedBlock] = field(default_factory=list)
    locals: list[ParsedBlock] = field(default_factory=list)
    outputs: list[ParsedBlock] = field(default_factory=list)
    data_sources: list[ParsedBlock] = field(default_factory=list)
    implicit_deps: dict[str, set[str]] = field(default_factory=dict)
    _raw_modules: list[dict[str, Any]] = field(default_factory=list)
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)  # ADD
```

**Hardened `_parse_file()` body:**
```python
def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    """Parse a single .tf file and append results."""
    with open(tf_file) as f:
        try:
            parsed = hcl2.load(f)
        except Exception as exc:
            result.parse_errors.append((tf_file, str(exc)))  # REPORT, NOT DROP
            return
    _extract_resources(parsed, result)
    _extract_variables(parsed, result)
    _extract_locals(parsed, result)
    _extract_outputs(parsed, result)
    _extract_data_sources(parsed, result)
    _extract_modules(parsed, result)
```

**Warning output after `parse_directory()` in `main.py` `_run_scan()`** — use existing Rich console pattern (lines 84–86):
```python
if parsed.parse_errors:
    for path, err in parsed.parse_errors:
        out.print(f"[yellow]Warning:[/yellow] Could not parse {path.name}: {err}")
```

---

### `cli/infracanvas/parser/azure.py` — NEW (parser, transform)

**Analog:** `cli/infracanvas/parser/hcl.py` (exact structure mirror)

**Imports pattern** (copy from hcl.py lines 1–11):
```python
"""Attribute normalisation layer for azurerm provider resources."""

from __future__ import annotations

from typing import Any

from infracanvas.parser.hcl import ParsedResource, ParsedTerraform
```

**Core pattern — provider auto-detection happens in builder, NOT parser.**
The Azure parser is purely an attribute normalisation layer called from `build_graph()`. The HCL parser already extracts `azurerm_*` blocks — no separate parser is needed. The builder assigns provider from resource type prefix (lines 30–31 of `builder.py`):
```python
# cli/infracanvas/graph/builder.py — existing provider detection (_create_nodes, line 30):
provider = res.resource_type.split("_")[0] if "_" in res.resource_type else "unknown"
# "azurerm" → provider = "azurerm"  ✓ already works
```

**What `azure.py` actually does — attribute normalisation:**
```python
"""Normalize azurerm resource attributes for the InfraCanvas graph model."""

from __future__ import annotations

from typing import Any


def normalize_azure_attrs(resource_type: str, attrs: dict[str, Any]) -> dict[str, Any]:
    """Map Azure-specific attribute names to InfraCanvas canonical form.

    Azure uses 'location' where AWS uses 'region'; this function ensures
    the graph builder can read node.region for all providers.
    """
    normalized = dict(attrs)

    # Azure uses 'location' instead of 'region'
    if "location" in normalized and "region" not in normalized:
        normalized["region"] = normalized["location"]

    return normalized
```

**Integration point in builder.py `_create_nodes()`** — call normaliser when provider is azurerm:
```python
# After existing line 31 in builder.py:
if provider == "azurerm":
    from infracanvas.parser.azure import normalize_azure_attrs
    res = ParsedResource(
        resource_type=res.resource_type,
        name=res.name,
        attributes=normalize_azure_attrs(res.resource_type, res.attributes),
        depends_on=res.depends_on,
        module=res.module,
    )
region = str(res.attributes.get("region", ""))  # now reads 'region' for both AWS + Azure
```

---

### `cli/infracanvas/shadow/detector.py` — NEW (service, request-response)

**Analog:** `cli/infracanvas/drift/analyzer.py` (service that annotates graph nodes)

**Imports pattern** (mirror drift/analyzer.py lines 1–6):
```python
"""Shadow infrastructure detector — compare live AWS API vs Terraform graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode

if TYPE_CHECKING:
    import boto3  # type: ignore[import-untyped]
```

**Class pattern** (mirror DriftAnalyzer structure):
```python
class ShadowDetector:
    """Compare live AWS API vs Terraform graph nodes; flag unmanaged resources."""

    # Supported resource types for shadow detection (read-only IAM surface)
    SUPPORTED_TYPES = {
        "aws_instance": "ec2",
        "aws_security_group": "ec2",
        "aws_vpc": "ec2",
        "aws_subnet": "ec2",
        "aws_s3_bucket": "s3",
        "aws_db_instance": "rds",
    }

    def __init__(self, region: str) -> None:
        self._region = region

    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        """Flag shadow resources; returns graph unchanged on missing creds/boto3."""
        try:
            import boto3  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                "boto3 not installed. Install with: pip install 'infracanvas[shadow]'"
            )

        session = boto3.Session()
        creds = session.get_credentials()
        if not creds:
            raise RuntimeError("No AWS credentials found")

        ec2 = session.client("ec2", region_name=self._region)
        s3 = session.client("s3")
        rds = session.client("rds", region_name=self._region)

        self._flag_shadow_ec2(graph, ec2)
        self._flag_shadow_s3(graph, s3)
        self._flag_shadow_rds(graph, rds)
        return graph
```

**Error handling in main.py** — follow D-02 (warn and continue):
```python
# In _run_scan(), after graph = build_graph(parsed):
if shadow:
    try:
        from infracanvas.shadow.detector import ShadowDetector
        region = graph.metadata.get("region", "us-east-1") or "us-east-1"
        detector = ShadowDetector(region=str(region))
        graph = detector.detect(graph)
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] --shadow: {exc}. Skipping shadow scan.")
```

---

### `cli/infracanvas/security/staleness.py` — NEW (service, transform)

**Analog:** `cli/infracanvas/security/engine.py` (analysis pass that appends `Finding` to nodes)

**Imports pattern** (mirror engine.py lines 1–8):
```python
"""Runtime staleness checks — Lambda EOL, EKS/AKS version lag, resource locks."""

from __future__ import annotations

from datetime import date

from infracanvas.graph.models import Finding, ResourceGraph, Severity
```

**Core pattern** — iterate nodes, check static EOL tables, append Finding:
```python
LAMBDA_EOL: dict[str, str] = {
    "python3.8": "2024-10-14",
    "python3.9": "2025-09-01",
    "nodejs14.x": "2024-11-11",
    "nodejs16.x": "2024-06-12",
    "nodejs18.x": "2025-07-31",
    "ruby2.7": "2023-12-07",
    "java8": "2024-12-05",
    "dotnet6": "2024-11-12",
}

EKS_EOL: dict[str, str] = {
    "1.24": "2024-01-31", "1.25": "2024-05-01",
    "1.26": "2024-06-11", "1.27": "2024-07-26",
    "1.28": "2025-04-01",
}


def check_staleness(graph: ResourceGraph) -> ResourceGraph:
    """Append staleness findings to applicable nodes."""
    today = date.today().isoformat()
    for node in graph.nodes:
        if node.type == "aws_lambda_function":
            _check_lambda(node, today)
        elif node.type == "aws_eks_cluster":
            _check_eks(node, today)
        elif node.type == "azurerm_kubernetes_cluster":
            _check_aks(node, today)
        elif node.type == "azurerm_management_lock":
            _check_resource_lock(node, graph)
    return graph
```

**Finding creation pattern** (copy from engine.py lines 66–73):
```python
def _check_lambda(node, today: str) -> None:
    runtime = str(node.attributes.get("runtime", ""))
    eol = LAMBDA_EOL.get(runtime)
    if eol and eol <= today:
        node.findings.append(Finding(
            rule_id="RST-001",
            severity=Severity.high,
            title=f"Lambda runtime {runtime} is EOL",
            description=f"Runtime reached end-of-life on {eol}. AWS may deprecate it.",
            remediation="Upgrade to a supported runtime (python3.12, nodejs20.x, etc.)",
            evidence={"runtime": runtime, "eol_date": eol},
            source="security",
            framework_ids=["NIST-SA-22"],
        ))
```

---

### `cli/infracanvas/security/models.py` — EXTEND IN PLACE (model)

**Current file** (lines 19–27) — add `framework_ids` field:
```python
@dataclass
class SecurityRule:
    id: str
    title: str
    severity: Severity
    resource_types: list[str]
    condition: RuleCondition
    remediation: str
    description: str
    framework_ids: list[str] = field(default_factory=list)  # ADD
```

---

### `cli/infracanvas/security/loader.py` — EXTEND IN PLACE (utility, transform)

**Current `_load_rules_file()` pattern** (lines 30–59) — add `framework_ids` extraction:
```python
rule = SecurityRule(
    id=item["id"],
    title=item["title"],
    severity=Severity(item["severity"]),
    resource_types=item.get("resource_types", []),
    condition=condition,
    remediation=item.get("remediation", ""),
    description=item.get("description", ""),
    framework_ids=item.get("framework_ids", []),  # ADD
)
```

**Policy loading function** — new function following `load_rules()` pattern (lines 16–26):
```python
def load_policy_rules(policy_dir: Path) -> list[SecurityRule]:
    """Load custom policy rules from user-provided directory.

    Identical to load_rules() — policy YAML uses the same schema.
    Caller injects source='policy' into resulting Findings at evaluation time.
    """
    rules: list[SecurityRule] = []
    if not policy_dir.is_dir():
        return rules
    for yaml_file in sorted(policy_dir.rglob("*.yaml")):
        rules.extend(_load_rules_file(yaml_file))
    return rules
```

---

### `cli/infracanvas/security/engine.py` — EXTEND IN PLACE (service, transform)

**Current `evaluate_all()` pattern** (lines 12–23) — add policy evaluation:
```python
def evaluate_all(graph: ResourceGraph, policy_rules: list[SecurityRule] | None = None) -> ResourceGraph:
    """Run all security rules (and optional policy rules) against all nodes."""
    rules = load_rules()
    if policy_rules:
        rules = rules + policy_rules  # policy rules appended after security rules
    # ... existing per-node evaluation loop unchanged
```

**Policy Finding injection** — pass `source` when creating findings from policy rules:
```python
# In _evaluate_rule(), add source parameter:
def _evaluate_rule(rule: SecurityRule, node: ResourceNode, source: str = "security") -> Finding | None:
    # ... existing match logic unchanged ...
    if matched:
        return Finding(
            rule_id=rule.id,
            severity=rule.severity,
            title=rule.title,
            description=rule.description,
            remediation=rule.remediation,
            evidence={"attribute": attr_name, "value": _sanitize_evidence(evidence_value)},
            source=source,                           # ADD
            framework_ids=rule.framework_ids,        # ADD
        )
```

---

### `cli/infracanvas/security/rules/aws/*.yaml` — 20 NEW FILES (config)

**Analog:** `cli/infracanvas/security/rules/aws/s3.yaml` (exact schema to copy)

**Existing schema** (all fields):
```yaml
- id: SEC-001
  title: "S3 Bucket Publicly Accessible"
  severity: critical
  resource_types: ["aws_s3_bucket"]
  condition:
    attribute: "acl"
    operator: "in"
    values: ["public-read", "public-read-write"]
  remediation: "Set acl to 'private' and use bucket policies for granular access control"
  description: "S3 bucket has public ACL which exposes all objects to the internet"
```

**Extended schema for Phase 2** (add `framework_ids`):
```yaml
- id: SEC-011
  title: "S3 Bucket Public Access Block Missing"
  severity: critical
  resource_types: ["aws_s3_bucket_public_access_block"]
  framework_ids: ["CIS-2.1.5", "NIST-SC-7", "SOC2-CC6.1", "PCI-DSS-1.2"]
  condition:
    attribute: "block_public_acls"
    operator: "not_equals"
    value: true
  remediation: "Set block_public_acls, block_public_policy, ignore_public_acls, restrict_public_buckets all to true"
  description: "S3 bucket is missing public access block configuration"
```

**File placement:** one YAML file per AWS service domain:
- `cli/infracanvas/security/rules/aws/s3_advanced.yaml` — SEC-011 through SEC-013, SEC-030
- `cli/infracanvas/security/rules/aws/networking_advanced.yaml` — SEC-014
- `cli/infracanvas/security/rules/aws/iam_advanced.yaml` — SEC-015, SEC-028
- `cli/infracanvas/security/rules/aws/lambda.yaml` — SEC-016, SEC-017
- `cli/infracanvas/security/rules/aws/rds_advanced.yaml` — SEC-018 through SEC-020
- `cli/infracanvas/security/rules/aws/eks.yaml` — SEC-021, SEC-022
- `cli/infracanvas/security/rules/aws/alb.yaml` — SEC-023
- `cli/infracanvas/security/rules/aws/cloudfront.yaml` — SEC-024
- `cli/infracanvas/security/rules/aws/messaging.yaml` — SEC-025, SEC-026
- `cli/infracanvas/security/rules/aws/dynamodb.yaml` — SEC-027
- `cli/infracanvas/security/rules/aws/kms_advanced.yaml` — SEC-029

---

### `cli/infracanvas/security/rules/azure/*.yaml` — 10 NEW FILES (config)

**Analog:** `cli/infracanvas/security/rules/aws/s3.yaml` (exact same schema)

**Schema example:**
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

**File placement:** `cli/infracanvas/security/rules/azure/`
- `network.yaml` — AZ-001 (NSG wildcard), AZ-003 (SSH/RDP open), AZ-009 (VNet DDoS)
- `storage.yaml` — AZ-002 (blob public), AZ-006 (HTTPS only), AZ-007 (min TLS)
- `compute.yaml` — AZ-004 (VM disk encryption), AZ-005 (no public IP)
- `identity.yaml` — AZ-008 (AKS RBAC)
- `database.yaml` — AZ-010 (SQL public access)

---

### `cli/infracanvas/cost/estimator.py` — EXTEND IN PLACE (service, transform)

**Current class structure** (lines 101–127) — add region multiplier:

**Add at module level** (after existing pricing dicts):
```python
REGION_MULTIPLIERS: dict[str, float] = {
    "us-east-1": 1.0, "us-east-2": 1.0, "us-west-1": 1.1, "us-west-2": 1.0,
    "eu-west-1": 1.1, "eu-west-2": 1.12, "eu-central-1": 1.12,
    "ap-southeast-1": 1.15, "ap-northeast-1": 1.12, "ap-south-1": 1.0,
}
```

**Extend `estimate()` method** (lines 103–111):
```python
def estimate(self, graph: ResourceGraph) -> ResourceGraph:
    """Annotate each node.cost and update summary.estimated_monthly_cost."""
    total = 0.0
    for node in graph.nodes:
        node.cost = _estimate_resource(node.type, node.attributes)
        # CST-03: apply region multiplier
        multiplier = REGION_MULTIPLIERS.get(node.region or "us-east-1", 1.0)
        node.cost = CostEstimate(
            monthly_usd=round(node.cost.monthly_usd * multiplier, 2),
            currency=node.cost.currency,
            basis=node.cost.basis + (f" ({node.region})" if node.region else ""),
        )
        total += node.cost.monthly_usd
    graph.summary.estimated_monthly_cost = round(total, 2)
    return graph
```

---

### `cli/infracanvas/graph/models.py` — EXTEND IN PLACE (model)

**Finding model** (lines 17–24) — add `source` and `framework_ids`:
```python
class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"           # ADD: "security" | "policy"
    framework_ids: list[str] = []      # ADD: ["CIS-1.20", "NIST-SC-7"]
```

---

### `cli/infracanvas/main.py` — EXTEND IN PLACE (controller, request-response)

**Current `scan()` signature** (lines 237–273) — add `--shadow` and `--policy` flags:
```python
@app.command()
def scan(
    directory: Annotated[Path, typer.Argument(...)],
    # ... existing args ...
    shadow: Annotated[
        bool,
        typer.Option("--shadow", help="Compare live AWS API vs Terraform state (requires boto3)"),
    ] = False,
    policy: Annotated[
        Optional[Path],
        typer.Option("--policy", help="Directory containing custom policy YAML files"),
    ] = None,
    fail_on: Annotated[
        Optional[str],
        typer.Option("--fail-on", help="Minimum severity for non-zero exit (critical/high/medium/info)"),
    ] = None,
) -> None:
```

**CI blocking pattern** (lines 296–303) — existing pattern, `fail_on` replaces hardcoded "high":
```python
if ci or quiet:
    sys.stdout.write(export_graph(graph))
    sys.stdout.write("\n")
    if ci:
        threshold = fail_on or effective_severity or "high"
        sev_order = ["critical", "high", "medium", "info"]
        threshold_idx = sev_order.index(threshold)
        has_findings = any(
            graph.summary.findings.get(s, 0) > 0
            for s in sev_order[: threshold_idx + 1]
        )
        raise typer.Exit(code=1 if has_findings else 0)
```

**Watch mode debounce** (line 362) — keep at 0.5s for scan (responsive), 1.0s for serve (already correct):
```python
if now - last_trigger < 0.5:  # 0.5s debounce for watch mode
    return
```

**Policy integration in `_run_scan()`** — call after `evaluate_all()`:
```python
if policy:
    from infracanvas.security.loader import load_policy_rules
    policy_rules = load_policy_rules(policy)
    graph = evaluate_all(graph, policy_rules=policy_rules)  # policy rules in second pass
else:
    graph = evaluate_all(graph)
```

**Shadow integration in `_run_scan()`** — call after `graph = build_graph(parsed)`:
```python
if shadow:
    try:
        from infracanvas.shadow.detector import ShadowDetector
        inferred_region = _infer_region(parsed) or "us-east-1"
        detector = ShadowDetector(region=inferred_region)
        graph = detector.detect(graph)
    except RuntimeError as exc:
        out.print(f"[yellow]Warning:[/yellow] {exc}. Skipping shadow scan.")
```

---

### `viewer/src/icons/azureServiceConfig.ts` — NEW (utility)

**Analog:** `viewer/src/icons/awsServiceConfig.ts` (exact mirror)

**Full pattern from awsServiceConfig.ts** (lines 1–37):
```typescript
// Mirror the exact interface + lookup + fallback function shape:
export interface AzureServiceConfig {
  color: string;
  label: string;
}

export const AZURE_SERVICE_CONFIG: Record<string, AzureServiceConfig> = {
  azurerm_virtual_network:        { color: '#0078D4', label: 'VNet' },
  azurerm_subnet:                 { color: '#0078D4', label: 'NET' },
  azurerm_network_security_group: { color: '#DD344C', label: 'NSG' },
  azurerm_virtual_machine:        { color: '#FF9900', label: 'VM' },
  azurerm_linux_virtual_machine:  { color: '#FF9900', label: 'VM' },
  azurerm_windows_virtual_machine: { color: '#FF9900', label: 'VM' },
  azurerm_storage_account:        { color: '#3F8624', label: 'STG' },
  azurerm_kubernetes_cluster:     { color: '#2E73B8', label: 'AKS' },
  azurerm_app_service:            { color: '#FF9900', label: 'APP' },
  azurerm_mssql_server:           { color: '#2E73B8', label: 'SQL' },
  azurerm_key_vault:              { color: '#DD344C', label: 'KV' },
  azurerm_application_gateway:    { color: '#8C4FFF', label: 'AGW' },
};

export function getAzureServiceConfig(resourceType: string): AzureServiceConfig {
  if (AZURE_SERVICE_CONFIG[resourceType]) return AZURE_SERVICE_CONFIG[resourceType];
  // Fallback: strip azurerm_ prefix, take first 4 chars uppercase
  return { color: '#94a3b8', label: resourceType.replace(/^azurerm_/, '').slice(0, 4).toUpperCase() };
}
```

---

### `viewer/src/types.ts` — EXTEND IN PLACE (model)

**Current `Finding` interface** (lines 5–12) — add `source` and `framework_ids`:
```typescript
export interface Finding {
  rule_id: string;
  severity: Severity;
  title: string;
  description: string;
  remediation: string;
  evidence: Record<string, unknown>;
  source?: string;              // ADD: 'security' | 'policy'
  framework_ids?: string[];     // ADD: ['CIS-2.1.5', 'NIST-SC-7']
}
```

---

### `viewer/src/store.ts` — EXTEND IN PLACE (store, event-driven)

**Current `Filters` interface** (lines 4–8) — add `sources`:
```typescript
interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
  sources: string[];   // ADD: [] = all; ['security', 'policy'] = filtered
}
```

**Current `StoreState` interface** (lines 10–26) — add action:
```typescript
toggleSourceFilter: (source: string) => void;  // ADD
```

**`emptyFilters` constant** (lines 28–32):
```typescript
const emptyFilters: Filters = {
  severities: [],
  resourceTypes: [],
  driftStatuses: [],
  sources: [],   // ADD
};
```

**New action** (copy exact shape from `toggleDriftFilter` lines 66–74):
```typescript
toggleSourceFilter: (source) =>
  set((s) => ({
    filters: {
      ...s.filters,
      sources: s.filters.sources.includes(source)
        ? s.filters.sources.filter((x) => x !== source)
        : [...s.filters.sources, source],
    },
  })),
```

---

### `viewer/src/components/FindingCard.tsx` — EXTEND IN PLACE (component, request-response)

**Current header block** (lines 29–41) — add source pill and framework tags:

**Source pill** — insert after severity badge (line 37), before rule_id:
```tsx
{/* Source pill — only render if source is 'policy' */}
{finding.source === 'policy' && (
  <span
    className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
    style={{ background: 'rgba(139,92,246,0.15)', color: '#a78bfa' }}
  >
    POLICY
  </span>
)}
```

**Framework tags** — insert before `</FindingCard>` closing, after remediation block (line 78):
```tsx
{/* Compliance framework tags */}
{!gateMode && finding.framework_ids && finding.framework_ids.length > 0 && (
  <div className="flex flex-wrap gap-1 mt-1.5">
    {finding.framework_ids.map(id => (
      <span
        key={id}
        className="text-[9px] px-1 py-0.5 rounded"
        style={{ background: '#1c2333', color: '#4a5568', border: '1px solid #252d3d' }}
      >
        {id}
      </span>
    ))}
  </div>
)}
```

---

### `viewer/src/components/FilterPanel.tsx` — EXTEND IN PLACE (component, event-driven)

**Analog for new Source section:** existing Drift Status section (lines 117–144) — copy exact structure.

**Add to selector block at top** (lines 13–17):
```tsx
const toggleSourceFilter = useStore(s => s.toggleSourceFilter);
```

**Add to `hasActiveFilters` check** (lines 23–26):
```tsx
const hasActiveFilters =
  filters.severities.length > 0 ||
  filters.resourceTypes.length > 0 ||
  filters.driftStatuses.length > 0 ||
  filters.sources.length > 0;   // ADD
```

**Fix `label` in Resource Type section** (line 101) — strip both `aws_` and `azurerm_` prefix:
```tsx
const label = rt.replace(/^aws_/, '').replace(/^azurerm_/, '');
```

**New Source filter section** — copy Drift Status section structure (lines 117–144):
```tsx
{/* Source */}
<div className="p-3">
  <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: '#4a5568' }}>
    Finding Source
  </div>
  <div className="flex flex-col gap-1">
    {(['security', 'policy'] as const).map(src => {
      const isActive = filters.sources.includes(src);
      const count = graph.nodes.reduce((acc, n) =>
        acc + n.findings.filter(f => (f.source ?? 'security') === src).length, 0
      );
      return (
        <label
          key={src}
          className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
          style={{ color: isActive ? '#e2e8f0' : '#4a5568' }}
        >
          <input
            type="checkbox"
            checked={isActive}
            onChange={() => toggleSourceFilter(src)}
            className="accent-sky-500"
          />
          <span className="flex-1 capitalize">{src}</span>
          <span className="text-[10px]" style={{ color: '#374151' }}>{count}</span>
        </label>
      );
    })}
  </div>
</div>
```

---

### `viewer/src/components/ResourceNode.tsx` — EXTEND IN PLACE (component, event-driven)

**Current `typeLabel` strip** (line 35) — extend to also strip `azurerm_`:
```tsx
// Current (line 35):
const typeLabel = data.type
  .replace(/^aws_/, '')
  .toUpperCase()
  .replaceAll('_', ' ');

// Replace with:
const typeLabel = data.type
  .replace(/^aws_/, '')
  .replace(/^azurerm_/, '')
  .toUpperCase()
  .replaceAll('_', ' ');
```

**Service config lookup** (line 21) — add Azure config fallback:
```tsx
// Current (line 21):
const svc = getServiceConfig(data.type);

// Replace with:
import { getAzureServiceConfig } from '../icons/azureServiceConfig';

const svc = data.provider === 'azurerm'
  ? getAzureServiceConfig(data.type)
  : getServiceConfig(data.type);
```

**Shadow badge** (lines 241–243) — existing pattern; "Shadow" badge text replaces "shadow":
```tsx
{isShadow && (
  <div
    style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#94a3b8',
             background: 'rgba(148,163,184,0.1)', borderRadius: 3, padding: '1px 4px' }}
  >
    Shadow
  </div>
)}
```

**Drift border colours** — D-15 spec maps to existing `driftColors` (already in colors.ts). Verify `driftColors.added = '#22c55e'` (green), `driftColors.changed = '#eab308'` (amber), `driftColors.deleted` needs to be red `'#ef4444'`. Confirm in `lib/colors.ts` before implementing.

---

### `cli/tests/test_azure_parser.py` — NEW (test)

**Analog:** `cli/tests/test_parser.py` (exact structure)

**Imports and FIXTURES pattern** (lines 1–9):
```python
"""Tests for Azure attribute normalisation and provider detection."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.parser.hcl import parse_directory

FIXTURES = Path(__file__).parent / "fixtures" / "azure"
```

**Helper pattern** (mirror `_scan_fixture()` from test_security.py lines 15–19):
```python
def _scan_azure_fixture(name: str):
    """Helper: parse Azure .tf fixtures → build graph."""
    parsed = parse_directory(FIXTURES / name)
    return build_graph(parsed)
```

**Test class pattern** (mirror `TestParseDirectory` from test_parser.py):
```python
class TestAzureParser:
    """AZR-001: Azure resource extraction from HCL."""

    def test_vnet_extracted(self):
        """AZR-001-A: azurerm_virtual_network resource extracted."""
        graph = _scan_azure_fixture("vnet")
        types = {n.type for n in graph.nodes}
        assert "azurerm_virtual_network" in types

    def test_provider_set_to_azurerm(self):
        """AZR-001-B: provider field set to 'azurerm'."""
        graph = _scan_azure_fixture("vnet")
        node = next(n for n in graph.nodes if n.type == "azurerm_virtual_network")
        assert node.provider == "azurerm"

    def test_location_mapped_to_region(self):
        """AZR-001-C: location attribute normalised to region field."""
        graph = _scan_azure_fixture("vnet")
        node = next(n for n in graph.nodes if n.type == "azurerm_virtual_network")
        assert node.region != ""  # location="East US" → region="East US"
```

---

### `cli/tests/test_shadow.py` — NEW (test)

**Analog:** `cli/tests/test_cost.py` (service that takes a graph and returns annotated graph)

**Imports and node factory pattern** (test_cost.py lines 1–19):
```python
"""Tests for shadow infrastructure detector (SHD-01)."""

from unittest.mock import MagicMock, patch

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode
from infracanvas.shadow.detector import ShadowDetector


def _node(resource_type: str, name: str) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes={},
    )
```

**Mock boto3 pattern:**
```python
class TestShadowDetector:
    def test_missing_boto3_raises_runtime_error(self):
        """SHD-001-A: RuntimeError when boto3 not installed."""
        with patch.dict("sys.modules", {"boto3": None}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[_node("aws_instance", "web")])
            with pytest.raises(RuntimeError, match="boto3 not installed"):
                detector.detect(graph)

    def test_no_credentials_raises_runtime_error(self):
        """SHD-001-B: RuntimeError when no AWS credentials."""
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        with patch("boto3.Session", return_value=mock_session):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[])
            with pytest.raises(RuntimeError, match="No AWS credentials"):
                detector.detect(graph)
```

---

### `cli/tests/test_staleness.py` — NEW (test)

**Analog:** `cli/tests/test_security.py` (engine test with per-rule assertions)

**Pattern:**
```python
"""Tests for runtime staleness checks (RST-01, RST-02)."""

from infracanvas.graph.models import ResourceGraph, ResourceNode
from infracanvas.security.staleness import check_staleness


def _node(resource_type: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.test",
        type=resource_type,
        name="test",
        provider="aws",
        attributes=attrs,
    )


class TestLambdaStaleness:
    def test_eol_runtime_flagged(self):
        """RST-001-A: EOL Lambda runtime creates RST-001 finding."""
        node = _node("aws_lambda_function", {"runtime": "python3.8"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert any(f.rule_id == "RST-001" for f in node.findings)

    def test_current_runtime_not_flagged(self):
        """RST-001-B: Current runtime does not create finding."""
        node = _node("aws_lambda_function", {"runtime": "python3.12"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert not any(f.rule_id == "RST-001" for f in node.findings)
```

---

### `cli/tests/test_policy.py` — NEW (test)

**Analog:** `cli/tests/test_security.py` (rule loader + engine test)

**Pattern:**
```python
"""Tests for custom policy engine (POL-01, POL-02)."""

from pathlib import Path

from infracanvas.graph.models import ResourceGraph, ResourceNode
from infracanvas.security.engine import evaluate_all
from infracanvas.security.loader import load_policy_rules

FIXTURES = Path(__file__).parent / "fixtures" / "policies"


class TestPolicyLoader:
    def test_loads_yaml_from_directory(self):
        """POL-001-A: load_policy_rules() discovers .yaml files in policy dir."""
        rules = load_policy_rules(FIXTURES)
        assert len(rules) > 0

    def test_policy_source_injected(self):
        """POL-001-B: Findings from policy rules have source='policy'."""
        rules = load_policy_rules(FIXTURES)
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", attributes={}
        )
        graph = ResourceGraph(nodes=[node])
        graph = evaluate_all(graph, policy_rules=rules)
        policy_findings = [f for f in node.findings if f.source == "policy"]
        assert len(policy_findings) > 0
```

---

### `viewer/src/__tests__/ResourceNode.test.tsx` — NEW (test)

**Analog:** `viewer/src/__tests__/store.test.ts` (Vitest with mock data pattern)

**Imports and mock data pattern** (store.test.ts lines 1–39):
```typescript
import { describe, it, expect } from 'vitest';
// Component tests use @testing-library/react (already in package.json):
import { render } from '@testing-library/react';
import { ResourceNodeMemo } from '../components/ResourceNode';

const azureNode = {
  id: 'azurerm_virtual_network.main',
  type: 'azurerm_virtual_network',
  name: 'main',
  provider: 'azurerm',
  module: '',
  region: 'East US',
  group: '',
  attributes: { address_space: ['10.0.0.0/16'] },
  dependencies: [],
  findings: [],
  cost: { monthly_usd: 0, currency: 'USD', basis: '' },
  drift: 'unchanged' as const,
  position: { x: 0, y: 0 },
};
```

---

## Shared Patterns

### Python Module Header
**Source:** `cli/infracanvas/parser/hcl.py` lines 1–11
**Apply to:** All new Python modules (`azure.py`, `detector.py`, `staleness.py`)
```python
"""Module docstring — one sentence describing purpose."""

from __future__ import annotations

from typing import Any
# ... other stdlib imports ...
# ... then third-party ...
# ... then infracanvas.* ...
```

### Python Dataclass Pattern
**Source:** `cli/infracanvas/parser/hcl.py` lines 14–38
**Apply to:** Any new dataclass additions
```python
@dataclass
class MyClass:
    field_with_default: list[str] = field(default_factory=list)
    optional_field: str = ""
```

### Pydantic Model Pattern
**Source:** `cli/infracanvas/graph/models.py` lines 17–24
**Apply to:** Any new Pydantic models (`Finding` extension pattern)
```python
class MyModel(BaseModel):
    required_field: str
    optional_with_default: dict[str, object] = {}
    list_field: list[str] = []
```

### Rich Console Error/Warning Output
**Source:** `cli/infracanvas/main.py` lines 84–86, 319
**Apply to:** All new error/warning output in main.py
```python
out.print(f"[red]Error:[/red] {message}")
out.print(f"[yellow]Warning:[/yellow] {message}")
```

### Optional Import Pattern (for boto3)
**Source:** `cli/infracanvas/main.py` lines 89–91 (watchdog lazy import pattern)
**Apply to:** `shadow/detector.py` boto3 import
```python
try:
    import boto3
except ImportError:
    raise RuntimeError("boto3 not installed. Install with: pip install 'infracanvas[shadow]'")
```

### Typer Optional Flag Pattern
**Source:** `cli/infracanvas/main.py` lines 262–272
**Apply to:** New `--shadow`, `--policy`, `--fail-on` flags in `scan()`
```python
flag_name: Annotated[
    Optional[TypeHint],
    typer.Option("--flag-name", help="Description"),
] = None  # or False for bool flags
```

### React Component Selector Pattern
**Source:** `viewer/src/components/FilterPanel.tsx` lines 10–17
**Apply to:** All component extensions that read store state
```typescript
const someValue = useStore(s => s.someValue);
const someAction = useStore(s => s.someAction);
```

### React Pill/Badge Pattern
**Source:** `viewer/src/components/FindingCard.tsx` lines 34–38, `viewer/src/components/ResourceNode.tsx` lines 161–177
**Apply to:** POLICY source pill, Shadow badge, framework tag badges
```tsx
<span
  className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
  style={{ background: `${color}20`, color }}
>
  LABEL
</span>
```

### Vitest Test Pattern
**Source:** `viewer/src/__tests__/store.test.ts` lines 1–5, 41–43
**Apply to:** `ResourceNode.test.tsx`
```typescript
import { describe, it, expect, beforeEach } from 'vitest';

describe('ComponentName', () => {
  it('TEST-ID: description', () => {
    // arrange → act → assert
  });
});
```

### Python Test Helper Factory Pattern
**Source:** `cli/tests/test_cost.py` lines 12–19
**Apply to:** `test_azure_parser.py`, `test_shadow.py`, `test_staleness.py`, `test_policy.py`
```python
def _node(resource_type: str, name: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes=attrs,
    )
```

### Python Fixture Scan Helper
**Source:** `cli/tests/test_security.py` lines 15–19
**Apply to:** `test_azure_parser.py`
```python
FIXTURES = Path(__file__).parent / "fixtures"

def _scan_fixture(name: str):
    """Helper: parse → build → evaluate a fixture."""
    parsed = parse_directory(FIXTURES / name)
    graph = build_graph(parsed)
    return evaluate_all(graph)
```

---

## No Analog Found

Files with no close match in the codebase (use RESEARCH.md patterns):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `cli/tests/fixtures/azure/*.tf` | fixture | — | No Azure .tf fixtures exist; write from scratch using azurerm_ resource blocks |
| `cli/tests/fixtures/policies/*.yaml` | fixture | — | No policy YAML fixtures exist; write minimal valid YAML using existing rule schema |
| GitHub Actions matrix workflow | CI/CD | batch | No `.github/workflows/` directory found; write from scratch per RESEARCH.md Pattern 8 |

---

## Metadata

**Analog search scope:** `cli/infracanvas/`, `viewer/src/`, `cli/tests/`
**Files read:** 22 source files
**Pattern extraction date:** 2026-04-16
