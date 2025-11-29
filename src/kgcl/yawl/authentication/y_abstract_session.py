"""Abstract base class for YAWL engine sessions.

Base class representing an active session between the engine and an external
service or application.
"""

from __future__ import annotations

import uuid


class YAbstractSession:
    """Abstract base class for engine sessions.

    Represents an active session between the engine and an external service
    or application. Provides session handle and timeout management.

    Parameters
    ----------
    timeout_seconds : int
        Maximum idle time for this session in seconds. A value of 0 defaults
        to 60 minutes; a value less than 0 means this session will never timeout.

    Attributes
    ----------
    _handle : str
        Unique session handle (UUID)
    _interval : int
        Timeout interval in milliseconds

    Examples
    --------
    >>> session = YAbstractSession(timeout_seconds=3600)
    >>> handle = session.get_handle()
    >>> interval = session.get_interval()
    """

    def __init__(self, timeout_seconds: int) -> None:
        """Initialize abstract session.

        Parameters
        ----------
        timeout_seconds : int
            Maximum idle time in seconds (0 = 60 min default, <0 = never timeout)
        """
        self._handle: str = str(uuid.uuid4())
        self._interval: int = self._set_interval(timeout_seconds)

    def get_handle(self) -> str:
        """Get session handle.

        Returns
        -------
        str
            Unique session handle (UUID)
        """
        return self._handle

    def get_interval(self) -> int:
        """Get timeout interval.

        Returns
        -------
        int
            Timeout interval in milliseconds
        """
        return self._interval

    def _set_interval(self, seconds: int) -> int:
        """Set timeout interval from seconds to milliseconds.

        Parameters
        ----------
        seconds : int
            Timeout in seconds (0 = 60 min default, <0 = never timeout)

        Returns
        -------
        int
            Timeout interval in milliseconds
        """
        if seconds == 0:
            return 3600000  # 60 minutes default
        elif seconds < 0:
            return -1  # Never timeout
        else:
            return seconds * 1000
