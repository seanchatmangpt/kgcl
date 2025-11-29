"""Resource filters for work item assignment (RBAC).

Implements YAWL's resource filters including:
- Filter expressions (role, capability, position, history)
- Four-eyes rule (separation of duties)
- Distribution strategies
- Filter context for evaluation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable


class FilterType(Enum):
    """Type of resource filter.

    Attributes
    ----------
    ROLE : auto
        Filter by role
    CAPABILITY : auto
        Filter by capability
    POSITION : auto
        Filter by position
    ORG_GROUP : auto
        Filter by org group
    FOUR_EYES : auto
        Four-eyes separation rule
    HISTORY : auto
        Filter by work item history
    CUSTOM : auto
        Custom filter expression
    """

    ROLE = auto()
    CAPABILITY = auto()
    POSITION = auto()
    ORG_GROUP = auto()
    FOUR_EYES = auto()
    HISTORY = auto()
    CUSTOM = auto()


class FilterOperator(Enum):
    """Filter operator for combining conditions.

    Attributes
    ----------
    EQUALS : auto
        Exact match
    NOT_EQUALS : auto
        Not match
    IN : auto
        In set
    NOT_IN : auto
        Not in set
    CONTAINS : auto
        Contains value
    STARTS_WITH : auto
        Starts with value
    """

    EQUALS = auto()
    NOT_EQUALS = auto()
    IN = auto()
    NOT_IN = auto()
    CONTAINS = auto()
    STARTS_WITH = auto()


@dataclass(frozen=True)
class WorkItemHistoryEntry:
    """Record of work item completion for history filters.

    Parameters
    ----------
    case_id : str
        Case ID
    task_id : str
        Task ID
    work_item_id : str
        Work item ID
    participant_id : str
        Participant who completed it
    completed_at : datetime
        Completion timestamp
    task_name : str
        Task name for display
    """

    case_id: str
    task_id: str
    work_item_id: str
    participant_id: str
    completed_at: datetime
    task_name: str = ""


@dataclass
class FilterContext:
    """Context for filter evaluation.

    Provides access to case data, history, and other information
    needed to evaluate resource filters.

    Parameters
    ----------
    case_id : str
        Current case ID
    task_id : str
        Current task ID
    work_item_id : str
        Current work item ID
    case_data : dict[str, Any]
        Case-level data
    work_item_history : list[WorkItemHistoryEntry]
        History of completed work items for this case
    four_eyes_tasks : set[str]
        Task IDs that require four-eyes separation
    """

    case_id: str
    task_id: str
    work_item_id: str
    case_data: dict[str, Any] = field(default_factory=dict)
    work_item_history: list[WorkItemHistoryEntry] = field(default_factory=list)
    four_eyes_tasks: set[str] = field(default_factory=set)

    def get_participants_who_completed_task(self, task_id: str) -> set[str]:
        """Get participants who completed a specific task.

        Parameters
        ----------
        task_id : str
            Task ID to check

        Returns
        -------
        set[str]
            Participant IDs
        """
        return {h.participant_id for h in self.work_item_history if h.task_id == task_id}

    def get_participants_who_completed_any(self, task_ids: set[str]) -> set[str]:
        """Get participants who completed any of the specified tasks.

        Parameters
        ----------
        task_ids : set[str]
            Task IDs to check

        Returns
        -------
        set[str]
            Participant IDs
        """
        return {h.participant_id for h in self.work_item_history if h.task_id in task_ids}


@dataclass
class FilterExpression:
    """A single filter expression.

    Parameters
    ----------
    filter_type : FilterType
        Type of filter
    operator : FilterOperator
        Comparison operator
    value : Any
        Filter value
    name : str
        Filter name (for ROLE, CAPABILITY, etc.)
    negate : bool
        Whether to negate the filter
    """

    filter_type: FilterType
    operator: FilterOperator = FilterOperator.EQUALS
    value: Any = None
    name: str = ""
    negate: bool = False

    def evaluate(
        self,
        participant: Any,  # YParticipant
        context: FilterContext,
    ) -> bool:
        """Evaluate this filter against a participant.

        Parameters
        ----------
        participant : Any
            Participant to evaluate
        context : FilterContext
            Filter context

        Returns
        -------
        bool
            True if participant matches filter
        """
        result = self._evaluate_internal(participant, context)
        return not result if self.negate else result

    def _evaluate_internal(self, participant: Any, context: FilterContext) -> bool:
        """Internal evaluation logic.

        Parameters
        ----------
        participant : Any
            Participant to evaluate
        context : FilterContext
            Filter context

        Returns
        -------
        bool
            Evaluation result
        """
        if self.filter_type == FilterType.ROLE:
            return self._match_value(participant.roles, self.value, self.operator)

        if self.filter_type == FilterType.CAPABILITY:
            return self._match_value(participant.capabilities, self.value, self.operator)

        if self.filter_type == FilterType.POSITION:
            return self._match_value(participant.positions, self.value, self.operator)

        if self.filter_type == FilterType.ORG_GROUP:
            return self._match_value(participant.org_groups, self.value, self.operator)

        if self.filter_type == FilterType.FOUR_EYES:
            # Check if participant completed any four-eyes task
            excluded = context.get_participants_who_completed_any(context.four_eyes_tasks)
            return participant.id not in excluded

        if self.filter_type == FilterType.HISTORY:
            # Check if participant completed the specified task
            completed = context.get_participants_who_completed_task(self.name)
            if self.operator == FilterOperator.NOT_IN:
                return participant.id not in completed
            return participant.id in completed

        return True  # Unknown filter type - allow

    def _match_value(self, participant_values: Any, filter_value: Any, operator: FilterOperator) -> bool:
        """Match participant values against filter value.

        Parameters
        ----------
        participant_values : Any
            Values from participant (set or single value)
        filter_value : Any
            Value to match
        operator : FilterOperator
            Comparison operator

        Returns
        -------
        bool
            Match result
        """
        # Handle set comparison
        if isinstance(participant_values, (set, list, frozenset)):
            values_set = set(participant_values)
        else:
            values_set = {participant_values}

        if isinstance(filter_value, (set, list, frozenset)):
            filter_set = set(filter_value)
        else:
            filter_set = {filter_value}

        if operator == FilterOperator.EQUALS:
            return bool(values_set & filter_set)

        if operator == FilterOperator.NOT_EQUALS:
            return not bool(values_set & filter_set)

        if operator == FilterOperator.IN:
            return bool(values_set & filter_set)

        if operator == FilterOperator.NOT_IN:
            return not bool(values_set & filter_set)

        if operator == FilterOperator.CONTAINS:
            return any(str(filter_value) in str(v) for v in values_set)

        if operator == FilterOperator.STARTS_WITH:
            return any(str(v).startswith(str(filter_value)) for v in values_set)

        return False


@dataclass
class CompositeFilter:
    """Composite filter combining multiple expressions.

    Parameters
    ----------
    filters : list[FilterExpression]
        Filter expressions
    combine_or : bool
        True for OR, False for AND
    """

    filters: list[FilterExpression] = field(default_factory=list)
    combine_or: bool = False

    def add_filter(self, filter_expr: FilterExpression) -> None:
        """Add a filter expression.

        Parameters
        ----------
        filter_expr : FilterExpression
            Filter to add
        """
        self.filters.append(filter_expr)

    def evaluate(self, participant: Any, context: FilterContext) -> bool:
        """Evaluate composite filter against participant.

        Parameters
        ----------
        participant : Any
            Participant to evaluate
        context : FilterContext
            Filter context

        Returns
        -------
        bool
            Evaluation result
        """
        if not self.filters:
            return True

        if self.combine_or:
            return any(f.evaluate(participant, context) for f in self.filters)
        else:
            return all(f.evaluate(participant, context) for f in self.filters)


def create_four_eyes_filter(task_ids: set[str]) -> FilterExpression:
    """Create a four-eyes separation filter.

    Parameters
    ----------
    task_ids : set[str]
        Task IDs that require separation

    Returns
    -------
    FilterExpression
        Four-eyes filter
    """
    return FilterExpression(filter_type=FilterType.FOUR_EYES, value=task_ids)


def create_role_filter(role_id: str, negate: bool = False) -> FilterExpression:
    """Create a role filter.

    Parameters
    ----------
    role_id : str
        Role ID to match
    negate : bool
        Whether to negate

    Returns
    -------
    FilterExpression
        Role filter
    """
    return FilterExpression(filter_type=FilterType.ROLE, value=role_id, negate=negate)


def create_history_filter(task_id: str, must_have_completed: bool = True) -> FilterExpression:
    """Create a history-based filter.

    Parameters
    ----------
    task_id : str
        Task ID to check
    must_have_completed : bool
        True if participant must have completed, False if must not have

    Returns
    -------
    FilterExpression
        History filter
    """
    return FilterExpression(
        filter_type=FilterType.HISTORY,
        operator=(FilterOperator.IN if must_have_completed else FilterOperator.NOT_IN),
        name=task_id,
    )
