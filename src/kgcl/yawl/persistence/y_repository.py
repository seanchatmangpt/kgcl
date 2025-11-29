"""Repository pattern for YAWL persistence (mirrors Java persistence).

Provides abstract and in-memory implementations for storing
specifications, cases, and work items.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_specification import YSpecification
    from kgcl.yawl.engine.y_case import YCase
    from kgcl.yawl.engine.y_work_item import YWorkItem


class Repository[T](ABC):
    """Abstract repository interface.

    Parameters
    ----------
    T : Type
        Entity type stored in repository
    """

    @abstractmethod
    def save(self, entity: T) -> None:
        """Save entity.

        Parameters
        ----------
        entity : T
            Entity to save
        """

    @abstractmethod
    def get(self, entity_id: str) -> T | None:
        """Get entity by ID.

        Parameters
        ----------
        entity_id : str
            Entity ID

        Returns
        -------
        T | None
            Entity or None if not found
        """

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity.

        Parameters
        ----------
        entity_id : str
            Entity ID

        Returns
        -------
        bool
            True if deleted
        """

    @abstractmethod
    def get_all(self) -> list[T]:
        """Get all entities.

        Returns
        -------
        list[T]
            All entities
        """

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists.

        Parameters
        ----------
        entity_id : str
            Entity ID

        Returns
        -------
        bool
            True if exists
        """


@dataclass
class YSpecificationRepository(Repository["YSpecification"]):
    """Repository for specifications.

    Parameters
    ----------
    _store : dict[str, YSpecification]
        In-memory storage
    """

    _store: dict[str, Any] = field(default_factory=dict)

    def save(self, spec: YSpecification) -> None:
        """Save specification.

        Parameters
        ----------
        spec : YSpecification
            Specification to save
        """
        self._store[spec.id] = spec

    def get(self, spec_id: str) -> YSpecification | None:
        """Get specification by ID.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        YSpecification | None
            Specification or None
        """
        return self._store.get(spec_id)

    def delete(self, spec_id: str) -> bool:
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
        if spec_id in self._store:
            del self._store[spec_id]
            return True
        return False

    def get_all(self) -> list[YSpecification]:
        """Get all specifications.

        Returns
        -------
        list[YSpecification]
            All specifications
        """
        return list(self._store.values())

    def exists(self, spec_id: str) -> bool:
        """Check if specification exists.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        bool
            True if exists
        """
        return spec_id in self._store

    def find_by_name(self, name: str) -> list[YSpecification]:
        """Find specifications by name.

        Parameters
        ----------
        name : str
            Specification name

        Returns
        -------
        list[YSpecification]
            Matching specifications
        """
        return [s for s in self._store.values() if s.name == name]

    def find_active(self) -> list[YSpecification]:
        """Find active specifications.

        Returns
        -------
        list[YSpecification]
            Active specifications
        """
        from kgcl.yawl.elements.y_specification import SpecificationStatus

        return [s for s in self._store.values() if s.status == SpecificationStatus.ACTIVE]


@dataclass
class YCaseRepository(Repository["YCase"]):
    """Repository for cases.

    Parameters
    ----------
    _store : dict[str, YCase]
        In-memory storage
    """

    _store: dict[str, Any] = field(default_factory=dict)

    def save(self, case: YCase) -> None:
        """Save case.

        Parameters
        ----------
        case : YCase
            Case to save
        """
        self._store[case.id] = case

    def get(self, case_id: str) -> YCase | None:
        """Get case by ID.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        YCase | None
            Case or None
        """
        return self._store.get(case_id)

    def delete(self, case_id: str) -> bool:
        """Delete case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        bool
            True if deleted
        """
        if case_id in self._store:
            del self._store[case_id]
            return True
        return False

    def get_all(self) -> list[YCase]:
        """Get all cases.

        Returns
        -------
        list[YCase]
            All cases
        """
        return list(self._store.values())

    def exists(self, case_id: str) -> bool:
        """Check if case exists.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        bool
            True if exists
        """
        return case_id in self._store

    def find_by_specification(self, spec_id: str) -> list[YCase]:
        """Find cases for a specification.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        list[YCase]
            Cases for specification
        """
        return [c for c in self._store.values() if c.specification_id == spec_id]

    def find_running(self) -> list[YCase]:
        """Find running cases.

        Returns
        -------
        list[YCase]
            Running cases
        """
        from kgcl.yawl.engine.y_case import CaseStatus

        return [c for c in self._store.values() if c.status == CaseStatus.RUNNING]

    def find_completed(self) -> list[YCase]:
        """Find completed cases.

        Returns
        -------
        list[YCase]
            Completed cases
        """
        from kgcl.yawl.engine.y_case import CaseStatus

        return [c for c in self._store.values() if c.status == CaseStatus.COMPLETED]

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> list[YCase]:
        """Find cases created in date range.

        Parameters
        ----------
        start_date : datetime
            Start of range
        end_date : datetime
            End of range

        Returns
        -------
        list[YCase]
            Cases in range
        """
        return [c for c in self._store.values() if start_date <= c.created <= end_date]


@dataclass
class YWorkItemRepository(Repository["YWorkItem"]):
    """Repository for work items.

    Parameters
    ----------
    _store : dict[str, YWorkItem]
        In-memory storage
    """

    _store: dict[str, Any] = field(default_factory=dict)

    def save(self, work_item: YWorkItem) -> None:
        """Save work item.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to save
        """
        self._store[work_item.id] = work_item

    def get(self, work_item_id: str) -> YWorkItem | None:
        """Get work item by ID.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        YWorkItem | None
            Work item or None
        """
        return self._store.get(work_item_id)

    def delete(self, work_item_id: str) -> bool:
        """Delete work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if deleted
        """
        if work_item_id in self._store:
            del self._store[work_item_id]
            return True
        return False

    def get_all(self) -> list[YWorkItem]:
        """Get all work items.

        Returns
        -------
        list[YWorkItem]
            All work items
        """
        return list(self._store.values())

    def exists(self, work_item_id: str) -> bool:
        """Check if work item exists.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if exists
        """
        return work_item_id in self._store

    def find_by_case(self, case_id: str) -> list[YWorkItem]:
        """Find work items for a case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        list[YWorkItem]
            Work items for case
        """
        return [wi for wi in self._store.values() if wi.case_id == case_id]

    def find_by_task(self, task_id: str) -> list[YWorkItem]:
        """Find work items for a task.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        list[YWorkItem]
            Work items for task
        """
        return [wi for wi in self._store.values() if wi.task_id == task_id]

    def find_by_participant(self, participant_id: str) -> list[YWorkItem]:
        """Find work items for a participant.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        list[YWorkItem]
            Work items for participant
        """
        return [
            wi for wi in self._store.values() if wi.resource_id == participant_id or participant_id in wi.offered_to
        ]

    def find_active(self) -> list[YWorkItem]:
        """Find active work items.

        Returns
        -------
        list[YWorkItem]
            Active work items
        """
        return [wi for wi in self._store.values() if wi.is_active()]


@dataclass
class YInMemoryRepository:
    """Combined in-memory repository for all entities.

    Provides a single repository instance for specifications,
    cases, and work items.

    Parameters
    ----------
    specifications : YSpecificationRepository
        Specification repository
    cases : YCaseRepository
        Case repository
    work_items : YWorkItemRepository
        Work item repository

    Examples
    --------
    >>> repo = YInMemoryRepository()
    >>> repo.specifications.save(spec)
    >>> repo.cases.save(case)
    """

    specifications: YSpecificationRepository = field(default_factory=YSpecificationRepository)
    cases: YCaseRepository = field(default_factory=YCaseRepository)
    work_items: YWorkItemRepository = field(default_factory=YWorkItemRepository)

    def clear_all(self) -> None:
        """Clear all repositories."""
        self.specifications._store.clear()
        self.cases._store.clear()
        self.work_items._store.clear()

    def get_statistics(self) -> dict[str, int]:
        """Get repository statistics.

        Returns
        -------
        dict[str, int]
            Counts for each entity type
        """
        return {
            "specifications": len(self.specifications._store),
            "cases": len(self.cases._store),
            "work_items": len(self.work_items._store),
        }
