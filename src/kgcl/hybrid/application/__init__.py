"""Application layer - Use cases for the hybrid engine.

This module contains the application-level logic that orchestrates
the domain objects and adapters to implement the hybrid engine use cases.

Use Cases
---------
TickExecutor
    Execute a single tick of physics application (original architecture)
ConvergenceRunner
    Run physics to completion (fixed point)
StatusInspector
    Query and analyze task statuses
HybridOrchestrator
    Execute ticks with thesis architecture (100% WCP-43 coverage)

Design
------
Application services depend on ports (not adapters), enabling
easy testing with mock implementations.

Thesis Architecture
-------------------
HybridOrchestrator implements the complete hybrid architecture:
1. Transaction begin (snapshot for rollback)
2. Precondition validation (SHACL)
3. Inference (EYE produces recommendations)
4. Mutation (SPARQL UPDATE executes recommendations)
5. Postcondition validation (SHACL)
6. Commit or rollback
"""

from __future__ import annotations

from kgcl.hybrid.application.convergence_runner import ConvergenceRunner
from kgcl.hybrid.application.hybrid_orchestrator import (
    HybridOrchestrator,
    OrchestratorConfig,
    TickOutcome,
    create_orchestrator,
)
from kgcl.hybrid.application.status_inspector import StatusInspector
from kgcl.hybrid.application.tick_executor import TickExecutor

__all__ = [
    # Original use cases
    "TickExecutor",
    "ConvergenceRunner",
    "StatusInspector",
    # Thesis architecture orchestrator
    "HybridOrchestrator",
    "OrchestratorConfig",
    "TickOutcome",
    "create_orchestrator",
]
