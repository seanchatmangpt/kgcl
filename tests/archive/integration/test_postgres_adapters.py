"""Integration tests for PostgreSQL adapters against container.

Tests verify the WorkflowAuditLogger and HookReceiptLogger can correctly:
- Connect to PostgreSQL
- Create required tables
- Log events and receipts
- Query history and statistics
- Handle concurrent operations

Examples
--------
>>> uv run pytest tests/integration/test_postgres_adapters.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from kgcl.hybrid.adapters.postgres_audit import (
    AuditEvent,
    HookReceiptLogger,
    WorkflowAuditLogger,
)

if TYPE_CHECKING:
    pass


# SQL to create required tables
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS workflow_audit (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    pattern_id INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    task_id VARCHAR(255),
    token_state JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hook_receipts (
    id SERIAL PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    condition_matched BOOLEAN NOT NULL,
    action_taken VARCHAR(50),
    duration_ms FLOAT,
    error TEXT,
    triples_affected INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflow_audit_workflow ON workflow_audit(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_audit_pattern ON workflow_audit(pattern_id);
CREATE INDEX IF NOT EXISTS idx_hook_receipts_hook ON hook_receipts(hook_id);
"""


@pytest.fixture
def postgres_connection(postgres_container: dict[str, Any]) -> Any:
    """Create a PostgreSQL connection with required tables."""
    import psycopg

    # Connect using the container URL
    conn = psycopg.connect(postgres_container["url"])

    # Create required tables
    with conn.cursor() as cursor:
        cursor.execute(CREATE_TABLES_SQL)
    conn.commit()

    yield conn

    # Cleanup
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS workflow_audit CASCADE")
        cursor.execute("DROP TABLE IF EXISTS hook_receipts CASCADE")
    conn.commit()
    conn.close()


@pytest.mark.container
class TestWorkflowAuditLogger:
    """Integration tests for WorkflowAuditLogger with PostgreSQL container."""

    def test_log_event_returns_id(self, postgres_connection: Any) -> None:
        """Verify log_event creates record and returns ID."""
        logger = WorkflowAuditLogger(postgres_connection)

        event_id = logger.log_event(
            workflow_id="WF-001",
            pattern_id=1,
            event_type="task_started",
            task_id="receive_order",
            token_state={"status": "active"},
        )

        assert event_id > 0, "Should return positive ID"

    def test_log_multiple_events(self, postgres_connection: Any) -> None:
        """Verify multiple events can be logged."""
        logger = WorkflowAuditLogger(postgres_connection)

        ids = []
        for i in range(5):
            event_id = logger.log_event(
                workflow_id="WF-002",
                pattern_id=i + 1,
                event_type=f"event_{i}",
            )
            ids.append(event_id)

        assert len(set(ids)) == 5, "All IDs should be unique"
        assert all(id > 0 for id in ids), "All IDs should be positive"

    def test_get_workflow_history(self, postgres_connection: Any) -> None:
        """Verify workflow history retrieval."""
        logger = WorkflowAuditLogger(postgres_connection)

        # Log events for a workflow
        logger.log_event(workflow_id="WF-003", pattern_id=1, event_type="start")
        logger.log_event(workflow_id="WF-003", pattern_id=1, event_type="process")
        logger.log_event(workflow_id="WF-003", pattern_id=1, event_type="complete")

        # Log event for different workflow
        logger.log_event(workflow_id="WF-OTHER", pattern_id=1, event_type="start")

        # Get history for WF-003
        history = logger.get_workflow_history("WF-003")

        assert len(history) == 3, f"Expected 3 events, got {len(history)}"
        assert all(isinstance(e, AuditEvent) for e in history)
        assert history[0].event_type == "start"
        assert history[2].event_type == "complete"

    def test_get_workflow_history_by_pattern(self, postgres_connection: Any) -> None:
        """Verify history can be filtered by pattern ID."""
        logger = WorkflowAuditLogger(postgres_connection)

        # Log events with different patterns
        logger.log_event(workflow_id="WF-004", pattern_id=1, event_type="wcp1_event")
        logger.log_event(workflow_id="WF-004", pattern_id=2, event_type="wcp2_event")
        logger.log_event(workflow_id="WF-004", pattern_id=1, event_type="wcp1_another")

        # Get only pattern 1 events
        history = logger.get_workflow_history("WF-004", pattern_id=1)

        assert len(history) == 2, f"Expected 2 events for pattern 1, got {len(history)}"
        assert all(e.pattern_id == 1 for e in history)

    def test_count_events(self, postgres_connection: Any) -> None:
        """Verify event counting."""
        logger = WorkflowAuditLogger(postgres_connection)

        logger.log_event(workflow_id="WF-005", pattern_id=1, event_type="error")
        logger.log_event(workflow_id="WF-005", pattern_id=1, event_type="error")
        logger.log_event(workflow_id="WF-005", pattern_id=1, event_type="success")

        total = logger.count_events("WF-005")
        errors = logger.count_events("WF-005", event_type="error")

        assert total == 3
        assert errors == 2

    def test_get_pattern_statistics(self, postgres_connection: Any) -> None:
        """Verify pattern statistics calculation."""
        logger = WorkflowAuditLogger(postgres_connection)

        # Log events for multiple patterns
        for _ in range(3):
            logger.log_event(workflow_id="WF-006", pattern_id=1, event_type="event")
        for _ in range(5):
            logger.log_event(workflow_id="WF-006", pattern_id=2, event_type="event")

        stats = logger.get_pattern_statistics("WF-006")

        assert stats[1] == 3
        assert stats[2] == 5

    def test_clear_workflow(self, postgres_connection: Any) -> None:
        """Verify workflow data can be cleared."""
        logger = WorkflowAuditLogger(postgres_connection)

        logger.log_event(workflow_id="WF-007", pattern_id=1, event_type="event1")
        logger.log_event(workflow_id="WF-007", pattern_id=1, event_type="event2")
        logger.log_event(workflow_id="WF-KEEP", pattern_id=1, event_type="keep")

        deleted = logger.clear_workflow("WF-007")

        assert deleted == 2
        assert logger.count_events("WF-007") == 0
        assert logger.count_events("WF-KEEP") == 1

    def test_token_state_json(self, postgres_connection: Any) -> None:
        """Verify token state is stored and retrieved as JSON."""
        logger = WorkflowAuditLogger(postgres_connection)

        token_state = {
            "status": "active",
            "count": 5,
            "flags": ["urgent", "priority"],
            "nested": {"key": "value"},
        }

        logger.log_event(
            workflow_id="WF-008",
            pattern_id=1,
            event_type="state_change",
            token_state=token_state,
        )

        history = logger.get_workflow_history("WF-008")
        assert len(history) == 1
        assert history[0].token_state == token_state


