"""Engine CLI commands.

kgcl engine <verb> - HybridEngine operations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def engine() -> None:
    """HybridEngine operations.

    \b
    Commands:
      run     Run physics to convergence
      tick    Execute single physics tick
      status  Show engine status
    """


@engine.command()
@click.argument("topology", type=click.Path(exists=True))
@click.option("--max-ticks", "-t", default=100, help="Maximum ticks to run")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(topology: str, max_ticks: int, verbose: bool) -> None:
    """Run physics to convergence.

    Load topology and apply N3 physics rules until fixed point.
    """
    from kgcl.hybrid import HybridEngine

    path = Path(topology)
    console.print(f"[bold blue]Loading:[/] {path.name}")

    try:
        eng = HybridEngine()
        eng.load_data(path.read_text())

        console.print(f"[green]Loaded {len(list(eng.store))} triples[/]")
        console.print(f"[bold]Running physics (max {max_ticks} ticks)...[/]")

        results = eng.run_to_completion(max_ticks=max_ticks)

        table = Table(title="Physics Results")
        table.add_column("Tick", style="cyan")
        table.add_column("Duration (ms)", style="magenta")
        table.add_column("Delta", style="green")
        table.add_column("Converged", style="yellow")

        for r in results:
            table.add_row(str(r.tick_number), f"{r.duration_ms:.2f}", str(r.delta), "Yes" if r.converged else "No")

        console.print(table)

        if verbose:
            statuses = eng.inspect()
            if statuses:
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


@engine.command()
@click.argument("topology", type=click.Path(exists=True))
def tick(topology: str) -> None:
    """Execute single physics tick.

    Apply one round of N3 reasoning and show delta.
    """
    from kgcl.hybrid import HybridEngine

    path = Path(topology)
    eng = HybridEngine()
    eng.load_data(path.read_text())

    console.print(f"[bold blue]Loaded:[/] {len(list(eng.store))} triples")

    try:
        result = eng.apply_physics()
        console.print(f"[green]Tick {result.tick_number}:[/] +{result.delta} triples in {result.duration_ms:.2f}ms")
        console.print(f"Converged: {'Yes' if result.converged else 'No'}")
    except FileNotFoundError:
        console.print("[bold red]Error:[/] EYE reasoner not installed")
        sys.exit(1)


@engine.command()
def status() -> None:
    """Show engine status and components."""
    import subprocess

    from kgcl.hybrid import HybridEngine

    console.print(Panel.fit("[bold]Engine Status[/]", border_style="blue"))

    # PyOxigraph
    try:
        import pyoxigraph

        ver = pyoxigraph.__version__ if hasattr(pyoxigraph, "__version__") else "installed"
        console.print(f"[green]✓[/] PyOxigraph: {ver}")
    except ImportError:
        console.print("[red]✗[/] PyOxigraph: not installed")

    # EYE
    try:
        result = subprocess.run(["eye", "--version"], check=False, capture_output=True, text=True, timeout=5)
        version = result.stdout.strip() or result.stderr.strip()
        console.print(f"[green]✓[/] EYE Reasoner: {version}")
    except FileNotFoundError:
        console.print("[red]✗[/] EYE Reasoner: not installed")
    except subprocess.TimeoutExpired:
        console.print("[yellow]?[/] EYE Reasoner: timeout")

    # Engine
    try:
        HybridEngine()
        console.print("[green]✓[/] HybridEngine: ready")
    except Exception as e:
        console.print(f"[red]✗[/] HybridEngine: {e}")
