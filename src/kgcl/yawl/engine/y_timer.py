"""Timer and deadline support (mirrors Java timer service).

Provides timer functionality for work items and tasks including
expiry actions and deadline monitoring.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_work_item import YWorkItem


class TimerTrigger(Enum):
    """When a timer starts counting.

    Attributes
    ----------
    ON_ENABLED : auto
        Timer starts when task is enabled
    ON_OFFERED : auto
        Timer starts when work item is offered
    ON_ALLOCATED : auto
        Timer starts when work item is allocated
    ON_STARTED : auto
        Timer starts when work item is started
    """

    ON_ENABLED = auto()
    ON_OFFERED = auto()
    ON_ALLOCATED = auto()
    ON_STARTED = auto()


class TimerAction(Enum):
    """Action to take when timer expires.

    Attributes
    ----------
    NOTIFY : auto
        Send notification
    REASSIGN : auto
        Reassign work item
    ESCALATE : auto
        Escalate to manager
    COMPLETE : auto
        Auto-complete work item
    FAIL : auto
        Fail the work item
    CANCEL : auto
        Cancel the work item
    """

    NOTIFY = auto()
    REASSIGN = auto()
    ESCALATE = auto()
    COMPLETE = auto()
    FAIL = auto()
    CANCEL = auto()


@dataclass
class YTimer:
    """Timer for work item or task (mirrors Java timer handling).

    Parameters
    ----------
    id : str
        Unique identifier
    work_item_id : str
        Associated work item ID
    trigger : TimerTrigger
        When timer starts
    duration : timedelta
        Duration until expiry
    action : TimerAction
        Action on expiry
    started : datetime | None
        When timer started
    expiry : datetime | None
        Computed expiry time
    expired : bool
        Whether timer has expired
    cancelled : bool
        Whether timer was cancelled
    action_data : dict[str, Any]
        Data for the action

    Examples
    --------
    >>> timer = YTimer(
    ...     id="t1",
    ...     work_item_id="wi-001",
    ...     trigger=TimerTrigger.ON_STARTED,
    ...     duration=timedelta(hours=1),
    ...     action=TimerAction.NOTIFY,
    ... )
    """

    id: str
    work_item_id: str
    trigger: TimerTrigger = TimerTrigger.ON_ENABLED
    duration: timedelta = timedelta(hours=1)
    action: TimerAction = TimerAction.NOTIFY

    # State
    started: datetime | None = None
    expiry: datetime | None = None
    expired: bool = False
    cancelled: bool = False

    # Action data
    action_data: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Start the timer."""
        self.started = datetime.now()
        self.expiry = self.started + self.duration

    def cancel(self) -> None:
        """Cancel the timer."""
        self.cancelled = True

    def check_expiry(self) -> bool:
        """Check if timer has expired.

        Returns
        -------
        bool
            True if expired
        """
        if self.cancelled or self.expired:
            return False
        if self.expiry and datetime.now() > self.expiry:
            self.expired = True
            return True
        return False

    def get_remaining_time(self) -> timedelta | None:
        """Get remaining time until expiry.

        Returns
        -------
        timedelta | None
            Remaining time or None if expired/cancelled
        """
        if self.cancelled or self.expired or self.expiry is None:
            return None
        remaining = self.expiry - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def is_active(self) -> bool:
        """Check if timer is active.

        Returns
        -------
        bool
            True if running and not expired/cancelled
        """
        return self.started is not None and not self.cancelled and not self.expired


