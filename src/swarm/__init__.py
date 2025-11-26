"""Swarm Test Orchestration.

Provides test coordination, parallel execution, and distributed test management.
Inspired by Chicago TDD tools' swarm coordination patterns.
"""

from .composition import CompositionBuilder, CompositionStrategy
from .coordinator import SwarmCoordinator
from .member import SwarmMember
from .task import SwarmTask, TaskResult, TaskStatus

__all__ = [
    "CompositionBuilder",
    "CompositionStrategy",
    "SwarmCoordinator",
    "SwarmMember",
    "SwarmTask",
    "TaskResult",
    "TaskStatus",
]
