# YAWL UI Code Generator

Semantic code generator for converting YAWL UI Java sources to Python clients.

## Overview

This code generator parses Java service classes from YAWL UI and generates:
1. **Python client classes** with full type hints
2. **Pytest test files** with fixtures and test stubs
3. **Comprehensive documentation** from Javadoc comments

## Architecture

```
┌─────────────┐
│ Java Parser │──> JavaClass (semantic metadata)
└─────────────┘

┌─────────────┐
│ Type Mapper │──> Python type hints
└─────────────┘

┌─────────────────┐
│ Template Engine │──> Python code + tests
└─────────────────┘

┌──────────────────┐
│ Code Generator   │──> Orchestrator
└──────────────────┘

┌──────────────────┐
│ Batch Processor  │──> Parallel processing
└──────────────────┘
```

## Components

### 1. Java Parser (`java_parser.py`)

Parses Java source files using `javalang` and extracts:
- Class metadata (package, imports, modifiers, annotations)
- Field declarations with types
- Method signatures with parameters and return types
- Javadoc comments for documentation
- Generic type information

**Example:**
```python
from pathlib import Path
from java_parser import JavaParser

parser = JavaParser()
java_class = parser.parse_file(Path("Service.java"))

print(java_class.name)  # "MyService"
print(java_class.package)  # "org.yawlfoundation.yawl.ui.service"
print(java_class.methods[0].name)  # "getItems"
```

### 2. Type Mapper (`type_mapper.py`)

Maps Java types to Python type hints:
- Primitives: `int`, `long` → `int`
- Collections: `List<String>` → `list[str]`
- Maps: `Map<String, Object>` → `dict[str, Any]`
- Nested generics: `Map<String, List<Integer>>` → `dict[str, list[int]]`
- Arrays: `String[]` → `list[str]`

**Example:**
```python
from type_mapper import TypeMapper

mapper = TypeMapper()
assert mapper.map_type("List<String>") == "list[str]"
assert mapper.map_type("Map<String, Object>") == "dict[str, Any]"

# Custom mappings
mapper.add_custom_mapping("YTask", "YawlTask")
```

### 3. Template Engine (`template_engine.py`)

Jinja2-based template rendering with custom filters:
- `snake_case`: `MyClassName` → `my_class_name`
- `camel_case`: `my_function` → `MyFunction`
- `indent`: Indent code blocks
- `python_default`: Get default values for types

**Templates:**
- `python_client.py.jinja2` - Python class template
- `pytest_test.py.jinja2` - Test file template

### 4. Code Generator (`generator.py`)

Main orchestrator that:
1. Parses Java files
2. Maps types to Python
3. Renders templates
4. Generates Python code and tests
5. Organizes output by package structure

**Example:**
```python
from pathlib import Path
from generator import CodeGenerator

gen = CodeGenerator(
    template_dir=Path("templates/codegen"),
    output_dir=Path("src")
)

python_file = gen.generate_python_client(Path("MyService.java"))
# Generates:
# - src/kgcl/yawl_ui/service/my_service.py
# - tests/kgcl/yawl_ui/service/test_my_service.py
```

### 5. Batch Processor (`batch_process.py`)

Parallel processing of multiple Java files:
- ProcessPoolExecutor for parallelism (default: 8 workers)
- Package-based grouping
- Comprehensive error reporting
- Progress tracking

**Example:**
```python
from batch_process import process_yawl_ui

# Process all YAWL UI sources
process_yawl_ui()
```

## Usage

### Generate from Single Java File

```python
from pathlib import Path
from generator import CodeGenerator

gen = CodeGenerator(
    template_dir=Path("templates/codegen"),
    output_dir=Path("src")
)

# Generate Python client
python_file = gen.generate_python_client(
    Path("vendors/yawlui-v5.2/src/.../MyService.java")
)
```

### Batch Process All Files

```bash
uv run python scripts/codegen/batch_process.py
```

This processes all Java files in `vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/`.

## Generated Code Structure

### Input (Java):
```java
package org.yawlfoundation.yawl.ui.service;

import java.util.List;

/**
 * Sample service for managing items.
 */
public class ItemService {
    /**
     * Get all items matching filter.
     * @param filter Filter criteria
     * @return List of matching items
     */
    public List<String> getItems(String filter) {
        return null;
    }
}
```

### Output (Python):
```python
"""ItemService Python client.

Sample service for managing items.
"""

from __future__ import annotations


class ItemService:
    """Sample service for managing items."""

    def __init__(self) -> None:
        """Initialize ItemService client."""
        pass

    def get_items(self, filter: str) -> list[str]:
        """Get all items matching filter.

        Parameters
        ----------
        filter : str
            Filter criteria

        Returns
        -------
        list[str]
            List of matching items
        """
        raise NotImplementedError("Generated stub - implement for real usage")
```

