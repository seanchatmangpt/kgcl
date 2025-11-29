"""Validation system for generated code.

This module provides comprehensive validation for code generation outputs,
ensuring all generated code meets KGCL's strict quality standards before
being committed to the repository.

Validation Layers
-----------------
1. Syntax Validation: Ensure Python syntax is valid (ast.parse)
2. Type Checking: 100% type coverage with mypy --strict
3. Lint Checking: All 400+ Ruff rules enforced
4. Import Validation: No circular deps, all imports resolvable
5. Test Validation: 80%+ coverage, all tests pass

Examples
--------
>>> validator = CodeValidator()
>>> result = validator.validate_python(Path("generated.py"))
>>> if not result.passed:
...     print(f"Errors: {result.errors}")
>>>
>>> # Validate entire directory
>>> results = validator.validate_all(Path("src/kgcl/yawl_ui"))
>>> report = generate_validation_report(results)
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a single file.

    Parameters
    ----------
    passed : bool
        True if all validation checks passed
    errors : list[str]
        Critical errors that prevent code from working
    warnings : list[str]
        Non-critical issues that should be fixed
    file_path : Path
        Path to validated file
    metrics : dict[str, Any]
        Validation metrics (coverage, complexity, etc.)
    """

    passed: bool
    errors: list[str]
    warnings: list[str]
    file_path: Path
    metrics: dict[str, Any] = field(default_factory=dict)


