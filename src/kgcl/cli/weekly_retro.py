"""Weekly retrospective CLI command.

Generates a weekly summary for retrospective analysis.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--store", "-s", type=click.Path(), help="Path to persistent store")
def weekly_retro(store: str | None) -> None:
    """Generate weekly retrospective summary.

    Analyzes knowledge graph evolution over the past week.
    """
    from kgcl.hybrid import HybridEngine

    console.print(Panel.fit("[bold]KGCL Weekly Retrospective[/]", border_style="blue"))

    engine = HybridEngine(store_path=store)
    triple_count = len(list(engine.store))

    console.print("\n[bold]Current State:[/]")
    console.print(f"  Total triples: {triple_count}")

    statuses = engine.inspect()
    if statuses:
        completed = sum(1 for s in statuses.values() if s == "Completed")
        active = sum(1 for s in statuses.values() if s == "Active")
        archived = sum(1 for s in statuses.values() if s == "Archived")

        console.print("\n[bold]Task Summary:[/]")
        console.print(f"  [green]Completed:[/] {completed}")
        console.print(f"  [yellow]Active:[/] {active}")
        console.print(f"  [dim]Archived:[/] {archived}")

    console.print("\n[green]Weekly retrospective complete.[/]")


if __name__ == "__main__":
    weekly_retro()
