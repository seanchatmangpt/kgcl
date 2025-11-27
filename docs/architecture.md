# Architecture

KGCL Hybrid Engine uses hexagonal architecture (ports and adapters) with strict separation between state and logic.

## Design Philosophy

**Hard Separation**:
- **Matter** (State): Inert RDF triples stored in PyOxigraph (Rust)
- **Physics** (Logic): N3 rules executed by EYE reasoner (external subprocess)
- **Time** (Orchestration): Python tick controller

No workflow logic in Python. All reasoning happens in N3 rules.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    HybridEngine (Facade)                         │
│                                                                  │
│  Composes all layers, provides simple public API                 │
│  - load_data(turtle)                                            │
│  - apply_physics() -> PhysicsResult                             │
│  - run_to_completion(max_ticks) -> list[PhysicsResult]         │
│  - inspect() -> dict[str, str]                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   TickExecutor    │ │ ConvergenceRunner │ │  StatusInspector  │
│                   │ │                   │ │                   │
│ Single tick:      │ │ Repeated ticks:   │ │ Query state:      │
│ Export→Reason→    │ │ Until delta=0     │ │ SPARQL for        │
│ Ingest            │ │ or max reached    │ │ task statuses     │
└─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│     RDFStore      │ │     Reasoner      │ │   RulesProvider   │
│    (Protocol)     │ │    (Protocol)     │ │    (Protocol)     │
│                   │ │                   │ │                   │
│ - load_turtle()   │ │ - reason()        │ │ - get_rules()     │
│ - dump()          │ │ - is_available()  │ │ - get_rule_subset │
│ - query()         │ │                   │ │                   │
│ - triple_count()  │ │                   │ │                   │
└─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  OxigraphAdapter  │ │    EYEAdapter     │ │ WCP43RulesAdapter │
│                   │ │                   │ │                   │
│ Wraps:            │ │ Wraps:            │ │ Wraps:            │
│ OxigraphStore     │ │ EYEReasoner       │ │ WCP43_COMPLETE_   │
│ (pyoxigraph)      │ │ (subprocess)      │ │ PHYSICS           │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

## Layer Details

### Domain Layer

Pure value objects with no external dependencies.

```python
# PhysicsResult - Result of one tick
@dataclass(frozen=True)
class PhysicsResult:
    tick_number: int
    duration_ms: float
    triples_before: int
    triples_after: int
    delta: int

    @property
    def converged(self) -> bool:
        return self.delta == 0

# TaskStatus - Workflow states with priority
class TaskStatus(Enum):
    PENDING = "Pending"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"
    WAITING = "Waiting"
    CANCELLED = "Cancelled"
    BLOCKED = "Blocked"

# Exceptions
class HybridEngineError(Exception): ...
class ConvergenceError(HybridEngineError): ...
class ReasonerError(HybridEngineError): ...
class StoreOperationError(HybridEngineError): ...
```

### Ports Layer

Abstract protocols defining contracts.

```python
# RDFStore - Storage abstraction
class RDFStore(Protocol):
    def load_turtle(self, data: str) -> int: ...
    def load_n3(self, data: str) -> int: ...
    def dump(self) -> str: ...
    def triple_count(self) -> int: ...
    def query(self, sparql: str) -> list[dict[str, Any]]: ...
    def clear(self) -> None: ...

# Reasoner - N3 reasoning abstraction
class Reasoner(Protocol):
    def reason(self, state: str, rules: str) -> ReasoningOutput: ...
    def is_available(self) -> bool: ...

# RulesProvider - Rules source abstraction
class RulesProvider(Protocol):
    def get_rules(self) -> str: ...
    def get_rule_subset(self, pattern_ids: list[int]) -> str: ...
```

### Adapters Layer

Implementations of ports wrapping concrete technologies.

| Adapter | Wraps | Technology |
|---------|-------|------------|
| `OxigraphAdapter` | `OxigraphStore` | PyOxigraph (Rust) |
| `EYEAdapter` | `EYEReasoner` | EYE subprocess |
| `WCP43RulesAdapter` | `WCP43_COMPLETE_PHYSICS` | N3 rules |

### Application Layer

Use cases orchestrating ports.

| Service | Responsibility |
|---------|---------------|
| `TickExecutor` | Single tick: Export → Reason → Ingest |
| `ConvergenceRunner` | Repeat ticks until delta=0 |
| `StatusInspector` | Query task statuses via SPARQL |

## Tick Execution Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   EXPORT     │     │   REASON     │     │   INGEST     │
│              │     │              │     │              │
│ Store.dump() │────▶│ EYE.reason() │────▶│ Store.load() │
│              │     │              │     │              │
│ State T₀     │     │ State + Rules│     │ State T₁     │
│ (RDF)        │     │ → Deductions │     │ (RDF + Δ)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

1. **Export**: Serialize current state to TRIG format
2. **Reason**: Apply N3 rules via EYE, get deductions
3. **Ingest**: Load new triples back into store
4. **Measure**: Calculate delta (T₁ - T₀)

## Dependency Injection

Ports enable testing without external dependencies:

```python
# Production
engine = HybridEngine()  # Uses real adapters

# Testing
store = FakeRDFStore()
reasoner = FakeReasoner()
rules = FakeRulesProvider()
executor = TickExecutor(store, reasoner, rules)
```

## File Structure

```
src/kgcl/hybrid/
├── __init__.py              # Public exports
├── hybrid_engine.py         # Facade (~150 lines)
│
├── domain/                  # Pure value objects
│   ├── physics_result.py
│   ├── task_status.py
│   └── exceptions.py
│
├── ports/                   # Abstract protocols
│   ├── store_port.py
│   ├── reasoner_port.py
│   └── rules_port.py
│
├── adapters/                # Port implementations
│   ├── oxigraph_adapter.py
│   ├── eye_adapter.py
│   └── wcp43_rules_adapter.py
│
├── application/             # Use cases
│   ├── tick_executor.py
│   ├── convergence_runner.py
│   └── status_inspector.py
│
└── [infrastructure]         # Supporting modules
    ├── oxigraph_store.py
    ├── eye_reasoner.py
    ├── wcp43_physics.py
    └── ...
```

## Benefits

1. **Testability**: Ports allow mocking without external systems
2. **Flexibility**: Swap adapters (different stores, reasoners)
3. **Clarity**: Clear boundaries between layers
4. **Maintainability**: Changes isolated to specific layers
5. **Type Safety**: Protocols enforce contracts at compile time
