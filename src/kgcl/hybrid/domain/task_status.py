"""TaskStatus - Enumeration of task lifecycle states.

This module defines the possible states a task can be in during workflow execution,
with priority ordering for monotonic status resolution.

Examples
--------
>>> TaskStatus.ACTIVE.priority
1
>>> TaskStatus.COMPLETED.priority
2
>>> TaskStatus.highest_priority(["Active", "Completed"])
'Completed'
"""

from __future__ import annotations

from enum import Enum


class TaskStatus(Enum):
    """Task lifecycle states with priority ordering.

    In monotonic reasoning, tasks may accumulate multiple statuses.
    Priority determines which status to report (higher priority wins).

    The lifecycle progression is:
    Pending -> Active -> Completed -> Archived

    With additional states for special conditions:
    - Waiting: Blocked on milestone
    - Cancelled: Explicitly cancelled
    - Blocked: Waiting for resource/lock

    Attributes
    ----------
    value : str
        Status string value as stored in RDF.
    priority : int
        Priority for status resolution (higher wins).

    Examples
    --------
    >>> TaskStatus.ACTIVE.value
    'Active'
    >>> TaskStatus.ACTIVE.priority
    1

    >>> TaskStatus.COMPLETED.priority > TaskStatus.ACTIVE.priority
    True

    >>> status = TaskStatus.from_string("Completed")
    >>> status
    <TaskStatus.COMPLETED: 'Completed'>
    """

    PENDING = "Pending"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"
    WAITING = "Waiting"
    CANCELLED = "Cancelled"
    BLOCKED = "Blocked"

    @property
    def priority(self) -> int:
        """Get priority for status resolution.

        Higher priority statuses take precedence in monotonic systems
        where multiple status assertions may exist.

        Returns
        -------
        int
            Priority value (higher = more progressed/dominant).

        Examples
        --------
        >>> TaskStatus.ACTIVE.priority
        1

        >>> TaskStatus.ARCHIVED.priority
        3

        >>> TaskStatus.CANCELLED.priority
        4
        """
        priorities = {
            TaskStatus.PENDING: 0,
            TaskStatus.ACTIVE: 1,
            TaskStatus.COMPLETED: 2,
            TaskStatus.ARCHIVED: 3,
            TaskStatus.CANCELLED: 4,
            TaskStatus.WAITING: 0,
            TaskStatus.BLOCKED: 0,
        }
        return priorities.get(self, 0)

    @classmethod
    def from_string(cls, status: str) -> TaskStatus:
        """Create TaskStatus from string value.

        Parameters
        ----------
        status : str
            Status string (e.g., "Active", "Completed").

        Returns
        -------
        TaskStatus
            Corresponding enum member.

        Raises
        ------
        ValueError
            If status string is not recognized.

        Examples
        --------
        >>> TaskStatus.from_string("Active")
        <TaskStatus.ACTIVE: 'Active'>

        >>> TaskStatus.from_string("Completed")
        <TaskStatus.COMPLETED: 'Completed'>

        >>> TaskStatus.from_string("Unknown")
        Traceback (most recent call last):
        ...
        ValueError: Unknown task status: Unknown
        """
        for member in cls:
            if member.value == status:
                return member
        msg = f"Unknown task status: {status}"
        raise ValueError(msg)

    @classmethod
    def highest_priority(cls, statuses: list[str]) -> str:
        """Get highest priority status from list.

        Used to resolve monotonic status accumulation by returning
        the most progressed status.

        Parameters
        ----------
        statuses : list[str]
            List of status strings.

        Returns
        -------
        str
            Status string with highest priority.

        Raises
        ------
        ValueError
            If statuses list is empty.

        Examples
        --------
        >>> TaskStatus.highest_priority(["Active", "Completed"])
        'Completed'

        >>> TaskStatus.highest_priority(["Active", "Completed", "Archived"])
        'Archived'

        >>> TaskStatus.highest_priority(["Pending"])
        'Pending'

        >>> TaskStatus.highest_priority([])
        Traceback (most recent call last):
        ...
        ValueError: Cannot determine highest priority from empty list
        """
        if not statuses:
            msg = "Cannot determine highest priority from empty list"
            raise ValueError(msg)

        best: str | None = None
        best_priority = -1

        for status_str in statuses:
            try:
                status = cls.from_string(status_str)
                if status.priority > best_priority:
                    best_priority = status.priority
                    best = status_str
            except ValueError:
                # Unknown status, use priority 0
                if best_priority < 0:
                    best = status_str
                    best_priority = 0

        # At this point best cannot be None since we checked for empty list
        # and every status gets a priority (even unknown ones get 0)
        return best if best is not None else statuses[0]
