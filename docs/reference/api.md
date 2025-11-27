# API Reference

Complete API documentation for KGCL Hybrid Engine.

## HybridEngine

Main facade class for workflow execution.

```python
from kgcl.hybrid import HybridEngine
```

### Constructor

```python
HybridEngine(store_path: str | None = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `store_path` | `str \| None` | `None` | Path for persistent store. `None` = in-memory |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `store` | `pyoxigraph.Store` | Raw PyOxigraph store (backward compat) |
| `tick_count` | `int` | Total ticks executed |

### Methods

#### `load_data(turtle_data: str) -> None`

Load RDF data in Turtle format.

```python
engine.load_data("""
    @prefix kgc: <https://kgc.org/ns/> .
    <urn:task:A> kgc:status "Completed" .
""")
```

#### `apply_physics() -> PhysicsResult`

Execute single tick of physics.

```python
result = engine.apply_physics()
print(f"Delta: {result.delta}")
```

#### `run_to_completion(max_ticks: int = 100) -> list[PhysicsResult]`

Run until convergence (delta=0) or max ticks.

```python
results = engine.run_to_completion(max_ticks=10)
if results[-1].converged:
    print("Reached fixed point")
```

**Raises**: `ConvergenceError` if max_ticks reached without convergence.

#### `inspect() -> dict[str, str]`

Query current task statuses.

```python
statuses = engine.inspect()
# {'urn:task:A': 'Completed', 'urn:task:B': 'Active'}
```

---

## PhysicsResult

Immutable result from one tick of physics execution.

```python
from kgcl.hybrid import PhysicsResult
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `tick_number` | `int` | Sequential tick identifier |
| `duration_ms` | `float` | Execution time in milliseconds |
| `triples_before` | `int` | Triple count before tick |
| `triples_after` | `int` | Triple count after tick |
| `delta` | `int` | Change in triples (after - before) |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `converged` | `bool` | `True` if `delta == 0` |

### Example

```python
result = engine.apply_physics()
print(f"Tick {result.tick_number}")
print(f"Duration: {result.duration_ms:.2f}ms")
print(f"Delta: {result.delta} triples")
print(f"Converged: {result.converged}")
```

---

## TaskStatus

Enumeration of workflow task states with priority ordering.

```python
from kgcl.hybrid import TaskStatus
```

### Values

| Value | Priority | Description |
|-------|----------|-------------|
| `PENDING` | 0 | Task not yet started |
| `ACTIVE` | 1 | Task in progress |
| `WAITING` | 2 | Task waiting on external |
| `BLOCKED` | 3 | Task blocked by dependency |
| `COMPLETED` | 4 | Task finished successfully |
| `CANCELLED` | 5 | Task cancelled |
| `ARCHIVED` | 6 | Task archived (final) |

### Class Methods

#### `from_string(status: str) -> TaskStatus`

Create enum from string value.

```python
status = TaskStatus.from_string("Active")
# TaskStatus.ACTIVE
```

#### `highest_priority(statuses: list[TaskStatus]) -> TaskStatus`

Resolve multiple statuses by priority (monotonic).

```python
highest = TaskStatus.highest_priority([
    TaskStatus.PENDING,
    TaskStatus.ACTIVE,
    TaskStatus.COMPLETED
])
# TaskStatus.COMPLETED (highest priority)
```

---

## Exceptions

### HybridEngineError

Base exception for all hybrid engine errors.

```python
from kgcl.hybrid import HybridEngineError
```

### ConvergenceError

Raised when system fails to reach fixed point.

```python
from kgcl.hybrid import ConvergenceError

try:
    results = engine.run_to_completion(max_ticks=5)
except ConvergenceError as e:
    print(f"No convergence after {e.max_ticks} ticks")
    print(f"Final delta: {e.final_delta}")
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `max_ticks` | `int` | Maximum ticks attempted |
| `final_delta` | `int` | Delta at failure |

### ReasonerError

Raised when EYE reasoner fails.

```python
from kgcl.hybrid import ReasonerError

