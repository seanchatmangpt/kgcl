"""Tests for YAWLHybridAdapter - YAWL-Hybrid Engine integration.

Chicago TDD: Tests verify YAWL events integrate with Hybrid Engine tick system.
"""

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from kgcl.yawl.integration.hybrid_adapter import WorkflowStateChange, YAWLHybridAdapter, YAWLTickReceipt
from kgcl.yawl.integration.unrdf_adapter import YAWLEvent, YAWLEventType


@pytest.fixture
def adapter() -> YAWLHybridAdapter:
    """Create YAWL-Hybrid adapter."""
    return YAWLHybridAdapter()


@pytest.fixture
def sample_event() -> YAWLEvent:
    """Create sample YAWL event."""
    return YAWLEvent(
        event_type=YAWLEventType.TASK_COMPLETED,
        case_id="case-001",
        timestamp=1700000000.0,
        spec_id="maketrip",
        task_id="register",
    )


@pytest.fixture
def mock_engine() -> MagicMock:
    """Create mock Hybrid Engine."""
    engine = MagicMock()
    engine.load_data = MagicMock()
    return engine


class TestWorkflowStateChange:
    """Tests for WorkflowStateChange dataclass."""

    def test_state_change_is_frozen(self, sample_event: YAWLEvent) -> None:
        """State change is immutable."""
        from datetime import UTC, datetime

        change = WorkflowStateChange(event=sample_event, triples=[("s", "p", "o")], timestamp=datetime.now(UTC))
        with pytest.raises(Exception):
            change.triples = []  # type: ignore[misc]

    def test_state_change_holds_triples(self, sample_event: YAWLEvent) -> None:
        """State change stores triples."""
        from datetime import UTC, datetime

        triples = [("task:1", "rdf:type", "yawl:Task")]
        change = WorkflowStateChange(event=sample_event, triples=triples, timestamp=datetime.now(UTC))

        assert change.triples == triples
        assert change.event == sample_event


class TestYAWLTickReceipt:
    """Tests for YAWLTickReceipt dataclass."""

    def test_receipt_is_frozen(self, sample_event: YAWLEvent) -> None:
        """Receipt is immutable."""
        receipt = YAWLTickReceipt(
            tick_number=1, event=sample_event, triples_added=5, provenance_id="prov:001", duration_ms=1.5
        )
        with pytest.raises(Exception):
            receipt.tick_number = 2  # type: ignore[misc]

    def test_receipt_fields(self, sample_event: YAWLEvent) -> None:
        """Receipt stores all fields."""
        receipt = YAWLTickReceipt(
            tick_number=1, event=sample_event, triples_added=5, provenance_id="prov:001", duration_ms=1.5
        )

        assert receipt.tick_number == 1
        assert receipt.event == sample_event
        assert receipt.triples_added == 5
        assert receipt.provenance_id == "prov:001"
        assert receipt.duration_ms == 1.5


class TestYAWLHybridAdapterEventQueue:
    """Tests for event queuing."""

    def test_queue_event(self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent) -> None:
        """Events can be queued."""
        adapter.queue_event(sample_event)
        pending = adapter.get_pending_events()

        assert len(pending) == 1
        assert pending[0] == sample_event

    def test_queue_multiple_events(self, adapter: YAWLHybridAdapter) -> None:
        """Multiple events can be queued."""
        events = [
            YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time()),
            YAWLEvent(event_type=YAWLEventType.TASK_ENABLED, case_id="case-001", timestamp=time.time()),
            YAWLEvent(event_type=YAWLEventType.TASK_COMPLETED, case_id="case-001", timestamp=time.time()),
        ]

        adapter.queue_events(events)
        pending = adapter.get_pending_events()

        assert len(pending) == 3

    def test_processed_events_empty_initially(self, adapter: YAWLHybridAdapter) -> None:
        """No processed events initially."""
        assert adapter.get_processed_events() == []

    def test_receipts_empty_initially(self, adapter: YAWLHybridAdapter) -> None:
        """No receipts initially."""
        assert adapter.get_receipts() == []


