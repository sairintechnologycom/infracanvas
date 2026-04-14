"""HTML export for InfraCanvas — embeds graph data into the single-file React viewer."""

from __future__ import annotations

from pathlib import Path

from infracanvas.graph.models import ResourceGraph

TEMPLATE_PATH = Path(__file__).parent / "viewer_template.html"

PLACEHOLDER = "window.__INFRACANVAS_DATA__ = null;"


def export_html(graph: ResourceGraph, output_path: Path) -> None:
    """Embed graph data into the viewer HTML template and write to output_path."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Viewer template not found at {TEMPLATE_PATH}. "
            "Run 'bash build.sh' from the repo root to build the viewer first."
        )

    template = TEMPLATE_PATH.read_text()
    graph_json = graph.model_dump_json()
    injected = template.replace(
        PLACEHOLDER,
        f"window.__INFRACANVAS_DATA__ = {graph_json};",
    )
    output_path.write_text(injected)
