"""Application layer - Use cases for the hybrid engine.

This module contains the application-level logic that orchestrates
the domain objects and adapters to implement the hybrid engine use cases.

Use Cases
---------
TickExecutor
    Execute a single tick of physics application
ConvergenceRunner
    Run physics to completion (fixed point)
StatusInspector
    Query and analyze task statuses

Design
------
Application services depend on ports (not adapters), enabling
easy testing with mock implementations.
"""

from __future__ import annotations

from kgcl.hybrid.application.convergence_runner import ConvergenceRunner
from kgcl.hybrid.application.status_inspector import StatusInspector
from kgcl.hybrid.application.tick_executor import TickExecutor

__all__ = ["TickExecutor", "ConvergenceRunner", "StatusInspector"]
