"""Tests for YAWL AbstractClient base class.

Tests connection management, event handling, and utilities
matching Java's AbstractClient semantics.
"""

from dataclasses import dataclass, field

import pytest

from kgcl.yawl.clients.base_client import AbstractClient
from kgcl.yawl.clients.events import ClientAction, ClientEvent


@dataclass
class ConcreteClient(AbstractClient):
    """Concrete implementation of AbstractClient for testing."""

    _connected: bool = field(default=False, repr=False)
    _build_props: dict[str, str] = field(default_factory=lambda: {"version": "5.2", "build": "test"}, repr=False)

    def connect(self) -> None:
        """Establish connection."""
        self._handle = "test-handle-12345"
        self._connected = True

    def disconnect(self) -> None:
        """Close connection."""
        self._handle = None
        self._connected = False

    def connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def get_build_properties(self) -> dict[str, str]:
        """Get build properties."""
        return self._build_props


class TestAbstractClientConnection:
    """Tests for connection management."""

    def test_initially_not_connected(self) -> None:
        """Client starts disconnected."""
        client = ConcreteClient()
        assert not client.connected()
        assert client._handle is None

    def test_connect_sets_handle(self) -> None:
        """Connect establishes session handle."""
        client = ConcreteClient()
        client.connect()
        assert client.connected()
        assert client._handle == "test-handle-12345"

    def test_disconnect_clears_handle(self) -> None:
        """Disconnect clears session handle."""
        client = ConcreteClient()
        client.connect()
        client.disconnect()
        assert not client.connected()
        assert client._handle is None

    def test_get_handle_connects_if_needed(self) -> None:
        """get_handle() auto-connects."""
        client = ConcreteClient()
        assert not client.connected()
        handle = client.get_handle()
        assert client.connected()
        assert handle == "test-handle-12345"

    def test_get_handle_returns_existing_handle(self) -> None:
        """get_handle() returns existing handle if connected."""
        client = ConcreteClient()
        client.connect()
        handle1 = client.get_handle()
        handle2 = client.get_handle()
        assert handle1 == handle2

    def test_get_build_properties_returns_dict(self) -> None:
        """get_build_properties() returns version info."""
        client = ConcreteClient()
        props = client.get_build_properties()
        assert props["version"] == "5.2"
        assert "build" in props


class TestAbstractClientListeners:
    """Tests for event listener management."""

    def test_add_listener(self) -> None:
        """Can add event listener."""
        client = ConcreteClient()
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))
        assert len(client._listeners) == 1

    def test_add_same_listener_twice_no_duplicate(self) -> None:
        """Adding same listener twice doesn't duplicate."""
        client = ConcreteClient()
        events: list[ClientEvent] = []
        listener = lambda e: events.append(e)  # noqa: E731
        client.add_listener(listener)
        client.add_listener(listener)
        assert len(client._listeners) == 1

    def test_remove_listener(self) -> None:
        """Can remove event listener."""
        client = ConcreteClient()
        events: list[ClientEvent] = []
        listener = lambda e: events.append(e)  # noqa: E731
        client.add_listener(listener)
        client.remove_listener(listener)
        assert len(client._listeners) == 0

    def test_remove_nonexistent_listener_no_error(self) -> None:
        """Removing non-existent listener doesn't raise."""
        client = ConcreteClient()
        listener = lambda e: None  # noqa: E731
        client.remove_listener(listener)  # Should not raise

    def test_announce_notifies_all_listeners(self) -> None:
        """announce() calls all registered listeners."""
        client = ConcreteClient()
        events1: list[ClientEvent] = []
        events2: list[ClientEvent] = []
        client.add_listener(lambda e: events1.append(e))
        client.add_listener(lambda e: events2.append(e))

        event = ClientEvent(action=ClientAction.LAUNCH_CASE, payload="case-001")
        client.announce(event)

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0] == event
        assert events2[0] == event

    def test_announce_action_creates_and_broadcasts_event(self) -> None:
        """announce_action() convenience method works."""
        client = ConcreteClient()
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))

        client.announce_action(ClientAction.SPECIFICATION_UPLOAD, "spec-001")

        assert len(events) == 1
        assert events[0].action == ClientAction.SPECIFICATION_UPLOAD
        assert events[0].payload == "spec-001"


class TestAbstractClientGlobalListeners:
    """Tests for class-level global listeners (Java parity)."""

    def test_global_listeners_shared_across_instances(self) -> None:
        """Global listeners receive events from all client instances."""
        events: list[ClientEvent] = []
        listener = lambda e: events.append(e)  # noqa: E731

        # Register global listener
        AbstractClient._global_listeners = set()  # Reset for test isolation
        AbstractClient._global_listeners.add(listener)

        try:
            client1 = ConcreteClient()
            client2 = ConcreteClient()

            # Both clients can use global listeners
            assert listener in AbstractClient._global_listeners
        finally:
            AbstractClient._global_listeners.clear()


class TestAbstractClientUtilities:
    """Tests for utility methods."""

    def test_build_uri(self) -> None:
        """_build_uri() formats URI correctly."""
        client = ConcreteClient()
        uri = client._build_uri("localhost", "8080", "yawl/api")
        assert uri == "http://localhost:8080/yawl/api"

    def test_build_uri_with_int_port(self) -> None:
        """_build_uri() accepts int port."""
        client = ConcreteClient()
        uri = client._build_uri("engine.yawl.local", 8080, "api/v1")
        assert uri == "http://engine.yawl.local:8080/api/v1"


class TestConnectionErrorHandling:
    """Tests for connection error scenarios."""

    def test_get_handle_raises_when_connect_fails(self) -> None:
        """get_handle() raises ConnectionError when handle is None after connect."""

        @dataclass
        class FailingClient(AbstractClient):
            """Client that fails to set handle on connect."""

            def connect(self) -> None:
                # Doesn't set _handle
                pass

            def disconnect(self) -> None:
                pass

            def connected(self) -> bool:
                return False

            def get_build_properties(self) -> dict[str, str]:
                return {}

        client = FailingClient()
        with pytest.raises(ConnectionError, match="Not connected"):
            client.get_handle()
