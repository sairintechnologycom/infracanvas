"""Asymmetry detection via hop-node symmetric difference (ASY-01).

Public functions:
    is_asymmetric(forward, ret) -> bool
    asymmetric_nodes(forward, ret) -> set[str]
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkPath


def is_asymmetric(forward: NetworkPath, ret: NetworkPath) -> bool:
    """True iff forward and return traverse different node sets.

    ASY-01: a pair is asymmetric when there exists a hop on exactly one
    of the two paths (set symmetric difference is non-empty).
    """
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    return (fwd_nodes ^ ret_nodes) != set()


def asymmetric_nodes(forward: NetworkPath, ret: NetworkPath) -> set[str]:
    """Nodes that appear on exactly one of the two paths.

    Returns the empty set when the pair is symmetric.
    """
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    return fwd_nodes ^ ret_nodes
