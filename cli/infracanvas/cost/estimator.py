"""Static cost estimator for AWS resources (us-east-1 on-demand pricing)."""

from __future__ import annotations

from typing import Any

from infracanvas.graph.models import CostEstimate, ResourceGraph
from infracanvas.parser.plan import PlanChange

HOURS_PER_MONTH = 730

# CST-03: Region price multipliers relative to us-east-1
REGION_MULTIPLIERS: dict[str, float] = {
    "us-east-1": 1.0, "us-east-2": 1.0, "us-west-1": 1.1, "us-west-2": 1.0,
    "eu-west-1": 1.1, "eu-west-2": 1.12, "eu-central-1": 1.12,
    "ap-southeast-1": 1.15, "ap-northeast-1": 1.12, "ap-south-1": 1.0,
    "East US": 1.0, "West US": 1.05, "West Europe": 1.1,
    "North Europe": 1.1, "Southeast Asia": 1.15,
}

# EC2 on-demand hourly rates (us-east-1)
EC2_PRICES: dict[str, float] = {
    "t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416,
    "t3.large": 0.0832, "t3.xlarge": 0.1664, "t3.2xlarge": 0.3328,
    "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384,
    "m5.4xlarge": 0.768, "c5.large": 0.085, "c5.xlarge": 0.17,
    "r5.large": 0.126, "r5.xlarge": 0.252,
}
EC2_DEFAULT_HOURLY = 0.10

# RDS on-demand hourly rates (us-east-1, single-AZ)
RDS_PRICES: dict[str, float] = {
    "db.t3.micro": 0.017, "db.t3.small": 0.034, "db.t3.medium": 0.068,
    "db.t3.large": 0.136, "db.r5.large": 0.24, "db.r5.xlarge": 0.48,
}

# Flat monthly rates
FLAT_MONTHLY: dict[str, float] = {
    "aws_nat_gateway": 0.045 * HOURS_PER_MONTH,   # $32.85
    "aws_alb": 0.0225 * HOURS_PER_MONTH,           # $16.43
    "aws_lb": 0.0225 * HOURS_PER_MONTH,             # $16.43
    "aws_eks_cluster": 0.10 * HOURS_PER_MONTH,      # $73.00
    "aws_kms_key": 1.00,                             # $1.00
    # Phase 9: CostLens shared resources
    "aws_ec2_transit_gateway": 0.05 * HOURS_PER_MONTH,    # $36.50/mo TGW hourly charge
    "aws_vpc_endpoint": 0.01 * HOURS_PER_MONTH,           # $7.30/mo Interface endpoint/hr
    "azurerm_express_route_circuit": 55.00,                # $55.00/mo flat (Standard, 50Mbps)
    "azurerm_firewall": 1.25 * HOURS_PER_MONTH,           # $912.50/mo Premium tier
}

# Usage-based resources — $0 at provisioning time
ZERO_COST_TYPES: set[str] = {
    "aws_s3_bucket", "aws_sqs_queue", "aws_sns_topic",
    "aws_lambda_function", "aws_cloudfront_distribution",
    "aws_dynamodb_table", "aws_ecs_service",
}

# Non-billable infrastructure resources
NON_BILLABLE: set[str] = {
    "aws_vpc", "aws_subnet", "aws_security_group", "aws_route_table",
    "aws_internet_gateway", "aws_route", "aws_iam_role", "aws_iam_policy",
    "aws_iam_role_policy_attachment", "aws_iam_instance_profile",
}


def _estimate_ec2(attrs: dict[str, Any]) -> CostEstimate:
    instance_type = str(attrs.get("instance_type", ""))
    hourly = EC2_PRICES.get(instance_type, EC2_DEFAULT_HOURLY)
    monthly = hourly * HOURS_PER_MONTH
    return CostEstimate(
        monthly_usd=round(monthly, 2),
        basis=f"{instance_type} @ ${hourly}/hr",
    )


