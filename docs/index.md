# KGCL Documentation

Knowledge Geometry Calculus for Life - A local-first autonomic knowledge engine implementing all 43 YAWL Workflow Control Patterns in pure N3 rules.

---

## Documentation Quadrants

This documentation follows the [Diátaxis](https://diataxis.fr/) framework:

### [Tutorials](tutorials/index.md) - Learning-oriented

Get started with KGCL through hands-on learning.

- [Getting Started](tutorials/getting-started.md) - Your first KGCL workflow
- [CLI Quickstart](tutorials/cli-quickstart.md) - Command-line basics
- [Hook Integration](tutorials/hook-integration.md) - Build your first hook
- [First Workflow](tutorials/first-workflow.md) - Create a complete workflow

### [How-To Guides](how-to/index.md) - Task-oriented

Solve specific problems with step-by-step instructions.

- [Hooks Quick Reference](how-to/hooks-quick-reference.md) - Hook patterns
- [YAWL MI Quick Reference](how-to/yawl-mi-quick-reference.md) - Multiple instance patterns
- [Execution Templates](how-to/execution-templates-quick-reference.md) - Template usage
- [Git Hooks Quality Gates](how-to/git-hooks-quality.md) - CI/CD setup

### [Reference](reference/index.md) - Information-oriented

Technical specifications and API documentation.

- [API Reference](reference/api.md) - Python API
- [WCP Pattern Reference](reference/wcp-43-patterns.md) - All 43 patterns
- [Feature Catalog](reference/feature-catalog.md) - Available features
- [SPARQL Templates](reference/sparql-template-index.md) - Query templates

### [Explanation](explanation/index.md) - Understanding-oriented

Architecture, design decisions, and concepts.

- [Architecture Overview](explanation/architecture/index.md) - System design
- [Hybrid Engine](explanation/architecture/hybrid-engine.md) - PyOxigraph + EYE
- [Compiled Physics](explanation/architecture/compiled-physics.md) - N3 rules
- [WCP FMEA Analysis](explanation/wcp-fmea-analysis.md) - Pattern risk analysis

---

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Get started | [Tutorials](tutorials/index.md) |
| Implement a pattern | [How-To Guides](how-to/index.md) |
| Look up API details | [Reference](reference/index.md) |
| Understand the architecture | [Explanation](explanation/index.md) |

---

## Project Status

| Metric | Value |
|--------|-------|
| Tests | 541 passing |
| WCP Coverage | 30/43 pure N3 (70%) |
| N3 Laws | 17 implemented |
| Architecture | PyOxigraph + EYE |

---

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

**Hard Separation**: State (Oxigraph) and Logic (N3/EYE) strictly separated. Python orchestrates ticks only - NO workflow logic in Python.
