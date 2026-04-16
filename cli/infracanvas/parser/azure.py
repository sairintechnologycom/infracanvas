"""Normalize azurerm resource attributes for the InfraCanvas graph model."""

from __future__ import annotations

from typing import Any

# Azure grouping attributes — used for group determination in builder
AZURE_GROUP_ATTRS = ("resource_group_name", "virtual_network_name")


def normalize_azure_attrs(resource_type: str, attrs: dict[str, Any]) -> dict[str, Any]:
    """Map Azure-specific attribute names to InfraCanvas canonical form.

    Normalisation rules:
    - Azure uses 'location' instead of 'region' — map location -> region
    """
    normalized = dict(attrs)
    # Azure uses 'location' instead of 'region'
    if "location" in normalized and "region" not in normalized:
        normalized["region"] = normalized["location"]
    return normalized
