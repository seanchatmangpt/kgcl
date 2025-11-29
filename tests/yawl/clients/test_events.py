"""Tests for YAWL client event system.

Tests ClientAction, ClientEvent, and ClientEventListener protocol
matching Java's event system semantics.

Java Parity:
    - ClientEvent.java: ClientEvent, ClientEvent.Action enum (5 core actions)
    - ClientEventListener.java: ClientEventListener interface
"""

import pytest

from kgcl.yawl.clients.events import ClientAction, ClientEvent, ClientEventListener


class TestClientAction:
    """Tests for ClientAction enum."""

    def test_specification_upload_action_exists(self) -> None:
        """ClientAction has SPECIFICATION_UPLOAD matching Java."""
        assert ClientAction.SPECIFICATION_UPLOAD is not None
        assert ClientAction.SPECIFICATION_UPLOAD.name == "SPECIFICATION_UPLOAD"

    def test_specification_unload_action_exists(self) -> None:
        """ClientAction has SPECIFICATION_UNLOAD matching Java."""
        assert ClientAction.SPECIFICATION_UNLOAD is not None

    def test_launch_case_action_exists(self) -> None:
        """ClientAction has LAUNCH_CASE matching Java."""
        assert ClientAction.LAUNCH_CASE is not None

    def test_cancel_case_action_exists(self) -> None:
        """ClientAction has CANCEL_CASE (Python extension)."""
        assert ClientAction.CANCEL_CASE is not None

    def test_service_add_action_exists(self) -> None:
        """ClientAction has SERVICE_ADD matching Java."""
        assert ClientAction.SERVICE_ADD is not None

    def test_service_remove_action_exists(self) -> None:
        """ClientAction has SERVICE_REMOVE matching Java."""
        assert ClientAction.SERVICE_REMOVE is not None

    def test_work_item_update_action_exists(self) -> None:
        """ClientAction has WORK_ITEM_UPDATE (Python extension)."""
        assert ClientAction.WORK_ITEM_UPDATE is not None

    def test_all_java_actions_present(self) -> None:
        """All Java ClientEvent.Action values have Python equivalents."""
        java_actions = {
            "SpecificationUpload": ClientAction.SPECIFICATION_UPLOAD,
            "SpecificationUnload": ClientAction.SPECIFICATION_UNLOAD,
            "LaunchCase": ClientAction.LAUNCH_CASE,
            "ServiceAdd": ClientAction.SERVICE_ADD,
            "ServiceRemove": ClientAction.SERVICE_REMOVE,
        }
        for java_name, python_action in java_actions.items():
            assert python_action is not None, f"Missing action for Java {java_name}"


class TestClientEvent:
    """Tests for ClientEvent dataclass."""

    def test_create_event_with_action_and_payload(self) -> None:
        """Event can be created with action and payload."""
        event = ClientEvent(action=ClientAction.SPECIFICATION_UPLOAD, payload="spec-001")
        assert event.action == ClientAction.SPECIFICATION_UPLOAD
        assert event.payload == "spec-001"

    def test_get_action_java_parity(self) -> None:
        """Event.get_action() returns action (Java parity)."""
        event = ClientEvent(action=ClientAction.LAUNCH_CASE, payload="case-001")
        assert event.get_action() == ClientAction.LAUNCH_CASE

    def test_get_object_java_parity(self) -> None:
        """Event.get_object() returns payload (Java parity for _object field)."""
        event = ClientEvent(action=ClientAction.LAUNCH_CASE, payload="case-001")
        assert event.get_object() == "case-001"

    def test_event_is_frozen(self) -> None:
        """Event is immutable (frozen dataclass)."""
        event = ClientEvent(action=ClientAction.LAUNCH_CASE, payload="case-001")
        with pytest.raises(AttributeError):
            event.action = ClientAction.CANCEL_CASE  # type: ignore[misc]

    def test_event_str_representation(self) -> None:
        """Event has readable string representation."""
        event = ClientEvent(action=ClientAction.SPECIFICATION_UPLOAD, payload="test-spec")
        str_repr = str(event)
        assert "SPECIFICATION_UPLOAD" in str_repr
        assert "test-spec" in str_repr

    def test_event_with_complex_payload(self) -> None:
        """Event can hold complex payload objects."""
        payload = {"spec_id": "spec-001", "version": "1.0", "errors": []}
        event = ClientEvent(action=ClientAction.SPECIFICATION_UPLOAD, payload=payload)
        assert event.payload["spec_id"] == "spec-001"
        assert event.payload["version"] == "1.0"

    def test_event_with_none_payload(self) -> None:
        """Event can have None payload."""
        event = ClientEvent(action=ClientAction.SERVICE_REMOVE, payload=None)
        assert event.payload is None


class TestClientEventListener:
    """Tests for ClientEventListener protocol."""

    def test_listener_protocol_accepts_conforming_class(self) -> None:
        """Class implementing on_client_event satisfies protocol."""

        class MyListener:
            def __init__(self) -> None:
                self.events: list[ClientEvent] = []

            def on_client_event(self, event: ClientEvent) -> None:
                self.events.append(event)

        listener = MyListener()
        event = ClientEvent(action=ClientAction.LAUNCH_CASE, payload="case-001")
        listener.on_client_event(event)
        assert len(listener.events) == 1
        assert listener.events[0] == event

    def test_listener_can_be_lambda(self) -> None:
        """Lambda functions can act as listeners."""
        events_received: list[ClientEvent] = []

        def listener(event: ClientEvent) -> None:
            events_received.append(event)

        event = ClientEvent(action=ClientAction.CANCEL_CASE, payload="case-002")
        listener(event)
        assert events_received == [event]
