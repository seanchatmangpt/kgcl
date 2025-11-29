"""CLI for semantic code porting tool.

Provides Typer-based CLI with commands for ingestion, delta detection,
porting suggestions, and MCP server mode.
"""

from pathlib import Path

import typer

from kgcl.porting.engine.delta_inference import DeltaInference
from kgcl.porting.engine.pattern_matcher import PatternMatcher
from kgcl.porting.engine.porting_engine import PortingEngine
from kgcl.porting.mcp.server import PortingMCPServer

app = typer.Typer(help="Semantic Code Porting Tool - Hybrid Engine Architecture")


@app.command()
def ingest(
    java_root: Path | None = typer.Option(None, "--java-root", "-j", help="Root directory of Java code"),
    python_root: Path | None = typer.Option(None, "--python-root", "-p", help="Root directory of Python code"),
    store_path: Path = typer.Option(Path("porting_store"), "--store", help="Path for RDF store"),
) -> None:
    """Ingest codebases into RDF store.

    Examples
    --------
    $ porting ingest --java-root vendors/yawl-v5.2/src --python-root src/kgcl/yawl
    """
    engine = PortingEngine(store_path=store_path)

    if java_root:
        typer.echo(f"Ingesting Java codebase from {java_root}...")
        java_count = engine.ingest_java(java_root)
        typer.echo(f"✓ Ingested {java_count} Java classes")

    if python_root:
        typer.echo(f"Ingesting Python codebase from {python_root}...")
        python_count = engine.ingest_python(python_root)
        typer.echo(f"✓ Ingested {python_count} Python classes")

    if not java_root and not python_root:
        typer.echo("Error: Must specify at least one of --java-root or --python-root", err=True)
        raise typer.Exit(1)


@app.command()
def detect(
    store_path: Path = typer.Option(Path("porting_store"), "--store", help="Path to RDF store"),
    rules_path: Path | None = typer.Option(None, "--rules", help="Path to N3 rules file"),
    output: Path = typer.Option(Path("deltas.json"), "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or yaml"),
) -> None:
    """Detect deltas between codebases using N3 rules or SPARQL.

    Examples
    --------
    $ porting detect --store porting_store --rules ontology/porting/structural-rules.n3
    """
    import json

    import yaml

    engine = PortingEngine(store_path=store_path)
    pattern_matcher = PatternMatcher(engine.codebase)
    delta_inference = DeltaInference(engine)

    typer.echo("Detecting deltas...")

    if rules_path and rules_path.exists():
        typer.echo(f"Using N3 rules from {rules_path}")
        deltas = delta_inference.infer_deltas(rules_path)
    else:
        typer.echo("Using SPARQL-based pattern matching")
        deltas = {
            "missing_classes": pattern_matcher.find_missing_classes(),
            "missing_methods": pattern_matcher.find_missing_methods(),
            "signature_mismatches": pattern_matcher.find_signature_mismatches(),
            "semantic_deltas": pattern_matcher.find_semantic_deltas(),
        }

    # Export results
    if format.lower() == "json":
        output.write_text(json.dumps(deltas, indent=2))
    elif format.lower() == "yaml":
        output.write_text(yaml.dump(deltas, default_flow_style=False))
    else:
        typer.echo(f"Error: Unsupported format: {format}", err=True)
        raise typer.Exit(1)

    typer.echo(f"✓ Exported deltas to {output}")
    typer.echo(f"  Missing classes: {len(deltas.get('missing_classes', []))}")
    typer.echo(f"  Missing methods: {len(deltas.get('missing_methods', []))}")
    typer.echo(f"  Signature mismatches: {len(deltas.get('signature_mismatches', []))}")


@app.command()
def suggest(
    class_name: str = typer.Argument(..., help="Class name to suggest porting for"),
    store_path: Path = typer.Option(Path("porting_store"), "--store", help="Path to RDF store"),
) -> None:
    """Suggest porting strategy for a class.

    Examples
    --------
    $ porting suggest YEngine --store porting_store
    """
    engine = PortingEngine(store_path=store_path)
    pattern_matcher = PatternMatcher(engine.codebase)

    typer.echo(f"Analyzing porting for class: {class_name}")

    missing_methods = pattern_matcher.find_missing_methods(class_name=class_name)
    signature_mismatches = pattern_matcher.find_signature_mismatches()

    typer.echo(f"\nMissing methods: {len(missing_methods)}")
    for method in missing_methods[:10]:
        typer.echo(f"  - {method['methodName']}")

    typer.echo(f"\nSignature mismatches: {len(signature_mismatches)}")


@app.command()
def serve(
    java_root: Path | None = typer.Option(None, "--java-root", "-j", help="Root directory of Java code"),
    python_root: Path | None = typer.Option(None, "--python-root", "-p", help="Root directory of Python code"),
    store_path: Path = typer.Option(Path("porting_store"), "--store", help="Path to RDF store"),
    port: int = typer.Option(8000, "--port", help="Server port"),
) -> None:
    """Start MCP server for porting tools.

    Examples
    --------
    $ porting serve --java-root vendors/yawl-v5.2/src --python-root src/kgcl/yawl
    """
    typer.echo("Starting MCP server...")
    typer.echo("Note: Full MCP server implementation requires FastMCP framework")
    typer.echo(f"Server would run on port {port}")

    server = PortingMCPServer(
        java_root=java_root,
        python_root=python_root,
        store_path=store_path,
    )

    typer.echo("MCP server initialized")
    typer.echo("Available tools: detect_deltas, suggest_port, validate_port")
    typer.echo("Note: This is a placeholder - full MCP integration pending FastMCP")


if __name__ == "__main__":
    app()

