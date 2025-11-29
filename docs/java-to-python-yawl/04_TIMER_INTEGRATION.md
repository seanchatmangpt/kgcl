# Gap 4: Timer Integration

## Problem Statement

Timer service exists but is NOT integrated with the engine. Work item timers and deadlines don't fire automatically.

## Current State

### Timer Service (Complete)
```python
# src/kgcl/yawl/engine/y_timer.py
@dataclass
class YTimerService:
    timers: dict[str, YTimer]
    deadlines: dict[str, YDeadline]
    timer_handlers: dict[TimerAction, Callable[[YTimer], None]]
    deadline_handlers: dict[TimerAction, Callable[[YDeadline], None]]

    def start(self) -> None: ...    # Background thread
    def add_timer(self, timer) -> None: ...
    def create_timer_for_work_item(...) -> YTimer: ...
    # etc.
```

### Engine (No Timer)
```python
# src/kgcl/yawl/engine/y_engine.py
@dataclass
class YEngine:
    # NO timer_service field
    # NO timer creation on work item
    # NO timer handlers registered
```

## Target Behavior

```
Work Item Created
       │
       ▼
Check task.has_timer()
       │
       ├─► True: Create timer with trigger/action
       │
       ▼
Timer Service monitors...
       │
       ├─► Timer expires → Execute action
       │       │
       │       ├─► NOTIFY: Send notification
       │       ├─► FAIL: fail_work_item()
       │       ├─► COMPLETE: complete_work_item()
       │       └─► ESCALATE: escalate_work_item()
       │
       ▼
Work Item Completed/Cancelled
       │
       ▼
Cancel associated timers
```

## Implementation

### Step 1: Add Timer Service to Engine

```python
# src/kgcl/yawl/engine/y_engine.py

from kgcl.yawl.engine.y_timer import (
    YTimerService, YTimer, YDeadline,
    TimerTrigger, TimerAction, parse_duration
)

@dataclass
class YEngine:
    # ... existing fields ...

    # Timer service
    timer_service: YTimerService = field(default_factory=YTimerService)

    def start(self) -> None:
        """Start the engine."""
        self.status = EngineStatus.STARTING
        self.started = datetime.now()

        # Initialize timer handlers
        self._setup_timer_handlers()

        # Start timer service
        self.timer_service.start()

        self.status = EngineStatus.RUNNING
        self._emit_event("ENGINE_STARTED")

    def stop(self) -> None:
        """Stop the engine."""
        self.status = EngineStatus.STOPPING

        # Stop timer service
        self.timer_service.stop()

        # Cancel all running cases
        for case in self.cases.values():
            if case.is_running():
                case.cancel("Engine stopping")

        self.status = EngineStatus.STOPPED
        self._emit_event("ENGINE_STOPPED")

    def _setup_timer_handlers(self) -> None:
        """Register timer action handlers."""
        self.timer_service.set_timer_handler(
            TimerAction.NOTIFY,
            self._handle_timer_notify
        )
        self.timer_service.set_timer_handler(
            TimerAction.FAIL,
            self._handle_timer_fail
        )
        self.timer_service.set_timer_handler(
            TimerAction.COMPLETE,
            self._handle_timer_complete
        )
        self.timer_service.set_timer_handler(
            TimerAction.CANCEL,
            self._handle_timer_cancel
        )
        self.timer_service.set_timer_handler(
            TimerAction.ESCALATE,
            self._handle_timer_escalate
        )

        # Deadline handlers
        self.timer_service.set_deadline_handler(
            TimerAction.NOTIFY,
            self._handle_deadline_notify
        )
        self.timer_service.set_deadline_handler(
            TimerAction.FAIL,
            self._handle_deadline_fail
        )
```

### Step 2: Create Timers on Work Item Creation

```python
def _resource_work_item(self, work_item: YWorkItem, task: YTask) -> None:
    """Resource a work item based on task configuration."""
    # Fire the work item
    work_item.fire()

    # Create timer if task has one configured
    self._create_work_item_timer(work_item, task)

    # ... existing resourcing logic ...


def _create_work_item_timer(
    self,
    work_item: YWorkItem,
    task: YTask,
) -> None:
    """Create timer for work item if task configured."""
    from kgcl.yawl.elements.y_atomic_task import YAtomicTask

    if not isinstance(task, YAtomicTask):
        return

    if not task.has_timer():
        return

    # Parse timer configuration
    duration = parse_duration(task.timer_expression)

    # Map trigger string to enum
    trigger_map = {
        "OnEnabled": TimerTrigger.ON_ENABLED,
        "OnOffered": TimerTrigger.ON_OFFERED,
        "OnAllocated": TimerTrigger.ON_ALLOCATED,
        "OnStarted": TimerTrigger.ON_STARTED,
    }
    trigger = trigger_map.get(task.timer_trigger, TimerTrigger.ON_ENABLED)

    # Determine action (could be task attribute, default to NOTIFY)
    action = TimerAction.NOTIFY
    if hasattr(task, 'timer_action'):
        action_map = {
            "notify": TimerAction.NOTIFY,
            "fail": TimerAction.FAIL,
            "complete": TimerAction.COMPLETE,
            "cancel": TimerAction.CANCEL,
            "escalate": TimerAction.ESCALATE,
        }
        action = action_map.get(task.timer_action, TimerAction.NOTIFY)

    # Create timer
    timer = self.timer_service.create_timer_for_work_item(
        work_item_id=work_item.id,
        duration=duration,
        trigger=trigger,
        action=action,
    )

    # Store timer reference on work item
    work_item.timer = WorkItemTimer(
        trigger=task.timer_trigger or "OnEnabled",
        duration=task.timer_expression,
        expiry=timer.expiry,
        action=action.name.lower(),
    )
```

