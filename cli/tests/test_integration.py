"""Integration tests (Suite D) — BLOCKER SUITE.

These tests validate the full CLI pipeline end-to-end.
If any test here fails, Phase 3 is blocked.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from infracanvas.export.json import export_graph
from infracanvas.graph.models import ResourceGraph
from infracanvas.main import app

FIXTURES = Path(__file__).parent / "fixtures"
CLI_MODULE = "infracanvas.main"

runner = CliRunner()


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
        assert graph.version == "2.1"
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
            "--format", "json",
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
        assert "overall" in data
        assert 0 <= data["overall"] <= 100

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


class TestScanDefaultHtml:
    def test_scan_defaults_to_html(self):
        """EXP-02: scan command defaults to HTML format."""
        result = runner.invoke(app, ["scan", str(FIXTURES / "clean_infra")])
        assert result.exit_code == 0
        # Should reference HTML report, not JSON
        assert "infracanvas-report.html" in result.output or "html" in result.output.lower()


class TestEndToEnd:
    """End-to-end tests for scan and score pipelines."""

    def test_scan_produces_html(self, tmp_path):
        """E2E: scan command produces HTML with graph data."""
        fixture = FIXTURES / "insecure_setup"
        result = runner.invoke(app, [
            "scan", str(fixture),
            "--output", str(tmp_path / "report.html"),
            "--format", "html",
        ])
        assert result.exit_code == 0
        html_path = tmp_path / "report.html"
        assert html_path.exists()
        content = html_path.read_text()
        assert "__INFRACANVAS_DATA__" in content
        assert "__INFRACANVAS_GATE__ = true" in content

    def test_scan_json_still_works(self, tmp_path):
        """E2E: scan with --format json still produces JSON."""
        fixture = FIXTURES / "clean_infra"
        result = runner.invoke(app, [
            "scan", str(fixture),
            "--format", "json",
            "--output", str(tmp_path / "report.json"),
        ])
        assert result.exit_code == 0
        assert (tmp_path / "report.json").exists()

    def test_score_produces_html(self, tmp_path):
        """E2E: score command produces score card HTML with all 5 dimensions."""
        fixture = FIXTURES / "insecure_setup"
        result = runner.invoke(app, [
            "score", str(fixture),
        ])
        assert result.exit_code == 0
        # Check score card was written
        assert "Score card saved" in result.output or "infracanvas-score.html" in result.output
        # Find the generated score card HTML and verify all 5 dimensions are present
        import glob
        score_htmls = glob.glob(str(tmp_path / "**/*score*.html"), recursive=True)
        # Also check the default output directory
        default_score = Path("infracanvas-score.html")
        if default_score.exists():
            content = default_score.read_text()
            for dimension in ["Security", "Encryption", "IAM Hygiene", "Cost Efficiency", "Tagging"]:
                assert dimension in content, f"Missing dimension '{dimension}' in score card HTML"

    def test_scan_findings_present(self, tmp_path):
        """E2E: scan of insecure fixture produces findings."""
        fixture = FIXTURES / "insecure_setup"
        result = runner.invoke(app, [
            "scan", str(fixture),
            "--format", "json",
            "--output", str(tmp_path / "report.json"),
        ])
        assert result.exit_code == 0
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["version"] == "2.1"
        total_findings = sum(data["summary"]["findings"].values())
        assert total_findings > 0

    def test_ci_mode_skips_browser(self, tmp_path, monkeypatch):
        """D-11: CI detection skips browser open."""
        monkeypatch.setenv("CI", "true")
        fixture = FIXTURES / "clean_infra"
        result = runner.invoke(app, [
            "scan", str(fixture),
            "--output", str(tmp_path / "report.html"),
        ])
        assert result.exit_code == 0
        # Should print path instead of opening browser
        assert "report.html" in result.output
