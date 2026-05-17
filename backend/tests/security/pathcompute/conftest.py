"""Shared fixtures for Phase 12 path-compute tests.

Per Pitfall 9: import NetworkPath/PathHop/NetworkFinding from
cli/infracanvas/graph/models.py — do NOT redeclare. The cli package is
already a backend dep (``infracanvas @ file:../cli`` in pyproject.toml).

Helpers exposed:

* ``mk_route_record(prefix, next_hop, **kw)`` — RouteRecord-shaped dict (Pydantic
  schemas not yet authored at Wave 0; dict keeps stubs runnable).
* ``mk_flow(src_ip, dst_ip, **kw)`` — observed NetFlow record-shaped dict.
* ``mk_path(direction, hops, **kw)`` — Pydantic ``NetworkPath`` instance.
* ``mk_nat_rule(iface_in, iface_out, **kw)`` — NAT-rule-shaped dict mirroring
  Phase 11 ``firewall_nat_rules`` row.

Downstream Phase 12 waves (12-02 … 12-07) import these helpers from
``backend.tests.security.pathcompute.conftest`` — do not redeclare locally.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

# Lazy import: the ``infracanvas`` cli package is declared in backend/pyproject.toml
# as ``infracanvas @ file:../cli`` but may not be installed in every dev env at
# Wave 0. The Pydantic shapes are only needed by ``mk_path`` — defer the import
# so the conftest itself always loads (collection-RED, not collection-ERROR).
try:
    from infracanvas.graph.models import NetworkFinding, NetworkPath, PathHop  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover — Wave 0 dev-env tolerance
    NetworkFinding = NetworkPath = PathHop = None  # type: ignore[misc,assignment]


def mk_route_record(prefix: str, next_hop: str, **kw: Any) -> dict:
    """Build a RouteRecord-shaped dict (matches agent push payload shape).

    Per Phase 10 D-08, agent pushes routes with fields:
    prefix, next_hop, protocol, metric, as_path.
    """
    return {
        "prefix": prefix,
        "next_hop": next_hop,
        "protocol": kw.get("protocol", "bgp"),
        "metric": kw.get("metric", 100),
        "as_path": kw.get("as_path", ""),
        "device_host": kw.get("device_host", "router-1"),
    }


def mk_flow(src_ip: str, dst_ip: str, **kw: Any) -> dict:
    """Build a NetFlow record-shaped dict.

    Defaults use RFC1918 ranges only (T-12-01-01 mitigation).
    """
    return {
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": kw.get("src_port", 12345),
        "dst_port": kw.get("dst_port", 443),
        "protocol": kw.get("protocol", 6),
        "bytes": kw.get("bytes", 1000),
        "packets": kw.get("packets", 1),
        "exporter": kw.get("exporter", "router-1"),
        "input_iface": kw.get("input_iface", "eth0"),
        "output_iface": kw.get("output_iface", "eth1"),
    }


def mk_path(direction: str, hops: "list[PathHop]", **kw: Any) -> "NetworkPath":
    """Build a Pydantic ``NetworkPath`` instance (shape per
    cli/infracanvas/graph/models.py).

    Requires the ``infracanvas`` cli package to be importable.
    Raises ``pytest.skip`` if the package is unavailable (Wave 0 dev-env
    tolerance — downstream waves install via ``pip install -e ../cli``).
    """
    if NetworkPath is None:  # type: ignore[truthy-bool]
        pytest.skip("infracanvas cli package not installed in backend env")
    return NetworkPath(  # type: ignore[misc]
        id=kw.get("id", f"path-{direction}-test"),
        source_node_id=kw.get("source_node_id", "src-node"),
        dest_node_id=kw.get("dest_node_id", "dst-node"),
        direction=direction,  # type: ignore[arg-type]
        hops=hops,
        evidence=kw.get("evidence", {}),
    )


def mk_nat_rule(iface_in: str, iface_out: str, **kw: Any) -> dict:
    """Build a NAT-rule-shaped dict (matches Phase 11 firewall_nat_rules row)."""
    return {
        "interface_in": iface_in,
        "interface_out": iface_out,
        "src_translation": kw.get("src_translation", None),
        "dst_translation": kw.get("dst_translation", None),
        "firewall_id": kw.get("firewall_id", "fw-a"),
    }


@pytest.fixture
def now_utc() -> datetime:
    """Return the current UTC timestamp (tz-aware)."""
    return datetime.now(timezone.utc)
