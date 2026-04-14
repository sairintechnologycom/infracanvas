"""Tests for the security rules engine."""

from pathlib import Path

from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import Severity
from infracanvas.parser.hcl import parse_directory
from infracanvas.security.engine import evaluate_all
from infracanvas.security.loader import load_rules

FIXTURES = Path(__file__).parent / "fixtures"


class TestRuleLoader:
    def test_loads_all_rules(self):
        rules = load_rules()
        assert len(rules) == 10

    def test_rule_ids(self):
        rules = load_rules()
        rule_ids = {r.id for r in rules}
        for i in range(1, 11):
            assert f"SEC-{i:03d}" in rule_ids

    def test_rule_severities(self):
        rules = load_rules()
        severity_map = {r.id: r.severity for r in rules}
        assert severity_map["SEC-001"] == Severity.critical
        assert severity_map["SEC-002"] == Severity.high
        assert severity_map["SEC-009"] == Severity.medium
        assert severity_map["SEC-010"] == Severity.info


class TestSecurityEngine:
    def test_insecure_setup_findings(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        all_findings = []
        for node in graph.nodes:
            all_findings.extend(node.findings)

        # Should have multiple findings
        assert len(all_findings) > 0

        rule_ids_found = {f.rule_id for f in all_findings}
        # SEC-001: S3 public ACL
        assert "SEC-001" in rule_ids_found
        # SEC-005: RDS publicly accessible
        assert "SEC-005" in rule_ids_found

    def test_s3_public_acl_detected(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        s3_bucket = next(n for n in graph.nodes if n.id == "aws_s3_bucket.public_data")
        sec001 = [f for f in s3_bucket.findings if f.rule_id == "SEC-001"]
        assert len(sec001) == 1
        assert sec001[0].severity == Severity.critical

    def test_rds_public_detected(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        db = next(n for n in graph.nodes if n.id == "aws_db_instance.exposed_db")
        sec005 = [f for f in db.findings if f.rule_id == "SEC-005"]
        assert len(sec005) == 1
        assert sec005[0].severity == Severity.critical

    def test_missing_tags_detected(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        # Untagged resources should trigger SEC-010
        untagged = next(n for n in graph.nodes if n.id == "aws_instance.untagged_server")
        sec010 = [f for f in untagged.findings if f.rule_id == "SEC-010"]
        assert len(sec010) == 1
        assert sec010[0].severity == Severity.info

    def test_secure_resources_no_critical(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        # simple_vpc has tagged resources and no wildly insecure config
        critical_findings = []
        for node in graph.nodes:
            for f in node.findings:
                if f.severity == Severity.critical:
                    critical_findings.append(f)

        # Should not have S3 public, RDS public, or IAM wildcard
        critical_rule_ids = {f.rule_id for f in critical_findings}
        assert "SEC-001" not in critical_rule_ids
        assert "SEC-005" not in critical_rule_ids
        assert "SEC-007" not in critical_rule_ids

    def test_iam_wildcard_detected(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        policy = next(n for n in graph.nodes if n.id == "aws_iam_policy.admin_policy")
        sec007 = [f for f in policy.findings if f.rule_id == "SEC-007"]
        assert len(sec007) == 1

    def test_kms_no_rotation_detected(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        kms = next(n for n in graph.nodes if n.id == "aws_kms_key.no_rotation")
        sec009 = [f for f in kms.findings if f.rule_id == "SEC-009"]
        assert len(sec009) == 1
        assert sec009[0].severity == Severity.medium

    def test_finding_has_evidence(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        graph = build_graph(parsed)
        graph = evaluate_all(graph)

        s3 = next(n for n in graph.nodes if n.id == "aws_s3_bucket.public_data")
        finding = next(f for f in s3.findings if f.rule_id == "SEC-001")
        assert "attribute" in finding.evidence
        assert finding.evidence["attribute"] == "acl"
