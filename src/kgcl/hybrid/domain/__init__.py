"""Domain layer for Hybrid Engine - Pure domain objects with no external dependencies.

This module contains immutable value objects that represent the core domain concepts
of the hybrid engine architecture. All types are frozen dataclasses for immutability.

Components
----------
PhysicsResult
    Result of applying physics (one tick of reasoning)
TaskStatus
    Enumeration of task lifecycle states with priority ordering
ConvergenceError
    Exception raised when system fails to reach fixed point
"""

from __future__ import annotations

from kgcl.hybrid.domain.exceptions import ConvergenceError, HybridEngineError, ReasonerError, StoreOperationError
from kgcl.hybrid.domain.physics_result import PhysicsResult
from kgcl.hybrid.domain.task_status import TaskStatus

__all__ = [
    "PhysicsResult",
    "TaskStatus",
    "ConvergenceError",
    "HybridEngineError",
    "ReasonerError",
    "StoreOperationError",
]
