"""Swarm Member - Individual test executor.

Represents a single member of a test swarm.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .task import SwarmTask, TaskResult, TaskStatus


@dataclass
class MemberMetadata:
    """Metadata about a swarm member."""

    member_id: str
    name: str
    created_at: datetime
    tasks_executed: int = 0
    tasks_failed: int = 0


class SwarmMember:
    """Individual member of a test swarm.

    Executes tasks and reports results back to coordinator.

    Example:
        member = SwarmMember("test-worker-1")
        task = SwarmTask("unit_test")
        result = member.execute_task(task)
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._metadata = MemberMetadata(
            member_id=str(uuid.uuid4())[:8], name=name, created_at=datetime.now()
        )
        self._task_handlers: dict[str, Callable[[SwarmTask], TaskResult]] = {}
        self._state: dict[str, Any] = {}

    def name(self) -> str:
        """Get member name."""
        return self._name

    def metadata(self) -> MemberMetadata:
        """Get member metadata."""
        return self._metadata

    def register_handler(
        self, task_type: str, handler: Callable[[SwarmTask], TaskResult]
    ) -> None:
        """Register handler for task type.

        Args:
            task_type: Type of task (e.g., "unit_test", "integration_test")
            handler: Callable that executes the task
        """
        self._task_handlers[task_type] = handler

    def execute_task(self, task: SwarmTask) -> TaskResult:
        """Execute a task.

        Args:
            task: Task to execute

        Returns
        -------
            TaskResult with execution outcome

        Raises
        ------
            ValueError: If no handler registered for task type
        """
        if task.task_type not in self._task_handlers:
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.FAILED,
                error=f"No handler registered for task type: {task.task_type}",
            )

        try:
            handler = self._task_handlers[task.task_type]
            result = handler(task)
            self._metadata.tasks_executed += 1
            return result
        except Exception as e:
            self._metadata.tasks_failed += 1
            return TaskResult(
                task_name=task.name, status=TaskStatus.FAILED, error=str(e), exception=e
            )

    def set_state(self, key: str, value: Any) -> None:
        """Set state value."""
        self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self._state.get(key, default)

    def reset_state(self) -> None:
        """Clear all state."""
        self._state.clear()

    def __repr__(self) -> str:
        return (
            f"SwarmMember(name={self._name!r}, "
            f"id={self._metadata.member_id!r}, "
            f"executed={self._metadata.tasks_executed})"
        )
