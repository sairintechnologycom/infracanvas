"""InfraCanvas CLI — scan Terraform code and generate annotated resource graphs."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from infracanvas.config import InfraCanvasConfig, load_config
from infracanvas.cost.estimator import CostEstimator
from infracanvas.drift.analyzer import DriftAnalyzer
from infracanvas.export.html import export_html
from infracanvas.export.json import export_graph
from infracanvas.export.scorecard import export_scorecard
from infracanvas.graph.builder import build_graph
from infracanvas.graph.models import GraphSummary, ResourceGraph, Severity
from infracanvas.parser.hcl import parse_directory
from infracanvas.parser.plan import PlanReader
from infracanvas.security.engine import evaluate_all
from infracanvas.security.scorer import Scorer

__version__ = "0.1.0"

app = typer.Typer(
    name="infracanvas",
    help="Parse Terraform code and generate annotated resource graphs.",
    no_args_is_help=True,
)
console = Console()
_ci_console = Console(stderr=True)  # for CI mode: diagnostics go to stderr


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"infracanvas {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", callback=_version_callback, is_eager=True,
                      help="Show version and exit"),
    ] = False,
) -> None:
    """InfraCanvas — interactive Terraform architecture diagrams."""


def _should_open_browser() -> bool:
    """Return False when running in CI/headless environment (per D-11)."""
    ci_env_vars = ["CI", "GITHUB_ACTIONS", "CIRCLECI", "TRAVIS", "JENKINS_URL"]
    if any(os.environ.get(v) for v in ci_env_vars):
        return False
    if not os.environ.get("DISPLAY"):
        return False
    return True


def _run_scan(
    directory: Path,
    severity_filter: str | None = None,
    ignore_rules: list[str] | None = None,
    *,
    allow_empty: bool = False,
    ci: bool = False,
) -> ResourceGraph:
    """Core scan pipeline: parse → graph → security → annotate."""
    out = _ci_console if ci else console

    try:
        parsed = parse_directory(directory)
    except Exception as exc:
        out.print(f"[red]Error:[/red] Failed to parse Terraform files: {exc}")
        out.print("  Run with --verbose for details, or check that this is a valid Terraform directory.")
        raise typer.Exit(code=2)

    if not allow_empty:
        tf_files = list(directory.glob("*.tf"))
        if not tf_files:
            out.print(
                "[red]Error:[/red] No .tf files found in directory. "
                "Are you pointing at a Terraform project?"
            )
            raise typer.Exit(code=2)

    graph = build_graph(parsed)

    if not allow_empty and len(graph.nodes) == 0:
        out.print(
            "[red]Error:[/red] No Terraform resources found. "
            "Check for parse errors with --verbose."
        )
        raise typer.Exit(code=2)

    graph = evaluate_all(graph)

    # Strip ignored rules
    if ignore_rules:
        ignore_set = set(ignore_rules)
        for node in graph.nodes:
            node.findings = [f for f in node.findings if f.rule_id not in ignore_set]

    # Build metadata
    graph.metadata = {
        "scan_id": str(uuid.uuid4()),
        "project": directory.resolve().name,
        "provider": _detect_provider(graph),
        "scanned_at": datetime.now(UTC).isoformat(),
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
    console.print("[bold]InfraCanvas Scan Results[/bold]", justify="center")
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
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (json, html)"),
    ] = "html",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="JSON only to stdout, for CI/CD"),
    ] = False,
    severity: Annotated[
        str | None,
        typer.Option("--severity", "-s", help="Filter findings by severity"),
    ] = None,
    ci: Annotated[
        bool,
        typer.Option(
            "--ci",
            help="CI mode: JSON to stdout, non-zero exit on findings",
        ),
    ] = False,
    watch: Annotated[
        bool,
        typer.Option("--watch", "-w", help="Re-scan on file changes"),
    ] = False,
    ignore: Annotated[
        list[str] | None,
        typer.Option("--ignore", help="Rule IDs to skip, e.g. --ignore SEC-010"),
    ] = None,
) -> None:
    """Scan a Terraform directory and generate an annotated resource graph."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=2)

    # Load project config
    config = load_config(directory)
    effective_ignore = list(set((ignore or []) + config.ignore_rules))
    effective_severity = severity or (config.severity_threshold if ci else severity)

    if watch:
        _run_watch(directory, output, format, effective_severity, effective_ignore, ci)
        return

    graph = _run_scan(directory, severity_filter=effective_severity,
                      ignore_rules=effective_ignore, ci=ci)

    if ci or quiet:
        # CI mode: only valid JSON to stdout, diagnostics to stderr
        sys.stdout.write(export_graph(graph))
        sys.stdout.write("\n")
        if ci:
            threshold = effective_severity or "high"
            sev_order = ["critical", "high", "medium", "info"]
            threshold_idx = sev_order.index(threshold)
            has_findings = any(
                graph.summary.findings.get(s, 0) > 0
                for s in sev_order[: threshold_idx + 1]
            )
            raise typer.Exit(code=1 if has_findings else 0)
        raise typer.Exit(code=0)

    _print_summary(graph)

    if format == "html":
        out_path = output or Path(config.output_dir) / "infracanvas-report.html"
        try:
            export_html(graph, out_path, gate_mode=True)
            console.print(f"  HTML report saved to: [bold]{out_path}[/bold]")
            if config.open_browser and _should_open_browser():
                webbrowser.open(out_path.resolve().as_uri())
            else:
                console.print(f"  Report saved: [bold]{out_path}[/bold]")
        except FileNotFoundError as e:
            console.print(f"  [yellow]Warning:[/yellow] {e}")
            console.print("  Falling back to JSON output.")
            out_path = output or Path(config.output_dir) / "infracanvas-report.json"
            out_path.write_text(export_graph(graph))
            console.print(f"  JSON report saved to: [bold]{out_path}[/bold]")
    else:
        out_path = output or Path(config.output_dir) / "infracanvas-report.json"
        out_path.write_text(export_graph(graph))
        console.print(f"  Report saved to: [bold]{out_path}[/bold]")

    raise typer.Exit(code=0)


