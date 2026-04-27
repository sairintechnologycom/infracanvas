"""Denormalized graph summary computation.

Extracted from :mod:`infracanvas.main._run_scan` so the backend indexing
worker (Phase 6 Plan 06-06) can reuse the same logic without depending
on the Typer CLI surface. The CLI calls ``compute_summary`` after
findings are attached to the graph; the backend worker calls it on the
ResourceGraph blob loaded from R2.

Score formula (preserved verbatim from main.py for behavioural equality):

    score = 100
            - 20 * critical_count
            - 10 * high_count
            -  5 * medium_count
            -  1 * info_count
    score = max(score, 0)
"""

from __future__ import annotations

from infracanvas.graph.models import GraphSummary, ResourceGraph

# Per-severity weights for the security score. Keys MUST match the
# ``Severity`` enum value strings exactly so f.severity.value resolves cleanly.
_SCORE_WEIGHTS: dict[str, int] = {
    "critical": 20,
    "high": 10,
    "medium": 5,
    "info": 1,
}


def compute_summary(graph: ResourceGraph) -> GraphSummary:
    """Build a :class:`GraphSummary` from finding counts on the graph nodes.

    Returns a fresh ``GraphSummary`` — does NOT mutate ``graph.summary``
    (the CLI/worker assigns the result back). Cost is left at 0.0 by
    design: CostLens phases populate it via a separate pipeline.
    """
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "info": 0}
    for node in graph.nodes:
        for finding in node.findings:
            key = finding.severity.value
            counts[key] = counts.get(key, 0) + 1

    score = 100 - sum(counts[k] * w for k, w in _SCORE_WEIGHTS.items())
    score = max(0, score)

    return GraphSummary(
        total_resources=len(graph.nodes),
        findings=counts,
        estimated_monthly_cost=0.0,
        score=score,
    )
