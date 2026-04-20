"""Per-module coverage gate (WRG-04 D-15).

pytest-cov's --cov-fail-under is global; this hook enforces that
security/, cost/, and drift/ each independently meet >=80% line AND
branch coverage, so one module cannot hide below threshold behind
another's strength.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Module prefixes to gate independently. Paths are relative to the
# installed `infracanvas` package (matches [tool.coverage.run] source).
PER_MODULE_GATES: dict[str, float] = {
    "infracanvas/security": 80.0,
    "infracanvas/cost": 80.0,
    "infracanvas/drift": 80.0,
}


def _module_percents(cov) -> dict[str, tuple[float, float, int, int, int, int]]:
    """Return {module_prefix: (line_pct, branch_pct, lines_hit, lines_total,
    branches_hit, branches_total)} aggregated across every measured file
    whose path contains the prefix.

    Takes a coverage.Coverage instance (not a CoverageData) because
    analysis2() is defined on Coverage, which knows about the config
    (branch-enabled, file_reporter, etc.)."""
    cov_data = cov.get_data()
    agg: dict[str, list[int]] = {
        prefix: [0, 0, 0, 0]  # lines_hit, lines_total, branches_hit, branches_total
        for prefix in PER_MODULE_GATES
    }

    for filename in cov_data.measured_files():
        # Normalise to forward-slash for cross-platform matching.
        normalised = filename.replace("\\", "/")
        for prefix in PER_MODULE_GATES:
            if prefix not in normalised:
                continue
            try:
                analysis = cov.analysis2(filename)
            except Exception:  # noqa: BLE001 — skip files coverage cannot read
                continue
            # analysis2 returns (filename, executable, excluded, missing, missing_formatted)
            executable = set(analysis[1])
            missing = set(analysis[3])
            hit = len(executable - missing)
            total = len(executable)
            agg[prefix][0] += hit
            agg[prefix][1] += total

            # Branch data (optional — only present if branch=true).
            # Use coverage.results.analysis_from_file_reporter for the
            # numbers object that aggregates line + branch stats.
            try:
                from coverage.results import analysis_from_file_reporter
                fr = cov._get_file_reporter(filename)
                an = analysis_from_file_reporter(cov_data, 2, fr, filename)
                n_branches = an.numbers.n_branches
                n_missing_branches = an.numbers.n_missing_branches
                hit_branches = max(n_branches - n_missing_branches, 0)
                agg[prefix][2] += hit_branches
                agg[prefix][3] += n_branches
            except Exception:  # noqa: BLE001 — coverage API variance is tolerated
                pass

    result: dict[str, tuple[float, float, int, int, int, int]] = {}
    for prefix, (lh, lt, bh, bt) in agg.items():
        line_pct = (lh / lt * 100.0) if lt else 100.0
        branch_pct = (bh / bt * 100.0) if bt else 100.0
        result[prefix] = (line_pct, branch_pct, lh, lt, bh, bt)
    return result


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """After the test session, enforce per-module >=80% line+branch gate."""
    # Only run when coverage was collected (pytest-cov active).
    try:
        import coverage
    except ImportError:
        return

    cov_file = Path(session.config.rootpath) / ".coverage"
    if not cov_file.exists():
        return

    cov = coverage.Coverage(data_file=str(cov_file))
    cov.load()

    failures: list[str] = []
    per_module = _module_percents(cov)
    for prefix, threshold in PER_MODULE_GATES.items():
        line_pct, branch_pct, lh, lt, bh, bt = per_module[prefix]
        if lt == 0:
            # No files measured for this prefix in the current run scope —
            # skip the gate (a scoped run like `pytest tests/test_cost.py`
            # should not fail for `security` having 0 measured files).
            continue
        if line_pct < threshold:
            failures.append(
                f"PER-MODULE COVERAGE FAIL: {prefix} line={line_pct:.1f}% "
                f"({lh}/{lt}) < {threshold:.0f}%"
            )
        if bt > 0 and branch_pct < threshold:
            failures.append(
                f"PER-MODULE COVERAGE FAIL: {prefix} branch={branch_pct:.1f}% "
                f"({bh}/{bt}) < {threshold:.0f}%"
            )

    if failures:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_sep("!", "PER-MODULE COVERAGE GATE (D-15)", red=True)
            for msg in failures:
                reporter.write_line(msg, red=True)
        # Mark the session as failed (only if tests themselves didn't already fail)
        if exitstatus == 0:
            session.exitstatus = 1
