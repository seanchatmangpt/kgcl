# Gap 1: OR-Join Semantics & Expression Evaluation

## Problem Statement

The OR-join is YAWL's most complex construct. Unlike AND-join (wait for all) or XOR-join (take any one), OR-join must:

1. Fire when all **expected** tokens have arrived
2. Determine which tokens are "expected" by analyzing the net structure
3. Avoid firing prematurely when more tokens could still arrive

## Current Implementation

```python
# src/kgcl/yawl/engine/y_net_runner.py:171-174
else:  # OR join - simplified (full OR-join needs flow history)
    return any(
        self.marking.has_tokens(cond_id) for cond_id in preset_conditions
    )
```

**Problem**: Fires when ANY preset has a token, regardless of whether other tokens might arrive.

## Example: Why This Breaks

```
         ┌──────────┐
    ┌────│ Task A   │────┐
    │    └──────────┘    │
    │         c1         │
[start]                [OR-Join]──[end]
    │         c2         │
    │    ┌──────────┐    │
    └────│ Task B   │────┘
         └──────────┘
```

**Scenario**: AND-split at start, both paths active.

1. Task A completes → token at c1
2. Current OR-join: "c1 has token? YES → FIRE!"
3. **Wrong**: Task B is still running, its token hasn't arrived yet
4. OR-join fires with only 1 token instead of waiting for both

## Java YAWL Solution

Java uses **optimistic/pessimistic OR-join evaluation**:

### Algorithm (Pessimistic)
```
1. Get all preset conditions
2. For each UNMARKED preset condition:
   a. Trace backward through net
   b. Check if any MARKED condition can reach this preset
   c. If reachable → more tokens could arrive → WAIT
3. If no unmarked preset is reachable from any marked condition:
   → All expected tokens have arrived → FIRE
```

### Reachability Check
```
can_reach(source_condition, target_condition, or_join_task):
    visited = set()
    queue = [source_condition]

    while queue:
        current = queue.pop()
        if current == target_condition:
            return True
        if current in visited:
            continue
        visited.add(current)

        # Get all outgoing flows
        for flow in current.postset_flows:
            next_element = flow.target

            # Skip the OR-join itself (avoid self-loop)
            if next_element == or_join_task:
                continue

            # If task, add its postset conditions
            if is_task(next_element):
                queue.extend(next_element.postset_conditions)
            else:
                queue.append(next_element)

    return False
```

## Python Implementation Plan

### New Module: `src/kgcl/yawl/util/y_analyzer.py`

