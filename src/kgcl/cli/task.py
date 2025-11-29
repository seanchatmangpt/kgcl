"""Task CLI commands.

kgcl task <verb> - Task management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
task = typer.Typer(help="Task management", no_args_is_help=True)


@task.command("list")
def task_list(topology: Annotated[Path, typer.Argument(exists=True, help="Topology file to load")]) -> None:
    """List all tasks and their statuses."""
    from kgcl.hybrid import HybridEngine

    eng = HybridEngine()
    eng.load_data(topology.read_text())

    statuses = eng.inspect()

    if not statuses:
        console.print("[yellow]No tasks found[/]")
        return

    table = Table(title=f"Tasks: {topology.name}")
    table.add_column("Task", style="cyan")
    table.add_column("Status", style="green")

    for t, s in sorted(statuses.items()):
        table.add_row(t, s)

    console.print(table)


@task.command()
def inspect(
    topology: Annotated[Path, typer.Argument(exists=True, help="Topology file to load")],
    task_uri: Annotated[str, typer.Argument(help="Task URI to inspect")],
) -> None:
    """Inspect specific task details."""
    from kgcl.hybrid import HybridEngine

    eng = HybridEngine()
    eng.load_data(topology.read_text())

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
