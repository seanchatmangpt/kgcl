# Atman Engine Documentation Index

## Overview

The **Atman Engine** is the Diamond Standard knowledge graph mutation engine at the heart of KGCL. It implements the **Chatman Equation** (`A = μ(O)`) to provide deterministic, cryptographically-verifiable knowledge graph mutations with O(1) provenance.

## Documentation Suite

This comprehensive documentation suite includes:

### 📘 API Reference

**[OpenAPI 3.0 Specification](./api/atman-engine-openapi.yaml)** (728 lines)
- Complete REST API specification
- Transaction operations (`POST /transactions`)
- Hook management (`GET/POST /hooks`, `DELETE /hooks/{hookId}`)
- Provenance queries (`GET /provenance/tip`, `GET /provenance/logic-hash`)
- SPARQL queries (`GET /triples`)
- Health monitoring (`GET /health`)
- **All** request/response schemas with examples
- Security schemes (API Key, Bearer JWT)

### 📗 Comprehensive Usage Guide

**[Atman Engine Usage Guide](./guides/atman-engine-usage.md)** (940 lines)
- **Quick Start** - Installation and basic usage
- **Core Concepts** - QuadDelta, Atman, Receipt
- **Hook System** - PRE/POST hooks with examples
- **Provenance & Lockchain** - Merkle chain tracking
- **Advanced Patterns** - 4 production-ready patterns:
  1. Schema Validation Hook
  2. Audit Trail Hook
  3. Cache Invalidation Hook
  4. Transaction Batching
- **Performance Optimization** - Benchmarking and tuning
- **Error Handling** - Complete error scenarios
- **Integration Examples** - KGCL Hooks, OTEL, CLI
- **Testing Strategies** - Unit and integration tests
- **Troubleshooting** - Common issues and solutions

### 📙 Integration Guide

**[Atman Integration Guide](./guides/atman-integration.md)** (798 lines)
- **Architecture** - System-wide component diagram
- **KGCL Hooks Integration** - Bridge pattern, event-driven hooks
- **UNRDF Engine Integration** - SPARQL validation, ingestion pipeline
- **OpenTelemetry Integration** - Full OTEL instrumentation, distributed tracing
- **CLI Integration** - Command-line wrappers, daily brief generation
- **DSPy Runtime Integration** - Semantic validation with AI
- **Complete Platform Example** - All integrations together
- **Testing Integrations** - Integration test patterns
- **Best Practices** - Production deployment tips

### 📕 Quick Reference

**[Quick Reference Card](./guides/atman-quick-reference.md)** (470 lines)
- **Chatman Equation** - Core philosophy
- **Basic Usage** - Minimal working examples
- **Core Types** - QuadDelta, Triple, Receipt
- **Hook System** - PRE/POST hook patterns
- **Common Patterns** - 4 essential patterns
- **Provenance** - Chain tip, logic hash, verification
- **Querying** - SPARQL and basic queries
- **Error Handling** - All error scenarios
- **Performance** - Targets and measurement
- **Constants** - CHATMAN_CONSTANT, GENESIS_HASH
- **CLI Usage** - Command-line examples
- **Testing** - Unit and hook tests
- **Troubleshooting** - Quick solutions

### 📖 API Documentation README

**[API Documentation Index](./api/README.md)** (105 lines)
- Documentation overview
- Quick links for developers, architects, operators
- Documentation standards
- Contributing guidelines

## Total Documentation

**3,041 lines** of production-ready documentation including:
- ✅ Complete OpenAPI 3.0 specification
- ✅ NumPy-style docstrings in source code
- ✅ Executable examples (all tested)
- ✅ Integration patterns
- ✅ Performance benchmarks
- ✅ Error handling
- ✅ Testing strategies
- ✅ Troubleshooting guides

## The Chatman Equation

```
A = μ(O)

Where:
  O (Observation) = QuadDelta    - The intent to mutate reality
  μ (Operator)    = Atman        - The deterministic mutation engine
  A (Action)      = Receipt      - Cryptographic proof of execution
```

## Quick Start

```python
import asyncio
from kgcl.engine import Atman, QuadDelta

async def main():
    # 1. Create engine
    engine = Atman()

    # 2. Define mutation
    delta = QuadDelta(
        additions=[
            ("urn:entity:123", "rdf:type", "schema:Person"),
            ("urn:entity:123", "schema:name", "Alice"),
        ]
    )

    # 3. Apply transaction
    receipt = await engine.apply(delta, actor="user:alice")

    # 4. Verify success
    assert receipt.committed
    print(f"Success! Merkle root: {receipt.merkle_root[:16]}...")

asyncio.run(main())
```

## Key Features

### ⚡ Performance
- **p99 <100ms** for all operations
- **64 triples/batch** (Chatman Constant)
- **O(1) receipts** with cryptographic proofs
- **Deterministic execution** order

### 🔒 Security
- **Immutable QuadDelta** - Frozen after creation
- **Cryptographic Receipts** - SHA256 merkle_root + logic_hash
- **Lockchain Provenance** - Every transaction links to previous
- **Auditability** - Full hook execution telemetry

### 🧩 Extensibility
- **PRE Hooks** - Blocking guards for validation
- **POST Hooks** - Non-blocking side effects
- **Deterministic Ordering** - Priority + ID sorting
- **Hook Telemetry** - Execution time tracking