def _run_watch(
    directory: Path,
    output: Path | None,
    fmt: str,
    severity: str | None,
    ignore_rules: list[str],
    ci: bool,
) -> None:
    """Watch *.tf files and re-scan on changes."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        console.print("[yellow]Install watchdog for --watch: pip install watchdog[/yellow]")
        raise typer.Exit(1)

    console.print("[cyan]Watching for changes...[/cyan] Press Ctrl+C to stop")

    # Initial scan
    graph = _run_scan(directory, severity_filter=severity, ignore_rules=ignore_rules, ci=ci)
    _print_summary(graph)

    last_trigger = 0.0

    class TfChangeHandler(FileSystemEventHandler):  # type: ignore[misc]
        def on_modified(self, event) -> None:  # type: ignore[no-untyped-def]
            nonlocal last_trigger
            if event.is_directory or not event.src_path.endswith(".tf"):
                return
            now = time.time()
            if now - last_trigger < 0.5:
                return  # debounce
            last_trigger = now
            console.print("\n[cyan]Change detected, re-scanning...[/cyan]")
            try:
                g = _run_scan(directory, severity_filter=severity, ignore_rules=ignore_rules, ci=ci)
                _print_summary(g)
            except SystemExit:
                pass

    observer = Observer()
    observer.schedule(TfChangeHandler(), str(directory), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]Stopped watching.[/dim]")
    observer.join()


@app.command()
def serve(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing Terraform files")
    ],
    port: Annotated[
        int, typer.Option("--port", "-p", help="HTTP server port"),
    ] = 8080,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Start a local HTTP server with live-reloading diagram. Re-scans on .tf file changes."""
    import http.server
    import tempfile
    import threading

    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=2)

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        console.print("[yellow]Install watchdog for serve: pip install watchdog[/yellow]")
        raise typer.Exit(1)

    config = load_config(directory)

    # Use a temporary directory for serving, or user-specified output
    serve_dir = Path(tempfile.mkdtemp(prefix="infracanvas-serve-"))
    html_path = output or serve_dir / "index.html"

    def _do_scan() -> None:
        """Run scan pipeline and write HTML."""
        try:
            graph = _run_scan(directory, severity_filter=None, ignore_rules=config.ignore_rules, ci=False)
            export_html(graph, html_path, gate_mode=True)
            # Append auto-refresh meta tag for live reload
            content = html_path.read_text()
            if '<meta http-equiv="refresh"' not in content:
                content = content.replace(
                    "</head>",
                    '<meta http-equiv="refresh" content="2"></head>',
                )
                html_path.write_text(content)
            console.print(f"  [green]Updated:[/green] {html_path.name}")
        except Exception as exc:
            console.print(f"  [red]Scan error:[/red] {exc}")

    # Initial scan
    console.print(f"[cyan]Scanning {directory}...[/cyan]")
    _do_scan()

    # Start HTTP server bound to localhost only (T-01-11: no external exposure)
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            super().__init__(*args, directory=str(html_path.parent), **kwargs)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access logs

    server = http.server.HTTPServer(("127.0.0.1", port), QuietHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}/{html_path.name}"
    console.print(f"[bold green]Serving at:[/bold green] {url}")

    if _should_open_browser():
        webbrowser.open(url)

    # File watcher — re-scans on .tf changes with 1s debounce
    last_trigger = 0.0

    class TfServeHandler(FileSystemEventHandler):  # type: ignore[misc]
        def on_modified(self, event) -> None:  # type: ignore[no-untyped-def]
            nonlocal last_trigger
            if event.is_directory or not event.src_path.endswith(".tf"):
                return
            now = time.time()
            if now - last_trigger < 1.0:  # 1s debounce for serve
                return
            last_trigger = now
            console.print("\n[cyan]Change detected, re-scanning...[/cyan]")
            _do_scan()

    observer = Observer()
    observer.schedule(TfServeHandler(), str(directory), recursive=True)
    observer.start()

    console.print("[dim]Watching for .tf changes... Press Ctrl+C to stop[/dim]")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        server.shutdown()
        console.print("\n[dim]Stopped serving.[/dim]")
    observer.join()


