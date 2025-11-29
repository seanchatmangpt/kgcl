# Gap 8: Persistence Layer

## Problem Statement

All state is in-memory only. Engine restart loses all cases, work items, and execution state.

## Current State

```python
# src/kgcl/yawl/engine/y_engine.py
@dataclass
class YEngine:
    specifications: dict[str, YSpecification] = field(default_factory=dict)
    cases: dict[str, YCase] = field(default_factory=dict)
    net_runners: dict[str, YNetRunner] = field(default_factory=dict)
    # All in-memory, lost on restart
```

**Problem**:
- No persistence of specifications, cases, or work items
- No recovery after crash
- No distributed execution support
- No audit trail persistence

## Target Behavior

```
┌─────────────────────────────────────────────────┐
│                  YEngine                        │
│                                                 │
│  ┌─────────────┐     ┌─────────────────────┐  │
│  │ In-Memory   │ ←─► │ Persistence Layer   │  │
│  │ State       │     │                     │  │
│  │ - cases     │     │ ┌─────────────────┐ │  │
│  │ - runners   │     │ │ Repository      │ │  │
│  │ - items     │     │ │ (pluggable)     │ │  │
│  └─────────────┘     │ │                 │ │  │
│                      │ │ - SQLite        │ │  │
│                      │ │ - PostgreSQL    │ │  │
│                      │ │ - Redis         │ │  │
│                      │ │ - File          │ │  │
│                      │ └─────────────────┘ │  │
│                      └─────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Implementation Plan

### New Module: `src/kgcl/yawl/persistence/`

```
src/kgcl/yawl/persistence/
├── __init__.py
├── y_repository.py       # Abstract repository interface
├── y_memory_repo.py      # In-memory implementation (default)
├── y_sqlite_repo.py      # SQLite implementation
├── y_file_repo.py        # JSON file implementation
└── y_serialization.py    # Object serialization
```

### Step 1: Repository Interface

```python
# src/kgcl/yawl/persistence/y_repository.py
"""Abstract persistence repository for YAWL engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_specification import YSpecification
    from kgcl.yawl.engine.y_case import YCase
    from kgcl.yawl.engine.y_work_item import YWorkItem
    from kgcl.yawl.state.y_marking import YMarking


T = TypeVar("T")


class YRepository(ABC):
    """Abstract repository for YAWL persistence.

    Implementations provide storage for:
    - Workflow specifications
    - Running cases
    - Work items
    - Net marking state
    """

    # --- Specification Storage ---

    @abstractmethod
    def save_specification(self, spec: YSpecification) -> None:
        """Save workflow specification."""
        pass

    @abstractmethod
    def load_specification(self, spec_id: str) -> YSpecification | None:
        """Load specification by ID."""
        pass

    @abstractmethod
    def list_specifications(self) -> list[str]:
        """List all specification IDs."""
        pass

    @abstractmethod
    def delete_specification(self, spec_id: str) -> bool:
        """Delete specification."""
        pass

    # --- Case Storage ---

    @abstractmethod
    def save_case(self, case: YCase) -> None:
        """Save case state."""
        pass

    @abstractmethod
    def load_case(self, case_id: str) -> YCase | None:
        """Load case by ID."""
        pass

    @abstractmethod
    def list_cases(
        self,
        specification_id: str | None = None,
        status: str | None = None,
    ) -> list[str]:
        """List case IDs with optional filters."""
        pass

    @abstractmethod
    def delete_case(self, case_id: str) -> bool:
        """Delete case and its work items."""
        pass

    # --- Work Item Storage ---

    @abstractmethod
    def save_work_item(self, work_item: YWorkItem) -> None:
        """Save work item state."""
        pass

    @abstractmethod
    def load_work_item(self, work_item_id: str) -> YWorkItem | None:
        """Load work item by ID."""
        pass

    @abstractmethod
    def list_work_items(
        self,
        case_id: str | None = None,
        status: str | None = None,
        resource_id: str | None = None,
    ) -> list[str]:
        """List work item IDs with optional filters."""
        pass

    # --- Marking Storage ---

    @abstractmethod
    def save_marking(
        self, case_id: str, net_id: str, marking: YMarking
    ) -> None:
        """Save net marking for case."""
        pass

    @abstractmethod
    def load_marking(self, case_id: str, net_id: str) -> YMarking | None:
        """Load net marking for case."""
        pass

    # --- Transaction Support ---

    def begin_transaction(self) -> None:
        """Begin atomic transaction (optional)."""
        pass

    def commit_transaction(self) -> None:
        """Commit transaction (optional)."""
        pass

    def rollback_transaction(self) -> None:
        """Rollback transaction (optional)."""
        pass
```

### Step 2: In-Memory Repository (Default)

```python
# src/kgcl/yawl/persistence/y_memory_repo.py
"""In-memory repository implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kgcl.yawl.persistence.y_repository import YRepository


