"""Daily brief CLI command.

Generates a daily summary of knowledge graph activity.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--store", "-s", type=click.Path(), help="Path to persistent store")
def daily_brief(store: str | None) -> None:
    """Generate daily knowledge graph activity brief.

    Summarizes recent changes, task statuses, and system health.
    """
    from kgcl.hybrid import HybridEngine

    console.print(Panel.fit("[bold]KGCL Daily Brief[/]", border_style="blue"))

    engine = HybridEngine(store_path=store)
    triple_count = len(list(engine.store))

    console.print("\n[bold]Store Statistics:[/]")
    console.print(f"  Triples: {triple_count}")

    statuses = engine.inspect()
    if statuses:
        console.print("\n[bold]Task Statuses:[/]")
        status_counts: dict[str, int] = {}
        for status in statuses.values():
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in sorted(status_counts.items()):
            color = {"Active": "green", "Completed": "blue", "Archived": "dim"}.get(status, "white")
            console.print(f"  [{color}]{status}:[/] {count}")
    else:
        console.print("\n[yellow]No task statuses found[/]")

    console.print("\n[green]Daily brief complete.[/]")


if __name__ == "__main__":
    daily_brief()
