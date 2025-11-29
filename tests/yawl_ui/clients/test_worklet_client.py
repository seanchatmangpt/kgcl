"""Tests for YAWL Worklet Service client.

Tests verify:
- Running worklet retrieval
- Administration task management
- External exception handling
"""

import pytest
from httpx import AsyncClient

from kgcl.yawl_ui.clients.worklet_client import AdministrationTask, WorkletClient, WorkletRunner


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
        "connect": "handle-worklet-123",
        "checkConnection": "true",
        "disconnect": "disconnected",
        "getBuildProperties": """<properties>
            <version>5.2</version>
            <build>2022.08.22</build>
        </properties>""",
        "getRunningWorklets": """<worklets>
            <worklet>
                <caseID>case-001</caseID>
                <name>HandleException</name>
                <parentTaskID>task-001</parentTaskID>
            </worklet>
        </worklets>""",
        "getAdministrationTask": """<task>
            <id>1</id>
            <caseID>case-001</caseID>
            <itemID>item-001</itemID>
            <title>Review Exception</title>
            <scenario>ExceptionHandling</scenario>
            <process>ReviewProcess</process>
            <taskType>manual</taskType>
        </task>""",
        "getAdministrationTasks": """<tasks>
            <task>
                <id>1</id>
                <caseID>case-001</caseID>
                <itemID>item-001</itemID>
                <title>Review Exception</title>
                <scenario>ExceptionHandling</scenario>
                <process>ReviewProcess</process>
                <taskType>manual</taskType>
            </task>
        </tasks>""",
        "addAdministrationTask": """<task>
            <id>2</id>
            <caseID>case-002</caseID>
            <itemID>item-002</itemID>
            <title>New Task</title>
            <scenario>NewScenario</scenario>
            <process>NewProcess</process>
            <taskType>automated</taskType>
        </task>""",
        "removeAdministrationTask": "removed",
        "raiseCaseExternalException": "exception raised",
        "raiseItemExternalException": "exception raised",
        "getExternalTriggersForCase": """<triggers>
            <trigger>timeout</trigger>
            <trigger>error</trigger>
        </triggers>""",
        "getExternalTriggersForItem": """<triggers>
            <trigger>validation_failed</trigger>
        </triggers>""",
    }

    async def mock_post(url: str, **kwargs: dict) -> MockResponse:
        action = kwargs.get("params", {}).get("action", "")
        return MockResponse(responses.get(action, "Fail: Unknown action"))

    monkeypatch.setattr(AsyncClient, "post", mock_post)


@pytest.mark.asyncio
async def test_connect_with_service_credentials(mock_client: None) -> None:
    """Test connecting with service credentials."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")

    # Act
    await client.connect()

    # Assert
    assert client._handle == "handle-worklet-123"
    assert await client.connected()


@pytest.mark.asyncio
async def test_get_build_properties_returns_properties(mock_client: None) -> None:
    """Test getting build properties."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    props = await client.get_build_properties()

    # Assert
    assert "version" in props
    assert props["version"] == "5.2"


@pytest.mark.asyncio
async def test_get_running_worklets_returns_worklet_list(mock_client: None) -> None:
    """Test getting running worklets."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    worklets = await client.get_running_worklets()

    # Assert
    assert len(worklets) == 1
    assert isinstance(worklets[0], WorkletRunner)
    assert worklets[0].case_id == "case-001"
    assert worklets[0].worklet_name == "HandleException"
    assert worklets[0].parent_task_id == "task-001"


@pytest.mark.asyncio
async def test_get_worklet_administration_task_returns_task(mock_client: None) -> None:
    """Test getting administration task by ID."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    task = await client.get_worklet_administration_task(1)

    # Assert
    assert isinstance(task, AdministrationTask)
    assert task.task_id == 1
    assert task.case_id == "case-001"
    assert task.title == "Review Exception"


@pytest.mark.asyncio
async def test_get_worklet_administration_tasks_returns_task_list(mock_client: None) -> None:
    """Test getting all administration tasks."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    tasks = await client.get_worklet_administration_tasks()

    # Assert
    assert len(tasks) == 1
    assert isinstance(tasks[0], AdministrationTask)
    assert tasks[0].task_id == 1


@pytest.mark.asyncio
async def test_add_worklet_administration_task_returns_task_with_id(mock_client: None) -> None:
    """Test adding administration task returns task with ID."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    task = AdministrationTask(
        task_id=None,
        case_id="case-002",
        item_id="item-002",
        title="New Task",
        scenario="NewScenario",
        process="NewProcess",
        task_type="automated",
    )

    # Act
    added_task = await client.add_worklet_administration_task(task)

    # Assert
    assert added_task.task_id == 2
    assert added_task.case_id == "case-002"


@pytest.mark.asyncio
async def test_remove_worklet_administration_task_sends_request(mock_client: None) -> None:
    """Test removing administration task."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    await client.remove_worklet_administration_task(1)

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_raise_case_external_exception_sends_request(mock_client: None) -> None:
    """Test raising case external exception."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    await client.raise_case_external_exception("case-001", "timeout")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_raise_item_external_exception_sends_request(mock_client: None) -> None:
    """Test raising item external exception."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    await client.raise_item_external_exception("item-001", "validation_failed")

    # Assert - No exception raised means success


@pytest.mark.asyncio
async def test_get_external_triggers_for_case_returns_trigger_list(mock_client: None) -> None:
    """Test getting external triggers for case."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    triggers = await client.get_external_triggers_for_case("case-001")

    # Assert
    assert len(triggers) == 2
    assert "timeout" in triggers
    assert "error" in triggers


@pytest.mark.asyncio
async def test_get_external_triggers_for_item_returns_trigger_list(mock_client: None) -> None:
    """Test getting external triggers for item."""
    # Arrange
    client = WorkletClient(worklet_host="localhost", worklet_port="9095")
    await client.connect()

    # Act
    triggers = await client.get_external_triggers_for_item("item-001")

    # Assert
    assert len(triggers) == 1
    assert "validation_failed" in triggers


def test_worklet_runner_is_immutable() -> None:
    """Test WorkletRunner is immutable."""
    # Arrange
    runner = WorkletRunner(case_id="case-001", worklet_name="HandleException", parent_task_id="task-001")

    # Act & Assert
    with pytest.raises(AttributeError):
        runner.case_id = "case-002"  # type: ignore


def test_administration_task_is_immutable() -> None:
    """Test AdministrationTask is immutable."""
    # Arrange
    task = AdministrationTask(
        task_id=1,
        case_id="case-001",
        item_id="item-001",
        title="Test Task",
        scenario="TestScenario",
        process="TestProcess",
        task_type="manual",
    )

    # Act & Assert
    with pytest.raises(AttributeError):
        task.task_id = 2  # type: ignore
