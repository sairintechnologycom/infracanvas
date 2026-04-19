"""Tests for FlowMap Pydantic models (FDM-01, FDM-02)."""

from __future__ import annotations

import pytest

from infracanvas.graph.models import (
    DCCollectorReading,
    DCSite,
    NetworkFinding,
    NetworkPath,
    PathHop,
    ResourceGraph,
    Severity,
)


class TestResourceGraphSchemaBump:
    """FDM-01: ResourceGraph v2.0 -> v2.1 additive schema bump."""

    def test_version_is_2_1(self):
        """ResourceGraph defaults to version '2.1' (bumped from '2.0')."""
        graph = ResourceGraph()
        assert graph.version == "2.1"

    def test_network_paths_defaults_empty(self):
        """ResourceGraph.network_paths defaults to empty list."""
        graph = ResourceGraph()
        assert graph.network_paths == []

    def test_dc_sites_defaults_empty(self):
        """ResourceGraph.dc_sites defaults to empty list."""
        graph = ResourceGraph()
        assert graph.dc_sites == []

    def test_legacy_v2_0_json_loads_with_defaults(self):
        """Backwards-compat: v2.0 JSON without network_paths/dc_sites loads into v2.1 shape."""
        legacy = {
            "version": "2.0",
            "metadata": {},
            "nodes": [],
            "edges": [],
            "summary": {
                "total_resources": 0,
                "findings": {"critical": 0, "high": 0, "medium": 0, "info": 0},
                "estimated_monthly_cost": 0.0,
                "score": 100,
                "drift": {"added": 0, "changed": 0, "deleted": 0},
            },
        }
        graph = ResourceGraph.model_validate(legacy)
        assert graph.network_paths == []
        assert graph.dc_sites == []

    def test_round_trip_serialisation_preserves_new_fields(self):
        """ResourceGraph.model_dump() includes network_paths and dc_sites."""
        graph = ResourceGraph(
            network_paths=[
                NetworkPath(
                    id="p",
                    source_node_id="a",
                    dest_node_id="b",
                    direction="forward",
                    hops=[],
                ),
            ],
        )
        dumped = graph.model_dump()
        assert dumped["network_paths"][0]["id"] == "p"
        assert dumped["version"] == "2.1"
        assert "dc_sites" in dumped


class TestNetworkPath:
    """FDM-01: NetworkPath model."""

    def test_valid_fields(self):
        path = NetworkPath(
            id="p1",
            source_node_id="tgw-abc",
            dest_node_id="vwan-hub-1",
            direction="forward",
            hops=[],
        )
        assert path.id == "p1"
        assert path.direction == "forward"
        assert path.hops == []
        assert path.evidence == {}

    def test_missing_required_raises(self):
        with pytest.raises(Exception):
            NetworkPath(id="p1")  # type: ignore[call-arg]


class TestPathHop:
    """FDM-01: PathHop model."""

    def test_valid_fields(self):
        hop = PathHop(
            hop_index=0,
            node_id="vpc-rt-1",
            source_ip="10.0.0.1",
            dest_ip="10.1.0.1",
            protocol="tcp",
            port=443,
            interface_in="eth0",
            interface_out="eth1",
        )
        assert hop.hop_index == 0
        assert hop.node_id == "vpc-rt-1"
        assert hop.port == 443
        assert hop.bgp_as_path == []
        assert hop.next_hop == ""
        assert hop.evidence == {}


class TestDCCollectorReading:
    """FDM-02: DCCollectorReading model."""

    def test_valid_fields(self):
        reading = DCCollectorReading(
            site_id="dc-nyc",
            collector_type="router",
            collected_at="2026-04-18T10:00:00Z",
            payload={},
        )
        assert reading.site_id == "dc-nyc"
        assert reading.collector_type == "router"
        assert reading.payload == {}


class TestDCSite:
    """FDM-02: DCSite model."""

    def test_valid_fields(self):
        site = DCSite(
            id="dc-nyc",
            name="New York DC",
            location="NYC",
            routers=[],
            firewalls=[],
        )
        assert site.id == "dc-nyc"
        assert site.name == "New York DC"
        assert site.readings == []


class TestNetworkFindingExtended:
    """FDM-01: extended NetworkFinding aligned with rule-engine shape (D-12, NFN-01)."""

    def test_rule_engine_compatible_fields(self):
        finding = NetworkFinding(
            rule_id="NET-001",
            severity=Severity.high,
            title="x",
            description="y",
            remediation="z",
            source_ip="",
            dest_ip="",
            protocol="",
            port=0,
        )
        assert finding.rule_id == "NET-001"
        assert finding.source == "network"
        assert finding.framework_ids == []
        assert finding.path_id == ""
        assert finding.hop_id == ""
