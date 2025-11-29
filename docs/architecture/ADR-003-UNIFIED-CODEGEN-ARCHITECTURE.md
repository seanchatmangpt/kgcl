# ADR-003: Unified Code Generation Architecture

**Status:** Proposed
**Date:** 2025-11-28
**Authors:** System Architecture Designer
**Supersedes:** None
**Related:** ADR-001 (Hybrid Engine), ADR-002 (Temporal N3)

---

## Context

KGCL currently has **three separate code generation systems** operating in isolation:

### Existing Systems Analysis

| System | Input | Output | Technology | Location | Status |
|--------|-------|--------|------------|----------|--------|
| **CLI Generator** | RDF/TTL (`.kgc/cli.ttl`) | Python CLI (Typer) | rdflib + Jinja2 (.j2) | Not found in codebase | Missing |
| **YAWL Generator** | Java source files | Python clients, React components, Tests | javalang + Jinja2 (.jinja2) | `scripts/codegen/` | Active |
| **Projection Engine** | RDF graphs + SPARQL | Multi-language artifacts | N3 reasoning + Jinja2 | `src/kgcl/projection/` | Production |

### Problems with Current Fragmentation

1. **Code Duplication**
   - Three separate Jinja2 template engines with different configurations
   - Duplicate type mapping logic (Java→Python, RDF→Python, etc.)
   - Separate validation systems (YAWL has comprehensive validator, others minimal)

2. **Inconsistent Standards**
   - Different template file extensions: `.j2`, `.jinja2`, `.njk`
   - Inconsistent naming conventions (snake_case vs camelCase filters)
   - No unified quality enforcement (YAWL has strict validation, projection has none)

3. **Missing Cross-Generator Features**
   - Projection engine has N3 reasoning, YAWL generator doesn't
   - YAWL generator has comprehensive validation, projection doesn't
   - No shared registry or discovery mechanism

4. **Scalability Issues**
   - Adding new generator requires reimplementing common infrastructure
   - No standardized parser protocol (each implements own parsing)
   - Template organization scattered across multiple locations

### Strategic Requirements

**From CLAUDE.md**:
- ✅ 100% type coverage (mypy --strict)
- ✅ All 400+ Ruff rules enforced
- ✅ Chicago School TDD (80%+ coverage)
- ✅ NumPy-style docstrings
- ✅ Absolute imports only
- ✅ Frozen dataclasses for value objects

**From Build System**:
- ✅ Pre-commit hooks block unvalidated code
- ✅ Cargo-make enforces zero-defect quality
- ✅ Lean Six Sigma standards (99.99966% defect-free)

---

## Decision

**Consolidate all code generation under a unified framework: `src/kgcl/codegen/`**

### Architecture Overview

```
src/kgcl/codegen/
├── __init__.py
├── base/                          # Shared infrastructure
│   ├── __init__.py
│   ├── generator.py               # Abstract BaseGenerator
│   ├── parser.py                  # Parser protocol
│   ├── template_engine.py         # Unified Jinja2 engine
│   ├── validator.py               # Comprehensive validation
│   └── registry.py                # Generator registry
├── generators/                    # Concrete implementations
│   ├── __init__.py
│   ├── cli_generator.py           # RDF→CLI generator
│   ├── java_generator.py          # Java→Python generator
│   ├── react_generator.py         # Java→React generator
│   ├── projection_generator.py    # RDF→Multi-language (N3-enabled)
│   └── api_generator.py           # Future: OpenAPI→FastAPI
├── parsers/                       # Input parsers
│   ├── __init__.py
│   ├── rdf_parser.py              # RDF/TTL parsing
│   ├── java_parser.py             # Java AST parsing
│   ├── openapi_parser.py          # Future: OpenAPI parsing
│   └── protobuf_parser.py         # Future: Protobuf parsing
├── templates/                     # Unified template repository
│   ├── cli/
│   │   └── typer_cli.py.j2
│   ├── python/
│   │   ├── client.py.j2
│   │   ├── model.py.j2
│   │   ├── test.py.j2
│   │   └── fastapi_endpoint.py.j2
│   ├── react/
│   │   ├── component.tsx.j2
│   │   └── test.tsx.j2
│   └── typescript/
│       ├── interface.ts.j2
│       └── type.ts.j2
├── validators/                    # Multi-layer validation
│   ├── __init__.py
│   ├── syntax_validator.py        # AST validation
│   ├── type_validator.py          # Mypy integration
│   ├── lint_validator.py          # Ruff integration
│   └── test_validator.py          # Pytest + coverage
├── mappers/                       # Type/schema mapping
│   ├── __init__.py
│   ├── java_to_python.py          # Java type mapper
│   ├── rdf_to_python.py           # RDF type mapper
│   └── openapi_to_fastapi.py      # Future: OpenAPI mapper
└── cli.py                         # Unified CLI entry point
```

