"""CLI contract tests for WRG-01 exit codes + stderr routing (Plan 01)."""
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "infracanvas.main"]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,  # cli/
    )


class TestExportExitCodes:
    def test_export_missing_file_exits_1(self, tmp_path):
        """CLI-EXIT-01: missing input file -> exit code 1."""
        result = _run(["export", str(tmp_path / "nonexistent.json")])
        assert result.returncode == 1, (
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        # Error on stderr, not stdout (D-03)
        assert "Error" in result.stderr or "not found" in result.stderr.lower()
        assert "Error" not in result.stdout

    def test_export_malformed_json_exits_2(self, tmp_path):
        """CLI-EXIT-02: parse/validation error -> exit code 2."""
        bad = tmp_path / "malformed.json"
        bad.write_text("{not valid json at all")
        result = _run(["export", str(bad)])
        assert result.returncode == 2, (
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "Error" in result.stderr or "Invalid" in result.stderr

    def test_export_help_shows_gate_mode_flag(self):
        """CLI-EXIT-03: --gate-mode / --no-gate-mode visible in help."""
        result = _run(["export", "--help"])
        assert result.returncode == 0
        # Rich/Typer may wrap option text across lines; check each flag
        # token appears somewhere in stdout (possibly on different lines).
        assert "--gate-mode" in result.stdout
        assert "--no-gate-mode" in result.stdout


class TestScoreExitCodes:
    def test_score_not_a_directory_exits_2(self, tmp_path):
        """Score on a file instead of directory -> parse/validation error = exit 2."""
        fake = tmp_path / "not-a-dir.txt"
        fake.write_text("hello")
        result = _run(["score", str(fake)])
        assert result.returncode == 2
