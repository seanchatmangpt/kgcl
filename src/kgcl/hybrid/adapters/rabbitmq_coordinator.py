"""RabbitMQ Event Coordinator for workflow event coordination.

Provides event-driven coordination for workflow patterns using RabbitMQ:
- Event publishing and subscription
- Fanout, direct, and topic routing
- Correlation-based event aggregation
- Dead letter handling
- Event acknowledgment patterns

Real-World Scenarios
--------------------
- Multi-service workflow coordination
- Event sourcing for audit trails
- Pub/sub for parallel task notification
- Request/reply patterns for sync coordination
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pika import BlockingConnection
    from pika.adapters.blocking_connection import BlockingChannel


@dataclass(frozen=True)
class Event:
    """Immutable workflow event.

    Parameters
    ----------
    event_type : str
        Type/name of the event (e.g., 'task.completed')
    payload : dict[str, Any]
        Event data
    correlation_id : str
        ID for correlating related events
    source : str
        Source of the event
    timestamp : float
        Unix timestamp when event was created
    event_id : str
        Unique identifier for this event
    """

    event_type: str
    payload: dict[str, Any]
    correlation_id: str
    source: str
    timestamp: float
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> str:
        """Serialize event to JSON.

        Returns
        -------
        str
            JSON representation of the event
        """
        return json.dumps(
            {
                "event_type": self.event_type,
                "payload": self.payload,
                "correlation_id": self.correlation_id,
                "source": self.source,
                "timestamp": self.timestamp,
                "event_id": self.event_id,
            }
        )

    @classmethod
    def from_json(cls, data: str | bytes) -> Event:
        """Deserialize event from JSON.

        Parameters
        ----------
        data : str | bytes
            JSON data

        Returns
        -------
        Event
            Deserialized event
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        parsed = json.loads(data)
        return cls(
            event_type=parsed["event_type"],
            payload=parsed["payload"],
            correlation_id=parsed["correlation_id"],
            source=parsed["source"],
            timestamp=parsed["timestamp"],
            event_id=parsed.get("event_id", str(uuid.uuid4())),
        )


@dataclass(frozen=True)
class EventResult:
    """Result of event processing.

    Parameters
    ----------
    event : Event
        The processed event
    success : bool
        Whether processing succeeded
    result : Any
        Processing result data
    error : str | None
        Error message if failed
    """

    event: Event
    success: bool
    result: Any = None
    error: str | None = None


EventHandler = Callable[[Event], EventResult]


