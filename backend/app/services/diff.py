"""Pure-function diff algorithm for ResourceGraph comparison (Plan 07-03, D-11).

``compute_diff(graph_a, graph_b, scan_a_id, scan_b_id)`` -> ``ResourceDiffResp``

Performs an outer-join on node IDs:

* present only in graph_b → ``added``
* present only in graph_a → ``removed``
* present in both, attributes differ → ``changed`` (with ``changed_fields``)
* present in both, attributes equal → ``unchanged``

Edge diff is set-based on ``(source, target, relationship)`` tuples — no
ordering assumed.

"Changed" follows D-12: any attribute key whose value differs (or whose
presence differs) marks the node as changed. This is the same definition
the drift overlay uses, so the dashboard's compare page can reuse drift
styling without translating between two diff vocabularies.

Designed for reuse by:

* ``GET /v1/scans/{a}/compare/{b}`` (Phase 7)
* the future CLI ``infracanvas diff`` command
* v1.2 PR-bot status checks (PRB-01)

The function is pure — no DB / R2 / network access — so it can be exercised
by fast unit tests without fixtures.
"""
from __future__ import annotations

from uuid import UUID

from infracanvas.graph.models import ResourceGraph

from app.schemas.scan import NodeDiff, ResourceDiffResp

# Node cap — keeps diff response sizes bounded (T-07-03-02). Each scan is
# already capped at 25 MB upstream (D-11), so most real diffs fit well
# under this limit; the cap is defence-in-depth for pathological inputs.
_MAX_NODES = 5000


def compute_diff(
    graph_a: ResourceGraph,
    graph_b: ResourceGraph,
    scan_a_id: UUID,
    scan_b_id: UUID,
) -> ResourceDiffResp:
    """Diff two ResourceGraph instances and return a ResourceDiffResp.

    Node diff: outer-join on ``node.id``.
    Edge diff: set diff on ``(source, target, relationship)`` tuples.

    Output is deterministic — node IDs are emitted in sorted order so the
    same input always produces byte-identical output (useful for caching
    and PR-bot status-check digests).
    """
    nodes_a: dict[str, dict] = {n.id: dict(n.attributes) for n in graph_a.nodes}
    nodes_b: dict[str, dict] = {n.id: dict(n.attributes) for n in graph_b.nodes}

    all_ids = set(nodes_a) | set(nodes_b)
    node_diffs: list[NodeDiff] = []
    counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}

    for node_id in sorted(all_ids):
        in_a = node_id in nodes_a
        in_b = node_id in nodes_b

        if in_b and not in_a:
            counts["added"] += 1
            node_diffs.append(
                NodeDiff(
                    id=node_id,
                    kind="added",
                    before=None,
                    after=nodes_b[node_id],
                )
            )
        elif in_a and not in_b:
            counts["removed"] += 1
            node_diffs.append(
                NodeDiff(
                    id=node_id,
                    kind="removed",
                    before=nodes_a[node_id],
                    after=None,
                )
            )
        else:
            attrs_a = nodes_a[node_id]
            attrs_b = nodes_b[node_id]
            changed_fields = _diff_attrs(attrs_a, attrs_b)
            if changed_fields:
                counts["changed"] += 1
                node_diffs.append(
                    NodeDiff(
                        id=node_id,
                        kind="changed",
                        before=attrs_a,
                        after=attrs_b,
                        changed_fields=changed_fields,
                    )
                )
            else:
                counts["unchanged"] += 1
                node_diffs.append(
                    NodeDiff(
                        id=node_id,
                        kind="unchanged",
                        before=attrs_a,
                        after=attrs_b,
                    )
                )

    # Cap to prevent oversized responses (T-07-03-02).
    node_diffs = node_diffs[:_MAX_NODES]

    # Edge diff — set-based on (source, target, relationship) tuples.
    # ResourceGraph.edges is list[dict[str, str]] in production
    # (cli/infracanvas/graph/models.py) but unit tests may pass
    # SimpleNamespace objects with attribute access. _edge_field handles
    # both shapes uniformly.
    def edge_key(e: object) -> tuple[str, str, str]:
        return (
            _edge_field(e, "source"),
            _edge_field(e, "target"),
            _edge_field(e, "relationship"),
        )

    edges_a = {edge_key(e): e for e in graph_a.edges}
    edges_b = {edge_key(e): e for e in graph_b.edges}

    edges_added = [
        {
            "source": _edge_field(e, "source"),
            "target": _edge_field(e, "target"),
            "relationship": _edge_field(e, "relationship"),
        }
        for e in edges_b.values()
        if edge_key(e) not in edges_a
    ]
    edges_removed = [
        {
            "source": _edge_field(e, "source"),
            "target": _edge_field(e, "target"),
            "relationship": _edge_field(e, "relationship"),
        }
        for e in edges_a.values()
        if edge_key(e) not in edges_b
    ]

    return ResourceDiffResp(
        scan_a_id=scan_a_id,
        scan_b_id=scan_b_id,
        nodes=node_diffs,
        edges_added=edges_added,
        edges_removed=edges_removed,
        summary=counts,
    )


def _edge_field(edge: object, field: str) -> str:
    """Read ``source`` / ``target`` / ``relationship`` from an edge.

    Production graphs (``ResourceGraph.edges`` is ``list[dict[str, str]]``)
    use dict access; unit tests may use SimpleNamespace attribute access.
    Returns "" for a missing field — keeps tuple keys hashable.
    """
    if isinstance(edge, dict):
        return str(edge.get(field, ""))
    return str(getattr(edge, field, ""))


def _diff_attrs(attrs_a: dict, attrs_b: dict) -> list[str]:
    """Return the sorted list of attribute keys that differ between two dicts.

    A key is "different" if:

    * it is present in one dict but not the other, or
    * it is present in both but the values are not equal (``==`` comparison).

    Sorted output makes ``changed_fields`` deterministic for caching.
    """
    all_keys = set(attrs_a) | set(attrs_b)
    return [k for k in sorted(all_keys) if attrs_a.get(k) != attrs_b.get(k)]
