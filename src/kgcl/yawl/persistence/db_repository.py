"""Database repository for YAWL runtime state.

Provides CRUD operations for cases, work items, and
other runtime entities using PostgreSQL.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    pass


class DatabaseConnection(Protocol):
    """Protocol for database connections."""

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute SQL statement."""
        ...

    def fetchone(self) -> tuple[Any, ...] | None:
        """Fetch one row."""
        ...

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Fetch all rows."""
        ...

    def commit(self) -> None:
        """Commit transaction."""
        ...

    def rollback(self) -> None:
        """Rollback transaction."""
        ...


@dataclass
class DatabaseRepository:
    """Repository for YAWL runtime state persistence.

    Provides CRUD operations using PostgreSQL.

    Parameters
    ----------
    connection_factory : Callable[[], DatabaseConnection] | None
        Factory for database connections
    auto_commit : bool
        Whether to auto-commit after each operation
    """

    connection_factory: Callable[[], DatabaseConnection] | None = None
    auto_commit: bool = True
    _connection: DatabaseConnection | None = field(default=None, init=False)

    def get_connection(self) -> DatabaseConnection:
        """Get database connection.

        Returns
        -------
        DatabaseConnection
            Active connection

        Raises
        ------
        RuntimeError
            If no connection factory configured
        """
        if self._connection is not None:
            return self._connection

        if self.connection_factory is None:
            raise RuntimeError("No database connection configured")

        self._connection = self.connection_factory()
        return self._connection

    # --- Specification operations ---

    def save_specification(
        self,
        spec_id: str,
        uri: str,
        name: str,
        version: str,
        status: str,
        xml_content: str | None = None,
        documentation: str | None = None,
    ) -> bool:
        """Save specification.

        Parameters
        ----------
        spec_id : str
            Specification ID
        uri : str
            Specification URI
        name : str
            Name
        version : str
            Version
        status : str
            Status
        xml_content : str | None
            XML content
        documentation : str | None
            Documentation

        Returns
        -------
        bool
            True if saved
        """
        conn = self.get_connection()
        sql = """
            INSERT INTO yawl_specifications
            (id, uri, name, version, status, xml_content, documentation)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            uri = EXCLUDED.uri,
            name = EXCLUDED.name,
            version = EXCLUDED.version,
            status = EXCLUDED.status,
            xml_content = EXCLUDED.xml_content,
            documentation = EXCLUDED.documentation,
            updated_at = CURRENT_TIMESTAMP
        """
        conn.execute(sql, (spec_id, uri, name, version, status, xml_content, documentation))
        if self.auto_commit:
            conn.commit()
        return True

    def get_specification(self, spec_id: str) -> dict[str, Any] | None:
        """Get specification by ID.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        dict[str, Any] | None
            Specification data or None
        """
        conn = self.get_connection()
        sql = "SELECT * FROM yawl_specifications WHERE id = %s"
        conn.execute(sql, (spec_id,))
        row = conn.fetchone()
        if row:
            return self._row_to_dict(
                row,
                ["id", "uri", "name", "version", "status", "documentation", "xml_content", "created_at", "updated_at"],
            )
        return None

    def delete_specification(self, spec_id: str) -> bool:
        """Delete specification.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        bool
            True if deleted
        """
        conn = self.get_connection()
        sql = "DELETE FROM yawl_specifications WHERE id = %s"
        conn.execute(sql, (spec_id,))
        if self.auto_commit:
            conn.commit()
        return True

    # --- Case operations ---

    def save_case(
        self,
        case_id: str,
        specification_id: str,
        status: str,
        root_net_id: str | None = None,
        parent_case_id: str | None = None,
        parent_work_item_id: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """Save case.

        Parameters
        ----------
        case_id : str
            Case ID
        specification_id : str
            Specification ID
        status : str
            Status
        root_net_id : str | None
            Root net ID
        parent_case_id : str | None
            Parent case ID
        parent_work_item_id : str | None
            Parent work item ID
        started_at : datetime | None
            Start time
        completed_at : datetime | None
            Completion time

        Returns
        -------
        bool
            True if saved
        """
        conn = self.get_connection()
        sql = """
            INSERT INTO yawl_cases
            (id, specification_id, status, root_net_id, parent_case_id,
             parent_work_item_id, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            started_at = COALESCE(EXCLUDED.started_at, yawl_cases.started_at),
            completed_at = EXCLUDED.completed_at
        """
        conn.execute(
            sql,
            (
                case_id,
                specification_id,
                status,
                root_net_id,
                parent_case_id,
                parent_work_item_id,
                started_at,
                completed_at,
            ),
        )
        if self.auto_commit:
            conn.commit()
        return True

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """Get case by ID.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        dict[str, Any] | None
            Case data or None
        """
        conn = self.get_connection()
        sql = "SELECT * FROM yawl_cases WHERE id = %s"
        conn.execute(sql, (case_id,))
        row = conn.fetchone()
        if row:
            return self._row_to_dict(
                row,
                [
                    "id",
                    "specification_id",
                    "status",
                    "root_net_id",
                    "created_at",
                    "started_at",
                    "completed_at",
                    "parent_case_id",
                    "parent_work_item_id",
                ],
            )
        return None

    def find_cases_by_status(self, status: str) -> list[dict[str, Any]]:
        """Find cases by status.

        Parameters
        ----------
        status : str
            Case status

        Returns
        -------
        list[dict[str, Any]]
            Matching cases
        """
        conn = self.get_connection()
        sql = "SELECT * FROM yawl_cases WHERE status = %s ORDER BY created_at DESC"
        conn.execute(sql, (status,))
        rows = conn.fetchall()
        return [
            self._row_to_dict(
                row,
                [
                    "id",
                    "specification_id",
                    "status",
                    "root_net_id",
                    "created_at",
                    "started_at",
                    "completed_at",
                    "parent_case_id",
                    "parent_work_item_id",
                ],
            )
            for row in rows
        ]

    def delete_case(self, case_id: str) -> bool:
        """Delete case and related data.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        bool
            True if deleted
        """
        conn = self.get_connection()
        sql = "DELETE FROM yawl_cases WHERE id = %s"
        conn.execute(sql, (case_id,))
        if self.auto_commit:
            conn.commit()
        return True

    # --- Work item operations ---

    def save_work_item(
        self,
        work_item_id: str,
        case_id: str,
        task_id: str,
        net_id: str,
        status: str,
        allocated_to: str | None = None,
        started_by: str | None = None,
        completed_by: str | None = None,
        instance_number: int = 0,
        data_in: dict[str, Any] | None = None,
        data_out: dict[str, Any] | None = None,
        fired_at: datetime | None = None,
        allocated_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """Save work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        case_id : str
            Case ID
        task_id : str
            Task ID
        net_id : str
            Net ID
        status : str
            Status
        allocated_to : str | None
            Allocated participant
        started_by : str | None
            Started by participant
        completed_by : str | None
            Completed by participant
        instance_number : int
            Instance number
        data_in : dict[str, Any] | None
            Input data
        data_out : dict[str, Any] | None
            Output data
        fired_at : datetime | None
            Fired time
        allocated_at : datetime | None
            Allocated time
        started_at : datetime | None
            Started time
        completed_at : datetime | None
            Completed time

        Returns
        -------
        bool
            True if saved
        """
        conn = self.get_connection()
        sql = """
            INSERT INTO yawl_work_items
            (id, case_id, task_id, net_id, status, allocated_to, started_by,
             completed_by, instance_number, data_in, data_out, fired_at,
             allocated_at, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            allocated_to = EXCLUDED.allocated_to,
            started_by = EXCLUDED.started_by,
            completed_by = EXCLUDED.completed_by,
            data_in = EXCLUDED.data_in,
            data_out = EXCLUDED.data_out,
            fired_at = COALESCE(EXCLUDED.fired_at, yawl_work_items.fired_at),
            allocated_at = COALESCE(EXCLUDED.allocated_at, yawl_work_items.allocated_at),
            started_at = COALESCE(EXCLUDED.started_at, yawl_work_items.started_at),
            completed_at = EXCLUDED.completed_at
        """
        conn.execute(
            sql,
            (
                work_item_id,
                case_id,
                task_id,
                net_id,
                status,
                allocated_to,
                started_by,
                completed_by,
                instance_number,
                json.dumps(data_in) if data_in else None,
                json.dumps(data_out) if data_out else None,
                fired_at,
                allocated_at,
                started_at,
                completed_at,
            ),
        )
        if self.auto_commit:
            conn.commit()
        return True

    def get_work_item(self, work_item_id: str) -> dict[str, Any] | None:
        """Get work item by ID.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        dict[str, Any] | None
            Work item data or None
        """
        conn = self.get_connection()
        sql = "SELECT * FROM yawl_work_items WHERE id = %s"
        conn.execute(sql, (work_item_id,))
        row = conn.fetchone()
        if row:
            data = self._row_to_dict(
                row,
                [
                    "id",
                    "case_id",
                    "task_id",
                    "net_id",
                    "status",
                    "created_at",
                    "fired_at",
                    "allocated_at",
                    "started_at",
                    "completed_at",
                    "allocated_to",
                    "started_by",
                    "completed_by",
                    "instance_number",
                    "data_in",
                    "data_out",
                ],
            )
            # Parse JSON data
            if data.get("data_in"):
                data["data_in"] = json.loads(data["data_in"])
            if data.get("data_out"):
                data["data_out"] = json.loads(data["data_out"])
            return data
        return None

    def find_work_items_by_case(self, case_id: str) -> list[dict[str, Any]]:
        """Find work items by case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        list[dict[str, Any]]
            Work items
        """
        conn = self.get_connection()
        sql = "SELECT * FROM yawl_work_items WHERE case_id = %s ORDER BY created_at"
        conn.execute(sql, (case_id,))
        rows = conn.fetchall()
        return [
            self._row_to_dict(
                row,
                [
                    "id",
                    "case_id",
                    "task_id",
                    "net_id",
                    "status",
                    "created_at",
                    "fired_at",
                    "allocated_at",
                    "started_at",
                    "completed_at",
                    "allocated_to",
                    "started_by",
                    "completed_by",
                    "instance_number",
                    "data_in",
                    "data_out",
                ],
            )
            for row in rows
        ]

    # --- Event operations ---

    def save_event(
        self,
        event_type: str,
        case_id: str | None = None,
        work_item_id: str | None = None,
        task_id: str | None = None,
        participant_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Save event.

        Parameters
        ----------
        event_type : str
            Event type
        case_id : str | None
            Case ID
        work_item_id : str | None
            Work item ID
        task_id : str | None
            Task ID
        participant_id : str | None
            Participant ID
        data : dict[str, Any] | None
            Event data

        Returns
        -------
        bool
            True if saved
        """
        conn = self.get_connection()
        sql = """
            INSERT INTO yawl_events
            (event_type, case_id, work_item_id, task_id, participant_id, data_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        conn.execute(
            sql, (event_type, case_id, work_item_id, task_id, participant_id, json.dumps(data) if data else None)
        )
        if self.auto_commit:
            conn.commit()
        return True

    def find_events_by_case(self, case_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Find events by case.

        Parameters
        ----------
        case_id : str
            Case ID
        limit : int
            Maximum results

        Returns
        -------
        list[dict[str, Any]]
            Events
        """
        conn = self.get_connection()
        sql = """
            SELECT * FROM yawl_events
            WHERE case_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        conn.execute(sql, (case_id, limit))
        rows = conn.fetchall()
        return [
            self._row_to_dict(
                row,
                ["id", "event_type", "case_id", "work_item_id", "task_id", "participant_id", "timestamp", "data_json"],
            )
            for row in rows
        ]

    # --- Helper methods ---

    def _row_to_dict(self, row: tuple[Any, ...], columns: list[str]) -> dict[str, Any]:
        """Convert row tuple to dictionary.

        Parameters
        ----------
        row : tuple[Any, ...]
            Database row
        columns : list[str]
            Column names

        Returns
        -------
        dict[str, Any]
            Row as dictionary
        """
        return dict(zip(columns, row))