class EventCoordinator:
    """RabbitMQ-based event coordinator for workflow patterns.

    Provides reliable event coordination for distributed workflows:
    - Topic-based routing for pattern-specific events
    - Correlation tracking for related events
    - Event aggregation for sync patterns
    - Dead letter handling for failed events

    Parameters
    ----------
    channel : BlockingChannel
        RabbitMQ channel
    exchange_name : str
        Name of the exchange for events
    exchange_type : str
        Type of exchange ('topic', 'fanout', 'direct')

    Example
    -------
    >>> coordinator = EventCoordinator(channel, "workflow.events", "topic")
    >>> coordinator.publish(
    ...     Event(
    ...         event_type="task.completed",
    ...         payload={"task_id": "T1"},
    ...         correlation_id="WF-001",
    ...         source="worker-1",
    ...         timestamp=time.time(),
    ...     )
    ... )
    """

    def __init__(
        self, channel: BlockingChannel, exchange_name: str = "workflow.events", exchange_type: str = "topic"
    ) -> None:
        """Initialize the event coordinator.

        Parameters
        ----------
        channel : BlockingChannel
            RabbitMQ channel
        exchange_name : str
            Name of the exchange
        exchange_type : str
            Type of exchange
        """
        self._channel = channel
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._handlers: dict[str, list[EventHandler]] = {}
        self._correlation_events: dict[str, list[Event]] = {}
        self._correlation_locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._consumer_tags: list[str] = []
        self._setup_exchange()

    def _setup_exchange(self) -> None:
        """Set up the RabbitMQ exchange and dead letter queue."""
        # Main exchange
        self._channel.exchange_declare(
            exchange=self._exchange_name, exchange_type=self._exchange_type, durable=False, auto_delete=True
        )

        # Dead letter exchange for failed messages
        self._dlx_name = f"{self._exchange_name}.dlx"
        self._channel.exchange_declare(exchange=self._dlx_name, exchange_type="fanout", durable=False, auto_delete=True)

        # Dead letter queue
        self._dlq_name = f"{self._exchange_name}.dlq"
        self._channel.queue_declare(queue=self._dlq_name, durable=False, auto_delete=True)
        self._channel.queue_bind(queue=self._dlq_name, exchange=self._dlx_name)

    def publish(self, event: Event, routing_key: str | None = None) -> bool:
        """Publish an event to the exchange.

        Parameters
        ----------
        event : Event
            Event to publish
        routing_key : str | None
            Routing key (defaults to event_type)

        Returns
        -------
        bool
            True if published successfully
        """
        key = routing_key or event.event_type

        try:
            self._channel.basic_publish(
                exchange=self._exchange_name, routing_key=key, body=event.to_json().encode("utf-8")
            )
            return True
        except Exception:
            return False

    def subscribe(self, routing_pattern: str, handler: EventHandler, queue_name: str | None = None) -> str:
        """Subscribe to events matching a routing pattern.

        Parameters
        ----------
        routing_pattern : str
            Pattern to match (e.g., 'task.*', '#.completed')
        handler : EventHandler
            Callback function for matching events
        queue_name : str | None
            Optional queue name (auto-generated if None)

        Returns
        -------
        str
            Consumer tag for this subscription
        """
        # Create queue for this subscription
        if queue_name is None:
            result = self._channel.queue_declare(
                queue="",
                durable=False,
                exclusive=True,
                auto_delete=True,
                arguments={"x-dead-letter-exchange": self._dlx_name},
            )
            queue_name = result.method.queue
        else:
            self._channel.queue_declare(
                queue=queue_name, durable=False, auto_delete=True, arguments={"x-dead-letter-exchange": self._dlx_name}
            )

        # Bind queue to exchange
        self._channel.queue_bind(queue=queue_name, exchange=self._exchange_name, routing_key=routing_pattern)

        # Store handler
        if routing_pattern not in self._handlers:
            self._handlers[routing_pattern] = []
        self._handlers[routing_pattern].append(handler)

        # Create callback wrapper
        def callback(ch: BlockingChannel, method: Any, properties: Any, body: bytes) -> None:
            try:
                event = Event.from_json(body)
                result = handler(event)
                if result.success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    # Reject without requeue (goes to DLQ)
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            except Exception:
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        # Start consuming
        consumer_tag = self._channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        self._consumer_tags.append(consumer_tag)

        return consumer_tag

    def unsubscribe(self, consumer_tag: str) -> None:
        """Cancel a subscription.

        Parameters
        ----------
        consumer_tag : str
            Consumer tag to cancel
        """
        if consumer_tag in self._consumer_tags:
            self._channel.basic_cancel(consumer_tag)
            self._consumer_tags.remove(consumer_tag)

    def track_correlation(self, correlation_id: str, event: Event) -> list[Event]:
        """Track an event by correlation ID.

        Parameters
        ----------
        correlation_id : str
            Correlation ID to track
        event : Event
            Event to add

        Returns
        -------
        list[Event]
            All events with this correlation ID
        """
        with self._global_lock:
            if correlation_id not in self._correlation_locks:
                self._correlation_locks[correlation_id] = threading.Lock()

        lock = self._correlation_locks[correlation_id]
        with lock:
            if correlation_id not in self._correlation_events:
                self._correlation_events[correlation_id] = []
            self._correlation_events[correlation_id].append(event)
            return list(self._correlation_events[correlation_id])

    def get_correlated_events(self, correlation_id: str) -> list[Event]:
        """Get all events with a correlation ID.

        Parameters
        ----------
        correlation_id : str
            Correlation ID to query

        Returns
        -------
        list[Event]
            All events with this correlation ID
        """
        with self._global_lock:
            if correlation_id not in self._correlation_locks:
                return []

        lock = self._correlation_locks[correlation_id]
        with lock:
            return list(self._correlation_events.get(correlation_id, []))

    def wait_for_correlation(
        self, correlation_id: str, expected_count: int, timeout: float = 30.0, poll_interval: float = 0.1
    ) -> list[Event]:
        """Wait for a specific number of correlated events.

        Parameters
        ----------
        correlation_id : str
            Correlation ID to wait for
        expected_count : int
            Number of events to wait for
        timeout : float
            Maximum time to wait in seconds
        poll_interval : float
            Polling interval in seconds

        Returns
        -------
        list[Event]
            Collected events (may be fewer than expected if timeout)
        """
        start = time.time()
        while time.time() - start < timeout:
            events = self.get_correlated_events(correlation_id)
            if len(events) >= expected_count:
                return events[:expected_count]
            time.sleep(poll_interval)

        return self.get_correlated_events(correlation_id)

    def clear_correlation(self, correlation_id: str) -> None:
        """Clear tracked events for a correlation ID.

        Parameters
        ----------
        correlation_id : str
            Correlation ID to clear
        """
        with self._global_lock:
            if correlation_id in self._correlation_locks:
                lock = self._correlation_locks[correlation_id]
                with lock:
                    self._correlation_events.pop(correlation_id, None)
                del self._correlation_locks[correlation_id]

    def request_reply(self, event: Event, routing_key: str, timeout: float = 30.0) -> Event | None:
        """Send request and wait for reply (sync pattern).

        Parameters
        ----------
        event : Event
            Request event
        routing_key : str
            Routing key for request
        timeout : float
            Timeout in seconds

        Returns
        -------
        Event | None
            Reply event or None if timeout
        """
        # Create reply queue
        result = self._channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        reply_queue = result.method.queue

        # Create correlation ID for this request
        request_correlation = event.correlation_id

        reply_event: list[Event | None] = [None]
        reply_received = threading.Event()

        def reply_callback(ch: BlockingChannel, method: Any, properties: Any, body: bytes) -> None:
            received = Event.from_json(body)
            if received.correlation_id == request_correlation:
                reply_event[0] = received
                reply_received.set()
            ch.basic_ack(delivery_tag=method.delivery_tag)

        # Subscribe to reply queue
        consumer_tag = self._channel.basic_consume(
            queue=reply_queue, on_message_callback=reply_callback, auto_ack=False
        )

        # Publish request with reply-to
        self._channel.basic_publish(
            exchange=self._exchange_name,
            routing_key=routing_key,
            body=event.to_json().encode("utf-8"),
            properties={"reply_to": reply_queue},  # type: ignore[arg-type]
        )

        # Wait for reply
        start = time.time()
        while time.time() - start < timeout:
            self._channel.connection.process_data_events(time_limit=0.1)
            if reply_received.is_set():
                break

        # Cleanup
        self._channel.basic_cancel(consumer_tag)

        return reply_event[0]

    def broadcast(self, event: Event) -> bool:
        """Broadcast event to all subscribers (fanout pattern).

        Parameters
        ----------
        event : Event
            Event to broadcast

        Returns
        -------
        bool
            True if published successfully
        """
        return self.publish(event, routing_key="")

    def close(self) -> None:
        """Close coordinator and clean up resources."""
        for tag in self._consumer_tags[:]:
            try:
                self._channel.basic_cancel(tag)
            except Exception:
                pass
        self._consumer_tags.clear()
        self._handlers.clear()
        self._correlation_events.clear()


