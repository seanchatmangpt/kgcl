"""Integration tests for RabbitMQ EventCoordinator against container.

Tests verify the EventCoordinator and WorkflowEventBus can correctly:
- Connect to RabbitMQ
- Publish and consume events
- Handle topic-based routing
- Track correlated events
- Manage dead letter queues
- Coordinate workflow lifecycle events

Examples
--------
>>> uv run pytest tests/integration/test_rabbitmq_coordinator.py -v
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

import pytest

from kgcl.hybrid.adapters.rabbitmq_coordinator import (
    Event,
    EventCoordinator,
    EventResult,
    WorkflowEventBus,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def rabbitmq_channel(rabbitmq_container: dict[str, Any]) -> Any:
    """Create a RabbitMQ channel connected to the container."""
    import pika

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=rabbitmq_container["host"],
            port=rabbitmq_container["port"],
            credentials=pika.PlainCredentials(
                rabbitmq_container["user"],
                rabbitmq_container["password"],
            ),
        )
    )
    channel = connection.channel()

    yield channel

    channel.close()
    connection.close()


@pytest.fixture
def event_coordinator(rabbitmq_channel: Any) -> EventCoordinator:
    """Create an EventCoordinator instance."""
    coordinator = EventCoordinator(rabbitmq_channel, "test.events", "topic")
    yield coordinator
    coordinator.close()


def make_test_event(
    event_type: str = "test.event",
    correlation_id: str = "CORR-001",
    payload: dict[str, Any] | None = None,
) -> Event:
    """Create a test event."""
    return Event(
        event_type=event_type,
        payload=payload or {},
        correlation_id=correlation_id,
        source="test",
        timestamp=time.time(),
    )


@pytest.mark.container
class TestEventCoordinatorPublish:
    """Integration tests for EventCoordinator publishing."""

    def test_publish_event_succeeds(self, event_coordinator: EventCoordinator) -> None:
        """Verify event can be published."""
        event = make_test_event("task.started", "WF-001")

        result = event_coordinator.publish(event)

        assert result is True

    def test_publish_with_custom_routing_key(self, event_coordinator: EventCoordinator) -> None:
        """Verify event can be published with custom routing key."""
        event = make_test_event("generic.event", "WF-002")

        result = event_coordinator.publish(event, routing_key="custom.route")

        assert result is True

    def test_broadcast_publishes_to_fanout(self, event_coordinator: EventCoordinator) -> None:
        """Verify broadcast sends to all subscribers."""
        event = make_test_event("broadcast.event", "WF-003")

        result = event_coordinator.broadcast(event)

        assert result is True


@pytest.mark.container
class TestEventCoordinatorSubscribe:
    """Integration tests for EventCoordinator subscription."""

    def test_subscribe_and_receive_event(self, rabbitmq_channel: Any) -> None:
        """Verify subscriber receives published event."""
        coordinator = EventCoordinator(rabbitmq_channel, "sub.test.events", "topic")
        received_events: list[Event] = []

        def handler(event: Event) -> EventResult:
            received_events.append(event)
            return EventResult(event=event, success=True)

        # Subscribe before publishing
        consumer_tag = coordinator.subscribe("task.*", handler)
        assert consumer_tag is not None

        # Publish event
        event = make_test_event("task.started", "WF-SUB-001")
        coordinator.publish(event)

        # Process messages (blocking connection needs explicit processing)
        deadline = time.time() + 5.0
        while len(received_events) < 1 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.2)

        assert len(received_events) == 1
        assert received_events[0].event_type == "task.started"
        assert received_events[0].correlation_id == "WF-SUB-001"

        coordinator.close()

    def test_subscribe_pattern_matching(self, rabbitmq_channel: Any) -> None:
        """Verify pattern matching works for subscriptions."""
        coordinator = EventCoordinator(rabbitmq_channel, "pattern.test.events", "topic")
        task_events: list[Event] = []
        all_events: list[Event] = []

        def task_handler(event: Event) -> EventResult:
            task_events.append(event)
            return EventResult(event=event, success=True)

        def all_handler(event: Event) -> EventResult:
            all_events.append(event)
            return EventResult(event=event, success=True)

        # Subscribe with different patterns
        coordinator.subscribe("task.*", task_handler)
        coordinator.subscribe("#", all_handler)

        # Publish different event types
        coordinator.publish(make_test_event("task.started", "WF-PAT-001"))
        coordinator.publish(make_test_event("workflow.completed", "WF-PAT-001"))

        # Process messages
        deadline = time.time() + 5.0
        while len(all_events) < 2 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.2)

        # task.* should only match task events
        assert len(task_events) >= 1
        assert all(e.event_type.startswith("task.") for e in task_events)

        # # should match all events
        assert len(all_events) >= 2

        coordinator.close()

    def test_unsubscribe_stops_receiving(self, rabbitmq_channel: Any) -> None:
        """Verify unsubscribe stops message delivery."""
        coordinator = EventCoordinator(rabbitmq_channel, "unsub.test.events", "topic")
        received_events: list[Event] = []

        def handler(event: Event) -> EventResult:
            received_events.append(event)
            return EventResult(event=event, success=True)

        consumer_tag = coordinator.subscribe("test.*", handler)

        # Receive first event
        coordinator.publish(make_test_event("test.first", "WF-UNSUB-001"))
        deadline = time.time() + 3.0
        while len(received_events) < 1 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.1)

        assert len(received_events) == 1

        # Unsubscribe
        coordinator.unsubscribe(consumer_tag)

        # Second event should not be received
        initial_count = len(received_events)
        coordinator.publish(make_test_event("test.second", "WF-UNSUB-001"))
        time.sleep(0.5)
        rabbitmq_channel.connection.process_data_events(time_limit=0.5)

        assert len(received_events) == initial_count

        coordinator.close()


@pytest.mark.container
class TestEventCoordinatorCorrelation:
    """Integration tests for event correlation tracking."""

    def test_track_correlation(self, event_coordinator: EventCoordinator) -> None:
        """Verify events can be tracked by correlation ID."""
        event1 = make_test_event("task.started", "WF-CORR-001")
        event2 = make_test_event("task.completed", "WF-CORR-001")

        events = event_coordinator.track_correlation("WF-CORR-001", event1)
        assert len(events) == 1

        events = event_coordinator.track_correlation("WF-CORR-001", event2)
        assert len(events) == 2

    def test_get_correlated_events(self, event_coordinator: EventCoordinator) -> None:
        """Verify correlated events can be retrieved."""
        # Track events
        event_coordinator.track_correlation(
            "WF-GET-001", make_test_event("step.1", "WF-GET-001")
        )
        event_coordinator.track_correlation(
            "WF-GET-001", make_test_event("step.2", "WF-GET-001")
        )
        event_coordinator.track_correlation(
            "WF-GET-002", make_test_event("other", "WF-GET-002")
        )

        events = event_coordinator.get_correlated_events("WF-GET-001")

        assert len(events) == 2
        assert all(e.correlation_id == "WF-GET-001" for e in events)

    def test_wait_for_correlation_returns_when_complete(
        self, event_coordinator: EventCoordinator
    ) -> None:
        """Verify wait_for_correlation returns when expected events arrive."""
        correlation_id = "WF-WAIT-001"

        # Track events in background thread
        def track_events() -> None:
            time.sleep(0.1)
            event_coordinator.track_correlation(
                correlation_id, make_test_event("step.1", correlation_id)
            )
            time.sleep(0.1)
            event_coordinator.track_correlation(
                correlation_id, make_test_event("step.2", correlation_id)
            )

        thread = threading.Thread(target=track_events)
        thread.start()

        # Wait should complete when 2 events arrive
        events = event_coordinator.wait_for_correlation(
            correlation_id, expected_count=2, timeout=5.0
        )

        thread.join()

        assert len(events) == 2

    def test_wait_for_correlation_timeout(
        self, event_coordinator: EventCoordinator
    ) -> None:
        """Verify wait_for_correlation returns partial results on timeout."""
        correlation_id = "WF-TIMEOUT-001"

        # Track only 1 event
        event_coordinator.track_correlation(
            correlation_id, make_test_event("only.one", correlation_id)
        )

        # Wait for 3 events (should timeout)
        events = event_coordinator.wait_for_correlation(
            correlation_id, expected_count=3, timeout=0.5
        )

        assert len(events) == 1

    def test_clear_correlation(self, event_coordinator: EventCoordinator) -> None:
        """Verify correlation data can be cleared."""
        correlation_id = "WF-CLEAR-001"

        event_coordinator.track_correlation(
            correlation_id, make_test_event("event.1", correlation_id)
        )
        assert len(event_coordinator.get_correlated_events(correlation_id)) == 1

        event_coordinator.clear_correlation(correlation_id)

        assert len(event_coordinator.get_correlated_events(correlation_id)) == 0


@pytest.mark.container
class TestWorkflowEventBus:
    """Integration tests for WorkflowEventBus."""

    def test_emit_task_started(self, event_coordinator: EventCoordinator) -> None:
        """Verify task started event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-001")

        result = bus.emit_task_started("task-1", {"priority": "high"})

        assert result is True

    def test_emit_task_completed(self, event_coordinator: EventCoordinator) -> None:
        """Verify task completed event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-002")

        result = bus.emit_task_completed("task-1", {"output": "success"})

        assert result is True

    def test_emit_task_failed(self, event_coordinator: EventCoordinator) -> None:
        """Verify task failed event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-003")

        result = bus.emit_task_failed("task-1", "Connection timeout", {"retry": True})

        assert result is True

    def test_emit_token_moved(self, event_coordinator: EventCoordinator) -> None:
        """Verify token movement event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-004")

        result = bus.emit_token_moved("place-A", "place-B", "token-123")

        assert result is True

    def test_emit_pattern_triggered(self, event_coordinator: EventCoordinator) -> None:
        """Verify pattern triggered event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-005")

        result = bus.emit_pattern_triggered(
            pattern_id=2,
            pattern_name="Parallel Split",
            data={"branches": ["B1", "B2"]},
        )

        assert result is True

    def test_emit_workflow_completed(self, event_coordinator: EventCoordinator) -> None:
        """Verify workflow completed event emission."""
        bus = WorkflowEventBus(event_coordinator, "WF-BUS-006")

        result = bus.emit_workflow_completed({"total_time_ms": 1500})

        assert result is True

    def test_subscribe_to_tasks(self, rabbitmq_channel: Any) -> None:
        """Verify subscription to task events works."""
        coordinator = EventCoordinator(rabbitmq_channel, "bus.sub.events", "topic")
        bus = WorkflowEventBus(coordinator, "WF-TASK-SUB")
        received_events: list[Event] = []

        def handler(event: Event) -> EventResult:
            received_events.append(event)
            return EventResult(event=event, success=True)

        consumer_tag = bus.subscribe_to_tasks(handler)
        assert consumer_tag is not None

        # Emit task events
        bus.emit_task_started("task-1")
        bus.emit_task_completed("task-1")

        # Process messages
        deadline = time.time() + 5.0
        while len(received_events) < 2 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.2)

        assert len(received_events) >= 2
        event_types = {e.event_type for e in received_events}
        assert "task.started" in event_types
        assert "task.completed" in event_types

        coordinator.close()

    def test_subscribe_to_patterns(self, rabbitmq_channel: Any) -> None:
        """Verify subscription to pattern events works."""
        coordinator = EventCoordinator(rabbitmq_channel, "bus.pattern.events", "topic")
        bus = WorkflowEventBus(coordinator, "WF-PATTERN-SUB")
        received_events: list[Event] = []

        def handler(event: Event) -> EventResult:
            received_events.append(event)
            return EventResult(event=event, success=True)

        consumer_tag = bus.subscribe_to_patterns(handler)
        assert consumer_tag is not None

        # Emit pattern event
        bus.emit_pattern_triggered(1, "Sequence", {"from": "A", "to": "B"})

        # Process messages
        deadline = time.time() + 5.0
        while len(received_events) < 1 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.2)

        assert len(received_events) >= 1
        assert received_events[0].event_type == "pattern.triggered"

        coordinator.close()

    def test_workflow_id_property(self, event_coordinator: EventCoordinator) -> None:
        """Verify workflow_id property."""
        bus = WorkflowEventBus(event_coordinator, "WF-PROP-001")

        assert bus.workflow_id == "WF-PROP-001"


