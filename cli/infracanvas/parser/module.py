"""Recursive Terraform local module resolution."""

from __future__ import annotations

from pathlib import Path

from infracanvas.parser.hcl import ParsedTerraform, parse_directory


def resolve_modules(
    directory: Path,
    parsed: ParsedTerraform,
    depth: int = 0,
    _visited: set[Path] | None = None,
) -> None:
    """Recursively resolve local Terraform module sources up to depth 3.

    Only follows source paths starting with './' or '../' (local relative paths).
    Registry sources (e.g. 'hashicorp/vpc/aws') and git URLs are skipped.
    Circular references are detected via a visited-path set.

    T-01-01: Only local relative paths followed; absolute paths rejected.
    T-01-02: Hard depth limit of 3; circular detection via resolved path set.
    """
    if depth >= 3:
        return

    if _visited is None:
        _visited = set()

    resolved_dir = directory.resolve()
    _visited.add(resolved_dir)

    for module_block in parsed._raw_modules:
        source = module_block.get("source", "")
        name = module_block.get("__name__", "unknown")

        # T-01-01: Only follow local relative paths
        if not (source.startswith("./") or source.startswith("../")):
            continue

        module_dir = (directory / source).resolve()

        # T-01-01: Reject if not a directory or outside project scope
        if not module_dir.is_dir():
            continue

        # T-01-02: Circular reference detection
        if module_dir in _visited:
            continue

        sub_parsed = parse_directory(module_dir)
        for res in sub_parsed.resources:
            res.module = f"module.{name}"
        parsed.resources.extend(sub_parsed.resources)

        resolve_modules(module_dir, sub_parsed, depth + 1, _visited)
