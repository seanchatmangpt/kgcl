"""External session management (mirrors Java YExternalSession).

Maintains an active session belonging to an external application client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kgcl.yawl.authentication.y_session import YSession
from kgcl.yawl.exceptions.y_exceptions import YPersistenceException

if TYPE_CHECKING:
    from kgcl.yawl.authentication.y_external_client import YExternalClient


class YExternalSession(YSession):
    """Active session for external application client.

    Maintains an active session belonging to an external application client.

    Parameters
    ----------
    client : YExternalClient
        The connected external client
    timeout_seconds : int
        Maximum idle time for this session (in seconds)

    Attributes
    ----------
    _client : YExternalClient
        The external client associated with this session

    Notes
    -----
    Mirrors Java YExternalSession class.

    Examples
    --------
    >>> from kgcl.yawl.authentication import YExternalClient, YExternalSession
    >>> client = YExternalClient("user1", "password", "Test client")
    >>> session = YExternalSession(client, timeout_seconds=3600)
    >>> name = session.get_name()
    >>> password = session.get_password()

    Since
    -----
    2.1

    Author
    ------
    Michael Adams
    """

    def __init__(self, client: YExternalClient, timeout_seconds: int) -> None:
        """Initialize external session.

        Parameters
        ----------
        client : YExternalClient
            The connected external client
        timeout_seconds : int
            Maximum idle time for this session (in seconds)
        """
        super().__init__(timeout_seconds, client)
        self._client: YExternalClient = client

    def get_name(self) -> str | None:
        """Get the client's user name.

        Returns
        -------
        str | None
            The user name of the client associated with this session, or None

        Notes
        -----
        Java signature: String getName()
        """
        return self._client.get_user_name() if self._client else None

    def get_password(self) -> str | None:
        """Get the client's password.

        Returns
        -------
        str | None
            The (hashed) password of the client associated with this session, or None

        Notes
        -----
        Java signature: String getPassword()
        """
        return self._client.get_password() if self._client else None

    def set_password(self, password: str) -> None:
        """Update (and persist) the password for an external client.

        Parameters
        ----------
        password : str
            The (hashed) password to set for the external client

        Raises
        ------
        YPersistenceException
            If there's some problem persisting the change

        Notes
        -----
        Java signature: void setPassword(String password) throws YPersistenceException
        """
        if self._client:
            self._client.set_password(password)
            from kgcl.yawl.engine.y_engine import YEngine

            engine = YEngine.get_instance()
            engine.update_object(self._client)

    def set_client(self, client: YExternalClient) -> None:
        """Set the external client for this session.

        Parameters
        ----------
        client : YExternalClient
            The external client to associate with this session

        Notes
        -----
        Java signature: void setClient(YExternalClient client)
        """
        self._client = client

    def get_client(self) -> YExternalClient | None:
        """Get the external client associated with this session.

        Returns
        -------
        YExternalClient | None
            The external client, or None if not set

        Notes
        -----
        Java signature: YExternalClient getClient()
        """
        return self._client
