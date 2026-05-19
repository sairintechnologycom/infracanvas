"""Parse Terraform HCL files from a directory."""

from __future__ import annotations

import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import hcl2

from infracanvas.parser.references import find_references

# T-05.1-05 (DoS guard): cap literal count/for_each expansion. A resource with
# count > COUNT_EXPANSION_CAP collapses to a single unresolved node instead of
# materializing millions of ParsedResources. Chosen to comfortably fit realistic
# Terraform usage (typical upper bound is a few hundred) while refusing OOM-scale input.
COUNT_EXPANSION_CAP: int = 1000

# Per-file HCL parse timeout. python-hcl2's Lark grammar can backtrack indefinitely
# on certain malformed inputs (e.g. unterminated string, missing close brace),
# leaving the scan hung at 96% CPU. We bound each file's parse so the user sees a
# clear error instead. Override via INFRACANVAS_PARSE_TIMEOUT_S (e.g. for very
# large generated .tf files).
PARSE_TIMEOUT_S: float = float(os.environ.get("INFRACANVAS_PARSE_TIMEOUT_S", "30"))


@dataclass
class ParsedResource:
    resource_type: str
    name: str
    attributes: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    module: str = ""
    index: int | None = None  # D-02: set when expanded from literal count/for_each
    unresolved_count: bool = False  # D-02: set when count/for_each is non-literal or exceeds cap


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
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)


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


class _ParseTimeoutError(Exception):
    """Raised when hcl2.load exceeds PARSE_TIMEOUT_S on a single file."""


def _load_hcl_with_timeout(tf_file: Path, timeout_s: float) -> tuple[Any, str | None]:
    """Run hcl2.load with a wall-clock deadline; return (parsed, error_str).

    python-hcl2's Lark grammar can hang indefinitely on malformed input (missing
    brace, unterminated string). On Unix we use SIGALRM, which interrupts pure-
    Python loops cleanly. On platforms without SIGALRM (Windows) we fall back to
    a best-effort threading watchdog.
    """
    timeout_msg = (
        f"parser exceeded {timeout_s:.0f}s — file is likely malformed "
        f"(unterminated string / missing brace). "
        f"Set INFRACANVAS_PARSE_TIMEOUT_S to raise the limit for large files."
    )

    has_sigalrm = hasattr(signal, "SIGALRM")
    if has_sigalrm:
        def _handler(_signum: int, _frame: Any) -> None:
            raise _ParseTimeoutError(timeout_msg)

        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            with open(tf_file) as f:
                return hcl2.load(f), None
        except _ParseTimeoutError as exc:
            return None, str(exc)
        except Exception as exc:  # noqa: BLE001 — hcl2 raises a wide variety
            return None, f"{type(exc).__name__}: {exc}"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    else:  # pragma: no cover — Windows fallback
        import threading

        out: dict[str, Any] = {}

        def _worker() -> None:
            try:
                with open(tf_file) as f:
                    out["parsed"] = hcl2.load(f)
            except Exception as exc:  # noqa: BLE001
                out["error"] = f"{type(exc).__name__}: {exc}"

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout_s)
        if t.is_alive():
            return None, timeout_msg
        if "error" in out:
            return None, out["error"]
        return out.get("parsed"), None


def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    """Parse a single .tf file and append results."""
    parsed, err = _load_hcl_with_timeout(tf_file, PARSE_TIMEOUT_S)
    if err is not None:
        result.parse_errors.append((tf_file, err))
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

                        # D-02: decide expansion. count takes precedence over for_each.
                        if "count" in attrs_dict:
                            expansions = _expand_count(attrs_dict)
                            # T-05.1-05: if the literal triggered the cap, emit a
                            # parse_error note so the CLI surfaces it to stderr.
                            raw = attrs_dict["count"]
                            if isinstance(raw, list) and len(raw) == 1:
                                raw = raw[0]
                            if (
                                isinstance(raw, int)
                                and not isinstance(raw, bool)
                                and raw > COUNT_EXPANSION_CAP
                            ):
                                result.parse_errors.append(
                                    (
                                        Path(f"<count-cap:{resource_type}.{name}>"),
                                        (
                                            f"count={raw} exceeds cap "
                                            f"{COUNT_EXPANSION_CAP}; "
                                            "collapsed to 1 unresolved node"
                                        ),
                                    )
                                )
                        elif "for_each" in attrs_dict:
                            expansions = _expand_for_each(attrs_dict)
                        else:
                            expansions = [(None, False)]

                        for idx, unresolved in expansions:
                            result.resources.append(
                                ParsedResource(
                                    resource_type=resource_type,
                                    name=name,
                                    attributes=attrs_dict,
                                    depends_on=depends_on,
                                    index=idx,
                                    unresolved_count=unresolved,
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


def _expand_count(attrs_dict: dict[str, Any]) -> list[tuple[int | None, bool]]:
    """Return a list of (index, unresolved_count) tuples describing instances to emit.

    D-02: Literal integer count expands to N instances with index 0..N-1 and
    unresolved_count=False. T-05.1-05: if the literal exceeds COUNT_EXPANSION_CAP
    (1000), collapse to a single unresolved instance — prevents OOM from
    `count = 10_000_000`. Non-literal count (string, dict, bool, negative, None,
    list wrapping an interpolation) returns a single (None, True) tuple. If
    `count` is absent, returns [(None, False)] (single unexpanded instance).
    """
    if "count" not in attrs_dict:
        return [(None, False)]
    raw = attrs_dict["count"]
    # python-hcl2 sometimes wraps single values in a 1-element list. Unwrap once.
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        # T-05.1-05 DoS guard: BEFORE range(raw), reject oversized counts.
        if raw > COUNT_EXPANSION_CAP:
            return [(None, True)]
        return [(i, False) for i in range(raw)]
    # Anything else — interpolation string, dict, negative, bool — treat as unresolved.
    return [(None, True)]


def _expand_for_each(attrs_dict: dict[str, Any]) -> list[tuple[int | None, bool]]:
    """Return a list of (index, unresolved_count) tuples for for_each handling.

    D-02: Literal dict/list for_each expands to one instance per key (index
    preserved as running int for now). T-05.1-05: oversized literal collections
    also collapse (same 1000 cap). Non-literal for_each returns a single
    (None, True) placeholder. Absent for_each returns (None, False) single instance.
    """
    if "for_each" not in attrs_dict:
        return [(None, False)]
    raw = attrs_dict["for_each"]
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if isinstance(raw, dict) and raw:
        if len(raw) > COUNT_EXPANSION_CAP:
            return [(None, True)]
        return [(i, False) for i in range(len(raw))]
    if (
        isinstance(raw, list)
        and raw
        and not any(isinstance(x, str) and x.startswith("${") for x in raw)
    ):
        if len(raw) > COUNT_EXPANSION_CAP:
            return [(None, True)]
        return [(i, False) for i in range(len(raw))]
    return [(None, True)]
