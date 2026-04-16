"""Self-contained HTML score card export — D-08 layout."""

from __future__ import annotations

from pathlib import Path

from infracanvas.graph.models import ScoreCard

# Grade → color mapping per UI-SPEC Score Card Grade Colors
GRADE_COLORS: dict[str, str] = {
    "A": "#22c55e",
    "B": "#4ade80",
    "C": "#f59e0b",
    "D": "#f97316",
    "F": "#ef4444",
}

# Dimension-specific progress bar fill colors per UI-SPEC Color section
DIMENSION_COLORS: dict[str, str] = {
    "Security":        "#3b82f6",
    "Encryption":      "#a855f7",
    "IAM Hygiene":     "#f97316",
    "Cost Efficiency": "#22c55e",
    "Tagging":         "#64748b",
}

# Severity display colors for the stats footer
SEVERITY_COLORS: dict[str, str] = {
    "critical": "#ef4444",
    "high":     "#f97316",
    "medium":   "#f59e0b",
    "info":     "#3b82f6",
}


def _grade_color(grade: str) -> str:
    """Return the UI-SPEC hex color for a letter grade."""
    return GRADE_COLORS.get(grade, "#e2e8f0")


def export_scorecard(card: ScoreCard, output_path: Path) -> None:
    """Generate a self-contained HTML score card file with D-08 layout."""
    grade_color = _grade_color(card.overall_grade)

    # Build dimension progress bar rows
    dimensions_html = ""
    for cat in card.categories:
        dim_color = DIMENSION_COLORS.get(cat.name, "#94a3b8")
        bar_width = max(cat.score, 0)
        dimensions_html += f"""
        <div class="dim-row">
          <div class="dim-header">
            <span class="dim-label">{cat.name}</span>
            <span class="dim-score">{cat.score}/100</span>
          </div>
          <div class="dim-track">
            <div class="dim-fill" style="width:{bar_width}%;background:{dim_color}"></div>
          </div>
        </div>"""

    # Build severity breakdown counts from top_issues
    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "info": 0}
    for issue in card.top_issues:
        sev = issue.severity.value
        if sev in severity_counts:
            severity_counts[sev] += 1

    total_findings = sum(severity_counts.values())

    severity_html = "  ".join(
        f'<span style="color:{SEVERITY_COLORS[sev]}">{sev.capitalize()}: {count}</span>'
        for sev, count in severity_counts.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InfraCanvas Score Card — {card.overall_grade} ({card.overall}/100)</title>
<meta property="og:title" content="InfraCanvas Score Card — {card.overall_grade} ({card.overall}/100)">
<meta property="og:description" content="{card.resource_count} resources, {total_findings} findings">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e2e8f0;font-family:'Inter',ui-sans-serif,system-ui,sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:2rem}}
.card{{max-width:480px;width:100%;background:#111827;border-radius:12px;border:1px solid #1e293b;padding:24px}}
.header{{margin-bottom:24px}}
.header-brand{{font-size:14px;font-weight:600;color:#e2e8f0}}
.header-project{{font-size:12px;color:#94a3b8;margin-top:2px}}
.header-date{{font-size:12px;color:#64748b;margin-top:2px}}
.grade-section{{text-align:center;margin-bottom:24px}}
.grade-letter{{font-size:72px;font-weight:600;line-height:1;color:{grade_color}}}
.grade-numeric{{font-size:14px;font-weight:600;color:{grade_color};margin-top:4px}}
.divider{{height:1px;background:#1e293b;margin:0 0 24px}}
.dimensions{{margin-bottom:24px}}
.dim-row{{margin-bottom:8px}}
.dim-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.dim-label{{font-size:12px;color:#94a3b8}}
.dim-score{{font-size:12px;font-family:ui-monospace,monospace;color:#e2e8f0}}
.dim-track{{height:4px;border-radius:4px;background:#1e293b}}
.dim-fill{{height:4px;border-radius:4px}}
.stats{{margin-bottom:24px;font-size:12px;color:#94a3b8}}
.stats-row{{margin-bottom:4px}}
.severity-row{{margin-top:4px}}
.cta-section{{text-align:center;margin-bottom:24px}}
.cta-btn{{display:inline-block;background:#3b82f640;border:1px solid #3b82f6;color:#60a5fa;font-size:12px;font-weight:600;border-radius:6px;padding:8px 16px;text-decoration:none;cursor:pointer}}
.cta-sub{{font-size:12px;color:#64748b;margin-top:8px}}
.attribution{{text-align:center;font-size:12px;color:#64748b}}
.attribution a{{color:#64748b;text-decoration:none}}
.attribution a:hover{{color:#94a3b8;text-decoration:underline}}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-brand">InfraCanvas</div>
    <div class="header-project">{card.project}</div>
    <div class="header-date">{card.scanned_at}</div>
  </div>

  <div class="grade-section">
    <div class="grade-letter">{card.overall_grade}</div>
    <div class="grade-numeric">{card.overall} / 100</div>
  </div>

  <div class="divider"></div>

  <div class="dimensions">
    {dimensions_html}
  </div>

  <div class="divider"></div>

  <div class="stats">
    <div class="stats-row">{card.resource_count} resources &nbsp;&middot;&nbsp; {total_findings} findings</div>
    <div class="severity-row">{severity_html}</div>
  </div>

  <div class="divider"></div>

  <div class="cta-section">
    <a class="cta-btn" href="https://infracanvas.dev/founding" target="_blank" rel="noopener noreferrer">
      Unlock finding details &rarr;
    </a>
    <div class="cta-sub">Founding member pricing &mdash; $49/mo locked forever</div>
  </div>

  <div class="divider"></div>

  <div class="attribution">
    Generated by InfraCanvas &middot; <a href="https://infracanvas.dev" target="_blank" rel="noopener noreferrer">infracanvas.dev</a>
  </div>
</div>
</body>
</html>"""

    output_path.write_text(html)
