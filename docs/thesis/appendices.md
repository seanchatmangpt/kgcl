# Appendices

[← Previous: Chapter 7](./chapter-7-future-work.md) | [Back to Contents](./README.md)

---

## Appendix A: Complete Delta Detection Schema

The Delta Detector system uses a comprehensive data model to represent all types of deltas. This schema is implemented in [`models.py`](../../src/kgcl/yawl_ontology/models.py).

### Data Classes

```python
from dataclasses import dataclass
from enum import Enum, auto

class DeltaSeverity(Enum):
    """Severity levels for deltas."""
    INFO = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass(frozen=True)
class ClassDelta:
    """Represents a missing or mismatched class."""
    java_class: str
    java_package: str
    python_class: str | None
    python_package: str | None
    severity: DeltaSeverity
    reason: str

@dataclass(frozen=True)
class MethodDelta:
    """Represents a missing or mismatched method."""
    java_class: str
    java_method: str
    java_signature: str
    python_method: str | None
    severity: DeltaSeverity
    reason: str

@dataclass(frozen=True)
class FingerprintDelta:
    """Represents a semantic difference detected via AST fingerprinting."""
    java_class: str
    java_method: str
    java_fingerprint: str
    python_fingerprint: str
    similarity_score: float  # 0.0 to 1.0
    severity: DeltaSeverity

@dataclass(frozen=True)
class CallPath:
    """Represents a method call path."""
    caller_class: str
    caller_method: str
    callee_class: str
    callee_method: str

@dataclass(frozen=True)
class TypeFlow:
    """Represents type flow through a method."""
    class_name: str
    method_name: str
    input_types: list[str]
    output_type: str
    transformations: list[str]

@dataclass(frozen=True)
class DeltaReport:
    """Complete delta detection report."""
    structural_deltas: StructuralDeltas
    semantic_deltas: SemanticDeltas
    call_graph_deltas: CallGraphDeltas
    type_flow_deltas: TypeFlowDeltas
    exception_deltas: ExceptionDeltas
    test_coverage_deltas: TestCoverageDeltas
    dependency_deltas: DependencyDeltas
    performance_deltas: PerformanceDeltas
    summary: DeltaSummary
```

## Appendix B: Code Generation Templates

Example Jinja2 templates used in Layer 2 (template-based generation):

### Getter Template

```jinja2
{# templates/method_bodies/getter.py.j2 #}
def get_{{ field_name }}(self) -> {{ return_type }}:
    """Get {{ field_name }}.

    Returns
    -------
    {{ return_type }}
        Current value of {{ field_name }}
    """
    return self._{{ field_name }}
```

### Setter Template

```jinja2
{# templates/method_bodies/setter.py.j2 #}
def set_{{ field_name }}(self, {{ field_name }}: {{ param_type }}) -> None:
    """Set {{ field_name }}.

    Parameters
    ----------
    {{ field_name }} : {{ param_type }}
        New value for {{ field_name }}
    """
    self._{{ field_name }} = {{ field_name }}
```

### Property Template

```jinja2
{# templates/method_bodies/property.py.j2 #}
@property
def {{ property_name }}(self) -> {{ return_type }}:
    """{{ property_name }} property.

    Returns
    -------
    {{ return_type }}
        Current value of {{ property_name }}
    """
    return self._{{ property_name }}

@{{ property_name }}.setter
def {{ property_name }}(self, value: {{ param_type }}) -> None:
    """Set {{ property_name }}.

    Parameters
    ----------
    value : {{ param_type }}
        New value
    """
    self._{{ property_name }} = value
```

## Appendix C: Quality Gate Configuration

Complete configuration for Lean Six Sigma quality enforcement.

### Mypy Configuration (`pyproject.toml`)

```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
```

### Ruff Configuration

```toml
[tool.ruff]
target-version = "py313"
line-length = 120
select = ["ALL"]  # Enable all 400+ rules
ignore = [
    "D203",   # one-blank-line-before-class (conflicts with D211)
    "D213",   # multi-line-summary-second-line (conflicts with D212)
]

[tool.ruff.pydocstyle]
convention = "numpy"

[tool.ruff.per-file-ignores]
"tests/**/*.py" = ["S101"]  # Allow assert in tests
```

### Pytest Configuration

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--cov=src/kgcl",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",
]
```

### Pre-Commit Hooks

```bash
#!/bin/bash
# scripts/git_hooks/pre-commit

# Type checking
uv run mypy --strict src/kgcl/yawl/ || exit 1

# Linting
uv run ruff check src/kgcl/yawl/ tests/ || exit 1

# Implementation lies detection
uv run poe detect-lies || exit 1

# Formatting
uv run ruff format --check src/kgcl/yawl/ tests/ || exit 1

