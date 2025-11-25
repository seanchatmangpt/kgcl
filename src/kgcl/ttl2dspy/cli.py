"""Command-line interface for ttl2dspy."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .ultra import UltraOptimizer, CacheConfig
from .writer import ModuleWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except errors")
def cli(verbose: bool, quiet: bool):
    """TTL2DSPy: Generate DSPy signatures from SHACL/TTL ontologies."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)


@cli.command()
@click.argument("ttl_file", type=click.Path(exists=True))
@click.option("--no-cache", is_flag=True, help="Disable caching")
def parse(ttl_file: str, no_cache: bool):
    """Parse and validate a TTL file."""
    ttl_path = Path(ttl_file)

    config = CacheConfig(
        memory_cache_enabled=not no_cache,
        disk_cache_enabled=not no_cache,
    )
    optimizer = UltraOptimizer(config)

    try:
        shapes = optimizer.parse_with_cache(ttl_path)
        click.echo(f"Successfully parsed {len(shapes)} SHACL shapes from {ttl_path.name}")

        # Show summary
        for shape in shapes:
            click.echo(f"\n  {shape.name}:")
            click.echo(f"    URI: {shape.uri}")
            click.echo(f"    Inputs: {len(shape.input_properties)}")
            click.echo(f"    Outputs: {len(shape.output_properties)}")
            if shape.description:
                desc = shape.description[:80] + "..." if len(shape.description) > 80 else shape.description
                click.echo(f"    Description: {desc}")

    except Exception as e:
        logger.error(f"Failed to parse TTL file: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.argument("ttl_file", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option("--module-name", "-m", default="signatures", help="Output module name")
@click.option("--no-cache", is_flag=True, help="Disable caching")
@click.option("--no-format", is_flag=True, help="Skip code formatting")
@click.option("--receipt", is_flag=True, help="Write JSON receipt")
def generate(
    ttl_file: str,
    output_dir: str,
    module_name: str,
    no_cache: bool,
    no_format: bool,
    receipt: bool,
):
    """Generate DSPy signatures from a TTL file."""
    ttl_path = Path(ttl_file)
    output_path = Path(output_dir) / f"{module_name}.py"

    config = CacheConfig(
        memory_cache_enabled=not no_cache,
        disk_cache_enabled=not no_cache,
    )
    optimizer = UltraOptimizer(config)
    writer = ModuleWriter()

    try:
        # Parse shapes
        click.echo(f"Parsing {ttl_path.name}...")
        shapes = optimizer.parse_with_cache(ttl_path)

        # Generate code
        click.echo(f"Generating code for {len(shapes)} shapes...")
        code = optimizer.generate_with_cache(shapes)

        # Write module
        click.echo(f"Writing module to {output_path}...")
        result = writer.write_module(
            code=code,
            output_path=output_path,
            shapes_count=len(shapes),
            ttl_source=ttl_path,
            format_code=not no_format,
        )

        click.echo(f"\nSuccess! Generated {result.signatures_count} signatures:")
        click.echo(f"  Output: {result.output_path}")
        click.echo(f"  Lines: {result.lines_count}")
        click.echo(f"  Size: {result.file_size} bytes")
        click.echo(f"  Time: {result.write_time:.3f}s")

        # Write receipt if requested
        if receipt:
            receipt_path = writer.write_receipt(result)
            click.echo(f"  Receipt: {receipt_path}")

        # Show cache stats
        stats = optimizer.get_detailed_stats()
        if stats["cache"]["memory_hits"] > 0 or stats["cache"]["disk_hits"] > 0:
            click.echo("\nCache hits:")
            if stats["cache"]["memory_hits"] > 0:
                click.echo(f"  Memory: {stats['cache']['memory_hits']}")
            if stats["cache"]["disk_hits"] > 0:
                click.echo(f"  Disk: {stats['cache']['disk_hits']}")

    except Exception as e:
        logger.error(f"Failed to generate module: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.argument("ttl_file", type=click.Path(exists=True))
def validate(ttl_file: str):
    """Validate SHACL shapes in a TTL file."""
    ttl_path = Path(ttl_file)

    optimizer = UltraOptimizer()

    try:
        shapes = optimizer.parse_with_cache(ttl_path)

        # Validation checks
        errors = []
        warnings = []

        for shape in shapes:
            # Check for empty shapes
            if not shape.properties:
                errors.append(f"{shape.name}: No properties defined")

            # Check for shapes without inputs or outputs
            if not shape.input_properties and not shape.output_properties:
                warnings.append(f"{shape.name}: No input/output categorization")

            # Check for properties without descriptions
            for prop in shape.properties:
                if not prop.description:
                    warnings.append(f"{shape.name}.{prop.name}: Missing description")

        # Report results
        if errors:
            click.echo(click.style("Errors:", fg="red"))
            for error in errors:
                click.echo(click.style(f"  - {error}", fg="red"))

        if warnings:
            click.echo(click.style("\nWarnings:", fg="yellow"))
            for warning in warnings:
                click.echo(click.style(f"  - {warning}", fg="yellow"))

        if not errors and not warnings:
            click.echo(click.style(f"Validation passed! {len(shapes)} shapes are valid.", fg="green"))
        elif not errors:
            click.echo(click.style(f"\nValidation passed with {len(warnings)} warnings.", fg="green"))
        else:
            click.echo(click.style(f"\nValidation failed with {len(errors)} errors.", fg="red"))
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to validate TTL file: {e}", exc_info=True)
        sys.exit(1)


@cli.command("list")
@click.argument("ttl_file", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list_shapes(ttl_file: str, verbose: bool):
    """List all SHACL shapes in a TTL file."""
    ttl_path = Path(ttl_file)

    optimizer = UltraOptimizer()

    try:
        shapes = optimizer.parse_with_cache(ttl_path)

        click.echo(f"Found {len(shapes)} SHACL shapes in {ttl_path.name}:\n")

        for i, shape in enumerate(shapes, 1):
            click.echo(f"{i}. {shape.name}")
            click.echo(f"   Signature: {shape.signature_name}")
            click.echo(f"   URI: {shape.uri}")

            if verbose:
                if shape.description:
                    click.echo(f"   Description: {shape.description}")
                if shape.target_class:
                    click.echo(f"   Target Class: {shape.target_class}")

                click.echo(f"\n   Input Properties ({len(shape.input_properties)}):")
                for prop in shape.input_properties:
                    python_type = prop.get_python_type()
                    req = "required" if prop.is_required else "optional"
                    click.echo(f"     - {prop.name}: {python_type} ({req})")

                click.echo(f"\n   Output Properties ({len(shape.output_properties)}):")
                for prop in shape.output_properties:
                    python_type = prop.get_python_type()
                    click.echo(f"     - {prop.name}: {python_type}")

            click.echo()

    except Exception as e:
        logger.error(f"Failed to list shapes: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def cache_stats(output_json: bool):
    """Show cache performance statistics."""
    optimizer = UltraOptimizer()
    stats = optimizer.get_detailed_stats()

    if output_json:
        click.echo(json.dumps(stats, indent=2))
    else:
        click.echo("Cache Statistics:\n")

        cache_stats = stats["cache"]
        click.echo("Overall:")
        click.echo(f"  Memory hits: {cache_stats['memory_hits']}")
        click.echo(f"  Memory misses: {cache_stats['memory_misses']}")
        click.echo(f"  Memory hit rate: {cache_stats['memory_hit_rate']:.2%}")
        click.echo(f"  Disk hits: {cache_stats['disk_hits']}")
        click.echo(f"  Disk misses: {cache_stats['disk_misses']}")
        click.echo(f"  Disk hit rate: {cache_stats['disk_hit_rate']:.2%}")

        click.echo("\nTiming:")
        click.echo(f"  Total parse time: {cache_stats['total_parse_time']:.3f}s")
        click.echo(f"  Total generate time: {cache_stats['total_generate_time']:.3f}s")
        click.echo(f"  Total write time: {cache_stats['total_write_time']:.3f}s")

        if stats["parser"]["graph_cache_size"] > 0:
            click.echo("\nParser:")
            click.echo(f"  Cached graphs: {stats['parser']['graph_cache_size']}")
            click.echo(f"  Cached shapes: {stats['parser']['shape_cache_size']}")

        if stats["generator"]["generated_signatures"] > 0:
            click.echo("\nGenerator:")
            click.echo(f"  Cached signatures: {stats['generator']['generated_signatures']}")

        if stats["index"]["shapes_by_name"] > 0:
            click.echo("\nIndex:")
            click.echo(f"  Shapes by name: {stats['index']['shapes_by_name']}")
            click.echo(f"  Shapes by URI: {stats['index']['shapes_by_uri']}")
            click.echo(f"  Target classes: {stats['index']['target_classes']}")


@cli.command()
def clear_cache():
    """Clear all caches."""
    optimizer = UltraOptimizer()
    optimizer.clear_all_caches()
    click.echo(click.style("All caches cleared successfully.", fg="green"))


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
