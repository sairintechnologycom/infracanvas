"""Phase 12 PTH-01 — forward path computation tests.

RED until Plan 12-05 lands ``app.security.pathcompute.forward``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.forward")  # collection RED

from app.security.pathcompute.forward import compute_forward  # noqa: E402


def test_forward_path_resolves_to_destination() -> None:
    """PTH-01: compute_forward returns a NetworkPath whose first hop has a
    next_hop set and whose last hop's dest_ip falls within the destination CIDR.
    """
    pytest.skip("Plan 12-05 to implement compute_forward")
    # snapshot = _build_snapshot()  # routes + firewall NAT + interfaces
    # path = compute_forward(src="10.1.0.5", dst="10.2.0.5", snapshot=snapshot)
    # assert path.direction == "forward"
    # assert path.hops[0].next_hop is not None
    # assert path.hops[-1].dest_ip.startswith("10.2.0.")
