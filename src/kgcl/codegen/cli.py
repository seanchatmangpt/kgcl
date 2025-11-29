"""Command-line interface for unified code generation from RDF ontologies.

Supports multiple output formats: DSPy signatures, YAWL specifications,
Python modules (dataclass/pydantic/plain), and more. Provides batch processing,
caching, and performance instrumentation.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

from kgcl.codegen.orchestrator import CodeGenOrchestrator, GenerationConfig, OutputFormat


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


def main(args: list[str] | None = None) -> int:
    """CLI entry point for unified code generation.

    Parameters
    ----------
    args : list[str] | None, default=None
        Command-line arguments (defaults to sys.argv)

    Returns
    -------
    int
        Exit code (0 for success, non-zero for errors)

    Examples
    --------
    >>> main(["ontology.ttl", "-o", "output.py", "--format", "dspy"])  # doctest: +SKIP
    0
    """
    parser = argparse.ArgumentParser(
        description="Generate code from RDF ontologies in multiple formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("input_files", nargs="*", type=str, help="TTL/RDF/OWL input files or directories")

    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=None,
        help="Output file/directory path (default: auto-generated based on format)",
    )

    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="dspy",
        choices=["dspy", "yawl", "python-dataclass", "python-pydantic", "python-plain"],
        help="Output format (default: dspy)",
    )

    parser.add_argument(
        "--template-dir", type=Path, default=None, help="Custom template directory (optional for some formats)"
    )

    parser.add_argument("--dry-run", action="store_true", help="Don't write output files, just validate")

    parser.add_argument("--cache-size", type=int, default=100, help="Graph cache size for DSPy (default: 100)")

    parser.add_argument("--max-workers", type=int, default=4, help="Maximum parallel workers for DSPy (default: 4)")

    parser.add_argument(
        "--dspy-model",
        type=str,
        default=None,
        help="DSPy model to configure (default: ollama/granite4 from env or config)",
    )

    parser.add_argument(
        "--dspy-api-base",
        type=str,
        default=None,
        help="DSPy API base URL (default: http://localhost:11434 from env or config)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output with metrics")

    parser.add_argument("--list-formats", action="store_true", help="List supported output formats and exit")

    parsed_args = parser.parse_args(args)

    # List formats if requested
    if parsed_args.list_formats:
        orchestrator = CodeGenOrchestrator()
        print("Supported output formats:")
        for fmt in orchestrator.list_formats():
            info = orchestrator.get_format_info(fmt)
            print(f"  {fmt:20s} - {info.get('description', 'No description')}")
        return 0

    # Validate input files provided
    if not parsed_args.input_files:
        parser.error("the following arguments are required: input_files")

    # Handle positional output argument
    input_paths = parsed_args.input_files
    output_path = parsed_args.output

    # Check if last input argument is actually the output file
    if len(input_paths) >= 2 and output_path is None:
        last_arg = Path(input_paths[-1])
        # If last arg doesn't exist or isn't a recognized ontology extension
        if not last_arg.exists() or last_arg.suffix.lower() not in {".ttl", ".rdf", ".owl", ".n3", ".turtle"}:
            output_path = last_arg
            input_paths = input_paths[:-1]

    # Collect input files
    input_files = collect_input_files(input_paths)

    if not input_files:
        print("Error: No TTL/RDF/OWL files found in specified paths", file=sys.stderr)
        return 2

    # Determine output directory
    if output_path is None:
        # Auto-generate based on format
        output_dir = Path("generated") / parsed_args.format
    elif output_path.is_dir() or (not output_path.exists() and not output_path.suffix):
        # Output is a directory
        output_dir = output_path
        output_path = None  # Let generator decide filename
    else:
        # Output is a file
        output_dir = output_path.parent
        # Keep output_path for single file generation

    if parsed_args.verbose:
        print(f"Processing {len(input_files)} ontology files...")
        print(f"Output format: {parsed_args.format}")
        print(f"Output directory: {output_dir}")

    # Create orchestrator and configuration
    orchestrator = CodeGenOrchestrator()

    config = GenerationConfig(
        format=OutputFormat(parsed_args.format),
        output_dir=output_dir,
        template_dir=parsed_args.template_dir,
        dry_run=parsed_args.dry_run,
        cache_size=parsed_args.cache_size,
        max_workers=parsed_args.max_workers,
        dspy_model=parsed_args.dspy_model,
        dspy_api_base=parsed_args.dspy_api_base,
    )

    # Generate code
    try:
        if len(input_files) == 1 and output_path:
            # Single file with explicit output path
            result = orchestrator.generate(input_files[0], config, output_path=output_path)
            results = [result]
        else:
            # Multiple files or auto-generated paths
            results = orchestrator.generate_multiple(input_files, config)

        if parsed_args.verbose:
            print(f"\nSuccessfully generated {len(results)} output file(s):")
            for result in results:
                print(f"  {result.output_path}")
                if "signatures_generated" in result.metadata:
                    print(f"    - Signatures: {result.metadata['signatures_generated']}")
                if "processing_time_ms" in result.metadata:
                    print(f"    - Processing time: {result.metadata['processing_time_ms']:.1f}ms")

    except Exception as e:
        print(f"Error during generation: {e}", file=sys.stderr)
        if parsed_args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