@dataclass
class YMemoryRepository(YRepository):
    """In-memory repository (default, non-persistent).

    Stores all data in memory. Data is lost on restart.
    Useful for testing and simple deployments.
    """

    _specifications: dict[str, Any] = field(default_factory=dict)
    _cases: dict[str, Any] = field(default_factory=dict)
    _work_items: dict[str, Any] = field(default_factory=dict)
    _markings: dict[str, Any] = field(default_factory=dict)  # key: "case:net"

    def save_specification(self, spec) -> None:
        self._specifications[spec.id] = spec

    def load_specification(self, spec_id: str):
        return self._specifications.get(spec_id)

    def list_specifications(self) -> list[str]:
        return list(self._specifications.keys())

    def delete_specification(self, spec_id: str) -> bool:
        if spec_id in self._specifications:
            del self._specifications[spec_id]
            return True
        return False

    def save_case(self, case) -> None:
        self._cases[case.id] = case

    def load_case(self, case_id: str):
        return self._cases.get(case_id)

    def list_cases(self, specification_id=None, status=None) -> list[str]:
        result = []
        for case_id, case in self._cases.items():
            if specification_id and case.specification_id != specification_id:
                continue
            if status and case.status.name != status:
                continue
            result.append(case_id)
        return result

    def delete_case(self, case_id: str) -> bool:
        if case_id in self._cases:
            # Delete associated work items
            case = self._cases[case_id]
            for wi_id in list(case.work_items.keys()):
                self._work_items.pop(wi_id, None)
            del self._cases[case_id]
            return True
        return False

    def save_work_item(self, work_item) -> None:
        self._work_items[work_item.id] = work_item

    def load_work_item(self, work_item_id: str):
        return self._work_items.get(work_item_id)

    def list_work_items(self, case_id=None, status=None, resource_id=None) -> list[str]:
        result = []
        for wi_id, wi in self._work_items.items():
            if case_id and wi.case_id != case_id:
                continue
            if status and wi.status.name != status:
                continue
            if resource_id and wi.resource_id != resource_id:
                continue
            result.append(wi_id)
        return result

    def save_marking(self, case_id: str, net_id: str, marking) -> None:
        key = f"{case_id}:{net_id}"
        self._markings[key] = marking

    def load_marking(self, case_id: str, net_id: str):
        key = f"{case_id}:{net_id}"
        return self._markings.get(key)
