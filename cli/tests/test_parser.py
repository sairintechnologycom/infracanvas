"""Tests for the HCL parser and reference detection (Suite A)."""

from pathlib import Path

import pytest

from infracanvas.parser.hcl import parse_directory
from infracanvas.parser.references import find_references
from infracanvas.parser.state import parse_state_file

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseDirectory:
    """A-001 through A-010: Parser unit tests."""

    def test_a001_parse_single_resource_block(self):
        """A-001: Parse single resource block — verify type, name, attributes."""
        parsed = parse_directory(FIXTURES / "single_resource")
        assert len(parsed.resources) == 1
        res = parsed.resources[0]
        assert res.resource_type == "aws_vpc"
        assert res.name == "only"
        assert res.attributes["cidr_block"] == "10.0.0.0/16"

    def test_a002_parse_multiple_resource_types(self):
        """A-002: Parse multiple resource types in one directory."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        resource_types = {r.resource_type for r in parsed.resources}
        assert "aws_vpc" in resource_types
        assert "aws_subnet" in resource_types
        assert "aws_security_group" in resource_types
        assert "aws_instance" in resource_types
        assert "aws_s3_bucket" in resource_types
        assert len(parsed.resources) == 6

    def test_a003_detect_implicit_dependency(self):
        """A-003: Detect implicit dependency from resource reference."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        subnet_deps = parsed.implicit_deps.get("aws_subnet.public", set())
        assert "aws_vpc.main" in subnet_deps

    def test_a004_detect_explicit_depends_on(self):
        """A-004: Detect explicit depends_on declaration."""
        parsed = parse_directory(FIXTURES / "multi_module")
        instance = next(
            r for r in parsed.resources
            if r.name == "app" and r.resource_type == "aws_instance"
        )
        assert "aws_vpc.prod" in instance.depends_on

    def test_a005_handle_empty_tf_file(self, tmp_path):
        """A-005: Handle empty .tf file without crashing."""
        (tmp_path / "empty.tf").write_text("")
        parsed = parse_directory(tmp_path)
        assert len(parsed.resources) == 0

    def test_a006_handle_no_tf_files(self, tmp_path):
        """A-006: Handle directory with no .tf files — returns empty result."""
        parsed = parse_directory(tmp_path)
        assert len(parsed.resources) == 0

    def test_a007_handle_malformed_hcl(self):
        """A-007: Handle malformed HCL — parser skips bad files gracefully."""
        parsed = parse_directory(FIXTURES / "malformed")
        # The malformed file should be skipped, not crash
        assert len(parsed.resources) == 0

    def test_a008_parse_tfstate_file(self):
        """A-008: Parse .tfstate file — verify resource count and attributes."""
        state = parse_state_file(FIXTURES / "simple_vpc" / "terraform.tfstate")
        assert state.terraform_version == "1.7.0"
        # Only managed resources (not data sources)
        assert len(state.resources) == 3
        vpc = next(r for r in state.resources if r.resource_type == "aws_vpc")
        assert vpc.attributes["cidr_block"] == "10.0.0.0/16"

    def test_a009_state_resource_addresses(self):
        """A-009: State reader maps resources to correct type.name format."""
        state = parse_state_file(FIXTURES / "simple_vpc" / "terraform.tfstate")
        addresses = {r.address for r in state.resources}
        assert "aws_vpc.main" in addresses
        assert "aws_subnet.public" in addresses
        assert "aws_s3_bucket.data" in addresses

    def test_a010_parse_variable_blocks(self):
        """A-010: Parse variable blocks without crashing."""
        parsed = parse_directory(FIXTURES / "multi_module")
        assert len(parsed.variables) == 1
        assert parsed.variables[0].name == "environment"

    def test_simple_vpc_attributes(self):
        parsed = parse_directory(FIXTURES / "simple_vpc")
        vpc = next(r for r in parsed.resources if r.name == "main")
        assert vpc.attributes["cidr_block"] == "10.0.0.0/16"

    def test_multi_module_parses_multiple_files(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        resource_ids = {f"{r.resource_type}.{r.name}" for r in parsed.resources}
        assert "aws_vpc.prod" in resource_ids
        assert "aws_lambda_function.processor" in resource_ids
        assert len(parsed.resources) == 6

    def test_multi_module_outputs(self):
        parsed = parse_directory(FIXTURES / "multi_module")
        assert len(parsed.outputs) == 1
        assert parsed.outputs[0].name == "vpc_id"

    def test_insecure_setup_resources(self):
        parsed = parse_directory(FIXTURES / "insecure_setup")
        resource_ids = {f"{r.resource_type}.{r.name}" for r in parsed.resources}
        assert "aws_s3_bucket.public_data" in resource_ids
        assert "aws_db_instance.exposed_db" in resource_ids
        assert len(parsed.resources) == 7

    def test_large_fixture_parses_50_resources(self):
        """Verify large fixture has 50 resources."""
        parsed = parse_directory(FIXTURES / "large")
        assert len(parsed.resources) == 50

    def test_state_provider_extraction(self):
        """State reader extracts provider name from full path."""
        state = parse_state_file(FIXTURES / "simple_vpc" / "terraform.tfstate")
        for r in state.resources:
            assert r.provider == "aws"


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

    def test_nested_references(self):
        known = {"aws_vpc.main", "aws_subnet.public"}
        refs = find_references(
            {"config": {"subnet_id": "aws_subnet.public.id"}},
            known,
        )
        assert "aws_subnet.public" in refs
