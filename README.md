# KGCL - Knowledge Geometry Calculus for Life

A local-first workflow engine implementing all 43 YAWL Workflow Control Patterns using pure N3 rules with hexagonal architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HybridEngine (Facade)                         │
│         load_data() | apply_physics() | run_to_completion()      │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer     │  Ports Layer         │  Adapters Layer  │
│  ─────────────────     │  ───────────         │  ──────────────  │
│  TickExecutor          │  RDFStore            │  OxigraphAdapter │
│  ConvergenceRunner     │  Reasoner            │  EYEAdapter      │
│  StatusInspector       │  RulesProvider       │  WCP43RulesAdapter│
├─────────────────────────────────────────────────────────────────┤
│  Domain Layer                                                    │
│  PhysicsResult | TaskStatus | Exceptions                         │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                                  │
│  PyOxigraph (Rust)  │  EYE Reasoner  │  N3 Rules (43 WCP)       │
└─────────────────────────────────────────────────────────────────┘
```

**Hard Separation**: State (PyOxigraph) and Logic (N3/EYE) are strictly separated. Python orchestrates ticks—NO workflow logic in Python.

## Quick Start

```bash
# Install
uv sync

# Run tests (1745 tests)
uv run poe test

# Quality checks
uv run poe verify
```

## Usage

```python
from kgcl.hybrid import HybridEngine, ConvergenceError

engine = HybridEngine()

# Load workflow topology (Turtle format)
engine.load_data("""
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    <urn:task:A> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] .

    <urn:task:B> a yawl:Task ;
        kgc:status "Pending" .
""")

# Run to completion
try:
    results = engine.run_to_completion(max_ticks=10)
    print(f"Converged in {len(results)} tick(s)")
except ConvergenceError as e:
    print(f"Failed after {e.max_ticks} ticks")

# Inspect final state
for task, status in engine.inspect().items():
    print(f"{task} -> {status}")
```

## Project Structure

```
src/
├── kgcl/
│   ├── hybrid/                    # Workflow engine (hexagonal architecture)
│   │   ├── domain/                # Value objects: PhysicsResult, TaskStatus
│   │   ├── ports/                 # Protocols: RDFStore, Reasoner, RulesProvider
│   │   ├── adapters/              # Implementations: Oxigraph, EYE, WCP43Rules
│   │   ├── application/           # Use cases: TickExecutor, ConvergenceRunner
│   │   ├── hybrid_engine.py       # Facade (276 lines)
│   │   └── wcp43_physics.py       # All 43 WCP patterns in N3
│   ├── cli/                       # Command-line interface
│   ├── ontology/                  # RDF/TTL ontologies
│   └── ingress/                   # SHACL validation at boundary
├── core/                          # Testing utilities
├── swarm/                         # Multi-agent coordination
└── validation/                    # Property-based validation

tests/                             # 1745 tests (Chicago School TDD)
docs/                              # Documentation
```

## WCP-43 Pattern Coverage

All 43 YAWL Workflow Control Patterns implemented as pure N3 rules:

| Category | Patterns | KGC Verb |
|----------|----------|----------|
| Basic Control Flow | WCP 1-5 | Transmute, Copy, Await, Filter |
| Advanced Branching | WCP 6-9 | Filter, Await |
| Structural | WCP 10-11 | Transmute |
| Multiple Instances | WCP 12-15 | Copy, Await |
| State-Based | WCP 16-18 | — |
| Cancellation | WCP 19-20, 25-27 | Void |
| Iteration | WCP 21-22 | Transmute |
| Triggers | WCP 23-24 | — |
| Advanced Sync | WCP 28-36 | Await |
| Termination | WCP 37-43 | Void |

## Development

```bash
# Format
uv run poe format

# Lint
uv run poe lint

# Type check
uv run poe type-check

# All checks
uv run poe verify

# Watch tests
uv run poe tdd-watch
```

## Quality Standards

| Metric | Target |
|--------|--------|
| Tests | 1745 passing |
| Coverage | 80%+ |
| Types | 100% function signatures |
| Lint | Ruff (120 char, strict) |

## Documentation

- [Getting Started](docs/getting-started.md) — 5-minute guide
- [Architecture](docs/architecture.md) — Hexagonal design
- [API Reference](docs/reference/api.md) — Complete API
- [WCP Patterns](docs/reference/wcp-patterns.md) — All 43 patterns
- [CLI Reference](docs/reference/cli.md) — Command-line usage

## License

MIT
