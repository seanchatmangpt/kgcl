"""KGCL Command Line Interface.

This module provides CLI commands for the Knowledge Geometry Calculus for Life
engine, integrating the HybridEngine (PyOxigraph + EYE) with user-friendly commands.
"""

from __future__ import annotations

__all__ = ["main"]


def main() -> None:
    """Entry point for KGCL CLI."""
    from kgcl.cli.app import app

    app()
