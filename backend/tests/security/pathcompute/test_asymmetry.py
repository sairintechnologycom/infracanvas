"""Phase 12 ASY-01 — asymmetry detector tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.asymmetry``.
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkPath, PathHop

from app.security.pathcompute.asymmetry import asymmetric_nodes, is_asymmetric


def _mk_path(direction: str, nodes: list[str]) -> NetworkPath:
    return NetworkPath(
        id=f"p-{direction}",
        source_node_id="src",
        dest_node_id="dst",
        direction=direction,
        hops=[PathHop(hop_index=i, node_id=n) for i, n in enumerate(nodes)],
    )


def test_symmetric_pair_no_finding() -> None:
    """ASY-01: forward and return traverse identical hop set → not asymmetric."""
    fwd = _mk_path("forward", ["r1", "fw-a", "r2"])
    ret = _mk_path("return", ["r2", "fw-a", "r1"])
    assert is_asymmetric(fwd, ret) is False
    assert asymmetric_nodes(fwd, ret) == set()


def test_asymmetric_pair_flagged() -> None:
    """ASY-01: forward through fw-A, return through fw-B → asymmetric;
    asymmetric_nodes returns {fw-A, fw-B}."""
    fwd = _mk_path("forward", ["r1", "fw-A", "r2"])
    ret = _mk_path("return", ["r2", "fw-B", "r1"])
    assert is_asymmetric(fwd, ret) is True
    assert asymmetric_nodes(fwd, ret) == {"fw-A", "fw-B"}
