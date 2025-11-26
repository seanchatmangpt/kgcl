# KGCL API Documentation

## Overview

This directory contains comprehensive API documentation for the KGCL platform.

## Available Documentation

### Atman Engine (Knowledge Graph Mutation Engine)

The Atman Monolith implements the Chatman Equation (A = μ(O)) for deterministic knowledge graph mutations with cryptographic provenance.

**Documentation:**
- **[OpenAPI Specification](./atman-engine-openapi.yaml)** - Complete REST API specification
  - Transaction operations
  - Hook management
  - Provenance queries
  - SPARQL queries
  - Health monitoring

**Guides:**
- **[Usage Guide](../guides/atman-engine-usage.md)** - Comprehensive usage examples
  - Quick start
  - Core concepts (QuadDelta, Receipt, Hooks)
  - Hook system (PRE/POST hooks)
  - Provenance & Lockchain
  - Advanced patterns
  - Performance optimization
  - Error handling
  - Testing strategies

- **[Integration Guide](../guides/atman-integration.md)** - System integration patterns
  - KGCL Hooks integration
  - UNRDF Engine integration
  - OpenTelemetry integration
  - CLI integration
  - DSPy Runtime integration
  - Complete platform example

## Quick Links

### For Developers

**Getting Started:**
```python
from kgcl.engine import Atman, QuadDelta

engine = Atman()
delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt = await engine.apply(delta)
```

**API Reference:**
- View the [OpenAPI spec](./atman-engine-openapi.yaml) in Swagger UI
- Read the [usage guide](../guides/atman-engine-usage.md) for examples
- Check [integration patterns](../guides/atman-integration.md) for system-wide usage

### For Architects

**Key Concepts:**
- **Chatman Equation**: A = μ(O) - Deterministic knowledge graph mutations
- **Hot Path**: All operations <100ms (p99) with batches ≤64 triples
- **Lockchain**: Merkle chain linking all transactions cryptographically
- **Hook System**: Extensible PRE (guards) and POST (side effects) hooks

**Architecture Diagrams:**
- See [integration guide](../guides/atman-integration.md#architecture) for system architecture
- Check [OpenAPI spec](./atman-engine-openapi.yaml) for API architecture

### For Operators

**Deployment:**
- Review [health check endpoint](./atman-engine-openapi.yaml#/paths/~1health/get)
- Configure [OpenTelemetry integration](../guides/atman-integration.md#3-integration-with-opentelemetry)
- Set up [hook-based monitoring](../guides/atman-engine-usage.md#2-audit-trail-hook)

**Performance:**
- Target: p99 <100ms for all operations
- Max batch size: 64 triples (Chatman Constant)
- See [performance section](../guides/atman-engine-usage.md#performance-optimization) for tuning

## Documentation Standards

All API documentation follows:
- **OpenAPI 3.0** specification for REST APIs
- **NumPy-style docstrings** for Python APIs
- **Executable examples** in all guides
- **Chicago School TDD** principles for test coverage

## Contributing

When adding new APIs:
1. Create OpenAPI specification (`.yaml`)
2. Write usage guide with examples (`.md`)
3. Add integration patterns (`.md`)
4. Update this README
5. Ensure 100% type coverage
6. Add comprehensive tests

## Support

- **GitHub Issues**: https://github.com/kgcl/kgcl/issues
- **Discussions**: https://github.com/kgcl/kgcl/discussions
- **Source Code**: `/src/kgcl/engine/`
- **Tests**: `/tests/engine/`
