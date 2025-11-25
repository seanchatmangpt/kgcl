"""Test Tasks for Swarm Execution

Represents units of work that can be executed by swarm members.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Status of a task"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestTask:
    """Represents a test task

    Example:
        task = TestTask(
            name="test_api",
            task_type="integration_test",
            payload={"endpoint": "/users"}
        )
    """

    name: str
    task_type: str = "generic"
    payload: dict[str, Any] | None = None
    priority: int = 0
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)

    def with_payload(self, key: str, value: Any) -> "TestTask":
        """Add to task payload (fluent interface)"""
        if self.payload is None:
            self.payload = {}
        self.payload[key] = value
        return self

    def get_payload(self, key: str, default: Any = None) -> Any:
        """Get payload value"""
        if self.payload is None:
            return default
        return self.payload.get(key, default)

    def __repr__(self) -> str:
        return (
            f"TestTask(id={self.task_id!r}, name={self.name!r}, "
            f"type={self.task_type!r}, priority={self.priority})"
        )


@dataclass
class TaskResult:
    """Result of task execution"""

    task_name: str
    status: TaskStatus
    output: Any | None = None
    error: str | None = None
    exception: Exception | None = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    duration_ms: float = 0.0

    def is_success(self) -> bool:
        """Check if task succeeded"""
        return self.status == TaskStatus.SUCCESS

    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == TaskStatus.FAILED

    def is_skipped(self) -> bool:
        """Check if task was skipped"""
        return self.status == TaskStatus.SKIPPED

    def mark_complete(self) -> None:
        """Mark task as completed"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def __repr__(self) -> str:
        return (
            f"TaskResult(task={self.task_name!r}, "
            f"status={self.status.value}, "
            f"duration={self.duration_ms:.1f}ms)"
        )
