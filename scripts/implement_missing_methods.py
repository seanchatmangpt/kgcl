"""Generate implementations for missing YEngine methods based on gap analysis.

This script:
1. Reads Java method signatures from ontology
2. Checks what exists in Python
3. Generates stub implementations for missing methods
4. Adds them to the existing YEngine class
"""

from pathlib import Path

from kgcl.yawl_ontology.explorer import YawlOntologyExplorer
from kgcl.yawl_ontology.stub_generator import StubGenerator


def get_python_methods(file_path: Path) -> set[str]:
    """Extract method names from Python file."""
    methods = set()
    content = file_path.read_text()
    for line in content.splitlines():
        if line.strip().startswith("def "):
            method_name = line.strip()[4:].split("(")[0]
            methods.add(method_name)
    return methods


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def main() -> None:
    """Generate missing method implementations."""
    ontology_file = Path("docs/yawl_full_ontology.ttl")
    python_file = Path("src/kgcl/yawl/engine/y_engine.py")

    # Load ontology
    explorer = YawlOntologyExplorer(ontology_file)
    stub_gen = StubGenerator(explorer)

    # Get Java methods
    java_methods = explorer.get_class_methods("YEngine")
    print(f"Java YEngine: {len(java_methods)} methods")

    # Get Python methods
    python_methods = get_python_methods(python_file)
    print(f"Python YEngine: {len(python_methods)} methods")

    # Find missing methods (considering snake_case conversion)
    missing = []
    for java_method in java_methods:
        python_name = camel_to_snake(java_method.name)
        # Check both camelCase and snake_case
        if java_method.name not in python_methods and python_name not in python_methods:
            missing.append(java_method)

    print(f"\nMissing methods: {len(missing)}")
    print(f"\nTop 20 missing methods:")
    for i, method in enumerate(missing[:20], 1):
        print(f"{i:2}. {method.name} -> {method.return_type}")

    # Generate stubs for missing methods
    output_file = Path("docs/yawl_engine_missing_methods.py")
    lines = [
        '"""Missing methods for YEngine class.',
        "",
        "Add these to src/kgcl/yawl/engine/y_engine.py",
        '"""',
        "",
        "",
    ]

    for method in missing:
        stub = stub_gen.generate_method_stub(method)
        lines.append(stub)
        lines.append("")

    output_file.write_text("\n".join(lines))
    print(f"\n✓ Generated stubs: {output_file}")
    print(f"  {len(missing)} methods ready to implement")


if __name__ == "__main__":
    main()
