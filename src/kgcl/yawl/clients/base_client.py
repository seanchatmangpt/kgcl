"""Abstract base client for YAWL services.

This module implements the AbstractClient pattern from Java, providing
connection management, event handling, and common utilities for all clients.

Java Parity:
    - AbstractClient.java: Base class with connect/disconnect/listeners
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from kgcl.yawl.clients.events import ClientAction, ClientEvent


@dataclass
class AbstractClient(ABC):
    """Base class for all YAWL service clients.

    Provides connection management, event listener handling, and common
    utilities. Mirrors Java's AbstractClient class.

    Attributes
    ----------
    _handle : str | None
        Session handle for authenticated operations
    _listeners : list[Callable[[ClientEvent], None]]
        Registered event listeners

    Notes
    -----
    Java's AbstractClient uses static listeners shared across all clients.
    This implementation uses instance-level listeners for better isolation.
    Use class-level listeners via class methods if global sharing is needed.

    Examples
    --------
    >>> class MyClient(AbstractClient):
    ...     def connect(self) -> None:
    ...         self._handle = "session-123"
    ...
    ...     def disconnect(self) -> None:
    ...         self._handle = None
    ...
    ...     def connected(self) -> bool:
    ...         return self._handle is not None
    ...
    ...     def get_build_properties(self) -> dict[str, str]:
    ...         return {"version": "5.2"}
    """

    _handle: str | None = field(default=None, repr=False)
    _listeners: list[Callable[[ClientEvent], None]] = field(default_factory=list, repr=False)

    # Class-level listeners for global event sharing (matches Java's static Set)
    _global_listeners: set[Callable[[ClientEvent], None]] = field(default_factory=set, init=False, repr=False)

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the service.

        Raises
        ------
        ConnectionError
            If connection cannot be established
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the service."""
        ...

    @abstractmethod
    def connected(self) -> bool:
        """Check if currently connected.

        Returns
        -------
        bool
            True if connected, False otherwise
        """
        ...

    @abstractmethod
    def get_build_properties(self) -> dict[str, str]:
        """Get service build properties.

        Returns
        -------
        dict[str, str]
            Map of property names to values (e.g., version, build date)
        """
        ...

    def get_handle(self) -> str:
        """Get session handle, connecting if needed.

        Returns
        -------
        str
            The session handle

        Raises
        ------
        ConnectionError
            If not connected and connection fails
        """
        self.connect()
        if self._handle is None:
            raise ConnectionError("Not connected to service")
        return self._handle

    def add_listener(self, listener: Callable[[ClientEvent], None]) -> None:
        """Register an event listener.

        Parameters
        ----------
        listener : Callable[[ClientEvent], None]
            Function to call when events occur
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ClientEvent], None]) -> None:
        """Unregister an event listener.

        Parameters
        ----------
        listener : Callable[[ClientEvent], None]
            The listener to remove
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def announce(self, event: ClientEvent) -> None:
        """Broadcast an event to all listeners.

        Parameters
        ----------
        event : ClientEvent
            The event to broadcast
        """
        for listener in self._listeners:
            listener(event)

    def announce_action(self, action: ClientAction, payload: Any) -> None:
        """Broadcast an event with the given action and payload.

        Convenience method that creates and announces a ClientEvent.

        Parameters
        ----------
        action : ClientAction
            The action type
        payload : Any
            The event payload
        """
        self.announce(ClientEvent(action=action, payload=payload))

    @classmethod
    def add_global_listener(cls, listener: Callable[[ClientEvent], None]) -> None:
        """Register a global event listener (shared across all instances).

        Mirrors Java's static listener set.

        Parameters
        ----------
        listener : Callable[[ClientEvent], None]
            Function to call when events occur
        """
        cls._global_listeners.add(listener)

    @classmethod
    def remove_global_listener(cls, listener: Callable[[ClientEvent], None]) -> None:
        """Unregister a global event listener.

        Parameters
        ----------
        listener : Callable[[ClientEvent], None]
            The listener to remove
        """
        cls._global_listeners.discard(listener)

    def _build_uri(self, host: str, port: str | int, path: str) -> str:
        """Build a service URI.

        Parameters
        ----------
        host : str
            Service hostname
        port : str | int
            Service port
        path : str
            URI path

        Returns
        -------
        str
            Formatted URI string
        """
        return f"http://{host}:{port}/{path}"