@app.command()
def score(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing Terraform files")
    ],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (terminal, json, html)"),
    ] = "terminal",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Show the security score for a Terraform directory."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=1)

    config = load_config(directory)
    graph = _run_scan(directory, ignore_rules=config.ignore_rules)

    # Apply cost estimation
    estimator = CostEstimator()
    graph = estimator.estimate(graph)

    scorer = Scorer()
    card = scorer.build(graph)

    if format == "json":
        json_out = card.model_dump_json(indent=2)
        if output:
            output.write_text(json_out)
            console.print(f"  Score card saved to: [bold]{output}[/bold]")
        else:
            typer.echo(json_out)
        return

    if format == "html":
        out_path = output or Path("scorecard.html")
        export_scorecard(card, out_path)
        console.print(f"  Score card saved to: [bold]{out_path}[/bold]")
        if config.open_browser:
            webbrowser.open(out_path.resolve().as_uri())
        return

    # Terminal output — rich box
    _print_scorecard(card)


@app.command()
def plan(
    directory: Annotated[
        Path, typer.Argument(help="Directory containing Terraform files")
    ],
    planfile: Annotated[
        Path,
        typer.Option("--planfile", "-p", help="Terraform plan JSON file"),
    ] = ...,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (html, json)"),
    ] = "html",
) -> None:
    """Scan directory and overlay terraform plan diff on the diagram."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory")
        raise typer.Exit(code=1)

    if not planfile.exists():
        console.print(f"[red]Error:[/red] Plan file {planfile} not found")
        raise typer.Exit(code=1)

    config = load_config(directory)
    graph = _run_scan(directory, ignore_rules=config.ignore_rules)

    # Read plan and apply drift
    reader = PlanReader()
    changes = reader.read(planfile)
    analyzer = DriftAnalyzer()
    graph = analyzer.apply(graph, changes)

    # Apply cost estimation with delta
    estimator = CostEstimator()
    graph = estimator.estimate(graph)
    cost_delta = estimator.delta(graph, changes)

    # Print drift summary
    drift = graph.summary.drift
    console.print()
    console.print(
        f"  [green]+{drift.get('added', 0)} added[/green]  ·  "
        f"[yellow]~{drift.get('changed', 0)} changed[/yellow]  ·  "
        f"[red]-{drift.get('deleted', 0)} deleted[/red]  ·  "
        f"est. cost delta: [bold]{'+'if cost_delta >= 0 else ''}"
        f"${cost_delta:.2f}/mo[/bold]"
    )
    console.print()

    if format == "html":
        out_path = output or Path("infracanvas-report.html")
        try:
            export_html(graph, out_path)
            console.print(f"  HTML report saved to: [bold]{out_path}[/bold]")
            if config.open_browser:
                webbrowser.open(out_path.resolve().as_uri())
        except FileNotFoundError as e:
            console.print(f"  [yellow]Warning:[/yellow] {e}")
            out_path = output or Path("infracanvas-report.json")
            out_path.write_text(export_graph(graph))
            console.print(f"  JSON report saved to: [bold]{out_path}[/bold]")
    else:
        out_path = output or Path("infracanvas-report.json")
        out_path.write_text(export_graph(graph))
        console.print(f"  Report saved to: [bold]{out_path}[/bold]")


def _print_scorecard(card: "ScoreCard") -> None:
    """Print a rich score card to the terminal."""
    from infracanvas.graph.models import ScoreCard  # noqa: F811

    if card.overall >= 80:
        score_style = "bold green"
    elif card.overall >= 60:
        score_style = "bold yellow"
    else:
        score_style = "bold red"

    console.print()
    console.print("[bold]╔══════════════════════════════════════╗[/bold]")
    console.print("[bold]║  InfraCanvas Score Card              ║[/bold]")
    console.print(
        f"[bold]║[/bold]  project: {card.project}  ·  "
        f"{card.resource_count} resources  [bold]║[/bold]"
    )
    console.print("[bold]╠══════════════════════════════════════╣[/bold]")
    console.print(
        f"[bold]║[/bold]  Overall Score    "
        f"[{score_style}]{card.overall} / 100    {card.overall_grade}[/{score_style}]"
        f"     [bold]║[/bold]"
    )
    console.print("[bold]╠══════════════════════════════════════╣[/bold]")

    for cat in card.categories:
        if cat.score >= 80:
            cat_style = "green"
        elif cat.score >= 60:
            cat_style = "yellow"
        else:
            cat_style = "red"
        console.print(
            f"[bold]║[/bold]  {cat.name:<15} [{cat_style}]{cat.score:>3}   "
            f"{cat.grade:<3}[/{cat_style}]  {cat.finding_count} issue{'s' if cat.finding_count != 1 else ''}"
            f"  [bold]║[/bold]"
        )

    if card.top_issues:
        console.print("[bold]╠══════════════════════════════════════╣[/bold]")
        console.print("[bold]║[/bold]  Top Issues                          [bold]║[/bold]")
        sev_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "info": "🔵"}
        for issue in card.top_issues[:5]:
            icon = sev_icons.get(issue.severity, "⚪")
            line = f"{icon} {issue.rule_id} {issue.title}"
            console.print(f"[bold]║[/bold]  {line:<36} [bold]║[/bold]")

    console.print("[bold]╠══════════════════════════════════════╣[/bold]")
    console.print(
        f"[bold]║[/bold]  Est. monthly cost: "
        f"[bold]${card.estimated_monthly_cost:,.0f}[/bold]"
        f"           [bold]║[/bold]"
    )
    console.print("[bold]╚══════════════════════════════════════╝[/bold]")
    console.print()


@app.command()
def export(
    report: Annotated[
        Path, typer.Argument(help="InfraCanvas report JSON file")
    ],
    output: Annotated[
        Path | None,
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

    try:
        data = json.loads(report.read_text())
        graph = ResourceGraph.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] Invalid report file: {exc}")
        raise typer.Exit(code=1)

    if format == "html":
        out_path = output or Path("infracanvas-report.html")
        export_html(graph, out_path)
        console.print(f"  HTML report saved to: [bold]{out_path}[/bold]")
        webbrowser.open(out_path.resolve().as_uri())
    elif format == "json":
        typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
