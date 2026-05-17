"""Hop-by-hop forward path expansion.

D-01 + PTH-01 — per-router LPM resolution; advance to next router until
destination CIDR is reached, max_hops exceeded, or loop detected.

Public function:
    compute_forward(src_ip, dst_ip, route_snapshot, max_hops=20) -> NetworkPath
"""
from __future__ import annotations

from typing import Any

import pytricia
import structlog
from infracanvas.graph.models import NetworkPath, PathHop

from app.security.pathcompute.lpm import build_trie, lookup

_log = structlog.get_logger("app.security.pathcompute.forward")


def compute_forward(
    src_ip: str,
    dst_ip: str,
    route_snapshot: dict[str, list[Any]],
    max_hops: int = 20,
) -> NetworkPath:
    """Compute the forward path from ``src_ip`` to ``dst_ip`` across the
    route snapshot.

    ``route_snapshot`` is keyed by ``device_host`` → list of RouteRecord-shaped
    objects. Hop expansion picks the next-hop router by LPM on each router's
    trie; stops when next_hop is None (destination reached), when ``max_hops``
    exceeded, or when a loop is detected (visited-set).

    Returns:
        A ``NetworkPath`` with ``direction='forward'``. Empty hops list when
        the src is unreachable from any device in the snapshot. The
        ``evidence`` dict carries ``src_cidr`` / ``dst_cidr`` / ``reason`` /
        ``hop_count`` for downstream correlation + diagnostics.
    """
    if not route_snapshot:
        return NetworkPath(
            id=f"fwd-empty-{src_ip}-{dst_ip}",
            source_node_id=src_ip,
            dest_node_id=dst_ip,
            direction="forward",
            hops=[],
            evidence={
                "src_cidr": src_ip,
                "dst_cidr": dst_ip,
                "reason": "empty_snapshot",
            },
        )

    tries = {host: build_trie(routes) for host, routes in route_snapshot.items()}
    hops: list[PathHop] = []
    visited: set[str] = set()
    current_host = _select_ingress(tries, src_ip)
    if current_host is None:
        return NetworkPath(
            id=f"fwd-unreachable-{src_ip}-{dst_ip}",
            source_node_id=src_ip,
            dest_node_id=dst_ip,
            direction="forward",
            hops=[],
            evidence={
                "src_cidr": src_ip,
                "dst_cidr": dst_ip,
                "reason": "no_ingress_device",
            },
        )

    hop_index = 0
    reason = "destination_reached"
    for _ in range(max_hops):
        if current_host in visited:
            _log.warning(
                "forward_loop_detected", host=current_host, src=src_ip, dst=dst_ip
            )
            reason = "loop_detected"
            break
        visited.add(current_host)
        result = lookup(tries[current_host], dst_ip)
        if result is None:
            reason = "no_route"
            break
        as_path_value = result["as_path"] or ""
        try:
            bgp_as_path = [int(tok) for tok in as_path_value.split() if tok.isdigit()]
        except (AttributeError, ValueError):
            bgp_as_path = []
        hop = PathHop(
            hop_index=hop_index,
            node_id=current_host,
            interface_out="",  # interface attribution requires firewall_rules join (Plan 12-06)
            interface_in="",
            next_hop=result["next_hop"],
            bgp_as_path=bgp_as_path,
            source_ip=src_ip,
            dest_ip=dst_ip,
            evidence={"metric": result["metric"], "matched_prefix": result["prefix"]},
        )
        hops.append(hop)
        hop_index += 1
        next_hop_host = result["next_hop"]
        if next_hop_host in tries and next_hop_host != current_host:
            current_host = next_hop_host
        else:
            # next_hop is a terminal device (destination CIDR reached) or
            # outside the snapshot — stop here.
            break
    else:
        reason = "max_hops_exceeded"

    return NetworkPath(
        id=f"fwd-{src_ip}-{dst_ip}",
        source_node_id=src_ip,
        dest_node_id=dst_ip,
        direction="forward",
        hops=hops,
        evidence={
            "src_cidr": src_ip,
            "dst_cidr": dst_ip,
            "hop_count": len(hops),
            "reason": reason,
        },
    )


def _select_ingress(
    tries: dict[str, pytricia.PyTricia],
    src_ip: str,
) -> str | None:
    """Pick the device whose trie covers ``src_ip`` with the longest prefix.

    On tie, lexicographically lowest host name (deterministic — Pitfall 3
    consistency).
    """
    best_host: str | None = None
    best_prefix_len = -1
    for host, t in sorted(tries.items()):
        if src_ip in t:
            try:
                prefix = t.get_key(src_ip)
                plen = int(prefix.split("/")[1]) if "/" in prefix else 32
            except (AttributeError, IndexError, ValueError):
                plen = 0
            if plen > best_prefix_len:
                best_prefix_len = plen
                best_host = host
    return best_host
