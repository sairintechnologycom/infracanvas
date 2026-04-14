"""InfraCanvas project configuration (.infracanvas.yml)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class InfraCanvasConfig(BaseModel):
    severity_threshold: str = "high"
    ignore_rules: list[str] = []
    output_dir: str = "."
    open_browser: bool = True
    provider: str = "aws"


def load_config(directory: Path) -> InfraCanvasConfig:
    """Load .infracanvas.yml from directory or any parent up to home dir."""
    config_file = _find_config_file(directory)
    if not config_file:
        return InfraCanvasConfig()
    try:
        data = yaml.safe_load(config_file.read_text())
        if not isinstance(data, dict):
            return InfraCanvasConfig()
        return InfraCanvasConfig.model_validate(data)
    except (yaml.YAMLError, ValueError):
        return InfraCanvasConfig()


def _find_config_file(directory: Path) -> Path | None:
    """Walk up from directory to home dir looking for .infracanvas.yml."""
    home = Path.home()
    current = directory.resolve()
    while True:
        candidate = current / ".infracanvas.yml"
        if candidate.is_file():
            return candidate
        if current == home or current == current.parent:
            break
        current = current.parent
    return None
