"""Phase 12 ASY-03 D-10 — impact scoring tests.

RED until Plan 12-05 lands ``app.security.pathcompute.impact``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.impact")  # collection RED

from app.security.pathcompute.impact import (  # noqa: E402
    impact_bytes_per_sec,
    impact_firewall_count,
)


def test_bytes_per_sec() -> None:
    """D-10: (1500 + 2500 + 3000) / 60s ≈ 116.67 B/s."""
    pytest.skip("Plan 12-05 to implement impact_bytes_per_sec")
    # flows = [
    #     mk_flow("10.1.0.5", "10.2.0.5", bytes=1500),
    #     mk_flow("10.1.0.5", "10.2.0.5", bytes=2500),
    #     mk_flow("10.1.0.5", "10.2.0.5", bytes=3000),
    # ]
    # bps = impact_bytes_per_sec(flows, window_seconds=60)
    # assert bps == pytest.approx(116.67, rel=1e-2)


def test_firewall_count() -> None:
    """D-10: forward traverses {fw-a, fw-b}, return traverses {fw-a, fw-c};
    stateful={fw-a, fw-b, fw-c} → impact_firewall_count == 2 (fw-b + fw-c each
    see only one leg)."""
    pytest.skip("Plan 12-05 to implement impact_firewall_count")
    # fwd = mk_path("forward", [PathHop(node_id="fw-a"), PathHop(node_id="fw-b")])
    # ret = mk_path("return", [PathHop(node_id="fw-a"), PathHop(node_id="fw-c")])
    # count = impact_firewall_count(fwd, ret, stateful_firewalls={"fw-a", "fw-b", "fw-c"})
    # assert count == 2
