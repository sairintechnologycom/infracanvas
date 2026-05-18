"""Impact scoring (ASY-03 D-10) — two scalars per asymmetry finding.

Public functions:
    impact_bytes_per_sec(flows, window_seconds=3600) -> float
    impact_firewall_count(forward, ret, stateful_firewalls) -> int
"""
from __future__ import annotations

from typing import Any

from infracanvas.graph.models import NetworkPath


def impact_bytes_per_sec(flows: list[Any], window_seconds: int = 3600) -> float:
    """D-10: total bytes from matched flows / window (default 1h per D-06).

    Returns 0.0 when ``window_seconds <= 0`` (defensive — no div-by-zero).
    Accepts both dict-shaped flow rows and attribute-bearing flow objects.
    """
    if window_seconds <= 0:
        return 0.0
    total = 0
    for f in flows:
        total += int(_attr(f, "bytes") or 0)
    return float(total) / float(window_seconds)


def impact_firewall_count(
    forward: NetworkPath,
    ret: NetworkPath,
    stateful_firewalls: set[str],
) -> int:
    """D-10: count of stateful firewalls that see only one leg of the pair.

    A "one-legged" stateful firewall is one whose node_id appears on
    exactly one of (forward.hops, ret.hops) AND is in the
    ``stateful_firewalls`` set.
    """
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    one_legged = (fwd_nodes ^ ret_nodes) & stateful_firewalls
    return len(one_legged)


def _attr(obj: Any, name: str) -> Any:
    """Read ``name`` from ``obj`` whether attribute (object) or key (dict)."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
