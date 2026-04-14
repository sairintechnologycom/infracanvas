"""Parse Terraform plan JSON (terraform show -json) output."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from infracanvas.graph.models import AttributeChange, DriftStatus


ACTION_MAP: dict[tuple[str, ...], DriftStatus] = {
    ("no-op",): DriftStatus.unchanged,
    ("create",): DriftStatus.added,
    ("delete",): DriftStatus.deleted,
    ("update",): DriftStatus.changed,
    ("delete", "create"): DriftStatus.changed,
    ("create", "delete"): DriftStatus.changed,
}


@dataclass
class PlanChange:
    resource_address: str
    resource_type: str
    resource_name: str
    action: DriftStatus
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    attribute_changes: list[AttributeChange] = field(default_factory=list)


class PlanReader:
    """Parse terraform show -json plan output into PlanChange objects."""

    def read(self, plan_path: Path) -> list[PlanChange]:
        """Read a plan JSON file and return a list of changes."""
        data = json.loads(plan_path.read_text())
        return self.parse(data)

    def parse(self, data: dict[str, Any]) -> list[PlanChange]:
        """Parse plan JSON data dict into PlanChange objects."""
        changes: list[PlanChange] = []

        resource_changes = data.get("resource_changes", [])
        for rc in resource_changes:
            change = self._parse_resource_change(rc)
            if change:
                changes.append(change)

        return changes

    def _parse_resource_change(self, rc: dict[str, Any]) -> PlanChange | None:
        """Parse a single resource_changes entry."""
        change_block = rc.get("change", {})
        actions = change_block.get("actions", [])

        action_key = tuple(actions)
        drift_status = ACTION_MAP.get(action_key, DriftStatus.unchanged)

        address = rc.get("address", "")
        rtype = rc.get("type", "")
        rname = rc.get("name", "")

        before = change_block.get("before") or {}
        after = change_block.get("after") or {}
        before_sensitive = change_block.get("before_sensitive") or {}
        after_sensitive = change_block.get("after_sensitive") or {}

        attr_changes = self._diff_attributes(before, after, before_sensitive, after_sensitive)

        return PlanChange(
            resource_address=address,
            resource_type=rtype,
            resource_name=rname,
            action=drift_status,
            before=before,
            after=after,
            attribute_changes=attr_changes,
        )

    def _diff_attributes(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
        before_sensitive: dict[str, Any] | bool,
        after_sensitive: dict[str, Any] | bool,
    ) -> list[AttributeChange]:
        """Compare before/after dicts and emit one AttributeChange per differing key."""
        changes: list[AttributeChange] = []
        all_keys = set(before.keys()) | set(after.keys())

        for key in sorted(all_keys):
            before_val = before.get(key)
            after_val = after.get(key)

            if before_val == after_val:
                continue

            sensitive = self._is_sensitive(key, before_sensitive, after_sensitive)

            changes.append(
                AttributeChange(
                    attribute=key,
                    before="[sensitive]" if sensitive else before_val,
                    after="[sensitive]" if sensitive else after_val,
                    sensitive=sensitive,
                )
            )

        return changes

    def _is_sensitive(
        self,
        key: str,
        before_sensitive: dict[str, Any] | bool,
        after_sensitive: dict[str, Any] | bool,
    ) -> bool:
        """Check if a key is marked sensitive in either before or after."""
        if isinstance(before_sensitive, bool):
            if before_sensitive:
                return True
        elif isinstance(before_sensitive, dict) and before_sensitive.get(key):
            return True

        if isinstance(after_sensitive, bool):
            if after_sensitive:
                return True
        elif isinstance(after_sensitive, dict) and after_sensitive.get(key):
            return True

        return False
