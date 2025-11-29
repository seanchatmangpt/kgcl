# Semantic Code Generator - C4 Architecture Diagrams

**System**: YAWL Java → Python/React Migration
**Version**: 1.0
**Date**: 2025-11-28

---

## C4 Model Overview

The C4 model provides hierarchical views of the system architecture:
- **Level 1 (Context)**: System in its environment
- **Level 2 (Container)**: High-level technical building blocks
- **Level 3 (Component)**: Components within containers
- **Level 4 (Code)**: Implementation details (class diagrams)

---

## Level 1: System Context Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        SYSTEM CONTEXT                              │
└────────────────────────────────────────────────────────────────────┘

┌─────────────┐                                    ┌─────────────┐
│             │                                    │             │
│  Developer  │◄──────────────────────────────────►│  CI/CD      │
│             │   Triggers generation              │  Pipeline   │
│             │   Reviews output                   │  (GitHub    │
└──────┬──────┘                                    │  Actions)   │
       │                                            └──────┬──────┘
       │                                                   │
       │ Runs codegen                                     │ Validates
       │ Reviews reports                                  │ output
       │                                                   │
       ▼                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│              SEMANTIC CODE GENERATOR SYSTEM                     │
│                                                                 │
│  Converts 122 Java files → Python/React with 100% types        │
│  and 80%+ test coverage                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
       │                           │                       │
       │ Reads                     │ Generates             │ Writes
       │                           │                       │
       ▼                           ▼                       ▼
