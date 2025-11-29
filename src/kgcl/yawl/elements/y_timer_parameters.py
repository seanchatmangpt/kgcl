"""Timer parameters for tasks (mirrors Java YTimerParameters).

Timer parameters define when and how timers are configured for tasks,
supporting duration, expiry, interval, and late-bound (variable) timers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any
from xml.etree import ElementTree as ET

from kgcl.yawl.engine.y_timer import TimerTrigger
from kgcl.yawl.engine.y_work_item import WorkItemStatus


class TimerType(Enum):
    """Type of timer parameter.

    Attributes
    ----------
    DURATION : auto
        Duration-based timer (e.g., "P1D" for 1 day)
    EXPIRY : auto
        Absolute expiry time
    INTERVAL : auto
        Interval-based timer (ticks + time unit)
    LATE_BOUND : auto
        Late-bound to net variable
    NIL : auto
        No timer configured
    """

    DURATION = auto()
    EXPIRY = auto()
    INTERVAL = auto()
    LATE_BOUND = auto()
    NIL = auto()


class TimeUnit(Enum):
    """Time unit for interval timers.

    Attributes
    ----------
    MSEC : auto
        Milliseconds
    SEC : auto
        Seconds
    MIN : auto
        Minutes
    HOUR : auto
        Hours
    DAY : auto
        Days
    """

    MSEC = auto()
    SEC = auto()
    MIN = auto()
    HOUR = auto()
    DAY = auto()

    def to_timedelta(self, ticks: int) -> timedelta:
        """Convert ticks to timedelta.

        Parameters
        ----------
        ticks : int
            Number of time units

        Returns
        -------
        timedelta
            Equivalent timedelta
        """
        match self:
            case TimeUnit.MSEC:
                return timedelta(milliseconds=ticks)
            case TimeUnit.SEC:
                return timedelta(seconds=ticks)
            case TimeUnit.MIN:
                return timedelta(minutes=ticks)
            case TimeUnit.HOUR:
                return timedelta(hours=ticks)
            case TimeUnit.DAY:
                return timedelta(days=ticks)


@dataclass
class YTimerParameters:
    """Timer parameters for a task (mirrors Java YTimerParameters).

    Parameters
    ----------
    timer_type : TimerType
        Type of timer
    trigger : TimerTrigger | None
        When timer starts
    variable_name : str | None
        Late-bound net variable name
    expiry_time : datetime | None
        Absolute expiry time
    duration : timedelta | None
        Duration until expiry
    ticks : int
        Interval ticks
    time_unit : TimeUnit
        Interval time unit
    work_days_only : bool
        Ignore non-work days

    Examples
    --------
    >>> params = YTimerParameters.from_expiry(
    ...     trigger=TimerTrigger.ON_ENABLED, expiry_time=datetime(2024, 12, 31, 23, 59, 59)
    ... )
    """

    timer_type: TimerType = TimerType.NIL
    trigger: TimerTrigger | None = None
    variable_name: str | None = None
    expiry_time: datetime | None = None
    duration: timedelta | None = None
    ticks: int = 0
    time_unit: TimeUnit = TimeUnit.MSEC
    work_days_only: bool = False

    @classmethod
    def from_variable(cls, net_param_name: str) -> YTimerParameters:
        """Create late-bound timer from net variable.

        Parameters
        ----------
        net_param_name : str
            Net variable name

        Returns
        -------
        YTimerParameters
            Configured timer parameters
        """
        params = cls()
        params.set_variable(net_param_name)
        return params

    @classmethod
    def from_expiry(cls, trigger: TimerTrigger, expiry_time: datetime) -> YTimerParameters:
        """Create expiry timer.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        expiry_time : datetime
            Absolute expiry time

        Returns
        -------
        YTimerParameters
            Configured timer parameters
        """
        params = cls()
        params.set_expiry(trigger, expiry_time)
        return params

    @classmethod
    def from_duration(cls, trigger: TimerTrigger, duration: timedelta) -> YTimerParameters:
        """Create duration timer.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        duration : timedelta
            Duration until expiry

        Returns
        -------
        YTimerParameters
            Configured timer parameters
        """
        params = cls()
        params.set_duration(trigger, duration)
        return params

    @classmethod
    def from_interval(cls, trigger: TimerTrigger, ticks: int, time_unit: TimeUnit) -> YTimerParameters:
        """Create interval timer.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        ticks : int
            Number of time units
        time_unit : TimeUnit
            Time unit

        Returns
        -------
        YTimerParameters
            Configured timer parameters
        """
        params = cls()
        params.set_interval(trigger, ticks, time_unit)
        return params

    def set_variable(self, net_param_name: str) -> None:
        """Set late-bound variable.

        Parameters
        ----------
        net_param_name : str
            Net variable name
        """
        self.variable_name = net_param_name
        self.timer_type = TimerType.LATE_BOUND

    def set_expiry(self, trigger: TimerTrigger, expiry_time: datetime) -> None:
        """Set expiry time.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        expiry_time : datetime
            Absolute expiry time
        """
        self.trigger = trigger
        self.expiry_time = expiry_time
        self.timer_type = TimerType.EXPIRY

    def set_duration(self, trigger: TimerTrigger, duration: timedelta) -> None:
        """Set duration.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        duration : timedelta
            Duration until expiry
        """
        self.trigger = trigger
        self.duration = duration
        self.timer_type = TimerType.DURATION

    def set_interval(self, trigger: TimerTrigger, ticks: int, time_unit: TimeUnit) -> None:
        """Set interval.

        Parameters
        ----------
        trigger : TimerTrigger
            When timer starts
        ticks : int
            Number of time units
        time_unit : TimeUnit
            Time unit (defaults to MSEC if None)
        """
        self.trigger = trigger
        self.ticks = ticks
        self.time_unit = time_unit if time_unit else TimeUnit.MSEC
        self.timer_type = TimerType.INTERVAL

    def trigger_matches_status(self, status: WorkItemStatus) -> bool:
        """Check if trigger matches work item status.

        Parameters
        ----------
        status : WorkItemStatus
            Work item status

        Returns
        -------
        bool
            True if trigger matches status
        """
        if self.timer_type == TimerType.NIL or self.trigger is None:
            return False

        if self.trigger == TimerTrigger.ON_ENABLED:
            return status == WorkItemStatus.ENABLED
        elif self.trigger == TimerTrigger.ON_STARTED:
            return status == WorkItemStatus.STARTED

        return False

    def get_work_day_duration(self) -> timedelta | None:
        """Get duration adjusted for work days.

        Returns
        -------
        timedelta | None
            Adjusted duration, or None if not duration type
        """
        if self.duration is None:
            return None
        # Work day adjustment requires calendar/workday service integration
        # This is handled by the timer service layer, not the parameter object
        return self.duration

    def to_xml(self) -> str:
        """Serialize to XML.

        Returns
        -------
        str
            XML representation
        """
        if self.timer_type == TimerType.NIL:
            return ""

        root = ET.Element("timer")

        if self.timer_type == TimerType.DURATION:
            if self.trigger:
                ET.SubElement(root, "trigger").text = self.trigger.name
            if self.duration:
                ET.SubElement(root, "duration").text = self._duration_to_iso8601(self.duration)
            if self.work_days_only:
                ET.SubElement(root, "workdays").text = "true"
        elif self.timer_type == TimerType.EXPIRY:
            if self.trigger:
                ET.SubElement(root, "trigger").text = self.trigger.name
            if self.expiry_time:
                ET.SubElement(root, "expiry").text = str(int(self.expiry_time.timestamp() * 1000))
        elif self.timer_type == TimerType.INTERVAL:
            if self.trigger:
                ET.SubElement(root, "trigger").text = self.trigger.name
            params = ET.SubElement(root, "durationparams")
            ET.SubElement(params, "ticks").text = str(self.ticks)
            ET.SubElement(params, "interval").text = self.time_unit.name
        elif self.timer_type == TimerType.LATE_BOUND:
            if self.variable_name:
                ET.SubElement(root, "netparam").text = self.variable_name

        return ET.tostring(root, encoding="unicode")

    def _duration_to_iso8601(self, duration: timedelta) -> str:
        """Convert timedelta to ISO 8601 duration string.

        Parameters
        ----------
        duration : timedelta
            Duration to convert

        Returns
        -------
        str
            ISO 8601 duration (e.g., "P1DT2H30M")
        """
        days = duration.days
        seconds = duration.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts: list[str] = ["P"]
        if days > 0:
            parts.append(f"{days}D")
        if hours > 0 or minutes > 0 or secs > 0:
            parts.append("T")
            if hours > 0:
                parts.append(f"{hours}H")
            if minutes > 0:
                parts.append(f"{minutes}M")
            if secs > 0:
                parts.append(f"{secs}S")

        return "".join(parts) if len(parts) > 1 else "PT0S"

    def __str__(self) -> str:
        """String representation.

        Returns
        -------
        str
            Human-readable string
        """
        if self.timer_type == TimerType.NIL:
            return "Nil"

        prefix = "Start: " if self.trigger == TimerTrigger.ON_STARTED else "Offer: "

        if self.timer_type == TimerType.DURATION and self.duration:
            return prefix + self._duration_to_iso8601(self.duration)
        elif self.timer_type == TimerType.EXPIRY and self.expiry_time:
            return prefix + self.expiry_time.isoformat()
        elif self.timer_type == TimerType.INTERVAL:
            return f"{prefix}{self.ticks} {self.time_unit.name}"
        elif self.timer_type == TimerType.LATE_BOUND and self.variable_name:
            return f"Variable: {self.variable_name}"

        return "Nil"
