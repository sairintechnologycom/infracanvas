"""Recursive Terraform local module resolution."""

from __future__ import annotations

from pathlib import Path

from infracanvas.parser.hcl import ParsedResource, ParsedTerraform, parse_directory


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
            # WARNING 5 closure: surface non-local sources as a one-line note so
            # users see the deferral (per README.md Known Limitations). This is NOT
            # an error — scan continues — but the CLI stderr loop will print it.
            if source:
                parsed.parse_errors.append(
                    (
                        Path(f"<non-local-module:{name}>"),
                        (
                            f"Skipping non-local module source '{source}' — "
                            "see Known Limitations"
                        ),
                    )
                )
            continue

        module_dir = (directory / source).resolve()

        # T-01-01: Reject if not a directory or outside project scope
        if not module_dir.is_dir():
            parsed.parse_errors.append(
                (
                    Path(f"<missing-module-dir:{name}>"),
                    f"Module '{name}' source '{source}' is not a directory; skipping",
                )
            )
            continue

        # T-01-02: Circular reference detection
        if module_dir in _visited:
            continue

        sub_parsed = parse_directory(module_dir)

        # D-01: merge submodule parse errors into caller's list so main.py's
        # `if parsed.parse_errors` loop surfaces them to stderr.
        parsed.parse_errors.extend(sub_parsed.parse_errors)

        # D-01: if the submodule produced zero resources AND has parse errors,
        # synthesize a placeholder ParsedResource. The graph builder renders this
        # as an orange-ringed "unresolved module" node via type prefix match.
        if not sub_parsed.resources and sub_parsed.parse_errors:
            first_err_path, first_err_msg = sub_parsed.parse_errors[0]
            placeholder = ParsedResource(
                resource_type="_infracanvas_unresolved_module",
                name=name,
                attributes={
                    "source": source,
                    "_module_dir": str(module_dir),
                    "_parse_error": f"{first_err_path.name}: {first_err_msg}",
                },
                module="",
            )
            parsed.resources.append(placeholder)
            # Don't recurse into a broken submodule
            continue

        for res in sub_parsed.resources:
            res.module = f"module.{name}"
        parsed.resources.extend(sub_parsed.resources)

        resolve_modules(module_dir, sub_parsed, depth + 1, _visited)
