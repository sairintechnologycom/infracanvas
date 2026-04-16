"""Tests for shadow infrastructure detector (SHD-01, SHD-02)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode


def _node(resource_type: str, name: str = "test") -> ResourceNode:
    return ResourceNode(
        id=f"{resource_type}.{name}",
        type=resource_type,
        name=name,
        provider="aws",
        attributes={},
    )


class TestShadowDetectorImport:
    def test_missing_boto3_raises_runtime_error(self):
        """SHD-001-A: RuntimeError when boto3 not installed."""
        from infracanvas.shadow.detector import ShadowDetector
        with patch.dict("sys.modules", {"boto3": None}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[_node("aws_instance", "web")])
            with pytest.raises(RuntimeError, match="boto3 not installed"):
                detector.detect(graph)

    def test_no_credentials_raises_runtime_error(self):
        """SHD-001-B: RuntimeError when no AWS credentials."""
        from infracanvas.shadow.detector import ShadowDetector
        mock_boto3 = MagicMock()
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        mock_boto3.Session.return_value = mock_session
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[])
            with pytest.raises(RuntimeError, match="AWS credentials"):
                detector.detect(graph)


class TestShadowDetection:
    def _mock_boto3_session(self):
        """Create a mock boto3 session with empty API responses."""
        mock_boto3 = MagicMock()
        mock_session = MagicMock()
        mock_creds = MagicMock()
        mock_session.get_credentials.return_value = mock_creds
        mock_boto3.Session.return_value = mock_session

        # EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {"Reservations": []}
        mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
        mock_ec2.describe_subnets.return_value = {"Subnets": []}

        # S3 client
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}

        # RDS client
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}

        mock_session.client.side_effect = lambda svc, **kw: {
            "ec2": mock_ec2, "s3": mock_s3, "rds": mock_rds,
        }.get(svc, MagicMock())

        return mock_boto3, mock_ec2, mock_s3, mock_rds

    def test_no_shadow_when_all_managed(self):
        """SHD-001-C: No shadow nodes when API returns only managed resources."""
        from infracanvas.shadow.detector import ShadowDetector
        mock_boto3, mock_ec2, _, _ = self._mock_boto3_session()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-abc123",
                    "InstanceType": "t3.micro",
                    "Tags": [{"Key": "Name", "Value": "web"}],
                }]
            }]
        }
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[_node("aws_instance", "web")])
            result = detector.detect(graph)
            shadow_nodes = [n for n in result.nodes if n.drift == DriftStatus.shadow]
            assert len(shadow_nodes) == 0

    def test_shadow_ec2_flagged(self):
        """SHD-001-D: Unmanaged EC2 instance flagged as shadow."""
        from infracanvas.shadow.detector import ShadowDetector
        mock_boto3, mock_ec2, _, _ = self._mock_boto3_session()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-xyz789",
                    "InstanceType": "t3.large",
                    "Tags": [{"Key": "Name", "Value": "rogue-server"}],
                }]
            }]
        }
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[_node("aws_instance", "web")])
            result = detector.detect(graph)
            shadow_nodes = [n for n in result.nodes if n.drift == DriftStatus.shadow]
            assert len(shadow_nodes) == 1
            assert shadow_nodes[0].cost.monthly_usd > 0

    def test_shadow_s3_flagged(self):
        """SHD-001-E: Unmanaged S3 bucket flagged as shadow."""
        from infracanvas.shadow.detector import ShadowDetector
        mock_boto3, _, mock_s3, _ = self._mock_boto3_session()
        mock_s3.list_buckets.return_value = {
            "Buckets": [{"Name": "rogue-bucket"}]
        }
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            detector = ShadowDetector(region="us-east-1")
            graph = ResourceGraph(nodes=[])
            result = detector.detect(graph)
            shadow_nodes = [n for n in result.nodes if n.drift == DriftStatus.shadow]
            assert len(shadow_nodes) == 1
            assert shadow_nodes[0].type == "aws_s3_bucket"
