"""Common temporal properties for workflow verification."""

from __future__ import annotations

from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.temporal.domain.ltl_formula import LTLFormula, LTLOperator
from kgcl.hybrid.temporal.ports.temporal_reasoner_port import TemporalProperty


def task_eventually_completes(task_id: str, workflow_id: str) -> TemporalProperty:
    """Every started task eventually completes (liveness).

    Parameters
    ----------
    task_id : str
        The task ID to verify
    workflow_id : str
        The workflow containing the task

    Returns
    -------
    TemporalProperty
        Property verifying task completion
    """

    def is_task_started(event: WorkflowEvent) -> bool:
        return event.payload.get("task_id") == task_id and event.event_type.name == "TaskStarted"

    def is_task_completed(event: WorkflowEvent) -> bool:
        return event.payload.get("task_id") == task_id and event.event_type.name == "TaskCompleted"

    return TemporalProperty(
        property_id=f"task_complete_{task_id}",
        name="Task Eventually Completes",
        description=f"Task {task_id} must complete after being started",
        formula=LTLFormula(operator=LTLOperator.UNTIL, inner=is_task_started, right=is_task_completed),
        workflow_id=workflow_id,
    )


def approval_precedes_execution(workflow_id: str) -> TemporalProperty:
    """Approval event must precede execution event (SOX compliance).

    Parameters
    ----------
    workflow_id : str
        The workflow to verify

    Returns
    -------
    TemporalProperty
        Property verifying approval precedes execution
    """

    def is_approval(event: WorkflowEvent) -> bool:
        return event.event_type.name == "Approved"

    def is_execution(event: WorkflowEvent) -> bool:
        return event.event_type.name == "Executed"

    def approval_before_execution(event: WorkflowEvent) -> bool:
        return not is_execution(event)

    return TemporalProperty(
        property_id=f"approval_precedes_{workflow_id}",
        name="Approval Precedes Execution",
        description="Approval must occur before execution (SOX compliance)",
        formula=LTLFormula(operator=LTLOperator.UNTIL, inner=approval_before_execution, right=is_approval),
        workflow_id=workflow_id,
    )


def no_concurrent_active_in_mutex(region_id: str, workflow_id: str) -> TemporalProperty:
    """At most one task active at a time in mutex region.

    Parameters
    ----------
    region_id : str
        The mutex region ID
    workflow_id : str
        The workflow to verify

    Returns
    -------
    TemporalProperty
        Property verifying mutex exclusion
    """

    def at_most_one_active(event: WorkflowEvent) -> bool:
        active_count = event.payload.get(f"active_in_{region_id}", 0)
        return bool(active_count <= 1)

    return TemporalProperty(
        property_id=f"mutex_{region_id}",
        name="Mutex Exclusion",
        description=f"At most one task active in mutex region {region_id}",
        formula=LTLFormula(operator=LTLOperator.ALWAYS, inner=at_most_one_active),
        workflow_id=workflow_id,
    )


def status_changes_are_monotonic(workflow_id: str) -> TemporalProperty:
    """Status can only move forward: Pending -> Active -> Completed.

    Parameters
    ----------
    workflow_id : str
        The workflow to verify

    Returns
    -------
    TemporalProperty
        Property verifying monotonic status progression
    """
    status_order = {"Pending": 0, "Active": 1, "Completed": 2}

    def status_is_monotonic(event: WorkflowEvent) -> bool:
        prev_status = event.payload.get("prev_status")
        curr_status = event.payload.get("status")
        if prev_status is None or curr_status is None:
            return True
        prev_order = status_order.get(prev_status, -1)
        curr_order = status_order.get(curr_status, -1)
        return curr_order >= prev_order

    return TemporalProperty(
        property_id=f"monotonic_status_{workflow_id}",
        name="Monotonic Status Transitions",
        description="Status transitions must be monotonically increasing",
        formula=LTLFormula(operator=LTLOperator.ALWAYS, inner=status_is_monotonic),
        workflow_id=workflow_id,
    )


def all_events_have_actor(workflow_id: str) -> TemporalProperty:
    """Every event has a non-empty actor (audit requirement).

    Parameters
    ----------
    workflow_id : str
        The workflow to verify

    Returns
    -------
    TemporalProperty
        Property verifying actor presence
    """

    def has_actor(event: WorkflowEvent) -> bool:
        actor = event.payload.get("actor")
        return actor is not None and actor != ""

    return TemporalProperty(
        property_id=f"actor_present_{workflow_id}",
        name="All Events Have Actor",
        description="Every event must have a non-empty actor (audit requirement)",
        formula=LTLFormula(operator=LTLOperator.ALWAYS, inner=has_actor),
        workflow_id=workflow_id,
    )