```

### Step 3: Serialization

```python
# src/kgcl/yawl/persistence/y_serialization.py
"""Serialization utilities for YAWL objects."""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class YSerializer:
    """Serializer for YAWL dataclass objects.

    Converts dataclasses to/from JSON-compatible dictionaries.
    Handles enums, datetimes, and nested dataclasses.
    """

    def serialize(self, obj: Any) -> dict[str, Any]:
        """Serialize object to dictionary.

        Parameters
        ----------
        obj : Any
            Object to serialize (must be dataclass)

        Returns
        -------
        dict[str, Any]
            JSON-compatible dictionary
        """
        if obj is None:
            return None

        if is_dataclass(obj) and not isinstance(obj, type):
            result = {}
            for field in fields(obj):
                value = getattr(obj, field.name)
                result[field.name] = self._serialize_value(value)
            result["__type__"] = type(obj).__name__
            return result

        return self._serialize_value(obj)

    def _serialize_value(self, value: Any) -> Any:
        """Serialize individual value."""
        if value is None:
            return None
        if isinstance(value, Enum):
            return {"__enum__": type(value).__name__, "value": value.value}
        if isinstance(value, datetime):
            return {"__datetime__": value.isoformat()}
        if isinstance(value, (set, frozenset)):
            return {"__set__": [self._serialize_value(v) for v in value]}
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        if is_dataclass(value) and not isinstance(value, type):
            return self.serialize(value)
        return value

    def deserialize(
        self, data: dict[str, Any], type_registry: dict[str, type]
    ) -> Any:
        """Deserialize dictionary to object.

        Parameters
        ----------
        data : dict[str, Any]
            Serialized dictionary
        type_registry : dict[str, type]
            Map of type names to classes

        Returns
        -------
        Any
            Deserialized object
        """
        if data is None:
            return None

        if isinstance(data, dict):
            if "__type__" in data:
                type_name = data.pop("__type__")
                cls = type_registry.get(type_name)
                if cls is None:
                    raise ValueError(f"Unknown type: {type_name}")
                kwargs = {
                    k: self._deserialize_value(v, type_registry)
                    for k, v in data.items()
                }
                return cls(**kwargs)

            if "__enum__" in data:
                enum_name = data["__enum__"]
                enum_cls = type_registry.get(enum_name)
                if enum_cls:
                    return enum_cls(data["value"])
                return data["value"]

            if "__datetime__" in data:
                return datetime.fromisoformat(data["__datetime__"])

            if "__set__" in data:
                return set(
                    self._deserialize_value(v, type_registry)
                    for v in data["__set__"]
                )

        return data

    def _deserialize_value(
        self, value: Any, type_registry: dict[str, type]
    ) -> Any:
        """Deserialize individual value."""
        if isinstance(value, dict):
            return self.deserialize(value, type_registry)
        if isinstance(value, list):
            return [self._deserialize_value(v, type_registry) for v in value]
        return value


def to_json(obj: Any) -> str:
    """Serialize object to JSON string."""
    serializer = YSerializer()
    return json.dumps(serializer.serialize(obj), indent=2)


def from_json(json_str: str, type_registry: dict[str, type]) -> Any:
    """Deserialize object from JSON string."""
    serializer = YSerializer()
    data = json.loads(json_str)
    return serializer.deserialize(data, type_registry)
