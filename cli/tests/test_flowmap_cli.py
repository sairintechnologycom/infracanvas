"""Tests for --flowmap CLI flag and FlowMap collection orchestrator (FDM-02)."""
from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from infracanvas.flowmap.collector import _infer_region, run_flowmap_collection
from infracanvas.graph.models import ResourceGraph, ResourceNode


def _node(region: str = "") -> ResourceNode:
    return ResourceNode(
        id="aws_instance.test",
        type="aws_instance",
        name="test",
        provider="aws",
        region=region,
        attributes={},
    )


def _console() -> tuple[Console, StringIO]:
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    return console, buf


class TestInferRegion:
    def test_metadata_region_wins(self):
        g = ResourceGraph(metadata={"region": "eu-west-1"})
        assert _infer_region(g) == "eu-west-1"

    def test_first_node_region_fallback(self):
        g = ResourceGraph(nodes=[_node(region="ap-south-1")])
        assert _infer_region(g) == "ap-south-1"

    def test_default_when_empty(self):
        g = ResourceGraph()
        assert _infer_region(g) == "us-east-1"


class TestRunFlowmapCollection:
    def test_aws_runtime_error_yields_warning(self):
        console, buf = _console()
        g = ResourceGraph(nodes=[_node(region="us-west-2")])
        mock_aws = MagicMock(side_effect=RuntimeError(
            "--flowmap requires AWS credentials."
        ))
        with patch.dict(sys.modules, {
            "infracanvas.flowmap.aws": MagicMock(collect_aws_network=mock_aws),
            "infracanvas.flowmap.azure": MagicMock(
                collect_azure_network=lambda g: g
            ),
        }):
            result = run_flowmap_collection(g, console)
        output = buf.getvalue()
        assert "Warning" in output
        assert "AWS credentials" in output
        assert "Skipping AWS network collection" in output
        assert result is g  # unchanged

    def test_azure_runtime_error_yields_warning(self):
        console, buf = _console()
        g = ResourceGraph()
        mock_azure = MagicMock(side_effect=RuntimeError(
            "--flowmap requires Azure credentials: ARM_CLIENT_ID missing."
        ))
        with patch.dict(sys.modules, {
            "infracanvas.flowmap.aws": MagicMock(
                collect_aws_network=lambda g, region: g
            ),
            "infracanvas.flowmap.azure": MagicMock(
                collect_azure_network=mock_azure
            ),
        }):
            result = run_flowmap_collection(g, console)
        output = buf.getvalue()
        assert "Azure credentials" in output
        assert "Skipping Azure network collection" in output
        assert result is g

    def test_graceful_when_submodules_absent(self):
        """Before Plans 03-03/04 land, orchestrator must not crash."""
        console, buf = _console()
        g = ResourceGraph()
        # Simulate neither submodule existing by inserting None into sys.modules
        # (None triggers ImportError on `from ... import ...`).
        with patch.dict(sys.modules, {
            "infracanvas.flowmap.aws": None,
            "infracanvas.flowmap.azure": None,
        }):
            result = run_flowmap_collection(g, console)
        assert result is g


class TestFlowmapFlag:
    def test_help_lists_flowmap(self):
        """CLI --help text must advertise the --flowmap flag."""
        import re

        from typer.testing import CliRunner

        from infracanvas.main import app
        runner = CliRunner()
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        # Strip ANSI escapes — newer typer/rich emits colour even off-TTY,
        # which fragments option strings.
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--flowmap" in plain
        # Rich may wrap the help text across lines and insert │ box-drawing
        # characters at boundaries; collapse whitespace + strip │ before
        # asserting on the advertised "Beta, free during preview" wording.
        collapsed = " ".join(plain.replace("│", " ").split())
        assert "Beta, free during preview" in collapsed

    def test_no_flowmap_flag_no_collector_import(self):
        """Running scan without --flowmap must not import flowmap.collector."""
        from pathlib import Path

        # Ensure a clean slate for the import probe
        sys.modules.pop("infracanvas.flowmap.collector", None)
        from infracanvas.main import _run_scan

        fixture = Path(__file__).parent / "fixtures" / "simple_vpc"
        # Run scan with flowmap=False; collector must NOT get imported.
        _run_scan(fixture, ignore_rules=[], flowmap=False)
        assert "infracanvas.flowmap.collector" not in sys.modules
