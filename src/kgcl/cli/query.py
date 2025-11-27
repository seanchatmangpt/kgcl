"""Query CLI command.

Execute SPARQL queries against the knowledge graph.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.argument("sparql_query")
@click.option("--store", "-s", type=click.Path(), help="Path to persistent store")
@click.option("--format", "-f", type=click.Choice(["table", "csv", "json"]), default="table")
def query(sparql_query: str, store: str | None, format: str) -> None:
    """Execute SPARQL query against the store.

    SPARQL_QUERY can be a query string or path to a .sparql file.
    """
    from kgcl.hybrid import HybridEngine

    # Check if it's a file path
    query_path = Path(sparql_query)
    if query_path.exists() and query_path.suffix == ".sparql":
        sparql = query_path.read_text()
    else:
        sparql = sparql_query

    engine = HybridEngine(store_path=store)

    try:
        results = list(engine.store.query(sparql))

        if not results:
            console.print("[yellow]No results found[/]")
            return

        if format == "table":
            table = Table(title="Query Results")
            first = results[0]
            for var in first:
                table.add_column(str(var), style="cyan")
            for row in results:
                table.add_row(*[str(row[var]) for var in first])
            console.print(table)

        elif format == "csv":
            first = results[0]
            print(",".join(str(var) for var in first))
            for row in results:
                print(",".join(str(row[var]) for var in first))

        elif format == "json":
            import json

            output = []
            for row in results:
                output.append({str(var): str(row[var]) for var in row})
            print(json.dumps(output, indent=2))

        console.print(f"\n[green]{len(results)} results[/]")

    except Exception as e:
        console.print(f"[bold red]Query error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    query()
