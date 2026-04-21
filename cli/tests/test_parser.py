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


class TestEnvsLayout:
    """Phase 5.1 tests: local module resolution, count expansion, parse-error surfacing.

    Fixture created by Plan 05.1-01: cli/tests/fixtures/envs_layout/
    """

    def test_51a_envs_layout_resolves_submodule(self):
        """5.1-A: envs_layout/prod resolves ../../modules/vpc submodule with module prefix."""
        from infracanvas.parser.module import resolve_modules

        root = FIXTURES / "envs_layout" / "envs" / "prod"
        parsed = parse_directory(root)
        resolve_modules(root, parsed)

        # aws_vpc.this and aws_subnet.public must be present with module = "module.vpc"
        vpcs = [r for r in parsed.resources if r.resource_type == "aws_vpc" and r.name == "this"]
        subnets = [
            r for r in parsed.resources
            if r.resource_type == "aws_subnet" and r.name == "public"
        ]
        assert len(vpcs) == 1, f"expected 1 aws_vpc.this from module.vpc, got {len(vpcs)}"
        assert vpcs[0].module == "module.vpc"
        assert len(subnets) >= 1, f"expected ≥1 aws_subnet.public, got {len(subnets)}"
        assert all(s.module == "module.vpc" for s in subnets)

    def test_51b_envs_layout_broken_submodule_surfaces_error(self):
        """5.1-B: broken submodule appears in parse_errors AND produces a placeholder."""
        from infracanvas.parser.module import resolve_modules

        root = FIXTURES / "envs_layout" / "envs" / "prod"
        parsed = parse_directory(root)
        resolve_modules(root, parsed)

        # D-01: parse_errors must contain at least one entry mentioning "broken"
        assert len(parsed.parse_errors) >= 1, "expected ≥1 parse_error from broken submodule"
        assert any("broken" in str(p) for p, _ in parsed.parse_errors), (
            f"no parse_error path mentions 'broken'; got: "
            f"{[str(p) for p, _ in parsed.parse_errors]}"
        )

        # D-01: a placeholder ParsedResource must be synthesized
        placeholders = [
            r for r in parsed.resources
            if r.resource_type == "_infracanvas_unresolved_module" and r.name == "broken"
        ]
        assert len(placeholders) == 1, (
            f"expected 1 _infracanvas_unresolved_module placeholder named 'broken', "
            f"got {len(placeholders)}"
        )
        # Placeholder must carry source + error evidence in attributes
        ph = placeholders[0]
        assert ph.attributes.get("source") == "../../modules/broken"
        assert "_parse_error" in ph.attributes

    def test_51c_count_literal_expands(self, tmp_path):
        """5.1-C: literal count = 3 expands into three ParsedResource objects with index 0/1/2."""
        tf = tmp_path / "main.tf"
        tf.write_text(
            'resource "aws_subnet" "x" {\n'
            '  count      = 3\n'
            '  cidr_block = "10.0.0.0/24"\n'
            '}\n'
        )
        parsed = parse_directory(tmp_path)

        xs = [r for r in parsed.resources if r.resource_type == "aws_subnet" and r.name == "x"]
        assert len(xs) == 3, f"expected 3 expansions of literal count=3, got {len(xs)}"
        indices = sorted(r.index for r in xs if r.index is not None)
        assert indices == [0, 1, 2], f"expected indices [0,1,2], got {indices}"
        assert all(not r.unresolved_count for r in xs)

    def test_51d_count_nonliteral_collapsed(self):
        """5.1-D: non-literal count (var.az_count) stays as single collapsed ParsedResource."""
        from infracanvas.parser.module import resolve_modules

        root = FIXTURES / "envs_layout" / "envs" / "prod"
        parsed = parse_directory(root)
        resolve_modules(root, parsed)

        subnets = [
            r for r in parsed.resources
            if r.resource_type == "aws_subnet" and r.name == "public"
        ]
        assert len(subnets) == 1, (
            f"expected 1 collapsed aws_subnet.public (count is var.az_count), got {len(subnets)}"
        )
        assert subnets[0].index is None
        assert subnets[0].unresolved_count is True

    def test_51p_count_cap_collapses_oversized_literal(self, tmp_path):
        """5.1-P: T-05.1-05 DoS guard — count = 10_000_000 collapses to 1 unresolved node."""
        from infracanvas.parser.hcl import COUNT_EXPANSION_CAP

        tf = tmp_path / "main.tf"
        # Use a literal well above the cap to prove the guard fires.
        tf.write_text(
            'resource "aws_subnet" "huge" {\n'
            '  count      = 10000000\n'
            '  cidr_block = "10.0.0.0/24"\n'
            '}\n'
        )
        parsed = parse_directory(tmp_path)

        huge = [
            r for r in parsed.resources
            if r.resource_type == "aws_subnet" and r.name == "huge"
        ]
        # Critical assertion: cap prevents OOM by collapsing to EXACTLY 1 instance.
        assert len(huge) == 1, (
            f"expected 1 collapsed node from oversized count, got {len(huge)} "
            f"(cap is {COUNT_EXPANSION_CAP})"
        )
        assert huge[0].index is None
        assert huge[0].unresolved_count is True

        # A synthetic parse_errors entry must reference the cap event.
        cap_notes = [
            (p, msg) for p, msg in parsed.parse_errors
            if "count-cap" in str(p) or "cap" in msg.lower()
        ]
        assert len(cap_notes) >= 1, (
            f"expected a synthetic parse_errors note about the cap; "
            f"got parse_errors={parsed.parse_errors}"
        )
