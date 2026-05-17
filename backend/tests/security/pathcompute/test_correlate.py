"""Phase 12 PTH-03 — NetFlow correlation tests (D-05 endpoint-only v1.1).

RED until Plan 12-05 lands ``app.security.pathcompute.correlate``.

Per Q2 RESOLVED in 12-RESEARCH.md: v1.1 ships endpoint-only matching;
edge-hop interface comparison is deferred to v1.2.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.correlate")  # collection RED

from app.security.pathcompute.correlate import emit_divergence, matches  # noqa: E402


def test_endpoint_only_match_v1_1() -> None:
    """D-05 v1.1 endpoint-only: flow whose src/dst fall in path CIDRs → matches."""
    pytest.skip("Plan 12-05 to implement endpoint-only matches()")
    # flow = {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", ...}
    # path = mk_path("forward", [...])  # CIDR 10.1.0.0/24 → 10.2.0.0/24
    # assert matches(flow, path) is True


def test_divergence_emitted() -> None:
    """D-07: observed flow that matches no computed path → emit path_divergence."""
    pytest.skip("Plan 12-05 to implement emit_divergence")
    # flow = {"src_ip": "10.99.0.5", "dst_ip": "10.99.0.6", ...}
    # paths = [mk_path("forward", [...])]  # nothing covering 10.99/16
    # finding = emit_divergence(flow, paths)
    # assert finding is not None
    # assert finding.rule_id == "PATH_DIVERGENCE"