┌─────────────┐          ┌─────────────┐         ┌─────────────┐
│             │          │             │         │             │
│  Java       │          │  Python     │         │  React      │
│  Source     │          │  Backend    │         │  Frontend   │
│  Files      │          │  (FastAPI)  │         │  (TypeScript│
│  (122)      │          │             │         │             │
└─────────────┘          └─────────────┘         └─────────────┘

┌─────────────┐
│             │
│  Quality    │
│  Gates      │
│  (mypy,     │
│  ruff,      │
│  pytest)    │
│             │
└──────┬──────┘
       │
       │ Validates
       │ all output
       │
       ▼
┌─────────────────────────────────────┐
│  Rollback on failure               │
│  Commit on success                 │
└─────────────────────────────────────┘
```

**Key Relationships**:
- **Developer** initiates generation, reviews output
- **CI/CD Pipeline** validates all changes automatically
- **Codegen System** reads Java, writes Python/React
- **Quality Gates** enforce 100% types, 80%+ coverage

---

## Level 2: Container Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│             SEMANTIC CODE GENERATOR (Containers)                   │
└────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR CONTAINER (Python)                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Batch Manager│  │ Dependency   │  │ Rollback     │           │
│  │              │→ │ Resolver     │→ │ Manager      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ Coordinates
             │ processing
             ▼
┌───────────────────────────────────────────────────────────────────┐
│  PARSER CONTAINER (Python + javalang)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Java AST     │→ │ Semantic     │→ │ Metadata     │           │
│  │ Parser       │  │ Analyzer     │  │ Extractor    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ Produces metadata
             │ (JSON/dict)
             ▼
┌───────────────────────────────────────────────────────────────────┐
│  MAPPER CONTAINER (Python)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Type Mapper  │→ │ Pattern      │→ │ API/UI       │           │
│  │ (Java→Py/TS) │  │ Translator   │  │ Splitter     │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ Produces backend
             │ + frontend metadata
             ▼
┌───────────────────────────────────────────────────────────────────┐
│  TEMPLATE CONTAINER (Jinja2)                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Python       │  │ TypeScript   │  │ Test         │           │
│  │ Generator    │  │ Generator    │  │ Generator    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ Writes files
             │
             ▼
┌───────────────────────────────────────────────────────────────────┐
│  VALIDATION CONTAINER (Python + Node.js)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Type Check   │→ │ Lint         │→ │ Test         │           │
│  │ (mypy/tsc)   │  │ (ruff/eslint)│  │ Execution    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ Pass/Fail
             │
             ▼
┌───────────────────────────────────────────────────────────────────┐
│  STORAGE CONTAINER (File System)                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Python       │  │ React        │  │ Test Files   │           │
│  │ Backend      │  │ Frontend     │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

**Container Descriptions**:

| Container | Technology | Responsibility |
|-----------|-----------|----------------|
| **Orchestrator** | Python (asyncio) | Batch processing, dependency resolution, rollback |
| **Parser** | Python + javalang | Java AST parsing, semantic extraction |
| **Mapper** | Python | Type mapping, pattern translation, API/UI split |
| **Template** | Python + Jinja2 | Code generation from templates |
| **Validation** | Python + Node.js | Quality gates (type check, lint, test) |
| **Storage** | File System | Generated Python/React/Test files |

---

## Level 3: Component Diagram - Parser Container

```
┌────────────────────────────────────────────────────────────────────┐
│                    PARSER CONTAINER                                │
└────────────────────────────────────────────────────────────────────┘

                  ┌────────────────┐
                  │ Java Source    │
                  │ Files (.java)  │
                  └────────┬───────┘
                           │
                           │ reads
                           ▼
          ┌─────────────────────────────────┐
          │  JavaFileReader Component       │
          │  - validate_file()               │
          │  - read_source()                 │
          └────────────┬────────────────────┘
                       │
                       │ source text
                       ▼
          ┌─────────────────────────────────┐
          │  ASTParser Component             │
          │  - parse_java(source: str)       │
          │  - handle_syntax_errors()        │
          │  Uses: javalang library          │
          └────────────┬────────────────────┘
                       │
                       │ AST tree
                       ▼
          ┌─────────────────────────────────┐
          │  SemanticAnalyzer Component      │
          │  - extract_classes()             │
          │  - extract_methods()             │
          │  - extract_fields()              │
          │  - resolve_types()               │
          │  - resolve_inheritance()         │
          └────────────┬────────────────────┘
                       │
                       │ semantic data
                       ▼
          ┌─────────────────────────────────┐
          │  PatternDetector Component       │
          │  - detect_view_pattern()         │
          │  - detect_service_pattern()      │
          │  - detect_model_pattern()        │
          │  - categorize_class()            │
          └────────────┬────────────────────┘
                       │
                       │ categorized
                       ▼
          ┌─────────────────────────────────┐
          │  MetadataExtractor Component     │
          │  - build_class_metadata()        │
          │  - build_method_metadata()       │
          │  - build_field_metadata()        │
          │  - serialize_to_dict()           │
          └────────────┬────────────────────┘
                       │
                       │ metadata (dict)
                       ▼
                  ┌────────────────┐
                  │ JavaClass      │
                  │ Metadata       │
                  │ (dataclass)    │
                  └────────────────┘
```

**Component Interfaces**:

```python
# Parser Container Components

class JavaFileReader:
    """Read and validate Java source files."""
    def validate_file(self, path: Path) -> ValidationResult: ...
    def read_source(self, path: Path) -> str: ...

class ASTParser:
    """Parse Java source to AST using javalang."""
    def parse_java(self, source: str) -> javalang.tree.CompilationUnit: ...
    def handle_syntax_errors(self, error: Exception) -> None: ...

class SemanticAnalyzer:
    """Extract semantic information from AST."""
    def extract_classes(self, ast: CompilationUnit) -> list[ClassDeclaration]: ...
    def extract_methods(self, cls: ClassDeclaration) -> list[MethodDeclaration]: ...
    def extract_fields(self, cls: ClassDeclaration) -> list[FieldDeclaration]: ...
    def resolve_types(self, type_ref: str) -> str: ...
    def resolve_inheritance(self, cls: ClassDeclaration) -> list[str]: ...

class PatternDetector:
    """Detect Java class patterns (View, Service, Model, etc.)."""
    def detect_view_pattern(self, cls: ClassDeclaration) -> bool: ...
    def detect_service_pattern(self, cls: ClassDeclaration) -> bool: ...
    def detect_model_pattern(self, cls: ClassDeclaration) -> bool: ...
    def categorize_class(self, cls: ClassDeclaration) -> ClassCategory: ...

class MetadataExtractor:
    """Build metadata dataclasses from semantic data."""
    def build_class_metadata(self, cls: ClassDeclaration) -> JavaClass: ...
    def build_method_metadata(self, method: MethodDeclaration) -> JavaMethod: ...
    def build_field_metadata(self, field: FieldDeclaration) -> JavaField: ...
    def serialize_to_dict(self, metadata: JavaClass) -> dict[str, Any]: ...
```

---

## Level 3: Component Diagram - Template Container

```
┌────────────────────────────────────────────────────────────────────┐
│                   TEMPLATE CONTAINER                               │
└────────────────────────────────────────────────────────────────────┘

          ┌────────────────┐         ┌────────────────┐
          │ Backend        │         │ Frontend       │
          │ Metadata       │         │ Metadata       │
          └────────┬───────┘         └────────┬───────┘
                   │                          │
                   │                          │
       ┌───────────┴──────────┐   ┌──────────┴───────────┐
       │                      │   │                      │
       ▼                      ▼   ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Python       │      │ Test         │      │ TypeScript   │
│ Generator    │      │ Generator    │      │ Generator    │
│              │      │              │      │              │
│ Uses:        │      │ Uses:        │      │ Uses:        │
│ - Jinja2     │      │ - Jinja2     │      │ - Jinja2     │
│ - Templates: │      │ - Templates: │      │ - Templates: │
│   * model.j2 │      │   * test.j2  │      │   * comp.j2  │
│   * route.j2 │      │              │      │   * hook.j2  │
│   * service.j2│      │              │      │   * types.j2 │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       │ renders             │ renders             │ renders
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Python Files │      │ Test Files   │      │ TS/TSX Files │
│ .py          │      │ test_*.py    │      │ .ts, .tsx    │
│              │      │ *.test.tsx   │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
```

**Component Details**:

```python
# Template Container Components

@dataclass(frozen=True)
class TemplateContext:
    """Context data for template rendering."""
    metadata: JavaClass | BackendMetadata | FrontendMetadata
    output_path: Path
    template_name: str
    variables: dict[str, Any]

class PythonGenerator:
    """Generate Python backend files from templates."""
    def __init__(self, template_dir: Path) -> None: ...
    def generate_model(self, metadata: BackendMetadata) -> Path: ...
    def generate_route(self, metadata: BackendMetadata) -> Path: ...
    def generate_service(self, metadata: BackendMetadata) -> Path: ...
    def render_template(self, context: TemplateContext) -> str: ...

class TestGenerator:
    """Generate test files from templates."""
    def generate_python_test(self, metadata: BackendMetadata) -> Path: ...
    def generate_typescript_test(self, metadata: FrontendMetadata) -> Path: ...

class TypeScriptGenerator:
    """Generate React/TypeScript files from templates."""
    def generate_component(self, metadata: FrontendMetadata) -> Path: ...
    def generate_hook(self, metadata: FrontendMetadata) -> Path: ...
    def generate_types(self, metadata: FrontendMetadata) -> Path: ...
```

---

## Level 3: Component Diagram - Validation Container

```
┌────────────────────────────────────────────────────────────────────┐
│                  VALIDATION CONTAINER                              │
└────────────────────────────────────────────────────────────────────┘

                   ┌────────────────┐
                   │ Generated      │
                   │ Files          │
                   └────────┬───────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌──────────┐     ┌──────────┐    ┌──────────┐
    │ Python   │     │ TypeScript│    │ Test     │
    │ Files    │     │ Files     │    │ Files    │
    └─────┬────┘     └─────┬─────┘    └─────┬────┘
          │                │                 │
          │                │                 │
          ▼                ▼                 ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ TypeChecker  │  │ TypeChecker  │  │ TestRunner   │
  │ (mypy)       │  │ (tsc)        │  │ (pytest)     │
  │              │  │              │  │ (vitest)     │
  │ - strict mode│  │ - strict mode│  │              │
  │ - 100% types │  │ - 100% types │  │ - 80%+ cov   │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │
         │                 │                  │
         ▼                 ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Linter       │  │ Linter       │  │ LieDetector  │
  │ (ruff)       │  │ (eslint)     │  │              │
  │              │  │              │  │ - Find TODO  │
  │ - 400+ rules │  │ - Airbnb     │  │ - Find FIXME │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │
         └─────────────────┴──────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ QualityGate    │
                  │ Aggregator     │
                  │                │
                  │ - Collect      │
                  │   results      │
                  │ - Pass/Fail    │
                  └────────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌─────────────┐      ┌─────────────┐
         │ PASS        │      │ FAIL        │
         │             │      │             │
         │ → Commit    │      │ → Rollback  │
         └─────────────┘      └─────────────┘
```

**Validation Flow**:

```python
@dataclass(frozen=True)
class QualityGateResult:
    """Result of a single quality gate."""
    name: str
    passed: bool
    output: str
    duration_ms: int
    failures: list[str]

class QualityGateRunner:
    """Run all quality gates on generated code."""

    async def run_all_gates(
        self,
        python_files: list[Path],
        typescript_files: list[Path]
    ) -> list[QualityGateResult]:
        """Run all quality gates in parallel."""
        tasks = [
            self.run_type_check_python(python_files),
            self.run_type_check_typescript(typescript_files),
            self.run_lint_python(python_files),
            self.run_lint_typescript(typescript_files),
            self.run_tests_python(),
            self.run_tests_typescript(),
            self.run_lie_detector(python_files + typescript_files)
        ]
        return await asyncio.gather(*tasks)

    async def run_type_check_python(self, files: list[Path]) -> QualityGateResult:
        """Run mypy in strict mode."""
        result = await self._run_command(["poe", "type-check"])
        return QualityGateResult(
            name="type-check-python",
            passed=result.returncode == 0,
            output=result.stdout,
            duration_ms=result.duration,
            failures=self._parse_mypy_errors(result.stdout)
        )

    # ... other gate runners ...
```

---

## Level 4: Code Diagram - Type Mapping

```
┌────────────────────────────────────────────────────────────────────┐
│                     TYPE MAPPING (Code Level)                      │
└────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  TypeMapper Class                                                │
├──────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│    - type_registry: dict[str, TypeMapping]                      │
│    - generic_handlers: dict[str, GenericHandler]                │
│    - custom_types: dict[str, CustomTypeMapping]                 │
├──────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│    + map_java_to_python(java_type: str) -> str                  │
│    + map_java_to_typescript(java_type: str) -> str              │
│    + register_custom_mapping(java: str, py: str, ts: str)       │
│    + handle_generics(java_type: str) -> GenericTypeMapping      │
│    + resolve_imports(python_type: str) -> list[str]             │
└──────────────────────────────────────────────────────────────────┘
                          │
                          │ uses
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  TypeMapping (dataclass)                                         │
├──────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│    + java_type: str                                             │
│    + python_type: str                                           │
│    + typescript_type: str                                       │
│    + python_imports: list[str]                                  │
│    + typescript_imports: list[str]                              │
│    + is_generic: bool                                           │
└──────────────────────────────────────────────────────────────────┘
                          │
                          │ extends
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  GenericTypeMapping (dataclass)                                  │
├──────────────────────────────────────────────────────────────────┤
│  Attributes:                                                     │
│    + base_type: str                                             │
│    + type_parameters: list[str]                                 │
│    + resolved_python: str                                       │
│    + resolved_typescript: str                                   │
├──────────────────────────────────────────────────────────────────┤
│  Methods:                                                        │
│    + map_parameters() -> None                                   │
│    + build_python_annotation() -> str                           │
│    + build_typescript_annotation() -> str                       │
└──────────────────────────────────────────────────────────────────┘
```

**Example Implementation**:

```python
@dataclass(frozen=True)
class TypeMapping:
    """Mapping from Java type to Python/TypeScript."""
    java_type: str
    python_type: str
    typescript_type: str
    python_imports: list[str] = field(default_factory=list)
    typescript_imports: list[str] = field(default_factory=list)
    is_generic: bool = False

class TypeMapper:
    """Map Java types to Python and TypeScript."""

    # Built-in type mappings
    TYPE_REGISTRY: dict[str, TypeMapping] = {
        "String": TypeMapping("String", "str", "string"),
        "int": TypeMapping("int", "int", "number"),
        "Integer": TypeMapping("Integer", "int", "number"),
        "long": TypeMapping("long", "int", "number"),
        "Long": TypeMapping("Long", "int", "number"),
        "boolean": TypeMapping("boolean", "bool", "boolean"),
        "Boolean": TypeMapping("Boolean", "bool", "boolean"),
        "LocalDateTime": TypeMapping(
            "LocalDateTime",
            "datetime",
            "string",
            python_imports=["from datetime import datetime"],
            typescript_imports=[]
        ),
        # ... more mappings
    }

    def map_java_to_python(self, java_type: str) -> str:
        """Map Java type to Python type annotation."""
        # Handle generics: List<String> → list[str]
        if "<" in java_type:
            return self._map_generic_python(java_type)

        # Handle arrays: String[] → list[str]
        if java_type.endswith("[]"):
            base = java_type[:-2]
            mapped = self.map_java_to_python(base)
            return f"list[{mapped}]"

        # Look up in registry
        mapping = self.TYPE_REGISTRY.get(java_type)
        if mapping:
            return mapping.python_type

        # Custom class → assume Pydantic model
        return java_type  # Will be generated as Pydantic model

    def _map_generic_python(self, java_type: str) -> str:
        """Map Java generic to Python generic."""
        # List<String> → list[str]
        # Map<String, Integer> → dict[str, int]
        # Optional<Long> → int | None

        base, params = self._parse_generic(java_type)

        if base == "List":
            return f"list[{self.map_java_to_python(params[0])}]"
        elif base == "Map":
            key = self.map_java_to_python(params[0])
            value = self.map_java_to_python(params[1])
            return f"dict[{key}, {value}]"
        elif base == "Optional":
            return f"{self.map_java_to_python(params[0])} | None"
        else:
            # Generic class: MyClass<T> → MyClass[T]
            mapped_params = [self.map_java_to_python(p) for p in params]
            return f"{base}[{', '.join(mapped_params)}]"
```

---

## Sequence Diagrams

### Sequence 1: Single File Generation

```
Developer      Orchestrator    Parser       Mapper      Template    Validator
    │                │            │            │            │            │
    │ generate()     │            │            │            │            │
    ├───────────────►│            │            │            │            │
    │                │ parse()    │            │            │            │
    │                ├───────────►│            │            │            │
    │                │            │ (AST)      │            │            │
    │                │ metadata   │            │            │            │
    │                │◄───────────┤            │            │            │
    │                │            │            │            │            │
    │                │ map_types()│            │            │            │
    │                ├────────────────────────►│            │            │
    │                │            │ (metadata) │            │            │
    │                │◄────────────────────────┤            │            │
    │                │            │            │            │            │
    │                │ render()   │            │            │            │
    │                ├────────────────────────────────────►│            │
    │                │            │            │ (files)    │            │
    │                │◄────────────────────────────────────┤            │
    │                │            │            │            │            │
    │                │ validate() │            │            │            │
    │                ├────────────────────────────────────────────────►│
    │                │            │            │            │  (PASS)   │
    │                │◄────────────────────────────────────────────────┤
    │                │            │            │            │            │
    │ success        │            │            │            │            │
    │◄───────────────┤            │            │            │            │
    │                │            │            │            │            │
```

### Sequence 2: Validation Failure & Rollback

```
Orchestrator    Template    Validator    Rollback
    │                │            │            │
    │ render()       │            │            │
    ├───────────────►│            │            │
    │                │ (files)    │            │
    │◄───────────────┤            │            │
    │                │            │            │
    │ validate()     │            │            │
    ├────────────────────────────►│            │
    │                │            │            │
    │                │  type_check() (FAIL)    │
    │                │◄───────────┤            │
    │                │            │            │
    │◄────────────────────────────┤            │
    │ (FAIL)         │            │            │
    │                │            │            │
    │ rollback()     │            │            │
    ├────────────────────────────────────────►│
    │                │            │            │
    │                │            │ delete_files()
    │                │            │ restore_backup()
    │                │            │            │
    │◄────────────────────────────────────────┤
    │ (rolled back)  │            │            │
```

---

## Deployment Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     DEVELOPER MACHINE                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Docker Container (optional)                             │    │
│  │  ┌────────────────────────────────────────────────┐      │    │
│  │  │  Codegen Runtime                                │      │    │
│  │  │  - Python 3.13                                  │      │    │
│  │  │  - Node.js 20                                   │      │    │
│  │  │  - uv package manager                           │      │    │
│  │  │  - npm                                          │      │    │
│  │  │                                                  │      │    │
│  │  │  Installed Tools:                               │      │    │
│  │  │  - javalang                                     │      │    │
│  │  │  - jinja2                                       │      │    │
│  │  │  - pydantic                                     │      │    │
│  │  │  - mypy                                         │      │    │
│  │  │  - ruff                                         │      │    │
│  │  │  - pytest                                       │      │    │
│  │  │  - typescript                                   │      │    │
│  │  │  - eslint                                       │      │    │
│  │  │  - vitest                                       │      │    │
│  │  └────────────────────────────────────────────────┘      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  File System                                             │    │
│  │  /Users/sac/dev/kgcl/                                    │    │
│  │  ├── vendors/yawlui-v5.2/src/main/java/  (INPUT)        │    │
│  │  ├── src/kgcl/yawl_ui/                   (OUTPUT)       │    │
│  │  ├── frontend/src/                       (OUTPUT)       │    │
│  │  ├── tests/yawl_ui/                      (OUTPUT)       │    │
│  │  └── reports/codegen/                    (LOGS)         │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                     CI/CD (GitHub Actions)                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Python Validation Job                                   │    │
│  │  - Python 3.13                                           │    │
│  │  - uv sync                                               │    │
│  │  - poe verify (format, lint, type-check, test)          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  TypeScript Validation Job                               │    │
│  │  - Node.js 20                                            │    │
│  │  - npm ci                                                │    │
│  │  - npm run verify (type-check, lint, test)              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Integration Test Job                                    │    │
│  │  - Python + Node.js                                      │    │
│  │  - Playwright E2E tests                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Summary

This C4 architecture provides:

1. **Context Diagram**: System boundaries and external actors
2. **Container Diagram**: High-level technical building blocks
3. **Component Diagrams**: Internal structure of Parser, Template, and Validation containers
4. **Code Diagram**: Implementation details of Type Mapping
5. **Sequence Diagrams**: Runtime behavior (generation flow, rollback flow)
6. **Deployment Diagram**: Physical deployment on developer machine and CI/CD

**Key Architectural Principles**:
- ✅ **Separation of Concerns**: Parse → Map → Template → Validate
- ✅ **Fail-Safe**: Quality gates enforce 100% types, 80%+ coverage
- ✅ **Rollback Safety**: Automatic rollback on any failure
- ✅ **Incremental Processing**: Package-by-package with dependencies
- ✅ **Parallel Execution**: Within-package parallel file processing
- ✅ **Type Safety**: 100% coverage in Python and TypeScript

---

**Next Steps**:
1. Implement Parser Container (Week 1)
2. Implement Mapper Container (Week 1)
3. Implement Template Container (Week 1)
4. Implement Validation Container (Week 1)
5. Implement Orchestrator Container (Week 1)
6. Begin Tier 1 package generation (Week 2)

**Reference**: See `SEMANTIC_CODEGEN_ARCHITECTURE.md` for detailed specifications.
