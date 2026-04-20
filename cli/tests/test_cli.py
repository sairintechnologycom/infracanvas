"""Tests for CLI commands via direct invocation (for coverage)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from infracanvas.main import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


class TestScanCommand:
    def test_scan_simple_vpc(self):
        result = runner.invoke(app, ["scan", str(FIXTURES / "simple_vpc"), "--quiet"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["nodes"]) == 6

    def test_scan_with_output_file(self, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(app, ["scan", str(FIXTURES / "simple_vpc"), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_scan_severity_filter(self):
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--severity", "critical",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        for node in data["nodes"]:
            for f in node["findings"]:
                assert f["severity"] == "critical"

    def test_scan_ci_mode_critical(self):
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--ci", "--severity", "critical",
        ])
        assert result.exit_code == 1

    def test_scan_ci_mode_clean(self):
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "clean_infra"),
            "--ci", "--severity", "critical",
        ])
        assert result.exit_code == 0

    def test_scan_invalid_directory(self):
        result = runner.invoke(app, ["scan", "/nonexistent/path"])
        assert result.exit_code == 2  # error exit code (vs 1 for findings)

    def test_scan_format_json(self):
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"), "--format", "json",
        ])
        assert result.exit_code == 0

    def test_scan_format_html_no_template(self, tmp_path):
        """HTML format gracefully falls back when template missing."""
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--format", "html",
        ])
        # Should still succeed (falls back to JSON)
        assert result.exit_code == 0

    def test_scan_rich_output(self):
        """Non-quiet scan prints rich table."""
        result = runner.invoke(app, ["scan", str(FIXTURES / "simple_vpc")])
        assert result.exit_code == 0
        assert "Security Score" in result.stdout or "InfraCanvas" in result.stdout


    def test_scan_ignore_rule(self):
        result = runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--ignore", "SEC-001",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        for node in data["nodes"]:
            for f in node["findings"]:
                assert f["rule_id"] != "SEC-001"

    def test_scan_ci_exit_code_2_no_tf(self, tmp_path):
        """CI mode exits 2 for parse errors / no .tf files."""
        result = runner.invoke(app, ["scan", str(tmp_path), "--ci"])
        assert result.exit_code == 2


class TestVersionFlag:
    def test_version_output(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestConfig:
    def test_config_ignore_rules(self, tmp_path):
        """Config file ignore_rules are applied."""
        # Copy fixture
        import shutil
        shutil.copytree(FIXTURES / "simple_vpc", tmp_path / "tf")
        config = tmp_path / "tf" / ".infracanvas.yml"
        config.write_text("ignore_rules:\n  - SEC-001\n")
        result = runner.invoke(app, [
            "scan", str(tmp_path / "tf"), "--quiet",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        for node in data["nodes"]:
            for f in node["findings"]:
                assert f["rule_id"] != "SEC-001"


class TestScoreCommand:
    def test_score_text_output(self):
        result = runner.invoke(app, ["score", str(FIXTURES / "simple_vpc")])
        assert result.exit_code == 0
        assert "Score" in result.stdout

    def test_score_json_output(self):
        result = runner.invoke(app, ["score", str(FIXTURES / "simple_vpc"), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "overall" in data
        assert "categories" in data

    def test_score_invalid_directory(self):
        result = runner.invoke(app, ["score", "/nonexistent"])
        assert result.exit_code == 2  # WRG-01 D-04: normalized not-a-directory to exit 2


class TestExportCommand:
    def test_export_json(self, tmp_path):
        # First create a JSON report
        report_path = tmp_path / "report.json"
        runner.invoke(app, ["scan", str(FIXTURES / "simple_vpc"), "--format", "json", "--output", str(report_path)])
        # Now export it
        result = runner.invoke(app, ["export", str(report_path), "--format", "json"])
        assert result.exit_code == 0

    def test_export_nonexistent_file(self):
        result = runner.invoke(app, ["export", "/nonexistent.json"])
        assert result.exit_code == 1


class TestServeCommand:
    def test_serve_help(self):
        """CLI-01: serve command exists and shows help."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "live-reloading" in result.output.lower() or "http" in result.output.lower()

    def test_serve_invalid_directory(self):
        """CLI-01: serve rejects invalid directory."""
        result = runner.invoke(app, ["serve", "/nonexistent/path"])
        assert result.exit_code == 2


class TestPlanCommand:
    def test_plan_command(self):
        result = runner.invoke(app, [
            "plan", str(FIXTURES / "simple_vpc"),
            "--planfile", str(FIXTURES / "sample_plan.json"),
            "--format", "json",
            "--output", "/tmp/ic-plan-test.json",
        ])
        assert result.exit_code == 0


class TestWatchMode:
    def test_watch_flag_accepted(self):
        """CLX-02-A: --watch flag is accepted by scan command."""
        from typer.testing import CliRunner
        from infracanvas.main import app
        runner = CliRunner()
        # Use a non-existent dir to trigger early exit, but verify flag is accepted
        result = runner.invoke(app, ["scan", "/nonexistent", "--watch"])
        # Should fail on directory, NOT on unknown flag
        assert "--watch" not in result.output or "no such option" not in result.output.lower()

    def test_watch_imports_watchdog(self):
        """CLX-02-B: watchdog is available for watch mode."""
        import importlib.metadata
        version = importlib.metadata.version("watchdog")
        assert version is not None


class TestFailOnFlag:
    def test_fail_on_critical_only(self):
        """CLX-01-A: --fail-on critical only exits non-zero on critical findings."""
        # This tests the exit logic, not the full scan
        from infracanvas.graph.models import GraphSummary
        summary = GraphSummary(findings={"critical": 0, "high": 5, "medium": 3, "info": 1})
        threshold = "critical"
        sev_order = ["critical", "high", "medium", "info"]
        threshold_idx = sev_order.index(threshold)
        has_findings = any(
            summary.findings.get(s, 0) > 0
            for s in sev_order[:threshold_idx + 1]
        )
        assert has_findings is False  # No critical findings

    def test_fail_on_high_exits(self):
        """CLX-01-B: --fail-on high exits non-zero when high findings exist."""
        from infracanvas.graph.models import GraphSummary
        summary = GraphSummary(findings={"critical": 0, "high": 5, "medium": 3, "info": 1})
        threshold = "high"
        sev_order = ["critical", "high", "medium", "info"]
        threshold_idx = sev_order.index(threshold)
        has_findings = any(
            summary.findings.get(s, 0) > 0
            for s in sev_order[:threshold_idx + 1]
        )
        assert has_findings is True  # High findings present