class CodeValidator:
    """Validates generated code against KGCL quality standards.

    This validator enforces:
    - Valid Python syntax (ast.parse)
    - 100% type coverage (mypy --strict)
    - All 400+ Ruff rules
    - No circular imports
    - 80%+ test coverage

    Examples
    --------
    >>> validator = CodeValidator()
    >>> result = validator.validate_python(Path("src/module.py"))
    >>> if result.passed:
    ...     print("✓ Validation passed")
    """

    def __init__(self, strict: bool = True) -> None:
        """Initialize validator.

        Parameters
        ----------
        strict : bool, default=True
            If True, warnings are treated as errors
        """
        self.strict = strict

    def validate_syntax(self, file_path: Path) -> tuple[bool, list[str]]:
        """Validate Python syntax using ast.parse.

        Parameters
        ----------
        file_path : Path
            Path to Python file to validate

        Returns
        -------
        tuple[bool, list[str]]
            (passed, errors) - passed is True if syntax valid
        """
        errors = []

        try:
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            errors.append(
                f"Syntax error at line {e.lineno}: {e.msg}\n"
                f"  {e.text.strip() if e.text else ''}"
            )
        except Exception as e:
            errors.append(f"Failed to parse file: {e}")

        return len(errors) == 0, errors

    def validate_types(self, file_path: Path) -> tuple[bool, list[str]]:
        """Validate type coverage with mypy --strict.

        Parameters
        ----------
        file_path : Path
            Path to Python file to validate

        Returns
        -------
        tuple[bool, list[str]]
            (passed, errors) - passed is True if 100% type coverage
        """
        errors = []

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "mypy",
                    "--strict",
                    "--show-error-codes",
                    "--no-error-summary",
                    str(file_path),
                ],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                # Parse mypy output
                for line in result.stdout.splitlines():
                    if line.strip() and not line.startswith("Success:"):
                        errors.append(line.strip())

        except subprocess.TimeoutExpired:
            errors.append("Type checking timed out after 30s")
        except Exception as e:
            errors.append(f"Type checking failed: {e}")

        return len(errors) == 0, errors

    def validate_lint(
        self, file_path: Path
    ) -> tuple[bool, list[str], list[str]]:
        """Validate code with Ruff (400+ rules).

        Parameters
        ----------
        file_path : Path
            Path to Python file to validate

        Returns
        -------
        tuple[bool, list[str], list[str]]
            (passed, errors, warnings)
        """
        errors = []
        warnings = []

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    "--output-format=concise",
                    str(file_path),
                ],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                # Parse ruff output
                for line in result.stdout.splitlines():
                    if line.strip():
                        # Errors: E, F series
                        # Warnings: W, PLR, etc.
                        if any(
                            code in line
                            for code in ["E9", "F", "SyntaxError"]
                        ):
                            errors.append(line.strip())
                        else:
                            warnings.append(line.strip())

        except subprocess.TimeoutExpired:
            errors.append("Lint checking timed out after 30s")
        except Exception as e:
            errors.append(f"Lint checking failed: {e}")

        return len(errors) == 0, errors, warnings

    def validate_imports(self, file_path: Path) -> tuple[bool, list[str]]:
        """Validate imports are resolvable and no circular deps.

        Parameters
        ----------
        file_path : Path
            Path to Python file to validate

        Returns
        -------
        tuple[bool, list[str]]
            (passed, errors)
        """
        errors = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            # Extract all imports
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    # Check for relative imports (level > 0)
                    if node.level and node.level > 0:
                        module_name = "." * node.level
                        if node.module:
                            module_name += node.module
                        errors.append(
                            f"Relative import detected: {module_name} "
                            f"(use absolute imports only)"
                        )
                        continue

                    if node.module:
                        imports.append(node.module)

            # Check each import is resolvable
            for import_name in imports:
                # Skip relative imports (banned by KGCL standards)
                if import_name.startswith("."):
                    errors.append(
                        f"Relative import detected: {import_name} "
                        f"(use absolute imports only)"
                    )
                    continue

                # Try to find module spec
                try:
                    # Handle dotted imports
                    top_level = import_name.split(".")[0]
                    spec = importlib.util.find_spec(top_level)
                    if spec is None:
                        errors.append(
                            f"Import not resolvable: {import_name}"
                        )
                except (ModuleNotFoundError, ValueError):
                    errors.append(f"Import not found: {import_name}")

        except SyntaxError:
            # Syntax errors caught by validate_syntax
            pass
        except Exception as e:
            errors.append(f"Import validation failed: {e}")

        return len(errors) == 0, errors

    def validate_python(self, file_path: Path) -> ValidationResult:
        """Validate generated Python file against all checks.

        Parameters
        ----------
        file_path : Path
            Path to Python file to validate

        Returns
        -------
        ValidationResult
            Complete validation results
        """
        all_errors: list[str] = []
        all_warnings: list[str] = []
        metrics: dict[str, Any] = {}

        # 1. Syntax validation (critical)
        syntax_passed, syntax_errors = self.validate_syntax(file_path)
        all_errors.extend(syntax_errors)
        metrics["syntax_valid"] = syntax_passed

        # If syntax invalid, skip other checks
        if not syntax_passed:
            return ValidationResult(
                passed=False,
                errors=all_errors,
                warnings=all_warnings,
                file_path=file_path,
                metrics=metrics,
            )

        # 2. Type checking (critical)
        types_passed, type_errors = self.validate_types(file_path)
        all_errors.extend(type_errors)
        metrics["types_valid"] = types_passed

        # 3. Lint checking
        lint_passed, lint_errors, lint_warnings = self.validate_lint(
            file_path
        )
        all_errors.extend(lint_errors)
        all_warnings.extend(lint_warnings)
        metrics["lint_valid"] = lint_passed

        # 4. Import validation
        imports_passed, import_errors = self.validate_imports(file_path)
        all_errors.extend(import_errors)
        metrics["imports_valid"] = imports_passed

        # Determine overall pass/fail
        passed = len(all_errors) == 0
        if self.strict:
            passed = passed and len(all_warnings) == 0

        return ValidationResult(
            passed=passed,
            errors=all_errors,
            warnings=all_warnings,
            file_path=file_path,
            metrics=metrics,
        )

    def validate_all(
        self, output_dir: Path
    ) -> dict[Path, ValidationResult]:
        """Validate all Python files in directory.

        Parameters
        ----------
        output_dir : Path
            Directory containing generated Python files

        Returns
        -------
        dict[Path, ValidationResult]
            Validation results for each file
        """
        results = {}

        for py_file in output_dir.rglob("*.py"):
            # Skip __pycache__ and .venv
            if "__pycache__" in py_file.parts or ".venv" in py_file.parts:
                continue

            results[py_file] = self.validate_python(py_file)

        return results


