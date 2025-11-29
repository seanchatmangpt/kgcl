"""Demonstration of YAWL UI code generator.

This script demonstrates the semantic code generator by creating a sample Java
file and generating Python client code from it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from codegen.generator import CodeGenerator


def create_sample_java_file(tmp_dir: Path) -> Path:
    """Create a sample Java service file for demonstration.

    Parameters
    ----------
    tmp_dir : Path
        Temporary directory for files

    Returns
    -------
    Path
        Path to created Java file
    """
    java_code = dedent(
        """
        package org.yawlfoundation.yawl.ui.service;

        import java.util.List;
        import java.util.Map;
        import java.util.Set;

        /**
         * Dynamic form service for YAWL UI.
         * Manages form generation and validation.
         */
        public class DynamicFormService {
            private String configPath;
            private int maxFormSize;

            /**
             * Generate dynamic form from specification.
             *
             * @param specId Specification identifier
             * @param taskId Task identifier
             * @return Generated form HTML
             */
            public String generateForm(String specId, String taskId) {
                // Implementation would go here
                return null;
            }

            /**
             * Validate form data against schema.
             *
             * @param formData Form data to validate
             * @param schemaId Schema identifier
             * @return Validation errors (empty if valid)
             */
            public List<String> validateForm(Map<String, Object> formData, String schemaId) {
                // Validation logic
                return null;
            }

            /**
             * Get available form templates.
             *
             * @return Set of template names
             */
            public Set<String> getTemplates() {
                return null;
            }

            /**
             * Update service configuration.
             *
             * @param config Configuration map
             */
            public void updateConfig(Map<String, String> config) {
                // Update config
            }
        }
        """
    ).strip()

    java_file = tmp_dir / "DynamicFormService.java"
    java_file.write_text(java_code)
    return java_file


def main() -> None:
    """Run code generation demonstration."""
    import tempfile

    print("=" * 80)
    print("YAWL UI Code Generator Demonstration")
    print("=" * 80)

    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        output_dir = tmp_dir / "output"
        output_dir.mkdir()

        # 1. Create sample Java file
        print("\n[1] Creating sample Java service file...")
        java_file = create_sample_java_file(tmp_dir)
        print(f"    Created: {java_file}")
        print(f"    Size: {java_file.stat().st_size} bytes")

        # 2. Initialize code generator
        print("\n[2] Initializing code generator...")
        template_dir = Path("templates/codegen")
        generator = CodeGenerator(template_dir, output_dir)
        print(f"    Template directory: {template_dir}")
        print(f"    Output directory: {output_dir}")

        # 3. Generate Python client
        print("\n[3] Generating Python client code...")
        try:
            python_file = generator.generate_python_client(java_file)
            print(f"    ✓ Generated: {python_file}")
            print(f"    ✓ Size: {python_file.stat().st_size} bytes")

            # 4. Show generated Python code
            print("\n[4] Generated Python Code:")
            print("-" * 80)
            python_content = python_file.read_text()
            for i, line in enumerate(python_content.split("\n")[:40], 1):
                print(f"    {i:3d} │ {line}")
            if len(python_content.split("\n")) > 40:
                print(f"    ... ({len(python_content.split('\n')) - 40} more lines)")
            print("-" * 80)

            # 5. Find and show test file
            test_file = (
                output_dir
                / "tests"
                / "kgcl"
                / "yawl_ui"
                / "service"
                / "test_dynamic_form_service.py"
            )
            if test_file.exists():
                print("\n[5] Generated Test File:")
                print("-" * 80)
                test_content = test_file.read_text()
                for i, line in enumerate(test_content.split("\n")[:30], 1):
                    print(f"    {i:3d} │ {line}")
                if len(test_content.split("\n")) > 30:
                    print(
                        f"    ... ({len(test_content.split('\n')) - 30} more lines)"
                    )
                print("-" * 80)

            # 6. Summary
            print("\n[6] Generation Summary:")
            print(f"    ✓ Input:  {java_file.name}")
            print(f"    ✓ Output: {python_file.name}")
            print(f"    ✓ Tests:  {test_file.name if test_file.exists() else 'N/A'}")

            # 7. Type mapping examples
            print("\n[7] Type Mappings Applied:")
            print("    • List<String> → list[str]")
            print("    • Map<String, Object> → dict[str, Any]")
            print("    • Set<String> → set[str]")
            print("    • String → str")
            print("    • void → None")

            print("\n" + "=" * 80)
            print("✓ Code generation completed successfully!")
            print("=" * 80)

        except Exception as e:
            print(f"\n✗ Error during generation: {e}")
            raise


if __name__ == "__main__":
    main()
