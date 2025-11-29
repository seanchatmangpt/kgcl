# Type Safety Patterns

**Philosophy**: 100% type coverage for documentation and maintainability.

## Type Hint Requirements

### ✅ REQUIRED - All Functions

```python
# Every function needs types
def execute_workflow(case_id: str, spec: WorkflowSpecification) -> WorkflowResult:
    """Execute YAWL workflow case."""
    ...

# Every parameter needs type
def parse_condition(
    condition: str,
    context: dict[str, Any],
    timeout_ms: int = 100
) -> bool:
    """Parse and evaluate N3 condition."""
    ...

# Inner functions need types too
def outer(items: list[str]) -> int:
    def inner(x: str) -> bool:
        return len(x) > 0
    return sum(1 for i in items if inner(i))
```

### ✅ Modern Python 3.13+ Syntax

```python
# Use | None instead of Optional
def fetch(path: str, default: str | None = None) -> str:
    ...

# Use built-in generics
def process(items: list[str]) -> dict[str, int]:
    ...

# Use type aliases for complex types
type JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None
type ConditionContext = dict[str, JSONValue]

def evaluate(cond: str, ctx: ConditionContext) -> bool:
    ...
```

### ❌ FORBIDDEN - Type Suppressions

```python
# ❌ Blanket type: ignore
result = unsafe_operation()  # type: ignore

# ❌ Blanket noqa
cast(ComplexType, data)  # noqa

# ✅ ALLOWED - With justification
# type: ignore[import]  # External lib lacks stubs - tracked in issue #123
from external_lib import UnstypedClass
```

## When to Use `Any`

### ✅ JUSTIFIED - With Comment

```python
from typing import Any

def parse_json(data: str) -> Any:  # JSON can be any valid JSON type
    """Parse JSON string into Python object."""
    return json.loads(data)

def handle_rdf_literal(literal: Any) -> str:  # RDFLib Literal type not in stubs
    """Convert RDF literal to string."""
    return str(literal)
```

### ❌ UNJUSTIFIED - Lazy Typing

```python
# ❌ Should use specific types
def process(data: Any) -> Any:  # What types are actually expected?
    ...

# ✅ Better - Specific types
def process(data: dict[str, str]) -> list[str]:
    ...
```

## When to Use `cast()`

### ✅ JUSTIFIED - SHACL Validated

```python
from typing import cast

def process_case(raw_data: dict[str, Any]) -> WorkflowCase:
    # SHACL validates WorkflowCase structure at ingress - safe to cast
    return cast(WorkflowCase, raw_data)
```

### ✅ JUSTIFIED - Type Narrowing

```python
from typing import cast

def get_config(key: str) -> str:
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Missing config: {key}")
    # Type narrowing - we know value is str after None check
    return cast(str, value)
```

### ❌ UNJUSTIFIED - Hope It Works

```python
# ❌ No justification
result = cast(ComplexType, untrusted_data)

# ❌ Avoiding proper type handling
result = cast(str, dict["key"])  # Should use .get() and check type
```

## Dataclass Patterns

### ✅ Frozen Dataclasses for Value Objects

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class WorkflowToken:
    """Immutable workflow token."""
    case_id: str
    task_id: str
    enabled: bool

@dataclass(frozen=True)
class Receipt:
    """Hook execution receipt."""
    execution_id: str
    hook_id: str
    success: bool
    duration_ms: int
```

### ✅ Default Factories for Mutable Defaults

```python
from dataclasses import dataclass, field

@dataclass
class WorkflowCase:
    """Mutable workflow case state."""
    id: str
    tokens: list[WorkflowToken] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    # ❌ NEVER do this (mutable default)
    # tokens: list[WorkflowToken] = []  # Shared across instances!
```

## Generic Types

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    """Generic repository pattern."""

    def save(self, item: T) -> None:
        """Save item to repository."""
        ...

    def get(self, id: str) -> T | None:
        """Retrieve item by ID."""
        ...

# Usage
cases: Repository[WorkflowCase] = CaseRepository()
specs: Repository[WorkflowSpecification] = SpecRepository()
```

## Protocol Types (Structural Subtyping)

```python
from typing import Protocol

class Executable(Protocol):
    """Protocol for executable workflow elements."""

    def execute(self, context: dict[str, Any]) -> bool:
        """Execute with given context."""
        ...

class Task:
    def execute(self, context: dict[str, Any]) -> bool:
        """Execute task."""
        return True

# Task satisfies Executable protocol without explicit inheritance
def run_workflow(steps: list[Executable]) -> bool:
    return all(step.execute({}) for step in steps)

tasks: list[Task] = [Task(), Task()]
run_workflow(tasks)  # Type-safe - Task matches Executable protocol
```

## Type Narrowing

```python
def process(value: str | int | None) -> str:
    """Process value based on type."""

    # Type narrowing with isinstance
    if isinstance(value, str):
        return value.upper()  # mypy knows value is str here

    if isinstance(value, int):
        return str(value)  # mypy knows value is int here

    # After two isinstance checks, mypy knows value must be None
    raise ValueError("Value must not be None")
```

## Mypy Configuration

**Current state (in pyproject.toml):**
```toml
[tool.mypy]
strict = false  # ❌ Technical debt - should be true
disable_error_code = [...]  # ❌ Too many disabled checks
```

**Target state (Order 1 from IMPLEMENTATION_ORDERS.md):**
```toml
[tool.mypy]
strict = true  # ✅ Enforce all checks

# Only specific overrides for external libraries
[[tool.mypy.overrides]]
module = "external_lib.*"
ignore_missing_imports = true  # No stubs available upstream
```

## Common Type Errors to Fix

### 1. Untyped Parameters

```python
# ❌ Before
def process(data):  # Untyped
    return data.get("key")

# ✅ After
def process(data: dict[str, Any]) -> str | None:
    return data.get("key")
```

### 2. Missing Return Types

```python
# ❌ Before
def calculate(x: int, y: int):  # No return type
    return x + y

# ✅ After
def calculate(x: int, y: int) -> int:
    return x + y
```

### 3. Deprecated Typing Imports

```python
# ❌ Before (UP035 violation)
from typing import Dict, List, Optional

def process(items: List[str]) -> Optional[Dict[str, int]]:
    ...

# ✅ After (Python 3.13+ syntax)
def process(items: list[str]) -> dict[str, int] | None:
    ...
```

## References

- ERROR_HANDLING.md - Error handling patterns
- FMEA.md - Risk analysis for type safety
- IMPLEMENTATION_ORDERS.md Order 1 - Fix mypy strict
- RUFF_IGNORES_HONEST_ANALYSIS.md - UP035 deprecated imports