echo "✓ All quality gates passed"
```

## Appendix D: RAG Vector Store Schema

ChromaDB collection schema for RAG-enhanced code generation:

```python
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="data/vector_store"
))

# Create collection for Java methods
java_methods = client.create_collection(
    name="yawl-methods",
    metadata={
        "description": "Java YAWL method embeddings for RAG",
        "hnsw:space": "cosine",
    }
)

# Schema for method documents
method_document = {
    "id": "org.yawl.engine.YEngine.launchCase",
    "embedding": [...],  # 768-dim embedding from OpenAI
    "metadata": {
        "class": "YEngine",
        "package": "org.yawlfoundation.yawl.engine",
        "method": "launchCase",
        "signature": "public YIdentifier launchCase(String specID, ...)",
        "return_type": "YIdentifier",
        "parameters": ["String specID", "Map<String, String> data"],
        "complexity": 5,
        "has_loops": True,
        "has_recursion": False,
        "calls": ["getSpecification", "createCase", "startCase"],
        "throws": ["YStateException", "YDataStateException"],
    },
    "document": """
    public YIdentifier launchCase(String specID, Map<String, String> data)
            throws YStateException {
        YSpecification spec = getSpecification(specID);
        if (spec == null) {
            throw new YStateException("Specification not found: " + specID);
        }
        YIdentifier caseID = createCase(spec);
        YCase yCase = new YCase(caseID, spec, data);
        _cases.put(caseID, yCase);
        startCase(yCase);
        return caseID;
    }
    """
}
```

## Appendix E: Key Implementation Files

Complete reference to all implementation files discussed in this thesis:

### Delta Detection System
- [`delta_detector.py`](../../src/kgcl/yawl_ontology/delta_detector.py) - Main orchestrator (362 lines)
- [`semantic_detector.py`](../../src/kgcl/yawl_ontology/semantic_detector.py) - AST fingerprinting (391 lines)
- [`call_graph_analyzer.py`](../../src/kgcl/yawl_ontology/call_graph_analyzer.py) - Call graph comparison (274 lines)
- [`type_flow_analyzer.py`](../../src/kgcl/yawl_ontology/type_flow_analyzer.py) - Type flow tracking (296 lines)
- [`performance_analyzer.py`](../../src/kgcl/yawl_ontology/performance_analyzer.py) - Performance analysis (263 lines)
- [`test_mapper.py`](../../src/kgcl/yawl_ontology/test_mapper.py) - Test coverage mapping (275 lines)
- [`exception_analyzer.py`](../../src/kgcl/yawl_ontology/exception_analyzer.py) - Exception pattern analysis
- [`dependency_analyzer.py`](../../src/kgcl/yawl_ontology/dependency_analyzer.py) - Dependency tracking

### Enhanced Parsers
- [`enhanced_java_parser.py`](../../src/kgcl/yawl_ontology/enhanced_java_parser.py) - Java AST parsing (485 lines)
- [`enhanced_python_analyzer.py`](../../src/kgcl/yawl_ontology/enhanced_python_analyzer.py) - Python AST analysis (496 lines)

### Data Models
- [`models.py`](../../src/kgcl/yawl_ontology/models.py) - All delta data classes

### Gap Analysis
- [`gap_analyzer.py`](../../src/kgcl/yawl_ontology/gap_analyzer.py) - Original gap detection system

## References

1. van der Aalst, W. M., ter Hofstede, A. H., Kiepuszewski, B., & Barros, A. P. (2003). Workflow patterns. *Distributed and Parallel Databases*, 14(1), 5-51.

2. YAWL Foundation. (2024). *YAWL: Yet Another Workflow Language*. Retrieved from https://yawlfoundation.github.io/

3. Fowler, M. (2018). *Refactoring: Improving the Design of Existing Code* (2nd ed.). Addison-Wesley.

4. Feathers, M. (2004). *Working Effectively with Legacy Code*. Prentice Hall.

5. Freeman, S., & Pryce, N. (2009). *Growing Object-Oriented Software, Guided by Tests*. Addison-Wesley.

6. Beck, K. (2002). *Test Driven Development: By Example*. Addison-Wesley.

7. Anthropic. (2024). *Claude 3.5 Sonnet: Technical Documentation*. Retrieved from https://anthropic.com/

8. Berners-Lee, T., Hendler, J., & Lassila, O. (2001). The semantic web. *Scientific American*, 284(5), 34-43.

9. Gruber, T. R. (1993). A translation approach to portable ontology specifications. *Knowledge Acquisition*, 5(2), 199-220.

10. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33.

---

[← Previous: Chapter 7](./chapter-7-future-work.md) | [Back to Contents](./README.md)
