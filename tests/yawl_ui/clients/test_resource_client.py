"""Tests for YAWL Resource Service client.

Tests verify:
- Work queue operations (offer, allocate, start, complete)
- Participant management
- User privilege retrieval
- Queue set parsing
"""

import pytest
from httpx import AsyncClient

from kgcl.yawl_ui.clients.resource_client import Participant, QueueSet, ResourceClient, UserPrivileges


class MockResponse:
    """Mock HTTP response."""

    def __init__(self, text: str, status_code: int = 200) -> None:
        """Initialize mock response."""
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise for HTTP errors."""
        if self.status_code >= 400:
            from httpx import HTTPError

            raise HTTPError("HTTP error")


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock httpx AsyncClient."""
    responses: dict[str, str] = {
        "connect": "<success>handle-456</success>",
        "checkConnection": "<success>true</success>",
        "disconnect": "<success>disconnected</success>",
        "getAdminQueues": """<queues>
            <queue type="offered">
                <workitem id="item-001">
                    <task>Review Application</task>
                    <case>case-001</case>
                </workitem>
            </queue>
            <queue type="allocated"/>
            <queue type="started"/>
        </queues>""",
        "getParticipants": """<participants>
            <participant id="PA-001">
                <userid>jsmith</userid>
                <firstname>John</firstname>
                <lastname>Smith</lastname>
                <administrator>false</administrator>
            </participant>
        </participants>""",
        "getUserPrivileges": """<privileges>
            <canChooseItemToStart>true</canChooseItemToStart>
            <canStartConcurrent>false</canStartConcurrent>
            <canReorder>true</canReorder>
            <canViewTeamItems>true</canViewTeamItems>
            <canViewOrgGroupItems>false</canViewOrgGroupItems>
            <canChain>true</canChain>
            <canManageCases>false</canManageCases>
        </privileges>""",
    }

    async def mock_post(url: str, **kwargs: dict) -> MockResponse:
        action = kwargs.get("params", {}).get("action", "")
        return MockResponse(responses.get(action, "<failure>Unknown action</failure>"))

    monkeypatch.setattr(AsyncClient, "post", mock_post)


@pytest.mark.asyncio
async def test_connect_with_service_credentials(mock_client: None) -> None:
    """Test connecting with service credentials."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")

    # Act
    await client.connect()

    # Assert
    assert client._handle == "handle-456"
    assert await client.connected()


@pytest.mark.asyncio
async def test_get_admin_work_queues_returns_queue_set(mock_client: None) -> None:
    """Test getting admin work queues."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    queues = await client.get_admin_work_queues()

    # Assert
    assert isinstance(queues, QueueSet)
    assert len(queues.offered) == 1
    assert queues.offered[0]["id"] == "item-001"
    assert queues.offered[0]["task"] == "Review Application"
    assert len(queues.allocated) == 0
    assert len(queues.started) == 0


@pytest.mark.asyncio
async def test_get_participants_returns_participant_list(mock_client: None) -> None:
    """Test getting participants."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    participants = await client.get_participants()

    # Assert
    assert len(participants) == 1
    assert isinstance(participants[0], Participant)
    assert participants[0].id == "PA-001"
    assert participants[0].user_id == "jsmith"
    assert participants[0].first_name == "John"
    assert participants[0].last_name == "Smith"
    assert not participants[0].admin


@pytest.mark.asyncio
async def test_get_user_privileges_returns_privileges(mock_client: None) -> None:
    """Test getting user privileges."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    privileges = await client.get_user_privileges("PA-001")

    # Assert
    assert isinstance(privileges, UserPrivileges)
    assert privileges.can_choose_item_to_start
    assert not privileges.can_start_concurrent
    assert privileges.can_reorder
    assert privileges.can_view_team_items
    assert not privileges.can_view_org_group_items
    assert privileges.can_chain
    assert not privileges.can_manage_cases


@pytest.mark.asyncio
async def test_offer_item_sends_request(mock_client: None) -> None:
    """Test offering item to participants."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.offer_item("item-001", {"PA-001", "PA-002"})

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_allocate_item_sends_request(mock_client: None) -> None:
    """Test allocating item to participant."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.allocate_item("item-001", "PA-001")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_start_item_sends_request(mock_client: None) -> None:
    """Test starting item."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.start_item("item-001", "PA-001")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_complete_item_updates_data_and_completes(mock_client: None) -> None:
    """Test completing item updates data and completes."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.complete_item("item-001", "PA-001", "<data>...</data>")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_suspend_item_sends_request(mock_client: None) -> None:
    """Test suspending item."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.suspend_item("item-001", "PA-001")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_delegate_item_sends_request(mock_client: None) -> None:
    """Test delegating item."""
    # Arrange
    client = ResourceClient(resource_host="localhost", resource_port="9090")
    await client.connect()

    # Act
    await client.delegate_item("item-001", "PA-001", "PA-002")

    # Assert - No exception raised means success


def test_participant_is_immutable() -> None:
    """Test Participant is immutable."""
    # Arrange
    participant = Participant(id="PA-001", user_id="jsmith", first_name="John", last_name="Smith", admin=False)

    # Act & Assert
    with pytest.raises(AttributeError):
        participant.user_id = "jdoe"  # type: ignore


def test_queue_set_is_immutable() -> None:
    """Test QueueSet is immutable."""
    # Arrange
    queue_set = QueueSet(offered=[], allocated=[], started=[])

    # Act & Assert
    with pytest.raises(AttributeError):
        queue_set.offered = [{"id": "item-001"}]  # type: ignore
