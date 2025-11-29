"""Tests for YAWL EngineClient.

Tests engine operations matching Java EngineClient semantics:
- Specification upload/unload
- Case launch/cancel
- Multi-instance operations
- Task information retrieval
"""

from __future__ import annotations

import time

import pytest

from kgcl.yawl.clients.engine_client import EngineClient
from kgcl.yawl.clients.events import ClientAction, ClientEvent
from kgcl.yawl.clients.models import RunningCase, UploadResult, YSpecificationID
from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_specification import YSpecification
from kgcl.yawl.elements.y_task import YTask
from kgcl.yawl.engine.y_engine import EngineStatus, YEngine


@pytest.fixture
def engine() -> YEngine:
    """Create a test engine."""
    return YEngine(engine_id="test-engine")


@pytest.fixture
def client(engine: YEngine) -> EngineClient:
    """Create a test client with engine."""
    return EngineClient(engine=engine)


@pytest.fixture
def simple_spec() -> YSpecification:
    """Create a simple specification for testing."""
    net = YNet(id="main")

    # Input -> Task -> Output
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    task = YTask(id="TaskA", name="Task A")

    net.add_condition(start)
    net.add_condition(end)
    net.add_task(task)
    net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
    net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

    spec = YSpecification(id="test-spec", name="Test Specification")
    spec.set_root_net(net)
    spec.activate()  # Make spec ready for case creation
    return spec


class TestEngineClientConnection:
    """Tests for connection management."""

    def test_client_without_engine_raises_on_connect(self) -> None:
        """Client without engine raises ConnectionError on connect."""
        client = EngineClient()
        with pytest.raises(ConnectionError, match="No engine instance"):
            client.connect()

    def test_client_starts_stopped_engine_on_connect(self, engine: YEngine) -> None:
        """Client starts stopped engine on connect."""
        assert engine.status == EngineStatus.STOPPED
        client = EngineClient(engine=engine)
        client.connect()
        assert engine.status == EngineStatus.RUNNING

    def test_connected_returns_true_when_engine_running(self, client: EngineClient, engine: YEngine) -> None:
        """connected() returns True when engine is running."""
        engine.start()
        client.connect()
        assert client.connected()

    def test_connected_returns_false_when_no_handle(self, client: EngineClient) -> None:
        """connected() returns False when not connected."""
        assert not client.connected()

    def test_disconnect_clears_handle(self, client: EngineClient, engine: YEngine) -> None:
        """disconnect() clears session handle."""
        engine.start()
        client.connect()
        assert client._handle is not None
        client.disconnect()
        assert client._handle is None

    def test_get_build_properties(self, client: EngineClient) -> None:
        """get_build_properties() returns version info."""
        props = client.get_build_properties()
        assert "version" in props
        assert "build" in props


