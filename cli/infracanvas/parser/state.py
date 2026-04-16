"""Parse Terraform .tfstate JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from infracanvas.graph.models import DriftStatus, ResourceGraph, ResourceNode


@dataclass
class StateResource:
    address: str  # e.g., "aws_vpc.main"
    resource_type: str
    name: str
    provider: str
    module: str
    attributes: dict[str, Any]
    instances: list[dict[str, Any]]


@dataclass
class ParsedState:
    version: int = 0
    terraform_version: str = ""
    resources: list[StateResource] = field(default_factory=list)


def parse_state_file(state_path: Path) -> ParsedState:
    """Parse a .tfstate JSON file and return structured data."""
    with open(state_path) as f:
        data = json.load(f)

    result = ParsedState(
        version=data.get("version", 0),
        terraform_version=data.get("terraform_version", ""),
    )

    for resource in data.get("resources", []):
        mode = resource.get("mode", "managed")
        if mode != "managed":
            continue

        rtype = resource.get("type", "")
        rname = resource.get("name", "")
        provider = resource.get("provider", "")
        module = resource.get("module", "")

        # Build address
        address = f"{rtype}.{rname}"
        if module:
            address = f"{module}.{address}"

        instances = resource.get("instances", [])
        # Use first instance attributes as the primary attributes
        attrs: dict[str, Any] = {}
        if instances:
            attrs = instances[0].get("attributes", {})

        result.resources.append(
            StateResource(
                address=address,
                resource_type=rtype,
                name=rname,
                provider=_extract_provider_name(provider),
                module=module,
                attributes=attrs,
                instances=instances,
            )
        )

    return result


def flag_shadow_resources(graph: ResourceGraph, state: ParsedState) -> None:
    """Flag resources present in state but absent from graph as shadow infrastructure.

    PRS-05: Resources in .tfstate but not in HCL are flagged as shadow infrastructure
    by appending ResourceNode entries with drift=DriftStatus.shadow.
    """
    graph_ids = {n.id for n in graph.nodes}
    for sr in state.resources:
        if sr.address not in graph_ids:
            graph.nodes.append(
                ResourceNode(
                    id=sr.address,
                    type=sr.resource_type,
                    name=sr.name,
                    provider=sr.provider,
                    attributes=sr.attributes,
                    drift=DriftStatus.shadow,
                )
            )


def _extract_provider_name(provider_str: str) -> str:
    """Extract short provider name from full provider path.

    e.g., 'provider["registry.terraform.io/hashicorp/aws"]' -> 'aws'
    """
    if "/" in provider_str:
        return provider_str.rstrip('"]').rsplit("/", 1)[-1]
    return provider_str
