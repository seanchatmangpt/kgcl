"""Feature list CLI command.

Lists available KGCL features and capabilities.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.command()
def feature_list() -> None:
    """List KGCL features and capabilities.

    Shows all available features of the HybridEngine.
    """
    console.print(Panel.fit("[bold]KGCL Feature List[/]", border_style="blue"))

    table = Table(title="Core Features")
    table.add_column("Feature", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    features = [
        ("PyOxigraph Store", "Rust-based RDF triple store (in-memory or persistent)", "Active"),
        ("EYE Reasoner", "N3 logic reasoning via subprocess", "Active"),
        ("N3 Physics", "Declarative workflow rules using implications (=>)", "Active"),
        ("SPARQL Queries", "Full SPARQL 1.1 query support", "Active"),
        ("Tick Execution", "Epoch-based physics application with convergence detection", "Active"),
        ("WCP-1 Sequence", "Basic task flow progression", "Active"),
        ("WCP-2 AND-Split", "Parallel task activation", "Active"),
        ("WCP-3 AND-Join", "Synchronization (requires all inputs)", "Active"),
        ("WCP-4 XOR-Split", "Exclusive choice with predicates", "Active"),
        ("WCP-5 Simple Merge", "Multiple paths to single successor", "Active"),
    ]

    for name, desc, status in features:
        table.add_row(name, desc, status)

    console.print(table)

    console.print("\n[bold]Architecture:[/]")
    console.print("  PyOxigraph = Matter (Inert State Storage in Rust)")
    console.print("  EYE Reasoner = Physics (External Force via subprocess)")
    console.print("  Python = Time (Tick Controller/Orchestrator)")


if __name__ == "__main__":
    feature_list()
