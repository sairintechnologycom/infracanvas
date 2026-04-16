"""Shadow infrastructure detector — compare live AWS API vs Terraform graph."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from infracanvas.graph.models import (
    CostEstimate,
    DriftStatus,
    ResourceGraph,
    ResourceNode,
)

if TYPE_CHECKING:
    pass  # boto3 types would go here with boto3-stubs

# Resource types supported for shadow detection (read-only IAM surface)
SUPPORTED_TYPES: dict[str, str] = {
    "aws_instance": "ec2",
    "aws_security_group": "ec2",
    "aws_vpc": "ec2",
    "aws_subnet": "ec2",
    "aws_s3_bucket": "s3",
    "aws_db_instance": "rds",
}

# Rough monthly cost estimates for shadow resource cost display
SHADOW_COST_ESTIMATES: dict[str, float] = {
    "aws_instance": 73.0,        # t3.medium default
    "aws_security_group": 0.0,
    "aws_vpc": 0.0,
    "aws_subnet": 0.0,
    "aws_s3_bucket": 5.0,        # nominal storage
    "aws_db_instance": 49.64,    # db.t3.medium
}


class ShadowDetector:
    """Compare live AWS API vs Terraform graph nodes; flag unmanaged resources."""

    def __init__(self, region: str) -> None:
        self._region = region

    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        """Flag shadow resources. Raises RuntimeError on missing boto3/creds."""
        try:
            import boto3  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                "boto3 not installed. Install with: pip install 'infracanvas[shadow]'"
            )

        session = boto3.Session()
        creds = session.get_credentials()
        if not creds:
            raise RuntimeError(
                "--shadow requires AWS credentials. Skipping shadow scan."
            )

        # Build set of known Terraform resource IDs per type
        known: dict[str, set[str]] = {}
        for node in graph.nodes:
            if node.type in SUPPORTED_TYPES:
                known.setdefault(node.type, set()).add(node.name)

        # Query each supported AWS service
        ec2 = session.client("ec2", region_name=self._region)
        self._detect_ec2_instances(graph, ec2, known.get("aws_instance", set()))
        self._detect_security_groups(graph, ec2, known.get("aws_security_group", set()))
        self._detect_vpcs(graph, ec2, known.get("aws_vpc", set()))
        self._detect_subnets(graph, ec2, known.get("aws_subnet", set()))

        s3 = session.client("s3")
        self._detect_s3_buckets(graph, s3, known.get("aws_s3_bucket", set()))

        rds = session.client("rds", region_name=self._region)
        self._detect_rds_instances(graph, rds, known.get("aws_db_instance", set()))

        return graph

    def _add_shadow_node(
        self,
        graph: ResourceGraph,
        resource_type: str,
        name: str,
        attrs: dict[str, Any],
    ) -> None:
        """Add a shadow node to the graph."""
        cost = SHADOW_COST_ESTIMATES.get(resource_type, 0.0)
        node = ResourceNode(
            id=f"{resource_type}.shadow_{name}",
            type=resource_type,
            name=f"shadow_{name}",
            provider="aws",
            region=self._region,
            attributes=attrs,
            drift=DriftStatus.shadow,
            cost=CostEstimate(
                monthly_usd=cost,
                basis="shadow estimate",
            ),
        )
        graph.nodes.append(node)

    def _detect_ec2_instances(
        self,
        graph: ResourceGraph,
        ec2: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    name_tag = ""
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            name_tag = tag["Value"]
                            break
                    # Match by Name tag or instance ID
                    if name_tag not in known_names and instance_id not in known_names:
                        self._add_shadow_node(
                            graph,
                            "aws_instance",
                            instance_id,
                            {
                                "instance_type": instance.get("InstanceType", ""),
                                "instance_id": instance_id,
                                "name_tag": name_tag,
                            },
                        )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error

    def _detect_security_groups(
        self,
        graph: ResourceGraph,
        ec2: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = ec2.describe_security_groups()
            for sg in response.get("SecurityGroups", []):
                sg_name = sg.get("GroupName", "")
                if sg_name not in known_names and sg_name != "default":
                    self._add_shadow_node(
                        graph,
                        "aws_security_group",
                        sg["GroupId"],
                        {"group_name": sg_name, "vpc_id": sg.get("VpcId", "")},
                    )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error

    def _detect_vpcs(
        self,
        graph: ResourceGraph,
        ec2: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = ec2.describe_vpcs()
            for vpc in response.get("Vpcs", []):
                vpc_id = vpc["VpcId"]
                name_tag = ""
                for tag in vpc.get("Tags", []):
                    if tag["Key"] == "Name":
                        name_tag = tag["Value"]
                        break
                if name_tag not in known_names and vpc_id not in known_names:
                    if not vpc.get("IsDefault", False):
                        self._add_shadow_node(
                            graph,
                            "aws_vpc",
                            vpc_id,
                            {"cidr_block": vpc.get("CidrBlock", "")},
                        )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error

    def _detect_subnets(
        self,
        graph: ResourceGraph,
        ec2: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = ec2.describe_subnets()
            for subnet in response.get("Subnets", []):
                subnet_id = subnet["SubnetId"]
                name_tag = ""
                for tag in subnet.get("Tags", []):
                    if tag["Key"] == "Name":
                        name_tag = tag["Value"]
                        break
                if name_tag not in known_names and subnet_id not in known_names:
                    self._add_shadow_node(
                        graph,
                        "aws_subnet",
                        subnet_id,
                        {
                            "cidr_block": subnet.get("CidrBlock", ""),
                            "vpc_id": subnet.get("VpcId", ""),
                        },
                    )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error

    def _detect_s3_buckets(
        self,
        graph: ResourceGraph,
        s3: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = s3.list_buckets()
            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]
                if bucket_name not in known_names:
                    self._add_shadow_node(
                        graph,
                        "aws_s3_bucket",
                        bucket_name,
                        {"bucket": bucket_name},
                    )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error

    def _detect_rds_instances(
        self,
        graph: ResourceGraph,
        rds: Any,
        known_names: set[str],
    ) -> None:
        try:
            response = rds.describe_db_instances()
            for db in response.get("DBInstances", []):
                db_id = db["DBInstanceIdentifier"]
                if db_id not in known_names:
                    self._add_shadow_node(
                        graph,
                        "aws_db_instance",
                        db_id,
                        {
                            "instance_class": db.get("DBInstanceClass", ""),
                            "engine": db.get("Engine", ""),
                        },
                    )
        except Exception:  # noqa: BLE001 — boto3 raises varied exceptions per service
            pass  # Non-fatal: skip this resource type on API error
