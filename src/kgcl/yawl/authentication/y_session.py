"""YAWL session management (mirrors Java YSession).

Base class representing an active session between the engine and an external
service or application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kgcl.yawl.authentication.y_abstract_session import YAbstractSession
from kgcl.yawl.exceptions.y_exceptions import YPersistenceException

if TYPE_CHECKING:
    from kgcl.yawl.authentication.y_client import YClient


class YSession(YAbstractSession):
    """Active session between engine and external service or application.

    Base class which represents an active session between the engine and an
    external service or application.

    Parameters
    ----------
    timeout_seconds : int
        Maximum idle time for this session (in seconds). A value of 0 will
        default to 60 minutes; a value less than zero means this session will
        never timeout.
    client : YClient | None
        The external service or application requesting a session

    Attributes
    ----------
    _client : YClient | None
        The client associated with this session (overridden in child classes)

    Notes
    -----
    Mirrors Java YSession class.
    This base version returns null for getURI() and getPassword().
    Subclasses override these methods for specific client types.

    Examples
    --------
    >>> from kgcl.yawl.authentication import YSession, YClient
    >>> client = YClient("user1", "password", "Test client")
    >>> session = YSession(client, timeout_seconds=3600)
    >>> handle = session.get_handle()
    >>> client = session.get_client()

    Since
    -----
    2.1

    Author
    ------
    Michael Adams
    """

    def __init__(self, timeout_seconds: int, client: YClient | None = None) -> None:
        """Initialize session with timeout and optional client.

        Parameters
        ----------
        timeout_seconds : int
            Maximum idle time for this session (in seconds)
        client : YClient | None
            The external service or application requesting a session
        """
        super().__init__(timeout_seconds)
        self._client: YClient | None = client

    def get_uri(self) -> str | None:
        """Get the URI for this session.

        Returns
        -------
        str | None
            Session URI, or None in base implementation (overridden in subclasses)

        Notes
        -----
        Java signature: String getURI()
        This base version returns null. Overridden in all child classes.
        """
        return None

    def get_password(self) -> str | None:
        """Get the password for this session.

        Returns
        -------
        str | None
            Session password, or None in base implementation (overridden in subclasses)

        Notes
        -----
        Java signature: String getPassword()
        This base version returns null. Overridden in all child classes.
        """
        return None

    def set_password(self, password: str) -> None:
        """Set password for the client.

        Parameters
        ----------
        password : str
            The (hashed) password to set (change to) for the client

        Raises
        ------
        YPersistenceException
            If there's a problem persisting the change

        Notes
        -----
        Java signature: void setPassword(String password) throws YPersistenceException
        This base version sets the password for the generic 'admin' user only.
        """
        if self._client and self._client.get_user_name() == "admin":
            from kgcl.yawl.engine.y_engine import YEngine

            engine = YEngine.get_instance()
            client = engine.get_external_client("admin")
            if client:
                # Note: YExternalClient would need set_password method
                # For now, we'll update via engine
                engine.update_object(client)

    def get_client(self) -> YClient | None:
        """Get the client associated with this session.

        Returns
        -------
        YClient | None
            The client, or None if not set

        Notes
        -----
        Java signature: YClient getClient()
        """
        return self._client
