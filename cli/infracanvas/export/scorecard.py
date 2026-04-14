"""Self-contained HTML score card export."""

from __future__ import annotations

from pathlib import Path

from infracanvas.graph.models import ScoreCard


def _score_color(score: int) -> str:
    if score >= 80:
        return "#06d6a0"
    if score >= 60:
        return "#f59e0b"
    return "#ef4444"


def _severity_icon(severity: str) -> str:
    return {
        "critical": "&#x1F534;",
        "high": "&#x1F7E0;",
        "medium": "&#x1F7E1;",
        "info": "&#x1F535;",
    }.get(severity, "&#x26AA;")


def export_scorecard(card: ScoreCard, output_path: Path) -> None:
    """Generate a self-contained HTML score card file."""
    color = _score_color(card.overall)
    stroke_pct = card.overall / 100
    stroke_offset = 283 * (1 - stroke_pct)

    categories_html = ""
    for cat in card.categories:
        cat_color = _score_color(cat.score)
        bar_width = max(cat.score, 2)
        categories_html += f"""
        <div class="cat-row">
          <div class="cat-name">{cat.name}</div>
          <div class="cat-bar-bg">
            <div class="cat-bar" style="width:{bar_width}%;background:{cat_color}"></div>
          </div>
          <div class="cat-grade" style="color:{cat_color}">{cat.grade}</div>
          <div class="cat-count">{cat.finding_count} issue{"s" if cat.finding_count != 1 else ""}</div>
        </div>"""

    issues_html = ""
    for issue in card.top_issues[:5]:
        icon = _severity_icon(issue.severity.value)
        issues_html += f"""
        <div class="issue-row">
          <span class="issue-icon">{icon}</span>
          <span class="issue-id">{issue.rule_id}</span>
          <span class="issue-title">{issue.title}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InfraCanvas Score: {card.overall}/100 — {card.project}</title>
<meta property="og:title" content="InfraCanvas Score: {card.overall}/100 — {card.project}">
<meta property="og:description" content="{card.resource_count} resources · {len(card.top_issues)} issues found">
<meta property="og:type" content="website">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e2e8f0;font-family:'DM Sans',system-ui,sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:2rem}}
.card{{max-width:480px;width:100%;background:#111827;border-radius:16px;border:1px solid #1e293b;overflow:hidden}}
.header{{padding:2rem 2rem 1rem;text-align:center}}
.header h1{{font-size:1.1rem;font-weight:700;margin-bottom:.25rem}}
.header .meta{{font-size:.75rem;color:#64748b;font-family:'JetBrains Mono',monospace}}
.score-circle{{display:flex;justify-content:center;padding:1.5rem 0}}
.score-circle svg{{width:140px;height:140px}}
.score-circle .bg{{fill:none;stroke:#1e293b;stroke-width:8}}
.score-circle .fg{{fill:none;stroke:{color};stroke-width:8;stroke-linecap:round;stroke-dasharray:283;stroke-dashoffset:{stroke_offset:.1f};transform:rotate(-90deg);transform-origin:50% 50%;animation:draw 1s ease-out}}
@keyframes draw{{from{{stroke-dashoffset:283}}}}
.score-text{{font-size:2rem;font-weight:700;fill:{color}}}
.score-label{{font-size:.7rem;fill:#64748b}}
.grade-text{{font-size:1rem;font-weight:700;fill:{color}}}
.divider{{height:1px;background:#1e293b;margin:0 2rem}}
.section{{padding:1.25rem 2rem}}
.section-title{{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#64748b;margin-bottom:.75rem;font-weight:500}}
.cat-row{{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem}}
.cat-name{{width:90px;font-size:.75rem;font-weight:500}}
.cat-bar-bg{{flex:1;height:6px;background:#1e293b;border-radius:3px;overflow:hidden}}
.cat-bar{{height:100%;border-radius:3px;transition:width .6s ease}}
.cat-grade{{width:24px;font-size:.75rem;font-weight:700;text-align:center}}
.cat-count{{width:70px;font-size:.65rem;color:#64748b;text-align:right}}
.issue-row{{display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;font-size:.75rem}}
.issue-icon{{font-size:.7rem}}
.issue-id{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#94a3b8;width:55px}}
.issue-title{{color:#e2e8f0;flex:1}}
.cost{{font-size:.85rem;font-weight:600;text-align:center;padding:1rem 2rem;color:#94a3b8}}
.cost span{{color:#e2e8f0}}
.cta{{text-align:center;padding:1.25rem 2rem;border-top:1px solid #1e293b}}
.cta a{{color:#06d6a0;font-size:.75rem;text-decoration:none;font-weight:500}}
.cta a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>InfraCanvas Score Card</h1>
    <div class="meta">{card.project} &middot; {card.resource_count} resources</div>
  </div>
  <div class="score-circle">
    <svg viewBox="0 0 100 100">
      <circle class="bg" cx="50" cy="50" r="45"/>
      <circle class="fg" cx="50" cy="50" r="45"/>
      <text class="score-text" x="50" y="48" text-anchor="middle" dominant-baseline="middle">{card.overall}</text>
      <text class="score-label" x="50" y="62" text-anchor="middle">/100</text>
      <text class="grade-text" x="50" y="76" text-anchor="middle">{card.overall_grade}</text>
    </svg>
  </div>
  <div class="divider"></div>
  <div class="section">
    <div class="section-title">Categories</div>
    {categories_html}
  </div>
  <div class="divider"></div>
  <div class="section">
    <div class="section-title">Top Issues</div>
    {issues_html if issues_html else '<div style="font-size:.75rem;color:#22c55e;text-align:center">No issues found</div>'}
  </div>
  <div class="divider"></div>
  <div class="cost">Est. monthly cost: <span>${card.estimated_monthly_cost:,.0f}</span></div>
  <div class="cta">
    <a href="https://infracanvas.dev">Scan your own infra &rarr; infracanvas.dev</a>
  </div>
</div>
</body>
</html>"""

    output_path.write_text(html)