try:
    result = engine.apply_physics()
except ReasonerError as e:
    print(f"Reasoner failed: {e.message}")
    print(f"Command: {e.command}")
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Error message |
| `command` | `str \| None` | Failed command |

### StoreOperationError

Raised when store operation fails.

```python
from kgcl.hybrid import StoreOperationError
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `operation` | `str` | Operation that failed |
| `message` | `str` | Error message |

---

## Port Protocols

Abstract interfaces for dependency injection.

### RDFStore

```python
from kgcl.hybrid import RDFStore

class RDFStore(Protocol):
    def load_turtle(self, data: str) -> int: ...
    def load_n3(self, data: str) -> int: ...
    def dump(self) -> str: ...
    def triple_count(self) -> int: ...
    def query(self, sparql: str) -> list[dict[str, Any]]: ...
    def clear(self) -> None: ...
```

### Reasoner

```python
from kgcl.hybrid import Reasoner, ReasoningOutput

class Reasoner(Protocol):
    def reason(self, state: str, rules: str) -> ReasoningOutput: ...
    def is_available(self) -> bool: ...

@dataclass(frozen=True)
class ReasoningOutput:
    success: bool
    output: str
    error: str | None
    duration_ms: float
```

### RulesProvider

```python
from kgcl.hybrid import RulesProvider

class RulesProvider(Protocol):
    def get_rules(self) -> str: ...
    def get_rule_subset(self, pattern_ids: list[int]) -> str: ...
```

---

## Adapters

Concrete implementations of ports.

### OxigraphAdapter

```python
from kgcl.hybrid import OxigraphAdapter

adapter = OxigraphAdapter(path=None)  # In-memory
adapter = OxigraphAdapter(path="/data/store")  # Persistent
```

### EYEAdapter

```python
from kgcl.hybrid import EYEAdapter

adapter = EYEAdapter()
if adapter.is_available():
    output = adapter.reason(state, rules)
```

### WCP43RulesAdapter

```python
from kgcl.hybrid import WCP43RulesAdapter

adapter = WCP43RulesAdapter()
all_rules = adapter.get_rules()
subset = adapter.get_rule_subset([1, 2, 3])  # WCP 1-3 only
```

---

## Application Services

Use case implementations.

### TickExecutor

Single tick execution.

```python
from kgcl.hybrid.application import TickExecutor

executor = TickExecutor(store, reasoner, rules_provider)
result = executor.execute_tick(tick_number=1)
```

### ConvergenceRunner

Run-to-completion logic.

```python
from kgcl.hybrid.application import ConvergenceRunner

runner = ConvergenceRunner(executor)
results = runner.run(max_ticks=100)
```

### StatusInspector

Query task statuses.

```python
from kgcl.hybrid.application import StatusInspector

inspector = StatusInspector(store)
statuses = inspector.get_task_statuses()
tasks = inspector.get_tasks_by_status("Active")
```

---

## WCP-43 Physics

Access to workflow control pattern rules.

```python
from kgcl.hybrid import (
    WCP43_COMPLETE_PHYSICS,
    WCP_PATTERN_CATALOG,
    get_pattern_info,
    get_pattern_rule,
    list_wcp_patterns,
    get_patterns_by_category,
    get_patterns_by_verb,
)

# Get pattern info
info = get_pattern_info(1)
# {'name': 'Sequence', 'verb': 'Transmute', 'category': 'Basic Control Flow'}

# Get N3 rule for pattern
rule = get_pattern_rule(1)

# List all patterns
patterns = list_wcp_patterns()  # [1, 2, 3, ..., 43]

# Filter by category
basic = get_patterns_by_category("Basic Control Flow")

# Filter by verb
transmute = get_patterns_by_verb("Transmute")
```