---

## Core Abstractions

### 1. Parser Protocol

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

class Parser(Protocol):
    """Parser protocol for different input formats.

    All parsers must implement this protocol to plug into the
    unified code generation framework.

    Examples
    --------
    >>> class JavaParser:
    ...     def parse(self, input_path: Path) -> JavaClass:
    ...         # Parse Java source file
    ...         return JavaClass(...)
    ...
    >>> class RDFParser:
    ...     def parse(self, input_path: Path) -> rdflib.Graph:
    ...         # Parse RDF/TTL file
    ...         return graph
    """

    def parse(self, input_path: Path) -> Any:
        """Parse input file into structured representation.

        Parameters
        ----------
        input_path : Path
            Path to input file to parse

        Returns
        -------
        Any
            Structured representation (JavaClass, Graph, etc.)

        Raises
        ------
        ParseError
            If parsing fails
        FileNotFoundError
            If input file doesn't exist
        """
        ...
```

### 2. Base Generator Class

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class GenerationResult:
    """Result of code generation operation.

    Parameters
    ----------
    output_path : Path
        Path to generated file
    source : str
        Generated source code
    metadata : dict[str, Any]
        Generation metadata (template used, timestamp, etc.)
    validation : ValidationResult | None
        Validation results if validation was performed

    Examples
    --------
    >>> result = GenerationResult(
    ...     output_path=Path("src/client.py"),
    ...     source="# Generated code\\nclass Client: pass",
    ...     metadata={"template": "python_client.py.j2", "timestamp": "2025-11-28"},
    ...     validation=None,
    ... )
    >>> result.output_path
    PosixPath('src/client.py')
    """

    output_path: Path
    source: str
    metadata: dict[str, Any]
    validation: Any | None = None  # ValidationResult from validators

class BaseGenerator(ABC):
    """Abstract base for all code generators.

    All generators must inherit from this class and implement
    the `generate()` method. The base class provides:
    - Template engine integration
    - Validation pipeline
    - Output directory management
    - Auto-formatting

    Parameters
    ----------
    parser : Parser
        Parser for input files
    template_dir : Path
        Directory containing Jinja2 templates
    output_dir : Path
        Root directory for generated code
    validator : CodeValidator | None
        Optional validator for generated code
    auto_format : bool
        Whether to auto-format generated code (default: True)

    Examples
    --------
    >>> class PythonClientGenerator(BaseGenerator):
    ...     def generate(self, input_path: Path) -> GenerationResult:
    ...         parsed = self.parser.parse(input_path)
    ...         code = self.templates.render("client.py.j2", {...})
    ...         return self._write_and_validate(code, output_path)
    """

    def __init__(
        self,
        parser: Parser,
        template_dir: Path,
        output_dir: Path,
        validator: Any | None = None,  # CodeValidator
        auto_format: bool = True,
    ) -> None:
        """Initialize generator with dependencies."""
        self.parser = parser
        self.template_engine = TemplateEngine(template_dir)
        self.output_dir = output_dir
        self.validator = validator
        self.auto_format = auto_format

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self, input_path: Path) -> GenerationResult:
        """Generate code from input file.

        Parameters
        ----------
        input_path : Path
            Path to input file to process

        Returns
        -------
        GenerationResult
            Generation results with metadata

        Raises
        ------
        FileNotFoundError
            If input file doesn't exist
        GenerationError
            If generation fails
        """
        ...

    def validate(self, result: GenerationResult) -> bool:
        """Validate generated code.

        Parameters
        ----------
        result : GenerationResult
            Generation result to validate

        Returns
        -------
        bool
            True if validation passed
        """
        if self.validator is None:
            return True

        validation_result = self.validator.validate_python(result.output_path)
        return validation_result.passed

    def _write_and_validate(
        self, source: str, output_path: Path, metadata: dict[str, Any]
    ) -> GenerationResult:
        """Write generated code and optionally validate.

        Parameters
        ----------
        source : str
            Generated source code
        output_path : Path
            Path to write code to
        metadata : dict[str, Any]
            Generation metadata

        Returns
        -------
        GenerationResult
            Generation results with validation
        """
        # Write source code
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(source)

        # Auto-format if enabled
        if self.auto_format:
            self._auto_format(output_path)

        # Validate if validator configured
        validation = None
        if self.validator is not None:
            validation = self.validator.validate_python(output_path)

        return GenerationResult(
            output_path=output_path,
            source=source,
            metadata=metadata,
            validation=validation,
        )

    def _auto_format(self, file_path: Path) -> None:
        """Auto-format generated code with Ruff."""
        import subprocess

        try:
            subprocess.run(
                ["uv", "run", "ruff", "format", str(file_path)],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except subprocess.SubprocessError:
            pass  # Continue even if formatting fails
```

