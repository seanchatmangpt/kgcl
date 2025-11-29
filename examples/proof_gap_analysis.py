"""Proof of concept: Gap analysis between Java YAWL and Python implementation.

Demonstrates:
1. Loading YAWL ontology (103K triples)
2. Dynamically discovering important classes from ontology
3. Scanning existing Python YAWL implementation
4. Identifying missing classes, methods, and stubs
5. Generating actionable gap analysis report
"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from kgcl.yawl_ontology.gap_analyzer import YawlGapAnalyzer

console = Console()


def main() -> None:
    """Run gap analysis proof of concept."""
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold cyan]YAWL Gap Analysis - Ontology-Driven Discovery[/bold cyan]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")

    # Paths
    ontology_file = Path("docs/yawl_full_ontology.ttl")
    python_root = Path("src/kgcl/yawl")
    output_file = Path("docs/yawl_gap_analysis.md")

    if not ontology_file.exists():
        console.print("[red]✗ Ontology file not found. Run: uv run poe yawl-ontology-full[/red]")
        return

    if not python_root.exists():
        console.print("[red]✗ Python YAWL directory not found[/red]")
        return

    console.print(f"\n[cyan]Ontology:[/cyan] {ontology_file}")
    console.print(f"[cyan]Python:  [/cyan] {python_root}")

    # Initialize analyzer
    analyzer = YawlGapAnalyzer(ontology_file, python_root)

    # Discover important classes dynamically
    console.print("\n[bold]Step 1: Discovering Important Classes (≥10 methods)[/bold]")
    important = analyzer.discover_important_classes(min_methods=10, limit=20)
    console.print(f"Found [green]{len(important)}[/green] important classes by method count")

    table = Table(title="Top Important Classes")
    table.add_column("#", style="dim")
    table.add_column("Class", style="cyan")
    for i, cls in enumerate(important[:10], 1):
        table.add_row(str(i), cls)
    console.print(table)

    # Discover base classes
    console.print("\n[bold]Step 2: Discovering Base Classes (Architectural Patterns)[/bold]")
    base_classes = analyzer.discover_base_classes()
    console.print(f"Found [green]{len(base_classes)}[/green] base classes")
    console.print(f"Examples: {', '.join(base_classes[:5])}")

    # Scan Python implementation
    console.print("\n[bold]Step 3: Scanning Existing Python Implementation[/bold]")
    py_classes = list(analyzer.python_analyzer.classes.keys())
    console.print(f"Found [green]{len(py_classes)}[/green] Python classes")
    console.print(f"Examples: {', '.join(py_classes[:5])}")

    # Run gap analysis
    console.print("\n[bold]Step 4: Running Gap Analysis[/bold]")
    analysis = analyzer.analyze_discovered_classes(min_methods=10, class_limit=20, include_base_classes=True)

    # Display results
    console.print(f"\n[bold cyan]Gap Analysis Results[/bold cyan]")
    console.print(f"  Coverage: [{'green' if analysis.coverage_percent > 50 else 'red'}]{analysis.coverage_percent:.1f}%[/]")
    console.print(f"  Missing classes: [red]{len(analysis.missing_classes)}[/red]")
    console.print(f"  Stub classes: [yellow]{len(analysis.stub_classes)}[/yellow]")
    console.print(f"  Partial implementations: [yellow]{len(analysis.partial_implementations)}[/yellow]")

    # Show missing classes
    if analysis.missing_classes:
        console.print("\n[bold red]Missing Classes (Top 10):[/bold red]")
        for cls in analysis.missing_classes[:10]:
            console.print(f"  • {cls.name} ({cls.package})")

    # Show stub classes
    if analysis.stub_classes:
        console.print("\n[bold yellow]Stub Classes (Empty Implementations):[/bold yellow]")
        for cls in analysis.stub_classes[:10]:
            console.print(f"  • {cls}")

    # Show partial implementations
    if analysis.partial_implementations:
        console.print("\n[bold]Partial Implementations:[/bold]")
        partial_table = Table()
        partial_table.add_column("Class", style="cyan")
        partial_table.add_column("Implemented", style="green")
        partial_table.add_column("Total", style="dim")
        partial_table.add_column("Completion", style="yellow")

        for cls, (impl, total) in sorted(analysis.partial_implementations.items())[:10]:
            if cls not in analysis.stub_classes:
                pct = (impl / total * 100) if total > 0 else 0
                partial_table.add_row(cls, str(impl), str(total), f"{pct:.1f}%")

        console.print(partial_table)

    # Export report
    console.print(f"\n[bold]Step 5: Exporting Gap Analysis Report[/bold]")
    analyzer.export_gap_report(output_file, min_methods=10, class_limit=20, include_base_classes=True)
    console.print(f"[green]✓[/green] Report exported: {output_file}")

    # Summary
    console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold cyan]Summary[/bold cyan]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print(f"[green]✓[/green] Dynamically discovered {len(important)} important classes")
    console.print(f"[green]✓[/green] Identified {len(base_classes)} architectural base classes")
    console.print(f"[green]✓[/green] Scanned {len(py_classes)} existing Python classes")
    console.print(f"[green]✓[/green] Coverage: {analysis.coverage_percent:.1f}%")
    console.print(f"[green]✓[/green] Gaps identified: {len(analysis.missing_classes)} missing, {len(analysis.stub_classes)} stubs")
    console.print(f"[green]✓[/green] Report: {output_file}")


if __name__ == "__main__":
    main()
