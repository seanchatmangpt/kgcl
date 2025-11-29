"""Tests for code validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from kgcl.codegen.base.validator import ValidationError, Validator


class TestValidator:
    """Test Validator functionality."""

    def test_init_with_defaults(self) -> None:
        """Test validator initialization with default settings."""
        validator = Validator()

        assert validator.max_line_length == 120
        assert validator.require_type_hints is True
        assert validator.require_docstrings is True

    def test_init_with_custom_settings(self) -> None:
        """Test validator initialization with custom settings."""
        validator = Validator(max_line_length=100, require_type_hints=False, require_docstrings=False)

        assert validator.max_line_length == 100
        assert validator.require_type_hints is False
        assert validator.require_docstrings is False

    def test_validate_python_valid_code(self) -> None:
        """Test validation of valid Python code."""
        validator = Validator()

        valid_code = '''
from __future__ import annotations

def hello(name: str) -> str:
    """Greet a person.

    Parameters
    ----------
    name : str
        Person's name

    Returns
    -------
    str
        Greeting message
    """
    return f"Hello, {name}!"
'''

        # Should not raise
        validator.validate_python(valid_code)

    def test_validate_python_syntax_error(self) -> None:
        """Test validation rejects syntax errors."""
        validator = Validator()

        invalid_code = "def hello(\n    return 'broken'"

        with pytest.raises(ValidationError, match="(Syntax error|Invalid Python syntax)"):
            validator.validate_python(invalid_code)

    def test_validate_python_missing_type_hints(self) -> None:
        """Test validation rejects missing type hints when required."""
        validator = Validator(require_type_hints=True)

        code_without_hints = '''
def hello(name):
    """Say hello."""
    return f"Hello, {name}!"
'''

        with pytest.raises(ValidationError, match="missing return type hint"):
            validator.validate_python(code_without_hints)

    def test_validate_python_accepts_missing_hints_when_disabled(self) -> None:
        """Test validation accepts missing type hints when not required."""
        validator = Validator(require_type_hints=False, require_docstrings=False)

        code_without_hints = """
def hello(name):
    return f"Hello, {name}!"
"""

        # Should not raise
        validator.validate_python(code_without_hints)

    def test_validate_python_missing_docstring(self) -> None:
        """Test validation rejects missing docstrings when required."""
        validator = Validator(require_docstrings=True)

        code_without_docstring = """
def hello(name: str) -> str:
    return f"Hello, {name}!"
"""

        with pytest.raises(ValidationError, match="missing docstring"):
            validator.validate_python(code_without_docstring)

    def test_validate_python_accepts_missing_docstring_when_disabled(self) -> None:
        """Test validation accepts missing docstrings when not required."""
        validator = Validator(require_docstrings=False)

        code_without_docstring = """
def hello(name: str) -> str:
    return f"Hello, {name}!"
"""

        # Should not raise
        validator.validate_python(code_without_docstring)

    def test_validate_python_line_length(self) -> None:
        """Test validation checks line length."""
        validator = Validator(max_line_length=50)

        long_line_code = '''
def hello(name: str) -> str:
    """Short."""
    return "This is a very long line that definitely exceeds fifty characters"
'''

        with pytest.raises(ValidationError, match="exceeds"):
            validator.validate_python(long_line_code)

    def test_validate_python_accepts_short_lines(self) -> None:
        """Test validation accepts code within line length limit."""
        validator = Validator(max_line_length=120, require_docstrings=False)

        short_line_code = """
def hello(name: str) -> str:
    return f"Hello, {name}!"
"""

        # Should not raise
        validator.validate_python(short_line_code)

    def test_validate_python_skips_private_functions(self) -> None:
        """Test validation skips private function checks."""
        validator = Validator(require_type_hints=True, require_docstrings=True)

        private_function_code = '''
def _private_helper(x):
    return x * 2

def public(x: int) -> int:
    """Public function."""
    return _private_helper(x)
'''

        # Should not raise - private functions are skipped
        validator.validate_python(private_function_code)

    def test_validate_python_rejects_relative_imports(self) -> None:
        """Test validation rejects relative imports."""
        validator = Validator()

        relative_import_code = '''
from ..module import function

def hello() -> str:
    """Say hello."""
    return "hello"
'''

        with pytest.raises(ValidationError, match="Relative import"):
            validator.validate_python(relative_import_code)

    def test_validate_file(self, tmp_path: Path) -> None:
        """Test file validation."""
        validator = Validator(require_docstrings=False)

        # Create valid Python file
        file_path = tmp_path / "test.py"
        file_path.write_text("""
from __future__ import annotations

def hello(name: str) -> str:
    return f"Hello, {name}!"
""")

        # Should not raise
        validator.validate_file(file_path)

    def test_validate_file_not_found(self, tmp_path: Path) -> None:
        """Test validation of non-existent file."""
        validator = Validator()

        nonexistent = tmp_path / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            validator.validate_file(nonexistent)
