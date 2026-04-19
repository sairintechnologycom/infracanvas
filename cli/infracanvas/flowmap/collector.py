"""FlowMap cloud network collection orchestrator.

Entrypoint for --flowmap CLI flag. Dispatches to AWS and Azure collectors
(Plans 03-03 and 03-04) and surfaces credential warnings without hard-failing.

Requirements: FDM-02, AWS-01..03 (via aws.py), AZN-01..03 (via azure.py).
Decisions: CONTEXT.md D-03 (CLI owns cloud collection), D-04 (--flowmap flag on scan),
           D-05 (warn-on-missing-creds, never hard-fail).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from infracanvas.graph.models import ResourceGraph

if TYPE_CHECKING:
    from rich.console import Console


def _infer_region(graph: ResourceGraph, default: str = "us-east-1") -> str:
    """Infer the primary region from graph metadata or first tagged node.

    Mirrors main.py --shadow region-inference pattern exactly.
    """
    region = str(graph.metadata.get("region", "")) or default
    for node in graph.nodes:
        if node.region:
            return node.region
    return region


def run_flowmap_collection(
    graph: ResourceGraph,
    out: Console,
) -> ResourceGraph:
    """Run AWS + Azure network collection; warn on missing creds per cloud.

    Returns the input graph (mutated in place) with network topology nodes
    appended and, in Phase 3b, network_paths populated. 3a leaves
    network_paths and dc_sites empty by design (D-10).

    Per D-05: missing creds produce a yellow warning and continue. Never hard-fails.
    """
    region = _infer_region(graph)

    # AWS collection — Plan 03-03 provides aws.collect_aws_network
    try:
        from infracanvas.flowmap.aws import collect_aws_network
        graph = collect_aws_network(graph, region=region)
    except ImportError:
        # Plan 03-03 not yet landed; orchestrator safely no-ops
        pass
    except RuntimeError as exc:
        out.print(
            f"[yellow]Warning:[/yellow] {exc} "
            "Skipping AWS network collection."
        )

    # Azure collection — Plan 03-04 provides azure.collect_azure_network
    try:
        from infracanvas.flowmap.azure import collect_azure_network
        graph = collect_azure_network(graph)
    except ImportError:
        pass
    except RuntimeError as exc:
        out.print(
            f"[yellow]Warning:[/yellow] {exc} "
            "Skipping Azure network collection."
        )

    return graph
