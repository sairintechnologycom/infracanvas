"""InfraCanvas CLI — scan Terraform code and generate annotated resource graphs."""

from __future__ import annotations

import json
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from infracanvas.export.html import export_html
from infracanvas.export.json import export_graph
from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import GraphSummary, ResourceGraph, Severity
from infracanvas.parser.hcl import parse_directory
from infracanvas.security.engine import evaluate_all

app = typer.Typer(
    name="infracanvas",
    help="Parse Terraform code and generate annotated resource graphs.",
    no_args_is_help=True,
)
console = Console()


def _run_scan(
    directory: Path,
    severity_filter: Optional[str] = None,
) -> ResourceGraph:
    """Core scan pipeline: parse → graph → security → annotate."""
    parsed = parse_directory(directory)
    graph = build_graph(parsed)
    graph = evaluate_all(graph)

    # Build metadata
    graph.metadata = {
        "scan_id": str(uuid.uuid4()),
        "project": directory.resolve().name,
        "provider": _detect_provider(graph),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "terraform_version": "unknown",
    }

    # Compute summary
    finding_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "info": 0}
    for node in graph.nodes:
        for f in node.findings:
            finding_counts[f.severity.value] += 1

    # Filter findings by severity if requested
    if severity_filter:
        sev = Severity(severity_filter)
        for node in graph.nodes:
            node.findings = [f for f in node.findings if f.severity == sev]

    score = 100 - (
        finding_counts["critical"] * 20
        + finding_counts["high"] * 10
        + finding_counts["medium"] * 5
        + finding_counts["info"] * 1
    )
    score = max(0, score)

    graph.summary = GraphSummary(
        total_resources=len(graph.nodes),
        findings=finding_counts,
        estimated_monthly_cost=0.0,
        score=score,
    )
    return graph


def _detect_provider(graph: ResourceGraph) -> str:
    providers: set[str] = set()
    for node in graph.nodes:
        if node.provider:
            providers.add(node.provider)
    if len(providers) == 1:
        return providers.pop()
    if providers:
        return ",".join(sorted(providers))
    return "unknown"


def _print_summary(graph: ResourceGraph) -> None:
    """Print a rich summary table to the terminal."""
    summary = graph.summary
    console.print()
    console.print(f"[bold]InfraCanvas Scan Results[/bold]", justify="center")
    console.print()

    # Score with color
    score = summary.score
    if score >= 80:
        score_style = "bold green"
    elif score >= 50:
        score_style = "bold yellow"
    else:
        score_style = "bold red"
    console.print(f"  Security Score: [{score_style}]{score}/100[/{score_style}]")
    console.print(f"  Total Resources: {summary.total_resources}")
    console.print()

    # Findings table
    findings = summary.findings
    table = Table(title="Security Findings")
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")

    severity_styles = {
        "critical": "red",
        "high": "bright_red",
        "medium": "yellow",
        "info": "blue",
    }
    for sev in ["critical", "high", "medium", "info"]:
        count = findings.get(sev, 0)
        style = severity_styles[sev]
        table.add_row(f"[{style}]{sev.upper()}[/{style}]", str(count))

    console.print(table)
    console.print()

    # Detailed findings per resource
    resources_with_findings = [n for n in graph.nodes if n.findings]
    if resources_with_findings:
        detail_table = Table(title="Findings Detail")
        detail_table.add_column("Resource", style="cyan")
        detail_table.add_column("Rule", style="bold")
        detail_table.add_column("Severity")
        detail_table.add_column("Title")

        for node in resources_with_findings:
            for f in node.findings:
                sev_style = severity_styles.get(f.severity.value, "white")
                detail_table.add_row(
                    node.id,
                    f.rule_id,
                    f"[{sev_style}]{f.severity.value.upper()}[/{sev_style}]",
                    f.title,
                )

        console.print(detail_table)
        console.print()


@app.command()
def scan(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing Terraform files")
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (json)"),
    ] = "json",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="JSON only to stdout, for CI/CD"),
    ] = False,
    severity: Annotated[
        Optional[str],
        typer.Option("--severity", "-s", help="Filter findings by severity"),
    ] = None,
) -> None:
    """Scan a Terraform directory and generate an annotated resource graph."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=1)

    graph = _run_scan(directory, severity_filter=severity)

    if quiet:
        typer.echo(export_graph(graph))
    else:
        _print_summary(graph)

        if format == "html":
            out_path = output or Path("infracanvas-report.html")
            try:
                export_html(graph, out_path)
                console.print(f"  HTML report saved to: [bold]{out_path}[/bold]")
                webbrowser.open(out_path.resolve().as_uri())
            except FileNotFoundError as e:
                console.print(f"  [yellow]Warning:[/yellow] {e}")
                console.print("  Falling back to JSON output.")
                out_path = output or Path("infracanvas-report.json")
                out_path.write_text(export_graph(graph))
                console.print(f"  JSON report saved to: [bold]{out_path}[/bold]")
        else:
            out_path = output or Path("infracanvas-report.json")
            out_path.write_text(export_graph(graph))
            console.print(f"  Report saved to: [bold]{out_path}[/bold]")

    raise typer.Exit(code=0)


@app.command()
def score(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing Terraform files")
    ],
) -> None:
    """Show the security score for a Terraform directory."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=1)

    graph = _run_scan(directory)
    summary = graph.summary
    score_val = summary.score

    console.print()
    console.print("[bold]InfraCanvas Security Score Card[/bold]", justify="center")
    console.print()

    if score_val >= 80:
        console.print(f"  Score: [bold green]{score_val}/100[/bold green]  Grade: A")
    elif score_val >= 60:
        console.print(f"  Score: [bold yellow]{score_val}/100[/bold yellow]  Grade: B")
    elif score_val >= 40:
        console.print(f"  Score: [bold yellow]{score_val}/100[/bold yellow]  Grade: C")
    else:
        console.print(f"  Score: [bold red]{score_val}/100[/bold red]  Grade: F")

    console.print(f"  Resources: {summary.total_resources}")
    console.print(
        f"  Findings: {summary.findings.get('critical', 0)} critical, "
        f"{summary.findings.get('high', 0)} high, "
        f"{summary.findings.get('medium', 0)} medium, "
        f"{summary.findings.get('info', 0)} info"
    )
    console.print()


@app.command()
def plan(
    plan_file: Annotated[
        Path, typer.Argument(help="Terraform plan JSON file")
    ],
) -> None:
    """Analyze a Terraform plan JSON for drift detection (Phase 2)."""
    console.print("[yellow]Plan analysis will be available in Phase 2.[/yellow]")


@app.command()
def export(
    report: Annotated[
        Path, typer.Argument(help="InfraCanvas report JSON file")
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format (json, html)"),
    ] = "html",
) -> None:
    """Export a JSON report to HTML or re-export as formatted JSON."""
    if not report.exists():
        console.print(f"[red]Error:[/red] {report} not found")
        raise typer.Exit(code=1)

    data = json.loads(report.read_text())
    graph = ResourceGraph.model_validate(data)

    if format == "html":
        out_path = output or Path("infracanvas-report.html")
        export_html(graph, out_path)
        console.print(f"  HTML report saved to: [bold]{out_path}[/bold]")
        webbrowser.open(out_path.resolve().as_uri())
    elif format == "json":
        typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
