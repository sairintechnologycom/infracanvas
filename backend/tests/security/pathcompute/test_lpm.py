"""Phase 12 — LPM (Longest-Prefix-Match) trie tests.

GREEN after Plan 12-05 lands ``app.security.pathcompute.lpm``.

Asserts:
  * test_lpm_lookup_returns_longest_prefix — /24 wins over /16 for nested CIDR.
  * test_lpm_ecmp_resolves_lex_lowest — D-08 deterministic ECMP tiebreak.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.security.pathcompute.lpm import build_trie, lookup


def _r(prefix: str, next_hop: str, metric: int = 100, as_path: str = "") -> SimpleNamespace:
    """Build a RouteRecord-like object with attribute access."""
    return SimpleNamespace(prefix=prefix, next_hop=next_hop, metric=metric, as_path=as_path)


def test_lpm_lookup_returns_longest_prefix() -> None:
    """LPM returns the /24 entry, not the encompassing /16."""
    routes = [
        _r("10.1.0.0/16", "router-A"),
        _r("10.1.2.0/24", "router-B"),
    ]
    trie = build_trie(routes)
    match = lookup(trie, "10.1.2.3")
    assert match is not None
    assert match["next_hop"] == "router-B"
    assert match["prefix"] == "10.1.2.0/24"


def test_lpm_ecmp_resolves_lex_lowest() -> None:
    """Pitfall 3 D-08: two routes for same prefix with same metric →
    pick lexicographically lowest ``next_hop`` (deterministic ECMP)."""
    routes = [
        _r("10.1.0.0/24", "router-Z", metric=100),
        _r("10.1.0.0/24", "router-A", metric=100),
    ]
    trie = build_trie(routes)
    match = lookup(trie, "10.1.0.5")
    assert match is not None
    assert match["next_hop"] == "router-A"  # lex-lowest wins


def test_lpm_lookup_returns_none_when_no_match() -> None:
    """No route covers the IP → returns None."""
    routes = [_r("10.1.0.0/24", "router-A")]
    trie = build_trie(routes)
    assert lookup(trie, "192.0.2.1") is None
