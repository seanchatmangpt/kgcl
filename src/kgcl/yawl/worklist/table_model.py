"""Table model for worklist data (ports Java YWorklistTableModel).

Provides a data structure for managing tabular worklist data
without GUI dependencies, suitable for use with any UI framework.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorklistTableModel:
    """Table model for worklist data (ports Java YWorklistTableModel).

    Manages rows of worklist data in a tabular format.
    Provides methods for adding, removing, and querying rows.

    Parameters
    ----------
    column_names : list[str]
        Column names for the table
    rows : dict[str, list[Any]]
        Row data by key (caseID + taskID)

    Examples
    --------
    >>> model = WorklistTableModel(column_names=["Case ID", "Task ID", "Description", "Status"])
    >>> model.add_row("case1:task1", ["case1", "task1", "Process", "Enabled"])
    >>> row = model.get_row("case1:task1")
    """

    column_names: list[str] = field(default_factory=list)
    rows: dict[str, list[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate table model."""
        if not self.column_names:
            raise ValueError("Column names cannot be empty")

    def __repr__(self) -> str:
        """Developer representation."""
        return f"WorklistTableModel(columns={len(self.column_names)}, rows={len(self.rows)})"

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"WorklistTableModel({len(self.rows)} rows, {len(self.column_names)} columns)"

    def get_row_count(self) -> int:
        """Get number of rows.

        Returns
        -------
        int
            Number of rows

        Examples
        --------
        >>> count = model.get_row_count()
        """
        return len(self.rows)

    def get_column_count(self) -> int:
        """Get number of columns.

        Returns
        -------
        int
            Number of columns

        Examples
        --------
        >>> cols = model.get_column_count()
        """
        return len(self.column_names)

    def get_value_at(self, row_index: int, column_index: int) -> Any:
        """Get value at row and column.

        Parameters
        ----------
        row_index : int
            Row index (0-based)
        column_index : int
            Column index (0-based)

        Returns
        -------
        Any
            Cell value or None

        Examples
        --------
        >>> value = model.get_value_at(0, 0)
        """
        if row_index < 0 or row_index >= len(self.rows):
            return None

        row_keys = list(self.rows.keys())
        if row_index >= len(row_keys):
            return None

        key = row_keys[row_index]
        row = self.rows[key]
        if column_index < len(row):
            return row[column_index]
        return None

    def get_column_name(self, column_index: int) -> str:
        """Get column name.

        Parameters
        ----------
        column_index : int
            Column index

        Returns
        -------
        str
            Column name

        Examples
        --------
        >>> name = model.get_column_name(0)
        """
        if 0 <= column_index < len(self.column_names):
            return self.column_names[column_index]
        return ""

    def get_column_names(self) -> list[str]:
        """Get all column names.

        Returns
        -------
        list[str]
            Column names

        Examples
        --------
        >>> names = model.get_column_names()
        """
        return self.column_names.copy()

    def add_row(self, key: str, row_values: list[Any]) -> None:
        """Add a row to the table.

        Parameters
        ----------
        key : str
            Row key (typically caseID + taskID)
        row_values : list[Any]
            Row data values

        Examples
        --------
        >>> model.add_row("case1:task1", ["case1", "task1", "Process", "Enabled"])
        """
        if len(row_values) != len(self.column_names):
            logger.warning(
                "Row values count doesn't match column count",
                extra={"key": key, "values_count": len(row_values), "columns_count": len(self.column_names)},
            )
        self.rows[key] = row_values.copy()

    def remove_row(self, key: str) -> bool:
        """Remove a row from the table.

        Parameters
        ----------
        key : str
            Row key to remove

        Returns
        -------
        bool
            True if row was removed

        Examples
        --------
        >>> removed = model.remove_row("case1:task1")
        """
        if key in self.rows:
            del self.rows[key]
            return True
        return False

    def get_row(self, key: str) -> list[Any] | None:
        """Get row data by key.

        Parameters
        ----------
        key : str
            Row key

        Returns
        -------
        list[Any] | None
            Row data or None

        Examples
        --------
        >>> row = model.get_row("case1:task1")
        """
        return self.rows.get(key)

    def get_row_index(self, key: str) -> int:
        """Get row index by key.

        Parameters
        ----------
        key : str
            Row key

        Returns
        -------
        int
            Row index or -1 if not found

        Examples
        --------
        >>> idx = model.get_row_index("case1:task1")
        """
        row_keys = list(self.rows.keys())
        try:
            return row_keys.index(key)
        except ValueError:
            return -1

    def get_row_map(self) -> dict[str, list[Any]]:
        """Get all rows as dictionary.

        Returns
        -------
        dict[str, list[Any]]
            All rows by key

        Examples
        --------
        >>> all_rows = model.get_row_map()
        """
        return self.rows.copy()

    def clear(self) -> None:
        """Clear all rows.

        Examples
        --------
        >>> model.clear()
        """
        self.rows.clear()

    def get_output_data(self, case_id: str, task_id: str) -> str | None:
        """Get output data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID

        Returns
        -------
        str | None
            Output data XML or None

        Examples
        --------
        >>> output = model.get_output_data("case1", "task1")
        """
        key = case_id + task_id
        row = self.rows.get(key)
        if row and len(row) > 9:
            # Output data is typically at index 9
            output_params_data = row[9]
            if isinstance(output_params_data, str):
                return output_params_data
        return None

    def set_output_data(self, case_id: str, task_id: str, output_data: str) -> bool:
        """Set output data for work item.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        output_data : str
            Output data XML

        Returns
        -------
        bool
            True if successful

        Examples
        --------
        >>> success = model.set_output_data("case1", "task1", "<output>...</output>")
        """
        key = case_id + task_id
        row = self.rows.get(key)
        if row:
            # Ensure row has enough elements
            while len(row) <= 9:
                row.append(None)
            row[9] = output_data
            return True
        return False


