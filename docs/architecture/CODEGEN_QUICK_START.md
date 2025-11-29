# KGCL Code Generation Quick Start

**Related:** [ADR-003: Unified Code Generation Architecture](ADR-003-UNIFIED-CODEGEN-ARCHITECTURE.md)

---

## Overview

KGCL provides a unified code generation framework for transforming various input formats (RDF, Java, OpenAPI) into production-ready code across multiple languages (Python, TypeScript, React).

---

## Quick Examples

### 1. Generate Python Client from Java

```bash
# Generate Python client from Java service
kgcl codegen java-python \
    --input vendors/yawlui-v5.2/YawlService.java \
    --output src/kgcl/yawl_ui/clients \
    --validate

# Output:
# ✓ Generated: src/kgcl/yawl_ui/clients/yawl_service.py
# ✓ Generated: tests/yawl_ui/test_yawl_service.py
# ✓ Validation passed (100% types, 0 errors)
```

### 2. Generate CLI from RDF

```bash
# Generate Typer CLI from RDF specification
kgcl codegen cli \
    --input .kgc/cli.ttl \
    --output src/kgcl/cli.py \
    --validate

# Output:
# ✓ Generated: src/kgcl/cli.py
# ✓ Commands: 12 discovered
# ✓ Validation passed
```

### 3. Generate via Projection (N3 Reasoning)

```bash
# Generate multi-language artifacts with N3 reasoning
kgcl codegen projection \
    --template api_openapi \
    --output src/kgcl/api \
    --params version=1.0 \
    --validate

# Output:
# ✓ N3 reasoning: 42 triples inferred
# ✓ Generated: src/kgcl/api/openapi.yaml
# ✓ Generated: src/kgcl/api/models.py
# ✓ Validation passed
```

### 4. List Available Generators

```bash
kgcl codegen --list

# Output:
# Available generators:
#   - cli           (RDF→Typer CLI)
#   - java-python   (Java→Python client)
#   - java-react    (Java→React component)
#   - projection    (RDF→Multi-language with N3)
#   - openapi       (OpenAPI→FastAPI)
```

---

## Creating a Custom Generator

### Step 1: Define Parser

```python
# src/kgcl/codegen/parsers/protobuf_parser.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProtoMessage:
    """Represents a Protobuf message."""
    name: str
    fields: list[ProtoField]
    package: str

class ProtobufParser:
    """Parse .proto files."""

    def parse(self, input_path: Path) -> ProtoMessage:
        """Parse Protobuf file.

        Parameters
        ----------
        input_path : Path
            Path to .proto file

        Returns
        -------
        ProtoMessage
            Parsed message definition
        """
        # Implementation: parse .proto file
        content = input_path.read_text()
        # ... parsing logic ...
        return ProtoMessage(...)
```

### Step 2: Create Type Mapper

```python
# src/kgcl/codegen/mappers/proto_to_python.py

from __future__ import annotations

from kgcl.codegen.mappers.base import TypeMapper

class ProtoToPythonMapper(TypeMapper):
    """Map Protobuf types to Python types."""

    def map_type(self, proto_type: str) -> str:
        """Map Protobuf type to Python type.

        Parameters
        ----------
        proto_type : str
            Protobuf type (e.g., "int32", "string")

        Returns
        -------
        str
            Python type hint (e.g., "int", "str")
        """
        mapping = {
            "int32": "int",
            "int64": "int",
            "float": "float",
            "double": "float",
            "string": "str",
            "bool": "bool",
            "bytes": "bytes",
        }
        return mapping.get(proto_type, "Any")
```

### Step 3: Create Template

```jinja2
{# src/kgcl/codegen/templates/python/pydantic_model.py.j2 #}
{# ---
name: Pydantic Model Generator
version: 1.0.0
language: python
framework: pydantic
input: ProtoMessage
variables:
  - message_name: str (Python class name)
  - fields: list[ProtoField] (Message fields)
--- #}
from __future__ import annotations

from pydantic import BaseModel, Field

class {{ message_name }}(BaseModel):
    """Generated from {{ proto_file }}."""

    {% for field in fields %}
    {{ field.name }}: {{ field.python_type }}{% if field.has_default %} = Field(default={{ field.default }}){% endif %}
    {% endfor %}
```

### Step 4: Implement Generator