### 3. Generator Registry

```python
from __future__ import annotations

from typing import Any

class GeneratorRegistry:
    """Registry for all code generators.

    Provides centralized discovery and instantiation of generators.
    Generators self-register via decorator.

    Examples
    --------
    >>> @GeneratorRegistry.register("cli")
    ... class CLIGenerator(BaseGenerator):
    ...     pass
    ...
    >>> generator_cls = GeneratorRegistry.get("cli")
    >>> generator = generator_cls(parser, template_dir, output_dir)
    >>> result = generator.generate(input_path)
    """

    _generators: dict[str, type[Any]] = {}  # type[BaseGenerator]

    @classmethod
    def register(cls, name: str):
        """Decorator to register generator.

        Parameters
        ----------
        name : str
            Generator identifier (e.g., "cli", "java-python")

        Examples
        --------
        >>> @GeneratorRegistry.register("api")
        ... class APIGenerator(BaseGenerator):
        ...     pass
        """
        def decorator(generator_cls: type[Any]) -> type[Any]:
            cls._generators[name] = generator_cls
            return generator_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> type[Any]:  # type[BaseGenerator]
        """Get generator class by name.

        Parameters
        ----------
        name : str
            Generator identifier

        Returns
        -------
        type[BaseGenerator]
            Generator class

        Raises
        ------
        KeyError
            If generator not found
        """
        if name not in cls._generators:
            available = ", ".join(cls._generators.keys())
            raise KeyError(
                f"Generator '{name}' not found. Available: {available}"
            )
        return cls._generators[name]

    @classmethod
    def list_generators(cls) -> list[str]:
        """List all registered generators.

        Returns
        -------
        list[str]
            List of generator identifiers
        """
        return sorted(cls._generators.keys())
```

### 4. Unified Template Engine

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

