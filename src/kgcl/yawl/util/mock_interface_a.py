"""Mock Interface A client for testing and development.

This is a minimal implementation to enable session management testing
without requiring a full YAWL engine Interface A connection.

MIGRATION NOTE:
    This should be replaced with the real InterfaceA_EnvironmentBasedClient
    when connecting to a production YAWL engine. See docs/interface-a-migration.md
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MockInterfaceAClient:
    """Mock Interface A client for testing.

    Provides in-memory credential storage without requiring database or
    network connections. Suitable for unit tests and development.

    Parameters
    ----------
    uri : str
        URI of engine's Interface A (stored but not used in mock)
    userid : str
        Userid for connection (stored but not used in mock)
    password : str
        Password for connection (stored but not used in mock)

    Examples
    --------
    >>> client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")
    >>> client.register_user("testuser", "testpass")
    >>> client.get_password("testuser")
    'testpass'

    Notes
    -----
    This is a MOCK implementation. For production use, replace with
    InterfaceA_EnvironmentBasedClient from the YAWL engine.
    """

    def __init__(self, uri: str, userid: str, password: str) -> None:
        """Initialize mock Interface A client.

        Parameters
        ----------
        uri : str
            URI of engine's Interface A
        userid : str
            Userid for connection
        password : str
            Password for connection
        """
        self.ia_uri: str = uri
        self.ia_userid: str = userid
        self.ia_password: str = password
        self.ia_handle: str | None = None

        # In-memory credential store
        self._users: dict[str, str] = {
            # Default admin user
            "admin": "admin",
            # Register the connecting user
            userid: password,
        }

        self._services: dict[str, dict[str, str]] = {}

        logger.debug("MockInterfaceAClient initialized for %s", uri)

    def register_user(self, userid: str, password: str) -> None:
        """Register a user in the mock store.

        Parameters
        ----------
        userid : str
            Username to register
        password : str
            Password to register

        Examples
        --------
        >>> client = MockInterfaceAClient("http://localhost", "admin", "admin")
        >>> client.register_user("testuser", "testpass")
        >>> client.get_password("testuser")
        'testpass'
        """
        self._users[userid] = password
        logger.debug("Registered user: %s", userid)

    def register_service(self, service_name: str, password: str, uri: str | None = None) -> None:
        """Register a YAWL service in the mock store.

        Parameters
        ----------
        service_name : str
            Service name (acts as username)
        password : str
            Service password
        uri : str | None, optional
            Service URI, by default None

        Examples
        --------
        >>> client = MockInterfaceAClient("http://localhost", "admin", "admin")
        >>> client.register_service("WorkletService", "workletpass", "http://localhost:8080")
        """
        self._services[service_name] = {
            "password": password,
            "uri": uri or f"http://localhost:8080/services/{service_name}",
        }
        logger.debug("Registered service: %s", service_name)

    def get_password(self, userid: str) -> str | None:
        """Get password from mock store for a userid.

        Checks both user and service registrations.

        Parameters
        ----------
        userid : str
            Userid to get password for

        Returns
        -------
        str | None
            Retrieved password, or None if userid is unknown

        Examples
        --------
        >>> client = MockInterfaceAClient("http://localhost", "admin", "admin")
        >>> client.get_password("admin")
        'admin'
        >>> client.get_password("unknown")
        """
        # Check users first
        if userid in self._users:
            return self._users[userid]

        # Check services
        if userid in self._services:
            return self._services[userid]["password"]

        logger.warning("Password requested for unknown user/service: %s", userid)
        return None

    def check_connection(self, handle: str | None = None) -> str:
        """Mock connection check (always succeeds).

        Parameters
        ----------
        handle : str | None, optional
            Session handle to check, by default None

        Returns
        -------
        str
            Success message

        Notes
        -----
        In real implementation, this would validate the session handle
        with the YAWL engine.
        """
        return "<success/>"

    def connect(self, userid: str, password: str) -> str:
        """Mock connection (always returns success handle).

        Parameters
        ----------
        userid : str
            Userid to connect with
        password : str
            Password to authenticate

        Returns
        -------
        str
            Mock session handle or failure message

        Notes
        -----
        In real implementation, this would authenticate with the YAWL engine
        and return a real session handle.
        """
        if self.get_password(userid) == password:
            self.ia_handle = f"mock-handle-{userid}"
            return self.ia_handle

        return "<failure>Invalid credentials</failure>"
