"""System CLI commands.

kgcl system <verb> - System management.
"""

from __future__ import annotations

import subprocess
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
system = typer.Typer(help="System management", no_args_is_help=True)


@system.command()
def check() -> None:
    """Check all system components."""
    console.print(Panel.fit("[bold]System Check[/]", border_style="blue"))

    checks = []

    # Python
    import sys as sys_mod

    checks.append(("Python", True, sys_mod.version.split()[0]))

    # PyOxigraph
    try:
        import pyoxigraph

        ver = pyoxigraph.__version__ if hasattr(pyoxigraph, "__version__") else "installed"
        checks.append(("PyOxigraph", True, ver))
    except ImportError:
        checks.append(("PyOxigraph", False, "not installed"))

    # EYE
    try:
        result = subprocess.run(["eye", "--version"], check=False, capture_output=True, text=True, timeout=5)
        ver = result.stdout.strip() or result.stderr.strip()
        checks.append(("EYE Reasoner", True, ver))
    except FileNotFoundError:
        checks.append(("EYE Reasoner", False, "not installed"))
    except subprocess.TimeoutExpired:
        checks.append(("EYE Reasoner", False, "timeout"))

    # HybridEngine
    try:
        from kgcl.hybrid import HybridEngine

        HybridEngine()
        checks.append(("HybridEngine", True, "ready"))
    except Exception as e:
        checks.append(("HybridEngine", False, str(e)))

    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Version/Info", style="dim")

    for name, ok, info in checks:
        icon = "[green]✓[/]" if ok else "[red]✗[/]"
        table.add_row(name, icon, info)

    console.print(table)

    all_ok = all(c[1] for c in checks)
    if all_ok:
        console.print("\n[bold green]All systems ready![/]")
    else:
        console.print("\n[bold red]Some components need attention[/]")
        raise typer.Exit(code=1)


@system.command()
def info() -> None:
    """Show system information."""
    console.print(Panel.fit("[bold]KGCL System Info[/]", border_style="blue"))

    console.print("\n[bold]Architecture:[/]")
    console.print("  PyOxigraph = Matter (Inert State Storage in Rust)")
    console.print("  EYE Reasoner = Physics (External Force via subprocess)")
    console.print("  Python = Time (Tick Controller/Orchestrator)")

    console.print("\n[bold]Workflow Control Patterns:[/]")
    console.print("  WCP-1  Sequence       Basic task flow")
    console.print("  WCP-2  AND-Split      Parallel activation")
    console.print("  WCP-3  AND-Join       Synchronization")
    console.print("  WCP-4  XOR-Split      Exclusive choice")
    console.print("  WCP-5  Simple Merge   Multiple paths merge")
