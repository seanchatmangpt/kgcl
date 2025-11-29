# YAWL Engine Conversion Map

This document maps incomplete/stub implementations in the Python YAWL engine to their corresponding locations, providing specific file paths and line numbers for what needs to be converted from the Java YAWL implementation.

**Status Legend:**
- `[STUB]` - Data structures exist but no execution logic
- `[PARTIAL]` - Some functionality implemented, key features missing
- `[TODO]` - Explicitly marked as incomplete in code
- `[MISSING]` - Required by Java but not implemented at all

---

## 1. OR-Join Semantics [PARTIAL]

**Current State:** Simplified OR-join that fires when any preset has tokens.

**Java Requirement:** Full OR-join requires future path analysis to determine if more tokens could arrive from other branches.

**Location:**
- `src/kgcl/yawl/engine/y_net_runner.py:171-174`

```python
# Current simplified implementation (lines 171-174):
else:  # OR join - simplified (full OR-join needs flow history)
    return any(
        self.marking.has_tokens(cond_id) for cond_id in preset_conditions
    )
```

**What Needs Conversion:**
1. Implement future path analysis algorithm from Java `YNetRunner.isOrJoinEnabled()`
2. Track token history to determine if more tokens are expected
3. Add method to analyze reachability of preset conditions from current marking
4. Consider deadlock detection for OR-join scenarios

**Java Reference:** `org.yawlfoundation.yawl.engine.YNetRunner.isOrJoinEnabled()`

---

## 2. XPath/XQuery Expression Evaluation [PARTIAL]

**Current State:** Only supports "true"/"false" literals and simple data key lookup.

**Java Requirement:** Full XQuery 1.0 / XPath 2.0 expression evaluation for predicates, MI queries, and data bindings.

**Location:**
- `src/kgcl/yawl/engine/y_net_runner.py:477-504`

```python
# Current simplified implementation (lines 477-504):
def _evaluate_predicate(
    self, predicate: str, data: dict[str, Any] | None
) -> bool:
    """Evaluate predicate string.

    Simplified implementation supporting:
    - "true" / "false" literals
    - Direct data key lookup
    """
    if predicate == "true":
        return True
    if predicate == "false":
        return False
    if data and predicate in data:
        return bool(data[predicate])
    return True  # Default true
```

**Also Affects:**
- `src/kgcl/yawl/elements/y_multi_instance.py:140-189` - MI queries using `min_query`, `max_query`, `threshold_query`
- `src/kgcl/yawl/elements/y_atomic_task.py:140-170` - `YDataBinding.expression` field
- `src/kgcl/yawl/elements/y_exception.py:214-239` - `ExceptionRule.condition` field (line 238 has TODO)

```python
# Line 238 in y_exception.py:
# TODO: Evaluate condition expression
return True
```

**What Needs Conversion:**
1. Implement XQuery/XPath expression parser
2. Support standard XPath functions (string, numeric, boolean operations)
3. Support YAWL-specific functions for data access
4. Create expression evaluation context from case data
5. Handle type coercion between XML types and Python types

**Java Reference:** `org.yawlfoundation.yawl.util.XQuery`, `net.sf.saxon` integration

---

## 3. Multi-Instance Task Execution [STUB]

**Current State:** `YMultiInstanceAttributes` defined but not wired into engine execution.

**Java Requirement:** Full WCP-12 through WCP-15 pattern support with child work item spawning, instance synchronization, and aggregation.

**Locations:**

### Data Structures (Complete):
- `src/kgcl/yawl/elements/y_multi_instance.py:46-210` - `YMultiInstanceAttributes` class
- `src/kgcl/yawl/elements/y_atomic_task.py:359-436` - `YMultipleInstanceTask` class
- `src/kgcl/yawl/elements/y_task.py:136` - `multi_instance: YMultiInstanceAttributes | None`

### Engine Integration (MISSING):
- `src/kgcl/yawl/engine/y_net_runner.py` - No MI spawning in `fire_task()`
- `src/kgcl/yawl/engine/y_engine.py:516-552` - `_create_work_items_for_enabled_tasks()` doesn't handle MI

```python
# y_net_runner.py:216-272 - fire_task() doesn't check for multi-instance:
def fire_task(
    self, task_id: str, data: dict[str, Any] | None = None
) -> FireResult:
    # ... no check for task.is_multi_instance()
    # ... no spawning of child instances
```

**What Needs Conversion:**
1. In `fire_task()`: Check if task is multi-instance
2. Evaluate MI count query to determine instance count
3. Spawn child work items for each instance
4. Track child completion status
5. Implement synchronization barrier (wait for threshold or all)
6. Aggregate outputs from child instances
7. Handle dynamic instance creation (WCP-15)

