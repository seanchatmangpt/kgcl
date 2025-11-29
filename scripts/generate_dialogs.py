#!/usr/bin/env python3
"""Generate dialog components from Java sources.

This script uses the unified code generation framework to convert
YAWL UI dialog Java classes to React components + FastAPI endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kgcl.codegen.generators.java_generator import JavaGenerator


def main() -> int:
    """Generate all dialog components."""
    # Input/output paths
    dialog_dir = Path("vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/dialog")
    output_dir = Path("src")  # Generator appends module path automatically
    template_dir = Path("src/kgcl/codegen/templates")

    # Find all Java files
    java_files = sorted(dialog_dir.glob("**/*.java"))
    print(f"Found {len(java_files)} Java files in dialog/")

    # Create generator
    generator = JavaGenerator(
        template_dir=template_dir / "python",
        output_dir=output_dir,
    )

    # Generate all files
    generated_count = 0
    errors: list[tuple[Path, Exception]] = []

    for java_file in java_files:
        try:
            result = generator.generate(java_file)
            print(f"✓ Generated: {result.output_path}")
            generated_count += 1
        except Exception as e:
            print(f"✗ Failed: {java_file.name} - {e}")
            errors.append((java_file, e))

    # Summary
    print(f"\n{'='*60}")
    print(f"Generated: {generated_count}/{len(java_files)} files")
    if errors:
        print(f"Errors: {len(errors)} files failed")
        for java_file, error in errors:
            print(f"  - {java_file.name}: {error}")
        return 1

    print("✓ All files generated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