@pytest.mark.container
class TestHookReceiptLogger:
    """Integration tests for HookReceiptLogger with PostgreSQL container."""

    def test_log_receipt_returns_id(self, postgres_connection: Any) -> None:
        """Verify log_receipt creates record and returns ID."""
        logger = HookReceiptLogger(postgres_connection)

        receipt_id = logger.log_receipt(
            hook_id="HOOK-001",
            phase="PRE_TICK",
            condition_matched=True,
            action_taken="ASSERT",
            duration_ms=5.5,
            triples_affected=10,
        )

        assert receipt_id > 0, "Should return positive ID"

    def test_log_failed_receipt(self, postgres_connection: Any) -> None:
        """Verify failed hook execution can be logged."""
        logger = HookReceiptLogger(postgres_connection)

        receipt_id = logger.log_receipt(
            hook_id="HOOK-002",
            phase="ON_CHANGE",
            condition_matched=True,
            action_taken="REJECT",
            error="Validation failed: missing required field",
        )

        assert receipt_id > 0

    def test_get_hook_statistics(self, postgres_connection: Any) -> None:
        """Verify hook statistics calculation."""
        logger = HookReceiptLogger(postgres_connection)

        # Log successful executions
        for i in range(5):
            logger.log_receipt(
                hook_id="HOOK-003",
                phase="PRE_TICK",
                condition_matched=True,
                action_taken="ASSERT",
                duration_ms=10.0 + i,
                triples_affected=i + 1,
            )

        # Log failed execution
        logger.log_receipt(
            hook_id="HOOK-003",
            phase="PRE_TICK",
            condition_matched=True,
            error="Timeout",
        )

        stats = logger.get_hook_statistics("HOOK-003")

        assert stats["total"] == 6
        assert stats["error_count"] == 1
        assert stats["total_triples"] == 15  # 1+2+3+4+5
        assert stats["avg_duration_ms"] > 0

    def test_statistics_for_all_hooks(self, postgres_connection: Any) -> None:
        """Verify statistics can be retrieved for all hooks."""
        logger = HookReceiptLogger(postgres_connection)

        logger.log_receipt(hook_id="HOOK-A", phase="PRE", condition_matched=True)
        logger.log_receipt(hook_id="HOOK-B", phase="POST", condition_matched=False)

        stats = logger.get_hook_statistics()  # All hooks

        assert stats["total"] >= 2
