"""Phase 12 D-11 — NET-010 Python detector tests.

Per Pitfall 6: NET-010 is a Python detector (this file), NOT a YAML rule.
The existing reservation test ``test_net_010_reserved_for_phase_3b`` at
``cli/tests/test_flowmap_network_rules.py:71`` STAYS as-is — it asserts the
YAML catalog does not contain NET-010 (correct per D-11). THIS file asserts
the Python module emits ``NetworkFinding`` objects with ``rule_id="NET-010"``
through the existing aggregation pipeline (Phase 2 D-09 / Phase 3 D-12).

Plan 12-05 lands ``cli/infracanvas/security/network/net_010.py`` and flips
these tests GREEN.
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkPath, PathHop
from infracanvas.security.network.net_010 import detect_stateful_firewall_asymmetry


def _mk_hop(hop_index: int, node_id: str) -> PathHop:
    return PathHop(hop_index=hop_index, node_id=node_id)


def _mk_path(direction: str, node_ids: list[str], path_id: str = "p1") -> NetworkPath:
    return NetworkPath(
        id=path_id,
        source_node_id=node_ids[0] if node_ids else "src",
        dest_node_id=node_ids[-1] if node_ids else "dst",
        direction=direction,
        hops=[_mk_hop(i, n) for i, n in enumerate(node_ids)],
        evidence={},
    )


def test_net_010_python_detector_module_exists() -> None:
    """D-11 — Python detector under cli/infracanvas/security/network/net_010.py."""
    assert callable(detect_stateful_firewall_asymmetry)


def test_net_010_emits_finding_when_stateful_firewall_one_legged() -> None:
    """D-11 — fires when a stateful firewall sees only one leg of an
    asymmetric pair.

    Asserts catalog integration: every finding has rule_id="NET-010" and
    source="network" so the existing Phase 2 D-09 / Phase 3 D-12
    aggregation pipeline picks it up.
    """
    forward = _mk_path("forward", ["router-1", "fw-a", "router-2"], path_id="fwd-1")
    ret = _mk_path("return", ["router-1", "fw-b", "router-2"], path_id="ret-1")
    findings = detect_stateful_firewall_asymmetry(forward, ret, {"fw-a", "fw-b"})
    assert len(findings) >= 2
    assert all(f.rule_id == "NET-010" for f in findings)
    assert all(f.source == "network" for f in findings)


def test_net_010_symmetric_pair_returns_empty() -> None:
    """Symmetric pair (identical hop sets) → detector returns []."""
    forward = _mk_path("forward", ["router-1", "fw-a", "router-2"])
    ret = _mk_path("return", ["router-1", "fw-a", "router-2"])
    findings = detect_stateful_firewall_asymmetry(forward, ret, {"fw-a"})
    assert findings == []


def test_net_010_only_stateful_firewalls_trigger() -> None:
    """Asymmetry on non-stateful nodes (plain routers) does NOT fire."""
    forward = _mk_path("forward", ["router-1", "router-x", "router-2"])
    ret = _mk_path("return", ["router-1", "router-y", "router-2"])
    # The asymmetric nodes (router-x, router-y) are not in the
    # stateful_firewalls set — no finding emitted.
    findings = detect_stateful_firewall_asymmetry(forward, ret, {"fw-a"})
    assert findings == []
