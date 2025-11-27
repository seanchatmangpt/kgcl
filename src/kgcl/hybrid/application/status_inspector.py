"""StatusInspector - Query and analyze task statuses.

This module implements status inspection logic that queries the store
for task statuses and resolves monotonic status accumulation.

Examples
--------
>>> from kgcl.hybrid.adapters import OxigraphAdapter
>>> from kgcl.hybrid.application import StatusInspector
>>> store = OxigraphAdapter()
>>> inspector = StatusInspector(store)
>>> statuses = inspector.get_task_statuses()
"""

from __future__ import annotations

import logging
from typing import Any

from kgcl.hybrid.domain.task_status import TaskStatus
from kgcl.hybrid.ports.store_port import RDFStore

logger = logging.getLogger(__name__)


class StatusInspector:
    """Query and analyze task statuses.

    Implements status inspection logic that queries the store and
    resolves monotonic status accumulation by returning highest-priority
    status for each task.

    Parameters
    ----------
    store : RDFStore
        The RDF store to query.

    Examples
    --------
    >>> from kgcl.hybrid.adapters import OxigraphAdapter
    >>> store = OxigraphAdapter()
    >>> _ = store.load_turtle('''
    ...     @prefix kgc: <https://kgc.org/ns/> .
    ...     <urn:task:A> kgc:status "Active" .
    ...     <urn:task:B> kgc:status "Completed" .
    ... ''')
    >>> inspector = StatusInspector(store)
    >>> statuses = inspector.get_task_statuses()
    >>> statuses["urn:task:A"]
    'Active'
    """

    # SPARQL query for fetching all task statuses
    STATUS_QUERY = """
        PREFIX kgc: <https://kgc.org/ns/>
        SELECT ?s ?status WHERE { ?s kgc:status ?status }
    """

    def __init__(self, store: RDFStore) -> None:
        """Initialize StatusInspector.

        Parameters
        ----------
        store : RDFStore
            The RDF store to query.
        """
        self._store = store
        logger.info("StatusInspector initialized")

    def get_task_statuses(self) -> dict[str, str]:
        """Query current task statuses (returning highest-priority status).

        Due to monotonic reasoning, tasks may accumulate multiple statuses
        (Active, Completed, Archived). This method returns the highest-priority
        status for each task.

        Priority order: Cancelled > Archived > Completed > Active > Pending

        Returns
        -------
        dict[str, str]
            Mapping of task IRI to highest-priority status string.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     <urn:task:A> kgc:status "Active" .
        ...     <urn:task:B> kgc:status "Completed" .
        ... ''')
        >>> inspector = StatusInspector(store)
        >>> statuses = inspector.get_task_statuses()
        >>> statuses["urn:task:A"]
        'Active'
        >>> statuses["urn:task:B"]
        'Completed'
        """
        # Collect all statuses per task
        task_statuses: dict[str, list[str]] = {}

        results = self._store.query(self.STATUS_QUERY)

        for binding in results:
            subject = self._extract_subject(binding)
            status = self._extract_status(binding)

            if subject and status:
                if subject not in task_statuses:
                    task_statuses[subject] = []
                task_statuses[subject].append(status)

        # Resolve to highest priority status per task
        resolved: dict[str, str] = {}
        for task, statuses in task_statuses.items():
            resolved[task] = TaskStatus.highest_priority(statuses)

        logger.debug(f"Inspected {len(resolved)} task statuses")
        return resolved

    def get_tasks_by_status(self, status: str) -> list[str]:
        """Get all tasks with a specific status.

        Parameters
        ----------
        status : str
            Status to filter by (e.g., "Active", "Completed").

        Returns
        -------
        list[str]
            List of task IRIs with the specified status.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     <urn:task:A> kgc:status "Active" .
        ...     <urn:task:B> kgc:status "Active" .
        ...     <urn:task:C> kgc:status "Completed" .
        ... ''')
        >>> inspector = StatusInspector(store)
        >>> active_tasks = inspector.get_tasks_by_status("Active")
        >>> len(active_tasks)
        2
        """
        all_statuses = self.get_task_statuses()
        return [task for task, task_status in all_statuses.items() if task_status == status]

    def get_active_tasks(self) -> list[str]:
        """Get all currently active tasks.

        Returns
        -------
        list[str]
            List of task IRIs with Active status.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     <urn:task:A> kgc:status "Active" .
        ...     <urn:task:B> kgc:status "Completed" .
        ... ''')
        >>> inspector = StatusInspector(store)
        >>> active = inspector.get_active_tasks()
        >>> "urn:task:A" in active
        True
        >>> "urn:task:B" in active
        False
        """
        return self.get_tasks_by_status("Active")

    def get_completed_tasks(self) -> list[str]:
        """Get all completed tasks.

        Returns
        -------
        list[str]
            List of task IRIs with Completed status.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     <urn:task:A> kgc:status "Active" .
        ...     <urn:task:B> kgc:status "Completed" .
        ... ''')
        >>> inspector = StatusInspector(store)
        >>> completed = inspector.get_completed_tasks()
        >>> "urn:task:B" in completed
        True
        """
        return self.get_tasks_by_status("Completed")

    def is_workflow_complete(self) -> bool:
        """Check if workflow has no active tasks remaining.

        Returns
        -------
        bool
            True if no tasks are Active or Pending.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     <urn:task:A> kgc:status "Completed" .
        ...     <urn:task:B> kgc:status "Archived" .
        ... ''')
        >>> inspector = StatusInspector(store)
        >>> inspector.is_workflow_complete()
        True
        """
        all_statuses = self.get_task_statuses()
        active_states = {"Active", "Pending", "Waiting", "Blocked"}
        return not any(status in active_states for status in all_statuses.values())

    def _extract_subject(self, binding: dict[str, Any]) -> str | None:
        """Extract subject IRI from query binding.

        Parameters
        ----------
        binding : dict[str, Any]
            Query result binding.

        Returns
        -------
        str | None
            Subject IRI or None if not found.
        """
        subject_raw = binding.get("s")
        if subject_raw is None:
            return None

        subject_str = str(subject_raw)
        # Strip angle brackets from URIs
        return subject_str.strip("<>")

    def _extract_status(self, binding: dict[str, Any]) -> str | None:
        """Extract status value from query binding.

        Parameters
        ----------
        binding : dict[str, Any]
            Query result binding.

        Returns
        -------
        str | None
            Status string or None if not found.
        """
        status_raw = binding.get("status")
        if status_raw is None:
            return None

        status_str = str(status_raw)
        # Strip quotes from literals
        return status_str.strip('"')
