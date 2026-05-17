"""NET-010 / ASY-03 — stateful firewall sees only one leg of an asymmetric pair (D-11).

Python detector (NOT YAML rule) per Phase 12 D-11. The YAML rule engine
cannot express "compare two path objects" without materially expanding
operators for one rule — see Phase 12 RESEARCH §"Don't Hand-Roll".

Catalog integration: emits ``NetworkFinding`` with ``rule_id="NET-010"``
and ``source="network"`` so findings aggregate through the existing
pipeline (Phase 2 D-09 / Phase 3 D-12). The rules catalog YAML count
stays at 51 (this is a Python detector, not a YAML rule — see Pitfall 7).

Public function:
    detect_stateful_firewall_asymmetry(forward, ret, stateful_firewalls)
        -> list[NetworkFinding]
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkFinding, NetworkPath


def detect_stateful_firewall_asymmetry(
    forward: NetworkPath,
    ret: NetworkPath,
    stateful_firewalls: set[str],
) -> list[NetworkFinding]:
    """Fire NET-010 when a stateful firewall is on exactly one path leg.

    Args:
        forward: Computed forward-direction ``NetworkPath``.
        ret: Computed return-direction ``NetworkPath``.
        stateful_firewalls: Set of ``node_id`` values that perform stateful
            inspection (e.g., from FirewallRulesetSnapshot device list).

    Returns:
        One ``NetworkFinding`` per stateful firewall that appears on
        exactly one leg. Empty list when symmetric or no overlap.
    """
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    one_legged = (fwd_nodes ^ ret_nodes) & stateful_firewalls
    findings: list[NetworkFinding] = []

    # Source / dest IPs are best-effort attribution from path endpoints
    # (Plan 12-06 wires real flow endpoints; tests use empty defaults).
    src_ip = forward.hops[0].source_ip if forward.hops else ""
    dst_ip = forward.hops[-1].dest_ip if forward.hops else ""

    fwd_only = fwd_nodes - ret_nodes
    ret_only = ret_nodes - fwd_nodes

    for node_id in sorted(one_legged):
        seen_on = "forward" if node_id in fwd_only else "return"
        findings.append(
            NetworkFinding(
                source_ip=src_ip,
                dest_ip=dst_ip,
                protocol="",
                port=0,
                severity="high",  # type: ignore[arg-type]
                title=(
                    f"Stateful firewall {node_id} sees only one leg of "
                    f"asymmetric pair"
                ),
                description=(
                    f"Forward path {forward.id} and return path {ret.id} "
                    f"traverse different stateful firewalls. {node_id} will "
                    f"drop return traffic with no matching session entry."
                ),
                remediation=(
                    "Symmetrize routing so both legs traverse the same "
                    "stateful firewall, OR disable stateful inspection on "
                    "this asymmetric pair."
                ),
                rule_id="NET-010",
                source="network",
                path_id=forward.id,
                hop_id=node_id,
                evidence={
                    "forward_only": sorted(fwd_only),
                    "return_only": sorted(ret_only),
                    "node_seen_on": seen_on,
                },
            )
        )
    return findings
