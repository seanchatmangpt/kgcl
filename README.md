# KGCL - Knowledge Geometry Calculus for Life

A local-first autonomic knowledge engine implementing all 43 YAWL Workflow Control Patterns in pure N3 rules with PyOxigraph + EYE reasoner architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Python (Time Layer)                       │
│                    Manual Tick Controller                        │
├─────────────────────────────────────────────────────────────────┤
│                     N3 Rules (Physics Layer)                     │
│              17 Laws implementing 43 WCP Patterns                │
├─────────────────────────────────────────────────────────────────┤
│                   PyOxigraph (State Layer)                       │
│                   Inert RDF Triple Store                         │
└─────────────────────────────────────────────────────────────────┘
```

**Hard Separation Principle**: State (Oxigraph) and Logic (N3/EYE) are strictly separated. Python only orchestrates ticks - NO workflow logic in Python.

## Key Features

- **Pure N3 Physics**: All 43 YAWL patterns implemented as N3 rules executed by EYE reasoner
- **PyOxigraph Storage**: Rust-based RDF triple store for state persistence
- **Tick-Based Execution**: Manual clock model for deterministic workflow execution
- **Lockchain Provenance**: Git-backed tick receipts for audit trail
- **SHACL Validation**: Data validated at ingress boundary only

## Quick Start

```bash
# Install
uv sync

# Run tests
uv run poe test

# Quality checks
uv run poe verify
```

## Usage

```python
from kgcl.hybrid import HybridEngine

# Create engine with N3 physics
engine = HybridEngine()

# Load workflow topology
engine.load_data("""
    @prefix kgc: <http://kgc.local/> .
    @prefix yawl: <http://yawl.local/> .

    kgc:task1 kgc:status "Active" ;
              yawl:flowsInto [ yawl:nextElementRef kgc:task2 ] .
    kgc:task2 kgc:status "Pending" .
""")

# Apply N3 physics (one tick)
result = engine.apply_physics()
```

## Project Structure

```
src/kgcl/
├── hybrid/           # PyOxigraph + EYE hybrid engine
│   ├── hybrid_engine.py     # Main engine with N3 physics
│   ├── oxigraph_store.py    # PyOxigraph wrapper
│   ├── tick_controller.py   # Tick orchestration
│   ├── physics_ontology.py  # N3 laws (17 laws, 43 patterns)
│   ├── eye_reasoner.py      # EYE reasoner interface
│   └── lockchain.py         # Git-backed provenance
├── engine/           # Core engine interfaces
├── ingress/          # SHACL validation at boundary
├── ontology/         # RDF/TTL ontologies
└── templates/        # SPARQL templates

tests/                # Chicago School TDD tests (541 passing)
docs/                 # Diátaxis documentation
ontology/             # WCP pattern ontologies
```

## Documentation

Documentation follows the [Diátaxis](https://diataxis.fr/) framework:

- **[Tutorials](docs/tutorials/)** - Learning-oriented guides
- **[How-To Guides](docs/how-to/)** - Task-oriented instructions
- **[Reference](docs/reference/)** - Technical specifications
- **[Explanation](docs/explanation/)** - Architecture and design

## WCP Pattern Coverage

| Tier | Patterns | Status |
|------|----------|--------|
| Basic Control | WCP 1-5 | Pure N3 |
| Advanced Branching | WCP 6-11 | Pure N3 |
| Structural | WCP 12-15 | Pure N3 |
| Multiple Instance | WCP 16-22 | Pure N3 |
| State-Based | WCP 23-28 | Pure N3 |
| Cancellation | WCP 29-35 | Pure N3 |
| Iteration | WCP 36-43 | Pure N3 |

30/43 patterns implemented in pure N3 (70%). Remaining 13 require L5 Python boundaries.

## N3 Physics Laws

The engine implements 17 N3 laws:

| Law | Pattern | Description |
|-----|---------|-------------|
| LAW 1 | SEQUENCE | Completed task activates next |
| LAW 2 | AND-SPLIT | Fork to all parallel branches |
| LAW 3 | AND-JOIN | Synchronize when ALL complete |
| LAW 4 | XOR-SPLIT | Exclusive choice |
| LAW 5 | AUTO-COMPLETE | Self-triggering tasks |
| LAW 6 | TERMINAL | End workflow |
| LAW 7 | MI-SPAWN | Multiple instance creation |
| LAW 8 | PARTIAL-JOIN | k-of-n synchronization |
| LAW 9/9b | DISCRIMINATOR | First-wins pattern |
| LAW 10 | DEFERRED | Future activation |
| LAW 11/11b | INTERLEAVED | Ordered parallel |
| LAW 12/12b | IMPLICIT-TERM | Auto-terminate on complete |
| LAW 13/13b | MI-COMPLETE | Instance completion |
| LAW 14/14b | CANCEL-CASE | Case cancellation |
| LAW 15/15b | OR-SPLIT | Multi-choice |
| LAW 16/16b | MILESTONE | Milestone gates |
| LAW 17 | OR-JOIN | Merge any branch |

## Development

```bash
# Format code
uv run poe format

# Lint
uv run poe lint

# Type check
uv run poe type-check

# Run all checks
uv run poe verify

# Detect implementation stubs
uv run poe detect-lies
```

## Quality Standards

- **Tests**: 541 passing (Chicago School TDD)
- **Coverage**: 80%+ minimum
- **Types**: 100% coverage required
- **Linting**: Ruff with 400+ rules
- **Security**: Bandit scanning

## License

MIT
