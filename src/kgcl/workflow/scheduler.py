"""Workflow scheduler for automated StandardWorkLoop execution.

Supports:
- Daily/weekly scheduled execution
- Background thread execution
- State persistence across restarts
- Manual trigger override
- Workflow history tracking
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Event, Thread
from typing import Any

from .orchestrator import StandardWorkLoop
from .state import WorkflowState


class ScheduleType(Enum):
    """Workflow schedule types."""

    ONCE = "once"  # Run once at specific time
    DAILY = "daily"  # Run every day at specific time
    WEEKLY = "weekly"  # Run weekly on specific day/time
    INTERVAL = "interval"  # Run at fixed intervals


@dataclass
class ScheduleConfig:
    """Configuration for workflow scheduling."""

    schedule_type: ScheduleType
    time_of_day: time | None = None  # For DAILY/WEEKLY
    day_of_week: int | None = None  # For WEEKLY (0=Monday, 6=Sunday)
    interval_hours: int | None = None  # For INTERVAL
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "schedule_type": self.schedule_type.value,
            "time_of_day": self.time_of_day.isoformat() if self.time_of_day else None,
            "day_of_week": self.day_of_week,
            "interval_hours": self.interval_hours,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleConfig":
        """Create from JSON dict."""
        time_str = data.get("time_of_day")
        return cls(
            schedule_type=ScheduleType(data["schedule_type"]),
            time_of_day=time.fromisoformat(time_str) if time_str else None,
            day_of_week=data.get("day_of_week"),
            interval_hours=data.get("interval_hours"),
            enabled=data.get("enabled", True),
        )


@dataclass
class WorkflowExecution:
    """Record of a workflow execution."""

    workflow_id: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    triggered_by: str = "scheduler"  # or "manual"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "workflow_id": self.workflow_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "success": self.success,
            "triggered_by": self.triggered_by,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowExecution":
        """Create from JSON dict."""
        completed_str = data.get("completed_at")
        return cls(
            workflow_id=data["workflow_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(completed_str)
            if completed_str
            else None,
            success=data.get("success", False),
            triggered_by=data.get("triggered_by", "scheduler"),
            error=data.get("error"),
        )


class WorkflowScheduler:
    """Schedules and executes StandardWorkLoop workflows.

    Runs in background thread, supports multiple schedule types,
    persists execution history, and allows manual triggers.
    """

    def __init__(
        self,
        orchestrator: StandardWorkLoop,
        schedule_config: ScheduleConfig,
        history_dir: Path | None = None,
    ):
        """Initialize scheduler.

        Args:
            orchestrator: StandardWorkLoop to execute
            schedule_config: Schedule configuration
            history_dir: Directory for execution history (default: .kgcl/history)
        """
        self.orchestrator = orchestrator
        self.config = schedule_config
        self.history_dir = history_dir or Path.cwd() / ".kgcl" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self._thread: Thread | None = None
        self._stop_event = Event()
        self._last_execution: datetime | None = None
        self._executions: list[WorkflowExecution] = []

        # Load execution history
        self._load_history()

    def start(self) -> None:
        """Start scheduler background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop scheduler background thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def trigger_manual(self) -> WorkflowState:
        """Manually trigger workflow execution.

        Returns
        -------
            WorkflowState from execution
        """
        execution = WorkflowExecution(
            workflow_id=f"manual-{datetime.now(UTC).isoformat()}",
            started_at=datetime.now(UTC),
            triggered_by="manual",
        )

        try:
            state = self.orchestrator.execute(workflow_id=execution.workflow_id)
            execution.completed_at = datetime.now(UTC)
            execution.success = not state.failed

            if state.failed:
                execution.error = "; ".join(state.all_errors)

            self._executions.append(execution)
            self._save_history()
            return state

        except Exception as e:
            execution.completed_at = datetime.now(UTC)
            execution.error = str(e)
            self._executions.append(execution)
            self._save_history()
            raise

    def get_history(self, limit: int = 10) -> list[WorkflowExecution]:
        """Get recent execution history.

        Args:
            limit: Maximum number of executions to return

        Returns
        -------
            List of WorkflowExecution records, newest first
        """
        return sorted(self._executions, key=lambda e: e.started_at, reverse=True)[
            :limit
        ]

    def get_next_execution_time(self) -> datetime | None:
        """Calculate next scheduled execution time.

        Returns
        -------
            Next execution datetime, or None if not scheduled
        """
        if not self.config.enabled:
            return None

        now = datetime.now(UTC)

        if self.config.schedule_type == ScheduleType.ONCE:
            # Already executed
            if self._last_execution:
                return None
            # Schedule for next occurrence of time_of_day
            if self.config.time_of_day:
                next_time = now.replace(
                    hour=self.config.time_of_day.hour,
                    minute=self.config.time_of_day.minute,
                    second=0,
                    microsecond=0,
                )
                if next_time <= now:
                    next_time += timedelta(days=1)
                return next_time

        elif self.config.schedule_type == ScheduleType.DAILY:
            if not self.config.time_of_day:
                return None

            next_time = now.replace(
                hour=self.config.time_of_day.hour,
                minute=self.config.time_of_day.minute,
                second=0,
                microsecond=0,
            )

            # If already passed today, schedule for tomorrow
            if next_time <= now:
                next_time += timedelta(days=1)

            return next_time

        elif self.config.schedule_type == ScheduleType.WEEKLY:
            if not self.config.time_of_day or self.config.day_of_week is None:
                return None

            # Calculate days until target day of week
            current_day = now.weekday()
            target_day = self.config.day_of_week
            days_ahead = (target_day - current_day) % 7

            next_time = now.replace(
                hour=self.config.time_of_day.hour,
                minute=self.config.time_of_day.minute,
                second=0,
                microsecond=0,
            ) + timedelta(days=days_ahead)

            # If already passed this week, schedule for next week
            if next_time <= now:
                next_time += timedelta(weeks=1)

            return next_time

        elif self.config.schedule_type == ScheduleType.INTERVAL:
            if not self.config.interval_hours:
                return None

            if self._last_execution:
                return self._last_execution + timedelta(
                    hours=self.config.interval_hours
                )
            return now

        return None

    def _run_loop(self) -> None:
        """Background thread execution loop."""
        while not self._stop_event.is_set():
            if not self.config.enabled:
                self._stop_event.wait(timeout=60)  # Check every minute
                continue

            next_execution = self.get_next_execution_time()
            if not next_execution:
                self._stop_event.wait(timeout=60)
                continue

            now = datetime.now(UTC)
            if now >= next_execution:
                # Execute workflow
                self._execute_scheduled()

            # Wait until next check (every minute)
            self._stop_event.wait(timeout=60)

    def _execute_scheduled(self) -> None:
        """Execute scheduled workflow."""
        execution = WorkflowExecution(
            workflow_id=f"scheduled-{datetime.now(UTC).isoformat()}",
            started_at=datetime.now(UTC),
            triggered_by="scheduler",
        )

        try:
            state = self.orchestrator.execute(workflow_id=execution.workflow_id)
            execution.completed_at = datetime.now(UTC)
            execution.success = not state.failed

            if state.failed:
                execution.error = "; ".join(state.all_errors)

            self._last_execution = datetime.now(UTC)

        except Exception as e:
            execution.completed_at = datetime.now(UTC)
            execution.error = str(e)

        finally:
            self._executions.append(execution)
            self._save_history()

    def _save_history(self) -> None:
        """Persist execution history to disk."""
        history_file = self.history_dir / "executions.json"
        data = {
            "last_execution": self._last_execution.isoformat()
            if self._last_execution
            else None,
            "executions": [e.to_dict() for e in self._executions],
        }
        with history_file.open("w") as f:
            json.dump(data, f, indent=2)

    def _load_history(self) -> None:
        """Load execution history from disk."""
        history_file = self.history_dir / "executions.json"
        if not history_file.exists():
            return

        with history_file.open("r") as f:
            data = json.load(f)

        last_exec = data.get("last_execution")
        if last_exec:
            self._last_execution = datetime.fromisoformat(last_exec)

        self._executions = [
            WorkflowExecution.from_dict(e) for e in data.get("executions", [])
        ]

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def status(self) -> dict[str, Any]:
        """Get scheduler status.

        Returns
        -------
            Dictionary with scheduler state
        """
        return {
            "enabled": self.config.enabled,
            "running": self.is_running,
            "schedule_type": self.config.schedule_type.value,
            "last_execution": self._last_execution.isoformat()
            if self._last_execution
            else None,
            "next_execution": self.get_next_execution_time().isoformat()
            if self.get_next_execution_time()
            else None,
            "total_executions": len(self._executions),
            "successful_executions": sum(1 for e in self._executions if e.success),
        }