### Step 3: Timer Action Handlers

```python
def _handle_timer_notify(self, timer: YTimer) -> None:
    """Handle timer notification."""
    self._emit_event(
        "TIMER_EXPIRED",
        work_item_id=timer.work_item_id,
        data={
            "timer_id": timer.id,
            "action": "notify",
            "duration": str(timer.duration),
        },
    )


def _handle_timer_fail(self, timer: YTimer) -> None:
    """Handle timer failure action."""
    self.fail_work_item(timer.work_item_id, "Timer expired")


def _handle_timer_complete(self, timer: YTimer) -> None:
    """Handle timer auto-complete action."""
    self.complete_work_item(
        timer.work_item_id,
        output_data={"_auto_completed": True, "_reason": "timer_expired"},
    )


def _handle_timer_cancel(self, timer: YTimer) -> None:
    """Handle timer cancel action."""
    work_item = self._find_work_item(timer.work_item_id)
    if work_item and work_item.is_active():
        work_item.cancel("Timer expired")
        case = self.cases.get(work_item.case_id)
        if case:
            case.update_work_item_status(work_item.id)


def _handle_timer_escalate(self, timer: YTimer) -> None:
    """Handle timer escalation."""
    work_item = self._find_work_item(timer.work_item_id)
    if work_item is None:
        return

    # Find task for escalation target
    case = self.cases.get(work_item.case_id)
    if case is None:
        return

    spec = self.specifications.get(case.specification_id)
    if spec is None:
        return

    task = spec.get_task(work_item.task_id)

    # Escalate: re-offer with escalation flag
    self._emit_event(
        "WORK_ITEM_ESCALATED",
        case_id=work_item.case_id,
        work_item_id=work_item.id,
        task_id=work_item.task_id,
        data={"original_resource": work_item.resource_id},
    )

    # Could implement: find manager, reallocate, etc.


def _handle_deadline_notify(self, deadline: YDeadline) -> None:
    """Handle deadline notification."""
    self._emit_event(
        "DEADLINE_WARNING" if deadline.warning_sent else "DEADLINE_BREACHED",
        work_item_id=deadline.work_item_id,
        case_id=deadline.case_id,
        data={
            "deadline_id": deadline.id,
            "deadline": deadline.deadline.isoformat(),
        },
    )


def _handle_deadline_fail(self, deadline: YDeadline) -> None:
    """Handle deadline failure."""
    if deadline.work_item_id:
        self.fail_work_item(deadline.work_item_id, "Deadline breached")
    elif deadline.case_id:
        self.cancel_case(deadline.case_id, "Case deadline breached")
```

### Step 4: Cancel Timers on Work Item Completion

```python
def complete_work_item(
    self,
    work_item_id: str,
    output_data: dict[str, Any] | None = None,
) -> bool:
    """Complete a work item."""
    work_item = self._find_work_item(work_item_id)
    if work_item is None:
        return False

    # Cancel any associated timers
    self._cancel_work_item_timers(work_item_id)

    # ... existing completion logic ...


def _cancel_work_item_timers(self, work_item_id: str) -> None:
    """Cancel all timers for a work item."""
    timers = self.timer_service.get_timers_for_work_item(work_item_id)
    for timer in timers:
        self.timer_service.cancel_timer(timer.id)

    deadlines = self.timer_service.get_deadlines_for_work_item(work_item_id)
    for deadline in deadlines:
        self.timer_service.remove_deadline(deadline.id)
```

## Test Cases

```python
class TestTimerIntegration:
    """Tests for timer-engine integration."""

    def test_timer_created_for_task_with_timer(self) -> None:
        """Timer created when task has timer configured."""
        task = YAtomicTask(
            id="Review",
            timer_expression="PT1H",  # 1 hour
            timer_trigger="OnStarted",
        )
        # Create work item
        # Assert: timer created in timer service

    def test_timer_not_created_for_task_without_timer(self) -> None:
        """No timer created for task without configuration."""
        task = YAtomicTask(id="Review")
        # Create work item
        # Assert: no timer in timer service

    def test_timer_fail_action(self) -> None:
        """Timer with FAIL action fails work item."""
        # Create work item with short timer (100ms)
        # Wait for expiry
        # Assert: work item status == FAILED

    def test_timer_cancelled_on_completion(self) -> None:
        """Timer cancelled when work item completes."""
        # Create work item with timer
        # Complete work item
        # Assert: timer.cancelled == True

    def test_deadline_warning(self) -> None:
        """Deadline warning fired before breach."""
        # Create deadline with warning_before
        # Wait until warning time
        # Assert: DEADLINE_WARNING event emitted

    def test_escalation(self) -> None:
        """Timer escalation emits event."""
        # Create work item with escalation timer
        # Wait for expiry
        # Assert: WORK_ITEM_ESCALATED event emitted
```

## Dependencies

- None (uses existing timer service)

## Complexity: LOW

All components exist, just need wiring.

## Estimated Effort

- Implementation: 2-3 hours
- Testing: 2-3 hours
- Total: 0.5 day
