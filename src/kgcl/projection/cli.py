"""Projection CLI commands for template rendering.

This module provides Click-based CLI commands for rendering templates
and bundles from the KGCL projection engine.

Examples
--------
$ kgcl proj render -t api.j2 -o api.py --param title=API
$ kgcl proj bundle -b crud.yaml -o output/ --dry-run
$ kgcl proj list
$ kgcl proj show api.j2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from kgcl.projection.adapters.filesystem_registry import FilesystemTemplateRegistry
from kgcl.projection.domain.bundle import ConflictMode
from kgcl.projection.engine.bundle_renderer import BundleRenderer
from kgcl.projection.engine.projection_engine import ProjectionEngine
from kgcl.projection.ports.graph_client import GraphRegistry

__all__ = ["proj"]


def _parse_params(param_tuples: tuple[str, ...], params_file: str | None) -> dict[str, Any]:
    """Parse parameters from CLI args and JSON file.

    Parameters
    ----------
    param_tuples : tuple[str, ...]
        Tuples of key=value strings.
    params_file : str | None
        Path to JSON params file.

    Returns
    -------
    dict[str, Any]
        Merged parameters.

    Examples
    --------
    >>> _parse_params(("x=1", "y=hello"), None)
    {'x': '1', 'y': 'hello'}
    """
    params: dict[str, Any] = {}

    # Load from file if provided
    if params_file:
        with Path(params_file).open() as f:
            params.update(json.load(f))

    # Parse CLI params (override file)
    for param_str in param_tuples:
        if "=" not in param_str:
            msg = f"Invalid param format (expected key=value): {param_str}"
            raise ValueError(msg)
        key, value = param_str.split("=", 1)
        params[key] = value

    return params


def _get_template_dir() -> Path:
    """Get default template directory.

    Returns
    -------
    Path
        Template directory path.
    """
    # Default to templates/ in current directory
    return Path.cwd() / "templates"


@click.group()
def proj() -> None:
    """Projection commands for template rendering.

    Render Jinja templates with SPARQL query integration for code generation
    from RDF ontologies.

    Examples
    --------
    $ kgcl proj render -t api.j2 -o api.py
    $ kgcl proj bundle -b crud.yaml -o output/
    $ kgcl proj list
    """


@proj.command()
@click.option("-t", "--template", required=True, help="Template name")
@click.option("-o", "--out", type=click.Path(), help="Output file path")
@click.option("-P", "--param", multiple=True, help="Parameter key=value")
@click.option("--params", type=click.Path(exists=True), help="JSON params file")
@click.option("--graph", default="main", help="Graph ID to use")
@click.option("--template-dir", type=click.Path(exists=True), help="Template directory")
def render(
    template: str, out: str | None, param: tuple[str, ...], params: str | None, graph: str, template_dir: str | None
) -> None:
    """Render a single template.

    Examples
    --------
    $ kgcl proj render -t api/service.j2 -o service.py
    $ kgcl proj render -t api.j2 -P title=API -P version=1.0
    $ kgcl proj render -t api.j2 --params config.json
    """
    try:
        # Parse parameters
        user_params = _parse_params(param, params)
        user_params["graph_id"] = graph

        # Set up registries
        tmpl_dir = Path(template_dir) if template_dir else _get_template_dir()
        template_registry = FilesystemTemplateRegistry(tmpl_dir)
        graph_registry = GraphRegistry()

        # Create engine and render
        engine = ProjectionEngine(template_registry, graph_registry)
        result = engine.render(template, user_params, graph)

        # Output
        if out:
            Path(out).write_text(result.content, encoding="utf-8")
            click.echo(f"Rendered to: {out}")
        else:
            click.echo(result.content)

        # Show stats
        click.echo(f"\n✓ Rendered in {result.render_time_ms:.2f}ms ({result.query_count} queries)", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@proj.command()
@click.option("-b", "--bundle", required=True, help="Bundle YAML path")
@click.option("-o", "--out-dir", type=click.Path(), required=True, help="Output directory")
@click.option("-P", "--param", multiple=True, help="Parameter key=value")
@click.option("--params", type=click.Path(exists=True), help="JSON params file")
@click.option(
    "--conflict", type=click.Choice(["error", "overwrite", "skip"]), default="error", help="Conflict resolution mode"
)
@click.option("--dry-run", is_flag=True, help="Don't write files")
@click.option("--template-dir", type=click.Path(exists=True), help="Template directory")
def bundle(
    bundle: str,
    out_dir: str,
    param: tuple[str, ...],
    params: str | None,
    conflict: str,
    dry_run: bool,
    template_dir: str | None,
) -> None:
    """Render a bundle of templates.

    Examples
    --------
    $ kgcl proj bundle -b crud.yaml -o output/
    $ kgcl proj bundle -b api.yaml -o src/ --dry-run
    $ kgcl proj bundle -b crud.yaml -o out/ --conflict overwrite
    """
    try:
        # Parse parameters
        user_params = _parse_params(param, params)

        # Map conflict mode
        conflict_map = {"error": ConflictMode.ERROR, "overwrite": ConflictMode.OVERWRITE, "skip": ConflictMode.SKIP}
        conflict_mode = conflict_map[conflict]

        # Set up registries
        tmpl_dir = Path(template_dir) if template_dir else _get_template_dir()
        template_registry = FilesystemTemplateRegistry(tmpl_dir)
        graph_registry = GraphRegistry()

        # Load bundle
        bundle_registry = FilesystemTemplateRegistry(tmpl_dir)
        bundle_desc = bundle_registry.get_bundle(bundle)
        if bundle_desc is None:
            msg = f"Bundle not found: {bundle}"
            raise ValueError(msg)

        # Create renderer and render
        engine = ProjectionEngine(template_registry, graph_registry)
        renderer = BundleRenderer(engine)

        output_path = Path(out_dir)
        result = renderer.render_bundle(bundle_desc, user_params, output_path, conflict_mode, dry_run)

        # Show results
        click.echo(f"\n✓ Rendered {result.file_count} files:")
        for file_result in result.files:
            status = "[DRY RUN] " if dry_run else ""
            click.echo(f"  {status}{file_result.output_path}")

        click.echo(f"\nTotal time: {result.total_render_time_ms:.2f}ms", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@proj.command("list")
@click.option("--dir", "template_dir", type=click.Path(exists=True), help="Template directory")
def list_templates(template_dir: str | None) -> None:
    """List available templates.

    Examples
    --------
    $ kgcl proj list
    $ kgcl proj list --dir /path/to/templates
    """
    try:
        tmpl_dir = Path(template_dir) if template_dir else _get_template_dir()
        registry = FilesystemTemplateRegistry(tmpl_dir)

        templates = registry.list_templates()
        if not templates:
            click.echo("No templates found.")
            return

        click.echo(f"\nAvailable templates in {tmpl_dir}:")
        for tmpl in sorted(templates):
            click.echo(f"  • {tmpl}")

        click.echo(f"\nTotal: {len(templates)} templates")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@proj.command()
@click.argument("template_or_bundle")
@click.option("--template-dir", type=click.Path(exists=True), help="Template directory")
def show(template_or_bundle: str, template_dir: str | None) -> None:
    """Show template or bundle details.

    Examples
    --------
    $ kgcl proj show api.j2
    $ kgcl proj show crud.yaml
    """
    try:
        tmpl_dir = Path(template_dir) if template_dir else _get_template_dir()
        registry = FilesystemTemplateRegistry(tmpl_dir)

        # Try as template first
        descriptor = registry.get(template_or_bundle)
        if descriptor:
            click.echo(f"\nTemplate: {descriptor.id}")
            click.echo(f"Engine: {descriptor.engine}")
            click.echo(f"Language: {descriptor.language}")
            click.echo(f"Framework: {descriptor.framework}")
            click.echo(f"Version: {descriptor.version}")
            click.echo(f"\nQueries: {len(descriptor.queries)}")
            for q in descriptor.queries:
                click.echo(f"  • {q.name}: {q.purpose}")
            if descriptor.metadata.description:
                click.echo(f"\nDescription:\n  {descriptor.metadata.description}")
            return

        # Try as bundle
        bundle_desc = registry.get_bundle(template_or_bundle)
        if bundle_desc:
            click.echo(f"\nBundle: {bundle_desc.id}")
            click.echo(f"Version: {bundle_desc.version}")
            click.echo(f"Templates: {bundle_desc.template_count}")
            for entry in bundle_desc.templates:
                iter_info = f" (iterate: {entry.iterate.query})" if entry.iterate else ""
                click.echo(f"  • {entry.template} → {entry.output}{iter_info}")
            if bundle_desc.description:
                click.echo(f"\nDescription:\n  {bundle_desc.description}")
            return

        click.echo(f"Not found: {template_or_bundle}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
