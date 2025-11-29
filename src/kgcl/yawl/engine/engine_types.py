"""Type definitions for YAWL engine (extracted from y_engine.py).

This module contains all type stubs, enums, and dataclasses used by
the YAWL engine, separated for better organization and maintainability.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from kgcl.yawl.engine.y_net_runner import YNetRunner
from kgcl.yawl.engine.y_work_item import YWorkItem

# === External client and service types ===


@dataclass(frozen=True)
class YExternalClient:
    """External client that can interact with the engine.

    Mirrors Java YExternalClient.

    Parameters
    ----------
    id : str
        Client ID
    password : str
        Client password (hashed)
    documentation : str
        Client documentation
    """

    id: str
    password: str
    documentation: str = ""


@dataclass(frozen=True)
class YAWLServiceReference:
    """Reference to a YAWL service.

    Mirrors Java YAWLServiceReference.

    Parameters
    ----------
    service_id : str
        Service ID
    uri : str
        Service URI
    documentation : str
        Service documentation
    """

    service_id: str
    uri: str
    documentation: str = ""


@dataclass
class YClient:
    """Client reference (participant or service).

    Parameters
    ----------
    id : str
        Client ID
    """

    id: str


# === Work item types ===


class WorkItemCompletion(Enum):
    """Work item completion type.

    Attributes
    ----------
    NORMAL : auto
        Normal completion
    FORCE : auto
        Force completion
    FAIL : auto
        Fail completion
    """

    NORMAL = auto()
    FORCE = auto()
    FAIL = auto()


# === Data types ===


@dataclass
class YNetData:
    """Net data container.

    Parameters
    ----------
    data : dict[str, Any]
        Data dictionary
    """

    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class YLogDataItemList:
    """Log data item list.

    Parameters
    ----------
    items : list[dict[str, Any]]
        Log items
    """

    items: list[dict[str, Any]] = field(default_factory=list)


# === Announcement types ===


@dataclass
class AnnouncementContext:
    """Context for announcements.

    Parameters
    ----------
    events : list[str]
        Event list
    """

    events: list[str] = field(default_factory=list)


@dataclass
class YAnnouncer:
    """Event announcer.

    Parameters
    ----------
    listeners : list[Callable[[str], None]]
        Event listeners
    """

    listeners: list[Callable[[str], None]] = field(default_factory=list)


# === Build and configuration types ===


@dataclass
class YBuildProperties:
    """Build properties.

    Parameters
    ----------
    version : str
        Build version
    timestamp : datetime
        Build timestamp
    """

    version: str = "5.2"
    timestamp: datetime = field(default_factory=datetime.now)


class Status(Enum):
    """Engine status.

    Attributes
    ----------
    RUNNING : auto
        Engine running
    STOPPED : auto
        Engine stopped
    """

    RUNNING = auto()
    STOPPED = auto()


class EngineStatus(Enum):
    """Status of the engine.

    Attributes
    ----------
    STOPPED : auto
        Engine is stopped
    STARTING : auto
        Engine is starting up
    RUNNING : auto
        Engine is running
    PAUSED : auto
        Engine is paused
    STOPPING : auto
        Engine is stopping
    """

    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()


# === Persistence types ===


@dataclass
class InstanceCache:
    """Instance cache for persistence.

    Parameters
    ----------
    cache : dict[str, Any]
        Cache storage
    """

    cache: dict[str, Any] = field(default_factory=dict)


@dataclass
class YSessionCache:
    """Session cache.

    Parameters
    ----------
    sessions : dict[str, dict[str, Any]]
        Sessions
    """

    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class YPersistenceManager:
    """Persistence manager.

    Parameters
    ----------
    transaction_active : bool
        Is transaction active
    """

    transaction_active: bool = False

    def start_transaction(self) -> bool:
        """Start transaction."""
        if not self.transaction_active:
            self.transaction_active = True
            return True
        return False

    def commit_transaction(self) -> None:
        """Commit transaction."""
        self.transaction_active = False

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        self.transaction_active = False

    def store_object(self, obj: object) -> None:
        """Store object."""

    def update_object(self, obj: object) -> None:
        """Update object."""

    def delete_object(self, obj: object) -> None:
        """Delete object."""


# === Repository types ===


@dataclass
class YNetRunnerRepository:
    """Repository of net runners.

    Parameters
    ----------
    runners : dict[str, YNetRunner]
        Runners by key
    """

    runners: dict[str, YNetRunner] = field(default_factory=dict)


@dataclass
class YWorkItemRepository:
    """Repository of work items.

    Parameters
    ----------
    work_items : dict[str, YWorkItem]
        Work items by ID
    """

    work_items: dict[str, YWorkItem] = field(default_factory=dict)


# === Validation types ===


@dataclass
class YVerificationHandler:
    """Verification handler for spec validation.

    Parameters
    ----------
    errors : list[str]
        Verification errors
    """

    errors: list[str] = field(default_factory=list)


# === Observer types ===


class InterfaceAManagementObserver:
    """Observer for Interface A management."""


class InterfaceBClientObserver:
    """Observer for Interface B events."""


class ObserverGateway:
    """Gateway for observers."""


# === Event types ===


@dataclass
class EngineEvent:
    """Event emitted by the engine.

    Parameters
    ----------
    event_type : str
        Type of event
    timestamp : datetime
        When event occurred
    case_id : str | None
        Related case ID
    work_item_id : str | None
        Related work item ID
    task_id : str | None
        Related task ID
    participant_id : str | None
        Related participant ID
    data : dict[str, Any]
        Additional event data
    """

    event_type: str
    timestamp: datetime
    case_id: str | None = None
    work_item_id: str | None = None
    task_id: str | None = None
    participant_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


# === Composite task types ===


@dataclass
class SubCaseContext:
    """Context for a sub-case (composite task execution).

    When a composite task fires, it launches a sub-case for its
    decomposed subnet. This context tracks the relationship.

    Parameters
    ----------
    sub_case_id : str
        ID of the sub-case
    parent_case_id : str
        ID of the parent case
    parent_work_item_id : str
        ID of the parent work item (composite task)
    composite_task_id : str
        ID of the composite task
    subnet_id : str
        ID of the decomposed subnet
    started : datetime
        When sub-case was started
    """

    sub_case_id: str
    parent_case_id: str
    parent_work_item_id: str
    composite_task_id: str
    subnet_id: str
    started: datetime = field(default_factory=datetime.now)
