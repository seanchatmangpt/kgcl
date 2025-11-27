# Getting Started

Get up and running with KGCL Hybrid Engine in 5 minutes.

## Prerequisites

1. **Python 3.12+**
2. **PyOxigraph** (installed automatically)
3. **EYE Reasoner** (external dependency)

### Install EYE Reasoner

```bash
# macOS
brew install eye

# Ubuntu/Debian
apt-get install eye

# Verify installation
eye --version
```

## Installation

```bash
# Using uv (recommended)
uv add kgcl

# Or pip
pip install kgcl
```

## Your First Workflow

### Step 1: Create an Engine

```python
from kgcl.hybrid import HybridEngine

engine = HybridEngine()
```

### Step 2: Define a Workflow Topology

```python
topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# Task A is completed
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

# Flow connects A to B
<urn:flow:1> yawl:nextElementRef <urn:task:B> .

# Task B is pending
<urn:task:B> a yawl:Task ;
    kgc:status "Pending" .
"""

engine.load_data(topology)
```

### Step 3: Apply Physics

```python
# Single tick
result = engine.apply_physics()
print(f"Tick {result.tick_number}: delta = {result.delta}")

# Or run to completion
results = engine.run_to_completion(max_ticks=10)
print(f"Converged in {len(results)} ticks")
```

### Step 4: Inspect Results

```python
statuses = engine.inspect()
for task, status in statuses.items():
    print(f"{task} -> {status}")

# Output:
# urn:task:A -> Completed
# urn:task:B -> Active
```

## Understanding Physics Results

Each tick returns a `PhysicsResult`:

```python
@dataclass(frozen=True)
class PhysicsResult:
    tick_number: int      # Sequential tick ID
    duration_ms: float    # Execution time
    triples_before: int   # State before tick
    triples_after: int    # State after tick
    delta: int            # Change in triples

    @property
    def converged(self) -> bool:
        return self.delta == 0
```

## Common Patterns

### Sequence (WCP-1)

```turtle
<urn:task:A> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:task:B> kgc:status "Pending" .
```

When A completes, B becomes Active.

### Parallel Split (WCP-2)

```turtle
<urn:task:Split> kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .
<urn:flow:1> yawl:nextElementRef <urn:task:B1> .
<urn:flow:2> yawl:nextElementRef <urn:task:B2> .
```

When Split completes, both B1 and B2 become Active.

### Synchronization (WCP-3)

```turtle
<urn:task:B1> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:task:B2> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .
<urn:flow:1> yawl:nextElementRef <urn:task:Join> .
<urn:flow:2> yawl:nextElementRef <urn:task:Join> .
<urn:task:Join> yawl:hasJoin yawl:ControlTypeAnd .
```

Join becomes Active only when ALL incoming tasks are Completed.

## Error Handling

```python
from kgcl.hybrid import ConvergenceError, ReasonerError

try:
    results = engine.run_to_completion(max_ticks=5)
except ConvergenceError as e:
    print(f"No convergence after {e.max_ticks} ticks")
    print(f"Final delta: {e.final_delta}")
except ReasonerError as e:
    print(f"EYE reasoner failed: {e.message}")
```

## Next Steps

- [Architecture](architecture.md) - Understand the hexagonal design
- [API Reference](reference/api.md) - Complete API documentation
- [WCP Patterns](reference/wcp-patterns.md) - All 43 workflow patterns
