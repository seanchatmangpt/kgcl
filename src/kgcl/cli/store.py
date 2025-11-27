"""Store CLI commands.

kgcl store <verb> - Triple store operations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def store() -> None:
    """Triple store operations.

    \b
    Commands:
      query  Execute SPARQL query
      load   Load RDF data
      dump   Dump store contents
      repl   Interactive SPARQL shell
    """


@store.command()
@click.argument("sparql")
@click.option("--file", "-f", type=click.Path(exists=True), help="Load data from file first")
@click.option("--format", "-o", type=click.Choice(["table", "csv", "json"]), default="table")
def query(sparql: str, file: str | None, format: str) -> None:
    """Execute SPARQL query.

    SPARQL can be a query string or path to .sparql file.
    """
    from kgcl.hybrid import HybridEngine

    # Check if sparql is a file
    sparql_path = Path(sparql)
    if sparql_path.exists() and sparql_path.suffix == ".sparql":
        sparql = sparql_path.read_text()

    eng = HybridEngine()

    if file:
        eng.load_data(Path(file).read_text())

    try:
        query_result = eng.store.query(sparql)

        # Get variables from the QuerySolutions object before consuming
        variables = list(query_result.variables)
        results = list(query_result)

        if not results:
            console.print("[yellow]No results[/]")
            return

        if format == "table":
            table = Table(title="Results")
            for var in variables:
                table.add_column(str(var).lstrip("?"), style="cyan")
            for row in results:
                table.add_row(*[str(row[var]) for var in variables])
            console.print(table)

        elif format == "csv":
            print(",".join(str(var).lstrip("?") for var in variables))
            for row in results:
                print(",".join(str(row[var]) for var in variables))

        elif format == "json":
            output = [{str(var).lstrip("?"): str(row[var]) for var in variables} for row in results]
            print(json.dumps(output, indent=2))

        console.print(f"\n[green]{len(results)} results[/]")

    except Exception as e:
        console.print(f"[bold red]Query error:[/] {e}")
        sys.exit(1)


@store.command()
@click.argument("file", type=click.Path(exists=True))
def load(file: str) -> None:
    """Load RDF data from file."""
    from kgcl.hybrid import HybridEngine

    path = Path(file)
    eng = HybridEngine()
    eng.load_data(path.read_text())

    console.print(f"[green]Loaded {len(list(eng.store))} triples from {path.name}[/]")


@store.command()
@click.argument("file", type=click.Path(exists=True))
def dump(file: str) -> None:
    """Dump store contents after loading file."""
    from kgcl.hybrid import HybridEngine

    path = Path(file)
    eng = HybridEngine()
    eng.load_data(path.read_text())

    for quad in eng.store:
        print(f"{quad.subject} {quad.predicate} {quad.object} .")


@store.command()
@click.option("--persistent", "-p", type=click.Path(), help="Path for persistent store")
def repl(persistent: str | None) -> None:
    """Interactive SPARQL shell.

    Type queries interactively. 'exit' or Ctrl+D to quit.
    """
    from kgcl.hybrid import HybridEngine

    eng = HybridEngine(store_path=persistent)
    store_type = "persistent" if persistent else "in-memory"

    console.print(Panel.fit(f"[bold]SPARQL REPL[/] ({store_type})", border_style="blue"))
    console.print("Enter queries. 'exit' or Ctrl+D to quit.\n")

    while True:
        try:
            q = console.input("[bold cyan]sparql>[/] ")
            if q.lower() in ("exit", "quit", "q"):
                break
            if not q.strip():
                continue

            results = list(eng.store.query(q))
            if results:
                for row in results:
                    console.print(f"  {row}")
                console.print(f"[green]{len(results)} results[/]\n")
            else:
                console.print("[yellow]No results[/]\n")

        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error:[/] {e}\n")

    console.print("[dim]Goodbye![/]")
