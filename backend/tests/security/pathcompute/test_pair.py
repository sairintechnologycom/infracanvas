"""Phase 12 PTH-02 — forward/return pair computation tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.pair``.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.security.pathcompute.pair import compute_pair


def _r(prefix: str, next_hop: str, metric: int = 100, as_path: str = "") -> SimpleNamespace:
    return SimpleNamespace(prefix=prefix, next_hop=next_hop, metric=metric, as_path=as_path)


def test_compute_pair_swaps_src_dst() -> None:
    """PTH-02: compute_pair returns (forward, return) where the return leg
    has direction='return' and was computed with src/dst swapped.
    """
    snapshot = {
        "router-1": [
            _r("10.1.0.0/24", "router-1"),
            _r("10.2.0.0/24", "router-2"),
        ],
        "router-2": [
            _r("10.2.0.0/24", "router-2"),
            _r("10.1.0.0/24", "router-1"),
        ],
    }
    forward, ret = compute_pair("10.1.0.5", "10.2.0.5", snapshot)
    assert forward.direction == "forward"
    assert ret.direction == "return"
    # Return path was computed with src/dst swapped
    assert ret.evidence.get("pair_src") == "10.1.0.5"
    assert ret.evidence.get("pair_dst") == "10.2.0.5"