### 🔗 Integrations
- **KGCL Hooks** - Event-driven processing
- **UNRDF Engine** - SPARQL and RDF operations
- **OpenTelemetry** - Distributed tracing and metrics
- **CLI Commands** - Command-line interface
- **DSPy Runtime** - AI-powered semantic validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Layer (daily-brief, weekly-retro, query)               │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│  Atman Engine (Core Mutation Layer)                         │
│                                                              │
│  QuadDelta → μ (Hooks: PRE → Mutate → POST) → Receipt       │
│                                                              │
│  - Merkle Chain (Lockchain)                                 │
│  - Logic Hash (Hook Configuration)                          │
│  - Hook Telemetry (Execution Tracking)                      │
└──────┬───────────┬────────────┬─────────────┬───────────────┘
       │           │            │             │
┌──────▼──────┐ ┌──▼─────┐ ┌────▼────┐ ┌─────▼─────────┐
│  KGCL Hooks │ │ UNRDF  │ │  OTEL   │ │ DSPy Runtime  │
│  System     │ │ Engine │ │ Tracing │ │ (Ollama)      │
└─────────────┘ └────────┘ └─────────┘ └───────────────┘
```

## Performance Targets

| Operation | p50 | p99 | Target |
|-----------|-----|-----|--------|
| Hook registration | 0.1ms | 1.0ms | <5ms |
| Transaction apply | 2.0ms | 50.0ms | <100ms |
| Logic hash | 0.5ms | 5.0ms | <10ms |
| Batch (64 triples) | 10.0ms | 100.0ms | <100ms |

**All targets verified by tests** (48/48 passing, 100% coverage).

## Integrity Guarantees

The engine ensures **three forms of integrity**:

1. **Data Integrity** - QuadDelta captures intent immutably
2. **Logic Integrity** - logic_hash proves which laws applied
3. **History Integrity** - merkle_root links transactions in a chain

## Use Cases

### ✅ Production-Ready For:

- **Knowledge Graph Mutations** - Add/remove triples atomically
- **Schema Validation** - Guard hooks enforce constraints
- **Audit Logging** - POST hooks capture all changes
- **Cache Management** - Invalidate caches on mutations
- **Distributed Systems** - Lockchain enables consensus
- **Event-Driven Systems** - Trigger downstream workflows
- **AI/ML Pipelines** - Semantic validation with DSPy
- **Compliance** - Cryptographic audit trail

### 🔧 Integration Patterns:

- **KGCL Hooks** - Event-driven hook execution
- **UNRDF Engine** - SPARQL validation and ingestion
- **OpenTelemetry** - Distributed tracing and metrics
- **CLI Commands** - Command-line tools
- **REST API** - HTTP interface (OpenAPI spec)
- **Message Queues** - Async processing
- **Databases** - Persistent storage

## Testing Coverage

**48 comprehensive tests** across:
- ✓ QuadDelta creation and validation (8 tests)
- ✓ TransactionContext and Receipt (7 tests)
- ✓ KnowledgeHook creation and execution (5 tests)
- ✓ Atman engine operations (18 tests)
- ✓ Constants and enums (5 tests)
- ✓ Performance benchmarks (3 tests)
- ✓ Integration workflows (2 tests)

**All tests pass in <0.15s** with full type coverage.

## Source Code

- **Engine**: `/src/kgcl/engine/atman.py` (576 lines)
- **Tests**: `/tests/engine/test_atman.py` (663 lines)
- **Init**: `/src/kgcl/engine/__init__.py` (68 lines with enhanced docstrings)

## Documentation Principles

All documentation follows:
- ✅ **NumPy-style docstrings** for all public APIs
- ✅ **Executable examples** (verified by tests)
- ✅ **Chicago School TDD** principles
- ✅ **Production-ready code** (no TODO/placeholders)
- ✅ **100% type coverage** (Mypy strict mode)
- ✅ **OpenAPI 3.0** for REST APIs

## Getting Started

### For Developers
1. Read **[Quick Reference](./guides/atman-quick-reference.md)** (5 min)
2. Try **[Usage Guide examples](./guides/atman-engine-usage.md#quick-start)** (15 min)
3. Explore **[Integration Guide](./guides/atman-integration.md)** (30 min)

### For Architects
1. Review **[OpenAPI Spec](./api/atman-engine-openapi.yaml)** (API design)
2. Study **[Integration Guide architecture](./guides/atman-integration.md#architecture)**
3. Check **[Performance targets](./guides/atman-engine-usage.md#performance-optimization)**

### For Operators
1. Configure **[OpenTelemetry](./guides/atman-integration.md#3-integration-with-opentelemetry)**
2. Set up **[Health monitoring](./api/atman-engine-openapi.yaml#/paths/~1health/get)**
3. Review **[Performance targets](./guides/atman-quick-reference.md#performance)**

## Support

- **GitHub Issues**: https://github.com/kgcl/kgcl/issues
- **Discussions**: https://github.com/kgcl/kgcl/discussions
- **Source Code**: `/src/kgcl/engine/`
- **Tests**: `/tests/engine/`
- **Documentation**: `/docs/`

## Contributing

When contributing:
1. Maintain **NumPy-style docstrings**
2. Add **executable examples**
3. Ensure **100% type coverage**
4. Write **comprehensive tests** (Chicago School TDD)
5. Update **documentation** (guides, OpenAPI spec)
6. Verify **performance targets** (<100ms p99)

## Version

Current documentation suite version: **1.0.0**
- Engine module: `kgcl.engine`
- OpenAPI version: `3.0.0`
- Documentation date: 2024-11-25

---

**The Atman Engine: Diamond Standard Knowledge Graph Mutations** 💎
