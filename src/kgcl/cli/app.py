"""Main KGCL CLI application.

Provides commands for working with the HybridEngine (PyOxigraph + EYE).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="2.0.0", prog_name="kgcl")
def app() -> None:
    """KGCL - Knowledge Geometry Calculus for Life.

    A hybrid RDF engine combining PyOxigraph (Rust storage) with
    EYE reasoner (N3 logic) for knowledge graph evolution.
    """


@app.command()
@click.argument("turtle_file", type=click.Path(exists=True))
@click.option("--max-ticks", "-t", default=100, help="Maximum ticks to run")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(turtle_file: str, max_ticks: int, verbose: bool) -> None:
    """Run HybridEngine on a Turtle topology file.

    Loads the RDF topology and applies N3 physics rules until
    convergence (fixed point) or max ticks reached.
    """
    from kgcl.hybrid import HybridEngine

    path = Path(turtle_file)
    console.print(f"[bold blue]Loading topology:[/] {path.name}")

    try:
        engine = HybridEngine()
        data = path.read_text()
        engine.load_data(data)

        console.print(f"[green]Loaded {len(list(engine.store))} triples[/]")
        console.print(f"[bold]Running physics (max {max_ticks} ticks)...[/]")

        results = engine.run_to_completion(max_ticks=max_ticks)

        # Summary table
        table = Table(title="Physics Results")
        table.add_column("Tick", style="cyan")
        table.add_column("Duration (ms)", style="magenta")
        table.add_column("Delta", style="green")
        table.add_column("Converged", style="yellow")

        for r in results:
            table.add_row(str(r.tick_number), f"{r.duration_ms:.2f}", str(r.delta), "Yes" if r.converged else "No")

        console.print(table)

        # Final status
        statuses = engine.inspect()
        if statuses and verbose:
            console.print("\n[bold]Final Task Statuses:[/]")
            for task, status in sorted(statuses.items()):
                color = {"Active": "green", "Completed": "blue", "Archived": "dim"}.get(status, "white")
                console.print(f"  [{color}]{task}[/]: {status}")

        console.print(f"\n[bold green]Converged after {len(results)} ticks[/]")

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/] {e}")
        console.print("[yellow]Hint: Install EYE reasoner from https://github.com/eyereasoner/eye[/]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@app.command()
@click.argument("sparql_query")
@click.option("--store", "-s", type=click.Path(exists=True), help="Path to persistent store")
def query(sparql_query: str, store: str | None) -> None:
    """Execute a SPARQL query against the store.

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

    console.print("[bold blue]Executing query...[/]")

    try:
        results = list(engine.store.query(sparql))

        if not results:
            console.print("[yellow]No results found[/]")
            return

        # Display results
        table = Table(title="Query Results")

        # Get variables from first result
        if results:
            first = results[0]
            for var in first:
                table.add_column(str(var), style="cyan")

            for row in results:
                table.add_row(*[str(row[var]) for var in first])

        console.print(table)
        console.print(f"\n[green]{len(results)} results[/]")

    except Exception as e:
        console.print(f"[bold red]Query error:[/] {e}")
        sys.exit(1)


@app.command()
def status() -> None:
    """Show HybridEngine status and capabilities."""
    import subprocess

    from kgcl.hybrid import HybridEngine

    console.print(Panel.fit("[bold]KGCL HybridEngine Status[/]", border_style="blue"))

    # Check PyOxigraph
    try:
        import pyoxigraph

        console.print(
            f"[green]\u2713[/] PyOxigraph: {pyoxigraph.__version__ if hasattr(pyoxigraph, '__version__') else 'installed'}"
        )
    except ImportError:
        console.print("[red]\u2717[/] PyOxigraph: not installed")

    # Check EYE reasoner
    try:
        result = subprocess.run(["eye", "--version"], check=False, capture_output=True, text=True, timeout=5)
        version = result.stdout.strip() or result.stderr.strip()
        console.print(f"[green]\u2713[/] EYE Reasoner: {version}")
    except FileNotFoundError:
        console.print("[red]\u2717[/] EYE Reasoner: not installed")
        console.print("  [yellow]Install from: https://github.com/eyereasoner/eye[/]")
    except subprocess.TimeoutExpired:
        console.print("[yellow]?[/] EYE Reasoner: timeout checking version")

    # Test engine creation
    try:
        engine = HybridEngine()
        console.print("[green]\u2713[/] HybridEngine: ready (in-memory store)")
    except Exception as e:
        console.print(f"[red]\u2717[/] HybridEngine: {e}")


@app.command()
@click.argument("turtle_file", type=click.Path(exists=True))
def inspect(turtle_file: str) -> None:
    """Inspect task statuses in a topology file."""
    from kgcl.hybrid import HybridEngine

    path = Path(turtle_file)
    engine = HybridEngine()
    engine.load_data(path.read_text())

    statuses = engine.inspect()

    if not statuses:
        console.print("[yellow]No task statuses found[/]")
        return

    table = Table(title=f"Task Statuses: {path.name}")
    table.add_column("Task", style="cyan")
    table.add_column("Status", style="green")

    for task, status in sorted(statuses.items()):
        table.add_row(task, status)

    console.print(table)


@app.command()
@click.option("--persistent", "-p", type=click.Path(), help="Path for persistent store")
def repl(persistent: str | None) -> None:
    """Start interactive SPARQL REPL.

    Enter SPARQL queries interactively. Type 'exit' or Ctrl+D to quit.
    """
    from kgcl.hybrid import HybridEngine

    engine = HybridEngine(store_path=persistent)
    store_type = "persistent" if persistent else "in-memory"

    console.print(Panel.fit(f"[bold]KGCL SPARQL REPL[/] ({store_type})", border_style="blue"))
    console.print("Enter SPARQL queries. Type 'exit' or Ctrl+D to quit.\n")

    while True:
        try:
            query_input = console.input("[bold cyan]sparql>[/] ")
            if query_input.lower() in ("exit", "quit", "q"):
                break
            if not query_input.strip():
                continue

            results = list(engine.store.query(query_input))
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


if __name__ == "__main__":
    app()
