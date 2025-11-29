"""Abstract base client for YAWL service clients.

Provides common functionality for authentication, connection management,
and event handling across all YAWL service clients.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

import httpx


class ClientEventListener(Protocol):
    """Protocol for client event listeners."""

    def on_client_event(self, event: "ClientEvent") -> None:
        """Handle client event.

        Parameters
        ----------
        event : ClientEvent
            Event to handle
        """
        ...


class ClientEventAction(str, Enum):
    """Client event action types."""

    SPECIFICATION_UNLOAD = "specification_unload"
    LAUNCH_CASE = "launch_case"
    SERVICE_ADD = "service_add"
    SERVICE_REMOVE = "service_remove"


@dataclass(frozen=True)
class ClientEvent:
    """Client event with action and payload."""

    action: ClientEventAction
    payload: Any


class AbstractClient(ABC):
    """Abstract base class for YAWL service clients.

    Provides common functionality for:
    - Authentication and session management
    - Connection lifecycle (connect, disconnect, check connection)
    - Event listener registration and notification
    - URI building
    - Build properties retrieval

    Parameters
    ----------
    base_url : str
        Base URL for the YAWL service
    timeout : float, optional
        Request timeout in seconds, by default 30.0
    """

    # Default credentials
    _DEFAULT_USERNAME = "admin"
    _DEFAULT_PASSWORD = "YAWL"

    # Service credentials
    _SERVICE_USERNAME = "yawlUI"
    _SERVICE_PASSWORD = "yYUI"

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """Initialize abstract client.

        Parameters
        ----------
        base_url : str
            Base URL for the YAWL service
        timeout : float, optional
            Request timeout in seconds, by default 30.0
        """
        self._base_url = base_url
        self._timeout = timeout
        self._handle: str | None = None
        self._client = httpx.AsyncClient(timeout=timeout)
        self._listeners: set[ClientEventListener] = set()

    async def __aenter__(self) -> "AbstractClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
        await self._client.aclose()

    @abstractmethod
    async def connect(self) -> None:
        """Connect to YAWL service and obtain session handle.

        Raises
        ------
        httpx.HTTPError
            If connection fails
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from YAWL service and invalidate session handle.

        Raises
        ------
        httpx.HTTPError
            If disconnection fails
        """
        ...

    @abstractmethod
    async def connected(self) -> bool:
        """Check if client is connected to YAWL service.

        Returns
        -------
        bool
            True if connected, False otherwise

        Raises
        ------
        httpx.HTTPError
            If connection check fails
        """
        ...

    @abstractmethod
    async def get_build_properties(self) -> dict[str, str]:
        """Get build properties from YAWL service.

        Returns
        -------
        dict[str, str]
            Build properties as key-value pairs

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        ...

    async def get_handle(self) -> str:
        """Get session handle, connecting if necessary.

        Returns
        -------
        str
            Session handle

        Raises
        ------
        httpx.HTTPError
            If connection fails
        """
        if not await self.connected():
            await self.connect()

        if self._handle is None:
            msg = "Failed to obtain session handle"
            raise RuntimeError(msg)

        return self._handle

    def build_uri(self, host: str, port: str, path: str) -> str:
        """Build URI from host, port, and path.

        Parameters
        ----------
        host : str
            Host name or IP address
        port : str
            Port number
        path : str
            URL path (without leading slash)

        Returns
        -------
        str
            Complete URI
        """
        return f"http://{host}:{port}/{path}"

    def add_event_listener(self, listener: ClientEventListener) -> None:
        """Add event listener.

        Parameters
        ----------
        listener : ClientEventListener
            Listener to add
        """
        self._listeners.add(listener)

    def remove_event_listener(self, listener: ClientEventListener) -> None:
        """Remove event listener.

        Parameters
        ----------
        listener : ClientEventListener
            Listener to remove
        """
        self._listeners.discard(listener)

    def _announce_event(self, event: ClientEvent) -> None:
        """Announce event to all listeners.

        Parameters
        ----------
        event : ClientEvent
            Event to announce
        """
        for listener in self._listeners:
            listener.on_client_event(event)

    def _announce_event_from_action(self, action: ClientEventAction, payload: Any) -> None:
        """Announce event from action and payload.

        Parameters
        ----------
        action : ClientEventAction
            Event action
        payload : Any
            Event payload
        """
        self._announce_event(ClientEvent(action=action, payload=payload))

    @staticmethod
    def _parse_xml_properties(xml: str) -> dict[str, str]:
        """Parse XML properties into dictionary.

        Parameters
        ----------
        xml : str
            XML string containing properties

        Returns
        -------
        dict[str, str]
            Parsed properties
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml)
            return {child.tag: child.text or "" for child in root}
        except ET.ParseError:
            return {}

    @staticmethod
    def _is_successful(xml: str) -> bool:
        """Check if XML response indicates success.

        Parameters
        ----------
        xml : str
            XML response

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        return xml and "<success" in xml.lower()

    @staticmethod
    def _unwrap_xml(xml: str) -> str:
        """Unwrap XML content from success/failure tags.

        Parameters
        ----------
        xml : str
            XML to unwrap

        Returns
        -------
        str
            Unwrapped content
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml)
            return root.text or ""
        except ET.ParseError:
            return xml
