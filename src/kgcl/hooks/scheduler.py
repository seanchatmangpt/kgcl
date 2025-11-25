"""Hook scheduler - Manages timed hook execution.

Parses cron expressions, schedules timed hooks, and executes them
at appointed times. Tracks execution history and supports manual triggers.

Chicago TDD Pattern:
    - Parse cron expressions from hooks.ttl
    - Schedule timed hooks (daily, weekly, etc.)
    - Execute at appointed times
    - Track execution history
    - Support manual override
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from croniter import croniter
from rdflib import Graph

from kgcl.hooks.loader import HookDefinition, HookLoader
from kgcl.hooks.orchestrator import ExecutionResult, HookOrchestrator
from kgcl.hooks.registry import HookRegistry

logger = logging.getLogger(__name__)


@dataclass
class ScheduledExecution:
    """Record of scheduled hook execution.

    Attributes
    ----------
        hook_name: Hook that was executed
        scheduled_time: When it was scheduled
        actual_time: When it actually executed
        result: Execution result
        skipped: Whether execution was skipped
        skip_reason: Why it was skipped (if applicable)
    """

    hook_name: str
    scheduled_time: datetime
    actual_time: datetime | None = None
    result: ExecutionResult | None = None
    skipped: bool = False
    skip_reason: str | None = None


class HookScheduler:
    """Manages timed hook execution with cron scheduling.

    Handles hooks with cron expressions (e.g., daily at 6am, Friday at 5pm).
    Executes hooks at scheduled times and tracks execution history.

    Example:
        >>> scheduler = HookScheduler(graph, orchestrator, registry)
        >>> scheduler.start()  # Start background scheduler
        >>>
        >>> # Wait for scheduled execution...
        >>>
        >>> history = scheduler.get_execution_history("DailyReviewHook")
        >>> print(f"Executed {len(history)} times")
        >>>
        >>> scheduler.stop()
    """

    def __init__(
        self, graph: Graph, orchestrator: HookOrchestrator, registry: HookRegistry
    ) -> None:
        """Initialize scheduler with orchestrator and registry.

        Args:
            graph: RDF graph
            orchestrator: Hook orchestrator for execution
            registry: Hook registry for hook discovery
        """
        self.graph = graph
        self.orchestrator = orchestrator
        self.registry = registry

        # Execution history: hook_name -> List[ScheduledExecution]
        self._history: dict[str, list[ScheduledExecution]] = {}

        # Background scheduler thread
        self._scheduler_thread: threading.Thread | None = None
        self._running = False
        self._check_interval = 60  # Check every minute

        logger.info("Hook scheduler initialized")

    def start(self) -> None:
        """Start background scheduler thread."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()

        logger.info("Hook scheduler started")

    def stop(self) -> None:
        """Stop background scheduler thread."""
        if not self._running:
            return

        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        logger.info("Hook scheduler stopped")

    def _run_scheduler(self) -> None:
        """Background scheduler loop."""
        logger.info("Scheduler loop started")

        while self._running:
            try:
                # Check for hooks to execute
                self._check_and_execute()

                # Sleep until next check
                time.sleep(self._check_interval)

            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                # Continue running

    def _check_and_execute(self) -> None:
        """Check timed hooks and execute if scheduled."""
        now = datetime.now()

        # Get all timed hooks
        timed_hooks = self.registry.get_timed_hooks()

        for registered_hook in timed_hooks:
            hook = registered_hook.definition

            try:
                if self._should_execute(hook, now):
                    logger.info(f"Executing scheduled hook: {hook.name}")
                    self._execute_scheduled_hook(hook, now)

            except Exception as e:
                logger.error(f"Failed to execute scheduled hook {hook.name}: {e}", exc_info=True)

    def _should_execute(self, hook: HookDefinition, now: datetime) -> bool:
        """Check if hook should execute at current time.

        Args:
            hook: Hook to check
            now: Current time

        Returns
        -------
            True if hook should execute
        """
        if not hook.cron_schedule:
            return False

        # Parse cron expression
        try:
            cron = croniter(hook.cron_schedule, now)
        except Exception as e:
            logger.error(f"Invalid cron expression for {hook.name}: {e}")
            return False

        # Get last execution time
        history = self._history.get(hook.name, [])
        last_execution = history[-1].actual_time if history else None

        # Check if it's time to execute
        if last_execution is None:
            # Never executed - check if we're past first scheduled time
            prev_time = cron.get_prev(datetime)
            return True

        # Check if enough time has passed since last execution
        next_time = cron.get_next(datetime)

        # Execute if we're past next scheduled time
        return now >= next_time

    def _execute_scheduled_hook(self, hook: HookDefinition, scheduled_time: datetime) -> None:
        """Execute a scheduled hook.

        Args:
            hook: Hook to execute
            scheduled_time: Scheduled execution time
        """
        actual_time = datetime.now()

        try:
            # Trigger event (use hook URI as event)
            event_type = str(hook.uri)
            result = self.orchestrator.trigger_event(
                event_type,
                event_data={"scheduled_time": scheduled_time.isoformat()},
                actor="scheduler",
            )

            # Record execution
            execution = ScheduledExecution(
                hook_name=hook.name,
                scheduled_time=scheduled_time,
                actual_time=actual_time,
                result=result,
            )

            if hook.name not in self._history:
                self._history[hook.name] = []
            self._history[hook.name].append(execution)

            logger.info(
                f"Scheduled hook {hook.name} executed successfully ({len(result.receipts)} effects)"
            )

        except Exception as e:
            # Record failed execution
            execution = ScheduledExecution(
                hook_name=hook.name,
                scheduled_time=scheduled_time,
                actual_time=actual_time,
                skipped=True,
                skip_reason=str(e),
            )

            if hook.name not in self._history:
                self._history[hook.name] = []
            self._history[hook.name].append(execution)

            logger.error(f"Failed to execute scheduled hook {hook.name}: {e}")

    def trigger_hook_manually(
        self, hook_name: str, event_data: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Manually trigger a timed hook outside its schedule.

        Args:
            hook_name: Hook to trigger
            event_data: Optional event data

        Returns
        -------
            ExecutionResult

        Raises
        ------
            ValueError: If hook not found or not a timed hook
        """
        # Find hook
        registered_hook = self.registry.get_hook(hook_name)

        if not registered_hook:
            raise ValueError(f"Hook {hook_name} not found")

        hook = registered_hook.definition

        if not hook.cron_schedule:
            raise ValueError(f"Hook {hook_name} is not a timed hook")

        # Execute
        now = datetime.now()
        result = self.orchestrator.trigger_event(
            str(hook.uri), event_data=event_data or {"manual_trigger": True}, actor="manual"
        )

        # Record execution
        execution = ScheduledExecution(
            hook_name=hook_name, scheduled_time=now, actual_time=now, result=result
        )

        if hook_name not in self._history:
            self._history[hook_name] = []
        self._history[hook_name].append(execution)

        logger.info(f"Manually triggered hook: {hook_name}")

        return result

    def get_execution_history(
        self, hook_name: str, limit: int | None = None
    ) -> list[ScheduledExecution]:
        """Get execution history for hook.

        Args:
            hook_name: Hook name
            limit: Maximum number of records to return

        Returns
        -------
            List of ScheduledExecution records
        """
        history = self._history.get(hook_name, [])

        if limit:
            return history[-limit:]

        return history

    def get_next_execution_time(self, hook_name: str) -> datetime | None:
        """Get next scheduled execution time for hook.

        Args:
            hook_name: Hook name

        Returns
        -------
            Next execution time or None
        """
        registered_hook = self.registry.get_hook(hook_name)

        if not registered_hook or not registered_hook.definition.cron_schedule:
            return None

        hook = registered_hook.definition

        try:
            cron = croniter(hook.cron_schedule, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Failed to parse cron for {hook_name}: {e}")
            return None

    def get_schedule_summary(self) -> dict[str, Any]:
        """Get summary of all scheduled hooks.

        Returns
        -------
            Dictionary with schedule information
        """
        timed_hooks = self.registry.get_timed_hooks()

        summary = {"total_timed_hooks": len(timed_hooks), "schedules": []}

        for registered_hook in timed_hooks:
            hook = registered_hook.definition
            next_time = self.get_next_execution_time(hook.name)
            history = self._history.get(hook.name, [])

            summary["schedules"].append(
                {
                    "hook_name": hook.name,
                    "cron_schedule": hook.cron_schedule,
                    "next_execution": next_time.isoformat() if next_time else None,
                    "execution_count": len(history),
                    "last_execution": history[-1].actual_time.isoformat() if history else None,
                }
            )

        return summary

    def clear_history(self, hook_name: str | None = None) -> None:
        """Clear execution history.

        Args:
            hook_name: Hook to clear history for, or None for all
        """
        if hook_name:
            if hook_name in self._history:
                del self._history[hook_name]
                logger.info(f"Cleared history for {hook_name}")
        else:
            self._history.clear()
            logger.info("Cleared all execution history")
