"""Phase 12 PTH-01 — forward path computation tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.forward``.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.security.pathcompute.forward import compute_forward


def _r(prefix: str, next_hop: str, metric: int = 100, as_path: str = "") -> SimpleNamespace:
    return SimpleNamespace(prefix=prefix, next_hop=next_hop, metric=metric, as_path=as_path)


def test_forward_path_resolves_to_destination() -> None:
    """PTH-01: compute_forward returns a NetworkPath whose hops chain
    src-side router → next hops toward dst CIDR.
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
    path = compute_forward("10.1.0.5", "10.2.0.5", snapshot)
    assert path.direction == "forward"
    assert len(path.hops) >= 1
    assert path.hops[0].next_hop != ""


def test_forward_empty_snapshot_returns_empty_path() -> None:
    """Empty snapshot → returns NetworkPath with empty hops + reason in evidence."""
    path = compute_forward("10.1.0.5", "10.2.0.5", {})
    assert path.direction == "forward"
    assert path.hops == []
    assert "reason" in path.evidence


def test_forward_loop_detection() -> None:
    """Loop in snapshot → loop detection terminates expansion (no infinite loop)."""
    snapshot = {
        "router-1": [_r("10.2.0.0/24", "router-2"), _r("10.1.0.0/24", "router-1")],
        "router-2": [_r("10.2.0.0/24", "router-1"), _r("10.1.0.0/24", "router-1")],
    }
    path = compute_forward("10.1.0.5", "10.2.0.5", snapshot, max_hops=20)
    # Should not loop forever; hops bounded
    assert len(path.hops) <= 20
