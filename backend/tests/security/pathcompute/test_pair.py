"""Phase 12 PTH-02 — forward/return pair computation tests.

RED until Plan 12-05 lands ``app.security.pathcompute.pair``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.pair")  # collection RED

from app.security.pathcompute.pair import compute_pair  # noqa: E402


def test_compute_pair_swaps_src_dst() -> None:
    """PTH-02: compute_pair returns (forward, return) where the return leg
    has src/dst swapped (return.hops[0].source_ip falls in dst CIDR).
    """
    pytest.skip("Plan 12-05 to implement compute_pair")
    # snapshot = _build_snapshot()
    # forward, ret = compute_pair("10.1.0.5", "10.2.0.5", snapshot)
    # assert forward.direction == "forward"
    # assert ret.direction == "return"
    # # return leg starts on the dst-side network (10.2.0.0/24)
    # assert ret.hops[0].source_ip.startswith("10.2.0.")
