"""Worklet repository for storing and retrieving worklets.

Provides storage and retrieval of worklet definitions,
RDR trees, and worklet case executions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from kgcl.yawl.worklets.exceptions import WorkletNotFoundError
from kgcl.yawl.worklets.models import RDRTree, Worklet, WorkletCase, WorkletStatus, WorkletType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class WorkletRepository:
    """Repository for worklet storage and retrieval.

    Provides in-memory storage with context manager support,
    iterator access, and query builder patterns.

    Parameters
    ----------
    worklets : dict[str, Worklet]
        Worklet definitions by ID
    trees : dict[str, RDRTree]
        RDR trees by ID
    cases : dict[str, WorkletCase]
        Running worklet cases by ID

    Examples
    --------
    >>> repo = WorkletRepository()
    >>> with repo:
    ...     repo.add_worklet(worklet)
    ...     worklet = repo.get_worklet("wl-001")
    >>> # Iterator support
    >>> for worklet in repo:
    ...     print(worklet.name)
    >>> # Query builder
    >>> query = repo.query_worklets()
    ...     .filter_type(WorkletType.ITEM_EXCEPTION)
    ...     .filter_enabled(True)
    ...     .execute()
    """

    worklets: dict[str, Worklet] = field(default_factory=dict)
    trees: dict[str, RDRTree] = field(default_factory=dict)
    cases: dict[str, WorkletCase] = field(default_factory=dict)

    def __enter__(self) -> WorkletRepository:
        """Enter context manager."""
        logger.debug("Entering repository context")
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> Literal[False]:
        """Exit context manager.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if raised
        exc_val : BaseException | None
            Exception value if raised
        exc_tb : Any
            Traceback if raised

        Returns
        -------
        bool
            False to propagate exceptions
        """
        if exc_type:
            logger.error(
                "Repository context exited with exception",
                extra={"exc_type": exc_type.__name__},
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            logger.debug("Repository context exited normally")
        return False  # Propagate exceptions

    def __iter__(self) -> Iterator[Worklet]:
        """Iterate over all worklets.

        Returns
        -------
        Iterator[Worklet]
            Iterator over worklets
        """
        return iter(self.worklets.values())

    def __len__(self) -> int:
        """Get total number of worklets.

        Returns
        -------
        int
            Number of worklets
        """
        return len(self.worklets)

    # --- Worklet management ---

    def add_worklet(self, worklet: Worklet) -> None:
        """Add a worklet definition.

        Parameters
        ----------
        worklet : Worklet
            Worklet to add

        Examples
        --------
        >>> repo.add_worklet(Worklet(id="wl-001", name="Handler"))
        """
        logger.debug("Adding worklet", extra={"worklet_id": worklet.id, "name": worklet.name})
        self.worklets[worklet.id] = worklet

    def get_worklet(self, worklet_id: str) -> Worklet | None:
        """Get worklet by ID.

        Parameters
        ----------
        worklet_id : str
            Worklet ID

        Returns
        -------
        Worklet | None
            Worklet or None

        Raises
        ------
        WorkletNotFoundError
            If worklet not found and raise_if_missing=True
        """
        worklet = self.worklets.get(worklet_id)
        if worklet:
            logger.debug("Retrieved worklet", extra={"worklet_id": worklet_id})
        else:
            logger.debug("Worklet not found", extra={"worklet_id": worklet_id})
        return worklet

    def require_worklet(self, worklet_id: str) -> Worklet:
        """Get worklet by ID, raising if not found.

        Parameters
        ----------
        worklet_id : str
            Worklet ID

        Returns
        -------
        Worklet
            Worklet instance

        Raises
        ------
        WorkletNotFoundError
            If worklet not found
        """
        worklet = self.get_worklet(worklet_id)
        if worklet is None:
            raise WorkletNotFoundError(worklet_id=worklet_id, message=f"Worklet not found: {worklet_id}")
        return worklet

    def remove_worklet(self, worklet_id: str) -> bool:
        """Remove worklet.

        Parameters
        ----------
        worklet_id : str
            Worklet ID

        Returns
        -------
        bool
            True if removed
        """
        if worklet_id in self.worklets:
            del self.worklets[worklet_id]
            return True
        return False

    def find_worklets(self, worklet_type: WorkletType | None = None, enabled_only: bool = True) -> list[Worklet]:
        """Find worklets matching criteria.

        Parameters
        ----------
        worklet_type : WorkletType | None
            Filter by type
        enabled_only : bool
            Only include enabled worklets

        Returns
        -------
        list[Worklet]
            Matching worklets
        """
        results = list(self.worklets.values())

        if enabled_only:
            results = [w for w in results if w.enabled]

        if worklet_type:
            results = [w for w in results if w.worklet_type == worklet_type]

        logger.debug(
            "Found worklets",
            extra={
                "count": len(results),
                "worklet_type": worklet_type.name if worklet_type else None,
                "enabled_only": enabled_only,
            },
        )
        return results

    def query_worklets(self) -> WorkletQueryBuilder:
        """Create a query builder for worklets.

        Returns
        -------
        WorkletQueryBuilder
            Query builder instance

        Examples
        --------
        >>> results = repo.query_worklets()
        ...     .filter_type(WorkletType.ITEM_EXCEPTION)
        ...     .filter_enabled(True)
        ...     .execute()
        """
        return WorkletQueryBuilder(self)

    def list_worklets(self) -> list[Worklet]:
        """List all worklets.

        Returns
        -------
        list[Worklet]
            All worklets
        """
        return list(self.worklets.values())

    # --- RDR Tree management ---

    def add_tree(self, tree: RDRTree) -> None:
        """Add an RDR tree.

        Parameters
        ----------
        tree : RDRTree
            Tree to add
        """
        self.trees[tree.id] = tree

    def get_tree(self, tree_id: str) -> RDRTree | None:
        """Get tree by ID.

        Parameters
        ----------
        tree_id : str
            Tree ID

        Returns
        -------
        RDRTree | None
            Tree or None
        """
        return self.trees.get(tree_id)

    def find_tree(self, task_id: str | None = None, exception_type: str = "default") -> RDRTree | None:
        """Find tree by task and exception type.

        Parameters
        ----------
        task_id : str | None
            Task ID
        exception_type : str
            Exception type

        Returns
        -------
        RDRTree | None
            Matching tree or None
        """
        for tree in self.trees.values():
            if tree.task_id == task_id and tree.exception_type == exception_type:
                return tree
        return None

    def remove_tree(self, tree_id: str) -> bool:
        """Remove tree.

        Parameters
        ----------
        tree_id : str
            Tree ID

        Returns
        -------
        bool
            True if removed
        """
        if tree_id in self.trees:
            del self.trees[tree_id]
            return True
        return False

    def list_trees(self) -> list[RDRTree]:
        """List all trees.

        Returns
        -------
        list[RDRTree]
            All trees
        """
        return list(self.trees.values())

    # --- Worklet case management ---

    def add_case(self, case: WorkletCase) -> None:
        """Add a worklet case.

        Parameters
        ----------
        case : WorkletCase
            Case to add
        """
        self.cases[case.id] = case

    def get_case(self, case_id: str) -> WorkletCase | None:
        """Get case by ID.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        WorkletCase | None
            Case or None
        """
        return self.cases.get(case_id)

    def remove_case(self, case_id: str) -> bool:
        """Remove case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        bool
            True if removed
        """
        if case_id in self.cases:
            del self.cases[case_id]
            return True
        return False

    def find_cases(self, parent_case_id: str | None = None, status: WorkletStatus | None = None) -> list[WorkletCase]:
        """Find cases matching criteria.

        Parameters
        ----------
        parent_case_id : str | None
            Filter by parent case
        status : WorkletStatus | None
            Filter by status

        Returns
        -------
        list[WorkletCase]
            Matching cases
        """
        results = list(self.cases.values())

        if parent_case_id:
            results = [c for c in results if c.parent_case_id == parent_case_id]

        if status:
            results = [c for c in results if c.status == status]

        return results

    def get_active_cases(self, parent_case_id: str) -> list[WorkletCase]:
        """Get active cases for parent.

        Parameters
        ----------
        parent_case_id : str
            Parent case ID

        Returns
        -------
        list[WorkletCase]
            Active cases
        """
        return [
            c
            for c in self.cases.values()
            if c.parent_case_id == parent_case_id and c.status in (WorkletStatus.PENDING, WorkletStatus.RUNNING)
        ]

    def cleanup_completed_cases(self, max_age_hours: float = 24) -> int:
        """Remove old completed cases.

        Parameters
        ----------
        max_age_hours : float
            Maximum age in hours

        Returns
        -------
        int
            Number of cases removed
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []

        for case_id, case in self.cases.items():
            if case.status in (WorkletStatus.COMPLETED, WorkletStatus.FAILED):
                if case.completed and case.completed < cutoff:
                    to_remove.append(case_id)

        for case_id in to_remove:
            del self.cases[case_id]

        logger.info(
            "Cleaned up completed cases", extra={"removed_count": len(to_remove), "max_age_hours": max_age_hours}
        )
        return len(to_remove)


