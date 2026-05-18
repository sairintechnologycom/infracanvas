"""Patricia trie wrapper for IP longest-prefix-match next-hop resolution.

D-01 — runs in-memory per recompute. pytricia provides the C-extension
Patricia tree; Python stdlib ``ipaddress`` lacks LPM (Pitfall: linear
``for net in routes: ip in net`` is O(n) per lookup and breaks at RIB
scale — see RESEARCH §Don't Hand-Roll §LPM).

ECMP determinism (Pitfall 3): on prefix collision (same prefix, multiple
sources), keep the entry with lexicographically lowest ``(metric, next_hop)``
tuple — mirrors ``vty show ip route`` line-order behavior so the same
flow always picks the same path. Prevents per-recompute flapping
asymmetry false-positives.

Public functions:
    build_trie(routes) -> PyTricia
    lookup(trie, ip) -> dict | None
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

import pytricia
import structlog

_log = structlog.get_logger("app.security.pathcompute.lpm")


class _RouteRecordLike(Protocol):
    """Structural type for any RouteRecord-shaped attribute carrier."""

    prefix: str
    next_hop: str
    metric: int
    as_path: str


def build_trie(routes: Iterable[_RouteRecordLike]) -> pytricia.PyTricia:
    """Build a Patricia trie keyed on CIDR prefix.

    On collision: keep lowest ``(metric, next_hop)`` tuple — deterministic
    ECMP per Pitfall 3. IPv6 deferred (32-bit trie).

    Args:
        routes: Iterable of RouteRecord-shaped objects (.prefix, .next_hop,
            .metric, .as_path attributes).

    Returns:
        ``pytricia.PyTricia`` storing the chosen (next_hop, metric, as_path,
        prefix) tuple per prefix.
    """
    trie: pytricia.PyTricia = pytricia.PyTricia(32)
    for r in routes:
        # ``pytricia.get`` performs LPM (returns the value of an ancestor
        # prefix on a miss). Use ``has_key`` for EXACT-prefix existence
        # so a /24 added after a /16 is not mistaken for a collision.
        if not trie.has_key(r.prefix):  # noqa: W601
            trie[r.prefix] = (r.next_hop, r.metric, r.as_path)
            continue
        ex_next, ex_metric, _ex_as_path = trie[r.prefix]
        if (r.metric, r.next_hop) < (ex_metric, ex_next):
            trie[r.prefix] = (r.next_hop, r.metric, r.as_path)
    return trie


def lookup(trie: pytricia.PyTricia, ip: str) -> dict[str, Any] | None:
    """LPM lookup. Returns a dict ``{prefix, next_hop, metric, as_path}``
    for the longest-matching prefix, or ``None`` if no route covers ``ip``.
    """
    if ip not in trie:
        return None
    next_hop, metric, as_path = trie[ip]
    matched_prefix = trie.get_key(ip)
    return {
        "prefix": matched_prefix,
        "next_hop": next_hop,
        "metric": metric,
        "as_path": as_path,
    }
