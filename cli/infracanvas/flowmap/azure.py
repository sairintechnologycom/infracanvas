"""Azure cloud-network topology collector for FlowMap (AZN-01, AZN-02, AZN-03).

Read-only azure-mgmt-network calls against VirtualWAN, VirtualHub, vNet, NSG,
ExpressRoute. Appends ResourceNode entries to the provided ResourceGraph.
Never hard-fails on individual API errors.

Credentials: ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
env vars only (CONTEXT.md D-05, Phase 2 D-07). Fails loudly if any missing — but
orchestrator (collector.py) catches the RuntimeError and warns without hard-failing.

SECURITY (T-03-04-02): RuntimeError strings NEVER embed env-var VALUES — only
the MISSING-var names. `from None` on ImportError strips SDK traceback.
"""
from __future__ import annotations

import os
from typing import Any

from infracanvas.graph.models import (
    CostEstimate,
    DriftStatus,
    ResourceGraph,
    ResourceNode,
)

_ARM_REQUIRED = [
    "ARM_CLIENT_ID",
    "ARM_CLIENT_SECRET",
    "ARM_TENANT_ID",
    "ARM_SUBSCRIPTION_ID",
]


def collect_azure_network(graph: ResourceGraph) -> ResourceGraph:
    """Collect Azure network topology; append to graph.nodes.

    Raises:
        RuntimeError: when azure SDK missing or ARM_* env vars absent.
    """
    try:
        from azure.identity import ClientSecretCredential  # noqa: PLC0415
        from azure.mgmt.network import NetworkManagementClient  # noqa: PLC0415
    except ImportError:
        # SECURITY: message must be credential-free
        raise RuntimeError(
            "azure-mgmt-network not installed. "
            "Install with: pip install 'infracanvas[flowmap]'"
        ) from None

    missing = [v for v in _ARM_REQUIRED if not os.environ.get(v)]
    if missing:
        # SECURITY: surface only the MISSING-var names — never the set values
        raise RuntimeError(
            f"--flowmap requires Azure credentials: {', '.join(missing)} missing."
        )

    cred = ClientSecretCredential(
        tenant_id=os.environ["ARM_TENANT_ID"],
        client_id=os.environ["ARM_CLIENT_ID"],
        client_secret=os.environ["ARM_CLIENT_SECRET"],
    )
    client = NetworkManagementClient(cred, os.environ["ARM_SUBSCRIPTION_ID"])

    location_hint = _infer_location(graph)

    _collect_virtual_wans(graph, client, location=location_hint)
    _collect_virtual_hubs(graph, client, location=location_hint)
    _collect_virtual_networks(graph, client, location=location_hint)
    _collect_network_security_groups(graph, client, location=location_hint)
    _collect_express_route_circuits(graph, client, location=location_hint)
    _collect_flow_log_metadata(graph, client, location=location_hint)

    return graph


def _infer_location(graph: ResourceGraph, default: str = "eastus") -> str:
    """Infer Azure location from graph nodes (mirrors region inference in aws.py)."""
    for node in graph.nodes:
        if node.provider == "azure" and node.region:
            return node.region
    return default


def _add_node(
    graph: ResourceGraph,
    *,
    resource_type: str,
    name: str,
    region: str,
    attributes: dict[str, Any],
) -> None:
    node = ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="azure",
        region=region,
        attributes=attributes,
        drift=DriftStatus.unchanged,
        cost=CostEstimate(monthly_usd=0.0, basis="flowmap collection"),
    )
    graph.nodes.append(node)


def _as_dict(obj: Any) -> dict[str, Any]:
    """Azure SDK returns Model objects; unwrap to dict via .as_dict() if present."""
    if hasattr(obj, "as_dict"):
        result = obj.as_dict()
        return result if isinstance(result, dict) else {}
    if isinstance(obj, dict):
        return obj
    return {}


def _collect_virtual_wans(graph: ResourceGraph, client: Any, *, location: str) -> None:
    try:
        for wan in client.virtual_wans.list() or []:
            data = _as_dict(wan)
            name = data.get("name", "")
            props = data.get("properties", {}) or {}
            _add_node(
                graph,
                resource_type="azurerm_virtual_wan",
                name=name,
                region=data.get("location", location),
                attributes={
                    "id": data.get("id", ""),
                    "provisioning_state": props.get("provisioningState", ""),
                    "allow_branch_to_branch_traffic": props.get(
                        "allowBranchToBranchTraffic", False
                    ),
                    "sku": props.get("type", ""),
                },
            )
    except Exception:  # noqa: BLE001 — Azure SDK raises HttpResponseError variants
        pass


