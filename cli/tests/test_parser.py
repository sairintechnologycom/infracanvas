"""Tests for the HCL parser and reference detection."""

from pathlib import Path

import pytest

from infracanvas.parser.hcl import parse_directory
from infracanvas.parser.references import find_references

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseDirectory:
    def test_simple_vpc_resources(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        resource_ids = {f"{r.resource_type}.{r.name}" for r in parsed.resources}

        assert "aws_vpc.main" in resource_ids
        assert "aws_subnet.public" in resource_ids
        assert "aws_subnet.private" in resource_ids
        assert "aws_security_group.web" in resource_ids
        assert "aws_instance.web" in resource_ids
        assert len(parsed.resources) == 5

    def test_simple_vpc_attributes(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        vpc = next(r for r in parsed.resources if r.name == "main")
        assert vpc.attributes["cidr_block"] == "10.0.0.0/16"

    def test_multi_module_parses_multiple_files(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        resource_ids = {f"{r.resource_type}.{r.name}" for r in parsed.resources}

        assert "aws_vpc.prod" in resource_ids
        assert "aws_subnet.app" in resource_ids
        assert "aws_instance.app" in resource_ids
        assert "aws_lambda_function.processor" in resource_ids
        assert "aws_iam_role.lambda_role" in resource_ids
        assert "aws_dynamodb_table.events" in resource_ids
        assert len(parsed.resources) == 6

    def test_multi_module_variables_and_outputs(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        assert len(parsed.variables) == 1
        assert parsed.variables[0].name == "environment"
        assert len(parsed.outputs) == 1
        assert parsed.outputs[0].name == "vpc_id"

    def test_insecure_setup_resources(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        resource_ids = {f"{r.resource_type}.{r.name}" for r in parsed.resources}

        assert "aws_s3_bucket.public_data" in resource_ids
        assert "aws_db_instance.exposed_db" in resource_ids
        assert "aws_iam_policy.admin_policy" in resource_ids
        assert len(parsed.resources) == 7

    def test_empty_directory(self, tmp_path):
        parsed = parse_directory(tmp_path)
        assert len(parsed.resources) == 0

    def test_implicit_dependencies_detected(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")

        # aws_subnet.public references aws_vpc.main via vpc_id = aws_vpc.main.id
        subnet_deps = parsed.implicit_deps.get("aws_subnet.public", set())
        assert "aws_vpc.main" in subnet_deps

    def test_explicit_depends_on(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        instance = next(r for r in parsed.resources if r.name == "app" and r.resource_type == "aws_instance")
        assert "aws_vpc.prod" in instance.depends_on


class TestFindReferences:
    def test_string_reference(self):
        known = {"aws_vpc.main", "aws_subnet.public"}
        refs = find_references("aws_vpc.main.id", known)
        assert "aws_vpc.main" in refs

    def test_dict_reference(self):
        known = {"aws_vpc.main"}
        refs = find_references({"vpc_id": "aws_vpc.main.id"}, known)
        assert "aws_vpc.main" in refs

    def test_list_reference(self):
        known = {"aws_security_group.web"}
        refs = find_references(["aws_security_group.web.id"], known)
        assert "aws_security_group.web" in refs

    def test_no_false_positives(self):
        known = {"aws_vpc.main"}
        refs = find_references("some random string", known)
        assert len(refs) == 0
