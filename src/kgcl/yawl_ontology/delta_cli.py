"""CLI interface for delta detector."""

from pathlib import Path

import typer

from kgcl.yawl_ontology.delta_detector import DeltaDetector

app = typer.Typer(help="YAWL Java → Python Delta Detector")


@app.command()
def detect(
    java_root: Path = typer.Option(
        ..., "--java-root", "-j", help="Root directory of Java YAWL implementation"
    ),
    python_root: Path = typer.Option(
        ..., "--python-root", "-p", help="Root directory of Python YAWL implementation"
    ),
    ontology: Path | None = typer.Option(
        None, "--ontology", "-o", help="Path to YAWL ontology file (optional)"
    ),
    java_test_root: Path | None = typer.Option(
        None, "--java-test-root", help="Root directory of Java test files (optional)"
    ),
    python_test_root: Path | None = typer.Option(
        None, "--python-test-root", help="Root directory of Python test files (optional)"
    ),
    output: Path = typer.Option(
        Path("deltas.json"), "--output", help="Output file path"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json or yaml"
    ),
) -> None:
    """Detect deltas between Java YAWL and Python conversion.

    Examples
    --------
    $ delta-detector --java-root vendors/yawl-v5.2/src \\
                     --python-root src/kgcl/yawl \\
                     --ontology ontology/codebase \\
                     --output deltas.json \\
                     --format json
    """
    if not java_root.exists():
        typer.echo(f"Error: Java root does not exist: {java_root}", err=True)
        raise typer.Exit(1)

    if not python_root.exists():
        typer.echo(f"Error: Python root does not exist: {python_root}", err=True)
        raise typer.Exit(1)

    if ontology and not ontology.exists():
        typer.echo(f"Warning: Ontology file does not exist: {ontology}", err=True)

    typer.echo("Initializing delta detector...")
    detector = DeltaDetector(
        java_root=java_root,
        python_root=python_root,
        ontology_path=ontology,
        java_test_root=java_test_root,
        python_test_root=python_test_root,
    )

    typer.echo("Detecting deltas...")
    report = detector.detect_all_deltas()

    typer.echo(f"Exporting report to {output}...")
    detector.export_report(report, output, format=format)

    typer.echo("\n" + "=" * 80)
    typer.echo("Delta Detection Summary")
    typer.echo("=" * 80)
    typer.echo(f"Total classes analyzed: {report.summary.total_classes_analyzed}")
    typer.echo(f"Total methods analyzed: {report.summary.total_methods_analyzed}")
    typer.echo(f"Coverage: {report.summary.coverage_percent:.1f}%")
    typer.echo(f"Critical deltas: {report.summary.critical_deltas}")
    typer.echo(f"High deltas: {report.summary.high_deltas}")
    typer.echo(f"Medium deltas: {report.summary.medium_deltas}")
    typer.echo(f"Warnings: {report.summary.warnings}")
    typer.echo("=" * 80)


if __name__ == "__main__":
    app()

