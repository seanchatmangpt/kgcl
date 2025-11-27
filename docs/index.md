# KGCL Hybrid Engine

A tick-based workflow execution engine using PyOxigraph + EYE Reasoner with hexagonal architecture.

## Quick Links

- [Getting Started](getting-started.md) - 5 minute quickstart
- [Architecture](architecture.md) - Hexagonal architecture overview
- [API Reference](reference/api.md) - Complete API documentation
- [WCP Patterns](reference/wcp-patterns.md) - 43 workflow control patterns
- [CLI Reference](reference/cli.md) - Command-line interface

## Installation

```bash
# Install KGCL
pip install kgcl

# Install EYE reasoner (required for physics execution)
# macOS
brew install eye

# Ubuntu/Debian
apt-get install eye
```

## Basic Usage

```python
from kgcl.hybrid import HybridEngine

# Create engine
engine = HybridEngine()

# Load workflow topology
topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:A> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:task:B> a yawl:Task .
"""
engine.load_data(topology)

# Run to completion
results = engine.run_to_completion(max_ticks=10)

# Inspect final state
statuses = engine.inspect()
for task, status in statuses.items():
    print(f"{task} -> {status}")
```

## Architecture Overview

```
┌─────────────────────────────────────────┐
│          HybridEngine (Facade)          │
└────────────────────┬────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Application Layer (Use Cases)
   TickExecutor | ConvergenceRunner | StatusInspector
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      Ports Layer (Protocols)
   RDFStore | Reasoner | RulesProvider
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    Adapters Layer (Implementations)
   OxigraphAdapter | EYEAdapter | WCP43RulesAdapter
```

**Hard Separation**: State (PyOxigraph) and Logic (N3/EYE) are strictly separated. Python orchestrates ticks only - NO workflow logic in Python.

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Matter** | Inert RDF triples stored in PyOxigraph |
| **Physics** | N3 rules applied by EYE reasoner |
| **Time** | Python tick controller orchestrates execution |
| **Convergence** | System reaches fixed point when delta = 0 |

## Project Status

| Metric | Value |
|--------|-------|
| Tests | 113 passing |
| Architecture | Hexagonal (Ports & Adapters) |
| WCP Coverage | 43/43 patterns implemented |
| Type Coverage | 100% (mypy strict) |