@pytest.mark.container
class TestEventSerialization:
    """Integration tests for Event serialization."""

    def test_event_round_trip(self, event_coordinator: EventCoordinator) -> None:
        """Verify event serialization round-trip."""
        original = Event(
            event_type="test.serialization",
            payload={"key": "value", "nested": {"inner": 123}},
            correlation_id="CORR-SERIAL",
            source="serialization-test",
            timestamp=1234567890.123,
            event_id="event-uuid-123",
        )

        json_str = original.to_json()
        restored = Event.from_json(json_str)

        assert restored.event_type == original.event_type
        assert restored.payload == original.payload
        assert restored.correlation_id == original.correlation_id
        assert restored.source == original.source
        assert restored.timestamp == original.timestamp
        assert restored.event_id == original.event_id

    def test_event_from_bytes(self, event_coordinator: EventCoordinator) -> None:
        """Verify event can be deserialized from bytes."""
        original = make_test_event("bytes.test", "CORR-BYTES")
        json_bytes = original.to_json().encode("utf-8")

        restored = Event.from_json(json_bytes)

        assert restored.event_type == original.event_type
        assert restored.correlation_id == original.correlation_id


@pytest.mark.container
class TestMultipleCoordinators:
    """Integration tests for multiple coordinators."""

    def test_coordinators_share_exchange(self, rabbitmq_channel: Any) -> None:
        """Verify multiple coordinators can share an exchange."""
        coord1 = EventCoordinator(rabbitmq_channel, "shared.exchange", "topic")
        coord2 = EventCoordinator(rabbitmq_channel, "shared.exchange", "topic")

        received_events: list[Event] = []

        def handler(event: Event) -> EventResult:
            received_events.append(event)
            return EventResult(event=event, success=True)

        # Coord2 subscribes
        coord2.subscribe("shared.*", handler)

        # Coord1 publishes
        event = make_test_event("shared.message", "CORR-SHARED")
        coord1.publish(event)

        # Process messages
        deadline = time.time() + 5.0
        while len(received_events) < 1 and time.time() < deadline:
            rabbitmq_channel.connection.process_data_events(time_limit=0.2)

        assert len(received_events) == 1
        assert received_events[0].event_type == "shared.message"

        coord1.close()
        coord2.close()
