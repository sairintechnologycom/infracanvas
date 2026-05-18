"""Phase 12 D-04 — scheduled + on-demand path-compute taskiq job.

Pipeline (per site):

  1. Fetch latest route snapshot per device under RLS
  2. Fetch NetFlow rolling 1h window (D-06; v1.1 endpoint-only fields per
     Warning 4 — no exporter_interface / exit_interface)
  3. Top-K pair selection by byte volume (D-03; K from PATH_COMPUTE_TOP_K
     env, default 200)
  4. Fetch latest firewall snapshot + NAT rules (Phase 11 contract)
  5. For each pair: compute_pair → asymmetry detect → classify (with
     PER-LEG device routes per Warning 5) → impact → NET-010 detector
  6. Persist computed_paths (snapshot-per-pull D-16)
  7. Reconcile asymmetry_findings + path_divergence_findings (D-16)
  8. NFN-02 Slack alerts on transitions only (D-13 + Pitfall 4 flap
     suppression — fire on detection_count==2 or cause-changed only)

Cron: ``*/15 * * * *`` (D-04). On-demand via ``.kiq(on_demand=True)``
from ``backend/app/routes/paths.py`` POST ``/paths/recompute``
(Plan 12-03; Plan 12-06 removed the deploy-state try/except wrapper).

Warning 5 — classifier per-leg routes
-------------------------------------

``classify()`` receives the route table of the FORWARD leg's LAST hop as
``fwd_routes`` and the RETURN leg's LAST hop as ``ret_routes``. Without
this split, ``score_leak`` + ``score_local_pref`` degenerate to 0.0
because both inputs are identical, and only ``NAT_ASYMMETRY`` ever
fires. The ``_leg_routes`` helper enforces the per-leg split.

Warning 6 — NET-010 persistence
-------------------------------

Each ``NetworkFinding`` emitted by ``detect_stateful_firewall_asymmetry``
is persisted as a row in ``asymmetry_findings`` with ``cause='NET-010'``,
``cause_confidence=1.0`` and evidence carrying the detector's evidence
dict + ``src_cidr`` / ``dst_cidr`` keys for reconciliation. The
``ck_asymmetry_findings_cause`` CHECK constraint (migration 013) was
extended to admit 'NET-010' alongside the BGP / ROUTE / NAT / UNKNOWN
values. The Plan 12-03 ``GET /asymmetries`` API surfaces NET-010 rows
into the viewer Asymmetry tab without further code change.

Pitfall 4 — flap suppression
----------------------------

NFN-02 alerts only fire on transitions: a freshly-inserted finding sets
``detection_count=1`` and does NOT fire. The next recompute that sees
the same finding increments ``detection_count`` to 2 and fires the
alert. Subsequent unchanged recomputes do not re-fire. A ``cause``
change always re-fires (operator visibility).

Pattern G logging allowlist
---------------------------

Allowed structlog fields: ``team_id``, ``site_id``, ``pair_count``,
``computed_paths``, ``asymmetry_count``, ``divergence_count``,
``net_010_findings``, ``net_010_persisted``, ``slack_fired_count``,
``on_demand``. Never: ``src_ip`` / ``dst_ip`` / hop content / evidence
blobs.
"""
from __future__ import annotations

import ipaddress
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from infracanvas.security.network.net_010 import detect_stateful_firewall_asymmetry
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.notifications.slack import send_team_slack
from app.queue.broker import broker
from app.security.pathcompute.asymmetry import is_asymmetric
from app.security.pathcompute.classify import classify
from app.security.pathcompute.correlate import emit_divergence, matches
from app.security.pathcompute.impact import impact_bytes_per_sec, impact_firewall_count
from app.security.pathcompute.pair import compute_pair

_log = structlog.get_logger("app.tasks.path_compute")
_K_DEFAULT = int(os.environ.get("PATH_COMPUTE_TOP_K", "200"))
_NFN_02_BYTES_THRESHOLD = float(
    os.environ.get("NFN_02_ALERT_BYTES_PER_SEC_THRESHOLD", "1000000")
)

NFN_02_TEMPLATE = (
    "Asymmetric path detected — site {site_id}\n"
    "Pair: {src_cidr} -> {dst_cidr}\n"
    "Cause: {cause} (confidence {confidence:.0%})\n"
    "Impact: {bytes_per_sec:.0f} B/s · {firewall_count} stateful firewall(s)\n"
    "View: /sites/{site_id}/asymmetries/{finding_id}"
)