def _estimate_rds(attrs: dict[str, Any]) -> CostEstimate:
    instance_class = str(attrs.get("instance_class", ""))
    hourly = RDS_PRICES.get(instance_class, 0.068)  # default to db.t3.medium
    multi_az = attrs.get("multi_az", False)
    if multi_az is True or str(multi_az).lower() == "true":
        hourly *= 2
    monthly = hourly * HOURS_PER_MONTH
    basis = f"{instance_class} @ ${hourly}/hr"
    if multi_az:
        basis += " (multi-AZ)"
    return CostEstimate(monthly_usd=round(monthly, 2), basis=basis)


def _estimate_lambda(attrs: dict[str, Any]) -> CostEstimate:
    reserved = attrs.get("reserved_concurrent_executions", 0)
    if reserved and int(reserved) > 0:
        monthly = int(reserved) * 0.0000041667 * HOURS_PER_MONTH * 3600
        return CostEstimate(monthly_usd=round(monthly, 2), basis=f"reserved: {reserved}")
    return CostEstimate(monthly_usd=0.0, basis="usage-based")


def _estimate_resource(resource_type: str, attrs: dict[str, Any]) -> CostEstimate:
    """Estimate monthly cost for a single resource."""
    if resource_type in ("aws_instance",):
        return _estimate_ec2(attrs)
    if resource_type in ("aws_db_instance", "aws_rds_instance"):
        return _estimate_rds(attrs)
    if resource_type == "aws_lambda_function":
        return _estimate_lambda(attrs)
    if resource_type in FLAT_MONTHLY:
        monthly = FLAT_MONTHLY[resource_type]
        return CostEstimate(monthly_usd=round(monthly, 2), basis="flat rate")
    if resource_type in ZERO_COST_TYPES:
        return CostEstimate(monthly_usd=0.0, basis="usage-based")
    if resource_type in NON_BILLABLE:
        return CostEstimate(monthly_usd=0.0, basis="no charge")
    return CostEstimate(monthly_usd=0.0, basis="unknown")


class CostEstimator:
    """Annotate resource nodes with cost estimates."""

    def estimate(self, graph: ResourceGraph) -> ResourceGraph:
        """Annotate each node.cost with region-aware pricing and update summary."""
        total = 0.0
        group_costs: dict[str, float] = {}
        for node in graph.nodes:
            base = _estimate_resource(node.type, node.attributes)
            # CST-03: apply region multiplier
            multiplier = REGION_MULTIPLIERS.get(node.region, 1.0) if node.region else 1.0
            adjusted = round(base.monthly_usd * multiplier, 2)
            basis = base.basis
            if node.region and multiplier != 1.0:
                basis += f" ({node.region} x{multiplier})"
            node.cost = CostEstimate(
                monthly_usd=adjusted,
                currency=base.currency,
                basis=basis,
            )
            total += node.cost.monthly_usd
            # CST-02: group-level aggregation
            if node.group:
                group_costs[node.group] = group_costs.get(node.group, 0.0) + node.cost.monthly_usd
        graph.summary.estimated_monthly_cost = round(total, 2)
        # Store group costs in metadata for viewer consumption
        graph.metadata["group_costs"] = {k: round(v, 2) for k, v in group_costs.items()}
        return graph

    def delta(self, graph: ResourceGraph, changes: list[PlanChange]) -> float:
        """Calculate cost delta from plan changes."""
        total_delta = 0.0
        for change in changes:
            if change.action.value == "added":
                cost = _estimate_resource(change.resource_type, change.after)
                total_delta += cost.monthly_usd
            elif change.action.value == "deleted":
                cost = _estimate_resource(change.resource_type, change.before)
                total_delta -= cost.monthly_usd
            elif change.action.value == "changed":
                before_cost = _estimate_resource(change.resource_type, change.before)
                after_cost = _estimate_resource(change.resource_type, change.after)
                total_delta += after_cost.monthly_usd - before_cost.monthly_usd
        return round(total_delta, 2)
