"""Main KGCL CLI application.

Noun-verb structure: kgcl <noun> <verb> [args]

Nouns (resources):
  engine  - HybridEngine operations (run, tick, status)
  store   - Triple store operations (query, load, dump, repl)
  task    - Task management (list, inspect)
  physics - N3 physics rules (show, validate)
  system  - System management (check, info)
"""

from __future__ import annotations

import click

from kgcl.cli.engine import engine
from kgcl.cli.physics import physics
from kgcl.cli.store import store
from kgcl.cli.system import system
from kgcl.cli.task import task


@click.group()
@click.version_option(version="2.0.0", prog_name="kgcl")
def app() -> None:
    """KGCL - Knowledge Geometry Calculus for Life.

    A hybrid RDF engine combining PyOxigraph (Rust storage) with
    EYE reasoner (N3 logic) for knowledge graph evolution.

    \b
    Structure: kgcl <noun> <verb> [args]

    \b
    Examples:
      kgcl engine run topology.ttl
      kgcl store query "SELECT * WHERE { ?s ?p ?o }"
      kgcl task list topology.ttl
      kgcl physics show
      kgcl system check
    """


# Register noun groups
app.add_command(engine)
app.add_command(store)
app.add_command(task)
app.add_command(physics)
app.add_command(system)


if __name__ == "__main__":
    app()
