"""Distribution strategies for work item assignment.

Implements YAWL's distribution strategies for allocating
work items among qualified participants.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class DistributionStrategy(Enum):
    """Strategy for distributing work items.

    Attributes
    ----------
    OFFER_TO_ALL : auto
        Offer to all qualified participants
    RANDOM : auto
        Randomly select one participant
    ROUND_ROBIN : auto
        Rotate through participants
    SHORTEST_QUEUE : auto
        Participant with fewest active items
    FASTEST : auto
        Fastest average completion time
    CLOSEST : auto
        Based on organizational proximity
    DIRECT_ALLOCATION : auto
        Allocate directly to specific participant
    """

    OFFER_TO_ALL = auto()
    RANDOM = auto()
    ROUND_ROBIN = auto()
    SHORTEST_QUEUE = auto()
    FASTEST = auto()
    CLOSEST = auto()
    DIRECT_ALLOCATION = auto()


@dataclass
class ParticipantMetrics:
    """Performance metrics for a participant.

    Parameters
    ----------
    participant_id : str
        Participant ID
    active_work_items : int
        Number of currently active work items
    completed_count : int
        Total completed work items
    average_completion_time_ms : float
        Average time to complete work items
    last_assigned : datetime | None
        Last time a work item was assigned
    """

    participant_id: str
    active_work_items: int = 0
    completed_count: int = 0
    average_completion_time_ms: float = 0.0
    last_assigned: datetime | None = None

    def update_completion(self, duration_ms: float) -> None:
        """Update metrics after completion.

        Parameters
        ----------
        duration_ms : float
            Completion duration in milliseconds
        """
        self.completed_count += 1
        # Running average
        if self.average_completion_time_ms == 0:
            self.average_completion_time_ms = duration_ms
        else:
            self.average_completion_time_ms = (
                self.average_completion_time_ms * (self.completed_count - 1) + duration_ms
            ) / self.completed_count


@dataclass
class DistributionContext:
    """Context for distribution decisions.

    Parameters
    ----------
    task_id : str
        Task being distributed
    case_id : str
        Case ID
    metrics : dict[str, ParticipantMetrics]
        Participant metrics by ID
    round_robin_index : dict[str, int]
        Round robin indices by task ID
    """

    task_id: str
    case_id: str
    metrics: dict[str, ParticipantMetrics] = field(default_factory=dict)
    round_robin_index: dict[str, int] = field(default_factory=dict)

    def get_next_round_robin_index(self, participant_count: int) -> int:
        """Get next index for round robin.

        Parameters
        ----------
        participant_count : int
            Number of participants

        Returns
        -------
        int
            Next index
        """
        current = self.round_robin_index.get(self.task_id, -1)
        next_index = (current + 1) % participant_count
        self.round_robin_index[self.task_id] = next_index
        return next_index


@dataclass
class Distributor:
    """Distributes work items according to strategy.

    Parameters
    ----------
    strategy : DistributionStrategy
        Distribution strategy
    context : DistributionContext | None
        Distribution context
    """

    strategy: DistributionStrategy = DistributionStrategy.OFFER_TO_ALL
    context: DistributionContext | None = None

    def distribute(
        self,
        participants: list[Any],  # list[YParticipant]
    ) -> list[Any]:
        """Distribute to participants based on strategy.

        Parameters
        ----------
        participants : list[Any]
            Qualified participants

        Returns
        -------
        list[Any]
            Selected participants
        """
        if not participants:
            return []

        if self.strategy == DistributionStrategy.OFFER_TO_ALL:
            return participants

        if self.strategy == DistributionStrategy.RANDOM:
            return [random.choice(participants)]

        if self.strategy == DistributionStrategy.ROUND_ROBIN:
            return self._round_robin(participants)

        if self.strategy == DistributionStrategy.SHORTEST_QUEUE:
            return self._shortest_queue(participants)

        if self.strategy == DistributionStrategy.FASTEST:
            return self._fastest(participants)

        if self.strategy == DistributionStrategy.DIRECT_ALLOCATION:
            # Direct allocation expects single participant
            return participants[:1]

        # Default to offer to all
        return participants

    def _round_robin(self, participants: list[Any]) -> list[Any]:
        """Select participant using round robin.

        Parameters
        ----------
        participants : list[Any]
            Available participants

        Returns
        -------
        list[Any]
            Selected participant
        """
        if not self.context:
            return [random.choice(participants)]

        index = self.context.get_next_round_robin_index(len(participants))
        return [participants[index]]

    def _shortest_queue(self, participants: list[Any]) -> list[Any]:
        """Select participant with shortest queue.

        Parameters
        ----------
        participants : list[Any]
            Available participants

        Returns
        -------
        list[Any]
            Selected participant
        """
        if not self.context or not self.context.metrics:
            return [random.choice(participants)]

        def get_queue_length(p: Any) -> int:
            metrics = self.context.metrics.get(p.id) if self.context else None
            return metrics.active_work_items if metrics else 0

        sorted_participants = sorted(participants, key=get_queue_length)
        return [sorted_participants[0]]

    def _fastest(self, participants: list[Any]) -> list[Any]:
        """Select fastest participant.

        Parameters
        ----------
        participants : list[Any]
            Available participants

        Returns
        -------
        list[Any]
            Selected participant
        """
        if not self.context or not self.context.metrics:
            return [random.choice(participants)]

        def get_avg_time(p: Any) -> float:
            metrics = self.context.metrics.get(p.id) if self.context else None
            if metrics and metrics.average_completion_time_ms > 0:
                return metrics.average_completion_time_ms
            return float("inf")

        sorted_participants = sorted(participants, key=get_avg_time)
        return [sorted_participants[0]]


def create_distributor(strategy: DistributionStrategy | str, context: DistributionContext | None = None) -> Distributor:
    """Create a distributor with specified strategy.

    Parameters
    ----------
    strategy : DistributionStrategy | str
        Strategy (enum or name)
    context : DistributionContext | None
        Distribution context

    Returns
    -------
    Distributor
        Configured distributor
    """
    if isinstance(strategy, str):
        strategy = DistributionStrategy[strategy.upper()]

    return Distributor(strategy=strategy, context=context)
