"""Test Coordinator for Swarm Management

Orchestrates multiple test members and coordinates their execution.
"""

from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .member import SwarmMember
from .task import TestTask, TaskResult, TaskStatus


@dataclass
class CoordinationMetrics:
    """Metrics about coordination"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100


class TestCoordinator:
    """Coordinates execution of test swarms

    Manages multiple test members, distributes tasks, and collects results.

    Example:
        coordinator = TestCoordinator(max_workers=4)
        coordinator.register_member(test_member_1)
        coordinator.register_member(test_member_2)

        task = TestTask("integration_test")
        results = coordinator.execute(task)
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._members: Dict[str, SwarmMember] = {}
        self._max_workers = max_workers
        self._current_task: Optional[TestTask] = None
        self._task_history: List[tuple[TestTask, TaskResult]] = []
        self._metrics = CoordinationMetrics()
        self._id = str(uuid.uuid4())[:8]

    def register_member(self, member: SwarmMember) -> None:
        """Register a test member with the coordinator"""
        self._members[member.name()] = member

    def unregister_member(self, member_name: str) -> bool:
        """Unregister a test member"""
        if member_name in self._members:
            del self._members[member_name]
            return True
        return False

    def member_count(self) -> int:
        """Get number of registered members"""
        return len(self._members)

    def members(self) -> List[SwarmMember]:
        """Get all registered members"""
        return list(self._members.values())

    def execute(self, task: TestTask) -> Dict[str, TaskResult]:
        """Execute task across all members

        Args:
            task: The task to execute

        Returns:
            Dictionary mapping member names to TaskResults
        """
        self._current_task = task
        self._metrics.total_tasks += 1
        if self._metrics.start_time is None:
            self._metrics.start_time = datetime.now()

        results: Dict[str, TaskResult] = {}

        for member in self._members.values():
            try:
                result = member.execute_task(task)
                results[member.name()] = result

                if result.status == TaskStatus.SUCCESS:
                    self._metrics.completed_tasks += 1
                else:
                    self._metrics.failed_tasks += 1

                self._task_history.append((task, result))
            except Exception as e:
                result = TaskResult(
                    task_name=task.name,
                    status=TaskStatus.FAILED,
                    error=str(e)
                )
                results[member.name()] = result
                self._metrics.failed_tasks += 1

        self._metrics.end_time = datetime.now()
        if self._metrics.end_time and self._metrics.start_time:
            duration = (self._metrics.end_time - self._metrics.start_time).total_seconds()
            if self._metrics.total_tasks > 0:
                self._metrics.avg_duration = duration / self._metrics.total_tasks

        return results

    def metrics(self) -> CoordinationMetrics:
        """Get coordination metrics"""
        return self._metrics

    def task_history(self) -> List[tuple[TestTask, TaskResult]]:
        """Get task execution history"""
        return self._task_history.copy()

    def clear_history(self) -> None:
        """Clear task history"""
        self._task_history.clear()

    def __repr__(self) -> str:
        return (
            f"TestCoordinator(id={self._id!r}, members={len(self._members)}, "
            f"max_workers={self._max_workers})"
        )
