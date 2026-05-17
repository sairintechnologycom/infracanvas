"""Phase 12 — LPM (Longest-Prefix-Match) trie tests.

RED until Plan 12-05 lands ``app.security.pathcompute.lpm``.

Asserts:
  * test_lpm_lookup_returns_longest_prefix — /24 wins over /16 for nested CIDR.
  * test_lpm_ecmp_resolves_lex_lowest — D-08 deterministic ECMP tiebreak.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.security.pathcompute.lpm")  # collection RED

from app.security.pathcompute.lpm import build_trie, lookup  # noqa: E402


def test_lpm_lookup_returns_longest_prefix() -> None:
    """LPM returns the /24 entry, not the encompassing /16."""
    pytest.skip("Plan 12-05 to implement build_trie + lookup")
    # routes = [
    #     {"prefix": "10.1.0.0/16", "next_hop": "router-A"},
    #     {"prefix": "10.1.2.0/24", "next_hop": "router-B"},
    # ]
    # trie = build_trie(routes)
    # match = lookup(trie, "10.1.2.3")
    # assert match["next_hop"] == "router-B"
    # assert match["prefix"] == "10.1.2.0/24"


def test_lpm_ecmp_resolves_lex_lowest() -> None:
    """Pitfall 3 D-08: two routes for same prefix with same metric →
    pick lexicographically lowest ``next_hop`` (deterministic ECMP)."""
    pytest.skip("Plan 12-05 to implement deterministic ECMP tiebreak")
    # routes = [
    #     {"prefix": "10.1.0.0/24", "next_hop": "router-Z", "metric": 100},
    #     {"prefix": "10.1.0.0/24", "next_hop": "router-A", "metric": 100},
    # ]
    # trie = build_trie(routes)
    # match = lookup(trie, "10.1.0.5")
    # assert match["next_hop"] == "router-A"  # lex-lowest wins
