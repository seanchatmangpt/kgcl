"""Session timer management (mirrors Java YSessionTimer).

Manages timeout timers for active sessions.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.authentication.i_session_cache import ISessionCache
    from kgcl.yawl.authentication.y_abstract_session import YAbstractSession

logger = logging.getLogger(__name__)


class YSessionTimer:
    """Timer for managing session timeouts.

    Manages timeout timers for active sessions, automatically expiring
    sessions after their idle timeout period.

    Parameters
    ----------
    cache : ISessionCache
        Session cache to manage

    Attributes
    ----------
    _session_map : dict[YAbstractSession, threading.Timer]
        Map of sessions to their timer tasks
    _cache : ISessionCache
        Session cache instance

    Notes
    -----
    Mirrors Java YSessionTimer class.
    Uses threading.Timer instead of java.util.Timer.

    Examples
    --------
    >>> from kgcl.yawl.authentication import YSessionCache, YSessionTimer
    >>> cache = YSessionCache()
    >>> timer = YSessionTimer(cache)
    >>> session = YAbstractSession(timeout_seconds=3600)
    >>> timer.add(session)
    True
    >>> timer.reset(session)
    True
    >>> timer.expire(session)
    True
    """

    def __init__(self, cache: ISessionCache) -> None:
        """Initialize session timer.

        Parameters
        ----------
        cache : ISessionCache
            Session cache to manage
        """
        self._session_map: dict[YAbstractSession, threading.Timer] = {}
        self._cache: ISessionCache = cache

    def get_cache(self) -> ISessionCache:
        """Get the session cache.

        Returns
        -------
        ISessionCache
            The session cache

        Notes
        -----
        Java signature: ISessionCache getCache()
        """
        return self._cache

    def add(self, session: YAbstractSession) -> bool:
        """Add a session to the timer.

        Parameters
        ----------
        session : YAbstractSession
            Session to add

        Returns
        -------
        bool
            True if session was added successfully

        Notes
        -----
        Java signature: boolean add(YAbstractSession session)
        """
        if session is None:
            return False
        timer_task = self._schedule_timeout(session)
        if timer_task is not None:
            self._session_map[session] = timer_task
        return timer_task is not None

    def reset(self, session: YAbstractSession) -> bool:
        """Reset the timer for a session.

        Parameters
        ----------
        session : YAbstractSession
            Session to reset

        Returns
        -------
        bool
            True if session timer was reset successfully

        Notes
        -----
        Java signature: boolean reset(YAbstractSession session)
        """
        if session is None:
            return False
        self.expire(session)
        return self.add(session)

    def expire(self, session: YAbstractSession) -> bool:
        """Expire (cancel) the timer for a session.

        Parameters
        ----------
        session : YAbstractSession
            Session to expire

        Returns
        -------
        bool
            True if session timer was cancelled

        Notes
        -----
        Java signature: boolean expire(YAbstractSession session)
        """
        if session is not None:
            timer_task = self._session_map.pop(session, None)
            if timer_task is not None:
                timer_task.cancel()
                return True
        return False

    def shutdown(self) -> None:
        """Shutdown the timer.

        Cancels all active timers.

        Notes
        -----
        Java signature: void shutdown()
        """
        for timer_task in self._session_map.values():
            timer_task.cancel()
        self._session_map.clear()

    def _schedule_timeout(self, session: YAbstractSession) -> threading.Timer | None:
        """Schedule a timeout task for a session.

        Starts a timer task to timeout a session after the specified period of
        inactivity - iff the timer interval set is positive (a negative interval
        means never timeout).

        Parameters
        ----------
        session : YAbstractSession
            Session to schedule timeout for

        Returns
        -------
        threading.Timer | None
            Timer task, or None if interval is negative (never timeout)

        Notes
        -----
        Java signature: protected TimerTask scheduleTimeout(YAbstractSession session)
        """
        interval_ms = session.get_interval()
        if interval_ms > 0:
            # Convert milliseconds to seconds for threading.Timer
            interval_seconds = interval_ms / 1000.0
            timeout = Timeout(session.get_handle(), self._cache)
            timer = threading.Timer(interval_seconds, timeout.run)
            timer.start()
            return timer
        return None


class Timeout:
    """Timeout task that expires a session.

    Expires (removes) the active session. Called when a session timer expires.

    Parameters
    ----------
    handle : str
        Session handle to expire
    cache : ISessionCache
        Session cache to expire session in

    Notes
    -----
    Mirrors Java YSessionTimer.TimeOut inner class.
    """

    def __init__(self, handle: str, cache: ISessionCache) -> None:
        """Initialize timeout task.

        Parameters
        ----------
        handle : str
            Session handle
        cache : ISessionCache
            Session cache
        """
        self._handle: str = handle
        self._cache: ISessionCache = cache

    def run(self) -> None:
        """Execute timeout - expire the session.

        Notes
        -----
        Java signature: void run()
        """
        self._cache.expire(self._handle)