@dataclass
class YDeadline:
    """Deadline for a work item or case.

    A deadline is an absolute time by which work must be completed,
    as opposed to a timer which is a relative duration.

    Parameters
    ----------
    id : str
        Unique identifier
    work_item_id : str | None
        Associated work item ID
    case_id : str | None
        Associated case ID
    deadline : datetime
        Absolute deadline time
    action : TimerAction
        Action on deadline breach
    warning_before : timedelta | None
        Time before deadline to warn
    warning_sent : bool
        Whether warning was sent
    breached : bool
        Whether deadline was breached
    action_data : dict[str, Any]
        Data for the action

    Examples
    --------
    >>> deadline = YDeadline(
    ...     id="d1",
    ...     work_item_id="wi-001",
    ...     deadline=datetime(2024, 12, 31, 17, 0, 0),
    ...     warning_before=timedelta(hours=24),
    ... )
    """

    id: str
    work_item_id: str | None = None
    case_id: str | None = None
    deadline: datetime = field(default_factory=datetime.now)
    action: TimerAction = TimerAction.NOTIFY

    # Warning
    warning_before: timedelta | None = None
    warning_sent: bool = False

    # State
    breached: bool = False

    # Action data
    action_data: dict[str, Any] = field(default_factory=dict)

    def check_warning(self) -> bool:
        """Check if warning should be sent.

        Returns
        -------
        bool
            True if warning time reached and not yet sent
        """
        if self.warning_sent or self.warning_before is None:
            return False
        warning_time = self.deadline - self.warning_before
        if datetime.now() > warning_time:
            self.warning_sent = True
            return True
        return False

    def check_breach(self) -> bool:
        """Check if deadline was breached.

        Returns
        -------
        bool
            True if breached
        """
        if self.breached:
            return False
        if datetime.now() > self.deadline:
            self.breached = True
            return True
        return False

    def get_time_remaining(self) -> timedelta | None:
        """Get time remaining until deadline.

        Returns
        -------
        timedelta | None
            Remaining time or None if breached
        """
        if self.breached:
            return None
        remaining = self.deadline - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


def parse_duration(duration_str: str) -> timedelta:
    """Parse ISO 8601 duration string.

    Parameters
    ----------
    duration_str : str
        Duration string (e.g., "PT1H30M", "P1D")

    Returns
    -------
    timedelta
        Parsed duration

    Examples
    --------
    >>> parse_duration("PT1H")
    datetime.timedelta(seconds=3600)
    >>> parse_duration("P1D")
    datetime.timedelta(days=1)
    """
    # Simple ISO 8601 duration parser
    pattern = r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