class WorkletQueryBuilder:
    """Query builder for worklet searches.

    Provides fluent interface for building complex queries.

    Examples
    --------
    >>> builder = repo.query_worklets()
    >>> results = builder.filter_type(WorkletType.ITEM_EXCEPTION).filter_enabled(True).execute()
    """

    def __init__(self, repository: WorkletRepository) -> None:
        """Initialize query builder.

        Parameters
        ----------
        repository : WorkletRepository
            Repository to query
        """
        self._repository = repository
        self._worklet_type: WorkletType | None = None
        self._enabled_only: bool | None = None

    def filter_type(self, worklet_type: WorkletType) -> WorkletQueryBuilder:
        """Filter by worklet type.

        Parameters
        ----------
        worklet_type : WorkletType
            Type to filter by

        Returns
        -------
        WorkletQueryBuilder
            Self for chaining
        """
        self._worklet_type = worklet_type
        return self

    def filter_enabled(self, enabled: bool) -> WorkletQueryBuilder:
        """Filter by enabled status.

        Parameters
        ----------
        enabled : bool
            Enabled status

        Returns
        -------
        WorkletQueryBuilder
            Self for chaining
        """
        self._enabled_only = enabled
        return self

    def execute(self) -> list[Worklet]:
        """Execute the query.

        Returns
        -------
        list[Worklet]
            Matching worklets
        """
        return self._repository.find_worklets(
            worklet_type=self._worklet_type, enabled_only=self._enabled_only if self._enabled_only is not None else True
        )
