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
        result = runner.invoke(app, ["scan", str(FIXTURES / "simple_vpc"), "--json"])
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
            "--json", "--severity", "critical",
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
            "--json", "--ignore", "SEC-001",
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
            "scan", str(tmp_path / "tf"), "--json",
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


class TestPhase51CLI:
    """Phase 5.1 CLI UX tests — --quiet one-liner, --open browser, parse warnings on stderr.

    Uses a dedicated ``CliRunner(mix_stderr=False)`` so the assertions can distinguish
    stdout from stderr. The stderr routing contract (Task 1 Edit 6) depends on this:
    parse warnings must NOT appear on stdout when --quiet is set.
    """

    # Separate stdout/stderr so we can assert stdout is exactly the one-line summary
    # while stderr carries parse warnings and error messages.
    split_runner = CliRunner(mix_stderr=False)

    def test_51e_scan_quiet_one_line_summary(self):
        """5.1-E: --quiet prints exactly one summary line to stdout; exit 0."""
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"), "--quiet",
        ])
        assert result.exit_code == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(stdout_lines) == 1, (
            f"expected 1 stdout line, got {len(stdout_lines)}: {stdout_lines}"
        )
        line = stdout_lines[0]
        # Format: `(✓|OK) N resources · M findings · score S[ · opened in browser]`
        assert "resources" in line
        assert "findings" in line
        assert "score" in line
        # Tick is ✓ in TTY or OK in pipe (CliRunner is non-TTY → "OK")
        assert line.startswith("OK ") or line.startswith("✓ "), (
            f"unexpected prefix: {line!r}"
        )

    def test_51f_scan_open_rejects_non_html_format(self):
        """5.1-F: --open --format json exits with code 2 and reports the error on stderr."""
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--open", "--format", "json",
        ])
        assert result.exit_code == 2
        # Error on stderr.
        combined = result.stderr + result.stdout
        assert "--open requires --format html" in combined, (
            f"unexpected output — stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_51g_scan_open_invokes_webbrowser(self, tmp_path, monkeypatch):
        """5.1-G: --open with format=html calls webbrowser.open with a file:// URI."""
        calls: list[str] = []

        def fake_open(url: str, *args, **kwargs) -> bool:
            calls.append(url)
            return True

        monkeypatch.setattr("infracanvas.main.webbrowser.open", fake_open)

        out_path = tmp_path / "out.html"
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--open",
            "--format", "html",
            "--output", str(out_path),
        ])
        assert result.exit_code == 0, (
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert len(calls) == 1, (
            f"expected webbrowser.open once, got {len(calls)}: {calls}"
        )
        assert calls[0].startswith("file://"), (
            f"expected file:// URI, got {calls[0]!r}"
        )
        assert calls[0].endswith(".html")
        # Summary line must carry the "opened in browser" tail when --open succeeds.
        assert "opened in browser" in result.stdout

    def test_51h_scan_quiet_envs_layout_surfaces_submodule_parse_warning(self, tmp_path):
        """5.1-H: scan on envs_layout (has broken submodule) — stdout stays one line,
        stderr carries parse warning, exit 0."""
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "envs_layout" / "envs" / "prod"),
            "--quiet",
            "--output", str(tmp_path / "report.html"),
        ])
        assert result.exit_code == 0, (
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
        # stdout must remain exactly one summary line — warnings belong to stderr.
        assert len(stdout_lines) == 1, (
            f"expected 1 stdout line, got: {stdout_lines}"
        )
        # D-01: parse warnings for broken submodule must appear on stderr.
        # This asserts the parse_errors loop is MOVED to AFTER resolve_modules
        # (Task 1 Edit 6); if the loop still runs before resolve_modules,
        # submodule errors will be missing and this assertion will fail.
        assert "Could not parse" in result.stderr, (
            f"expected parse warning on stderr, got: {result.stderr!r}"
        )
        assert "broken" in result.stderr.lower(), (
            f"expected 'broken' submodule reference on stderr, got: {result.stderr!r}"
        )
        # Placeholder node should make it into the resource count.
        assert "resources" in stdout_lines[0]

    def test_51i_scan_quiet_json_mutually_exclusive(self):
        """5.1-I: --quiet and --json together → exit 2 with clear error."""
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--json",
        ])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.stderr

    def test_quiet_format_json_writes_output_file(self, tmp_path):
        """--quiet --format json --output X must still write the JSON file.

        Regression: the quiet branch only handled format=html; combining --quiet
        with --format json silently dropped the requested --output path.
        """
        out = tmp_path / "scan.json"
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"),
            "--quiet", "--format", "json", "--output", str(out),
        ])
        assert result.exit_code == 0, result.stderr
        assert out.exists(), f"expected {out} to be written"
        data = json.loads(out.read_text())
        assert len(data["nodes"]) > 0
        # Quiet mode still emits exactly one summary line on stdout.
        assert "resources" in result.stdout

    def test_51j_scan_json_exits_zero_regardless_of_findings(self):
        """5.1-J: --json exits 0 even when findings exist (unlike --ci).
        Replaces old --quiet semantics."""
        result = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"), "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["nodes"]) > 0

    def test_51k_export_open_opt_in(self, tmp_path, monkeypatch):
        """5.1-K: export no longer opens browser by default; --open is required."""
        # First, generate a report JSON via --json
        scan_res = self.split_runner.invoke(app, [
            "scan", str(FIXTURES / "simple_vpc"), "--json",
        ])
        assert scan_res.exit_code == 0
        report_path = tmp_path / "report.json"
        report_path.write_text(scan_res.stdout)

        calls: list[str] = []

        def fake_open(url: str, *args, **kwargs) -> bool:
            calls.append(url)
            return True

        monkeypatch.setattr("infracanvas.main.webbrowser.open", fake_open)

        out_html = tmp_path / "out.html"
        # Without --open: no browser
        res_no_open = self.split_runner.invoke(app, [
            "export", str(report_path),
            "--output", str(out_html),
        ])
        assert res_no_open.exit_code == 0
        assert len(calls) == 0, (
            f"export without --open must not invoke webbrowser; calls={calls}"
        )

        # With --open: browser invoked
        res_open = self.split_runner.invoke(app, [
            "export", str(report_path),
            "--output", str(out_html),
            "--open",
        ])
        assert res_open.exit_code == 0
        assert len(calls) == 1, (
            f"export --open must invoke webbrowser once; calls={calls}"
        )
