"""Multi-instance task configuration (mirrors Java YMultiInstanceAttributes).

Supports Workflow Control Patterns 12-15:
- WCP-12: Multiple Instances Without Synchronization
- WCP-13: Multiple Instances With a Priori Design-Time Knowledge
- WCP-14: Multiple Instances With a Priori Run-Time Knowledge
- WCP-15: Multiple Instances Without a Priori Run-Time Knowledge
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class MICreationMode(Enum):
    """Mode for creating multi-instance task instances.

    Attributes
    ----------
    STATIC : auto
        Fixed number of instances known at design time (WCP-13)
    DYNAMIC : auto
        Number of instances determined at runtime (WCP-14, WCP-15)
    """

    STATIC = auto()
    DYNAMIC = auto()


class MICompletionMode(Enum):
    """Mode for completing multi-instance task.

    Attributes
    ----------
    ALL : auto
        Wait for all instances to complete
    THRESHOLD : auto
        Continue when threshold number complete
    """

    ALL = auto()
    THRESHOLD = auto()


@dataclass(frozen=True)
class YMultiInstanceAttributes:
    """Multi-instance task configuration (mirrors Java YMultiInstanceAttributes).

    Configures how a task spawns and synchronizes multiple concurrent instances.
    This supports Workflow Control Patterns 12-15 from the WCP taxonomy.

    Parameters
    ----------
    minimum : int
        Minimum number of instances (default: 1)
    maximum : int | None
        Maximum number of instances (None = unlimited)
    threshold : int
        Number of completions required to continue (default: 1)
    creation_mode : MICreationMode
        How instances are created (STATIC or DYNAMIC)
    completion_mode : MICompletionMode
        How completion is determined (ALL or THRESHOLD)
    min_query : str | None
        Query to determine minimum at runtime
    max_query : str | None
        Query to determine maximum at runtime
    threshold_query : str | None
        Query to determine threshold at runtime

    Examples
    --------
    >>> # WCP-13: Static multi-instance (3 instances, wait for all)
    >>> mi = YMultiInstanceAttributes(minimum=3, maximum=3)
    >>> mi.is_static()
    True

    >>> # WCP-14: Dynamic multi-instance with threshold
    >>> mi = YMultiInstanceAttributes(
    ...     creation_mode=MICreationMode.DYNAMIC, completion_mode=MICompletionMode.THRESHOLD, threshold=2
    ... )
    >>> mi.is_dynamic()
    True
    """

    minimum: int = 1
    maximum: int | None = None  # None = unlimited
    threshold: int = 1
    creation_mode: MICreationMode = MICreationMode.STATIC
    completion_mode: MICompletionMode = MICompletionMode.ALL

    # Queries for dynamic values (simplified as strings)
    min_query: str | None = None
    max_query: str | None = None
    threshold_query: str | None = None

    def is_static(self) -> bool:
        """Check if instance count is known at design time.

        Returns
        -------
        bool
            True if creation_mode is STATIC
        """
        return self.creation_mode == MICreationMode.STATIC

    def is_dynamic(self) -> bool:
        """Check if instance count is determined at runtime.

        Returns
        -------
        bool
            True if creation_mode is DYNAMIC
        """
        return self.creation_mode == MICreationMode.DYNAMIC

    def requires_all_completion(self) -> bool:
        """Check if all instances must complete.

        Returns
        -------
        bool
            True if completion_mode is ALL
        """
        return self.completion_mode == MICompletionMode.ALL

    def uses_threshold(self) -> bool:
        """Check if completion uses threshold.

        Returns
        -------
        bool
            True if completion_mode is THRESHOLD
        """
        return self.completion_mode == MICompletionMode.THRESHOLD

    def get_effective_minimum(self, data: dict[str, int] | None = None) -> int:
        """Get effective minimum, evaluating query if dynamic.

        Parameters
        ----------
        data : dict[str, int] | None
            Data for query evaluation

        Returns
        -------
        int
            Effective minimum instance count
        """
        if self.min_query and data and self.min_query in data:
            return data[self.min_query]
        return self.minimum

    def get_effective_maximum(self, data: dict[str, int] | None = None) -> int | None:
        """Get effective maximum, evaluating query if dynamic.

        Parameters
        ----------
        data : dict[str, int] | None
            Data for query evaluation

        Returns
        -------
        int | None
            Effective maximum instance count (None = unlimited)
        """
        if self.max_query and data and self.max_query in data:
            return data[self.max_query]
        return self.maximum

    def get_effective_threshold(self, data: dict[str, int] | None = None) -> int:
        """Get effective threshold, evaluating query if dynamic.

        Parameters
        ----------
        data : dict[str, int] | None
            Data for query evaluation

        Returns
        -------
        int
            Effective completion threshold
        """
        if self.threshold_query and data and self.threshold_query in data:
            return data[self.threshold_query]
        return self.threshold

    def is_completion_satisfied(self, completed_count: int, total_count: int) -> bool:
        """Check if completion condition is satisfied.

        Parameters
        ----------
        completed_count : int
            Number of instances completed
        total_count : int
            Total number of instances

        Returns
        -------
        bool
            True if task can proceed
        """
        if self.completion_mode == MICompletionMode.ALL:
            return completed_count >= total_count
        else:  # THRESHOLD
            return completed_count >= self.threshold
