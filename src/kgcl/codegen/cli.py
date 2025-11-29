"""Command-line interface for unified code generation from RDF ontologies.

Supports multiple output formats: DSPy signatures, YAWL specifications,
Python modules (dataclass/pydantic/plain), and more. Provides batch processing,
caching, and performance instrumentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from kgcl.codegen.orchestrator import CodeGenOrchestrator, GenerationConfig, OutputFormat

codegen = typer.Typer(help="Code generation from RDF ontologies", no_args_is_help=True)


def collect_input_files(paths: list[str | Path]) -> list[Path]:
    """Collect all TTL files from paths (files and directories).

    Parameters
    ----------
    paths : list[str | Path]
        List of file paths and/or directory paths to process

    Returns
    -------
    list[Path]
        Flattened list of all .ttl files found

    Examples
    --------
    >>> files = collect_input_files(["ontology.ttl", "schemas/"])
    >>> all(f.suffix == ".ttl" for f in files)
    True
    """
    collected: list[Path] = []

    for path_input in paths:
        path = Path(path_input)

        # Skip nonexistent paths
        if not path.exists():
            continue

        if path.is_file() and path.suffix.lower() in {".ttl", ".rdf", ".owl", ".n3", ".turtle"}:
            collected.append(path)
        elif path.is_dir():
            # Recursively find all RDF files
            for ext in ("*.ttl", "*.rdf", "*.owl", "*.n3", "*.turtle"):
                collected.extend(path.rglob(ext))

    return collected


@codegen.command()
def generate(
    input_files: Annotated[list[str], typer.Argument(help="TTL/RDF/OWL input files or directories")],
    output: Annotated[Path | None, typer.Argument(help="Output file/directory path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "dspy",
    template_dir: Annotated[
        Path | None, typer.Option("--template-dir", help="Custom template directory (optional for some formats)")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Don't write output files, just validate")] = False,
    cache_size: Annotated[int, typer.Option("--cache-size", help="Graph cache size for DSPy")] = 100,
    max_workers: Annotated[int, typer.Option("--max-workers", help="Maximum parallel workers for DSPy")] = 4,
    dspy_model: Annotated[str | None, typer.Option("--dspy-model", help="DSPy model to configure")] = None,
    dspy_api_base: Annotated[str | None, typer.Option("--dspy-api-base", help="DSPy API base URL")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output with metrics")] = False,
) -> None:
    """Generate code from RDF ontologies in multiple formats.

    Supported formats: dspy, yawl, python-dataclass, python-pydantic, python-plain

    Examples
    --------
    $ kgcl codegen generate ontology.ttl output.py --format dspy
    $ kgcl codegen generate schema/ generated/ --format python-dataclass
    """
    # Validate format
    valid_formats = ["dspy", "yawl", "python-dataclass", "python-pydantic", "python-plain"]
    if format not in valid_formats:
        typer.echo(f"Error: Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}", err=True)
        raise typer.Exit(code=1)

    # Collect input files
    input_paths = collect_input_files(input_files)

    if not input_paths:
        typer.echo("Error: No TTL/RDF/OWL files found in specified paths", err=True)
        raise typer.Exit(code=2)

    # Determine output directory
    if output is None:
        # Auto-generate based on format
        output_dir = Path("generated") / format
        output_path = None
    elif output.is_dir() or (not output.exists() and not output.suffix):
        # Output is a directory
        output_dir = output
        output_path = None  # Let generator decide filename
    else:
        # Output is a file
        output_dir = output.parent
        output_path = output

    if verbose:
        typer.echo(f"Processing {len(input_paths)} ontology files...")
        typer.echo(f"Output format: {format}")
        typer.echo(f"Output directory: {output_dir}")

    # Create orchestrator and configuration
    orchestrator = CodeGenOrchestrator()

    config = GenerationConfig(
        format=OutputFormat(format),
        output_dir=output_dir,
        template_dir=template_dir,
        dry_run=dry_run,
        cache_size=cache_size,
        max_workers=max_workers,
        dspy_model=dspy_model,
        dspy_api_base=dspy_api_base,
    )

    # Generate code
    try:
        if len(input_paths) == 1 and output_path:
            # Single file with explicit output path
            result = orchestrator.generate(input_paths[0], config, output_path=output_path)
            results = [result]
        else:
            # Multiple files or auto-generated paths
            results = orchestrator.generate_multiple(input_paths, config)

        if verbose:
            typer.echo(f"\nSuccessfully generated {len(results)} output file(s):")
            for result in results:
                typer.echo(f"  {result.output_path}")
                if "signatures_generated" in result.metadata:
                    typer.echo(f"    - Signatures: {result.metadata['signatures_generated']}")
                if "processing_time_ms" in result.metadata:
                    typer.echo(f"    - Processing time: {result.metadata['processing_time_ms']:.1f}ms")

    except Exception as e:
        typer.echo(f"Error during generation: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(code=1)


@codegen.command("list-formats")
def list_formats() -> None:
    """List supported output formats."""
    orchestrator = CodeGenOrchestrator()
    typer.echo("Supported output formats:")
    for fmt in orchestrator.list_formats():
        info = orchestrator.get_format_info(fmt)
        typer.echo(f"  {fmt:20s} - {info.get('description', 'No description')}")


def main(args: list[str] | None = None) -> int:
    """Main entry point for testing and CLI execution.

    Parameters
    ----------
    args : list[str] | None
        Command line arguments (for testing)

    Returns
    -------
    int
        Exit code
    """
    try:
        codegen(args)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    codegen()
