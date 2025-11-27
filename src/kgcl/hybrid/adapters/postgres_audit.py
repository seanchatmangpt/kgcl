"""PostgreSQL audit logging adapter for workflow execution.

Provides persistent audit trails for workflow execution, hook receipts,
and lockchain persistence.

Examples
--------
>>> logger = WorkflowAuditLogger(connection)
>>> logger.log_event(
...     workflow_id="ORD-001",
...     pattern_id=1,
...     event_type="status_change",
...     task_id="receive_order",
...     token_state={"status": "received"},
... )  # doctest: +SKIP
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event record.

    Attributes
    ----------
    id : int | None
        Database-assigned ID (None before persistence).
    workflow_id : str
        Identifier for the workflow instance.
    pattern_id : int
        WCP pattern number (1-43).
    event_type : str
        Type of event (e.g., "status_change", "approval", "error").
    task_id : str | None
        Identifier of the task that generated the event.
    token_state : dict[str, Any] | None
        Current token state as JSON-serializable dict.
    created_at : datetime | None
        Timestamp of event creation.
    metadata : dict[str, Any] | None
        Additional event metadata.
    """

    id: int | None
    workflow_id: str
    pattern_id: int
    event_type: str
    task_id: str | None = None
    token_state: dict[str, Any] | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class WorkflowAuditLogger:
    """PostgreSQL-based audit logger for workflow execution.

    Provides methods for logging workflow events, querying audit history,
    and generating compliance reports.

    Parameters
    ----------
    connection : Any
        Active psycopg connection object.

    Examples
    --------
    >>> import psycopg
    >>> conn = psycopg.connect("postgresql://...")  # doctest: +SKIP
    >>> logger = WorkflowAuditLogger(conn)  # doctest: +SKIP
    >>> logger.log_event(workflow_id="WF-001", pattern_id=1, event_type="start")  # doctest: +SKIP
    """

    def __init__(self, connection: Any) -> None:
        """Initialize WorkflowAuditLogger.

        Parameters
        ----------
        connection : Any
            Active psycopg connection object.
        """
        self._conn = connection

    def log_event(
        self,
        workflow_id: str,
        pattern_id: int,
        event_type: str,
        task_id: str | None = None,
        token_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Log a workflow event to the audit table.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        pattern_id : int
            WCP pattern number (1-43).
        event_type : str
            Type of event.
        task_id : str | None, optional
            Identifier of the task.
        token_state : dict[str, Any] | None, optional
            Current token state.
        metadata : dict[str, Any] | None, optional
            Additional metadata.

        Returns
        -------
        int
            Database ID of the created audit record.

        Examples
        --------
        >>> logger.log_event(  # doctest: +SKIP
        ...     workflow_id="ORD-001",
        ...     pattern_id=1,
        ...     event_type="task_completed",
        ...     task_id="ship_order",
        ...     token_state={"status": "shipped"},
        ... )
        42
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workflow_audit
                    (workflow_id, pattern_id, event_type, task_id, token_state, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    workflow_id,
                    pattern_id,
                    event_type,
                    task_id,
                    json.dumps(token_state) if token_state else None,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            result = cursor.fetchone()
            self._conn.commit()
            return result[0] if result else 0

    def get_workflow_history(self, workflow_id: str, pattern_id: int | None = None) -> list[AuditEvent]:
        """Get audit history for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        pattern_id : int | None, optional
            Filter by pattern ID.

        Returns
        -------
        list[AuditEvent]
            List of audit events ordered by creation time.
        """
        query = """
            SELECT id, workflow_id, pattern_id, event_type, task_id, token_state, created_at, metadata
            FROM workflow_audit
            WHERE workflow_id = %s
        """
        params: list[Any] = [workflow_id]

        if pattern_id is not None:
            query += " AND pattern_id = %s"
            params.append(pattern_id)

        query += " ORDER BY id"

        with self._conn.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        return [
            AuditEvent(
                id=row[0],
                workflow_id=row[1],
                pattern_id=row[2],
                event_type=row[3],
                task_id=row[4],
                token_state=json.loads(row[5]) if row[5] else None,
                created_at=row[6],
                metadata=json.loads(row[7]) if row[7] else None,
            )
            for row in results
        ]

    def count_events(self, workflow_id: str, event_type: str | None = None) -> int:
        """Count events for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        event_type : str | None, optional
            Filter by event type.

        Returns
        -------
        int
            Number of matching events.
        """
        query = "SELECT COUNT(*) FROM workflow_audit WHERE workflow_id = %s"
        params: list[Any] = [workflow_id]

        if event_type is not None:
            query += " AND event_type = %s"
            params.append(event_type)

        with self._conn.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_pattern_statistics(self, workflow_id: str) -> dict[int, int]:
        """Get event counts grouped by pattern ID.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        dict[int, int]
            Mapping of pattern_id to event count.
        """
        query = """
            SELECT pattern_id, COUNT(*) as count
            FROM workflow_audit
            WHERE workflow_id = %s
            GROUP BY pattern_id
        """

        with self._conn.cursor() as cursor:
            cursor.execute(query, (workflow_id,))
            results = cursor.fetchall()

        return {row[0]: row[1] for row in results}

    def clear_workflow(self, workflow_id: str) -> int:
        """Delete all audit records for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        int
            Number of records deleted.
        """
        with self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM workflow_audit WHERE workflow_id = %s", (workflow_id,))
            deleted = cursor.rowcount
            self._conn.commit()
            return deleted


class HookReceiptLogger:
    """PostgreSQL-based logger for hook execution receipts.

    Provides persistent storage for hook execution records,
    enabling compliance auditing and performance analysis.

    Parameters
    ----------
    connection : Any
        Active psycopg connection object.
    """

    def __init__(self, connection: Any) -> None:
        """Initialize HookReceiptLogger.

        Parameters
        ----------
        connection : Any
            Active psycopg connection object.
        """
        self._conn = connection

    def log_receipt(
        self,
        hook_id: str,
        phase: str,
        condition_matched: bool,
        action_taken: str | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
        triples_affected: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Log a hook execution receipt.

        Parameters
        ----------
        hook_id : str
            Identifier for the hook.
        phase : str
            Execution phase (PRE_TICK, ON_CHANGE, etc.).
        condition_matched : bool
            Whether the hook condition matched.
        action_taken : str | None, optional
            Action that was taken (ASSERT, REJECT, etc.).
        duration_ms : float | None, optional
            Execution duration in milliseconds.
        error : str | None, optional
            Error message if execution failed.
        triples_affected : int, optional
            Number of triples modified.
        metadata : dict[str, Any] | None, optional
            Additional metadata.

        Returns
        -------
        int
            Database ID of the created receipt.
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO hook_receipts
                    (hook_id, phase, condition_matched, action_taken, duration_ms, error, triples_affected, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    hook_id,
                    phase,
                    condition_matched,
                    action_taken,
                    duration_ms,
                    error,
                    triples_affected,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            result = cursor.fetchone()
            self._conn.commit()
            return result[0] if result else 0

    def get_hook_statistics(self, hook_id: str | None = None) -> dict[str, Any]:
        """Get execution statistics for hooks.

        Parameters
        ----------
        hook_id : str | None, optional
            Filter by specific hook ID.

        Returns
        -------
        dict[str, Any]
            Statistics including total executions, avg duration, error rate.
        """
        query = """
            SELECT
                COUNT(*) as total,
                AVG(duration_ms) as avg_duration_ms,
                SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
                SUM(triples_affected) as total_triples
            FROM hook_receipts
        """
        params: list[Any] = []

        if hook_id is not None:
            query += " WHERE hook_id = %s"
            params.append(hook_id)

        with self._conn.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        if not row:
            return {"total": 0, "avg_duration_ms": 0, "error_count": 0, "total_triples": 0}

        return {
            "total": row[0] or 0,
            "avg_duration_ms": float(row[1]) if row[1] else 0,
            "error_count": row[2] or 0,
            "total_triples": row[3] or 0,
        }
