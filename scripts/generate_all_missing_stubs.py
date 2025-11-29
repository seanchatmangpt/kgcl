"""Generate missing method stubs for all 7 core YAWL classes.

This script identifies missing methods by comparing Java ontology against Python
implementation, accounting for camelCase→snake_case conversion, and generates
properly formatted stub implementations.
"""

import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from kgcl.yawl_ontology.explorer import YawlOntologyExplorer
from kgcl.yawl_ontology.stub_generator import StubGenerator

console = Console()


def get_python_methods(file_path: Path) -> set[str]:
    """Extract method names from Python file."""
    methods = set()
    if not file_path.exists():
        return methods

    content = file_path.read_text()
    for line in content.splitlines():
        if line.strip().startswith("def "):
            method_name = line.strip()[4:].split("(")[0]
            methods.add(method_name)
    return methods


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def generate_missing_stubs(
    class_name: str,
    python_file: Path,
    explorer: YawlOntologyExplorer,
    stub_gen: StubGenerator,
    output_dir: Path,
) -> tuple[int, int, Path | None]:
    """Generate stubs for missing methods in a class.

    Parameters
    ----------
    class_name : str
        Java class name
    python_file : Path
        Python implementation file path
    explorer : YawlOntologyExplorer
        Ontology explorer
    stub_gen : StubGenerator
        Stub generator
    output_dir : Path
        Output directory for stub files

    Returns
    -------
    tuple[int, int, Path | None]
        (total_java_methods, missing_methods_count, output_file_path)
    """
    # Get Java methods
    java_methods = explorer.get_class_methods(class_name)

    # Get Python methods (if file exists)
    python_methods = get_python_methods(python_file)

    # Find missing methods (considering snake_case conversion)
    missing = []
    for java_method in java_methods:
        python_name = camel_to_snake(java_method.name)
        # Check both camelCase and snake_case
        if java_method.name not in python_methods and python_name not in python_methods:
            missing.append(java_method)

    if not missing:
        return len(java_methods), 0, None

    # Generate stubs with class wrapper for valid Python syntax
    output_file = output_dir / f"{class_name.lower()}_missing_methods.py"
    lines = [
        f'"""Missing methods for {class_name} class.',
        "",
        f"Copy these methods to {python_file}",
        "",
        "NOTE: This file wraps methods in a class for syntax validation.",
        "When copying to the actual class, copy only the method definitions.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "",
        f"class {class_name}Stubs:",
        f'    """Generated stubs for missing {class_name} methods."""',
        "",
    ]

    for method in missing:
        stub = stub_gen.generate_method_stub(method)
        lines.append(stub)
        lines.append("")

    output_file.write_text("\n".join(lines))
    return len(java_methods), len(missing), output_file


def main() -> None:
    """Generate missing method stubs for all core YAWL classes."""
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold cyan]YAWL Missing Methods Stub Generator[/bold cyan]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")

    ontology_file = Path("docs/yawl_full_ontology.ttl")
    output_dir = Path("docs/missing_methods")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not ontology_file.exists():
        console.print("[red]✗ Ontology file not found. Run: uv run poe yawl-ontology-full[/red]")
        return

    # Initialize tools
    console.print(f"\n[cyan]Loading ontology:[/cyan] {ontology_file}")
    explorer = YawlOntologyExplorer(ontology_file)
    stub_gen = StubGenerator(explorer)

    # Core classes to analyze
    core_classes = [
        ("YEngine", Path("src/kgcl/yawl/engine/y_engine.py")),
        ("YWorkItem", Path("src/kgcl/yawl/engine/y_work_item.py")),
        ("YTask", Path("src/kgcl/yawl/elements/y_task.py")),
        ("YDecomposition", Path("src/kgcl/yawl/elements/y_decomposition.py")),
        ("YNetRunner", Path("src/kgcl/yawl/engine/y_net_runner.py")),
        ("YCondition", Path("src/kgcl/yawl/elements/y_condition.py")),
        ("YVariable", Path("src/kgcl/yawl/elements/y_decomposition.py")),  # YVariable is in decomposition.py
    ]

    # Results table
    table = Table(title="Missing Methods Analysis")
    table.add_column("#", style="dim", width=3)
    table.add_column("Class", style="cyan", width=20)
    table.add_column("Java", style="blue", width=8)
    table.add_column("Missing", style="red", width=10)
    table.add_column("Gap %", style="yellow", width=10)
    table.add_column("Status", style="green", width=30)

    total_missing = 0
    generated_files = []

    console.print("\n[bold]Analyzing classes and generating stubs...[/bold]\n")

    for i, (class_name, python_file) in enumerate(core_classes, 1):
        console.print(f"[cyan]{i}.[/cyan] Processing {class_name}...", end=" ")

        java_count, missing_count, output_file = generate_missing_stubs(
            class_name, python_file, explorer, stub_gen, output_dir
        )

        if output_file:
            generated_files.append(output_file)
            status = f"✓ {output_file.name}"
            console.print(f"[green]{missing_count} missing[/green]")
        else:
            status = "✓ No missing methods"
            console.print("[green]complete[/green]")

        gap_pct = (missing_count / java_count * 100) if java_count > 0 else 0
        table.add_row(
            str(i),
            class_name,
            str(java_count),
            str(missing_count),
            f"{gap_pct:.1f}%",
            status,
        )
        total_missing += missing_count

    console.print("\n")
    console.print(table)

    # Summary
    console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold cyan]Summary[/bold cyan]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print(f"[green]✓[/green] Analyzed {len(core_classes)} core classes")
    console.print(f"[green]✓[/green] Total missing methods: [red]{total_missing}[/red]")
    console.print(f"[green]✓[/green] Generated {len(generated_files)} stub files")
    console.print(f"[green]✓[/green] Output directory: {output_dir}")

    if generated_files:
        console.print("\n[bold]Generated stub files:[/bold]")
        for stub_file in generated_files:
            console.print(f"  • {stub_file}")


if __name__ == "__main__":
    main()