class TemplateEngine:
    """Unified Jinja2 template rendering engine.

    Provides consistent template rendering across all generators with:
    - Standardized filters (snake_case, camel_case, indent)
    - Consistent whitespace handling (trim_blocks, lstrip_blocks)
    - Safe defaults (undefined raises error in strict mode)
    - Custom filters for code generation

    Parameters
    ----------
    template_dir : Path
        Directory containing Jinja2 templates
    strict : bool
        If True, undefined variables raise errors (default: True)

    Examples
    --------
    >>> engine = TemplateEngine(Path("templates/"))
    >>> code = engine.render(
    ...     "python_client.py.j2",
    ...     {"class_name": "MyClient", "methods": [...]}
    ... )
    """

    def __init__(self, template_dir: Path, strict: bool = True) -> None:
        """Initialize template engine."""
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.template_dir = template_dir

        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,           # Remove first newline after block
            lstrip_blocks=True,         # Remove leading spaces before block
            keep_trailing_newline=True, # Preserve trailing newline
            undefined=self._get_undefined_behavior(strict),
        )

        # Register custom filters
        self._register_filters()

    def _get_undefined_behavior(self, strict: bool) -> Any:
        """Get Jinja2 undefined behavior based on strict mode."""
        from jinja2 import StrictUndefined, Undefined
        return StrictUndefined if strict else Undefined

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters for code generation."""
        self.env.filters["snake_case"] = self._to_snake_case
        self.env.filters["camel_case"] = self._to_camel_case
        self.env.filters["pascal_case"] = self._to_pascal_case
        self.env.filters["indent"] = self._indent
        self.env.filters["python_default"] = self._python_default_value
        self.env.filters["docstring"] = self._format_docstring

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render template with context.

        Parameters
        ----------
        template_name : str
            Template filename (e.g., "client.py.j2")
        context : dict[str, Any]
            Template variables

        Returns
        -------
        str
            Rendered template

        Raises
        ------
        TemplateNotFoundError
            If template doesn't exist
        TemplateRenderError
            If rendering fails
        """
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            raise TemplateNotFoundError(
                f"Template not found: {template_name}"
            ) from e

        try:
            return template.render(**context)
        except Exception as e:
            raise TemplateRenderError(
                f"Failed to render {template_name}: {e}"
            ) from e

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Convert snake_case to camelCase."""
        words = name.split("_")
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def _indent(text: str, spaces: int = 4) -> str:
        """Indent text by specified number of spaces."""
        indent_str = " " * spaces
        lines = text.split("\n")
        return "\n".join(indent_str + line if line.strip() else "" for line in lines)

    @staticmethod
    def _python_default_value(python_type: str) -> str:
        """Get Python default value for a type."""
        defaults = {
            "int": "0",
            "float": "0.0",
            "bool": "False",
            "str": '""',
            "list": "[]",
            "dict": "{}",
        }
        return defaults.get(python_type, "None")

    @staticmethod
    def _format_docstring(text: str, indent: int = 4) -> str:
        """Format text as NumPy-style docstring."""
        indent_str = " " * indent
        lines = text.strip().split("\n")
        return "\n".join(indent_str + line for line in lines)
```

---

## Migration Strategy

### Phase 1: Foundation (Week 1)

**Goal:** Establish unified infrastructure without breaking existing systems.

```bash
# Create base structure
mkdir -p src/kgcl/codegen/{base,generators,parsers,templates,validators,mappers}

# Move existing YAWL generator components
cp scripts/codegen/template_engine.py src/kgcl/codegen/base/
cp scripts/codegen/validator.py src/kgcl/codegen/validators/
cp scripts/codegen/java_parser.py src/kgcl/codegen/parsers/
cp scripts/codegen/type_mapper.py src/kgcl/codegen/mappers/java_to_python.py

# Move templates to unified location
cp -r scripts/codegen/templates/* src/kgcl/codegen/templates/python/
```

**Deliverables:**
- ✅ Base classes implemented (`generator.py`, `parser.py`, `registry.py`)
- ✅ All modules have 100% type coverage
- ✅ All modules have NumPy-style docstrings
- ✅ Tests achieve 80%+ coverage

### Phase 2: YAWL Generator Migration (Week 2)

**Goal:** Migrate YAWL generator to new framework while maintaining functionality.

```python
# src/kgcl/codegen/generators/java_generator.py

from __future__ import annotations

from pathlib import Path

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.registry import GeneratorRegistry
from kgcl.codegen.parsers.java_parser import JavaParser
from kgcl.codegen.mappers.java_to_python import JavaToPythonMapper
from kgcl.codegen.validators.code_validator import CodeValidator

@GeneratorRegistry.register("java-python")
class JavaPythonGenerator(BaseGenerator):
    """Generate Python client from Java service.

    Migrated from scripts/codegen/generator.py
    """

    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
    ) -> None:
        """Initialize Java→Python generator."""
        super().__init__(
            parser=JavaParser(),
            template_dir=template_dir / "python",
            output_dir=output_dir,
            validator=CodeValidator(strict=True),
            auto_format=True,
        )
        self.mapper = JavaToPythonMapper()

    def generate(self, input_path: Path) -> GenerationResult:
        """Generate Python client from Java file."""
        # 1. Parse Java
        java_class = self.parser.parse(input_path)

        # 2. Map to Python
        python_class = self.mapper.map_class(java_class)

        # 3. Render template
        code = self.template_engine.render(
            "client.py.j2",
            {
                "class_name": python_class.name,
                "methods": python_class.methods,
                "imports": python_class.imports,
                "docstring": python_class.docstring,
            },
        )

        # 4. Write and validate
        output_path = self.output_dir / f"{python_class.name.lower()}.py"
        return self._write_and_validate(
            code,
            output_path,
            {"template": "client.py.j2", "source": str(input_path)},
        )
```

**Deliverables:**
- ✅ JavaPythonGenerator registered and functional
- ✅ ReactGenerator registered and functional
- ✅ All existing YAWL generator tests passing
- ✅ No regressions in generated code quality

### Phase 3: Projection Integration (Week 3)

**Goal:** Integrate projection engine while preserving N3 reasoning capabilities.

```python
# src/kgcl/codegen/generators/projection_generator.py

from __future__ import annotations

from pathlib import Path

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.registry import GeneratorRegistry
from kgcl.projection.engine.projection_engine import ProjectionEngine
from kgcl.projection.engine.n3_executor import N3Executor

@GeneratorRegistry.register("projection")
class ProjectionGenerator(BaseGenerator):
    """Multi-language code generation with N3 reasoning.

    Integrates existing projection engine while conforming to
    unified generator interface.
    """

    def __init__(
        self,
        projection_engine: ProjectionEngine,
        output_dir: Path,
    ) -> None:
        """Initialize projection generator."""
        # ProjectionGenerator doesn't use standard parser
        # It uses ProjectionEngine's internal pipeline
        self.projection_engine = projection_engine
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, template_name: str, params: dict) -> GenerationResult:
        """Generate code via projection engine.

        Parameters
        ----------
        template_name : str
            Projection template identifier (e.g., "cli", "api")
        params : dict
            Template parameters

        Returns
        -------
        GenerationResult
            Projection results
        """
        # Delegate to projection engine
        proj_result = self.projection_engine.render(template_name, params)

        # Write output
        output_path = self.output_dir / f"{template_name}_output"
        output_path.write_text(proj_result.content)

        return GenerationResult(
            output_path=output_path,
            source=proj_result.content,
            metadata={
                "template": template_name,
                "projection_id": proj_result.id,
                "timestamp": proj_result.timestamp,
            },
            validation=None,  # Projection engine has own validation
        )
```

**Deliverables:**
- ✅ ProjectionGenerator registered
- ✅ All projection templates accessible via unified registry
- ✅ N3 reasoning preserved
- ✅ Existing projection tests passing

### Phase 4: CLI Generator (Week 4)

**Goal:** Implement missing CLI generator using unified framework.

```python
# src/kgcl/codegen/generators/cli_generator.py

from __future__ import annotations

from pathlib import Path

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.base.registry import GeneratorRegistry
from kgcl.codegen.parsers.rdf_parser import RDFParser
from kgcl.codegen.mappers.rdf_to_python import RDFToPythonMapper

@GeneratorRegistry.register("cli")
class CLIGenerator(BaseGenerator):
    """Generate Typer CLI from RDF/TTL specifications.

    Input: .kgc/cli.ttl
    Output: Python CLI with Typer
    """

    def __init__(
        self,
        template_dir: Path,
        output_dir: Path,
    ) -> None:
        """Initialize CLI generator."""
        super().__init__(
            parser=RDFParser(),
            template_dir=template_dir / "cli",
            output_dir=output_dir,
            validator=CodeValidator(strict=True),
            auto_format=True,
        )
        self.mapper = RDFToPythonMapper()

    def generate(self, input_path: Path) -> GenerationResult:
        """Generate CLI from RDF/TTL file."""
        # 1. Parse RDF
        graph = self.parser.parse(input_path)

        # 2. Extract CLI metadata
        cli_spec = self.mapper.extract_cli_spec(graph)

        # 3. Render template
        code = self.template_engine.render(
            "typer_cli.py.j2",
            {
                "commands": cli_spec.commands,
                "app_name": cli_spec.app_name,
                "description": cli_spec.description,
            },
        )

        # 4. Write and validate
        output_path = self.output_dir / "cli.py"
        return self._write_and_validate(
            code,
            output_path,
            {"template": "typer_cli.py.j2", "source": str(input_path)},
        )
```

**Deliverables:**
- ✅ CLIGenerator implemented and tested
- ✅ RDFParser handles TTL input
- ✅ Template generates valid Typer CLI
- ✅ Integration with .kgc/cli.ttl

### Phase 5: Unified CLI (Week 5)

**Goal:** Single CLI entry point for all generators.

```python
# src/kgcl/codegen/cli.py

"""Unified CLI for KGCL code generation.

