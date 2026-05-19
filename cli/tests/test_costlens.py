"""Tests for CostLens — SharedCostAllocator, IdleDetector, EgressEstimator."""


from infracanvas.cost.allocator import SharedCostAllocator
from infracanvas.cost.egress import EgressEstimator
from infracanvas.cost.idle import IdleDetector  # noqa: F401  (RED — Plan 03)
from infracanvas.graph.models import CostEstimate, NetworkPath, ResourceGraph, ResourceNode


def _node(
    resource_type: str,
    name: str,
    attrs: dict | None = None,
    monthly_usd: float = 0.0,
    provider: str = "aws",
) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider=provider,
        attributes=attrs or {},
        cost=CostEstimate(monthly_usd=monthly_usd, currency="USD", basis="flat"),
    )


def _graph(nodes: list[ResourceNode], edges: list[tuple[str, str]] | None = None) -> ResourceGraph:
    return ResourceGraph(
        nodes=nodes,
        edges=[{"source": s, "target": t} for s, t in (edges or [])],
    )


class TestSharedAllocator:
    def test_tgw_two_workload_split(self):
        """CLA-C-1: Two workloads share a TGW → each gets 50% of TGW cost."""
        tgw = _node("aws_ec2_transit_gateway", "tgw", monthly_usd=100.0)
        ec2_a = _node("aws_instance", "app_a", attrs={"Service": "frontend"}, monthly_usd=20.0)
        ec2_b = _node("aws_instance", "app_b", attrs={"Service": "backend"}, monthly_usd=20.0)
        graph = _graph(
            [tgw, ec2_a, ec2_b],
            [(tgw.id, ec2_a.id), (tgw.id, ec2_b.id)],
        )
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        wl_names = {w.name for w in result.costlens.workloads}
        assert "frontend" in wl_names
        assert "backend" in wl_names
        for wl in result.costlens.workloads:
            items_for_tgw = [i for i in wl.line_items if i.resource_id == tgw.id]
            assert len(items_for_tgw) == 1
            assert items_for_tgw[0].share_pct == 50.0

    def test_nat_gateway_three_way_split(self):
        """CLA-C-2: Three workloads share a NAT gateway → shares sum to 100.0."""
        nat = _node("aws_nat_gateway", "nat1", monthly_usd=32.85)
        ec2_a = _node("aws_instance", "a", attrs={"Service": "svc-a"})
        ec2_b = _node("aws_instance", "b", attrs={"Service": "svc-b"})
        ec2_c = _node("aws_instance", "c", attrs={"Service": "svc-c"})
        graph = _graph(
            [nat, ec2_a, ec2_b, ec2_c],
            [(nat.id, ec2_a.id), (nat.id, ec2_b.id), (nat.id, ec2_c.id)],
        )
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        all_items_for_nat = [
            i
            for wl in result.costlens.workloads
            for i in wl.line_items
            if i.resource_id == nat.id
        ]
        assert len(all_items_for_nat) == 3
        total_pct = sum(i.share_pct for i in all_items_for_nat)
        assert abs(total_pct - 100.0) < 0.001

    def test_untagged_workload_appears(self):
        """CLA-C-3: Resources with no workload tag are bucketed into 'untagged' workload."""
        vpc_ep = _node("aws_vpc_endpoint", "ep1", monthly_usd=7.30)
        tagged = _node("aws_instance", "tagged_inst", attrs={"Service": "api"})
        untagged = _node("aws_instance", "no_tag_inst", attrs={})
        graph = _graph(
            [vpc_ep, tagged, untagged],
            [(vpc_ep.id, tagged.id), (vpc_ep.id, untagged.id)],
        )
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        wl_names = {w.name for w in result.costlens.workloads}
        assert "untagged" in wl_names
        assert "api" in wl_names

    def test_allocation_pct_sums_to_100(self):
        """CLA-C-4: allocation_pct values across all workloads sum to exactly 100.0."""
        nat = _node("aws_nat_gateway", "nat1", monthly_usd=32.85)
        nodes = [nat] + [
            _node("aws_instance", f"inst_{i}", attrs={"Service": f"svc-{i}"})
            for i in range(3)
        ]
        edges = [(nat.id, nodes[i + 1].id) for i in range(3)]
        graph = _graph(nodes, edges)
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        for sr in result.costlens.shared_resources:
            items_for_sr = [
                i
                for wl_obj in result.costlens.workloads
                for i in wl_obj.line_items
                if i.resource_id == sr.resource_id
            ]
            if items_for_sr:
                total_pct = sum(i.share_pct for i in items_for_sr)
                assert abs(total_pct - 100.0) < 0.001, (
                    f"Allocation %% sums to {total_pct}, expected 100.0"
                )

    def test_no_attachments_skips_allocation(self):
        """CLA-C-5: A shared resource with zero attachments appears in shared_resources only."""
        tgw = _node("aws_ec2_transit_gateway", "tgw", monthly_usd=36.50)
        ec2_a = _node("aws_instance", "app_a", attrs={"Service": "frontend"})
        # No edges — TGW has no attachments
        graph = _graph([tgw, ec2_a], [])
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        # TGW appears in shared_resources
        sr_ids = {sr.resource_id for sr in result.costlens.shared_resources}
        assert tgw.id in sr_ids
        # No workload receives a TGW line item
        all_tgw_items = [
            i
            for wl in result.costlens.workloads
            for i in wl.line_items
            if i.resource_id == tgw.id
        ]
        assert all_tgw_items == []

    def test_express_route_split(self):
        """CLA-C-6: Azure ExpressRoute shared by two vNet workloads → equal split."""
        er = _node(
            "azurerm_express_route_circuit", "er1", monthly_usd=55.0, provider="azure"
        )
        vnet_a = _node("azurerm_virtual_network", "vnet-a", attrs={"Service": "prod"}, provider="azure")
        vnet_b = _node("azurerm_virtual_network", "vnet-b", attrs={"Service": "staging"}, provider="azure")
        graph = _graph(
            [er, vnet_a, vnet_b],
            [(er.id, vnet_a.id), (er.id, vnet_b.id)],
        )
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        wl_names = {w.name for w in result.costlens.workloads}
        assert "prod" in wl_names
        assert "staging" in wl_names
        for wl in result.costlens.workloads:
            er_items = [i for i in wl.line_items if i.resource_id == er.id]
            assert len(er_items) == 1
            assert er_items[0].share_pct == 50.0

    def test_azure_firewall_split(self):
        """CLA-C-7: Azure Firewall shared by three route-table workloads → three-way split."""
        fw = _node("azurerm_firewall", "fw1", monthly_usd=912.50, provider="azure")
        rt_a = _node("azurerm_route_table", "rt-a", attrs={"Service": "app"}, provider="azure")
        rt_b = _node("azurerm_route_table", "rt-b", attrs={"Service": "data"}, provider="azure")
        rt_c = _node("azurerm_route_table", "rt-c", attrs={"Service": "mgmt"}, provider="azure")
        graph = _graph(
            [fw, rt_a, rt_b, rt_c],
            [(fw.id, rt_a.id), (fw.id, rt_b.id), (fw.id, rt_c.id)],
        )
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        all_fw_items = [
            i
            for wl in result.costlens.workloads
            for i in wl.line_items
            if i.resource_id == fw.id
        ]
        assert len(all_fw_items) == 3
        total_pct = sum(i.share_pct for i in all_fw_items)
        assert abs(total_pct - 100.0) < 0.001

    def test_workload_tag_key_config(self):
        """CLA-C-8: workload_tag_key='Team' reads node.attributes['Team'] not 'Service'."""
        tgw = _node("aws_ec2_transit_gateway", "tgw", monthly_usd=36.50)
        ec2_a = _node("aws_instance", "a", attrs={"Team": "platform", "Service": "wrong-key"})
        ec2_b = _node("aws_instance", "b", attrs={"Team": "data", "Service": "wrong-key"})
        graph = _graph(
            [tgw, ec2_a, ec2_b],
            [(tgw.id, ec2_a.id), (tgw.id, ec2_b.id)],
        )
        allocator = SharedCostAllocator(workload_tag_key="Team")
        result = allocator.allocate(graph)
        assert result.costlens is not None
        wl_names = {w.name for w in result.costlens.workloads}
        assert "platform" in wl_names
        assert "data" in wl_names
        assert "wrong-key" not in wl_names

    def test_dedicated_resource_costs(self):
        """CLA-C-9: Dedicated (non-shared) resources are attributed entirely to their workload."""
        # No shared resources — only dedicated EC2 instances tagged to workloads
        ec2_a = _node("aws_instance", "app1", attrs={"Service": "frontend"}, monthly_usd=50.0)
        ec2_b = _node("aws_instance", "app2", attrs={"Service": "backend"}, monthly_usd=80.0)
        graph = _graph([ec2_a, ec2_b], [])
        allocator = SharedCostAllocator()
        result = allocator.allocate(graph)
        assert result.costlens is not None
        wl_map = {w.name: w for w in result.costlens.workloads}
        assert "frontend" in wl_map
        assert "backend" in wl_map
        assert wl_map["frontend"].total_monthly_usd == 50.0
        assert wl_map["backend"].total_monthly_usd == 80.0
        # share_pct is 0.0 for dedicated resources
        for item in wl_map["frontend"].line_items:
            assert item.share_pct == 0.0
        for item in wl_map["backend"].line_items:
            assert item.share_pct == 0.0


