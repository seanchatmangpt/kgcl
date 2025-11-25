"""Swarm Test Orchestration

Provides test coordination, parallel execution, and distributed test management.
Inspired by Chicago TDD tools' swarm coordination patterns.
"""

from .coordinator import TestCoordinator
from .member import SwarmMember
from .task import TestTask, TaskResult
from .composition import TestComposition

__all__ = [
    "TestCoordinator",
    "SwarmMember",
    "TestTask",
    "TaskResult",
    "TestComposition",
]
