"""Load security rules from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from infracanvas.graph.models import Severity
from infracanvas.security.models import RuleCondition, SecurityRule

# Default rules directory within the package
RULES_DIR = Path(__file__).parent / "rules"


def load_rules(rules_dir: Path | None = None) -> list[SecurityRule]:
    """Load all security rules from YAML files in the given directory."""
    base_dir = rules_dir or RULES_DIR
    rules: list[SecurityRule] = []

    if not base_dir.is_dir():
        return rules

    for yaml_file in sorted(base_dir.rglob("*.yaml")):
        rules.extend(_load_rules_file(yaml_file))

    return rules


def _load_rules_file(path: Path) -> list[SecurityRule]:
    """Parse a single YAML rules file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    rules: list[SecurityRule] = []
    items = data if isinstance(data, list) else [data]

    for item in items:
        condition_data = item.get("condition", {})
        condition = RuleCondition(
            attribute=condition_data.get("attribute", ""),
            operator=condition_data.get("operator", "exists"),
            values=condition_data.get("values", []),
            value=condition_data.get("value"),
        )

        rule = SecurityRule(
            id=item["id"],
            title=item["title"],
            severity=Severity(item["severity"]),
            resource_types=item.get("resource_types", []),
            condition=condition,
            remediation=item.get("remediation", ""),
            description=item.get("description", ""),
        )
        rules.append(rule)

    return rules
