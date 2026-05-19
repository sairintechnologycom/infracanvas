"""Security rule evaluation engine."""

from __future__ import annotations

import re
from typing import Any

from infracanvas.graph.models import Finding, ResourceGraph, ResourceNode
from infracanvas.security.loader import load_rules
from infracanvas.security.models import SecurityRule

# Modern AWS provider pattern: S3 bucket configuration is split across sibling
# resources rather than inline attributes (the v4 deprecation). Without folding,
# rules like SEC-002 (S3 Bucket Missing Encryption) fire as false-positives on
# every bucket that uses the canonical aws_s3_bucket_server_side_encryption_*
# pattern. This map lists each companion → the synthetic attribute key it should
# project onto the parent bucket, plus the source attribute on the companion.
_S3_COMPANION_FOLD: dict[str, tuple[str, str]] = {
    "aws_s3_bucket_server_side_encryption_configuration": (
        "server_side_encryption_configuration", "rule",
    ),
    "aws_s3_bucket_versioning":          ("versioning_configuration", "versioning_configuration"),
    "aws_s3_bucket_logging":             ("logging", "target_bucket"),
    "aws_s3_bucket_acl":                 ("acl", "acl"),
    "aws_s3_bucket_public_access_block": ("public_access_block", "*"),
}

# Matches `${aws_s3_bucket.<name>.id}` (HCL ref) or bare `aws_s3_bucket.<name>`.
_BUCKET_REF_RE = re.compile(r"aws_s3_bucket\.([A-Za-z0-9_\-]+)")


def _bucket_target_name(companion_attrs: dict[str, Any]) -> str | None:
    """Return the referenced bucket's local name from a companion's `bucket` attr."""
    bucket_ref = companion_attrs.get("bucket")
    if not isinstance(bucket_ref, str):
        return None
    m = _BUCKET_REF_RE.search(bucket_ref)
    return m.group(1) if m else None


def _fold_s3_companions(graph: ResourceGraph) -> None:
    """Project companion-resource attributes onto their parent aws_s3_bucket.

    Mutates `graph.nodes` in place. Idempotent: re-running has no effect once
    folded keys exist on the parent. Falls back silently if the companion's
    `bucket` reference can't be resolved.
    """
    buckets_by_name: dict[str, ResourceNode] = {
        n.name: n for n in graph.nodes if n.type == "aws_s3_bucket"
    }
    if not buckets_by_name:
        return

    for node in graph.nodes:
        fold = _S3_COMPANION_FOLD.get(node.type)
        if fold is None:
            continue
        synthetic_key, source_key = fold
        target_name = _bucket_target_name(node.attributes) or node.name
        bucket = buckets_by_name.get(target_name)
        if bucket is None:
            continue
        if synthetic_key in bucket.attributes:
            continue  # already folded — preserve any inline value
        if source_key == "*":
            # PAB-style: project the whole companion attribute dict, minus the
            # `bucket` reference itself.
            payload = {k: v for k, v in node.attributes.items() if k != "bucket"}
            bucket.attributes[synthetic_key] = payload
        else:
            value = node.attributes.get(source_key)
            if value is not None:
                bucket.attributes[synthetic_key] = value


def evaluate_all(
    graph: ResourceGraph,
    policy_rules: list[SecurityRule] | None = None,
) -> ResourceGraph:
    """Run all security rules (and optional policy rules) against all nodes."""
    rules = load_rules()
    _fold_s3_companions(graph)

    for node in graph.nodes:
        for rule in rules:
            if node.type in rule.resource_types:
                finding = _evaluate_rule(rule, node, source="security")
                if finding:
                    node.findings.append(finding)

    if policy_rules:
        for node in graph.nodes:
            for rule in policy_rules:
                if node.type in rule.resource_types:
                    finding = _evaluate_rule(rule, node, source="policy")
                    if finding:
                        node.findings.append(finding)

    return graph


def _evaluate_rule(rule: SecurityRule, node: ResourceNode, source: str = "security") -> Finding | None:
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
                # Check raw, double-quote-unescaped, and Python-dict-repr forms.
                # jsonencode({...}) HCL gets parsed by python-hcl2 into a string
                # that uses single quotes and spaces around colons (Python repr).
                # We normalise to JSON style so rules can author needles in the
                # natural `"Action":"*"` form.
                target = str(condition.value)
                normalised = (
                    value.replace("'", '"')
                         .replace('": "', '":"')
                         .replace('": [', '":[')
                         .replace('": {', '":{')
                )
                matched = (
                    target in value
                    or target in value.replace("\\\"", "\"")
                    or target in normalised
                )
            elif isinstance(value, list):
                matched = condition.value in value
        case "not_starts_with":
            # Used by literal-secret detection: a Terraform variable or
            # function-call reference begins with `${`, a hardcoded literal
            # does not. `value` here is the raw attribute string.
            if isinstance(value, str):
                target = str(condition.value)
                matched = not value.startswith(target) and len(value) > 0
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
            source=source,
            framework_ids=rule.framework_ids,
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
