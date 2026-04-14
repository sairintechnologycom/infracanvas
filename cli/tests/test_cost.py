"""Tests for the cost estimator (T-017)."""

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