class TestIdleDetector:
    def test_idle_nat_gateway(self):
        """CLA-C-10: NAT GW with no aws_route edge targeting it → IdleRecommendation generated."""
        nat = _node("aws_nat_gateway", "main", monthly_usd=32.85)
        graph = _graph([nat], [])
        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)
        assert len(graph.costlens.recommendations) == 1
        rec = graph.costlens.recommendations[0]
        assert rec.resource_id == nat.id
        assert rec.monthly_waste_usd == 32.85

    def test_idle_tgw(self):
        """CLA-C-11: TGW with no aws_ec2_transit_gateway_vpc_attachment child → recommendation."""
        tgw = _node("aws_ec2_transit_gateway", "main", monthly_usd=36.50)
        graph = _graph([tgw], [])
        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)
        assert len(graph.costlens.recommendations) == 1
        rec = graph.costlens.recommendations[0]
        assert rec.resource_id == tgw.id
        assert rec.monthly_waste_usd == 36.50

    def test_idle_express_route(self):
        """CLA-C-12: Azure ExpressRoute with no gateway_connection child → recommendation."""
        er = _node("azurerm_express_route_circuit", "main", monthly_usd=55.0, provider="azure")
        graph = _graph([er], [])
        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)
        assert len(graph.costlens.recommendations) == 1
        rec = graph.costlens.recommendations[0]
        assert rec.resource_id == er.id
        assert rec.monthly_waste_usd == 55.0

    def test_idle_vpc_endpoint(self):
        """CLA-C-13: VPC endpoint with no aws_route_table edge targeting it → recommendation."""
        ep = _node("aws_vpc_endpoint", "main", monthly_usd=7.30)
        graph = _graph([ep], [])
        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)
        assert len(graph.costlens.recommendations) == 1
        rec = graph.costlens.recommendations[0]
        assert rec.resource_id == ep.id
        assert rec.monthly_waste_usd == 7.30

    def test_non_idle_nat_gateway(self):
        """CLA-C-14: NAT GW WITH a valid aws_route edge targeting it → NO recommendation."""
        nat = _node("aws_nat_gateway", "main", monthly_usd=32.85)
        route = _node("aws_route", "main_route")
        # route → nat (aws_route has an edge targeting the NAT GW)
        graph = _graph([nat, route], [(route.id, nat.id)])
        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)
        assert len(graph.costlens.recommendations) == 0

    def test_integration_full_graph(self):
        """CLA-C-15: Full graph scan produces valid CostLensData JSON block."""
        import json

        from infracanvas.cost.allocator import SharedCostAllocator
        from infracanvas.cost.idle import IdleDetector

        # Build a graph with: TGW + attachment (1 workload), idle NAT GW
        tgw = _node("aws_ec2_transit_gateway", "main", monthly_usd=36.50)
        attachment = _node(
            "aws_ec2_transit_gateway_vpc_attachment",
            "app_attach",
            attrs={"Service": "payments"},
            monthly_usd=0.0,
        )
        nat = _node("aws_nat_gateway", "main", monthly_usd=32.85)  # idle — no aws_route edge

        graph = _graph(
            [tgw, attachment, nat],
            [(tgw.id, attachment.id)],  # TGW → attachment; no aws_route → nat, so nat is idle
        )

        graph = SharedCostAllocator().allocate(graph)
        graph = IdleDetector().detect(graph)

        assert graph.costlens is not None
        # Workloads: 'payments' should appear (from attachment tag)
        wl_names = [w.name for w in graph.costlens.workloads]
        assert "payments" in wl_names
        # Recommendations: nat should be idle
        assert len(graph.costlens.recommendations) >= 1
        assert any(r.resource_id == nat.id for r in graph.costlens.recommendations)
        # JSON serialization works
        json_str = graph.model_dump_json()
        parsed = json.loads(json_str)
        assert "costlens" in parsed
        assert parsed["costlens"]["workloads"] is not None