Examples
--------
# Generate Python client from Java
kgcl codegen java-python --input vendors/yawlui-v5.2/YawlService.java --output src/kgcl/yawl

# Generate CLI from RDF
kgcl codegen cli --input .kgc/cli.ttl --output src/kgcl/cli

# Generate via projection
kgcl codegen projection --template api --output src/kgcl/api

# List available generators
kgcl codegen --list
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from kgcl.codegen.base.registry import GeneratorRegistry

app = typer.Typer()

@app.command()
def generate(
    generator: str = typer.Argument(..., help="Generator name (java-python, cli, projection)"),
    input_path: Path = typer.Option(None, help="Input file path"),
    template: str = typer.Option(None, help="Template name (for projection)"),
    output_dir: Path = typer.Option(Path("output"), help="Output directory"),
    validate: bool = typer.Option(True, help="Validate generated code"),
    auto_fix: bool = typer.Option(True, help="Auto-fix validation errors"),
) -> None:
    """Generate code using specified generator."""
    try:
        generator_cls = GeneratorRegistry.get(generator)
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    # Instantiate generator
    gen = generator_cls(
        template_dir=Path("src/kgcl/codegen/templates"),
        output_dir=output_dir,
    )

    # Generate code
    if generator == "projection":
        result = gen.generate(template, {})
    else:
        if input_path is None:
            typer.echo("Error: --input-path required", err=True)
            raise typer.Exit(1)
        result = gen.generate(input_path)

    # Report results
    typer.echo(f"✓ Generated: {result.output_path}")

    if result.validation and not result.validation.passed:
        typer.echo("✗ Validation failed:", err=True)
        for error in result.validation.errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(1)

