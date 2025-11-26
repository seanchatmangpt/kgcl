"""KGCT code generation helpers."""

from __future__ import annotations

from pathlib import Path

from personal_kgcl.generators.cli_generator import generate_cli_module


def generate_cli(
    template_path: Path | None = None,
    output_path: Path | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """Regenerate the Typer CLI from `.kgc/cli.ttl`.

    Parameters
    ----------
    template_path:
        Optional override for the Jinja template.
    output_path:
        Optional override for the generated CLI destination.
    verbose:
        When true, include additional details in the returned message.
    dry_run:
        If true, parse and render but do not write the output file.

    Returns
    -------
    str
        Human-readable summary for the CLI/technician.
    """
    generated = generate_cli_module(
        template_path=template_path, output_path=output_path, dry_run=dry_run
    )

    if dry_run:
        return f"[DRY-RUN] CLI generation succeeded ({len(generated.source)} bytes rendered)."

    message = f"Generated KGCT CLI → {generated.output_path}"
    if verbose:
        message += f" (commands: {', '.join(cmd.name for cmd in generated.commands)})"
    return message
