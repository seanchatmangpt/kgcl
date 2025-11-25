"""Swarm Test Orchestration

Provides test coordination, parallel execution, and distributed test management.
Inspired by Chicago TDD tools' swarm coordination patterns.
"""

from .composition import CompositionStrategy, TestComposition
from .coordinator import TestCoordinator
from .member import SwarmMember
from .task import TaskResult, TaskStatus, TestTask

__all__ = [
    "CompositionStrategy",
    "SwarmMember",
    "TaskResult",
    "TaskStatus",
    "TestComposition",
    "TestCoordinator",
    "TestTask",
]
