"""Security rule data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from infracanvas.graph.models import Severity


@dataclass
class RuleCondition:
    attribute: str
    operator: str  # equals, not_equals, in, not_in, exists, not_exists, contains, matches_cidr
    values: list[Any] = field(default_factory=list)
    value: Any = None


@dataclass
class SecurityRule:
    id: str
    title: str
    severity: Severity
    resource_types: list[str]
    condition: RuleCondition
    remediation: str
    description: str
    framework_ids: list[str] = field(default_factory=list)