class TestYAWLHybridAdapterTickHook:
    """Tests for TickHook protocol implementation."""

    def test_on_pre_tick_processes_queue(
        self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent, mock_engine: MagicMock
    ) -> None:
        """on_pre_tick processes queued events."""
        adapter.queue_event(sample_event)

        result = adapter.on_pre_tick(mock_engine, tick_number=1)

        assert result is True
        assert len(adapter.get_pending_events()) == 0
        assert len(adapter.get_processed_events()) == 1

    def test_on_pre_tick_creates_receipts(
        self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent, mock_engine: MagicMock
    ) -> None:
        """on_pre_tick creates receipts."""
        adapter.queue_event(sample_event)

        adapter.on_pre_tick(mock_engine, tick_number=1)
        receipts = adapter.get_receipts()

        assert len(receipts) == 1
        assert receipts[0].tick_number == 1
        assert receipts[0].event == sample_event
        assert receipts[0].triples_added > 0

    def test_on_pre_tick_empty_queue_succeeds(self, adapter: YAWLHybridAdapter, mock_engine: MagicMock) -> None:
        """on_pre_tick succeeds with empty queue."""
        result = adapter.on_pre_tick(mock_engine, tick_number=1)

        assert result is True

    def test_on_pre_tick_loads_data_to_engine(
        self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent, mock_engine: MagicMock
    ) -> None:
        """on_pre_tick loads turtle data to engine."""
        adapter.queue_event(sample_event)

        adapter.on_pre_tick(mock_engine, tick_number=1)

        mock_engine.load_data.assert_called_once()
        turtle_data = mock_engine.load_data.call_args[0][0]
        assert "@prefix yawl:" in turtle_data
        assert "task_completed" in turtle_data

    def test_on_rule_fired_is_noop(self, adapter: YAWLHybridAdapter, mock_engine: MagicMock) -> None:
        """on_rule_fired is a no-op (does not raise)."""
        adapter.on_rule_fired(mock_engine, rule="test-rule", tick_number=1)

    def test_on_post_tick_is_noop(self, adapter: YAWLHybridAdapter, mock_engine: MagicMock) -> None:
        """on_post_tick is a no-op (does not raise)."""
        result = MagicMock()
        adapter.on_post_tick(mock_engine, result)


class TestYAWLHybridAdapterRDFConversion:
    """Tests for RDF conversion."""

    def test_event_generates_triples(self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent) -> None:
        """Events generate RDF triples."""
        triples = adapter._event_to_rdf_triples(sample_event)

        assert len(triples) >= 4  # type, eventType, caseId, timestamp
        # Check for expected predicates
        predicates = [t[1] for t in triples]
        assert any("type" in p for p in predicates)
        assert any("eventType" in p for p in predicates)
        assert any("caseId" in p for p in predicates)

    def test_event_includes_task_id(self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent) -> None:
        """Events with task_id include it."""
        triples = adapter._event_to_rdf_triples(sample_event)

        task_triples = [t for t in triples if "taskId" in t[1]]
        assert len(task_triples) == 1
        assert '"register"' in task_triples[0][2]

    def test_triples_to_turtle_format(self, adapter: YAWLHybridAdapter) -> None:
        """Triples convert to valid Turtle."""
        triples = [
            ("<urn:event:1>", "<http://example.org/type>", "<http://example.org/Event>"),
            ("<urn:event:1>", "<http://example.org/value>", '"test"'),
        ]

        turtle = adapter._triples_to_turtle(triples)

        assert "@prefix yawl:" in turtle
        assert "@prefix rdf:" in turtle
        assert "<urn:event:1>" in turtle


class TestYAWLHybridAdapterEventCreation:
    """Tests for convenience event creation methods."""

    def test_create_task_enabled_event(self, adapter: YAWLHybridAdapter) -> None:
        """Create task enabled event."""
        event = adapter.create_task_enabled_event(case_id="case-001", task_id="register", spec_id="maketrip")

        assert event.event_type == YAWLEventType.TASK_ENABLED
        assert event.case_id == "case-001"
        assert event.task_id == "register"
        assert event.spec_id == "maketrip"
        assert event.timestamp > 0

    def test_create_task_completed_event(self, adapter: YAWLHybridAdapter) -> None:
        """Create task completed event."""
        event = adapter.create_task_completed_event(
            case_id="case-001", task_id="register", spec_id="maketrip", data={"customer": "John"}
        )

        assert event.event_type == YAWLEventType.TASK_COMPLETED
        assert event.task_id == "register"
        assert event.data == {"customer": "John"}

    def test_create_token_event(self, adapter: YAWLHybridAdapter) -> None:
        """Create token event."""
        event = adapter.create_token_event(
            event_type=YAWLEventType.TOKEN_SPLIT,
            case_id="case-001",
            task_id="register",
            data={"branches": ["flight", "hotel", "car"]},
        )

        assert event.event_type == YAWLEventType.TOKEN_SPLIT
        assert event.task_id == "register"
        assert "branches" in event.data


