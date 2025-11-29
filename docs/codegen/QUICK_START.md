# Code Generator Quick Start

## 5-Minute Quick Start

### 1. Generate from Single Java File

```python
from pathlib import Path
from scripts.codegen.generator import CodeGenerator

# Initialize generator
gen = CodeGenerator(
    template_dir=Path("templates/codegen"),
    output_dir=Path("src")
)

# Generate Python client
python_file = gen.generate_python_client(
    Path("path/to/YourService.java")
)

print(f"Generated: {python_file}")
```

### 2. Run Demonstration

```bash
uv run python examples/codegen_demo.py
```

### 3. Test Everything

```bash
# Run all tests
uv run pytest tests/codegen/ -v

# Type check
uv run mypy scripts/codegen --strict

# Lint
uv run ruff check scripts/codegen
```

## Common Use Cases

### Parse Java File

```python
from pathlib import Path
from scripts.codegen.java_parser import JavaParser

parser = JavaParser()
java_class = parser.parse_file(Path("MyService.java"))

print(f"Class: {java_class.name}")
print(f"Package: {java_class.package}")
print(f"Methods: {[m.name for m in java_class.methods]}")
```

### Map Java Types to Python

```python
from scripts.codegen.type_mapper import TypeMapper

mapper = TypeMapper()

# Simple types
assert mapper.map_type("String") == "str"
assert mapper.map_type("int") == "int"

# Collections
assert mapper.map_type("List<String>") == "list[str]"
assert mapper.map_type("Map<String, Object>") == "dict[str, Any]"

# Nested
assert mapper.map_type("Map<String, List<Integer>>") == "dict[str, list[int]]"

# Arrays
assert mapper.map_type("String[]") == "list[str]"
```

### Render Templates

```python
from pathlib import Path
from scripts.codegen.template_engine import TemplateEngine

engine = TemplateEngine(Path("templates/codegen"))

# Render from file
code = engine.render("python_client.py.jinja2", {
    "class_name": "MyService",
    "methods": [...],
})

# Render from string
code = engine.render_string(
    "{{ name | snake_case }}",
    {"name": "MyClassName"}
)
print(code)  # "my_class_name"
```

## Type Mappings

| Java | Python | Example |
|------|--------|---------|
| `String` | `str` | `"hello"` |
| `int`, `long` | `int` | `42` |
| `boolean` | `bool` | `True` |
| `List<T>` | `list[T]` | `["a", "b"]` |
| `Map<K, V>` | `dict[K, V]` | `{"key": "value"}` |
| `Set<T>` | `set[T]` | `{"a", "b"}` |
| `T[]` | `list[T]` | `["a", "b"]` |
| `void` | `None` | `None` |

## Files Generated

For input `MyService.java`:

```
src/kgcl/yawl_ui/service/
└── my_service.py              # Python client

tests/kgcl/yawl_ui/service/
└── test_my_service.py         # Test file
```

## Quality Checks

```bash
# All checks in one command
uv run mypy scripts/codegen --strict && \
uv run pytest tests/codegen/ -v && \
uv run ruff check scripts/codegen
```

Expected output:
```
Success: no issues found in 8 source files
41 passed in 3.16s
All checks passed!
```

## Architecture

```
Java File → Parser → JavaClass (metadata)
                ↓
            Type Mapper → Python types
                ↓
          Template Engine → Python code
```

## Next Steps

- **Full Documentation**: `scripts/codegen/README.md`
- **Implementation Details**: `docs/codegen/IMPLEMENTATION_SUMMARY.md`
- **Source Code**: `scripts/codegen/`
- **Tests**: `tests/codegen/`
- **Examples**: `examples/codegen_demo.py`

## Support

For issues or questions:
1. Check `scripts/codegen/README.md`
2. Review test examples in `tests/codegen/`
3. Run demo: `uv run python examples/codegen_demo.py`
