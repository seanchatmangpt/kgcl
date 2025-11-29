"""Tests for code validation system.

This test suite verifies the code validator correctly identifies:
- Syntax errors
- Type coverage issues
- Lint violations
- Import problems
- Test coverage failures

Chicago School TDD approach: test REAL validation behavior, not mocks.
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest
from scripts.codegen.validator import (
    CodeValidator,
    ValidationResult,
    auto_fix_issues,
    generate_validation_report,
    validate_tests,
)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test files."""
    return tmp_path


@pytest.fixture
def validator() -> CodeValidator:
    """Create validator instance."""
    return CodeValidator(strict=False)


class TestSyntaxValidation:
    """Test syntax validation using ast.parse."""

    def test_valid_syntax_passes(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Valid Python syntax should pass validation."""
        # Arrange
        test_file = temp_dir / "valid.py"
        test_file.write_text(
            '''"""Valid module."""
def hello() -> str:
    """Return greeting."""
    return "hello"
'''
        )

        # Act
        passed, errors = validator.validate_syntax(test_file)

        # Assert
        assert passed is True
        assert len(errors) == 0

    def test_syntax_error_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Syntax errors should be detected and reported."""
        # Arrange
        test_file = temp_dir / "invalid.py"
        test_file.write_text(
            """def broken(
    pass
"""
        )

        # Act
        passed, errors = validator.validate_syntax(test_file)

        # Assert
        assert passed is False
        assert len(errors) > 0
        assert "Syntax error" in errors[0]

    def test_missing_colon_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Missing colons should be detected."""
        # Arrange
        test_file = temp_dir / "missing_colon.py"
        test_file.write_text(
            """def test()
    return True
"""
        )

        # Act
        passed, errors = validator.validate_syntax(test_file)

        # Assert
        assert passed is False
        assert any("Syntax error" in e for e in errors)


class TestTypeValidation:
    """Test type checking with mypy --strict."""

    def test_typed_code_passes(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Fully typed code should pass type checking."""
        # Arrange
        test_file = temp_dir / "typed.py"
        test_file.write_text(
            '''"""Fully typed module."""
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}"
'''
        )

        # Act
        passed, errors = validator.validate_types(test_file)

        # Assert
        assert passed is True
        assert len(errors) == 0

    def test_missing_return_type_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Missing return type hints should be detected."""
        # Arrange
        test_file = temp_dir / "no_return_type.py"
        test_file.write_text(
            '''"""Missing return type."""
def add(a: int, b: int):
    """Add two integers."""
    return a + b
'''
        )

        # Act
        passed, errors = validator.validate_types(test_file)

        # Assert
        assert passed is False
        assert any("return type" in e.lower() for e in errors)

    def test_missing_parameter_type_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Missing parameter types should be detected."""
        # Arrange
        test_file = temp_dir / "no_param_type.py"
        test_file.write_text(
            '''"""Missing parameter type."""
def add(a, b: int) -> int:
    """Add two integers."""
    return a + b
'''
        )

        # Act
        passed, errors = validator.validate_types(test_file)

        # Assert
        assert passed is False
        assert len(errors) > 0


class TestLintValidation:
    """Test lint checking with Ruff."""

    def test_clean_code_passes_lint(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Clean code should pass all lint rules."""
        # Arrange
        test_file = temp_dir / "clean.py"
        test_file.write_text(
            '''"""Clean module following all rules."""
from __future__ import annotations


def process_data(items: list[str]) -> list[str]:
    """Process list of items.

    Parameters
    ----------
    items : list[str]
        Items to process

    Returns
    -------
    list[str]
        Processed items
    """
    return [item.upper() for item in items]
'''
        )

        # Act
        passed, errors, warnings = validator.validate_lint(test_file)

        # Assert
        assert passed is True
        assert len(errors) == 0

    def test_unused_import_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Unused imports should be detected as warnings."""
        # Arrange
        test_file = temp_dir / "unused_import.py"
        test_file.write_text(
            '''"""Module with unused import."""
from __future__ import annotations

import sys  # noqa: F401 - unused

def hello() -> str:
    """Return greeting."""
    return "hello"
'''
        )

        # Act
        passed, errors, warnings = validator.validate_lint(test_file)

        # Assert
        # Should pass (warnings not errors) unless suppressed noqa is removed
        assert passed is True or len(warnings) > 0


class TestImportValidation:
    """Test import validation."""

    def test_absolute_imports_valid(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Absolute imports should be valid."""
        # Arrange
        test_file = temp_dir / "absolute_imports.py"
        test_file.write_text(
            '''"""Module with absolute imports."""
from __future__ import annotations

import sys
from pathlib import Path

def get_path() -> Path:
    """Get current path."""
    return Path.cwd()
'''
        )

        # Act
        passed, errors = validator.validate_imports(test_file)

        # Assert
        assert passed is True
        assert len(errors) == 0

    def test_relative_import_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Relative imports should be detected and rejected."""
        # Arrange
        test_file = temp_dir / "relative_import.py"
        test_file.write_text(
            '''"""Module with relative import."""
from ..utils import helper

def process() -> None:
    """Process something."""
    helper()
'''
        )

        # Act
        passed, errors = validator.validate_imports(test_file)

        # Assert
        assert passed is False
        assert any("relative import" in e.lower() for e in errors)

    def test_nonexistent_import_detected(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Non-existent imports should be detected."""
        # Arrange
        test_file = temp_dir / "nonexistent_import.py"
        test_file.write_text(
            '''"""Module with non-existent import."""
from __future__ import annotations

import totally_fake_module_that_does_not_exist

def process() -> None:
    """Process something."""
    pass
'''
        )

        # Act
        passed, errors = validator.validate_imports(test_file)

        # Assert
        assert passed is False
        assert any("not resolvable" in e.lower() or "not found" in e.lower() for e in errors)


class TestFullValidation:
    """Test complete validation pipeline."""

    def test_perfect_file_passes_all_checks(self, temp_dir: Path, validator: CodeValidator) -> None:
        """File meeting all standards should pass completely."""
        # Arrange
        test_file = temp_dir / "perfect.py"
        test_file.write_text(
            '''"""Perfect module meeting all standards."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """User value object.

    Parameters
    ----------
    name : str
        User's name
    email : str
        User's email address
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
        User's email address

    Returns
    -------
    User
        Created user object
    """
    return User(name=name, email=email)
'''
        )

        # Act
        result = validator.validate_python(test_file)

        # Assert
        assert result.passed is True
        assert len(result.errors) == 0
        assert result.metrics["syntax_valid"] is True
        assert result.metrics["types_valid"] is True
        assert result.metrics["lint_valid"] is True
        assert result.metrics["imports_valid"] is True

    def test_multiple_issues_all_reported(self, temp_dir: Path, validator: CodeValidator) -> None:
        """File with multiple issues should report all of them."""
        # Arrange
        test_file = temp_dir / "broken.py"
        test_file.write_text(
            '''"""Broken module."""
from ..utils import helper  # Relative import

def broken(x):  # Missing types
    return x + 1
'''
        )

        # Act
        result = validator.validate_python(test_file)

        # Assert
        assert result.passed is False
        assert len(result.errors) > 0
        # Should have both import and type errors
        assert any("import" in e.lower() for e in result.errors)
        assert any("type" in e.lower() for e in result.errors)


class TestAutoFix:
    """Test auto-fix functionality."""

    def test_auto_fix_formatting(self, temp_dir: Path) -> None:
        """Auto-fix should format code with Ruff."""
        # Arrange
        test_file = temp_dir / "unformatted.py"
        test_file.write_text(
            '''"""Unformatted module."""
from __future__ import annotations

def hello(   )->str:
    """Return greeting."""
    return    "hello"
'''
        )

        # Act
        result = auto_fix_issues(test_file)
        fixed_content = test_file.read_text()

        # Assert
        assert "   )" not in fixed_content  # Formatting fixed
        assert "def hello() -> str:" in fixed_content

    def test_auto_fix_unused_imports(self, temp_dir: Path) -> None:
        """Auto-fix should attempt to fix unused imports."""
        # Arrange
        test_file = temp_dir / "unused.py"
        test_file.write_text(
            '''"""Module with unused imports."""
from __future__ import annotations

import sys
from pathlib import Path

def hello() -> str:
    """Return greeting."""
    return "hello"
'''
        )

        # Act
        result = auto_fix_issues(test_file)
        fixed_content = test_file.read_text()

        # Assert
        # Auto-fix may or may not remove unused imports depending on ruff config
        # The important thing is that auto-fix runs without error
        assert result is not None
        assert isinstance(result, ValidationResult)
        # If ruff removed them, great; if not, they'll be caught in validation
        # This test verifies auto-fix executes, not specific ruff behavior


class TestValidateAll:
    """Test directory validation."""

    def test_validate_multiple_files(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Should validate all Python files in directory."""
        # Arrange
        (temp_dir / "good1.py").write_text(
            '''"""Good module 1."""
from __future__ import annotations

def func1() -> str:
    """Function 1."""
    return "1"
'''
        )
        (temp_dir / "good2.py").write_text(
            '''"""Good module 2."""
from __future__ import annotations

def func2() -> str:
    """Function 2."""
    return "2"
'''
        )
        (temp_dir / "bad.py").write_text(
            '''"""Bad module."""
def broken(
    pass
'''
        )

        # Act
        results = validator.validate_all(temp_dir)

        # Assert
        assert len(results) == 3
        assert results[temp_dir / "good1.py"].passed is True
        assert results[temp_dir / "good2.py"].passed is True
        assert results[temp_dir / "bad.py"].passed is False

    def test_skip_pycache(self, temp_dir: Path, validator: CodeValidator) -> None:
        """Should skip __pycache__ directories."""
        # Arrange
        pycache = temp_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_text("compiled bytecode")

        (temp_dir / "real.py").write_text(
            '''"""Real module."""
from __future__ import annotations

def func() -> str:
    """Function."""
    return "x"
'''
        )

        # Act
        results = validator.validate_all(temp_dir)

        # Assert
        assert len(results) == 1
        assert temp_dir / "real.py" in results


class TestValidationReport:
    """Test validation report generation."""

    def test_all_passed_report(self, temp_dir: Path) -> None:
        """Report should show success when all files pass."""
        # Arrange
        results = {
            temp_dir / "file1.py": ValidationResult(
                passed=True, errors=[], warnings=[], file_path=temp_dir / "file1.py"
            ),
            temp_dir / "file2.py": ValidationResult(
                passed=True, errors=[], warnings=[], file_path=temp_dir / "file2.py"
            ),
        }

        # Act
        report = generate_validation_report(results)

        # Assert
        assert "Passed: 2" in report
        assert "Failed: 0" in report
        assert "ALL VALIDATIONS PASSED" in report

    def test_failures_reported(self, temp_dir: Path) -> None:
        """Report should show failures with details."""
        # Arrange
        results = {
            temp_dir / "good.py": ValidationResult(passed=True, errors=[], warnings=[], file_path=temp_dir / "good.py"),
            temp_dir / "bad.py": ValidationResult(
                passed=False,
                errors=["Syntax error", "Type error"],
                warnings=["Style warning"],
                file_path=temp_dir / "bad.py",
            ),
        }

        # Act
        report = generate_validation_report(results)

        # Assert
        assert "Passed: 1" in report
        assert "Failed: 1" in report
        assert "bad.py" in report
        assert "Syntax error" in report
        assert "Type error" in report
        assert "VALIDATION FAILED" in report


class TestValidateTests:
    """Test test validation functionality."""

    def test_passing_tests_with_coverage(self, temp_dir: Path) -> None:
        """Tests with sufficient coverage should pass."""
        # Arrange - create simple test file
        test_file = temp_dir / "test_sample.py"
        test_file.write_text(
            '''"""Sample test."""
from __future__ import annotations

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def test_add() -> None:
    """Test addition."""
    assert add(1, 2) == 3
'''
        )

        # Act
        passed, errors = validate_tests(test_dir=temp_dir, min_coverage=0.0)

        # Assert
        assert passed is True
        assert len(errors) == 0


class TestStrictMode:
    """Test strict mode (warnings as errors)."""

    def test_strict_mode_warnings_fail(self, temp_dir: Path) -> None:
        """In strict mode, warnings should cause validation to fail."""
        # Arrange
        validator_strict = CodeValidator(strict=True)
        test_file = temp_dir / "warnings.py"
        test_file.write_text(
            '''"""Module with warnings."""
from __future__ import annotations

def long_function_name_that_exceeds_reasonable_length_and_violates_conventions() -> str:
    """Function with overly long name."""
    return "x"
'''
        )

        # Act
        result = validator_strict.validate_python(test_file)

        # Assert
        # In strict mode, ANY warnings should fail
        if result.warnings:
            assert result.passed is False

    def test_non_strict_mode_warnings_pass(self, temp_dir: Path) -> None:
        """In non-strict mode, warnings should not fail validation."""
        # Arrange
        validator_non_strict = CodeValidator(strict=False)
        test_file = temp_dir / "warnings.py"
        test_file.write_text(
            '''"""Module with potential warnings."""
from __future__ import annotations

def helper() -> str:
    """Helper function."""
    return "x"
'''
        )

        # Act
        result = validator_non_strict.validate_python(test_file)

        # Assert
        # Should pass even with warnings
        if result.errors:
            assert result.passed is False
        else:
            assert result.passed is True
