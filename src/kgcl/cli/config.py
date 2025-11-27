"""Config CLI command.

Manage KGCL configuration.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--show", "-s", is_flag=True, help="Show current configuration")
@click.option("--check", "-c", is_flag=True, help="Check system requirements")
def config(show: bool, check: bool) -> None:
    """Manage KGCL configuration.

    View and verify system configuration and dependencies.
    """
    if check or (not show and not check):
        _check_requirements()

    if show:
        _show_config()


def _check_requirements() -> None:
    """Check system requirements."""
    console.print(Panel.fit("[bold]System Requirements Check[/]", border_style="blue"))

    # Check Python
    import sys

    console.print(f"[green]\u2713[/] Python: {sys.version.split()[0]}")

    # Check PyOxigraph
    try:
        import pyoxigraph

        ver = pyoxigraph.__version__ if hasattr(pyoxigraph, "__version__") else "installed"
        console.print(f"[green]\u2713[/] PyOxigraph: {ver}")
    except ImportError:
        console.print("[red]\u2717[/] PyOxigraph: not installed")
        console.print("  [yellow]Run: pip install pyoxigraph[/]")

    # Check EYE
    try:
        result = subprocess.run(["eye", "--version"], check=False, capture_output=True, text=True, timeout=5)
        version = result.stdout.strip() or result.stderr.strip()
        console.print(f"[green]\u2713[/] EYE Reasoner: {version}")
    except FileNotFoundError:
        console.print("[red]\u2717[/] EYE Reasoner: not installed")
        console.print("  [yellow]Install from: https://github.com/eyereasoner/eye[/]")
    except subprocess.TimeoutExpired:
        console.print("[yellow]?[/] EYE Reasoner: timeout")

    # Check rdflib
    try:
        import rdflib

        console.print(f"[green]\u2713[/] rdflib: {rdflib.__version__}")
    except ImportError:
        console.print("[red]\u2717[/] rdflib: not installed")

    # Check click
    try:
        import click as click_lib

        console.print(f"[green]\u2713[/] click: {click_lib.__version__}")
    except ImportError:
        console.print("[red]\u2717[/] click: not installed")

    # Check rich
    try:
        from importlib.metadata import version

        rich_version = version("rich")
        console.print(f"[green]\u2713[/] rich: {rich_version}")
    except Exception:
        console.print("[red]\u2717[/] rich: not installed")


def _show_config() -> None:
    """Show current configuration."""
    console.print(Panel.fit("[bold]Current Configuration[/]", border_style="blue"))

    # Check for config file
    config_paths = [
        Path.home() / ".kgcl" / "config.yaml",
        Path.cwd() / ".kgcl" / "config.yaml",
        Path.cwd() / "kgcl.yaml",
    ]

    for path in config_paths:
        if path.exists():
            console.print(f"[green]Config file:[/] {path}")
            console.print(path.read_text())
            return

    console.print("[yellow]No configuration file found[/]")
    console.print("Searched locations:")
    for path in config_paths:
        console.print(f"  - {path}")


if __name__ == "__main__":
    config()