class TestYAWLHybridAdapterHookGeneration:
    """Tests for knowledge hook generation."""

    def test_generate_task_completion_hook(self, adapter: YAWLHybridAdapter) -> None:
        """Generate task completion hook."""
        hook = adapter.generate_task_completion_hook("register")

        assert "@prefix hook:" in hook
        assert "yawl-task-register" in hook
        assert 'yawl:taskId "register"' in hook
        assert "task_completed" in hook
        assert "hook:conditionQuery" in hook

    def test_generate_case_lifecycle_hook(self, adapter: YAWLHybridAdapter) -> None:
        """Generate case lifecycle hook."""
        hook = adapter.generate_case_lifecycle_hook()

        assert "yawl-case-lifecycle" in hook
        assert "case_started" in hook
        assert "case_completed" in hook
        assert "case_cancelled" in hook

    def test_generate_wcp_sync_hook(self, adapter: YAWLHybridAdapter) -> None:
        """Generate WCP-3 synchronization hook."""
        hook = adapter.generate_wcp_sync_hook("pay", required_branches=3)

        assert "wcp3-sync-pay" in hook
        assert "token_joined" in hook
        assert "3" in hook  # required branches


class TestYAWLHybridAdapterProvenanceIntegration:
    """Tests for provenance tracking."""

    def test_provenance_recorded_on_process(
        self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent, mock_engine: MagicMock
    ) -> None:
        """Provenance is recorded when processing events."""
        adapter.queue_event(sample_event)
        adapter.on_pre_tick(mock_engine, tick_number=1)

        receipts = adapter.get_receipts()
        assert len(receipts) == 1
        assert receipts[0].provenance_id != ""

    def test_unrdf_adapter_records_event(self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent) -> None:
        """UNRDF adapter records queued events."""
        adapter.queue_event(sample_event)

        # Check UNRDF adapter has the event
        assert adapter.unrdf_adapter is not None
        history = adapter.unrdf_adapter.get_event_history()
        assert len(history) == 1
        assert history[0] == sample_event


class TestYAWLHybridAdapterMultipleTicks:
    """Tests for multi-tick scenarios."""

    def test_events_processed_once(
        self, adapter: YAWLHybridAdapter, sample_event: YAWLEvent, mock_engine: MagicMock
    ) -> None:
        """Events are only processed once."""
        adapter.queue_event(sample_event)

        adapter.on_pre_tick(mock_engine, tick_number=1)
        adapter.on_pre_tick(mock_engine, tick_number=2)

        assert len(adapter.get_processed_events()) == 1
        assert len(adapter.get_receipts()) == 1

    def test_new_events_processed_on_new_tick(self, adapter: YAWLHybridAdapter, mock_engine: MagicMock) -> None:
        """New events are processed on subsequent ticks."""
        event1 = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time())
        event2 = YAWLEvent(event_type=YAWLEventType.TASK_ENABLED, case_id="case-001", timestamp=time.time())

        adapter.queue_event(event1)
        adapter.on_pre_tick(mock_engine, tick_number=1)

        adapter.queue_event(event2)
        adapter.on_pre_tick(mock_engine, tick_number=2)

        assert len(adapter.get_processed_events()) == 2
        assert len(adapter.get_receipts()) == 2
        assert adapter.get_receipts()[0].tick_number == 1
        assert adapter.get_receipts()[1].tick_number == 2


class TestYAWLHybridAdapterAutoCommit:
    """Tests for auto-commit behavior."""

    def test_auto_commit_enabled_calls_load_data(self, sample_event: YAWLEvent, mock_engine: MagicMock) -> None:
        """Auto-commit enabled loads data to engine."""
        adapter = YAWLHybridAdapter(auto_commit=True)
        adapter.queue_event(sample_event)

        adapter.on_pre_tick(mock_engine, tick_number=1)

        mock_engine.load_data.assert_called()

    def test_auto_commit_disabled_skips_load_data(self, sample_event: YAWLEvent, mock_engine: MagicMock) -> None:
        """Auto-commit disabled skips loading data."""
        adapter = YAWLHybridAdapter(auto_commit=False)
        adapter.queue_event(sample_event)

        adapter.on_pre_tick(mock_engine, tick_number=1)

        mock_engine.load_data.assert_not_called()