class WorkflowEventBus:
    """High-level workflow event bus built on EventCoordinator.

    Provides workflow-specific event patterns:
    - Task lifecycle events
    - Token flow events
    - Pattern-specific coordination

    Parameters
    ----------
    coordinator : EventCoordinator
        Underlying event coordinator
    workflow_id : str
        ID of the workflow this bus is for

    Example
    -------
    >>> bus = WorkflowEventBus(coordinator, "WF-001")
    >>> bus.emit_task_completed("task_1", {"result": "success"})
    """

    def __init__(self, coordinator: EventCoordinator, workflow_id: str) -> None:
        """Initialize the workflow event bus.

        Parameters
        ----------
        coordinator : EventCoordinator
            Underlying coordinator
        workflow_id : str
            Workflow ID
        """
        self._coordinator = coordinator
        self._workflow_id = workflow_id

    @property
    def workflow_id(self) -> str:
        """Get the workflow ID."""
        return self._workflow_id

    def emit_task_started(self, task_id: str, data: dict[str, Any] | None = None) -> bool:
        """Emit task started event.

        Parameters
        ----------
        task_id : str
            ID of the task
        data : dict[str, Any] | None
            Additional data

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="task.started",
            payload={"task_id": task_id, **(data or {})},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.task.started")

    def emit_task_completed(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        """Emit task completed event.

        Parameters
        ----------
        task_id : str
            ID of the task
        result : dict[str, Any] | None
            Task result

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="task.completed",
            payload={"task_id": task_id, "result": result or {}},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.task.completed")

    def emit_task_failed(self, task_id: str, error: str, data: dict[str, Any] | None = None) -> bool:
        """Emit task failed event.

        Parameters
        ----------
        task_id : str
            ID of the task
        error : str
            Error message
        data : dict[str, Any] | None
            Additional data

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="task.failed",
            payload={"task_id": task_id, "error": error, **(data or {})},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.task.failed")

    def emit_token_moved(self, from_place: str, to_place: str, token_id: str) -> bool:
        """Emit token movement event.

        Parameters
        ----------
        from_place : str
            Source place
        to_place : str
            Destination place
        token_id : str
            Token identifier

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="token.moved",
            payload={"from": from_place, "to": to_place, "token_id": token_id},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.token")

    def emit_pattern_triggered(self, pattern_id: int, pattern_name: str, data: dict[str, Any] | None = None) -> bool:
        """Emit workflow pattern triggered event.

        Parameters
        ----------
        pattern_id : int
            WCP pattern number
        pattern_name : str
            Human-readable pattern name
        data : dict[str, Any] | None
            Pattern-specific data

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="pattern.triggered",
            payload={"pattern_id": pattern_id, "pattern_name": pattern_name, **(data or {})},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.pattern")

    def emit_workflow_completed(self, final_state: dict[str, Any] | None = None) -> bool:
        """Emit workflow completed event.

        Parameters
        ----------
        final_state : dict[str, Any] | None
            Final workflow state

        Returns
        -------
        bool
            True if emitted successfully
        """
        event = Event(
            event_type="workflow.completed",
            payload={"workflow_id": self._workflow_id, "final_state": final_state or {}},
            correlation_id=self._workflow_id,
            source=f"workflow:{self._workflow_id}",
            timestamp=time.time(),
        )
        return self._coordinator.publish(event, f"workflow.{self._workflow_id}.lifecycle")

    def subscribe_to_tasks(self, handler: EventHandler) -> str:
        """Subscribe to all task events for this workflow.

        Parameters
        ----------
        handler : EventHandler
            Event handler callback

        Returns
        -------
        str
            Consumer tag
        """
        return self._coordinator.subscribe(f"workflow.{self._workflow_id}.task.*", handler)

    def subscribe_to_patterns(self, handler: EventHandler) -> str:
        """Subscribe to pattern events for this workflow.

        Parameters
        ----------
        handler : EventHandler
            Event handler callback

        Returns
        -------
        str
            Consumer tag
        """
        return self._coordinator.subscribe(f"workflow.{self._workflow_id}.pattern", handler)