**Java Reference:** `org.yawlfoundation.yawl.engine.YNetRunner.createMIInstances()`

---

## 4. Worklet Service (Exception Handling) [STUB]

**Current State:** Basic `YExceptionService` with rules/retry but no worklet invocation.

**Java Requirement:** Full "exlet" worklet subprocess execution for exception handling.

**Locations:**
- `src/kgcl/yawl/engine/y_exception.py:282-555`
- `src/kgcl/yawl/engine/y_exception.py:96` - `ExceptionAction.WORKLET` defined but not executed

```python
# Line 96 - WORKLET action defined:
WORKLET = auto()

# Lines 390-402 - handle_exception() doesn't invoke worklets:
def handle_exception(
    self, exception: YWorkflowException
) -> ExceptionAction:
    # ...
    # Note: WORKLET action is defined but handler execution
    # at line 394-399 is generic, doesn't load/execute worklet specs
```

**What Needs Conversion:**
1. Add worklet specification loading mechanism
2. Implement worklet subprocess instantiation
3. Create separate case execution for worklet
4. Handle worklet completion/failure
5. Integrate worklet results back into main case

**Java Reference:** `org.yawlfoundation.yawl.worklet.WorkletService`

---

## 5. Timer Integration with Engine [PARTIAL]

**Current State:** `YTimerService` exists standalone. Not integrated with `YEngine` to auto-fire timers.

**Locations:**
- `src/kgcl/yawl/engine/y_timer.py:306-631` - `YTimerService` class
- `src/kgcl/yawl/engine/y_engine.py` - No timer service integration

```python
# y_timer.py has full timer service but:
# y_engine.py doesn't create or use YTimerService

# y_atomic_task.py:216-219 defines timer fields but they're unused:
timer_expression: str | None = None
timer_trigger: str = "OnEnabled"
```

**What Needs Conversion:**
1. Add `YTimerService` instance to `YEngine`
2. Create timers when work items reach trigger state
3. Wire timer expiry actions to engine operations:
   - `NOTIFY` → emit event
   - `REASSIGN` → delegate work item
   - `ESCALATE` → notify manager
   - `COMPLETE` → auto-complete
   - `FAIL` → fail work item
   - `CANCEL` → cancel work item
4. Cancel timers when work items complete/fail

**Java Reference:** `org.yawlfoundation.yawl.engine.time.YTimerService`

---

## 6. External Service/Codelet Execution [STUB]

**Current State:** `task.codelet` field exists but is never executed.

**Locations:**
- `src/kgcl/yawl/elements/y_atomic_task.py:225` - `codelet: str | None = None`
- `src/kgcl/yawl/elements/y_decomposition.py:219` - `codelet: str | None = None`
- `src/kgcl/yawl/engine/y_engine.py:568-574` - Only checks `is_automated_task()`, doesn't execute

```python
# y_engine.py:568-574 - Detects automated task but doesn't execute codelet:
if isinstance(task, YAtomicTask):
    if task.is_automated_task() or task.resourcing.is_system_task():
        # System task - auto-start execution
        work_item.transition(WorkItemEvent.START)
        return  # <-- Missing: actual codelet invocation
```

**What Needs Conversion:**
1. Define codelet interface (Python protocol/ABC)
2. Implement codelet loading mechanism (dynamic import)
3. Execute codelet when automated task starts
4. Pass input parameters to codelet
5. Capture codelet output and map to work item output
6. Handle codelet exceptions

**Java Reference:** `org.yawlfoundation.yawl.engine.interfaceB.InterfaceBWebsideController`

---

## 7. Resource Service (RBAC) [PARTIAL]

**Current State:** Basic `YResourceManager` with roles/participants. Missing capability-based assignment, 4-eyes rule, filters.

**Locations:**
- `src/kgcl/yawl/resources/y_resource.py:519-918` - `YResourceManager` class
- `src/kgcl/yawl/elements/y_atomic_task.py:61-137` - `YResourcingSpec` class

```python
# y_resource.py:865-917 - find_participants() is basic:
def find_participants(
    self,
    role_ids: set[str] | None = None,
    position_ids: set[str] | None = None,
    capability_ids: set[str] | None = None,
    available_only: bool = True,
) -> list[YParticipant]:
    # Simple set intersection - no advanced features

# Missing from YResourcingSpec:
# - filter_expressions evaluation (lines 99-100 defined but unused)
# - distribution_set evaluation (line 101 defined but unused)
# - familiar_participant resolution (line 102 defined but unused)
```

