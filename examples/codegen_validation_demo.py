"""Demonstration of code validation system.

This example shows how to use the code validator to ensure generated
code meets KGCL quality standards.

Run with: uv run python examples/codegen_validation_demo.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "codegen"))

from validator import (  # type: ignore[import-not-found]
    CodeValidator,
    auto_fix_issues,
    generate_validation_report,
)


def demo_syntax_validation() -> None:
    """Demonstrate syntax validation."""
    print("\n" + "=" * 80)
    print("DEMO 1: Syntax Validation")
    print("=" * 80)

    validator = CodeValidator()

    # Valid syntax
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Valid module."""
from __future__ import annotations

def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"
'''
        )
        valid_file = Path(f.name)

    passed, errors = validator.validate_syntax(valid_file)
    print(f"\n✓ Valid syntax: passed={passed}, errors={errors}")

    # Invalid syntax
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """def broken(
    pass
"""
        )
        invalid_file = Path(f.name)

    passed, errors = validator.validate_syntax(invalid_file)
    print(f"\n✗ Invalid syntax: passed={passed}")
    print(f"  Errors: {errors[0] if errors else 'None'}")

    # Cleanup
    valid_file.unlink()
    invalid_file.unlink()


def demo_type_validation() -> None:
    """Demonstrate type checking validation."""
    print("\n" + "=" * 80)
    print("DEMO 2: Type Checking")
    print("=" * 80)

    validator = CodeValidator()

    # Fully typed
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Fully typed module."""
from __future__ import annotations

def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
'''
        )
        typed_file = Path(f.name)

    passed, errors = validator.validate_types(typed_file)
    print(f"\n✓ Fully typed: passed={passed}, errors={errors}")

    # Missing types
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Module with missing types."""
def add(a, b):
    """Add two numbers."""
    return a + b
'''
        )
        untyped_file = Path(f.name)

    passed, errors = validator.validate_types(untyped_file)
    print(f"\n✗ Missing types: passed={passed}")
    if errors:
        print(f"  First error: {errors[0]}")

    # Cleanup
    typed_file.unlink()
    untyped_file.unlink()


def demo_import_validation() -> None:
    """Demonstrate import validation."""
    print("\n" + "=" * 80)
    print("DEMO 3: Import Validation")
    print("=" * 80)

    validator = CodeValidator()

    # Absolute imports (valid)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Module with absolute imports."""
from __future__ import annotations

import sys
from pathlib import Path

def get_path() -> Path:
    """Get current path."""
    return Path.cwd()
'''
        )
        absolute_file = Path(f.name)

    passed, errors = validator.validate_imports(absolute_file)
    print(f"\n✓ Absolute imports: passed={passed}, errors={errors}")

    # Relative imports (invalid)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Module with relative imports."""
from ..utils import helper

def process() -> None:
    """Process something."""
    helper()
'''
        )
        relative_file = Path(f.name)

    passed, errors = validator.validate_imports(relative_file)
    print(f"\n✗ Relative imports: passed={passed}")
    print(f"  Errors: {errors[0] if errors else 'None'}")

    # Cleanup
    absolute_file.unlink()
    relative_file.unlink()


def demo_full_validation() -> None:
    """Demonstrate full validation pipeline."""
    print("\n" + "=" * 80)
    print("DEMO 4: Full Validation Pipeline")
    print("=" * 80)

    validator = CodeValidator(strict=False)

    # Perfect file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Perfect module meeting all standards."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """User value object.

    Attributes
    ----------
    name : str
        User's name
    email : str
        User's email
    """

    name: str
    email: str


def create_user(name: str, email: str) -> User:
    """Create new user.

    Parameters
    ----------
    name : str
        User's name
    email : str
        User's email

    Returns
    -------
    User
        Created user
    """
    return User(name=name, email=email)
'''
        )
        perfect_file = Path(f.name)

    result = validator.validate_python(perfect_file)
    print(f"\n✓ Perfect file validation:")
    print(f"  Passed: {result.passed}")
    print(f"  Errors: {result.errors}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Metrics: {result.metrics}")

    # Cleanup
    perfect_file.unlink()


def demo_auto_fix() -> None:
    """Demonstrate auto-fix functionality."""
    print("\n" + "=" * 80)
    print("DEMO 5: Auto-Fix")
    print("=" * 80)

    # Unformatted file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''"""Unformatted module."""
from __future__ import annotations

def hello(   )->str:
    """Return greeting."""
    return    "hello"
'''
        )
        unformatted_file = Path(f.name)

    print("\nBefore auto-fix:")
    print(unformatted_file.read_text())

    result = auto_fix_issues(unformatted_file)

    print("\nAfter auto-fix:")
    print(unformatted_file.read_text())
    print(f"\nValidation result: passed={result.passed}")

    # Cleanup
    unformatted_file.unlink()


def demo_directory_validation() -> None:
    """Demonstrate validating entire directory."""
    print("\n" + "=" * 80)
    print("DEMO 6: Directory Validation")
    print("=" * 80)

    validator = CodeValidator(strict=False)

    # Create temp directory with multiple files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Good file 1
        (tmp_path / "good1.py").write_text(
            '''"""Good module 1."""
from __future__ import annotations

def func1() -> str:
    """Function 1."""
    return "1"
'''
        )

        # Good file 2
        (tmp_path / "good2.py").write_text(
            '''"""Good module 2."""
from __future__ import annotations

def func2() -> int:
    """Function 2."""
    return 2
'''
        )

        # Bad file
        (tmp_path / "bad.py").write_text(
            '''"""Bad module."""
def broken(
    pass
'''
        )

        # Validate all files
        results = validator.validate_all(tmp_path)

        # Generate report
        report = generate_validation_report(results)
        print(report)


def main() -> None:
    """Run all validation demos."""
    print("\n" + "=" * 80)
    print("CODE VALIDATION SYSTEM DEMONSTRATION")
    print("=" * 80)

    demo_syntax_validation()
    demo_type_validation()
    demo_import_validation()
    demo_full_validation()
    demo_auto_fix()
    demo_directory_validation()

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print(
        "\nKey Takeaways:\n"
        "1. Syntax validation catches parse errors early\n"
        "2. Type checking ensures 100% type coverage\n"
        "3. Import validation prevents relative imports\n"
        "4. Full validation provides comprehensive checks\n"
        "5. Auto-fix resolves many issues automatically\n"
        "6. Directory validation scales to multiple files\n"
    )


if __name__ == "__main__":
    main()