@app.command()
def list_generators() -> None:
    """List all available generators."""
    generators = GeneratorRegistry.list_generators()
    typer.echo("Available generators:")
    for gen in generators:
        typer.echo(f"  - {gen}")

if __name__ == "__main__":
    app()
```

**Deliverables:**
- ✅ Unified CLI (`kgcl codegen`)
- ✅ All generators accessible via CLI
- ✅ Comprehensive help documentation
- ✅ Integration with existing `poe` tasks

---

## Benefits

### 1. Code Reuse (DRY Principle)

**Before (Fragmented):**
- 3 separate Jinja2 implementations
- Duplicate validation logic
- Scattered type mappers

**After (Unified):**
- Single `TemplateEngine` with consistent filters
- Single `CodeValidator` enforcing all standards
- Shared `TypeMapper` base class

**Impact:** ~40% reduction in code duplication

### 2. Consistent Quality

**Enforced Standards:**
- ✅ All generators use same validation pipeline
- ✅ Auto-formatting with Ruff
- ✅ 100% type coverage enforced
- ✅ 80%+ test coverage required

**Result:** Zero-defect code generation (Lean Six Sigma)

### 3. Extensibility

**Adding New Generator:**

```python
# Before: Implement from scratch (100+ LOC)
# After: Inherit from BaseGenerator (20 LOC)

