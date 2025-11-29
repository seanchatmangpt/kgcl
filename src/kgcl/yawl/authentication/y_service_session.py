"""Service session for custom YAWL services.

Maintains an active session belonging to a custom service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from kgcl.yawl.authentication.y_client import YClient
    from kgcl.yawl.elements.y_awl_service_reference import YAWLServiceReference
    from kgcl.yawl.engine.y_engine import YEngine
    from kgcl.yawl.exceptions.y_exceptions import YPersistenceException

from kgcl.yawl.authentication.y_session import YSession


class YServiceSession(YSession):
    """Session for custom YAWL service.

    Maintains an active session belonging to a custom service (as opposed to
    an external application client).

    Parameters
    ----------
    service : YAWLServiceReference
        The connected custom service
    timeout_seconds : int
        Maximum idle time for this session in seconds

    Examples
    --------
    >>> from kgcl.yawl.elements.y_awl_service_reference import YAWLServiceReference
    >>> service = YAWLServiceReference(service_name="MyService", uri="http://...")
    >>> session = YServiceSession(service=service, timeout_seconds=3600)
    >>> session.get_uri()
    'http://...'
    """

    def __init__(self, service: YAWLServiceReference, timeout_seconds: int) -> None:
        """Initialize service session.

        Parameters
        ----------
        service : YAWLServiceReference
            Connected custom service
        timeout_seconds : int
            Maximum idle time in seconds
        """
        super().__init__(timeout_seconds)
        self._service: YAWLServiceReference = service

    def get_uri(self) -> str | None:
        """Get service URI.

        Returns
        -------
        str | None
            URI of the service, or None if service is None
        """
        return self._service.get_uri() if self._service else None

    def get_name(self) -> str | None:
        """Get service name.

        Returns
        -------
        str | None
            Service name, or None if service is None
        """
        return self._service.get_service_name() if self._service else None

    def get_password(self) -> str | None:
        """Get service password.

        Returns
        -------
        str | None
            Hashed password of the service, or None if service is None
        """
        return self._service.get_service_password() if self._service else None

    def set_password(self, password: str) -> None:
        """Update and persist password for custom service.

        Parameters
        ----------
        password : str
            Hashed password to set

        Raises
        ------
        YPersistenceException
            If persistence operation fails
        """
        if self._service:
            from kgcl.yawl.engine.y_engine import YEngine

            self._service.set_service_password(password)
            engine = YEngine.get_instance()
            engine.update_object(self._service)

    def set_service(self, service: YAWLServiceReference) -> None:
        """Set service for this session.

        Parameters
        ----------
        service : YAWLServiceReference
            Service to set
        """
        self._service = service

    def get_client(self) -> YClient | None:
        """Get service (as client interface).

        Returns
        -------
        YClient | None
            Service associated with this session (as YClient interface)
        """
        return cast("YClient", self._service)
