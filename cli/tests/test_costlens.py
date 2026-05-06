"""Tests for CostLens — SharedCostAllocator, IdleDetector, EgressEstimator."""

import pytest

from infracanvas.cost.allocator import SharedCostAllocator  # noqa: F401  (RED — Plan 02)
from infracanvas.cost.idle import IdleDetector  # noqa: F401  (RED — Plan 03)
from infracanvas.cost.egress import EgressEstimator  # noqa: F401  (RED — Plan 04)
from infracanvas.graph.models import ResourceGraph, ResourceNode


def _node(resource_type: str, name: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes=attrs,
    )


def _graph(nodes: list[ResourceNode], edges: list[dict[str, str]] | None = None) -> ResourceGraph:
    return ResourceGraph(nodes=nodes, edges=edges or [])


class TestSharedAllocator:
    @pytest.mark.xfail(reason="not implemented — stub")
    def test_tgw_two_workload_split(self):
        """CLA-C-1: Two workloads share a TGW → each gets 50% of TGW cost"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_nat_gateway_three_way_split(self):
        """CLA-C-2: Three workloads share a NAT gateway → each gets ~33% of NAT cost"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_untagged_workload_appears(self):
        """CLA-C-3: Resources with no workload tag are bucketed into 'untagged' workload"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_allocation_pct_sums_to_100(self):
        """CLA-C-4: allocation_pct values across all workloads sum to 100 for each shared resource"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_no_attachments_skips_allocation(self):
        """CLA-C-5: A shared resource with zero attachments is not allocated to any workload"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_express_route_split(self):
        """CLA-C-6: Azure ExpressRoute shared by N workloads → equal split per workload"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_azure_firewall_split(self):
        """CLA-C-7: Azure Firewall shared by N workloads → equal split per workload"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_workload_tag_key_config(self):
        """CLA-C-8: costlens.workload_tag_key config overrides default 'Service' tag key"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_dedicated_resource_costs(self):
        """CLA-C-9: Dedicated (non-shared) resources are attributed entirely to their tagged workload"""
        pytest.fail("not implemented")


class TestIdleDetector:
    @pytest.mark.xfail(reason="not implemented — stub")
    def test_idle_nat_gateway(self):
        """CLA-C-10: NAT gateway with no attached subnets is flagged as idle"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_idle_tgw(self):
        """CLA-C-11: Transit gateway with zero attachments is flagged as idle"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_idle_express_route(self):
        """CLA-C-12: Azure ExpressRoute circuit with no peering links is flagged as idle"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_idle_vpc_endpoint(self):
        """CLA-C-13: VPC endpoint with no associated services is flagged as idle"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_non_idle_nat_gateway(self):
        """CLA-C-14: NAT gateway with attached subnets is NOT flagged as idle"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_integration_full_graph(self):
        """CLA-C-15: Full graph with mixed idle/non-idle resources returns correct idle list"""
        pytest.fail("not implemented")


class TestEgressEstimator:
    @pytest.mark.xfail(reason="not implemented — stub")
    def test_inter_region_aws_rate(self):
        """CPC-C-1: Inter-region AWS egress path (us-east-1 → us-west-2) uses correct $/GB rate"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_cross_cloud_rate(self):
        """CPC-C-2: Cross-cloud egress path (AWS → Azure) uses correct cross-cloud $/GB rate"""
        pytest.fail("not implemented")

    @pytest.mark.xfail(reason="not implemented — stub")
    def test_no_region_data_graceful(self):
        """CPC-C-3: Missing region data returns zero cost gracefully (no exception)"""
        pytest.fail("not implemented")