@GeneratorRegistry.register("openapi")
class OpenAPIGenerator(BaseGenerator):
    def generate(self, input_path: Path) -> GenerationResult:
        spec = self.parser.parse(input_path)  # OpenAPIParser
        code = self.template_engine.render("fastapi.py.j2", {...})
        return self._write_and_validate(code, output_path, {})
```

**Impact:** 5x faster generator development

### 4. Discoverability

**Unified Registry:**
```bash
$ kgcl codegen --list
Available generators:
  - cli           (RDF→Typer CLI)
  - java-python   (Java→Python client)
  - java-react    (Java→React component)
  - projection    (RDF→Multi-language with N3)
  - openapi       (OpenAPI→FastAPI)
```

**Impact:** Single source of truth for all generators

### 5. Testing

**Before:**
- YAWL: Comprehensive validator, no integration tests
- Projection: Integration tests, no validation
- CLI: Missing entirely

**After:**
- Unified test suite for all generators
- Shared fixtures and test utilities
- Consistent coverage requirements

---

## Quality Gates

### Pre-Commit Enforcement

```toml
# pyproject.toml

[tool.poe.tasks]
codegen-validate = "uv run python -m kgcl.codegen.cli validate"
codegen-test = "uv run pytest tests/codegen/ -v"

[tool.poe.tasks.verify]
sequence = [
    "format",
    "lint",
    "type-check",
    "codegen-validate",
    "codegen-test",
    "test"
]
```

### Validation Pipeline

```python
# Every generated file must pass:
1. Syntax validation (ast.parse)
2. Type checking (mypy --strict)
3. Lint checking (400+ Ruff rules)
4. Import validation (no circular deps)
5. Test coverage (80%+ minimum)
```

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Java→Python generation | <5s per file | End-to-end including validation |
| RDF→CLI generation | <3s | Single CLI file |
| Projection rendering | <10s | With N3 reasoning |
| Validation pipeline | <2s per file | All checks combined |
| Template hot reload | <100ms | Development mode |

---

## Risks & Mitigations

### Risk 1: Breaking Existing Code

**Mitigation:**
- ✅ Parallel implementation (keep old generators during migration)
- ✅ Comprehensive regression tests
- ✅ Gradual migration (one generator per week)
- ✅ Feature parity verification

### Risk 2: Performance Regression

**Mitigation:**
- ✅ Benchmark current generators before migration
- ✅ Performance tests in CI/CD
- ✅ SLO monitoring (p99 latency)
- ✅ Rollback plan if targets missed

### Risk 3: N3 Reasoning Complexity

**Mitigation:**
- ✅ Keep ProjectionEngine's N3Executor intact
- ✅ Thin wrapper pattern (don't reimpl
ement)
- ✅ Preserve all existing tests
- ✅ Add integration tests for N3 workflows

### Risk 4: Template Compatibility

**Mitigation:**
- ✅ Standardize on `.j2` extension (migrate `.jinja2` → `.j2`)
- ✅ Template validation in CI/CD
- ✅ Version templates with semantic versioning
- ✅ Template upgrade guide

---

## Success Metrics

### Code Quality
- ✅ 100% type coverage (mypy --strict)
- ✅ Zero Ruff errors/warnings
- ✅ 80%+ test coverage on all modules
- ✅ All pre-commit hooks passing

### Developer Experience
- ✅ Single CLI for all generators
- ✅ <5 LOC to add new generator
- ✅ Comprehensive documentation
- ✅ Examples for all generators

### Performance
- ✅ All SLOs met (see Performance Targets)
- ✅ <5s end-to-end generation
- ✅ <2s validation pipeline

### Production Readiness
- ✅ Zero defects in generated code
- ✅ Dogfooding: KGCL CLI generated by CLI generator
- ✅ All generators validated in production

---

## References

### Internal Documents
- `CLAUDE.md` - Project standards and quality requirements
- `docs/BUILD_SYSTEM_SUMMARY.md` - Cargo-make build system
- `docs/architecture/ADR-001-HYBRID-ENGINE-ARCHITECTURE.md` - Hybrid engine design
- `scripts/codegen/README.md` - YAWL generator documentation

### Existing Code
- `scripts/codegen/generator.py` - YAWL generator implementation
- `scripts/codegen/validator.py` - Comprehensive validation system
- `src/kgcl/projection/engine/projection_engine.py` - Projection engine
- `.kgc/cli.ttl` - CLI specification (RDF)

### External References
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Mypy Strict Mode](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Lean Six Sigma Quality](https://en.wikipedia.org/wiki/Six_Sigma)

---

## Appendices

### A. Template Standard

All templates must:
- Use `.j2` extension
- Include YAML frontmatter with metadata
- Document all template variables
- Include usage examples
- Pass template validation

**Example:**
```jinja2
{# python_client.py.j2
---
name: Python Client Generator
version: 1.0.0
language: python
framework: httpx
input: JavaClass
variables:
  - class_name: str (Python class name)
  - methods: list[PythonMethod] (Client methods)
  - imports: list[str] (Required imports)
---

Generates Python HTTP client from Java service definition.
#}
from __future__ import annotations

{% for import_stmt in imports %}
{{ import_stmt }}
{% endfor %}

class {{ class_name }}:
    """{{ docstring }}"""

    {% for method in methods %}
    def {{ method.name }}(self{% for param_name, param_type in method.parameters %}, {{ param_name }}: {{ param_type }}{% endfor %}) -> {{ method.return_type }}:
        """{{ method.docstring | indent(8) }}"""
        # Implementation generated from Java method
        pass
    {% endfor %}
```

### B. Validation Report Format

```
================================================================================
CODE VALIDATION REPORT
================================================================================
Total Files: 12
Passed: 11 ✓
Failed: 1 ✗

FAILED FILES:
--------------------------------------------------------------------------------

❌ src/kgcl/yawl/client.py
  ERRORS:
    - Line 45: Missing return type annotation [no-untyped-def]
    - Line 52: Import 'requests' not found [import-not-found]
  WARNINGS:
    - Line 23: Line too long (121 > 120) [E501]

================================================================================
✗ VALIDATION FAILED - FIX ERRORS BEFORE COMMITTING
================================================================================
```

### C. Generator Development Checklist

When implementing a new generator:

- [ ] Inherit from `BaseGenerator`
- [ ] Implement `generate()` method
- [ ] Register via `@GeneratorRegistry.register()`
- [ ] Create parser class implementing `Parser` protocol
- [ ] Create type mapper if needed
- [ ] Add templates to `src/kgcl/codegen/templates/`
- [ ] Write comprehensive tests (80%+ coverage)
- [ ] Add NumPy-style docstrings to all public methods
- [ ] Ensure 100% type coverage
- [ ] Add CLI documentation
- [ ] Create usage examples
- [ ] Run `poe verify` - all checks must pass

---

**Status:** Awaiting approval and implementation prioritization.
