"""Phase 12 PTH-03 — NetFlow correlation tests (D-05 endpoint-only v1.1).

GREEN after Plan 12-05 lands ``app.security.pathcompute.correlate``.

Per Q2 RESOLVED in 12-RESEARCH.md: v1.1 ships endpoint-only matching;
edge-hop interface comparison is deferred to v1.2.
"""
from __future__ import annotations

from infracanvas.graph.models import NetworkPath, PathHop

from app.security.pathcompute.correlate import emit_divergence, matches


def _mk_path(src_cidr: str, dst_cidr: str, hops: list[str]) -> NetworkPath:
    return NetworkPath(
        id=f"p-{src_cidr}-{dst_cidr}",
        source_node_id="src",
        dest_node_id="dst",
        direction="forward",
        hops=[PathHop(hop_index=i, node_id=n) for i, n in enumerate(hops)],
        evidence={"src_cidr": src_cidr, "dst_cidr": dst_cidr},
    )


def test_endpoint_only_match_v1_1() -> None:
    """D-05 v1.1 endpoint-only: flow whose src/dst fall in path CIDRs → matches."""
    flow = {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", "bytes": 1000}
    path = _mk_path("10.1.0.0/24", "10.2.0.0/24", ["r1", "r2"])
    assert matches(flow, path) is True


def test_endpoint_only_no_match_when_outside_cidr() -> None:
    """Flow whose src/dst do NOT fall in path CIDRs → does not match."""
    flow = {"src_ip": "192.0.2.5", "dst_ip": "10.2.0.5", "bytes": 1000}
    path = _mk_path("10.1.0.0/24", "10.2.0.0/24", ["r1", "r2"])
    assert matches(flow, path) is False


def test_divergence_emitted() -> None:
    """D-07: observed flow that matches no computed path → emit path_divergence."""
    flow = {"src_ip": "10.99.0.5", "dst_ip": "10.99.0.6", "bytes": 500}
    paths = [_mk_path("10.1.0.0/24", "10.2.0.0/24", ["r1", "r2"])]
    findings = emit_divergence([flow], paths)
    assert len(findings) == 1
    assert findings[0]["observed_path"]["src_ip"] == "10.99.0.5"


def test_divergence_skipped_when_match_found() -> None:
    """Flow that matches at least one path → no divergence emitted."""
    flow = {"src_ip": "10.1.0.5", "dst_ip": "10.2.0.5", "bytes": 1000}
    paths = [_mk_path("10.1.0.0/24", "10.2.0.0/24", ["r1", "r2"])]
    findings = emit_divergence([flow], paths)
    assert findings == []