def _collect_virtual_hubs(graph: ResourceGraph, client: Any, *, location: str) -> None:
    try:
        for hub in client.virtual_hubs.list() or []:
            data = _as_dict(hub)
            name = data.get("name", "")
            props = data.get("properties", {}) or {}
            _add_node(
                graph,
                resource_type="azurerm_virtual_hub",
                name=name,
                region=data.get("location", location),
                attributes={
                    "id": data.get("id", ""),
                    "address_prefix": props.get("addressPrefix", ""),
                    "virtual_wan_id": (props.get("virtualWan", {}) or {}).get("id", ""),
                    "provisioning_state": props.get("provisioningState", ""),
                },
            )
            # Fetch hub connections — best-effort (requires rg + hub name from id)
            rg, hub_name = _parse_rg_and_name(data.get("id", ""))
            if rg and hub_name:
                try:
                    for conn in client.hub_virtual_network_connections.list(
                        rg, hub_name
                    ) or []:
                        conn_data = _as_dict(conn)
                        conn_props = conn_data.get("properties", {}) or {}
                        _add_node(
                            graph,
                            resource_type="azurerm_virtual_hub_connection",
                            name=conn_data.get("name", ""),
                            region=location,
                            attributes={
                                "id": conn_data.get("id", ""),
                                "virtual_hub_id": data.get("id", ""),
                                "remote_virtual_network_id": (
                                    conn_props.get("remoteVirtualNetwork", {}) or {}
                                ).get("id", ""),
                                "allow_hub_to_remote_vnet_transit": conn_props.get(
                                    "allowHubToRemoteVnetTransit", False
                                ),
                                "enable_internet_security": conn_props.get(
                                    "enableInternetSecurity", False
                                ),
                                "provisioning_state": conn_props.get(
                                    "provisioningState", ""
                                ),
                            },
                        )
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        pass


def _collect_virtual_networks(graph: ResourceGraph, client: Any, *, location: str) -> None:
    try:
        for vnet in client.virtual_networks.list_all() or []:
            data = _as_dict(vnet)
            name = data.get("name", "")
            props = data.get("properties", {}) or {}
            subnets_raw = props.get("subnets") or []
            _add_node(
                graph,
                resource_type="azurerm_virtual_network",
                name=name,
                region=data.get("location", location),
                attributes={
                    "id": data.get("id", ""),
                    "address_space": (props.get("addressSpace", {}) or {}).get(
                        "addressPrefixes", []
                    ),
                    "subnets": [
                        {
                            "name": s.get("name", ""),
                            "address_prefix": (s.get("properties") or {}).get(
                                "addressPrefix", ""
                            ),
                        }
                        for s in subnets_raw
                    ],
                },
            )
            rg, vnet_name = _parse_rg_and_name(data.get("id", ""))
            if rg and vnet_name:
                try:
                    for peering in client.virtual_network_peerings.list(
                        rg, vnet_name
                    ) or []:
                        p = _as_dict(peering)
                        p_props = p.get("properties", {}) or {}
                        _add_node(
                            graph,
                            resource_type="azurerm_virtual_network_peering",
                            name=p.get("name", ""),
                            region=location,
                            attributes={
                                "id": p.get("id", ""),
                                "virtual_network_id": data.get("id", ""),
                                "remote_virtual_network_id": (
                                    p_props.get("remoteVirtualNetwork", {}) or {}
                                ).get("id", ""),
                                "allow_virtual_network_access": p_props.get(
                                    "allowVirtualNetworkAccess", False
                                ),
                                "allow_forwarded_traffic": p_props.get(
                                    "allowForwardedTraffic", False
                                ),
                                "allow_gateway_transit": p_props.get(
                                    "allowGatewayTransit", False
                                ),
                                "use_remote_gateways": p_props.get(
                                    "useRemoteGateways", False
                                ),
                                "peering_state": p_props.get("peeringState", ""),
                            },
                        )
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        pass


def _collect_network_security_groups(
    graph: ResourceGraph, client: Any, *, location: str
) -> None:
    try:
        for nsg in client.network_security_groups.list_all() or []:
            data = _as_dict(nsg)
            props = data.get("properties", {}) or {}
            _add_node(
                graph,
                resource_type="azurerm_network_security_group",
                name=data.get("name", ""),
                region=data.get("location", location),
                attributes={
                    "id": data.get("id", ""),
                    "security_rules": props.get("securityRules", []),
                    "default_security_rules": props.get("defaultSecurityRules", []),
                },
            )
    except Exception:  # noqa: BLE001
        pass


