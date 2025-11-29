"""Worklet repository for storing and retrieving worklets.

Provides storage and retrieval of worklet definitions,
RDR trees, and worklet case executions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from kgcl.yawl.worklets.models import RDRTree, Worklet, WorkletCase, WorkletStatus, WorkletType


@dataclass
class WorkletRepository:
    """Repository for worklet storage and retrieval.

    Parameters
    ----------
    worklets : dict[str, Worklet]
        Worklet definitions by ID
    trees : dict[str, RDRTree]
        RDR trees by ID
    cases : dict[str, WorkletCase]
        Running worklet cases by ID
    """

    worklets: dict[str, Worklet] = field(default_factory=dict)
    trees: dict[str, RDRTree] = field(default_factory=dict)
    cases: dict[str, WorkletCase] = field(default_factory=dict)

    # --- Worklet management ---

    def add_worklet(self, worklet: Worklet) -> None:
        """Add a worklet definition.

        Parameters
        ----------
        worklet : Worklet
            Worklet to add
        """
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
        """
        return self.worklets.get(worklet_id)

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

        return results

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

        return len(to_remove)
