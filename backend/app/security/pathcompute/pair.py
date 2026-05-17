"""Bidirectional path pair builder (PTH-02).

Public function:
    compute_pair(src_ip, dst_ip, route_snapshot) -> tuple[NetworkPath, NetworkPath]
"""
from __future__ import annotations

from typing import Any

from infracanvas.graph.models import NetworkPath

from app.security.pathcompute.forward import compute_forward


def compute_pair(
    src_ip: str,
    dst_ip: str,
    route_snapshot: dict[str, list[Any]],
) -> tuple[NetworkPath, NetworkPath]:
    """Compute forward + return paths for a single src/dst pair.

    The return path is the result of ``compute_forward(dst_ip, src_ip, ...)``
    with ``direction='return'`` and a stable ID prefix. The ``evidence`` dict
    carries the original pair anchors (``pair_src`` / ``pair_dst``) so
    downstream classifiers + correlate know the un-swapped endpoints.
    """
    fwd = compute_forward(src_ip, dst_ip, route_snapshot)
    ret_raw = compute_forward(dst_ip, src_ip, route_snapshot)
    ret = NetworkPath(
        id=f"ret-{src_ip}-{dst_ip}",
        source_node_id=dst_ip,
        dest_node_id=src_ip,
        direction="return",
        hops=ret_raw.hops,
        evidence={
            **ret_raw.evidence,
            "pair_src": src_ip,
            "pair_dst": dst_ip,
        },
    )
    return fwd, ret
