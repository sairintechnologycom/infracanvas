"""Idle resource detector for CostLens (CLA-05..06) — implemented in Plan 03."""

from __future__ import annotations

from infracanvas.graph.models import ResourceGraph


class IdleDetector:
    """Detect idle shared resources and populate CostLensData.recommendations."""

    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        """Stub — implemented in Plan 03."""
        raise NotImplementedError("IdleDetector implemented in Plan 03")
