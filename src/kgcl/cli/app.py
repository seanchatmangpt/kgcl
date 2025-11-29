"""Main KGCL CLI application.

Noun-verb structure: kgcl <noun> <verb> [args]

Nouns (resources):
  engine  - HybridEngine operations (run, tick, status)
  store   - Triple store operations (query, load, dump, repl)
  task    - Task management (list, inspect)
  physics - N3 physics rules (show, validate)
  system  - System management (check, info)
  yawl    - YAWL workflow engine operations
  proj    - Projection/template rendering
  codegen - Code generation from RDF ontologies
"""

from __future__ import annotations

import typer

from kgcl.cli.engine import engine
from kgcl.cli.physics import physics
from kgcl.cli.store import store
from kgcl.cli.system import system
from kgcl.cli.task import task
from kgcl.cli.yawl import yawl
from kgcl.codegen.cli import codegen
from kgcl.observability.cli import health
from kgcl.projection.cli import proj

app = typer.Typer(
    name="kgcl",
    help="""KGCL - Knowledge Geometry Calculus for Life.

    A hybrid RDF engine combining PyOxigraph (Rust storage) with
    EYE reasoner (N3 logic) for knowledge graph evolution.

    Structure: kgcl <noun> <verb> [args]

    Examples:
      kgcl engine run topology.ttl
      kgcl store query "SELECT * WHERE { ?s ?p ?o }"
      kgcl task list topology.ttl
      kgcl physics show
      kgcl system check
      kgcl yawl spec load workflow.yawl
      kgcl yawl case launch my-workflow
      kgcl codegen generate ontology.ttl output.py --format dspy
    """,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo("kgcl version 2.0.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """KGCL main entry point."""


# Register noun groups as sub-applications
app.add_typer(engine, name="engine", help="HybridEngine operations")
app.add_typer(store, name="store", help="Triple store operations")
app.add_typer(task, name="task", help="Task management")
app.add_typer(physics, name="physics", help="N3 physics rules")
app.add_typer(system, name="system", help="System management")
app.add_typer(yawl, name="yawl", help="YAWL workflow engine operations")
app.add_typer(proj, name="proj", help="Projection/template rendering")
app.add_typer(codegen, name="codegen", help="Code generation from RDF")
app.add_typer(health, name="health", help="Health checks and observability")


if __name__ == "__main__":
    app()
