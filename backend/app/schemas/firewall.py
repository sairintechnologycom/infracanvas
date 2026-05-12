"""Pydantic schemas for firewall push + read endpoints (Phase 11).

Locked contracts consumed by both backend routes and the Go push client
(``agent/internal/push/types.go`` ``FirewallRulesPayload`` /
``FirewallNATPayload`` / ``FirewallObjectsPayload``). Any drift on either
side breaks the agent <-> backend contract — keep field names verbatim.

T-11-02-01: ``rules`` / ``nat_rules`` / ``objects`` bounded at 50000 to
prevent DoS via unbounded payload allocation. Higher than Phase 10's
10000 (T-10-02-06) because enterprise rule bases can legitimately exceed
10k.

D-15 forward-feed contract (DO NOT rename without coordinated Phase 12
update):

* ``FirewallRule``    — src_zone, dst_zone, src_cidr, dst_cidr, action,
                        protocol, ports, position
* ``FirewallNATRule`` — src_translation, dst_translation, interface_in,
                        interface_out
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FirewallRule(BaseModel):
    """A single access rule normalized for Phase 12 path computation.

    D-08 hybrid: normalized columns drive path-comp; ``raw_blob`` preserves
    the vendor-native rule shape for UI/audit.
    """

    position: int
    src_zone: str | None = None
    dst_zone: str | None = None
    src_cidr: str
    dst_cidr: str
    action: str  # 'permit'|'deny'|'accept'|'drop'
    protocol: str | None = None
    ports: str | None = None
    raw_blob: dict  # vendor-native (D-08 hybrid)


class FirewallNATRule(BaseModel):
    """A single NAT rule normalized for Phase 12 NAT_ASYMMETRY (REQ §ASY-02)."""

    position: int
    src_translation: str | None = None
    dst_translation: str | None = None
    interface_in: str | None = None
    interface_out: str | None = None
    raw_blob: dict


class FirewallObject(BaseModel):
    """A host/network/group/service object (D-09).

    ``kind`` is one of: ``host`` | ``network`` | ``group`` | ``service``.
    """

    kind: str
    name: str
    value: dict
    raw_blob: dict


class FirewallRulesPushBody(BaseModel):
    """Request body for ``POST /v1/agent/firewall-rules``.

    T-11-02-01: ``rules`` bounded at 50000.
    """

    site_id: str
    snapshot_id: str  # UUIDv4 minted by agent (RESEARCH Pattern 2)
    firewall_id: str
    vendor: str  # 'cisco-asa'|'cisco-fmc'|'checkpoint'
    source: str  # 'asa-rest'|'asa-ssh'|'fmc'|'checkpoint'|'checkpoint-import'
    snapshot_ts: str  # ISO 8601
    rules: list[FirewallRule] = Field(..., max_length=50000)


class FirewallNATPushBody(BaseModel):
    """Request body for ``POST /v1/agent/firewall-nat``.

    T-11-02-01: ``nat_rules`` bounded at 50000.
    """

    site_id: str
    snapshot_id: str
    firewall_id: str
    vendor: str
    source: str
    snapshot_ts: str
    nat_rules: list[FirewallNATRule] = Field(..., max_length=50000)


class FirewallObjectsPushBody(BaseModel):
    """Request body for ``POST /v1/agent/firewall-objects``.

    T-11-02-01: ``objects`` bounded at 50000.
    """

    site_id: str
    snapshot_id: str
    firewall_id: str
    vendor: str
    source: str
    snapshot_ts: str
    objects: list[FirewallObject] = Field(..., max_length=50000)
