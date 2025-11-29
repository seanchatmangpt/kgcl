"""Session cache interface (mirrors Java ISessionCache).

Protocol interface for session cache implementations.
"""

from __future__ import annotations

from typing import Protocol

from kgcl.yawl.authentication.y_abstract_session import YAbstractSession


class ISessionCache(Protocol):
    """Protocol interface for session cache implementations.

    Defines the interface for managing engine connections from custom services
    and external applications.

    Notes
    -----
    Mirrors Java ISessionCache interface.
    YSessionCache implements this protocol.

    Examples
    --------
    >>> from kgcl.yawl.authentication import YSessionCache
    >>> cache: ISessionCache = YSessionCache()
    >>> handle = cache.connect("user1", "password", 3600)
    >>> cache.check_connection(handle)
    True
    >>> session = cache.get_session(handle)
    >>> cache.disconnect(handle)
    """

    def connect(self, name: str, password: str, timeout_seconds: int) -> str:
        """Create and store a new session.

        Parameters
        ----------
        name : str
            Username of the external client or service name
        password : str
            Corresponding (hashed) password
        timeout_seconds : int
            Maximum idle time for this session (in seconds)

        Returns
        -------
        str
            Valid session handle, or XML error message

        Notes
        -----
        Java signature: String connect(String name, String password, long timeOutSeconds)
        """
        ...

    def check_connection(self, handle: str) -> bool:
        """Check that a session handle represents an active session.

        Parameters
        ----------
        handle : str
            Session handle held by a client or service

        Returns
        -------
        bool
            True if the handle's session is active

        Notes
        -----
        Java signature: boolean checkConnection(String handle)
        """
        ...

    def get_session(self, handle: str) -> YAbstractSession | None:
        """Get the session associated with a session handle.

        Parameters
        ----------
        handle : str
            Session handle

        Returns
        -------
        YAbstractSession | None
            Session object, or None if handle is invalid or inactive

        Notes
        -----
        Java signature: YAbstractSession getSession(String handle)
        """
        ...

    def expire(self, handle: str) -> None:
        """Remove a session from the set of active sessions after an idle timeout.

        Parameters
        ----------
        handle : str
            Session handle of the session to remove

        Notes
        -----
        Java signature: void expire(String handle)
        """
        ...

    def disconnect(self, handle: str) -> None:
        """End an active session of a custom service or external application.

        Parameters
        ----------
        handle : str
            Session handle to disconnect

        Notes
        -----
        Java signature: void disconnect(String handle)
        """
        ...

    def shutdown(self) -> None:
        """Shutdown the session cache.

        Called when the hosting server shuts down to write a shutdown record
        for each active session to the audit log.

        Notes
        -----
        Java signature: void shutdown()
        """
        ...
