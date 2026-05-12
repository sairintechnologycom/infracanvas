"""Wave 0 RED test stubs for Phase 11 firewall Pydantic schemas.

Collection-RED until Plan 11-04 lands ``app.schemas.firewall``.

Locks the following load-bearing schema contracts:
- T-11-04-01: ``rules`` list bounded at 50000 to prevent DoS
- D-08 hybrid: FirewallRule has normalized columns AND raw_blob
- D-15 forward-feed: FirewallNATRule normalized for Phase 12 path comp
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# T-11-04-01 — payload bound on rules list (Pattern D, mirrors T-10-02-06)
# ---------------------------------------------------------------------------


def test_firewall_rules_push_body_max_length() -> None:
    """T-11-04-01: instantiating with >50000 rules raises ValidationError.

    Higher bound than Phase 10's 10000 because enterprise firewall rule
    bases can legitimately exceed 10k. Documented bound prevents
    unbounded memory allocation on the ingest path.
    """
    from pydantic import ValidationError

    from app.schemas.firewall import FirewallRule, FirewallRulesPushBody

    rule = FirewallRule(
        position=1,
        src_cidr="0.0.0.0/0",
        dst_cidr="10.0.0.0/24",
        action="permit",
        raw_blob={},
    )
    with pytest.raises(ValidationError):
        FirewallRulesPushBody(
            site_id="00000000-0000-0000-0000-000000000001",
            snapshot_id="00000000-0000-0000-0000-0000000000aa",
            firewall_id="asa-edge-01",
            vendor="cisco-asa",
            source="asa-rest",
            snapshot_ts="2026-05-12T07:00:00Z",
            rules=[rule] * 50001,  # T-11-04-01: max_length=50000
        )


# ---------------------------------------------------------------------------
# D-08 — hybrid normalized + raw_blob schema
# ---------------------------------------------------------------------------


def test_firewall_rule_hybrid_shape() -> None:
    """D-08: FirewallRule has BOTH normalized columns AND raw_blob.

    Normalized columns drive Phase 12 path computation. raw_blob preserves
    vendor-native rule for UI/audit. Renaming any normalized column
    breaks Phase 12; locking the names here is intentional.
    """
    from app.schemas.firewall import FirewallRule

    rule = FirewallRule(
        position=1,
        src_zone="outside",
        dst_zone="dmz",
        src_cidr="0.0.0.0/0",
        dst_cidr="10.1.1.10/32",
        action="permit",
        protocol="tcp",
        ports="80,443",
        raw_blob={"vendor": "cisco-asa", "ruleId": 268435457},
    )
    # Normalized columns
    assert rule.position == 1
    assert rule.src_cidr == "0.0.0.0/0"
    assert rule.dst_cidr == "10.1.1.10/32"
    assert rule.action == "permit"
    assert rule.protocol == "tcp"
    assert rule.ports == "80,443"
    assert rule.src_zone == "outside"
    assert rule.dst_zone == "dmz"
    # Vendor-native side car
    assert rule.raw_blob == {"vendor": "cisco-asa", "ruleId": 268435457}


# ---------------------------------------------------------------------------
# D-15 — NAT normalized columns Phase 12 reads
# ---------------------------------------------------------------------------


def test_firewall_nat_push_body_normalized_columns() -> None:
    """D-15: FirewallNATRule exposes the normalized columns Phase 12 reads.

    Phase 12's NAT_ASYMMETRY classifier (REQUIREMENTS §ASY-02) consumes:
    src_translation, dst_translation, interface_in, interface_out.
    """
    from app.schemas.firewall import FirewallNATPushBody, FirewallNATRule

    nat = FirewallNATRule(
        position=1,
        src_translation="10.1.1.10 -> 203.0.113.10",
        dst_translation=None,
        interface_in="inside",
        interface_out="outside",
        raw_blob={"vendor": "cisco-asa", "objectId": "nat-rule-1"},
    )
    body = FirewallNATPushBody(
        site_id="00000000-0000-0000-0000-000000000001",
        snapshot_id="00000000-0000-0000-0000-0000000000aa",
        firewall_id="asa-edge-01",
        vendor="cisco-asa",
        source="asa-rest",
        snapshot_ts="2026-05-12T07:00:00Z",
        nat_rules=[nat],
    )
    assert body.nat_rules[0].src_translation == "10.1.1.10 -> 203.0.113.10"
    assert body.nat_rules[0].interface_in == "inside"
    assert body.nat_rules[0].interface_out == "outside"


# ---------------------------------------------------------------------------
# D-09 — objects table kind enum
# ---------------------------------------------------------------------------


def test_firewall_objects_push_body_kind_enum() -> None:
    """D-09: FirewallObject.kind is constrained to host|network|group|service."""
    from app.schemas.firewall import FirewallObject, FirewallObjectsPushBody

    obj_host = FirewallObject(
        name="web-server",
        kind="host",
        value={"ip": "10.1.1.10"},
        raw_blob={},
    )
    obj_net = FirewallObject(
        name="dmz-net",
        kind="network",
        value={"cidr": "10.2.0.0/16"},
        raw_blob={},
    )
    obj_group = FirewallObject(
        name="DMZ-NETS",
        kind="group",
        value={"members": ["web-server", "dmz-net"]},
        raw_blob={},
    )
    obj_svc = FirewallObject(
        name="WEB-SVC",
        kind="service",
        value={"protocol": "tcp", "ports": "80,443"},
        raw_blob={},
    )
    body = FirewallObjectsPushBody(
        site_id="00000000-0000-0000-0000-000000000001",
        snapshot_id="00000000-0000-0000-0000-0000000000aa",
        firewall_id="asa-edge-01",
        vendor="cisco-asa",
        source="asa-rest",
        snapshot_ts="2026-05-12T07:00:00Z",
        objects=[obj_host, obj_net, obj_group, obj_svc],
    )
    assert {o.kind for o in body.objects} == {"host", "network", "group", "service"}