### Output (Test):
```python
"""Tests for ItemService Python client."""

from __future__ import annotations

import pytest

from kgcl.yawl_ui.service.item_service import ItemService


class TestItemService:
    """Test ItemService client functionality."""

    @pytest.fixture
    def client(self) -> ItemService:
        """Create client instance for testing."""
        return ItemService()

    def test_get_items(self, client: ItemService) -> None:
        """Test get_items method."""
        filter: str = ""

        with pytest.raises(NotImplementedError):
            result = client.get_items(filter)
```

## Type Mapping Reference

| Java Type | Python Type |
|-----------|-------------|
| `int`, `long` | `int` |
| `float`, `double` | `float` |
| `boolean` | `bool` |
| `String` | `str` |
| `void` | `None` |
| `Object` | `Any` |
| `List<T>` | `list[T]` |
| `Set<T>` | `set[T]` |
| `Map<K, V>` | `dict[K, V]` |
| `T[]` | `list[T]` |
| `Date` | `datetime` |
| `UUID` | `str` |

## Testing

Run the test suite:

```bash
# All tests
uv run pytest tests/codegen/ -v

# Specific component
uv run pytest tests/codegen/test_java_parser.py -v

# With coverage
uv run pytest tests/codegen/ --cov=scripts/codegen --cov-report=html
```

## Quality Checks

```bash
# Type checking (strict mode)
uv run mypy scripts/codegen --strict

# Linting
uv run ruff check scripts/codegen

# Formatting
uv run ruff format scripts/codegen

# All checks
uv run mypy scripts/codegen --strict && \
uv run ruff check scripts/codegen && \
uv run pytest tests/codegen/
```

## Dependencies

- `javalang` - Java source parsing
- `jinja2` - Template rendering
- Python 3.13+ (PEP 695 type syntax)

## Limitations & Future Work

### Current Limitations

1. **Method bodies not extracted** - Only generates stubs
2. **No inheritance mapping** - Base classes noted but not implemented
3. **Annotations not processed** - Java annotations are captured but not mapped
4. **No dependency resolution** - Generated code may have missing imports

### Planned Enhancements

1. **Semantic analysis** - Understand method behavior from code
2. **Dependency graph** - Resolve and generate all dependencies
3. **Advanced patterns** - Factory, singleton, builder patterns
4. **Test generation** - Real test cases based on method semantics
5. **Documentation** - Full API documentation generation

## Contributing

When adding new components:

1. Create module in `scripts/codegen/`
2. Add comprehensive tests in `tests/codegen/`
3. Update this README
4. Ensure 100% type coverage (`mypy --strict`)
5. Follow NumPy docstring convention
6. Maintain 80%+ test coverage

---

## Code Validation System

### Overview

The validation system ensures all generated code meets KGCL's strict quality standards before being committed.

### Validation Layers

1. **Syntax Validation** - `ast.parse()` ensures valid Python
2. **Type Checking** - `mypy --strict` requires 100% type coverage
3. **Lint Checking** - `ruff check` enforces 400+ quality rules
4. **Import Validation** - Prevents relative imports, checks resolvability
5. **Test Validation** - Ensures 80%+ coverage and passing tests

### Usage

```bash
# Validate generated code
poe validate-code src/kgcl/yawl_ui/

# Strict mode (warnings as errors)
poe validate-code-strict src/kgcl/yawl_ui/

# Auto-fix issues
poe validate-code-autofix src/kgcl/yawl_ui/
```

### Python API

```python
from pathlib import Path
from scripts.codegen.validator import CodeValidator, auto_fix_issues

validator = CodeValidator(strict=True)
results = validator.validate_all(Path("src/kgcl/yawl_ui"))

# Auto-fix issues
for file_path, result in results.items():
    if not result.passed:
        auto_fix_issues(file_path)
```

### Recommended Workflow

1. **Generate Code**: Run code generator
2. **Validate**: `poe validate-code src/kgcl/yawl_ui/`
3. **Auto-Fix**: `poe validate-code-autofix src/kgcl/yawl_ui/`
4. **Re-Validate**: Verify all issues resolved
5. **Manual Review**: Address unfixable issues
6. **Commit**: Only after ALL validations pass

### Demo

```bash
# Run validation demonstration
uv run python examples/codegen_validation_demo.py
```

### Documentation

- **Full Guide**: `docs/codegen/VALIDATION.md`
- **API Reference**: `scripts/codegen/validator.py`
- **Examples**: `examples/codegen_validation_demo.py`
- **Tests**: `tests/codegen/test_validator.py`

---

## License

Part of the KGCL research library.
