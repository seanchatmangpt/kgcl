"""CLI interface for the UNRDF engine.

Provides command-line tools for ingestion, querying, and graph management.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from opentelemetry import trace
from rdflib import URIRef

from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.hooks import HookExecutor, HookRegistry
from kgcl.unrdf_engine.ingestion import IngestionPipeline
from kgcl.unrdf_engine.validation import ShaclValidator

tracer = trace.get_tracer(__name__)


@click.group()
@click.option(
    "--graph-file",
    type=click.Path(path_type=Path),
    help="Path to RDF graph file (Turtle format)",
)
@click.pass_context
def cli(ctx: click.Context, graph_file: Path | None) -> None:
    """UNRDF Knowledge Engine CLI.

    Manage RDF triple stores with SPARQL, transactions, hooks, and validation.
    """
    ctx.ensure_object(dict)
    ctx.obj["graph_file"] = graph_file


@cli.command()
@click.argument("data_file", type=click.Path(exists=True, path_type=Path))
@click.option("--agent", default="cli", help="Agent performing ingestion")
@click.option("--reason", help="Reason for ingestion")
@click.option("--shapes", type=click.Path(exists=True, path_type=Path), help="SHACL shapes file")
@click.option("--validate/--no-validate", default=True, help="Validate data before committing")
@click.option("--base-uri", default="http://unrdf.org/data/", help="Base URI for entities")
@click.pass_context
def ingest(
    ctx: click.Context,
    data_file: Path,
    agent: str,
    reason: str | None,
    shapes: Path | None,
    validate: bool,
    base_uri: str,
) -> None:
    """Ingest JSON data into the RDF graph.

    DATA_FILE: Path to JSON file containing data to ingest (object or array).
    """
    with tracer.start_as_current_span("cli.ingest") as span:
        span.set_attribute("data.file", str(data_file))
        span.set_attribute("agent", agent)

        # Load data
        with data_file.open() as f:
            data = json.load(f)

        # Initialize engine
        engine = UnrdfEngine(file_path=ctx.obj.get("graph_file"))

        # Initialize validator if shapes provided
        validator = None
        if shapes:
            validator = ShaclValidator()
            validator.load_shapes(shapes)

        # Initialize pipeline
        pipeline = IngestionPipeline(
            engine=engine,
            validator=validator,
            validate_on_ingest=validate,
        )

        # Ingest data
        result = pipeline.ingest_json(data=data, agent=agent, reason=reason, base_uri=base_uri)

        # Output result
        click.echo(json.dumps(result.to_dict(), indent=2))

        if result.success:
            # Save graph
            if ctx.obj.get("graph_file"):
                engine.save_to_file()
                click.echo(f"\nGraph saved to {ctx.obj['graph_file']}")
            sys.exit(0)
        else:
            click.echo(f"\nIngestion failed: {result.error}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("sparql_query")
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="table")
@click.pass_context
def query(ctx: click.Context, sparql_query: str, output_format: str) -> None:
    """Execute SPARQL query against the graph.

    SPARQL_QUERY: SPARQL query string or path to query file.
    """
    with tracer.start_as_current_span("cli.query") as span:
        # Load query from file if it's a path
        query_text = sparql_query
        if Path(sparql_query).exists():
            query_text = Path(sparql_query).read_text()
            span.set_attribute("query.file", sparql_query)

        span.set_attribute("query.text", query_text)

        # Initialize engine
        engine = UnrdfEngine(file_path=ctx.obj.get("graph_file"))

        # Execute query
        results = engine.query(query_text)

        # Format output
        if output_format == "json":
            output = []
            for row in results:
                output.append({str(var): str(row[var]) for var in results.vars})
            click.echo(json.dumps(output, indent=2))
        else:
            # Table format
            if results.vars:
                # Header
                header = "\t".join(str(var) for var in results.vars)
                click.echo(header)
                click.echo("-" * len(header))

                # Rows
                for row in results:
                    values = "\t".join(str(row[var]) for var in results.vars)
                    click.echo(values)
            else:
                click.echo("No results")


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Display graph statistics."""
    with tracer.start_as_current_span("cli.stats"):
        engine = UnrdfEngine(file_path=ctx.obj.get("graph_file"))
        stats_data = engine.export_stats()

        click.echo("UNRDF Engine Statistics")
        click.echo("=" * 40)
        for key, value in stats_data.items():
            click.echo(f"{key:20s}: {value}")


@cli.command()
@click.argument("subject")
@click.option("--format", "output_format", type=click.Choice(["json", "turtle"]), default="json")
@click.pass_context
def provenance(ctx: click.Context, subject: str, output_format: str) -> None:
    """Get provenance information for triples involving a subject.

    SUBJECT: Subject URI to query provenance for.
    """
    with tracer.start_as_current_span("cli.provenance") as span:
        span.set_attribute("subject", subject)

        engine = UnrdfEngine(file_path=ctx.obj.get("graph_file"))
        subject_uri = URIRef(subject)

        # Get all triples with this subject
        provenance_data = []
        for s, p, o in engine.triples(subject=subject_uri):
            prov = engine.get_provenance(s, p, o)
            if prov:
                provenance_data.append(
                    {
                        "triple": {"subject": str(s), "predicate": str(p), "object": str(o)},
                        "provenance": prov.to_dict(),
                    }
                )

        if output_format == "json":
            click.echo(json.dumps(provenance_data, indent=2))
        else:
            for item in provenance_data:
                triple = item["triple"]
                prov = item["provenance"]
                click.echo(f"\nTriple: {triple['predicate']}")
                click.echo(f"  Object: {triple['object']}")
                click.echo(f"  Agent: {prov['agent']}")
                click.echo(f"  Timestamp: {prov['timestamp']}")
                if prov["reason"]:
                    click.echo(f"  Reason: {prov['reason']}")


@cli.command()
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["turtle", "xml", "json-ld"]), default="turtle")
@click.pass_context
def export(ctx: click.Context, output_file: Path, output_format: str) -> None:
    """Export graph to file.

    OUTPUT_FILE: Path to output file.
    """
    with tracer.start_as_current_span("cli.export") as span:
        span.set_attribute("output.file", str(output_file))
        span.set_attribute("output.format", output_format)

        engine = UnrdfEngine(file_path=ctx.obj.get("graph_file"))

        # Map format names to rdflib format strings
        format_map = {"turtle": "turtle", "xml": "xml", "json-ld": "json-ld"}

        engine.graph.serialize(destination=output_file, format=format_map[output_format])
        click.echo(f"Graph exported to {output_file} ({output_format})")


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