```python
"""Net structure analysis for OR-join evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet
    from kgcl.yawl.elements.y_task import YTask
    from kgcl.yawl.state.y_marking import YMarking


@dataclass
class YNetAnalyzer:
    """Analyzer for net structure and reachability."""

    net: YNet

    def can_reach(
        self,
        source_id: str,
        target_id: str,
        exclude_element_id: str | None = None,
    ) -> bool:
        """Check if source can reach target without passing through exclude.

        Parameters
        ----------
        source_id : str
            Starting element ID
        target_id : str
            Target element ID
        exclude_element_id : str | None
            Element to exclude from paths (typically the OR-join task)

        Returns
        -------
        bool
            True if path exists
        """
        visited: set[str] = set()
        queue: list[str] = [source_id]

        while queue:
            current_id = queue.pop(0)

            if current_id == target_id:
                return True

            if current_id in visited:
                continue

            visited.add(current_id)

            # Skip excluded element
            if current_id == exclude_element_id:
                continue

            # Get successors
            successors = self._get_successors(current_id)
            queue.extend(s for s in successors if s not in visited)

        return False

    def _get_successors(self, element_id: str) -> list[str]:
        """Get direct successors of an element."""
        successors = []

        # Check if it's a condition
        if element_id in self.net.conditions:
            for flow in self.net.flows.values():
                if flow.source_id == element_id:
                    successors.append(flow.target_id)

        # Check if it's a task
        elif element_id in self.net.tasks:
            task = self.net.tasks[element_id]
            for flow_id in task.postset_flows:
                flow = self.net.flows.get(flow_id)
                if flow:
                    successors.append(flow.target_id)

        return successors

    def is_or_join_enabled(
        self,
        task: YTask,
        marking: YMarking,
    ) -> bool:
        """Check if OR-join task should fire.

        Uses pessimistic evaluation: only fire when no more
        tokens can possibly arrive at any unmarked preset.

        Parameters
        ----------
        task : YTask
            OR-join task to evaluate
        marking : YMarking
            Current token marking

        Returns
        -------
        bool
            True if OR-join should fire
        """
        # Get preset conditions
        preset_ids = self._get_preset_conditions(task)

        if not preset_ids:
            return False

        # Split into marked and unmarked
        marked = [c for c in preset_ids if marking.has_tokens(c)]
        unmarked = [c for c in preset_ids if not marking.has_tokens(c)]

        # Must have at least one token
        if not marked:
            return False

        # If all presets marked, definitely fire
        if not unmarked:
            return True

        # Check if any unmarked preset could receive a token
        # from any currently marked condition in the net
        all_marked_conditions = marking.get_marked_conditions()

        for unmarked_preset in unmarked:
            for marked_condition in all_marked_conditions:
                # Skip if marked condition IS this preset
                if marked_condition == unmarked_preset:
                    continue

                # Check if marked condition can reach unmarked preset
                # without passing through the OR-join itself
                if self.can_reach(
                    marked_condition,
                    unmarked_preset,
                    exclude_element_id=task.id,
                ):
                    # Token could still arrive → wait
                    return False

        # No unmarked preset is reachable → safe to fire
        return True

    def _get_preset_conditions(self, task: YTask) -> list[str]:
        """Get condition IDs in task's preset."""
        conditions = []
        for flow_id in task.preset_flows:
            flow = self.net.flows.get(flow_id)
            if flow and flow.source_id in self.net.conditions:
                conditions.append(flow.source_id)
        return conditions
```

### Modify: `src/kgcl/yawl/engine/y_net_runner.py`

```python
from kgcl.yawl.util.y_analyzer import YNetAnalyzer

@dataclass
class YNetRunner:
    net: YNet
    # ... existing fields ...
    _analyzer: YNetAnalyzer | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._analyzer = YNetAnalyzer(self.net)

    def _is_task_enabled(self, task: YTask) -> bool:
        """Check if task is enabled based on join type."""
        preset_conditions = self._get_preset_conditions(task)

        if not preset_conditions:
            return False

        if task.join_type == JoinType.AND:
            return all(
                self.marking.has_tokens(cond_id)
                for cond_id in preset_conditions
            )
        elif task.join_type == JoinType.XOR:
            return any(
                self.marking.has_tokens(cond_id)
                for cond_id in preset_conditions
            )
        else:  # OR join - full semantics
            return self._analyzer.is_or_join_enabled(task, self.marking)
```

## Test Cases

### Test 1: XOR-Split followed by OR-Join
```python
def test_or_join_after_xor_split(self) -> None:
    """OR-join fires immediately after XOR-split (only one path taken)."""
    # XOR-split → only path A taken
    # OR-join should fire with just path A token
    # (path B will NEVER get a token)
    pass
```

### Test 2: AND-Split followed by OR-Join
```python
def test_or_join_after_and_split_waits(self) -> None:
    """OR-join waits for both branches after AND-split."""
    # AND-split → both paths A and B active
    # Complete path A
    # OR-join should NOT fire (path B still active)
    pass

def test_or_join_after_and_split_fires(self) -> None:
    """OR-join fires when both branches complete."""
    # AND-split → both paths complete
    # OR-join should fire with both tokens
    pass
```

### Test 3: Mixed patterns
```python
def test_or_join_complex_net(self) -> None:
    """OR-join with mix of active and inactive paths."""
    # Complex net with some paths disabled by XOR
    # Some paths active from AND
    # OR-join should correctly identify which paths to wait for
    pass
```

## Performance Considerations

- Reachability check is O(V + E) per evaluation
- Cache results for static net analysis
- For large nets, consider incremental updates

## Dependencies

- None (uses existing net structure)

## Estimated Effort

- Implementation: 4-6 hours
- Testing: 4-6 hours
- Total: 1-2 days