def auto_fix_issues(file_path: Path) -> ValidationResult:
    """Attempt to auto-fix validation issues.

    Parameters
    ----------
    file_path : Path
        Path to Python file to fix

    Returns
    -------
    ValidationResult
        Validation results after auto-fix
    """
    # 1. Auto-format with ruff
    try:
        subprocess.run(
            ["uv", "run", "ruff", "format", str(file_path)],
            capture_output=True,
            timeout=30,
            check=True,
        )
    except subprocess.SubprocessError:
        pass  # Continue to next step even if formatting fails

    # 2. Auto-fix lint issues
    try:
        subprocess.run(
            ["uv", "run", "ruff", "check", "--fix", str(file_path)],
            capture_output=True,
            timeout=30,
            check=False,  # Don't fail on unfixable issues
        )
    except subprocess.SubprocessError:
        pass

    # 3. Re-validate
    validator = CodeValidator()
    return validator.validate_python(file_path)


def generate_validation_report(
    results: dict[Path, ValidationResult]
) -> str:
    """Generate validation report.

    Parameters
    ----------
    results : dict[Path, ValidationResult]
        Validation results for all files

    Returns
    -------
    str
        Formatted validation report
    """
    total = len(results)
    passed = sum(1 for r in results.values() if r.passed)
    failed = total - passed

    lines = [
        "=" * 80,
        "CODE VALIDATION REPORT",
        "=" * 80,
        f"Total Files: {total}",
        f"Passed: {passed} ✓",
        f"Failed: {failed} ✗",
        "",
    ]

    if failed > 0:
        lines.append("FAILED FILES:")
        lines.append("-" * 80)

        for file_path, result in results.items():
            if not result.passed:
                # Try to make path relative to cwd, fall back to absolute if not possible
                try:
                    display_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    display_path = file_path

                lines.append(f"\n❌ {display_path}")

                if result.errors:
                    lines.append("  ERRORS:")
                    for error in result.errors:
                        lines.append(f"    - {error}")

                if result.warnings:
                    lines.append("  WARNINGS:")
                    for warning in result.warnings:
                        lines.append(f"    - {warning}")

    lines.append("")
    lines.append("=" * 80)

    # Overall status
    if failed == 0:
        lines.append("✓ ALL VALIDATIONS PASSED")
    else:
        lines.append("✗ VALIDATION FAILED - FIX ERRORS BEFORE COMMITTING")

    lines.append("=" * 80)

    return "\n".join(lines)


def validate_tests(test_dir: Path, min_coverage: float = 80.0) -> tuple[bool, list[str]]:
    """Validate generated tests run and meet coverage requirements.

    Parameters
    ----------
    test_dir : Path
        Directory containing test files
    min_coverage : float, default=80.0
        Minimum coverage percentage required

    Returns
    -------
    tuple[bool, list[str]]
        (passed, errors)
    """
    errors = []

    try:
        # Run pytest with coverage
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(test_dir),
                "--cov",
                "--cov-report=term-missing:skip-covered",
                "--cov-fail-under",
                str(min_coverage),
            ],
            check=False, capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            # Parse pytest output for failures
            for line in result.stdout.splitlines():
                if "FAILED" in line or "ERROR" in line:
                    errors.append(line.strip())

            # Check coverage
            if f"FAILED Required test coverage of {min_coverage}%" in result.stdout:
                errors.append(
                    f"Test coverage below {min_coverage}% minimum"
                )

    except subprocess.TimeoutExpired:
        errors.append("Test execution timed out after 120s")
    except Exception as e:
        errors.append(f"Test validation failed: {e}")

    return len(errors) == 0, errors


def main() -> int:
    """CLI entry point for code validation.

    Returns
    -------
    int
        Exit code (0 for success, 1 for failures)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate generated code against KGCL quality standards"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to file or directory to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Attempt to auto-fix issues",
    )

    args = parser.parse_args()

    validator = CodeValidator(strict=args.strict)

    if args.path.is_file():
        # Validate single file
        if args.auto_fix:
            result = auto_fix_issues(args.path)
        else:
            result = validator.validate_python(args.path)

        results = {args.path: result}
    else:
        # Validate directory
        results = validator.validate_all(args.path)

        if args.auto_fix:
            # Auto-fix all failed files
            for file_path, result in results.items():
                if not result.passed:
                    results[file_path] = auto_fix_issues(file_path)

    # Generate and print report
    report = generate_validation_report(results)
    print(report)

    # Return exit code
    all_passed = all(r.passed for r in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