def _collect_express_route_circuits(
    graph: ResourceGraph, client: Any, *, location: str
) -> None:
    try:
        for circuit in client.express_route_circuits.list_all() or []:
            data = _as_dict(circuit)
            name = data.get("name", "")
            props = data.get("properties", {}) or {}
            sp_props = props.get("serviceProviderProperties", {}) or {}
            _add_node(
                graph,
                resource_type="azurerm_express_route_circuit",
                name=name,
                region=data.get("location", location),
                attributes={
                    "id": data.get("id", ""),
                    "sku": data.get("sku", {}),
                    "bandwidth_mbps": sp_props.get("bandwidthInMbps", 0),
                    "service_provider": sp_props.get("serviceProviderName", ""),
                    "peering_location": sp_props.get("peeringLocation", ""),
                    "service_provider_provisioning_state": props.get(
                        "serviceProviderProvisioningState", ""
                    ),
                    "circuit_provisioning_state": props.get(
                        "circuitProvisioningState", ""
                    ),
                },
            )
            rg, circuit_name = _parse_rg_and_name(data.get("id", ""))
            if rg and circuit_name:
                try:
                    for peering in client.express_route_circuit_peerings.list(
                        rg, circuit_name
                    ) or []:
                        p = _as_dict(peering)
                        p_props = p.get("properties", {}) or {}
                        _add_node(
                            graph,
                            resource_type="azurerm_express_route_circuit_peering",
                            name=p.get("name", ""),
                            region=location,
                            attributes={
                                "id": p.get("id", ""),
                                "circuit_id": data.get("id", ""),
                                "peering_type": p_props.get("peeringType", ""),
                                "state": p_props.get("state", ""),
                                "peer_asn": p_props.get("peerASN", 0),
                                "primary_peer_address_prefix": p_props.get(
                                    "primaryPeerAddressPrefix", ""
                                ),
                                "secondary_peer_address_prefix": p_props.get(
                                    "secondaryPeerAddressPrefix", ""
                                ),
                                "vlan_id": p_props.get("vlanId", 0),
                            },
                        )
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        pass


def _collect_flow_log_metadata(
    graph: ResourceGraph, client: Any, *, location: str
) -> None:
    """AZN-03 metadata-only in 3a — attach flow-log existence to the NSG node."""
    try:
        watchers_by_rg: dict[str, list[str]] = {}
        for watcher in client.network_watchers.list_all() or []:
            w = _as_dict(watcher)
            rg, name = _parse_rg_and_name(w.get("id", ""))
            if rg and name:
                watchers_by_rg.setdefault(rg, []).append(name)

        nsg_flow_log: dict[str, dict[str, Any]] = {}
        for rg, watchers in watchers_by_rg.items():
            for watcher_name in watchers:
                try:
                    for fl in client.flow_logs.list(rg, watcher_name) or []:
                        data = _as_dict(fl)
                        props = data.get("properties", {}) or {}
                        target_id = props.get("targetResourceId", "")
                        if target_id:
                            nsg_flow_log[target_id] = {
                                "flow_log_id": data.get("id", ""),
                                "enabled": props.get("enabled", False),
                                "retention_days": (
                                    props.get("retentionPolicy", {}) or {}
                                ).get("days", 0),
                                "format_type": (
                                    props.get("format", {}) or {}
                                ).get("type", ""),
                                "storage_id": props.get("storageId", ""),
                            }
                except Exception:  # noqa: BLE001
                    pass

        # Attach to collected NSG nodes
        for node in graph.nodes:
            if node.type == "azurerm_network_security_group":
                nsg_id = str(node.attributes.get("id", ""))
                if nsg_id in nsg_flow_log:
                    node.attributes["flow_log"] = nsg_flow_log[nsg_id]
    except Exception:  # noqa: BLE001
        pass


def _parse_rg_and_name(resource_id: str) -> tuple[str, str]:
    """Parse '/subscriptions/.../resourceGroups/{rg}/providers/.../(resource)/{name}'.

    Returns (resource_group, resource_name) or ("", "") if parse fails.
    """
    if not resource_id:
        return "", ""
    parts = resource_id.split("/")
    try:
        rg_idx = parts.index("resourceGroups")
        rg = parts[rg_idx + 1]
        name = parts[-1]
        return rg, name
    except (ValueError, IndexError):
        return "", ""
