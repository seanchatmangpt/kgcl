"""Task CLI commands.

kgcl task <verb> - Task management.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def task() -> None:
    """Task management.

    \b
    Commands:
      list      List all tasks and statuses
      inspect   Detailed task inspection
    """


@task.command("list")
@click.argument("topology", type=click.Path(exists=True))
def task_list(topology: str) -> None:
    """List all tasks and their statuses."""
    from kgcl.hybrid import HybridEngine

    path = Path(topology)
    eng = HybridEngine()
    eng.load_data(path.read_text())

    statuses = eng.inspect()

    if not statuses:
        console.print("[yellow]No tasks found[/]")
        return

    table = Table(title=f"Tasks: {path.name}")
    table.add_column("Task", style="cyan")
    table.add_column("Status", style="green")

    for t, s in sorted(statuses.items()):
        table.add_row(t, s)

    console.print(table)


@task.command()
@click.argument("topology", type=click.Path(exists=True))
@click.argument("task_uri")
def inspect(topology: str, task_uri: str) -> None:
    """Inspect specific task details."""
    from kgcl.hybrid import HybridEngine

    path = Path(topology)
    eng = HybridEngine()
    eng.load_data(path.read_text())

    # Query for task details
    sparql = f"""
        SELECT ?p ?o WHERE {{
            <{task_uri}> ?p ?o .
        }}
    """

    results = list(eng.store.query(sparql))

    if not results:
        console.print(f"[yellow]Task not found: {task_uri}[/]")
        return

    console.print(Panel.fit(f"[bold]{task_uri}[/]", border_style="blue"))

    for row in results:
        pred = str(row["p"]).split("#")[-1].split("/")[-1]
        obj = str(row["o"])
        console.print(f"  {pred}: {obj}")
