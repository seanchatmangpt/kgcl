"""OR-Join backwards reachability analyzer (WCP-7 compliance).

The OR-join (structured synchronizing merge) must wait for all
potentially arriving tokens before firing. This requires analyzing
which unmarked preset conditions could still receive tokens from
active paths in the net.

Java Reference: YOrJoinRunner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet
    from kgcl.yawl.elements.y_task import YTask
    from kgcl.yawl.state.y_marking import YMarking


@dataclass(frozen=True)
class OrJoinAnalysisResult:
    """Result of OR-join enablement analysis.

    Parameters
    ----------
    is_enabled : bool
        Whether the OR-join can safely fire
    marked_presets : frozenset[str]
        Preset condition IDs that have tokens
    unmarked_presets : frozenset[str]
        Preset condition IDs without tokens
    blocked_by : frozenset[str]
        Unmarked presets that could still receive tokens (blocking)
    """

    is_enabled: bool
    marked_presets: frozenset[str]
    unmarked_presets: frozenset[str]
    blocked_by: frozenset[str]


@dataclass
class YOrJoinAnalyzer:
    """Analyzer for OR-join enablement using backwards reachability.

    The OR-join semantics require:
    1. At least one preset condition has a token
    2. No unmarked preset can receive a token from active paths

    An unmarked preset CAN receive a token if there exists a path from
    any currently marked condition to that preset that doesn't go through
    the OR-join task itself.

    Parameters
    ----------
    net : YNet
        The workflow net containing the OR-join task
    marking : YMarking
        Current token distribution

    Examples
    --------
    >>> analyzer = YOrJoinAnalyzer(net=net, marking=marking)
    >>> result = analyzer.is_or_join_enabled(or_join_task)
    >>> if result.is_enabled:
    ...     # Safe to fire
    ... else:
    ...     # Blocked by: result.blocked_by
    """

    net: YNet
    marking: YMarking
    _reachability_cache: dict[tuple[str, str], bool] = field(default_factory=dict, repr=False)

    def is_or_join_enabled(self, task: YTask, exclude_task_id: str | None = None) -> OrJoinAnalysisResult:
        """Determine if OR-join task should fire.

        Parameters
        ----------
        task : YTask
            The OR-join task to analyze
        exclude_task_id : str | None
            Task ID to exclude from paths (usually the OR-join itself)

        Returns
        -------
        OrJoinAnalysisResult
            Analysis result with enablement and blocking info
        """
        if exclude_task_id is None:
            exclude_task_id = task.id

        preset_conditions = self._get_preset_conditions(task)

        if not preset_conditions:
            return OrJoinAnalysisResult(
                is_enabled=False, marked_presets=frozenset(), unmarked_presets=frozenset(), blocked_by=frozenset()
            )

        # Partition presets into marked and unmarked
        marked_presets: set[str] = set()
        unmarked_presets: set[str] = set()

        for cond_id in preset_conditions:
            if self.marking.has_tokens(cond_id):
                marked_presets.add(cond_id)
            else:
                unmarked_presets.add(cond_id)

        # Must have at least one token to consider firing
        if not marked_presets:
            return OrJoinAnalysisResult(
                is_enabled=False,
                marked_presets=frozenset(marked_presets),
                unmarked_presets=frozenset(unmarked_presets),
                blocked_by=frozenset(unmarked_presets),
            )

        # If all presets are marked, fire immediately
        if not unmarked_presets:
            return OrJoinAnalysisResult(
                is_enabled=True,
                marked_presets=frozenset(marked_presets),
                unmarked_presets=frozenset(),
                blocked_by=frozenset(),
            )

        # Check if any unmarked preset can receive a token
        # from currently active (marked) conditions
        blocked_by: set[str] = set()
        all_marked_conditions = set(self.marking.get_marked_conditions())

        for unmarked in unmarked_presets:
            if self._can_reach_from_active(unmarked, all_marked_conditions, exclude_task_id):
                blocked_by.add(unmarked)

        is_enabled = len(blocked_by) == 0

        return OrJoinAnalysisResult(
            is_enabled=is_enabled,
            marked_presets=frozenset(marked_presets),
            unmarked_presets=frozenset(unmarked_presets),
            blocked_by=frozenset(blocked_by),
        )

    def _can_reach_from_active(self, target: str, active_conditions: set[str], exclude_task: str) -> bool:
        """Check if target is reachable from any active condition.

        Uses forward reachability from each active condition to
        determine if target can receive a token.

        Parameters
        ----------
        target : str
            Target condition ID (an unmarked OR-join preset)
        active_conditions : set[str]
            Currently marked condition IDs
        exclude_task : str
            Task to exclude from paths (the OR-join itself)

        Returns
        -------
        bool
            True if target is reachable from any active condition
        """
        for start in active_conditions:
            # Don't consider paths from OR-join's own presets
            # (they already have tokens or we're checking them)
            cache_key = (start, target)
            if cache_key in self._reachability_cache:
                if self._reachability_cache[cache_key]:
                    return True
                continue

            reachable = self._is_forward_reachable(start, target, exclude_task, set())
            self._reachability_cache[cache_key] = reachable

            if reachable:
                return True

        return False

    def _is_forward_reachable(self, current: str, target: str, exclude_task: str, visited: set[str]) -> bool:
        """Check if target is reachable from current via forward traversal.

        Traverses the net forward (condition -> task -> condition)
        to find if target can be reached.

        Parameters
        ----------
        current : str
            Current position (condition ID)
        target : str
            Target condition ID
        exclude_task : str
            Task to exclude from traversal
        visited : set[str]
            Already visited elements (cycle detection)

        Returns
        -------
        bool
            True if target is reachable
        """
        if current == target:
            return True

        if current in visited:
            return False

        visited = visited | {current}

        # Current is a condition - find tasks it can enable
        for flow in self.net.flows.values():
            if flow.source_id != current:
                continue

            # flow goes from current condition to a task
            task_id = flow.target_id
            if task_id == exclude_task:
                continue

            if task_id not in self.net.tasks:
                continue

            task = self.net.tasks[task_id]

            # Find conditions in task's postset
            for post_flow in self.net.flows.values():
                if post_flow.source_id != task_id:
                    continue

                post_cond = post_flow.target_id
                if post_cond not in self.net.conditions:
                    continue

                if self._is_forward_reachable(post_cond, target, exclude_task, visited):
                    return True

        return False

    def _get_preset_conditions(self, task: YTask) -> list[str]:
        """Get condition IDs in task's preset.

        Parameters
        ----------
        task : YTask
            Task to get preset for

        Returns
        -------
        list[str]
            Condition IDs feeding into this task
        """
        conditions = []
        for flow_id in task.preset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.source_id in self.net.conditions:
                conditions.append(flow.source_id)
        return conditions

    def can_reach_condition(self, from_conditions: set[str], target: str, exclude_task: str | None = None) -> bool:
        """Check if target is reachable from any of the given conditions.

        Public method for testing reachability.

        Parameters
        ----------
        from_conditions : set[str]
            Starting condition IDs
        target : str
            Target condition ID
        exclude_task : str | None
            Task to exclude from paths

        Returns
        -------
        bool
            True if target is reachable
        """
        exclude = exclude_task or ""
        for start in from_conditions:
            if self._is_forward_reachable(start, target, exclude, set()):
                return True
        return False

    def clear_cache(self) -> None:
        """Clear the reachability cache.

        Call when marking changes significantly.
        """
        self._reachability_cache.clear()