# --------------------------------------------------------------------------
# Module-level helpers (Task 1 portion of Plan 12-06)
# --------------------------------------------------------------------------


class _RouteRow:
    """In-memory route record wrapper — attribute access matches what the
    pathcompute LPM / classify modules expect (``prefix`` / ``next_hop`` /
    ``protocol`` / ``metric`` / ``as_path``)."""

    def __init__(self, **kw: Any) -> None:
        self.prefix = kw["prefix"]
        self.next_hop = kw["next_hop"]
        self.protocol = kw["protocol"]
        self.metric = int(kw["metric"]) if kw.get("metric") is not None else 0
        self.as_path = kw.get("as_path", "") or ""


class _NATRow:
    """In-memory NAT rule wrapper — attribute access matches what the NAT
    scorer expects (``interface_in`` / ``interface_out`` /
    ``src_translation`` / ``dst_translation``)."""

    def __init__(self, **kw: Any) -> None:
        self.interface_in = kw.get("interface_in")
        self.interface_out = kw.get("interface_out")
        self.src_translation = kw.get("src_translation")
        self.dst_translation = kw.get("dst_translation")


def _jsonify_hops(hops: list[Any]) -> str:
    """Serialise a list of PathHop (Pydantic v2) objects to a JSON string
    suitable for a ``jsonb`` column INSERT cast."""
    return json.dumps(
        [h.model_dump() if hasattr(h, "model_dump") else dict(h) for h in hops]
    )


def _json_dumps(obj: Any) -> str:
    """JSON encoder that falls back to ``str()`` for non-native types
    (UUID, datetime). Used for evidence + observed_path INSERTs."""
    return json.dumps(obj, default=str)


def _leg_routes(path: Any, route_snapshot: dict[str, list[Any]]) -> list[Any]:
    """Warning 5 — return the route table of the LAST hop of ``path``.

    The last hop is where the egress decision was made for that leg. If
    the hop's device is not in ``route_snapshot`` (the snapshot edge
    fell off the compute), return an empty list — the classify scorers
    handle empty inputs (every score collapses to 0.0). When both legs
    end on the same device (intra-DC asymmetry), ``fwd_routes`` and
    ``ret_routes`` are legitimately equal — that's a non-event for the
    BGP_LOCAL_PREF / ROUTE_LEAK scorers (no divergence), so NAT_ASYMMETRY
    wins or UNKNOWN fires (correct, by D-08 contract).
    """
    if not path.hops:
        return []
    last_node = path.hops[-1].node_id
    return route_snapshot.get(last_node, [])


# --------------------------------------------------------------------------
# Cron fan-out — D-04 every 15 minutes
# --------------------------------------------------------------------------


@broker.task(
    task_name="recompute_paths_all_sites",
    schedule=[{"cron": "*/15 * * * *"}],
)
async def recompute_paths_all_sites() -> dict[str, int]:
    """D-04 fan-out — enqueue per-site compute under each team's RLS context.

    Walks ``teams``, sets ``app.current_team_id`` GUC per team, lists
    that team's ``dc_sites`` (RLS-isolated), and enqueues
    ``recompute_paths_for_site.kiq(site_id=...)`` for each. Returns the
    total number of enqueued site tasks plus the number of teams
    scanned for observability.
    """
    sm = get_sessionmaker()
    enqueued = 0
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        team_ids = [str(row[0]) for row in team_rows]
    for team_id in team_ids:
        site_rows: list[Any]
        async with sm() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": team_id},
            )
            site_rows = (
                await session.execute(text("SELECT id FROM dc_sites"))
            ).all()
        for (site_id,) in site_rows:
            await recompute_paths_for_site.kiq(site_id=site_id)
            enqueued += 1
    _log.info(
        "path_recompute_fanout",
        sites_enqueued=enqueued,
        teams_scanned=len(team_ids),
    )
    return {"enqueued": enqueued, "teams_scanned": len(team_ids)}


# --------------------------------------------------------------------------
# Per-site compute — D-04 / D-08 / D-10 / D-11 / D-13 / D-16
# --------------------------------------------------------------------------