@dataclass
class YTimerService:
    """Service for managing timers and deadlines (mirrors Java timer service).

    The timer service monitors active timers and deadlines, triggering
    actions when they expire.

    Parameters
    ----------
    timers : dict[str, YTimer]
        Active timers by ID
    deadlines : dict[str, YDeadline]
        Active deadlines by ID
    timer_handlers : dict[TimerAction, Callable[[YTimer], None]]
        Handlers for timer actions
    deadline_handlers : dict[TimerAction, Callable[[YDeadline], None]]
        Handlers for deadline actions
    check_interval : float
        Seconds between expiry checks
    running : bool
        Whether service is running
    _check_thread : threading.Thread | None
        Background check thread

    Examples
    --------
    >>> service = YTimerService()
    >>> service.start()
    >>> service.add_timer(timer)
    """

    timers: dict[str, YTimer] = field(default_factory=dict)
    deadlines: dict[str, YDeadline] = field(default_factory=dict)

    # Action handlers
    timer_handlers: dict[TimerAction, Callable[[YTimer], None]] = field(default_factory=dict)
    deadline_handlers: dict[TimerAction, Callable[[YDeadline], None]] = field(default_factory=dict)

    # Configuration
    check_interval: float = 1.0

    # State
    running: bool = False
    _check_thread: threading.Thread | None = field(default=None, repr=False)

    def start(self) -> None:
        """Start the timer service."""
        self.running = True
        self._check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self._check_thread.start()

    def stop(self) -> None:
        """Stop the timer service."""
        self.running = False
        if self._check_thread:
            self._check_thread.join(timeout=2.0)

    def _check_loop(self) -> None:
        """Background loop to check timers and deadlines."""
        import time

        while self.running:
            self._check_all_timers()
            self._check_all_deadlines()
            time.sleep(self.check_interval)

    def _check_all_timers(self) -> None:
        """Check all timers for expiry."""
        for timer in list(self.timers.values()):
            if timer.check_expiry():
                self._handle_timer_expiry(timer)

    def _check_all_deadlines(self) -> None:
        """Check all deadlines."""
        for deadline in list(self.deadlines.values()):
            # Check warning
            if deadline.check_warning():
                self._handle_deadline_warning(deadline)
            # Check breach
            if deadline.check_breach():
                self._handle_deadline_breach(deadline)

    def _handle_timer_expiry(self, timer: YTimer) -> None:
        """Handle timer expiry.

        Parameters
        ----------
        timer : YTimer
            Expired timer
        """
        handler = self.timer_handlers.get(timer.action)
        if handler:
            try:
                handler(timer)
            except Exception:
                pass

    def _handle_deadline_warning(self, deadline: YDeadline) -> None:
        """Handle deadline warning.

        Parameters
        ----------
        deadline : YDeadline
            Deadline with warning
        """
        handler = self.deadline_handlers.get(TimerAction.NOTIFY)
        if handler:
            try:
                # Create a "pseudo-deadline" for the warning
                warning_deadline = YDeadline(
                    id=f"{deadline.id}_warning",
                    work_item_id=deadline.work_item_id,
                    case_id=deadline.case_id,
                    action=TimerAction.NOTIFY,
                    action_data={"warning": True, **deadline.action_data},
                )
                handler(warning_deadline)
            except Exception:
                pass

    def _handle_deadline_breach(self, deadline: YDeadline) -> None:
        """Handle deadline breach.

        Parameters
        ----------
        deadline : YDeadline
            Breached deadline
        """
        handler = self.deadline_handlers.get(deadline.action)
        if handler:
            try:
                handler(deadline)
            except Exception:
                pass

    def add_timer(self, timer: YTimer) -> None:
        """Add timer.

        Parameters
        ----------
        timer : YTimer
            Timer to add
        """
        self.timers[timer.id] = timer

    def remove_timer(self, timer_id: str) -> bool:
        """Remove timer.

        Parameters
        ----------
        timer_id : str
            Timer ID

        Returns
        -------
        bool
            True if removed
        """
        if timer_id in self.timers:
            del self.timers[timer_id]
            return True
        return False

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel timer.

        Parameters
        ----------
        timer_id : str
            Timer ID

        Returns
        -------
        bool
            True if cancelled
        """
        timer = self.timers.get(timer_id)
        if timer:
            timer.cancel()
            return True
        return False

    def add_deadline(self, deadline: YDeadline) -> None:
        """Add deadline.

        Parameters
        ----------
        deadline : YDeadline
            Deadline to add
        """
        self.deadlines[deadline.id] = deadline

    def remove_deadline(self, deadline_id: str) -> bool:
        """Remove deadline.

        Parameters
        ----------
        deadline_id : str
            Deadline ID

        Returns
        -------
        bool
            True if removed
        """
        if deadline_id in self.deadlines:
            del self.deadlines[deadline_id]
            return True
        return False

    def get_timers_for_work_item(self, work_item_id: str) -> list[YTimer]:
        """Get timers for a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        list[YTimer]
            Timers for work item
        """
        return [t for t in self.timers.values() if t.work_item_id == work_item_id]

    def get_deadlines_for_work_item(self, work_item_id: str) -> list[YDeadline]:
        """Get deadlines for a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        list[YDeadline]
            Deadlines for work item
        """
        return [d for d in self.deadlines.values() if d.work_item_id == work_item_id]

    def set_timer_handler(self, action: TimerAction, handler: Callable[[YTimer], None]) -> None:
        """Set handler for timer action.

        Parameters
        ----------
        action : TimerAction
            Action type
        handler : Callable[[YTimer], None]
            Handler function
        """
        self.timer_handlers[action] = handler

    def set_deadline_handler(self, action: TimerAction, handler: Callable[[YDeadline], None]) -> None:
        """Set handler for deadline action.

        Parameters
        ----------
        action : TimerAction
            Action type
        handler : Callable[[YDeadline], None]
            Handler function
        """
        self.deadline_handlers[action] = handler

    def create_timer_for_work_item(
        self,
        work_item_id: str,
        duration: timedelta | str,
        trigger: TimerTrigger = TimerTrigger.ON_ENABLED,
        action: TimerAction = TimerAction.NOTIFY,
    ) -> YTimer:
        """Create and start a timer for a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        duration : timedelta | str
            Duration (timedelta or ISO 8601 string)
        trigger : TimerTrigger
            When timer starts
        action : TimerAction
            Action on expiry

        Returns
        -------
        YTimer
            Created timer
        """
        if isinstance(duration, str):
            duration = parse_duration(duration)

        timer = YTimer(
            id=f"timer_{work_item_id}_{len(self.timers)}",
            work_item_id=work_item_id,
            trigger=trigger,
            duration=duration,
            action=action,
        )
        timer.start()
        self.add_timer(timer)
        return timer
