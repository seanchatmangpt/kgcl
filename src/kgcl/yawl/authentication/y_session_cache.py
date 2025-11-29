"""Session cache management (mirrors Java YSessionCache).

An extended dictionary that manages connections to the engine from custom
services and external applications.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.authentication.i_session_cache import ISessionCache
    from kgcl.yawl.authentication.y_abstract_session import YAbstractSession
    from kgcl.yawl.authentication.y_client import YClient
    from kgcl.yawl.authentication.y_external_client import YExternalClient

logger = logging.getLogger(__name__)


class YSessionCache(MutableMapping[str, YAbstractSession]):
    """Session cache for managing active sessions.

    An extended dictionary that manages connections to the engine from custom
    services and external applications. The map is of the form [sessionHandle, session].

    Parameters
    ----------
    timer : YSessionTimer | None
        Timer for managing session timeouts (optional, will be created if None)

    Attributes
    ----------
    _sessions : dict[str, YAbstractSession]
        Map of session handles to session objects
    _timer : YSessionTimer
        Timer for managing session timeouts

    Notes
    -----
    Mirrors Java YSessionCache class.
    Implements ISessionCache interface.

    Examples
    --------
    >>> cache = YSessionCache()
    >>> handle = cache.connect("user1", "password", 3600)
    >>> is_valid = cache.check_connection(handle)
    >>> session = cache.get_session(handle)
    >>> cache.disconnect(handle)
    """

    def __init__(self, timer: YSessionTimer | None = None) -> None:
        """Initialize session cache.

        Parameters
        ----------
        timer : YSessionTimer | None
            Timer for managing session timeouts (optional)
        """
        from kgcl.yawl.authentication.y_session_timer import YSessionTimer

        self._sessions: dict[str, YAbstractSession] = {}
        self._timer: YSessionTimer = timer or YSessionTimer(self)

    def connect(self, name: str, password: str, timeout_seconds: int) -> str:
        """Create and store a new session.

        Parameters
        ----------
        name : str
            Username of the external client or service name
        password : str
            Corresponding (hashed) password
        timeout_seconds : int
            Maximum idle time for this session (in seconds). A value of 0 will
            default to 60 minutes; a value less than zero means this session
            will never timeout.

        Returns
        -------
        str
            A valid session handle, or an appropriate error message

        Notes
        -----
        Java signature: String connect(String name, String password, long timeOutSeconds)
        """
        if name is None:
            return self._fail_msg("Null user name")

        from kgcl.yawl.authentication.y_external_session import YExternalSession
        from kgcl.yawl.authentication.y_service_session import YServiceSession
        from kgcl.yawl.authentication.y_session import YSession
        from kgcl.yawl.engine.y_engine import YEngine

        engine = YEngine.get_instance()

        # First check if it's an external client
        client = None
        if hasattr(engine, "get_external_client"):
            client = engine.get_external_client(name)
        if client:
            if self._validate_credentials(client, password):
                # Admin gets special session type
                if name == "admin":
                    session: YAbstractSession = YSession(client, timeout_seconds)
                else:
                    session = YExternalSession(client, timeout_seconds)
                return self._store_session(session)
            else:
                return self._bad_password(name)

        # Now check if it's a service
        service = self._get_service(name, engine)
        if service:
            if self._validate_service_credentials(service, password):
                session = YServiceSession(service, timeout_seconds)
                return self._store_session(session)
            else:
                return self._bad_password(name)

        return self._unknown_user(name)

    def check_connection(self, handle: str) -> bool:
        """Check that a session handle represents an active session.

        If the session is active, the session idle timer is restarted.

        Parameters
        ----------
        handle : str
            The session handle held by a client or service

        Returns
        -------
        bool
            True if the handle's session is active

        Notes
        -----
        Java signature: boolean checkConnection(String handle)
        """
        if handle is None:
            return False
        session = self._sessions.get(handle)
        return session is not None and self._timer.reset(session)

    def is_service_connected(self, uri: str) -> bool:
        """Check that a particular custom service has an active session.

        Parameters
        ----------
        uri : str
            The URI of the custom service

        Returns
        -------
        bool
            True if the service has an active session

        Notes
        -----
        Java signature: boolean isServiceConnected(String uri)
        """
        for session in self._sessions.values():
            session_uri = session.get_uri() if hasattr(session, "get_uri") else None
            if session_uri == uri:
                return True
        return False

    def is_client_connected(self, client: YExternalClient) -> bool:
        """Check that a particular external client has an active session.

        Parameters
        ----------
        client : YExternalClient
            The client

        Returns
        -------
        bool
            True if the client has an active session

        Notes
        -----
        Java signature: boolean isClientConnected(YExternalClient client)
        """
        for session in self._sessions.values():
            session_client = session.get_client() if hasattr(session, "get_client") else None
            if session_client == client:
                return True
        return False

    def get_session(self, handle: str) -> YAbstractSession | None:
        """Get the session associated with a session handle.

        Parameters
        ----------
        handle : str
            A session handle

        Returns
        -------
        YAbstractSession | None
            The session object associated with the handle, or None if the handle
            is invalid or inactive

        Notes
        -----
        Java signature: YAbstractSession getSession(String handle)
        """
        if handle is not None:
            return self._sessions.get(handle)
        return None

    def expire(self, handle: str) -> None:
        """Remove a session from the set of active sessions after an idle timeout.

        Also writes the expiration to the session audit log.

        Parameters
        ----------
        handle : str
            The session handle of the session to remove

        Notes
        -----
        Java signature: void expire(String handle)
        """
        self._remove_session(handle, "expired")

    def disconnect(self, client_or_handle: YClient | str) -> None:
        """End an active session of a custom service or external application.

        Also writes the disconnection to the session audit log.

        Parameters
        ----------
        client_or_handle : YClient | str
            The service/application to disconnect, or the session handle

        Notes
        -----
        Java signature: void disconnect(YClient client) or void disconnect(String handle)
        """
        if isinstance(client_or_handle, str):
            self._remove_session(client_or_handle, "logoff")
        else:
            # Find session by client
            for handle, session in self._sessions.items():
                session_client = session.get_client() if hasattr(session, "get_client") else None
                if session_client == client_or_handle:
                    self._remove_session(handle, "logoff")
                    break

    def shutdown(self) -> None:
        """Shutdown the session cache.

        Called when the hosting server shuts down to write a shutdown record
        for each active session to the audit log.

        Notes
        -----
        Java signature: void shutdown()
        """
        for session in self._sessions.values():
            client = session.get_client() if hasattr(session, "get_client") else None
            if client:
                username = client.get_user_name() if hasattr(client, "get_user_name") else "unknown"
                self._audit(username, "shutdown")
        self._timer.shutdown()

    # MutableMapping interface implementation
    def __getitem__(self, key: str) -> YAbstractSession:
        """Get session by handle."""
        return self._sessions[key]

    def __setitem__(self, key: str, value: YAbstractSession) -> None:
        """Set session by handle."""
        self._sessions[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete session by handle."""
        del self._sessions[key]

    def __iter__(self):
        """Iterate over session handles."""
        return iter(self._sessions)

    def __len__(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    # Private helper methods
    def _validate_credentials(self, client: YExternalClient, password: str) -> bool:
        """Validate external client credentials.

        Parameters
        ----------
        client : YExternalClient
            External client
        password : str
            Password to validate

        Returns
        -------
        bool
            True if credentials are valid
        """
        return client.get_password() == password

    def _validate_service_credentials(self, service: YAWLServiceReference, password: str) -> bool:
        """Validate service credentials.

        Parameters
        ----------
        service : YAWLServiceReference
            Service reference
        password : str
            Password to validate

        Returns
        -------
        bool
            True if credentials are valid
        """
        return service.get_service_password() == password

    def _get_service(
        self, name: str, engine: YEngine
    ) -> YAWLServiceReference | None:
        """Get service by name.

        Parameters
        ----------
        name : str
            Service name
        engine : YEngine
            Engine instance

        Returns
        -------
        YAWLServiceReference | None
            Service reference or None
        """
        from kgcl.yawl.elements.y_awl_service_reference import YAWLServiceReference

        # Note: These methods may need to be implemented in YEngine
        # For now, we'll use placeholder logic
        if hasattr(engine, "get_default_worklist") and name == "DefaultWorklist":
            return engine.get_default_worklist()

        if hasattr(engine, "get_yawl_services"):
            services = engine.get_yawl_services()
            for service in services:
                if service.get_service_name() == name:
                    return service
        return None

    def _store_session(self, session: YAbstractSession) -> str:
        """Store session and return handle.

        Parameters
        ----------
        session : YAbstractSession
            Session to store

        Returns
        -------
        str
            Session handle
        """
        handle = session.get_handle()
        self._sessions[handle] = session
        self._timer.add(session)
        client = session.get_client() if hasattr(session, "get_client") else None
        if client:
            username = client.get_user_name() if hasattr(client, "get_user_name") else "unknown"
            self._audit(username, "logon")
        return handle

    def _remove_session(self, handle: str, action: str) -> YAbstractSession | None:
        """Remove session by handle.

        Parameters
        ----------
        handle : str
            Session handle
        action : str
            Action type (expired, logoff, etc.)

        Returns
        -------
        YAbstractSession | None
            Removed session or None
        """
        session = self._sessions.pop(handle, None)
        if session:
            self._timer.expire(session)
            client = session.get_client() if hasattr(session, "get_client") else None
            if client:
                username = client.get_user_name() if hasattr(client, "get_user_name") else "unknown"
                self._audit(username, action)
        return session

    def _fail_msg(self, msg: str) -> str:
        """Create failure message XML.

        Parameters
        ----------
        msg : str
            Error message

        Returns
        -------
        str
            XML failure message
        """
        return f"<failure>{msg}</failure>"

    def _audit(self, username: str, action: str) -> None:
        """Write audit log entry.

        Parameters
        ----------
        username : str
            Username
        action : str
            Action type
        """
        # Note: Full audit logging would integrate with logging system
        logger.info("Session audit", extra={"username": username, "action": action})

    def _bad_password(self, username: str) -> str:
        """Handle bad password attempt.

        Parameters
        ----------
        username : str
            Username

        Returns
        -------
        str
            Failure message
        """
        self._audit(username, "invalid")
        return self._fail_msg("Incorrect Password")

    def _unknown_user(self, username: str) -> str:
        """Handle unknown user attempt.

        Parameters
        ----------
        username : str
            Username

        Returns
        -------
        str
            Failure message
        """
        self._audit(username, "unknown")
        return self._fail_msg(f"Unknown service or client: {username}")