```python
# src/kgcl/codegen/generators/protobuf_generator.py

from __future__ import annotations

from pathlib import Path

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.registry import GeneratorRegistry
from kgcl.codegen.parsers.protobuf_parser import ProtobufParser
from kgcl.codegen.mappers.proto_to_python import ProtoToPythonMapper
from kgcl.codegen.validators.code_validator import CodeValidator

@GeneratorRegistry.register("protobuf-python")
class ProtobufPythonGenerator(BaseGenerator):
    """Generate Pydantic models from Protobuf definitions.

    Examples
    --------
    >>> generator = ProtobufPythonGenerator(
    ...     template_dir=Path("templates/"),
    ...     output_dir=Path("src/models/"),
    ... )
    >>> result = generator.generate(Path("schema.proto"))
    >>> result.output_path
    PosixPath('src/models/schema.py')
    """

    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
    ) -> None:
        """Initialize Protobuf→Python generator."""
        super().__init__(
            parser=ProtobufParser(),
            template_dir=template_dir / "python",
            output_dir=output_dir,
            validator=CodeValidator(strict=True),
            auto_format=True,
        )
        self.mapper = ProtoToPythonMapper()

    def generate(self, input_path: Path) -> GenerationResult:
        """Generate Pydantic model from .proto file.

        Parameters
        ----------
        input_path : Path
            Path to .proto file

        Returns
        -------
        GenerationResult
            Generation results with validation
        """
        # 1. Parse Protobuf
        proto_message = self.parser.parse(input_path)

        # 2. Map fields to Python types
        fields = [
            {
                "name": field.name,
                "python_type": self.mapper.map_type(field.proto_type),
                "has_default": field.default is not None,
                "default": field.default,
            }
            for field in proto_message.fields
        ]

        # 3. Render template
        code = self.template_engine.render(
            "pydantic_model.py.j2",
            {
                "message_name": proto_message.name,
                "fields": fields,
                "proto_file": input_path.name,
            },
        )

        # 4. Write and validate
        output_path = self.output_dir / f"{proto_message.name.lower()}.py"
        return self._write_and_validate(
            code,
            output_path,
            {"template": "pydantic_model.py.j2", "source": str(input_path)},
        )
```

### Step 5: Write Tests

```python
# tests/codegen/test_protobuf_generator.py

from __future__ import annotations

from pathlib import Path

import pytest

from kgcl.codegen.generators.protobuf_generator import ProtobufPythonGenerator

def test_protobuf_generator_creates_valid_pydantic_model(tmp_path: Path) -> None:
    """Test Protobuf→Pydantic generation produces valid code."""
    # Arrange
    proto_content = """
    syntax = "proto3";
    package example;

    message User {
        int32 id = 1;
        string name = 2;
        string email = 3;
    }
    """
    proto_file = tmp_path / "user.proto"
    proto_file.write_text(proto_content)

    template_dir = Path("src/kgcl/codegen/templates")
    output_dir = tmp_path / "output"

    generator = ProtobufPythonGenerator(template_dir, output_dir)

    # Act
    result = generator.generate(proto_file)

    # Assert
    assert result.output_path.exists()
    assert result.validation is not None
    assert result.validation.passed

    # Verify generated code is importable
    code = result.output_path.read_text()
    assert "from pydantic import BaseModel" in code
    assert "class User(BaseModel):" in code
    assert "id: int" in code
    assert "name: str" in code
    assert "email: str" in code

def test_protobuf_generator_handles_nested_messages(tmp_path: Path) -> None:
    """Test generator handles nested Protobuf messages."""
    # Similar structure...
    pass

def test_protobuf_generator_validates_output(tmp_path: Path) -> None:
    """Test generator validates generated code."""
    # Verify validation runs and catches errors
    pass
```

### Step 6: Use the Generator

```bash
# Via CLI
kgcl codegen protobuf-python \
    --input schema.proto \
    --output src/kgcl/models

# Via Python API
from pathlib import Path
from kgcl.codegen.base.registry import GeneratorRegistry

generator_cls = GeneratorRegistry.get("protobuf-python")
generator = generator_cls(
    template_dir=Path("templates/"),
    output_dir=Path("src/models/"),
)
result = generator.generate(Path("schema.proto"))

print(f"Generated: {result.output_path}")
print(f"Validation: {'✓' if result.validation.passed else '✗'}")
```

---

## Development Checklist

When creating a new generator, ensure:

### Required Components
- [ ] Parser class implementing `Parser` protocol
- [ ] Type mapper extending `TypeMapper` base class
- [ ] Generator extending `BaseGenerator`
- [ ] Jinja2 templates with YAML frontmatter
- [ ] Self-registration via `@GeneratorRegistry.register()`

