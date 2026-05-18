"""NetFlow correlation — endpoint-only match (v1.1) + divergence emit (D-07).

v1.1 scope (RESEARCH Q2 RESOLVED): endpoint-only correlation. Edge-hop
comparison is deferred to v1.2 alongside the Go agent emitter extension
and the ``netflow_records`` column migration. See the ``# TODO(v1.2)``
marker in ``matches()`` for the integration point.

Pitfall 8: per-rule try/except around CIDR parsing for stored TEXT cidrs.

Public functions:
    matches(flow, path) -> bool
    emit_divergence(observed_flows, computed_paths) -> list[dict]
"""
from __future__ import annotations

import ipaddress
from typing import Any

import structlog
from infracanvas.graph.models import NetworkPath

_log = structlog.get_logger("app.security.pathcompute.correlate")


def _in_cidr(ip: str, cidr: str) -> bool:
    """Check whether ``ip`` is contained in ``cidr``.

    Per Pitfall 8 (firewall_rules.src_cidr is TEXT, not INET): wrap parse
    in try/except so a malformed stored CIDR returns ``False`` and is
    skipped — does NOT crash the whole site's compute.
    """
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except (ValueError, TypeError):
        return False


def matches(flow: dict[str, Any], path: NetworkPath) -> bool:
    """v1.1 endpoint-only correlation predicate.

    Compares only ``src_cidr`` / ``dst_cidr`` per RESEARCH Q2 RESOLVED.
    Returns True iff the flow's src/dst IPs both fall inside the path's
    source/destination CIDRs (read from ``path.evidence``) AND the path
    actually carries hops (an empty-hops path is not a real match candidate).
    """
    # TODO(v1.2): add edge-hop comparison once agent emits the exporter
    # ingress + egress field pair. When v1.2 lands: compare the flow's
    # ingress edge field to path.hops[0].interface_in and the egress edge
    # field to path.hops[-1].interface_out as a tighter match predicate.
    # v1.1 endpoint-only is acceptable per Warning 4.
    src_cidr = str(path.evidence.get("src_cidr", "0.0.0.0/0"))
    dst_cidr = str(path.evidence.get("dst_cidr", "0.0.0.0/0"))
    flow_src = str(flow.get("src_ip", ""))
    flow_dst = str(flow.get("dst_ip", ""))
    if not _in_cidr(flow_src, src_cidr):
        return False
    if not _in_cidr(flow_dst, dst_cidr):
        return False
    if not path.hops:
        return False
    return True


def emit_divergence(
    observed_flows: list[dict[str, Any]],
    computed_paths: list[NetworkPath],
) -> list[dict[str, Any]]:
    """D-07 — for each flow that matches NO computed path, emit a divergence dict.

    v1.1 endpoint-only; the synthesized ``observed_path`` dict carries only
    the endpoint signal (src_ip / dst_ip / bytes) because the Phase 10 agent
    does not yet emit edge-hop interface metadata (deferred to v1.2 per
    Warning 4).

    Returns:
        List of dicts shaped for ``PathDivergenceFindingORM`` insert downstream.
    """
    findings: list[dict[str, Any]] = []
    for flow in observed_flows:
        if any(matches(flow, p) for p in computed_paths):
            continue
        findings.append(
            {
                "observed_path": {
                    "src_ip": flow.get("src_ip"),
                    "dst_ip": flow.get("dst_ip"),
                    "bytes": flow.get("bytes"),
                },
                "evidence": {"reason": "no_computed_path_match"},
            }
        )
    return findings