@broker.task(task_name="recompute_paths_for_site")
async def recompute_paths_for_site(
    site_id: UUID,
    *,
    on_demand: bool = False,
) -> dict[str, int]:
    """D-04 per-site compute pipeline.

    Fetches latest routes / NetFlows / firewall snapshot under the
    site's team RLS context, picks top-K NetFlow pairs by byte volume,
    computes forward + return paths, runs asymmetry + classify + impact
    + NET-010 detection, persists ``computed_paths`` (full-replace per
    pair per D-16), reconciles ``asymmetry_findings`` +
    ``path_divergence_findings`` (D-16), and fires NFN-02 Slack alerts
    on transitions (Pitfall 4 flap suppression).

    Args:
        site_id: ``dc_sites.id`` — RLS GUC derived from the row's
            ``team_id``.
        on_demand: True when called from POST /paths/recompute; False
            when called from the cron fan-out. Surfaced in the
            structlog summary for observability.

    Returns:
        Summary dict shaped per the Pattern G logging allowlist.
    """
    sm = get_sessionmaker()
    now = datetime.now(UTC)
    summary: dict[str, int] = {
        "pair_count": 0,
        "computed_paths": 0,
        "asymmetry_count": 0,
        "divergence_count": 0,
        "net_010_findings": 0,
        "net_010_persisted": 0,
        "slack_fired_count": 0,
    }

    # 1. Resolve team_id from dc_sites (PK lookup — table-scoped, not RLS-gated
    #    yet; the per-site transaction below sets the RLS GUC up-front).
    async with sm() as session:
        team_row = (
            await session.execute(
                text("SELECT team_id FROM dc_sites WHERE id = :sid"),
                {"sid": str(site_id)},
            )
        ).one_or_none()
    if team_row is None:
        _log.warning("path_compute_site_not_found", site_id=str(site_id))
        return summary
    team_id = str(team_row.team_id)

    async with sm() as session, session.begin():
        # Pattern B — RLS GUC set FIRST inside the transaction
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": team_id},
        )

        # 2. Latest routes per device (DISTINCT ON keyed on device_host)
        route_rows = (
            await session.execute(
                text(
                    "SELECT DISTINCT ON (device_host) device_host, prefix, "
                    "next_hop, protocol, metric, as_path "
                    "FROM route_records WHERE site_id = :sid "
                    "ORDER BY device_host, collected_at DESC"
                ),
                {"sid": str(site_id)},
            )
        ).mappings().all()
        route_snapshot: dict[str, list[Any]] = {}
        for r in route_rows:
            route_snapshot.setdefault(r["device_host"], []).append(
                _RouteRow(**{k: r[k] for k in r.keys() if k != "device_host"})
            )

        # 3. NetFlow rolling 1h window — Warning 4: endpoint-only columns.
        #    NO exporter_interface / exit_interface (v1.1 contract).
        flow_rows = (
            await session.execute(
                text(
                    "SELECT src_ip::text AS src_ip, dst_ip::text AS dst_ip, "
                    "src_port, dst_port, protocol, bytes, packets "
                    "FROM netflow_records "
                    "WHERE site_id = :sid "
                    "AND collected_at > NOW() - INTERVAL '1 hour'"
                ),
                {"sid": str(site_id)},
            )
        ).mappings().all()
        all_flows: list[dict[str, Any]] = [dict(r) for r in flow_rows]

        # 4. Top-K pairs by byte volume (D-03; CIDR /24 grouping per src/dst)
        pair_volume: dict[tuple[str, str], int] = {}
        for f in all_flows:
            try:
                s_cidr = str(
                    ipaddress.ip_network(f"{f['src_ip']}/24", strict=False)
                )
                d_cidr = str(
                    ipaddress.ip_network(f"{f['dst_ip']}/24", strict=False)
                )
            except (ValueError, TypeError):
                continue
            pair_volume[(s_cidr, d_cidr)] = pair_volume.get(
                (s_cidr, d_cidr), 0
            ) + int(f["bytes"] or 0)
        top_pairs = sorted(
            pair_volume.items(), key=lambda kv: -kv[1]
        )[:_K_DEFAULT]
        summary["pair_count"] = len(top_pairs)

        # 5. Latest firewall snapshot + NAT rules + stateful_firewalls set
        snap_rows = (
            await session.execute(
                text(
                    "SELECT DISTINCT ON (firewall_id) snapshot_id, "
                    "firewall_id, vendor "
                    "FROM firewall_ruleset_snapshots WHERE site_id = :sid "
                    "ORDER BY firewall_id, snapshot_ts DESC"
                ),
                {"sid": str(site_id)},
            )
        ).mappings().all()
        snapshot_ids = [r["snapshot_id"] for r in snap_rows]
        stateful_firewalls = {str(r["firewall_id"]) for r in snap_rows}
        nat_rules: list[Any] = []
        if snapshot_ids:
            nat_rows = (
                await session.execute(
                    text(
                        "SELECT interface_in, interface_out, src_translation, "
                        "dst_translation FROM firewall_nat_rules "
                        "WHERE snapshot_id = ANY(:sids)"
                    ),
                    {"sids": snapshot_ids},
                )
            ).mappings().all()
            nat_rules = [_NATRow(**dict(r)) for r in nat_rows]

        # 6. Per-pair compute → asymmetry → classify → impact → NET-010
        current_asymmetry_keys: set[tuple[str, str, str]] = set()
        current_net010_keys: set[tuple[str, str, str]] = set()

        for (src_cidr, dst_cidr), _vol in top_pairs:
            try:
                src_ip = str(next(ipaddress.ip_network(src_cidr).hosts()))
                dst_ip = str(next(ipaddress.ip_network(dst_cidr).hosts()))
            except (StopIteration, ValueError):
                continue
            fwd, ret = compute_pair(src_ip, dst_ip, route_snapshot)
            fwd.evidence["src_cidr"] = src_cidr
            fwd.evidence["dst_cidr"] = dst_cidr
            ret.evidence["src_cidr"] = dst_cidr
            ret.evidence["dst_cidr"] = src_cidr

            # Persist computed_paths — D-16 snapshot-per-pull (delete older
            # rows for this pair, then INSERT the freshly-computed pair).
            fwd_path_id = uuid.uuid4()
            ret_path_id = uuid.uuid4()
            await session.execute(
                text(
                    "DELETE FROM computed_paths "
                    "WHERE site_id = :sid AND pair_src_cidr = :s "
                    "AND pair_dst_cidr = :d "
                    "AND direction IN ('forward','return') "
                    "AND computed_at < :now"
                ),
                {
                    "sid": str(site_id),
                    "s": src_cidr,
                    "d": dst_cidr,
                    "now": now,
                },
            )
            await session.execute(
                text(
                    "INSERT INTO computed_paths (path_id, team_id, site_id, "
                    "pair_src_cidr, pair_dst_cidr, direction, hops, "
                    "match_evidence, computed_at) VALUES "
                    "(:pid, :tid, :sid, :s, :d, 'forward', "
                    ":hops::jsonb, :me::jsonb, :now), "
                    "(:pid2, :tid, :sid, :s, :d, 'return', "
                    ":hops2::jsonb, :me2::jsonb, :now)"
                ),
                {
                    "pid": str(fwd_path_id),
                    "pid2": str(ret_path_id),
                    "tid": team_id,
                    "sid": str(site_id),
                    "s": src_cidr,
                    "d": dst_cidr,
                    "hops": _jsonify_hops(fwd.hops),
                    "hops2": _jsonify_hops(ret.hops),
                    "me": "{}",
                    "me2": "{}",
                    "now": now,
                },
            )
            summary["computed_paths"] += 2

            if is_asymmetric(fwd, ret):
                summary["asymmetry_count"] += 1
                # Warning 5 — PER-LEG device routes (D-08 fully live)
                fwd_routes = _leg_routes(fwd, route_snapshot)
                ret_routes = _leg_routes(ret, route_snapshot)
                cause, confidence, evidence = classify(
                    fwd, ret, fwd_routes, ret_routes, nat_rules
                )
                matched_flows = [f for f in all_flows if matches(f, fwd)]
                bps = impact_bytes_per_sec(matched_flows, window_seconds=3600)
                fwc = impact_firewall_count(fwd, ret, stateful_firewalls)
                current_asymmetry_keys.add((str(site_id), src_cidr, dst_cidr))

                # Reconciliation — open finding lookup (exclude NET-010 rows
                # so the main cause + NET-010 cause families reconcile
                # independently per Warning 6).
                existing = (
                    await session.execute(
                        text(
                            "SELECT finding_id, cause, evidence "
                            "FROM asymmetry_findings "
                            "WHERE site_id = :sid "
                            "AND evidence->>'src_cidr' = :s "
                            "AND evidence->>'dst_cidr' = :d "
                            "AND cause != 'NET-010' "
                            "AND resolved_at IS NULL"
                        ),
                        {
                            "sid": str(site_id),
                            "s": src_cidr,
                            "d": dst_cidr,
                        },
                    )
                ).mappings().one_or_none()

                cause_changed = (
                    existing is not None and existing["cause"] != cause
                )

                if existing is None:
                    # Pitfall 4 — first detection: NO alert (flap suppression)
                    finding_id = uuid.uuid4()
                    evidence_with_keys = {
                        **evidence,
                        "src_cidr": src_cidr,
                        "dst_cidr": dst_cidr,
                        "detection_count": 1,
                    }
                    await session.execute(
                        text(
                            "INSERT INTO asymmetry_findings ("
                            "finding_id, team_id, site_id, "
                            "forward_path_id, return_path_id, "
                            "cause, cause_confidence, evidence, "
                            "impact_bytes_per_sec, impact_firewall_count, "
                            "first_seen_at, last_seen_at"
                            ") VALUES ("
                            ":fid, :tid, :sid, :fpid, :rpid, "
                            ":cause, :conf, :ev::jsonb, "
                            ":bps, :fwc, :now, :now"
                            ")"
                        ),
                        {
                            "fid": str(finding_id),
                            "tid": team_id,
                            "sid": str(site_id),
                            "fpid": str(fwd_path_id),
                            "rpid": str(ret_path_id),
                            "cause": cause,
                            "conf": confidence,
                            "ev": _json_dumps(evidence_with_keys),
                            "bps": bps,
                            "fwc": fwc,
                            "now": now,
                        },
                    )
                else:
                    prior_evidence = existing["evidence"] or {}
                    prior_count = int(prior_evidence.get("detection_count", 1))
                    new_count = prior_count + 1
                    new_evidence = {
                        **prior_evidence,
                        **evidence,
                        "src_cidr": src_cidr,
                        "dst_cidr": dst_cidr,
                        "detection_count": new_count,
                    }
                    await session.execute(
                        text(
                            "UPDATE asymmetry_findings SET "
                            "cause = :cause, cause_confidence = :conf, "
                            "evidence = :ev::jsonb, "
                            "impact_bytes_per_sec = :bps, "
                            "impact_firewall_count = :fwc, "
                            "last_seen_at = :now "
                            "WHERE finding_id = :fid"
                        ),
                        {
                            "cause": cause,
                            "conf": confidence,
                            "ev": _json_dumps(new_evidence),
                            "bps": bps,
                            "fwc": fwc,
                            "now": now,
                            "fid": str(existing["finding_id"]),
                        },
                    )
                    should_alert = (
                        (new_count == 2 or cause_changed)
                        and (fwc >= 1 or bps > _NFN_02_BYTES_THRESHOLD)
                    )
                    if should_alert:
                        try:
                            await send_team_slack(
                                team_id=team_id,
                                message=NFN_02_TEMPLATE.format(
                                    site_id=str(site_id),
                                    src_cidr=src_cidr,
                                    dst_cidr=dst_cidr,
                                    cause=cause,
                                    confidence=confidence,
                                    bytes_per_sec=bps,
                                    firewall_count=fwc,
                                    finding_id=str(existing["finding_id"]),
                                ),
                                log_ctx_key="path_compute",
                            )
                            summary["slack_fired_count"] += 1
                        except Exception as exc:  # noqa: BLE001
                            # send_team_slack already swallows + Sentry-
                            # captures; this is double-belt against an
                            # unexpected helper exception (e.g. DB connect
                            # error during the helper's RLS lookup).
                            _log.warning(
                                "path_compute.slack_unexpected",
                                error=repr(exc),
                            )

                # Warning 6 — NET-010 PERSISTENCE
                net_010_findings = detect_stateful_firewall_asymmetry(
                    fwd, ret, stateful_firewalls
                )
                summary["net_010_findings"] += len(net_010_findings)
                for net_finding in net_010_findings:
                    current_net010_keys.add(
                        (str(site_id), src_cidr, dst_cidr)
                    )
                    existing_net = (
                        await session.execute(
                            text(
                                "SELECT finding_id, evidence "
                                "FROM asymmetry_findings "
                                "WHERE site_id = :sid "
                                "AND evidence->>'src_cidr' = :s "
                                "AND evidence->>'dst_cidr' = :d "
                                "AND cause = 'NET-010' "
                                "AND resolved_at IS NULL"
                            ),
                            {
                                "sid": str(site_id),
                                "s": src_cidr,
                                "d": dst_cidr,
                            },
                        )
                    ).mappings().one_or_none()
                    net_evidence = {
                        **(net_finding.evidence or {}),
                        "src_cidr": src_cidr,
                        "dst_cidr": dst_cidr,
                        "hop_id": net_finding.hop_id,
                        "rule_id": "NET-010",
                    }
                    if existing_net is None:
                        await session.execute(
                            text(
                                "INSERT INTO asymmetry_findings ("
                                "finding_id, team_id, site_id, "
                                "forward_path_id, return_path_id, "
                                "cause, cause_confidence, evidence, "
                                "impact_bytes_per_sec, "
                                "impact_firewall_count, "
                                "first_seen_at, last_seen_at"
                                ") VALUES ("
                                ":fid, :tid, :sid, :fpid, :rpid, "
                                "'NET-010', 1.0, :ev::jsonb, "
                                ":bps, :fwc, :now, :now"
                                ")"
                            ),
                            {
                                "fid": str(uuid.uuid4()),
                                "tid": team_id,
                                "sid": str(site_id),
                                "fpid": str(fwd_path_id),
                                "rpid": str(ret_path_id),
                                "ev": _json_dumps(net_evidence),
                                "bps": bps,
                                "fwc": fwc,
                                "now": now,
                            },
                        )
                        summary["net_010_persisted"] += 1
                    else:
                        await session.execute(
                            text(
                                "UPDATE asymmetry_findings SET "
                                "evidence = :ev::jsonb, "
                                "impact_bytes_per_sec = :bps, "
                                "impact_firewall_count = :fwc, "
                                "last_seen_at = :now "
                                "WHERE finding_id = :fid"
                            ),
                            {
                                "ev": _json_dumps(net_evidence),
                                "bps": bps,
                                "fwc": fwc,
                                "now": now,
                                "fid": str(existing_net["finding_id"]),
                            },
                        )
            else:
                # SYMMETRIC pair — check for divergence against observed flows
                divergences = emit_divergence(all_flows, [fwd, ret])
                for d in divergences:
                    await session.execute(
                        text(
                            "INSERT INTO path_divergence_findings ("
                            "finding_id, team_id, site_id, "
                            "expected_path_id, observed_path, evidence, "
                            "first_seen_at, last_seen_at"
                            ") VALUES ("
                            ":fid, :tid, :sid, :epid, "
                            ":op::jsonb, :ev::jsonb, :now, :now"
                            ") ON CONFLICT DO NOTHING"
                        ),
                        {
                            "fid": str(uuid.uuid4()),
                            "tid": team_id,
                            "sid": str(site_id),
                            "epid": str(fwd_path_id),
                            "op": _json_dumps(d.get("observed_path", {})),
                            "ev": _json_dumps(d.get("evidence", {})),
                            "now": now,
                        },
                    )
                    summary["divergence_count"] += 1

        # 7. Resolve missing — UPDATE resolved_at on open findings whose key
        #    isn't in the current set. Two separate sweeps: main cause family
        #    and NET-010 family.
        asym_keys = [f"{s}|{d}" for (_, s, d) in current_asymmetry_keys]
        await session.execute(
            text(
                "UPDATE asymmetry_findings SET resolved_at = :now "
                "WHERE site_id = :sid "
                "AND resolved_at IS NULL "
                "AND cause != 'NET-010' "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM unnest(CAST(:keys AS text[])) AS k(v) "
                "  WHERE v = evidence->>'src_cidr' || '|' "
                "    || evidence->>'dst_cidr'"
                ")"
            ),
            {
                "now": now,
                "sid": str(site_id),
                "keys": asym_keys,
            },
        )
        net010_keys = [f"{s}|{d}" for (_, s, d) in current_net010_keys]
        await session.execute(
            text(
                "UPDATE asymmetry_findings SET resolved_at = :now "
                "WHERE site_id = :sid "
                "AND resolved_at IS NULL "
                "AND cause = 'NET-010' "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM unnest(CAST(:keys AS text[])) AS k(v) "
                "  WHERE v = evidence->>'src_cidr' || '|' "
                "    || evidence->>'dst_cidr'"
                ")"
            ),
            {
                "now": now,
                "sid": str(site_id),
                "keys": net010_keys,
            },
        )

    _log.info(
        "path_compute_complete",
        site_id=str(site_id),
        team_id=team_id,
        on_demand=on_demand,
        **summary,
    )
    return summary
