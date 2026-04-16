"""Runtime staleness checks — Lambda EOL, EKS/AKS version lag, resource locks."""

from __future__ import annotations

from datetime import date

from infracanvas.graph.models import Finding, ResourceGraph, ResourceNode, Severity

# Lambda runtime EOL dates (verified from AWS docs)
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

# EKS version EOL dates
EKS_EOL: dict[str, str] = {
    "1.24": "2024-01-31",
    "1.25": "2024-05-01",
    "1.26": "2024-06-11",
    "1.27": "2024-07-26",
    "1.28": "2025-04-01",
}

# AKS version EOL dates (approximate, Azure support lifecycle)
AKS_EOL: dict[str, str] = {
    "1.24": "2024-03-01",
    "1.25": "2024-05-01",
    "1.26": "2024-07-01",
    "1.27": "2024-11-01",
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
    _check_resource_locks(graph)
    return graph


def _check_lambda(node: ResourceNode, today: str) -> None:
    runtime = str(node.attributes.get("runtime", ""))
    eol = LAMBDA_EOL.get(runtime)
    if eol and eol <= today:
        node.findings.append(Finding(
            rule_id="RST-001",
            severity=Severity.high,
            title=f"Lambda runtime {runtime} is end-of-life",
            description=f"Runtime reached end-of-life on {eol}. AWS may deprecate.",
            remediation="Upgrade to a supported runtime (python3.12, nodejs20.x)",
            evidence={"runtime": runtime, "eol_date": eol},
            source="security",
            framework_ids=["NIST-SA-22"],
        ))


def _check_eks(node: ResourceNode, today: str) -> None:
    version = str(node.attributes.get("version", ""))
    eol = EKS_EOL.get(version)
    if eol and eol <= today:
        node.findings.append(Finding(
            rule_id="RST-002",
            severity=Severity.high,
            title=f"EKS cluster version {version} is end-of-life",
            description=f"EKS {version} reached end-of-life on {eol}.",
            remediation="Upgrade to a supported EKS version (1.29+)",
            evidence={"version": version, "eol_date": eol},
            source="security",
            framework_ids=["NIST-SA-22"],
        ))


def _check_aks(node: ResourceNode, today: str) -> None:
    version = str(node.attributes.get("kubernetes_version", ""))
    eol = AKS_EOL.get(version)
    if eol and eol <= today:
        node.findings.append(Finding(
            rule_id="RST-003",
            severity=Severity.high,
            title=f"AKS cluster version {version} is end-of-life",
            description=f"AKS {version} reached end-of-life on {eol}.",
            remediation="Upgrade to a supported AKS version (1.28+)",
            evidence={"version": version, "eol_date": eol},
            source="security",
            framework_ids=["NIST-SA-22"],
        ))


def _check_resource_locks(graph: ResourceGraph) -> None:
    """RST-02: Validate azurerm_management_lock linked to protected resource."""
    lock_nodes = [n for n in graph.nodes if n.type == "azurerm_management_lock"]
    locked_scopes: set[str] = set()
    for lock in lock_nodes:
        scope = str(lock.attributes.get("scope", ""))
        if scope:
            locked_scopes.add(scope)

    # Flag high-value Azure resources without locks
    lockable_types = {
        "azurerm_mssql_server",
        "azurerm_storage_account",
        "azurerm_key_vault",
        "azurerm_kubernetes_cluster",
    }
    for node in graph.nodes:
        if node.type in lockable_types:
            resource_id = node.id
            if resource_id not in locked_scopes:
                node.findings.append(Finding(
                    rule_id="RST-004",
                    severity=Severity.info,
                    title="Critical resource has no management lock",
                    description=f"{node.type} '{node.name}' has no azurerm_management_lock.",
                    remediation="Add azurerm_management_lock with lock_level = 'CanNotDelete'",
                    evidence={"resource": resource_id},
                    source="security",
                    framework_ids=["NIST-CM-3"],
                ))
