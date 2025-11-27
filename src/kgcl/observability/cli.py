"""Observability CLI commands.

Health checks and monitoring for KGCL.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def cli() -> None:
    """KGCL Health and Observability commands."""


@cli.command()
def check() -> None:
    """Run health checks on all components."""
    from kgcl.observability import health_check

    console.print(Panel.fit("[bold]KGCL Health Check[/]", border_style="blue"))

    status = health_check()

    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    all_healthy = True
    for component, healthy in status.items():
        icon = "\u2713" if healthy else "\u2717"
        color = "green" if healthy else "red"
        table.add_row(component, f"[{color}]{icon}[/{color}]")
        if not healthy:
            all_healthy = False

    console.print(table)

    if all_healthy:
        console.print("\n[bold green]All systems healthy![/]")
    else:
        console.print("\n[bold red]Some components need attention[/]")


@cli.command()
def metrics() -> None:
    """Display system metrics."""
    from kgcl.observability import get_metrics

    console.print(Panel.fit("[bold]KGCL Metrics[/]", border_style="blue"))

    metrics_data = get_metrics()

    for key, value in metrics_data.items():
        console.print(f"  {key}: {value}")


@cli.command()
def status() -> None:
    """Show overall system status."""
    from kgcl.observability import health_check

    status_data = health_check()
    healthy_count = sum(1 for v in status_data.values() if v)
    total = len(status_data)

    console.print(Panel.fit(f"[bold]KGCL Status: {healthy_count}/{total} healthy[/]", border_style="blue"))


if __name__ == "__main__":
    cli()