class TestEgressEstimator:
    def test_inter_region_aws_rate(self):
        """CPC-C-1: Inter-region path AWS us-east-1 → eu-west-1 → correct per-GB rate."""
        src = _node("aws_instance", "web", attrs={"region": "us-east-1"})
        dst = _node("aws_instance", "api", attrs={"region": "eu-west-1"})
        path = NetworkPath(
            id="p1", source_node_id=src.id, dest_node_id=dst.id,
            direction="forward", hops=[], evidence={},
        )
        graph = ResourceGraph(nodes=[src, dst], edges=[], network_paths=[path])
        graph = EgressEstimator().estimate(graph)
        assert graph.network_paths[0].path_cost is not None
        assert graph.network_paths[0].path_cost.rate_per_gb == 0.02
        assert abs(graph.network_paths[0].path_cost.estimated_monthly_usd - 2.0) < 0.001

    def test_cross_cloud_rate(self):
        """CPC-C-2: Cross-cloud path (AWS → Azure) → CROSS_CLOUD_EGRESS rate."""
        src = _node("aws_ec2_transit_gateway", "tgw", attrs={"region": "us-east-1"})
        dst = _node("azurerm_express_route_circuit", "er", attrs={"location": "East US"}, provider="azurerm")
        path = NetworkPath(
            id="p2", source_node_id=src.id, dest_node_id=dst.id,
            direction="forward", hops=[], evidence={},
        )
        graph = ResourceGraph(nodes=[src, dst], edges=[], network_paths=[path])
        graph = EgressEstimator().estimate(graph)
        pc = graph.network_paths[0].path_cost
        assert pc is not None
        assert pc.rate_per_gb == 0.09
        assert "100 GB/mo" in pc.basis

    def test_no_region_data_graceful(self):
        """CPC-C-3: Path with no region data → path_cost is None."""
        src = _node("aws_instance", "web", attrs={})  # no region attribute
        dst = _node("aws_instance", "api", attrs={})
        path = NetworkPath(
            id="p3", source_node_id=src.id, dest_node_id=dst.id,
            direction="forward", hops=[], evidence={},
        )
        graph = ResourceGraph(nodes=[src, dst], edges=[], network_paths=[path])
        graph = EgressEstimator().estimate(graph)
        assert graph.network_paths[0].path_cost is None
