"""Tests for Azure resource extraction and attribute normalisation (AZR-01)."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.parser.hcl import parse_directory

FIXTURES = Path(__file__).parent / "fixtures" / "azure"


def _scan_azure():
    """Parse all Azure fixture files in the azure/ directory."""
    parsed = parse_directory(FIXTURES)
    return build_graph(parsed)


class TestAzureParser:
    def test_vnet_extracted(self):
        """AZR-001-A: azurerm_virtual_network resource extracted."""
        graph = _scan_azure()
        types = {n.type for n in graph.nodes}
        assert "azurerm_virtual_network" in types

    def test_nsg_extracted(self):
        """AZR-001-B: azurerm_network_security_group resource extracted."""
        graph = _scan_azure()
        types = {n.type for n in graph.nodes}
        assert "azurerm_network_security_group" in types

    def test_provider_set_to_azurerm(self):
        """AZR-001-C: provider field set to 'azurerm'."""
        graph = _scan_azure()
        node = next(n for n in graph.nodes if n.type == "azurerm_virtual_network")
        assert node.provider == "azurerm"

    def test_location_mapped_to_region(self):
        """AZR-001-D: location attribute normalised to region field."""
        graph = _scan_azure()
        node = next(n for n in graph.nodes if n.type == "azurerm_virtual_network")
        assert node.region != ""

    def test_storage_account_extracted(self):
        """AZR-001-E: azurerm_storage_account extracted from storage fixture."""
        graph = _scan_azure()
        types = {n.type for n in graph.nodes}
        assert "azurerm_storage_account" in types

    def test_aks_extracted(self):
        """AZR-001-F: azurerm_kubernetes_cluster extracted from compute fixture."""
        graph = _scan_azure()
        types = {n.type for n in graph.nodes}
        assert "azurerm_kubernetes_cluster" in types
