"""KGCL: Knowledge Geometry Calculus for Life.

A local-first, autonomic knowledge system that observes macOS/iOS behavior,
formalizes it as a knowledge graph, and uses DSPy + Ollama for reasoning.

Architecture:
    PyObjC Agent → UNRDF Engine → Feature Materialization → TTL2DSPy → DSPy/Ollama

Components:
    - pyobjc_agent: Observes macOS/iOS capabilities and events
    - unrdf_engine: Manages RDF knowledge graph with hooks
    - ttl2dspy: Generates DSPy signatures from SHACL ontologies
    - dspy_runtime: Executes reasoning via DSPy + Ollama
    - ingestion: Event collection and feature computation
    - cli: User-facing command-line tools
    - signatures: Pre-built DSPy signatures for common tasks
    - observability: OpenTelemetry instrumentation

Example:
    from kgcl.cli.daily_brief import generate_daily_brief
    brief = generate_daily_brief(days_back=1)
    print(brief)
"""

__version__ = "0.1.0"
__author__ = "KGCL Team"
__all__ = [
    "cli",
    "dspy_runtime",
    "ingestion",
    "observability",
    "pyobjc_agent",
    "signatures",
    "ttl2dspy",
    "unrdf_engine",
]
