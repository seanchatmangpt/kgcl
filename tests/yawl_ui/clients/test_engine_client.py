"""Tests for YAWL Engine client.

Tests verify:
- Connection with service and default credentials
- Specification upload and unload
- Case launching and cancellation
- Work item instance creation
- Running case retrieval
"""

import pytest
from httpx import AsyncClient, HTTPError, Response

from kgcl.yawl_ui.clients.engine_client import EngineClient, RunningCase, UploadResult, YSpecificationID


class MockResponse:
    """Mock HTTP response."""

    def __init__(self, text: str, status_code: int = 200) -> None:
        """Initialize mock response."""
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise for HTTP errors."""
        if self.status_code >= 400:
            raise HTTPError("HTTP error")


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock httpx AsyncClient."""
    responses: dict[str, str] = {
        "connect": "<success>handle-123</success>",
        "checkConnection": "<success>true</success>",
        "disconnect": "<success>disconnected</success>",
        "getBuildProperties": "<success><properties><version>5.2</version><build>2022.08.22</build></properties></success>",
        "upload": "<success>Specification uploaded successfully</success>",
        "unload": "<success>Specification unloaded</success>",
        "launchCase": "case-001",
        "cancelCase": "<success>Case cancelled</success>",
        "getAllRunningCases": """<success>
            <specifications>
                <specification id="MakeRecipe" version="0.3" uri="http://example.com">
                    <caseID>case-001</caseID>
                    <caseID>case-002</caseID>
                </specification>
            </specifications>
        </success>""",
    }

    async def mock_post(url: str, **kwargs: dict) -> MockResponse:
        action = kwargs.get("params", {}).get("action", "")
        return MockResponse(responses.get(action, "<failure>Unknown action</failure>"))

    monkeypatch.setattr(AsyncClient, "post", mock_post)


@pytest.mark.asyncio
async def test_connect_with_service_credentials(mock_client: None) -> None:
    """Test connecting with service credentials."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")

    # Act
    await client.connect()

    # Assert
    assert client._handle == "handle-123"
    assert await client.connected()


@pytest.mark.asyncio
async def test_disconnect_invalidates_handle(mock_client: None) -> None:
    """Test disconnecting invalidates session handle."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    # Act
    await client.disconnect()

    # Assert
    assert client._handle is None


@pytest.mark.asyncio
async def test_get_build_properties_returns_properties(mock_client: None) -> None:
    """Test getting build properties."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    # Act
    props = await client.get_build_properties()

    # Assert
    assert "version" in props
    assert props["version"] == "5.2"


@pytest.mark.asyncio
async def test_get_running_cases_returns_cases(mock_client: None) -> None:
    """Test getting running cases."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    # Act
    cases = await client.get_running_cases()

    # Assert
    assert len(cases) == 2
    assert isinstance(cases[0], RunningCase)
    assert cases[0].spec_id.identifier == "MakeRecipe"
    assert cases[0].case_id == "case-001"
    assert cases[1].case_id == "case-002"


@pytest.mark.asyncio
async def test_upload_specification_returns_result(mock_client: None) -> None:
    """Test uploading specification."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()
    spec_xml = "<specification>...</specification>"

    # Act
    result = await client.upload_specification(spec_xml)

    # Assert
    assert isinstance(result, UploadResult)
    assert "success" in result.message.lower()


@pytest.mark.asyncio
async def test_unload_specification_announces_event(mock_client: None) -> None:
    """Test unloading specification announces event."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    events = []
    client.add_event_listener(lambda e: events.append(e))

    spec_id = YSpecificationID(identifier="MakeRecipe", version="0.3", uri="http://example.com")

    # Act
    result = await client.unload_specification(spec_id)

    # Assert
    assert result is True
    assert len(events) == 1


@pytest.mark.asyncio
async def test_launch_case_returns_case_id(mock_client: None) -> None:
    """Test launching case returns case ID."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    spec_id = YSpecificationID(identifier="MakeRecipe", version="0.3", uri="http://example.com")
    case_data = "<data>...</data>"

    # Act
    case_id = await client.launch_case(spec_id, case_data)

    # Assert
    assert case_id == "case-001"


@pytest.mark.asyncio
async def test_cancel_case_sends_request(mock_client: None) -> None:
    """Test cancelling case sends request."""
    # Arrange
    client = EngineClient(engine_host="localhost", engine_port="8080")
    await client.connect()

    # Act
    await client.cancel_case("case-001")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_async_context_manager_lifecycle(mock_client: None) -> None:
    """Test async context manager handles lifecycle."""
    # Arrange & Act
    async with EngineClient(engine_host="localhost", engine_port="8080") as client:
        # Assert - Connected
        assert await client.connected()

    # Assert - Disconnected after context exit
    assert not await client.connected()


def test_yspecification_id_is_immutable() -> None:
    """Test YSpecificationID is immutable."""
    # Arrange
    spec_id = YSpecificationID(identifier="MakeRecipe", version="0.3", uri="http://example.com")

    # Act & Assert
    with pytest.raises(AttributeError):
        spec_id.identifier = "NewRecipe"  # type: ignore


def test_running_case_is_immutable() -> None:
    """Test RunningCase is immutable."""
    # Arrange
    spec_id = YSpecificationID(identifier="MakeRecipe", version="0.3", uri="http://example.com")
    case = RunningCase(spec_id=spec_id, case_id="case-001")

    # Act & Assert
    with pytest.raises(AttributeError):
        case.case_id = "case-002"  # type: ignore
