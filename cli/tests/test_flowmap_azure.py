"""Tests for Azure cloud-network FlowMap collector (AZN-01, AZN-02, AZN-03).

All tests mock azure-identity + azure-mgmt-network via sys.modules; no real SDK
install is required. Mirrors Plan 03-03 test_flowmap_aws.py sibling structure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from infracanvas.flowmap.azure import _parse_rg_and_name, collect_azure_network
from infracanvas.graph.models import ResourceGraph

FIXTURES = Path(__file__).parent / "fixtures" / "flowmap" / "azure"
ALL_ARM = {
    "ARM_CLIENT_ID": "test-client-id",
    "ARM_CLIENT_SECRET": "test-secret",
    "ARM_TENANT_ID": "test-tenant-id",
    "ARM_SUBSCRIPTION_ID": "00000000-0000-0000-0000-000000000000",
}


def _load(name: str) -> dict[str, Any]:
    with open(FIXTURES / name) as f:
        return json.load(f)


def _mock_sdk_modules() -> dict[str, Any]:
    """Return patched sys.modules dict with azure.identity + azure.mgmt.network."""
    identity_mod = MagicMock()
    identity_mod.ClientSecretCredential = MagicMock(return_value=MagicMock())
    network_mod = MagicMock()
    network_mod.NetworkManagementClient = MagicMock()
    return {
        "azure": MagicMock(),
        "azure.identity": identity_mod,
        "azure.mgmt": MagicMock(),
        "azure.mgmt.network": network_mod,
    }


def _wrap(items: list[dict[str, Any]]) -> list[MagicMock]:
    wrapped = []
    for item in items:
        m = MagicMock()
        m.as_dict.return_value = item
        wrapped.append(m)
    return wrapped


def _populated_client() -> MagicMock:
    """Build a mocked NetworkManagementClient returning .as_dict()-compatible fakes."""
    vwan = _load("vwan.json")
    vnet = _load("vnet.json")
    er = _load("expressroute.json")

    client = MagicMock()
    client.virtual_wans.list.return_value = _wrap(vwan["virtual_wans"])
    client.virtual_hubs.list.return_value = _wrap(vwan["virtual_hubs"])
    client.hub_virtual_network_connections.list.return_value = _wrap(
        vwan["hub_connections"]
    )
    client.virtual_networks.list_all.return_value = _wrap(vnet["virtual_networks"])
    client.virtual_network_peerings.list.return_value = _wrap(vnet["peerings"])
    client.network_security_groups.list_all.return_value = _wrap(
        vnet["network_security_groups"]
    )
    client.express_route_circuits.list_all.return_value = _wrap(
        er["express_route_circuits"]
    )
    client.express_route_circuit_peerings.list.return_value = _wrap(er["peerings"])
    watcher_id = (
        "/subscriptions/00000000-0000-0000-0000-000000000000"
        "/resourceGroups/NetworkWatcherRG"
        "/providers/Microsoft.Network/networkWatchers/NetworkWatcher_eastus"
    )
    client.network_watchers.list_all.return_value = _wrap([{"id": watcher_id}])
    client.flow_logs.list.return_value = _wrap(er["flow_logs"])
    return client


class TestParseRgAndName:
    def test_happy(self) -> None:
        rg, name = _parse_rg_and_name(
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-hybrid/providers/Microsoft.Network/virtualHubs/hub-east"
        )
        assert rg == "rg-hybrid"
        assert name == "hub-east"

    def test_empty(self) -> None:
        assert _parse_rg_and_name("") == ("", "")

    def test_malformed(self) -> None:
        assert _parse_rg_and_name("/not/a/real/resource/id") == ("", "")


class TestImportGuards:
    def test_missing_sdk_raises(self) -> None:
        with patch.dict(
            "sys.modules",
            {"azure.identity": None, "azure.mgmt.network": None},
        ):
            with pytest.raises(RuntimeError, match="azure-mgmt-network not installed"):
                collect_azure_network(ResourceGraph())


class TestCredentialGuards:
    def test_missing_all_creds_lists_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v in ALL_ARM:
            monkeypatch.delenv(v, raising=False)
        with patch.dict("sys.modules", _mock_sdk_modules()):
            with pytest.raises(RuntimeError) as exc_info:
                collect_azure_network(ResourceGraph())
        msg = str(exc_info.value)
        for v in ALL_ARM:
            assert v in msg

    def test_missing_single_cred_lists_only_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for v, val in ALL_ARM.items():
            monkeypatch.setenv(v, val)
        monkeypatch.delenv("ARM_TENANT_ID", raising=False)
        with patch.dict("sys.modules", _mock_sdk_modules()):
            with pytest.raises(RuntimeError) as exc_info:
                collect_azure_network(ResourceGraph())
        msg = str(exc_info.value)
        assert "ARM_TENANT_ID" in msg
        # The 3 set vars must NOT appear in the message
        assert "ARM_CLIENT_ID" not in msg
        assert "ARM_CLIENT_SECRET" not in msg
        assert "ARM_SUBSCRIPTION_ID" not in msg

    def test_credential_values_not_leaked_in_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-03-04-02: ARM_CLIENT_SECRET value must never appear in error output."""
        monkeypatch.setenv("ARM_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("ARM_CLIENT_SECRET", "super-secret-v4lue-xyz")
        monkeypatch.setenv("ARM_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000000")
        monkeypatch.delenv("ARM_TENANT_ID", raising=False)
        with patch.dict("sys.modules", _mock_sdk_modules()):
            with pytest.raises(RuntimeError) as exc_info:
                collect_azure_network(ResourceGraph())
        assert "super-secret-v4lue-xyz" not in str(exc_info.value)
        assert "super-secret-v4lue-xyz" not in str(exc_info.value.args)


class TestCollectAzureNetwork:
    @pytest.fixture(autouse=True)
    def _setenv(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v, val in ALL_ARM.items():
            monkeypatch.setenv(v, val)

    def _run(self, client: MagicMock | None = None) -> ResourceGraph:
        client = client or _populated_client()
        modules = _mock_sdk_modules()
        modules["azure.mgmt.network"].NetworkManagementClient.return_value = client
        with patch.dict("sys.modules", modules):
            return collect_azure_network(ResourceGraph())

    def test_virtual_wans(self) -> None:
        g = self._run()
        wans = [n for n in g.nodes if n.type == "azurerm_virtual_wan"]
        assert len(wans) == 1
        assert wans[0].name == "vwan-primary"
        assert wans[0].provider == "azure"
        assert wans[0].attributes["provisioning_state"] == "Succeeded"
        assert wans[0].attributes["allow_branch_to_branch_traffic"] is True
        assert wans[0].attributes["sku"] == "Standard"

    def test_virtual_hubs_and_connections(self) -> None:
        g = self._run()
        hubs = [n for n in g.nodes if n.type == "azurerm_virtual_hub"]
        conns = [n for n in g.nodes if n.type == "azurerm_virtual_hub_connection"]
        assert len(hubs) == 1
        assert hubs[0].name == "hub-east"
        assert hubs[0].attributes["address_prefix"] == "10.100.0.0/23"
        assert len(conns) == 1
        assert conns[0].name == "conn-vnet-prod"
        assert conns[0].attributes["enable_internet_security"] is True

    def test_virtual_networks_and_peerings(self) -> None:
        g = self._run()
        vnets = [n for n in g.nodes if n.type == "azurerm_virtual_network"]
        peerings = [n for n in g.nodes if n.type == "azurerm_virtual_network_peering"]
        assert len(vnets) == 1
        assert vnets[0].attributes["address_space"] == ["10.10.0.0/16"]
        subnets = vnets[0].attributes["subnets"]
        assert isinstance(subnets, list)
        assert len(subnets) == 2
        assert len(peerings) == 1
        assert peerings[0].attributes["peering_state"] == "Connected"

    def test_nsg_with_rules(self) -> None:
        g = self._run()
        nsgs = [n for n in g.nodes if n.type == "azurerm_network_security_group"]
        assert len(nsgs) == 1
        rules = nsgs[0].attributes.get("security_rules", [])
        assert isinstance(rules, list)
        assert any(r.get("name") == "allow-https" for r in rules)

    def test_express_route_circuit_and_peering(self) -> None:
        g = self._run()
        circuits = [n for n in g.nodes if n.type == "azurerm_express_route_circuit"]
        peerings = [
            n for n in g.nodes if n.type == "azurerm_express_route_circuit_peering"
        ]
        assert len(circuits) == 1
        assert circuits[0].attributes["bandwidth_mbps"] == 10000
        assert circuits[0].attributes["service_provider"] == "Equinix"
        assert len(peerings) == 1
        assert peerings[0].attributes["peer_asn"] == 64521
        assert peerings[0].attributes["peering_type"] == "AzurePrivatePeering"
        assert peerings[0].attributes["vlan_id"] == 100

    def test_flow_log_metadata_attached_to_nsg(self) -> None:
        g = self._run()
        nsg = next(n for n in g.nodes if n.type == "azurerm_network_security_group")
        assert "flow_log" in nsg.attributes
        fl = nsg.attributes["flow_log"]
        assert isinstance(fl, dict)
        assert fl["enabled"] is True
        assert fl["retention_days"] == 30
        assert fl["format_type"] == "JSON"

    def test_api_failure_swallowed(self) -> None:
        """HttpResponseError on one API must NOT abort other collectors (defensive wrapper)."""
        client = _populated_client()
        client.virtual_networks.list_all.side_effect = Exception(
            "HttpResponseError: 403"
        )
        g = self._run(client=client)
        # vWAN still collects
        assert any(n.type == "azurerm_virtual_wan" for n in g.nodes)
        # ExpressRoute still collects
        assert any(n.type == "azurerm_express_route_circuit" for n in g.nodes)
        # vNet was the one that failed — should be absent
        assert not any(n.type == "azurerm_virtual_network" for n in g.nodes)

    def test_empty_subscription_returns_empty_graph(self) -> None:
        """With all list() APIs empty, graph stays empty — no exceptions."""
        client = MagicMock()
        client.virtual_wans.list.return_value = []
        client.virtual_hubs.list.return_value = []
        client.virtual_networks.list_all.return_value = []
        client.network_security_groups.list_all.return_value = []
        client.express_route_circuits.list_all.return_value = []
        client.network_watchers.list_all.return_value = []
        g = self._run(client=client)
        azure_nodes = [n for n in g.nodes if n.provider == "azure"]
        assert len(azure_nodes) == 0

    def test_node_types_use_azurerm_prefix(self) -> None:
        """All produced node types must match Phase 2 Azure parser convention."""
        g = self._run()
        expected_types = {
            "azurerm_virtual_wan",
            "azurerm_virtual_hub",
            "azurerm_virtual_hub_connection",
            "azurerm_virtual_network",
            "azurerm_virtual_network_peering",
            "azurerm_network_security_group",
            "azurerm_express_route_circuit",
            "azurerm_express_route_circuit_peering",
        }
        produced_types = {n.type for n in g.nodes if n.provider == "azure"}
        assert expected_types.issubset(produced_types), (
            f"Missing: {expected_types - produced_types}"
        )
