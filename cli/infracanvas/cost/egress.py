"""Egress cost estimator for CostLens (CPC-01) — implemented in Plan 04."""

from __future__ import annotations

from infracanvas.graph.models import ResourceGraph


class EgressEstimator:
    """Estimate egress costs for NetworkPath objects in the graph."""

    def estimate(self, graph: ResourceGraph) -> ResourceGraph:
        """Stub — implemented in Plan 04."""
        raise NotImplementedError("EgressEstimator implemented in Plan 04")
