"""Swarm Test Orchestration

Provides test coordination, parallel execution, and distributed test management.
Inspired by Chicago TDD tools' swarm coordination patterns.
"""

from .coordinator import TestCoordinator
from .member import SwarmMember
from .task import TestTask, TaskResult, TaskStatus
from .composition import TestComposition, CompositionStrategy

__all__ = [
    "TestCoordinator",
    "SwarmMember",
    "TestTask",
    "TaskResult",
    "TaskStatus",
    "TestComposition",
    "CompositionStrategy",
]
