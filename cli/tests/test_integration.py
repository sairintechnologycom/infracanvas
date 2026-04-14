"""Integration tests (Suite D) — BLOCKER SUITE.

These tests validate the full CLI pipeline end-to-end.
If any test here fails, Phase 3 is blocked.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from infracanvas.export.json import export_graph
from infracanvas.graph.models import ResourceGraph

FIXTURES = Path(__file__).parent / "fixtures"
CLI_MODULE = "infracanvas.main"


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run infracanvas CLI as a subprocess."""
    cmd = [sys.executable, "-m", "typer", "infracanvas.main", "run", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=FIXTURES.parent.parent,  # cli/ directory
        check=check,
    )


def _run_scan_quiet(fixture: str) -> dict:
    """Run scan in quiet mode and return parsed JSON."""
    result = _run_cli("scan", str(FIXTURES / fixture), "--quiet", check=False)
    return json.loads(result.stdout)


class TestIntegration:
    """D-001 through D-005: End-to-end integration tests."""

    def test_d001_end_to_end_scan(self):
        """D-001: Full scan of simple_vpc outputs valid JSON with ≥4 nodes and ≥1 finding."""
        data = _run_scan_quiet("simple_vpc")

        # Validate against Pydantic model
        graph = ResourceGraph.model_validate(data)
        assert len(graph.nodes) >= 4
        assert graph.version == "1.0"
        assert graph.metadata["project"] == "simple_vpc"

        # At least one finding
        total_findings = sum(
            len(n.findings) for n in graph.nodes
        )
        assert total_findings >= 1

        # Validate summary
        assert graph.summary.total_resources == len(graph.nodes)
        assert graph.summary.score >= 0
        assert graph.summary.score <= 100

    def test_d002_severity_filter(self):
        """D-002: --severity critical flag filters output correctly."""
        data = _run_scan_quiet("simple_vpc")
        graph = ResourceGraph.model_validate(data)

        # With severity filter, only critical findings remain on nodes
        result = _run_cli(
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--severity", "critical",
            check=False,
        )
        filtered_data = json.loads(result.stdout)
        filtered_graph = ResourceGraph.model_validate(filtered_data)

        for node in filtered_graph.nodes:
            for f in node.findings:
                assert f.severity.value == "critical"

    def test_d003_json_output_file(self, tmp_path):
        """D-003: Scan outputs a JSON file to specified path."""
        output_path = tmp_path / "report.json"
        _run_cli(
            "scan", str(FIXTURES / "simple_vpc"),
            "--output", str(output_path),
            check=False,
        )
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        graph = ResourceGraph.model_validate(data)
        assert len(graph.nodes) > 0

    def test_d004_cli_exits_zero(self):
        """D-004: CLI exits 0 on clean scan."""
        result = _run_cli(
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet",
            check=False,
        )
        assert result.returncode == 0

    def test_d005_ci_flag_nonzero_on_criticals(self):
        """D-005: CLI exits non-zero with --ci flag when critical findings present."""
        result = _run_cli(
            "scan", str(FIXTURES / "simple_vpc"),
            "--ci", "--severity", "critical",
            check=False,
        )
        assert result.returncode != 0

        # Verify JSON output is valid even in CI mode
        data = json.loads(result.stdout)
        assert "nodes" in data
        assert "summary" in data

    def test_d005b_ci_flag_zero_when_clean(self):
        """CI mode exits 0 when no findings at threshold."""
        result = _run_cli(
            "scan", str(FIXTURES / "clean_infra"),
            "--ci", "--severity", "critical",
            check=False,
        )
        assert result.returncode == 0

    def test_invalid_directory(self, tmp_path):
        """CLI exits non-zero for non-existent directory."""
        result = _run_cli(
            "scan", str(tmp_path / "nonexistent"),
            check=False,
        )
        assert result.returncode != 0

    def test_score_command(self):
        """Score command outputs valid data."""
        result = _run_cli(
            "score", str(FIXTURES / "simple_vpc"),
            "--format", "json",
            check=False,
        )
        data = json.loads(result.stdout)
        assert "score" in data
        assert 0 <= data["score"] <= 100

    def test_schema_fields_complete(self):
        """Verify all required schema fields are present in output."""
        data = _run_scan_quiet("simple_vpc")

        # Top-level fields
        assert "version" in data
        assert "metadata" in data
        assert "nodes" in data
        assert "edges" in data
        assert "summary" in data

        # Metadata fields
        meta = data["metadata"]
        assert "scan_id" in meta
        assert "project" in meta
        assert "provider" in meta
        assert "scanned_at" in meta

        # Node fields
        node = data["nodes"][0]
        for field in ["id", "type", "name", "provider", "module", "region",
                       "group", "attributes", "dependencies", "findings",
                       "cost", "drift", "position"]:
            assert field in node, f"Missing field: {field}"

        # Summary fields
        summary = data["summary"]
        for field in ["total_resources", "findings", "estimated_monthly_cost",
                       "score", "drift"]:
            assert field in summary, f"Missing summary field: {field}"

        # Finding severity buckets
        for sev in ["critical", "high", "medium", "info"]:
            assert sev in summary["findings"]

        # Drift buckets
        for status in ["added", "changed", "deleted"]:
            assert status in summary["drift"]
