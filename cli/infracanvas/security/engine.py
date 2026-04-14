"""Security rule evaluation engine."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from infracanvas.graph.models import Finding, ResourceGraph, ResourceNode, Severity
from infracanvas.security.loader import load_rules
from infracanvas.security.models import SecurityRule


def evaluate_all(graph: ResourceGraph) -> ResourceGraph:
    """Run all security rules against all nodes in the graph."""
    rules = load_rules()

    for node in graph.nodes:
        for rule in rules:
            if node.type in rule.resource_types:
                finding = _evaluate_rule(rule, node)
                if finding:
                    node.findings.append(finding)

    return graph


def _evaluate_rule(rule: SecurityRule, node: ResourceNode) -> Finding | None:
    """Evaluate a single rule against a resource node."""
    attrs = node.attributes
    condition = rule.condition
    attr_name = condition.attribute

    # Handle nested attribute access (e.g., "ingress.cidr_blocks")
    value = _get_nested_attr(attrs, attr_name)

    matched = False
    evidence_value: Any = value

    match condition.operator:
        case "equals":
            matched = value == condition.value
        case "not_equals":
            matched = value != condition.value and value is not None
        case "in":
            matched = value in condition.values
        case "not_in":
            matched = value is not None and value not in condition.values
        case "exists":
            matched = value is not None
        case "not_exists":
            matched = value is None
        case "contains":
            if isinstance(value, str):
                # Check both the raw value and unescaped version
                target = str(condition.value)
                matched = target in value or target in value.replace("\\\"", "\"")
            elif isinstance(value, list):
                matched = condition.value in value
        case "matches_cidr":
            matched = _check_cidr_match(value, condition.values)
        case "list_contains_cidr":
            matched = _check_list_contains_cidr(attrs, attr_name, condition.values)
        case "any_equals":
            matched = _check_any_equals(attrs, attr_name, condition.value)

    if matched:
        return Finding(
            rule_id=rule.id,
            severity=rule.severity,
            title=rule.title,
            description=rule.description,
            remediation=rule.remediation,
            evidence={"attribute": attr_name, "value": _sanitize_evidence(evidence_value)},
        )
    return None


def _get_nested_attr(attrs: dict[str, Any], path: str) -> Any:
    """Get a value from nested attributes using dot notation."""
    parts = path.split(".")
    current: Any = attrs
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and current:
            # For lists, check first element
            current = current[0].get(part) if isinstance(current[0], dict) else None
        else:
            return None
    return current


def _check_cidr_match(value: Any, cidrs: list[Any]) -> bool:
    """Check if value matches any of the given CIDR patterns."""
    if value is None:
        return False
    str_val = str(value)
    return str_val in [str(c) for c in cidrs]


def _check_list_contains_cidr(attrs: dict[str, Any], attr_path: str, cidrs: list[Any]) -> bool:
    """Check if any item in a list attribute contains the target CIDRs.

    Handles structures like ingress blocks with cidr_blocks lists.
    """
    parts = attr_path.split(".")
    if len(parts) < 2:
        return False

    list_attr = parts[0]
    inner_attr = ".".join(parts[1:])

    items = attrs.get(list_attr, [])
    if not isinstance(items, list):
        return False

    target_cidrs = {str(c) for c in cidrs}

    for item in items:
        if isinstance(item, dict):
            inner_val = _get_nested_attr(item, inner_attr)
            if isinstance(inner_val, list):
                for v in inner_val:
                    if str(v) in target_cidrs:
                        return True
            elif isinstance(inner_val, str) and inner_val in target_cidrs:
                return True

    return False


def _check_any_equals(attrs: dict[str, Any], attr_path: str, target_value: Any) -> bool:
    """Check if any item in a list attribute has a field equal to target."""
    parts = attr_path.split(".")
    if len(parts) < 2:
        return False

    list_attr = parts[0]
    inner_attr = ".".join(parts[1:])

    items = attrs.get(list_attr, [])
    if not isinstance(items, list):
        return False

    for item in items:
        if isinstance(item, dict):
            val = _get_nested_attr(item, inner_attr)
            if str(val) == str(target_value):
                return True

    return False


def _sanitize_evidence(value: Any) -> Any:
    """Sanitize evidence value for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize_evidence(v) for v in value[:10]]
    if isinstance(value, dict):
        return {k: _sanitize_evidence(v) for k, v in list(value.items())[:10]}
    return str(value)