**What Needs Conversion:**
1. Implement filter expression evaluation
2. Implement distribution set patterns (round-robin, random, etc.)
3. Add "familiar participant" resolution (same as previous task)
4. Implement separation of duties (4-eyes rule)
5. Add delegation chain support
6. Implement privilege-based access control
7. Add organizational hierarchy traversal for escalation

**Java Reference:** `org.yawlfoundation.yawl.resourcing.ResourceManager`

---

## 8. Composite Task (Subprocess) Execution [STUB]

**Current State:** `YCompositeTask` defined with `subnet_id` but actual subnet instantiation/execution missing.

**Locations:**
- `src/kgcl/yawl/elements/y_atomic_task.py:292-356` - `YCompositeTask` class
- `src/kgcl/yawl/engine/y_case.py:477-504` - `CaseFactory.create_sub_case()` exists

```python
# y_atomic_task.py:292-356 - YCompositeTask is defined but engine doesn't use it:
@dataclass
class YCompositeTask(YTask):
    task_type: TaskType = TaskType.COMPOSITE
    subnet_id: str | None = None
    # ...

# y_engine.py has NO code to:
# 1. Detect composite tasks
# 2. Create sub-case for subnet
# 3. Start subnet execution
# 4. Wait for subnet completion
# 5. Merge subnet output back to parent
```

**What Needs Conversion:**
1. In `_resource_work_item()`: detect composite task type
2. Create sub-case using `CaseFactory.create_sub_case()`
3. Get subnet from specification decompositions
4. Create `YNetRunner` for subnet
5. Start subnet execution
6. Handle subnet completion event
7. Merge subnet output to parent case data
8. Complete parent work item when subnet completes

**Java Reference:** `org.yawlfoundation.yawl.engine.YNetRunner.attemptToFireAtomicTask()` for composite handling

---

## 9. Persistence [STUB]

**Current State:** `YRepository`/`YSerializer` exist but only in-memory. No actual XML/DB persistence.

**Locations:**
- `src/kgcl/yawl/persistence/y_serializer.py:1-476` - JSON serialization only
- `src/kgcl/yawl/persistence/y_repository.py:1-550` - In-memory only

```python
# y_serializer.py - Has JSON but comments note limitation:
def from_dict(self, data: dict[str, Any]) -> YSpecification:
    """...
    Notes
    -----
    This is a simplified implementation. Full deserialization
    would need to reconstruct all nested objects properly.
    """

# y_repository.py - All repositories use dict storage:
_store: dict[str, Any] = field(default_factory=dict)  # In-memory only
```

**What Needs Conversion:**
1. Implement YAWL XML specification format serialization
2. Add database persistence layer (PostgreSQL adapter)
3. Implement specification versioning
4. Add case state checkpoint/restore
5. Implement work item persistence
6. Add marking snapshot persistence for recovery

**Java Reference:** `org.yawlfoundation.yawl.engine.interfaceA.InterfaceA_EnvironmentBasedServer`

---

## 10. Data Binding Evaluation [STUB]

**Current State:** `YDataBinding` defined but not evaluated during execution.

**Locations:**
- `src/kgcl/yawl/elements/y_atomic_task.py:140-171` - `YDataBinding` class
- `src/kgcl/yawl/elements/y_atomic_task.py:212-215` - Task has binding fields

```python
# y_atomic_task.py:140-171 - YDataBinding defined:
@dataclass
class YDataBinding:
    name: str
    expression: str  # <-- Never evaluated
    target: str
    is_input: bool = True

# y_engine.py - complete_work_item() doesn't evaluate output bindings:
def complete_work_item(
    self,
    work_item_id: str,
    output_data: dict[str, Any] | None = None,  # Raw data passed directly
) -> bool:
    # ... output_data is passed directly to fire_task, no binding evaluation
```

**What Needs Conversion:**
1. Before task execution: evaluate input bindings to create task input
2. After task completion: evaluate output bindings to update case data
3. Handle binding expression types (XQuery, copy, etc.)
4. Support schema validation during binding
5. Handle binding errors/exceptions

**Java Reference:** `org.yawlfoundation.yawl.engine.YNetRunner.evaluateDataMappings()`

---

## 11. Case-Level Data Management [PARTIAL]

**Current State:** `CaseData` is basic dict storage. No schema validation or type coercion.

**Locations:**
- `src/kgcl/yawl/engine/y_case.py:49-104` - `CaseData` class

```python
# y_case.py:49-104 - CaseData is simple dict wrapper:
@dataclass
class CaseData:
    variables: dict[str, Any] = field(default_factory=dict)
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    # No schema validation
    # No type coercion
    # No variable definitions from net
```

