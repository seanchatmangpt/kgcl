"""CLI for YAWL ontology generation, exploration, and stub generation."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kgcl.yawl_ontology.explorer import YawlOntologyExplorer
from kgcl.yawl_ontology.gap_analyzer import YawlGapAnalyzer
from kgcl.yawl_ontology.generator import YawlOntologyGenerator
from kgcl.yawl_ontology.stub_generator import StubGenerator

app = typer.Typer(help="YAWL ontology tools: generate, explore, and create Python stubs")
console = Console()


@app.command()
def generate(
    source_root: Path,
    output_file: Path,
    validate: bool = True,  # noqa: B008
) -> None:
    """Generate RDF/Turtle ontology from YAWL Java source code."""
    console.print(f"[bold blue]Generating ontology from[/bold blue] {source_root}")
    generator = YawlOntologyGenerator()
    generator.generate_from_directory(source_root, output_file)
    console.print(f"[bold green]✓[/bold green] Generated {output_file}")


@app.command()
def explore(ontology_file: Path, class_name: str | None = None, hierarchy: bool = False) -> None:
    """Explore YAWL ontology with SPARQL queries."""
    explorer = YawlOntologyExplorer(ontology_file)

    if hierarchy:
        console.print("\n[bold]Decomposition Hierarchy[/bold]")
        hierarchy_data = explorer.analyze_decomposition_hierarchy()
        for base, children in hierarchy_data.items():
            console.print(f"\n[cyan]{base}[/cyan]")
            for child in children:
                console.print(f"  • {child.name} ({child.package})")

    if class_name:
        console.print(f"\n[bold]API Surface: {class_name}[/bold]")
        methods = explorer.get_class_methods(class_name)

        table = Table(title=f"{class_name} Methods ({len(methods)} total)")
        table.add_column("Method", style="cyan")
        table.add_column("Return Type", style="green")
        table.add_column("Parameters")

        for m in methods:
            table.add_row(m.name, m.return_type, m.parameters[:50] + "..." if len(m.parameters) > 50 else m.parameters)

        console.print(table)


@app.command()
def generate_stubs(
    ontology_file: Path, output_dir: Path = Path("src/kgcl/yawl"), class_name: str | None = None
) -> None:
    """Generate Python implementation stubs from YAWL ontology."""
    explorer = YawlOntologyExplorer(ontology_file)
    generator = StubGenerator(explorer)

    if class_name:
        console.print(f"[bold blue]Generating stub for {class_name}[/bold blue]")
        stub = generator.generate_class_stub(class_name)
        output_file = generator.write_stub_file(stub, output_dir)
        console.print(f"[bold green]✓[/bold green] Generated {output_file}")
    else:
        console.print("[bold blue]Generating core engine stubs[/bold blue]")
        files = generator.generate_core_engine_stubs(output_dir)
        console.print(f"\n[bold green]✓[/bold green] Generated {len(files)} stub files in {output_dir}")
        for f in files:
            console.print(f"  • {f.name}")


@app.command()
def analyze(ontology_file: Path, output_file: Path = Path("docs/yawl_architecture.md")) -> None:
    """Generate comprehensive architecture analysis report."""
    explorer = YawlOntologyExplorer(ontology_file)
    explorer.export_architecture_summary(output_file)
    console.print(f"[bold green]✓[/bold green] Exported architecture analysis: {output_file}")


@app.command()
def gap_analysis(
    ontology_file: Path,
    python_root: Path,
    output_file: Path = Path("docs/yawl_gap_analysis.md"),
    min_methods: int = 10,
    class_limit: int = 20,
) -> None:
    """Analyze gaps between Java YAWL and Python implementation."""
    console.print("[bold blue]Analyzing gaps between Java ontology and Python code[/bold blue]")
    console.print(f"  Ontology: {ontology_file}")
    console.print(f"  Python:   {python_root}")

    analyzer = YawlGapAnalyzer(ontology_file, python_root)
    analyzer.export_gap_report(output_file)
    console.print(f"[bold green]✓[/bold green] Gap analysis complete: {output_file}")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
