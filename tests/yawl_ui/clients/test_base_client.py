"""Tests for abstract base client functionality.

Tests verify:
- Connection lifecycle (connect, disconnect, check connection)
- Session handle management
- Event listener registration and notification
- URI building
- XML parsing utilities
"""

import pytest

from kgcl.yawl_ui.clients.base_client import AbstractClient, ClientEvent, ClientEventAction, ClientEventListener


class ConcreteClient(AbstractClient):
    """Concrete implementation for testing abstract client."""

    async def connect(self) -> None:
        """Simulate connection."""
        self._handle = "test-handle-123"

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._handle = None

    async def connected(self) -> bool:
        """Check connection status."""
        return self._handle is not None

    async def get_build_properties(self) -> dict[str, str]:
        """Get build properties."""
        return {"version": "1.0", "build": "123"}


class TestEventListener:
    """Test event listener implementation."""

    def __init__(self) -> None:
        """Initialize test listener."""
        self.events: list[ClientEvent] = []

    def on_client_event(self, event: ClientEvent) -> None:
        """Handle client event."""
        self.events.append(event)


@pytest.mark.asyncio
async def test_connect_obtains_session_handle() -> None:
    """Test connecting obtains session handle."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)

    # Act
    await client.connect()

    # Assert
    assert client._handle == "test-handle-123"
    assert await client.connected()


@pytest.mark.asyncio
async def test_disconnect_invalidates_session_handle() -> None:
    """Test disconnecting invalidates session handle."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    await client.connect()
    assert await client.connected()

    # Act
    await client.disconnect()

    # Assert
    assert client._handle is None
    assert not await client.connected()


@pytest.mark.asyncio
async def test_get_handle_connects_if_not_connected() -> None:
    """Test get_handle connects if not already connected."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    assert not await client.connected()

    # Act
    handle = await client.get_handle()

    # Assert
    assert handle == "test-handle-123"
    assert await client.connected()


@pytest.mark.asyncio
async def test_async_context_manager_connects_and_disconnects() -> None:
    """Test async context manager handles connection lifecycle."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    assert not await client.connected()

    # Act & Assert
    async with client:
        assert await client.connected()
        assert client._handle == "test-handle-123"

    # Verify disconnection after context exit
    assert client._handle is None
    assert not await client.connected()


def test_build_uri_formats_correctly() -> None:
    """Test URI building formats correctly."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)

    # Act
    uri = client.build_uri("example.com", "8080", "yawl/ia")

    # Assert
    assert uri == "http://example.com:8080/yawl/ia"


def test_add_event_listener_registers_listener() -> None:
    """Test adding event listener registers listener."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    listener = TestEventListener()

    # Act
    client.add_event_listener(listener)

    # Assert
    assert listener in client._listeners


def test_remove_event_listener_unregisters_listener() -> None:
    """Test removing event listener unregisters listener."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    listener = TestEventListener()
    client.add_event_listener(listener)

    # Act
    client.remove_event_listener(listener)

    # Assert
    assert listener not in client._listeners


def test_announce_event_notifies_all_listeners() -> None:
    """Test announcing event notifies all listeners."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    listener1 = TestEventListener()
    listener2 = TestEventListener()
    client.add_event_listener(listener1)
    client.add_event_listener(listener2)

    event = ClientEvent(action=ClientEventAction.LAUNCH_CASE, payload="case-001")

    # Act
    client._announce_event(event)

    # Assert
    assert len(listener1.events) == 1
    assert listener1.events[0].action == ClientEventAction.LAUNCH_CASE
    assert listener1.events[0].payload == "case-001"

    assert len(listener2.events) == 1
    assert listener2.events[0].action == ClientEventAction.LAUNCH_CASE


def test_announce_event_from_action_creates_and_announces_event() -> None:
    """Test announcing event from action creates and announces event."""
    # Arrange
    client = ConcreteClient(base_url="http://localhost:8080", timeout=30.0)
    listener = TestEventListener()
    client.add_event_listener(listener)

    # Act
    client._announce_event_from_action(ClientEventAction.SPECIFICATION_UNLOAD, "spec-001")

    # Assert
    assert len(listener.events) == 1
    assert listener.events[0].action == ClientEventAction.SPECIFICATION_UNLOAD
    assert listener.events[0].payload == "spec-001"


def test_parse_xml_properties_parses_correctly() -> None:
    """Test parsing XML properties into dictionary."""
    # Arrange
    xml = """<?xml version="1.0"?>
    <properties>
        <version>5.2</version>
        <build>2022.08.22</build>
        <author>Michael Adams</author>
    </properties>
    """

    # Act
    props = AbstractClient._parse_xml_properties(xml)

    # Assert
    assert props["version"] == "5.2"
    assert props["build"] == "2022.08.22"
    assert props["author"] == "Michael Adams"


def test_parse_xml_properties_handles_malformed_xml() -> None:
    """Test parsing malformed XML returns empty dict."""
    # Arrange
    xml = "not valid xml"

    # Act
    props = AbstractClient._parse_xml_properties(xml)

    # Assert
    assert props == {}


def test_is_successful_detects_success_tag() -> None:
    """Test detecting success tag in XML response."""
    # Arrange
    success_xml = "<success>test-handle-123</success>"
    failure_xml = "<failure>Error message</failure>"

    # Act & Assert
    assert AbstractClient._is_successful(success_xml)
    assert not AbstractClient._is_successful(failure_xml)


def test_unwrap_xml_extracts_content() -> None:
    """Test unwrapping XML content from tags."""
    # Arrange
    xml = "<success>test-handle-123</success>"

    # Act
    content = AbstractClient._unwrap_xml(xml)

    # Assert
    assert content == "test-handle-123"


def test_unwrap_xml_handles_malformed_xml() -> None:
    """Test unwrapping malformed XML returns original."""
    # Arrange
    xml = "not valid xml"

    # Act
    content = AbstractClient._unwrap_xml(xml)

    # Assert
    assert content == xml