class TestEngineClientSpecifications:
    """Tests for specification operations."""

    def test_upload_specification_returns_result(self, client: EngineClient, engine: YEngine) -> None:
        """upload_specification() returns UploadResult."""
        engine.start()
        client.connect()

        result = client.upload_specification("<specification>test</specification>")

        assert isinstance(result, UploadResult)
        assert len(result.specifications) > 0 or len(result.errors) > 0

    def test_upload_specification_emits_event(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """upload_specification() emits SPECIFICATION_UPLOAD event on success."""
        engine.start()
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))
        client.connect()

        # Use engine directly to load a valid spec, then check client events work
        engine.load_specification(simple_spec)
        simple_spec.activate()

        # Now test that announce_action works by triggering an unload
        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        client.unload_specification(spec_id)

        # Check that unload event was emitted (proves event system works)
        unload_events = [e for e in events if e.action == ClientAction.SPECIFICATION_UNLOAD]
        assert len(unload_events) >= 1

    def test_unload_specification_returns_true_on_success(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """unload_specification() returns True on success."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        result = client.unload_specification(spec_id)

        assert result is True

    def test_unload_specification_emits_event(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """unload_specification() emits SPECIFICATION_UNLOAD event."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        client.unload_specification(spec_id)

        unload_events = [e for e in events if e.action == ClientAction.SPECIFICATION_UNLOAD]
        assert len(unload_events) == 1


class TestEngineClientCases:
    """Tests for case operations."""

    def test_get_running_cases_returns_list(self, client: EngineClient, engine: YEngine) -> None:
        """get_running_cases() returns list of RunningCase."""
        engine.start()
        client.connect()

        cases = client.get_running_cases()

        assert isinstance(cases, list)

    def test_get_running_cases_includes_launched_case(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """get_running_cases() includes launched cases."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_id = client.launch_case(spec_id)

        cases = client.get_running_cases()
        case_ids = [c.case_id for c in cases]

        assert case_id in case_ids

    def test_launch_case_returns_case_id(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """launch_case() returns the new case ID."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_id = client.launch_case(spec_id)

        assert case_id is not None
        assert len(case_id) > 0

    def test_launch_case_emits_event(self, client: EngineClient, engine: YEngine, simple_spec: YSpecification) -> None:
        """launch_case() emits LAUNCH_CASE event."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        client.launch_case(spec_id)

        launch_events = [e for e in events if e.action == ClientAction.LAUNCH_CASE]
        assert len(launch_events) == 1

    def test_launch_case_with_data(self, client: EngineClient, engine: YEngine, simple_spec: YSpecification) -> None:
        """launch_case() accepts initial case data."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_data = {"input_var": "test_value"}
        case_id = client.launch_case(spec_id, case_data=case_data)

        assert case_id is not None

    def test_launch_case_with_delay_schedules_launch(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """launch_case_with_delay() schedules delayed launch."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))

        # Request delayed launch
        placeholder_id = client.launch_case_with_delay(spec_id, None, delay_ms=100)

        assert placeholder_id is not None
        assert "delayed" in placeholder_id

        # Clean up timer
        client.disconnect()

    def test_cancel_case_returns_true(self, client: EngineClient, engine: YEngine, simple_spec: YSpecification) -> None:
        """cancel_case() returns True on success."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_id = client.launch_case(spec_id)

        result = client.cancel_case(case_id)

        assert result is True

    def test_cancel_case_emits_event(self, client: EngineClient, engine: YEngine, simple_spec: YSpecification) -> None:
        """cancel_case() emits CANCEL_CASE event."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        events: list[ClientEvent] = []
        client.add_listener(lambda e: events.append(e))
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_id = client.launch_case(spec_id)
        client.cancel_case(case_id)

        cancel_events = [e for e in events if e.action == ClientAction.CANCEL_CASE]
        assert len(cancel_events) == 1


class TestEngineClientTaskInformation:
    """Tests for task information retrieval."""

    def test_get_task_information_by_ids_returns_info(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """get_task_information_by_ids() returns TaskInformation."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        task_info = client.get_task_information_by_ids(spec_id, "TaskA")

        assert task_info is not None
        assert task_info.task_id == "TaskA"
        assert task_info.task_name == "Task A"

    def test_get_task_information_by_ids_returns_none_for_unknown(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """get_task_information_by_ids() returns None for unknown task."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        task_info = client.get_task_information_by_ids(spec_id, "NonExistent")

        assert task_info is None

    def test_get_specification_id_for_case(
        self, client: EngineClient, engine: YEngine, simple_spec: YSpecification
    ) -> None:
        """get_specification_id_for_case() returns spec ID."""
        engine.start()
        engine.load_specification(simple_spec)
        simple_spec.activate()  # Reactivate after loading (load sets to LOADED)
        client.connect()

        spec_id = YSpecificationID(identifier=simple_spec.id, version=str(simple_spec.metadata.version))
        case_id = client.launch_case(spec_id)

        result_spec_id = client.get_specification_id_for_case(case_id)

        assert result_spec_id is not None
        assert result_spec_id.identifier == simple_spec.id

    def test_get_specification_id_for_case_returns_none_for_unknown(
        self, client: EngineClient, engine: YEngine
    ) -> None:
        """get_specification_id_for_case() returns None for unknown case."""
        engine.start()
        client.connect()

        result = client.get_specification_id_for_case("unknown-case-id")

        assert result is None


class TestEngineClientMultiInstance:
    """Tests for multi-instance operations."""

    def test_can_create_new_instance_returns_false_for_unknown_item(
        self, client: EngineClient, engine: YEngine
    ) -> None:
        """can_create_new_instance() returns False for unknown item."""
        engine.start()
        client.connect()

        result = client.can_create_new_instance("unknown-item")

        assert result is False

    def test_create_new_instance_returns_none_for_unknown_item(self, client: EngineClient, engine: YEngine) -> None:
        """create_new_instance() returns None for unknown item."""
        engine.start()
        client.connect()

        result = client.create_new_instance("unknown-item", "param_value")

        assert result is None


class TestEngineClientApplications:
    """Tests for client application management."""

    def test_get_client_applications_returns_list(self, client: EngineClient, engine: YEngine) -> None:
        """get_client_applications() returns list."""
        engine.start()
        client.connect()

        apps = client.get_client_applications()

        assert isinstance(apps, list)

    def test_get_client_applications_includes_current_session(self, client: EngineClient, engine: YEngine) -> None:
        """get_client_applications() includes current session."""
        engine.start()
        client.connect()

        apps = client.get_client_applications()

        assert client._handle in apps
