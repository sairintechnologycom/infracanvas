"""Tests for the cost estimator (T-017)."""

import pytest

from infracanvas.cost.estimator import CostEstimator, HOURS_PER_MONTH, _estimate_resource
from infracanvas.graph.models import (
    DriftStatus,
    GraphSummary,
    ResourceGraph,
    ResourceNode,
)
from infracanvas.parser.plan import PlanChange


def _node(resource_type: str, name: str, attrs: dict) -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes=attrs,
    )


class TestCostEstimator:
    def test_ec2_t3_medium_price(self):
        cost = _estimate_resource("aws_instance", {"instance_type": "t3.medium"})
        expected = round(0.0416 * HOURS_PER_MONTH, 2)
        assert cost.monthly_usd == expected  # $30.37

    def test_ec2_unknown_type_default(self):
        cost = _estimate_resource("aws_instance", {"instance_type": "z9.mega"})
        expected = round(0.10 * HOURS_PER_MONTH, 2)
        assert cost.monthly_usd == expected

    def test_rds_multi_az_doubles(self):
        single = _estimate_resource("aws_db_instance", {"instance_class": "db.t3.micro"})
        multi = _estimate_resource(
            "aws_db_instance", {"instance_class": "db.t3.micro", "multi_az": True}
        )
        assert multi.monthly_usd == round(single.monthly_usd * 2, 2)

    def test_nat_gateway_flat(self):
        cost = _estimate_resource("aws_nat_gateway", {})
        expected = round(0.045 * HOURS_PER_MONTH, 2)
        assert cost.monthly_usd == expected  # $32.85

    def test_lambda_zero_no_concurrency(self):
        cost = _estimate_resource("aws_lambda_function", {})
        assert cost.monthly_usd == 0.0

    def test_estimator_total_sum(self):
        nodes = [
            _node("aws_instance", "a", {"instance_type": "t3.medium"}),
            _node("aws_nat_gateway", "b", {}),
        ]
        graph = ResourceGraph(nodes=nodes, summary=GraphSummary(total_resources=2))
        estimator = CostEstimator()
        result = estimator.estimate(graph)
        ec2_cost = round(0.0416 * HOURS_PER_MONTH, 2)
        nat_cost = round(0.045 * HOURS_PER_MONTH, 2)
        assert result.summary.estimated_monthly_cost == round(ec2_cost + nat_cost, 2)

    def test_delta_added_resource(self):
        graph = ResourceGraph(nodes=[], summary=GraphSummary())
        changes = [
            PlanChange(
                resource_address="aws_nat_gateway.main",
                resource_type="aws_nat_gateway",
                resource_name="main",
                action=DriftStatus.added,
                after={},
            )
        ]
        estimator = CostEstimator()
        delta = estimator.delta(graph, changes)
        assert delta == round(0.045 * HOURS_PER_MONTH, 2)

    def test_delta_deleted_resource(self):
        graph = ResourceGraph(nodes=[], summary=GraphSummary())
        changes = [
            PlanChange(
                resource_address="aws_nat_gateway.old",
                resource_type="aws_nat_gateway",
                resource_name="old",
                action=DriftStatus.deleted,
                before={},
            )
        ]
        estimator = CostEstimator()
        delta = estimator.delta(graph, changes)
        assert delta == round(-0.045 * HOURS_PER_MONTH, 2)


class TestRegionMultiplier:
    def test_us_east_1_no_change(self):
        """CST-03-A: us-east-1 has multiplier 1.0."""
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", region="us-east-1",
            attributes={"instance_type": "t3.medium"},
        )
        graph = ResourceGraph(nodes=[node])
        estimator = CostEstimator()
        estimator.estimate(graph)
        # t3.medium = $0.0416/hr * 730 = $30.37
        assert node.cost.monthly_usd == pytest.approx(30.37, abs=0.1)

    def test_eu_west_1_higher(self):
        """CST-03-B: eu-west-1 has 1.1x multiplier."""
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", region="eu-west-1",
            attributes={"instance_type": "t3.medium"},
        )
        graph = ResourceGraph(nodes=[node])
        estimator = CostEstimator()
        estimator.estimate(graph)
        base = 0.0416 * 730
        expected = round(base * 1.1, 2)
        assert node.cost.monthly_usd == pytest.approx(expected, abs=0.1)

    def test_unknown_region_defaults_to_1(self):
        """CST-03-C: Unknown region uses multiplier 1.0."""
        node = ResourceNode(
            id="aws_instance.web", type="aws_instance", name="web",
            provider="aws", region="unknown-region",
            attributes={"instance_type": "t3.medium"},
        )
        graph = ResourceGraph(nodes=[node])
        estimator = CostEstimator()
        estimator.estimate(graph)
        assert node.cost.monthly_usd == pytest.approx(30.37, abs=0.1)


class TestGroupCostAggregation:
    def test_group_costs_in_metadata(self):
        """CST-02-A: Group costs aggregated in graph.metadata."""
        nodes = [
            ResourceNode(
                id="aws_instance.web", type="aws_instance", name="web",
                provider="aws", group="vpc-main",
                attributes={"instance_type": "t3.medium"},
            ),
            ResourceNode(
                id="aws_instance.api", type="aws_instance", name="api",
                provider="aws", group="vpc-main",
                attributes={"instance_type": "t3.medium"},
            ),
        ]
        graph = ResourceGraph(nodes=nodes)
        estimator = CostEstimator()
        estimator.estimate(graph)
        assert "group_costs" in graph.metadata
        assert "vpc-main" in graph.metadata["group_costs"]
        assert graph.metadata["group_costs"]["vpc-main"] > 0
