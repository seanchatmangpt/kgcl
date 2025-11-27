"""Physics CLI commands.

kgcl physics <verb> - N3 physics rules.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
def physics() -> None:
    """N3 physics rules.

    \b
    Commands:
      show      Show current physics rules
      validate  Validate rules syntax
    """


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
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Invalid N3:[/] {e.stderr}")
            sys.exit(1)
