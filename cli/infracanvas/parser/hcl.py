"""Parse Terraform HCL files from a directory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import hcl2

from infracanvas.parser.references import find_references


@dataclass
class ParsedResource:
    resource_type: str
    name: str
    attributes: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    module: str = ""


@dataclass
class ParsedBlock:
    block_type: str  # "variable", "local", "output", "data"
    name: str
    attributes: dict[str, Any]


@dataclass
class ParsedTerraform:
    resources: list[ParsedResource] = field(default_factory=list)
    variables: list[ParsedBlock] = field(default_factory=list)
    locals: list[ParsedBlock] = field(default_factory=list)
    outputs: list[ParsedBlock] = field(default_factory=list)
    data_sources: list[ParsedBlock] = field(default_factory=list)
    implicit_deps: dict[str, set[str]] = field(default_factory=dict)
    _raw_modules: list[dict[str, Any]] = field(default_factory=list)


def _strip_quotes(value: str) -> str:
    """Strip surrounding double quotes that python-hcl2 adds to keys/values."""
    if isinstance(value, str) and len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _clean_value(value: Any) -> Any:
    """Recursively strip quotes from all string values in a structure."""
    if isinstance(value, str):
        return _strip_quotes(value)
    if isinstance(value, dict):
        return {_strip_quotes(k): _clean_value(v) for k, v in value.items()
                if k != "__is_block__"}
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    return value


def parse_directory(directory: Path) -> ParsedTerraform:
    """Parse all .tf files in a directory and return structured data."""
    result = ParsedTerraform()
    tf_files = sorted(directory.glob("*.tf"))

    if not tf_files:
        return result

    for tf_file in tf_files:
        _parse_file(tf_file, result)

    # Build implicit dependency map
    known_resources: set[str] = set()
    for res in result.resources:
        resource_id = f"{res.resource_type}.{res.name}"
        known_resources.add(resource_id)

    for res in result.resources:
        resource_id = f"{res.resource_type}.{res.name}"
        refs = find_references(res.attributes, known_resources)
        refs.discard(resource_id)  # Don't self-reference
        if refs:
            result.implicit_deps[resource_id] = refs

    return result


def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    """Parse a single .tf file and append results."""
    with open(tf_file) as f:
        try:
            parsed = hcl2.load(f)
        except Exception:
            return

    _extract_resources(parsed, result)
    _extract_variables(parsed, result)
    _extract_locals(parsed, result)
    _extract_outputs(parsed, result)
    _extract_data_sources(parsed, result)
    _extract_modules(parsed, result)


def _extract_resources(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract resource blocks from parsed HCL."""
    for resource_block in parsed.get("resource", []):
        for resource_type_raw, instances in resource_block.items():
            resource_type = _strip_quotes(resource_type_raw)
            items = instances if isinstance(instances, list) else [instances]
            for instance in items:
                if isinstance(instance, dict):
                    for name_raw, attrs in instance.items():
                        name = _strip_quotes(name_raw)
                        attrs_dict = _clean_value(attrs) if isinstance(attrs, dict) else {}
                        depends_on_raw = attrs_dict.pop("depends_on", [])
                        depends_on = _normalize_depends_on(depends_on_raw)
                        result.resources.append(
                            ParsedResource(
                                resource_type=resource_type,
                                name=name,
                                attributes=attrs_dict,
                                depends_on=depends_on,
                            )
                        )


def _extract_variables(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract variable blocks from parsed HCL."""
    for var_block in parsed.get("variable", []):
        if isinstance(var_block, dict):
            for name_raw, attrs in var_block.items():
                name = _strip_quotes(name_raw)
                result.variables.append(
                    ParsedBlock(
                        block_type="variable",
                        name=name,
                        attributes=_clean_value(attrs) if isinstance(attrs, dict) else {},
                    )
                )


def _extract_locals(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract locals blocks from parsed HCL."""
    for local_block in parsed.get("locals", []):
        if isinstance(local_block, dict):
            for name_raw, value in local_block.items():
                name = _strip_quotes(name_raw)
                result.locals.append(
                    ParsedBlock(
                        block_type="local",
                        name=name,
                        attributes={"value": _clean_value(value)},
                    )
                )


def _extract_outputs(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract output blocks from parsed HCL."""
    for output_block in parsed.get("output", []):
        if isinstance(output_block, dict):
            for name_raw, attrs in output_block.items():
                name = _strip_quotes(name_raw)
                result.outputs.append(
                    ParsedBlock(
                        block_type="output",
                        name=name,
                        attributes=_clean_value(attrs) if isinstance(attrs, dict) else {},
                    )
                )


def _extract_data_sources(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract data source blocks from parsed HCL."""
    for data_block in parsed.get("data", []):
        for data_type_raw, instances in data_block.items():
            data_type = _strip_quotes(data_type_raw)
            items = instances if isinstance(instances, list) else [instances]
            for instance in items:
                if isinstance(instance, dict):
                    for name_raw, attrs in instance.items():
                        name = _strip_quotes(name_raw)
                        result.data_sources.append(
                            ParsedBlock(
                                block_type="data",
                                name=f"{data_type}.{name}",
                                attributes=_clean_value(attrs) if isinstance(attrs, dict) else {},
                            )
                        )


def _extract_modules(parsed: dict[str, Any], result: ParsedTerraform) -> None:
    """Extract module blocks from parsed HCL and store in _raw_modules."""
    for module_block in parsed.get("module", []):
        if isinstance(module_block, dict):
            for name_raw, attrs in module_block.items():
                name = _strip_quotes(name_raw)
                attrs_dict = _clean_value(attrs) if isinstance(attrs, dict) else {}
                attrs_dict["__name__"] = name
                result._raw_modules.append(attrs_dict)


def _normalize_depends_on(raw: Any) -> list[str]:
    """Normalize depends_on to a list of resource address strings."""
    if not raw:
        return []
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(_strip_interpolation(_strip_quotes(item)))
            elif isinstance(item, list):
                result.extend(_strip_interpolation(_strip_quotes(str(i))) for i in item)
        return result
    if isinstance(raw, str):
        return [_strip_interpolation(_strip_quotes(raw))]
    return []


def _strip_interpolation(value: str) -> str:
    """Strip ${...} interpolation wrapper from a string."""
    if value.startswith("${") and value.endswith("}"):
        return value[2:-1]
    return value
