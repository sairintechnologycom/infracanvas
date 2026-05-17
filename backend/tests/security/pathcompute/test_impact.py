"""Phase 12 ASY-03 D-10 — impact scoring tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.impact``.
"""
from __future__ import annotations

import pytest
from infracanvas.graph.models import NetworkPath, PathHop

from app.security.pathcompute.impact import impact_bytes_per_sec, impact_firewall_count


def _mk_path(direction: str, nodes: list[str]) -> NetworkPath:
    return NetworkPath(
        id=f"p-{direction}",
        source_node_id="src",
        dest_node_id="dst",
        direction=direction,
        hops=[PathHop(hop_index=i, node_id=n) for i, n in enumerate(nodes)],
    )


def test_bytes_per_sec() -> None:
    """D-10: (1500 + 2500 + 3000) / 60s ≈ 116.67 B/s."""
    flows = [
        {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", "bytes": 1500},
        {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", "bytes": 2500},
        {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", "bytes": 3000},
    ]
    bps = impact_bytes_per_sec(flows, window_seconds=60)
    assert bps == pytest.approx(116.67, rel=1e-2)


def test_bytes_per_sec_zero_window_safe() -> None:
    """window_seconds <= 0 returns 0.0 (no div-by-zero)."""
    flows = [{"bytes": 100}]
    assert impact_bytes_per_sec(flows, window_seconds=0) == 0.0


def test_firewall_count() -> None:
    """D-10: forward traverses {fw-a, fw-b}, return traverses {fw-a, fw-c};
    stateful={fw-a, fw-b, fw-c} → impact_firewall_count == 2 (fw-b + fw-c each
    see only one leg)."""
    fwd = _mk_path("forward", ["fw-a", "fw-b"])
    ret = _mk_path("return", ["fw-a", "fw-c"])
    count = impact_firewall_count(fwd, ret, stateful_firewalls={"fw-a", "fw-b", "fw-c"})
    assert count == 2


def test_firewall_count_symmetric_returns_zero() -> None:
    """Symmetric pair → no one-legged firewall."""
    fwd = _mk_path("forward", ["fw-a", "fw-b"])
    ret = _mk_path("return", ["fw-a", "fw-b"])
    assert impact_firewall_count(fwd, ret, stateful_firewalls={"fw-a", "fw-b"}) == 0