### Quality Standards
- [ ] 100% type coverage (`poe type-check` passes)
- [ ] All Ruff rules passing (`poe lint` passes)
- [ ] 80%+ test coverage (`poe test` with coverage report)
- [ ] NumPy-style docstrings on all public methods
- [ ] Absolute imports only (no relative imports)
- [ ] Frozen dataclasses for value objects

### Documentation
- [ ] Module-level docstring with examples
- [ ] Usage examples in docstrings
- [ ] Template variables documented in frontmatter
- [ ] README with generator-specific instructions
- [ ] Integration tests demonstrating end-to-end flow

### Validation
- [ ] Generated code passes syntax validation
- [ ] Generated code passes type checking
- [ ] Generated code passes lint checking
- [ ] Generated tests achieve 80%+ coverage
- [ ] Auto-formatting works correctly

### Integration
- [ ] Generator listed in `kgcl codegen --list`
- [ ] CLI help documentation complete
- [ ] Pre-commit hooks validate generator output
- [ ] CI/CD includes generator in test suite

---

## Common Patterns

### Pattern 1: Multi-File Generation

```python
def generate(self, input_path: Path) -> GenerationResult:
    """Generate multiple files from single input."""
    # Parse input
    schema = self.parser.parse(input_path)

    # Generate main file
    main_code = self.template_engine.render("main.py.j2", {...})
    main_path = self.output_dir / "main.py"
    main_path.write_text(main_code)

    # Generate test file
    test_code = self.template_engine.render("test.py.j2", {...})
    test_path = self.output_dir / "test_main.py"
    test_path.write_text(test_code)

    # Return primary result
    return self._write_and_validate(main_code, main_path, {...})
```

### Pattern 2: Incremental Generation

```python
def generate_batch(self, input_files: list[Path]) -> list[GenerationResult]:
    """Generate code from multiple input files."""
    results = []
    for input_file in input_files:
        result = self.generate(input_file)
        results.append(result)

        # Stop on first validation failure
        if result.validation and not result.validation.passed:
            break

    return results
```

### Pattern 3: Custom Validation

```python
def validate(self, result: GenerationResult) -> bool:
    """Custom validation beyond standard checks."""
    # Run standard validation
    if not super().validate(result):
        return False

    # Add custom checks (e.g., API compatibility)
    api_valid = self._check_api_compatibility(result.output_path)
    security_valid = self._check_security_patterns(result.output_path)

    return api_valid and security_valid
```

---

## Troubleshooting

### Generated Code Fails Validation

```bash
# Run validation manually
kgcl codegen validate src/kgcl/generated/

# Auto-fix common issues
kgcl codegen validate --auto-fix src/kgcl/generated/

# Common fixes:
# - Missing type hints → Add via annotations
# - Import errors → Check absolute import paths
# - Lint errors → Run `ruff check --fix`
```

### Template Rendering Fails

```python
# Enable debug mode in template engine
engine = TemplateEngine(template_dir, strict=False)

# Check template syntax
from jinja2 import Template
try:
    Template(template_content)
except Exception as e:
    print(f"Template syntax error: {e}")

# Verify context variables
print(f"Template expects: {template.module.__doc__}")
print(f"Context provides: {context.keys()}")
```

### Parser Errors

```python
# Add error handling in parser
try:
    parsed = parser.parse(input_path)
except ParseError as e:
    print(f"Parse error at line {e.lineno}: {e.msg}")
    print(f"Context: {e.context}")
```

---

## Performance Optimization

### Caching Template Compilation

```python
# TemplateEngine automatically caches compiled templates
# For additional performance:

from functools import lru_cache

class CachedGenerator(BaseGenerator):
    @lru_cache(maxsize=128)
    def _compile_template(self, template_name: str):
        return self.template_engine.env.get_template(template_name)
```

### Parallel Generation

```python
from concurrent.futures import ThreadPoolExecutor

def generate_parallel(files: list[Path]) -> list[GenerationResult]:
    """Generate code from multiple files in parallel."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(generator.generate, files)
    return list(results)
```

---

## References

- [ADR-003: Unified Code Generation Architecture](ADR-003-UNIFIED-CODEGEN-ARCHITECTURE.md)
- [CLAUDE.md - Project Standards](../../CLAUDE.md)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [KGCL Build System](../BUILD_SYSTEM_SUMMARY.md)

---

**Status:** Reference implementation for unified code generation framework.