**What Needs Conversion:**
1. Initialize case data from net's local variables (`YVariable`)
2. Validate input data against specification schema
3. Coerce data types based on variable definitions
4. Track variable modification history
5. Support complex XML types (not just primitives)

**Java Reference:** `org.yawlfoundation.yawl.engine.YCase.getCaseData()`

---

## 12. Automatic Work Item Propagation [PARTIAL]

**Current State:** Work items created for initial tasks only. Manual workarounds needed for cascading.

**Location:**
- `src/kgcl/yawl/engine/y_engine.py:745-791` - `complete_work_item()`

```python
# y_engine.py:745-791 - Does create new work items but observed issues in tests:
def complete_work_item(...):
    # ...
    # Fire the task in the net runner
    runner.fire_task(work_item.task_id, output_data)

    # Check for completion
    if runner.completed:
        case.complete(output_data)
    else:
        # Create work items for newly enabled tasks
        self._create_work_items_for_enabled_tasks(case, runner)  # <-- Should work but test failures observed
```

**Known Issues from Tests:**
- Work items not automatically created for subsequent tasks in some scenarios
- Manual `fire_task()` calls required as workarounds
- Token propagation not triggering work item creation consistently

**What Needs Conversion:**
1. Ensure `_create_work_items_for_enabled_tasks()` is called after every token movement
2. Handle edge cases where task enables but work item already exists
3. Add event-driven work item creation (not just after completion)
4. Support work item creation for parallel branches

---

## Summary Table

| Feature | Status | Primary Location | Lines |
|---------|--------|-----------------|-------|
| OR-Join Semantics | PARTIAL | `engine/y_net_runner.py` | 171-174 |
| XPath/XQuery | PARTIAL | `engine/y_net_runner.py` | 477-504 |
| Multi-Instance | STUB | `elements/y_multi_instance.py`, `engine/y_net_runner.py` | 46-210, 216-272 |
| Worklet Service | STUB | `engine/y_exception.py` | 96, 367-402 |
| Timer Integration | PARTIAL | `engine/y_timer.py`, `engine/y_engine.py` | 306-631, (missing) |
| Codelet Execution | STUB | `elements/y_atomic_task.py`, `engine/y_engine.py` | 225, 568-574 |
| Resource RBAC | PARTIAL | `resources/y_resource.py` | 865-917 |
| Composite Tasks | STUB | `elements/y_atomic_task.py`, `engine/y_engine.py` | 292-356, (missing) |
| Persistence | STUB | `persistence/y_serializer.py`, `persistence/y_repository.py` | 1-476, 1-550 |
| Data Binding | STUB | `elements/y_atomic_task.py`, `engine/y_engine.py` | 140-171, 745-791 |
| Case Data | PARTIAL | `engine/y_case.py` | 49-104 |
| Work Item Propagation | PARTIAL | `engine/y_engine.py` | 516-552, 745-791 |

---

## Estimated Implementation Coverage

**Currently Implemented:** ~60-70% of Java YAWL core engine

**Feature Categories:**
- Core Petri net semantics: ✅ Complete
- AND/XOR split and join: ✅ Complete
- Work item state machine (13 states): ✅ Complete
- Basic resourcing (offer/allocate/start/complete): ✅ Complete
- Engine events and listeners: ✅ Complete
- Cancellation sets (reset net): ✅ Complete
- Timer/Deadline data structures: ✅ Complete
- Exception rule matching: ✅ Complete
- Compensation framework: ✅ Complete

**Major Gaps:**
- OR-join semantics: ⚠️ Simplified
- Expression evaluation: ⚠️ Minimal
- Multi-instance execution: ❌ Not wired
- Subprocess decomposition: ❌ Not wired
- Persistence to DB/XML: ❌ In-memory only
- Codelet execution: ❌ Not implemented
- Advanced resourcing: ⚠️ Basic only

---

## Recommended Conversion Order

1. **Data Binding Evaluation** - Blocking for realistic workflows
2. **XPath/XQuery Expressions** - Required by #1 and MI
3. **Multi-Instance Tasks** - Core WCP patterns
4. **Composite Tasks** - Hierarchical workflows
5. **Timer Integration** - SLA compliance
6. **OR-Join Semantics** - Complex synchronization
7. **Codelet Execution** - Automation
8. **Resource RBAC** - Enterprise features
9. **Worklet Service** - Advanced exception handling
10. **Persistence** - Production deployment

Each feature should be implemented with comprehensive tests that verify the ENGINE enforces the pattern, not just that Python code simulates it.
