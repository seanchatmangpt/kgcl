"""Physics CLI commands.

kgcl physics <verb> - N3 physics rules.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
physics = typer.Typer(help="N3 physics rules", no_args_is_help=True)


@physics.command()
def show() -> None:
    """Show current N3 physics rules."""
    from kgcl.hybrid.hybrid_engine import N3_PHYSICS

    console.print(Panel.fit("[bold]N3 Physics Rules[/]", border_style="blue"))
    console.print(N3_PHYSICS)


@physics.command()
def validate() -> None:
    """Validate physics rules syntax."""
    from kgcl.hybrid.hybrid_engine import N3_PHYSICS

    with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
        f.write(N3_PHYSICS)
        f.flush()

        try:
            subprocess.run(["eye", "--nope", "--pass", f.name], check=True, capture_output=True, text=True, timeout=10)
            console.print("[green]✓ Physics rules are valid N3[/]")
        except FileNotFoundError:
            console.print("[red]✗ EYE reasoner not installed[/]")
            raise typer.Exit(code=1)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Invalid N3:[/] {e.stderr}")
            raise typer.Exit(code=1)
