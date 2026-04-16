"""Tests for runtime staleness checks (RST-01, RST-02)."""

from infracanvas.graph.models import ResourceGraph, ResourceNode
from infracanvas.security.staleness import check_staleness


def _node(
    resource_type: str,
    name: str = "test",
    attrs: dict | None = None,
    provider: str = "aws",
) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider=provider,
        attributes=attrs or {},
    )


class TestLambdaStaleness:
    def test_eol_runtime_flagged(self):
        """RST-001-A: EOL Lambda runtime creates RST-001 finding."""
        node = _node("aws_lambda_function", attrs={"runtime": "python3.8"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert any(f.rule_id == "RST-001" for f in node.findings)

    def test_current_runtime_not_flagged(self):
        """RST-001-B: Current runtime does not create finding."""
        node = _node("aws_lambda_function", attrs={"runtime": "python3.12"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert not any(f.rule_id == "RST-001" for f in node.findings)

    def test_finding_has_framework_ids(self):
        """RST-001-C: Staleness finding includes framework_ids."""
        node = _node("aws_lambda_function", attrs={"runtime": "python3.8"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        finding = next(f for f in node.findings if f.rule_id == "RST-001")
        assert len(finding.framework_ids) > 0


class TestEksStaleness:
    def test_old_eks_flagged(self):
        """RST-002-A: Old EKS version creates RST-002 finding."""
        node = _node("aws_eks_cluster", attrs={"version": "1.24"})
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert any(f.rule_id == "RST-002" for f in node.findings)


class TestAksStaleness:
    def test_old_aks_flagged(self):
        """RST-003-A: Old AKS version creates RST-003 finding."""
        node = _node(
            "azurerm_kubernetes_cluster",
            attrs={"kubernetes_version": "1.24"},
            provider="azurerm",
        )
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert any(f.rule_id == "RST-003" for f in node.findings)


class TestResourceLocks:
    def test_unlocked_critical_resource_flagged(self):
        """RST-004-A: Critical Azure resource without lock gets RST-004."""
        node = _node("azurerm_key_vault", name="vault", provider="azurerm")
        graph = ResourceGraph(nodes=[node])
        check_staleness(graph)
        assert any(f.rule_id == "RST-004" for f in node.findings)

    def test_locked_resource_not_flagged(self):
        """RST-004-B: Resource with management lock does not get RST-004."""
        vault = _node("azurerm_key_vault", name="vault", provider="azurerm")
        lock = _node(
            "azurerm_management_lock",
            name="lock",
            attrs={"scope": "azurerm_key_vault.vault"},
            provider="azurerm",
        )
        graph = ResourceGraph(nodes=[vault, lock])
        check_staleness(graph)
        assert not any(f.rule_id == "RST-004" for f in vault.findings)