```

### Step 4: SQLite Repository

```python
# src/kgcl/yawl/persistence/y_sqlite_repo.py
"""SQLite-based persistence repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kgcl.yawl.persistence.y_repository import YRepository
from kgcl.yawl.persistence.y_serialization import YSerializer


@dataclass
class YSQLiteRepository(YRepository):
    """SQLite-based repository for YAWL persistence.

    Parameters
    ----------
    db_path : str | Path
        Path to SQLite database file
    """

    db_path: str | Path
    _conn: sqlite3.Connection | None = field(default=None, repr=False)
    _serializer: YSerializer = field(default_factory=YSerializer, repr=False)
    _type_registry: dict[str, type] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Initialize database connection and schema."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()

    def _create_schema(self) -> None:
        """Create database tables."""
        cursor = self._conn.cursor()

        # Specifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS specifications (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                specification_id TEXT NOT NULL,
                status TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_spec
            ON cases(specification_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_status
            ON cases(status)
        """)

        # Work items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                resource_id TEXT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wi_case
            ON work_items(case_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wi_status
            ON work_items(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wi_resource
            ON work_items(resource_id)
        """)

        # Markings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markings (
                case_id TEXT NOT NULL,
                net_id TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (case_id, net_id)
            )
        """)

        self._conn.commit()

    def set_type_registry(self, registry: dict[str, type]) -> None:
        """Set type registry for deserialization."""
        self._type_registry = registry

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Specification Storage ---

    def save_specification(self, spec) -> None:
        import json
        cursor = self._conn.cursor()
        data = json.dumps(self._serializer.serialize(spec))
        cursor.execute("""
            INSERT OR REPLACE INTO specifications (id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (spec.id, data))
        self._conn.commit()

    def load_specification(self, spec_id: str):
        import json
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT data FROM specifications WHERE id = ?",
            (spec_id,)
        )
        row = cursor.fetchone()
        if row:
            data = json.loads(row[0])
            return self._serializer.deserialize(data, self._type_registry)
        return None

    def list_specifications(self) -> list[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM specifications")
        return [row[0] for row in cursor.fetchall()]

    def delete_specification(self, spec_id: str) -> bool:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM specifications WHERE id = ?", (spec_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # --- Case Storage ---

    def save_case(self, case) -> None:
        import json
        cursor = self._conn.cursor()
        data = json.dumps(self._serializer.serialize(case))
        cursor.execute("""
            INSERT OR REPLACE INTO cases
            (id, specification_id, status, data, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (case.id, case.specification_id, case.status.name, data))
        self._conn.commit()

    def load_case(self, case_id: str):
        import json
        cursor = self._conn.cursor()
        cursor.execute("SELECT data FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        if row:
            data = json.loads(row[0])
            return self._serializer.deserialize(data, self._type_registry)
        return None

    def list_cases(self, specification_id=None, status=None) -> list[str]:
        cursor = self._conn.cursor()
        query = "SELECT id FROM cases WHERE 1=1"
        params = []
        if specification_id:
            query += " AND specification_id = ?"
            params.append(specification_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        cursor.execute(query, params)
        return [row[0] for row in cursor.fetchall()]

    def delete_case(self, case_id: str) -> bool:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM work_items WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM markings WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    # --- Work Item Storage ---

    def save_work_item(self, work_item) -> None:
        import json
        cursor = self._conn.cursor()
        data = json.dumps(self._serializer.serialize(work_item))
        cursor.execute("""
            INSERT OR REPLACE INTO work_items
            (id, case_id, task_id, status, resource_id, data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            work_item.id,
            work_item.case_id,
            work_item.task_id,
            work_item.status.name,
            work_item.resource_id,
            data,
        ))
        self._conn.commit()

    def load_work_item(self, work_item_id: str):
        import json
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT data FROM work_items WHERE id = ?",
            (work_item_id,)
        )
        row = cursor.fetchone()
        if row:
            data = json.loads(row[0])
            return self._serializer.deserialize(data, self._type_registry)
        return None

    def list_work_items(self, case_id=None, status=None, resource_id=None) -> list[str]:
        cursor = self._conn.cursor()
        query = "SELECT id FROM work_items WHERE 1=1"
        params = []
        if case_id:
            query += " AND case_id = ?"
            params.append(case_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if resource_id:
            query += " AND resource_id = ?"
            params.append(resource_id)
        cursor.execute(query, params)
        return [row[0] for row in cursor.fetchall()]

    # --- Marking Storage ---

    def save_marking(self, case_id: str, net_id: str, marking) -> None:
        import json
        cursor = self._conn.cursor()
        data = json.dumps(self._serializer.serialize(marking))
        cursor.execute("""
            INSERT OR REPLACE INTO markings (case_id, net_id, data)
            VALUES (?, ?, ?)
        """, (case_id, net_id, data))
        self._conn.commit()

    def load_marking(self, case_id: str, net_id: str):
        import json
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT data FROM markings WHERE case_id = ? AND net_id = ?",
            (case_id, net_id)
        )
        row = cursor.fetchone()
        if row:
            data = json.loads(row[0])
            return self._serializer.deserialize(data, self._type_registry)
        return None

    # --- Transaction Support ---

    def begin_transaction(self) -> None:
        self._conn.execute("BEGIN")

    def commit_transaction(self) -> None:
        self._conn.commit()

    def rollback_transaction(self) -> None:
        self._conn.rollback()
```

### Step 5: Engine Integration

```python
# src/kgcl/yawl/engine/y_engine.py

from kgcl.yawl.persistence.y_repository import YRepository
from kgcl.yawl.persistence.y_memory_repo import YMemoryRepository

@dataclass
class YEngine:
    # ... existing fields ...

    repository: YRepository = field(default_factory=YMemoryRepository)

    # Disable in-memory storage when using persistent repo
    _use_memory_cache: bool = True

    def load_specification(self, spec_id: str) -> YSpecification | None:
        """Load specification from repository."""
        if spec_id in self.specifications:
            return self.specifications[spec_id]

        spec = self.repository.load_specification(spec_id)
        if spec:
            self.specifications[spec_id] = spec
        return spec

    def save_case_state(self, case_id: str) -> None:
        """Persist current case state."""
        case = self.cases.get(case_id)
        if case:
            self.repository.save_case(case)

            # Save work items
            for work_item in case.work_items.values():
                self.repository.save_work_item(work_item)

            # Save markings
            for runner_key, runner in self.net_runners.items():
                if runner_key.startswith(f"{case_id}:"):
                    _, net_id = runner_key.split(":", 1)
                    self.repository.save_marking(
                        case_id, net_id, runner.marking
                    )

    def recover_case(self, case_id: str) -> YCase | None:
        """Recover case from repository.

        Reconstructs in-memory state from persisted data.
        """
        case = self.repository.load_case(case_id)
        if case is None:
            return None

        # Load specification
        spec = self.load_specification(case.specification_id)
        if spec is None:
            return None

        # Restore case
        self.cases[case_id] = case

        # Restore net runners with markings
        for net in spec.decompositions.values():
            marking = self.repository.load_marking(case_id, net.id)
            if marking:
                runner = YNetRunner(
                    net=net,
                    case_id=case_id,
                    specification_id=spec.id,
                )
                runner.marking = marking
                self.net_runners[f"{case_id}:{net.id}"] = runner

        return case

    def recover_all_running_cases(self) -> list[YCase]:
        """Recover all running cases from repository."""
        case_ids = self.repository.list_cases(status="RUNNING")
        cases = []
        for case_id in case_ids:
            case = self.recover_case(case_id)
            if case:
                cases.append(case)
        return cases
```

## Test Cases

```python
class TestPersistence:
    """Tests for persistence layer."""

    def test_specification_roundtrip(self) -> None:
        """Specification survives save/load."""
        # Create spec
        # Save to repo
        # Load from repo
        # Assert: equal to original

    def test_case_roundtrip(self) -> None:
        """Case state survives save/load."""
        # Create case with work items
        # Save
        # Load
        # Assert: all state preserved

    def test_marking_persistence(self) -> None:
        """Marking (tokens) persisted correctly."""
        # Run case to mid-point
        # Save marking
        # Load marking
        # Assert: tokens in correct positions

    def test_recovery_continues_execution(self) -> None:
        """Recovered case can continue execution."""
        # Start case, partial execution
        # Save state
        # Create new engine
        # Recover case
        # Complete remaining work
        # Assert: case completes correctly

    def test_sqlite_repo(self) -> None:
        """SQLite repository works correctly."""
        # Create SQLite repo
        # Save/load specification
        # Save/load case
        # Assert: data persisted to file

    def test_concurrent_saves(self) -> None:
        """Multiple saves don't corrupt data."""
        # Rapid save operations
        # Assert: data consistent
```

## Dependencies

- None for memory repo
- `sqlite3` (stdlib) for SQLite repo

## Complexity: MEDIUM

- Serialization of complex dataclasses
- State reconstruction
- Transaction handling

## Estimated Effort

- Implementation: 8-12 hours
- Testing: 6-8 hours
- Total: 2-3 days

## Priority: LOW

Important for production but not blocking development/testing.
