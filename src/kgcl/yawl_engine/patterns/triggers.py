"""YAWL Trigger Patterns Implementation (Patterns 24-27).

This module implements event-driven workflow patterns from the YAWL specification:

Pattern 24: Implicit Termination (Persistent Trigger)
    Workflow terminates when no more tasks can be executed.

Pattern 25: Transient Trigger
    One-shot trigger that fires once on condition, then deactivates.

Pattern 26: Persistent Trigger
    Trigger remains active and fires every time condition is met.

Pattern 27: Cancel Multiple Instance Activity
    Cancel all spawned instances of a multi-instance task.

Examples
--------
>>> from rdflib import Graph
>>> graph = Graph()
>>> trigger = TransientTrigger(trigger_condition="ASK { ?s ?p ?o }")
>>> result = trigger.check_trigger(graph, {"count": 5})
>>> if result:
...     fired_result = trigger.fire(graph, URIRef("urn:task:1"), {})
...     assert fired_result.triggered

>>> persistent = PersistentTrigger(trigger_condition="count > 10")
>>> for event in events:
...     result = persistent.on_event(graph, event)
...     if result.triggered:
...         print(f"Fired {persistent.fire_count} times")

>>> cancel = CancelMIActivity()
>>> result = cancel.cancel_all_instances(graph, URIRef("urn:task:mi"))
>>> assert result.cancelled_count > 0
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef

logger = logging.getLogger(__name__)

# YAWL namespace
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")


@dataclass(frozen=True)
class TriggerResult:
    """Result of trigger evaluation and firing.

    Parameters
    ----------
    triggered : bool
        Whether the trigger condition was met and fired
    target_task : str | None
        Task URI that was triggered (None if not triggered)
    timestamp : float
        Unix timestamp when trigger was evaluated
    fire_count : int
        Number of times this trigger has fired (for persistent triggers)
    metadata : dict[str, Any]
        Additional metadata about trigger execution

    Examples
    --------
    >>> result = TriggerResult(
    ...     triggered=True,
    ...     target_task="urn:task:1",
    ...     timestamp=time.time(),
    ...     fire_count=1,
    ...     metadata={"reason": "threshold_exceeded"},
    ... )
    >>> assert result.triggered
    >>> assert result.target_task == "urn:task:1"
    """

    triggered: bool
    target_task: str | None
    timestamp: float
    fire_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CancellationResult:
    """Result of multi-instance task cancellation.

    Parameters
    ----------
    cancelled_count : int
        Number of instances successfully cancelled
    failed_count : int
        Number of instances that failed to cancel
    cancelled_instances : list[str]
        URIs of cancelled task instances
    errors : list[str]
        Error messages for failed cancellations
    timestamp : float
        Unix timestamp when cancellation occurred

    Examples
    --------
    >>> result = CancellationResult(
    ...     cancelled_count=5,
    ...     failed_count=0,
    ...     cancelled_instances=["urn:task:mi:1", "urn:task:mi:2"],
    ...     errors=[],
    ...     timestamp=time.time(),
    ... )
    >>> assert result.cancelled_count == 5
    >>> assert result.failed_count == 0
    """

    cancelled_count: int
    failed_count: int
    cancelled_instances: list[str]
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class TransientTrigger:
    """Pattern 25: Transient Trigger (one-shot event).

    A transient trigger fires exactly once when its condition is met,
    then deactivates permanently. Subsequent condition matches are ignored.

    Use Cases
    ---------
    - Emergency stop buttons (single activation)
    - One-time deadline triggers
    - Single-shot notifications
    - Fail-once conditions (e.g., security breach)

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (25)
    name : str
        Human-readable pattern name
    trigger_condition : str
        SPARQL ASK query or Python expression to evaluate
    fired : bool
        Whether this trigger has already fired (immutable state)
    condition_type : str
        Type of condition ("sparql" or "expression")

    Examples
    --------
    >>> from rdflib import Graph
    >>> graph = Graph()
    >>> trigger = TransientTrigger(trigger_condition="ASK { ?s ?p ?o }")
    >>> result = trigger.check_trigger(graph, {"count": 5})
    >>> if result:
    ...     fired = trigger.fire(graph, URIRef("urn:task:1"), {})
    ...     assert fired.triggered
    ...     assert not trigger.check_trigger(graph, {"count": 10})  # Deactivated
    """

    pattern_id: int = 25
    name: str = "Transient Trigger"
    trigger_condition: str = ""
    fired: bool = False
    condition_type: str = "expression"  # "sparql" or "expression"

    def check_trigger(self, graph: Graph, context: dict[str, Any]) -> bool:
        """Check if trigger condition is met and trigger is still active.

        Parameters
        ----------
        graph : Graph
            RDF graph for SPARQL evaluation
        context : dict[str, Any]
            Workflow variables for expression evaluation

        Returns
        -------
        bool
            True if condition met and not yet fired, False otherwise

        Examples
        --------
        >>> graph = Graph()
        >>> trigger = TransientTrigger(trigger_condition="count > 10", condition_type="expression")
        >>> assert trigger.check_trigger(graph, {"count": 15})
        >>> assert not trigger.check_trigger(graph, {"count": 5})
        """
        if self.fired:
            return False  # Already fired - deactivated

        try:
            if self.condition_type == "sparql":
                # SPARQL ASK query
                result = graph.query(self.trigger_condition)
                return bool(result.askAnswer) if hasattr(result, "askAnswer") else False

            # Python expression evaluation
            return bool(eval(self.trigger_condition, {"__builtins__": {}}, context))

        except Exception as e:
            logger.exception(
                "Trigger condition evaluation failed",
                extra={"pattern": self.name, "condition": self.trigger_condition, "error": str(e)},
            )
            return False

    def fire(self, graph: Graph, task: URIRef, context: dict[str, Any]) -> tuple[TriggerResult, TransientTrigger]:
        """Fire the trigger and deactivate permanently.

        Parameters
        ----------
        graph : Graph
            RDF graph to update with trigger state
        task : URIRef
            Task URI to trigger
        context : dict[str, Any]
            Workflow execution context

        Returns
        -------
        tuple[TriggerResult, TransientTrigger]
            Result of trigger firing and updated trigger instance

        Raises
        ------
        RuntimeError
            If trigger has already been fired

        Examples
        --------
        >>> graph = Graph()
        >>> trigger = TransientTrigger(trigger_condition="count > 10")
        >>> result, new_trigger = trigger.fire(graph, URIRef("urn:task:1"), {"count": 15})
        >>> assert result.triggered
        >>> assert new_trigger.fired
        """
        if self.fired:
            msg = f"Transient trigger {self.name} already fired"
            raise RuntimeError(msg)

        timestamp = time.time()

        # Mark trigger as fired in RDF graph
        graph.add((task, YAWL.triggeredBy, Literal(self.name)))
        graph.add((task, YAWL.triggerTimestamp, Literal(timestamp)))
        graph.add((task, YAWL.triggerType, Literal("transient")))

        logger.info("Transient trigger fired", extra={"pattern": self.name, "task": str(task), "timestamp": timestamp})

        result = TriggerResult(
            triggered=True,
            target_task=str(task),
            timestamp=timestamp,
            fire_count=1,
            metadata={"trigger_type": "transient", "deactivated": True},
        )

        # Create new immutable instance with fired=True
        new_trigger = replace(self, fired=True)

        return result, new_trigger


@dataclass(frozen=True)
class PersistentTrigger:
    """Pattern 26: Persistent Trigger (recurring event).

    A persistent trigger remains active indefinitely and fires every time
    its condition is met. Used for continuous monitoring and event streams.

    Use Cases
    ---------
    - Continuous health monitoring
    - Stream processing (fire on each event)
    - Recurring alarms (threshold violations)
    - Event-driven workflows (message queues)

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (26)
    name : str
        Human-readable pattern name
    trigger_condition : str
        SPARQL ASK query or Python expression
    fire_count : int
        Total number of times trigger has fired
    condition_type : str
        Type of condition ("sparql" or "expression")
    enabled : bool
        Whether trigger is currently enabled

    Examples
    --------
    >>> graph = Graph()
    >>> trigger = PersistentTrigger(trigger_condition="temperature > 100")
    >>> for temp in [95, 105, 110, 90, 120]:
    ...     result, trigger = trigger.on_event(graph, {"temperature": temp})
    ...     if result.triggered:
    ...         print(f"Alarm! Temp={temp}, Count={trigger.fire_count}")
    """

    pattern_id: int = 26
    name: str = "Persistent Trigger"
    trigger_condition: str = ""
    fire_count: int = 0
    condition_type: str = "expression"
    enabled: bool = True

    def on_event(self, graph: Graph, event: dict[str, Any]) -> tuple[TriggerResult, PersistentTrigger]:
        """Evaluate trigger on incoming event.

        Parameters
        ----------
        graph : Graph
            RDF graph for SPARQL evaluation
        event : dict[str, Any]
            Event data to evaluate against condition

        Returns
        -------
        tuple[TriggerResult, PersistentTrigger]
            Result of evaluation and updated trigger instance

        Examples
        --------
        >>> graph = Graph()
        >>> trigger = PersistentTrigger(trigger_condition="count > 10")
        >>> result, trigger = trigger.on_event(graph, {"count": 15})
        >>> assert result.triggered
        >>> assert trigger.fire_count == 1
        >>> result2, trigger = trigger.on_event(graph, {"count": 20})
        >>> assert trigger.fire_count == 2
        """
        if not self.enabled:
            return (
                TriggerResult(
                    triggered=False,
                    target_task=None,
                    timestamp=time.time(),
                    fire_count=self.fire_count,
                    metadata={"reason": "trigger_disabled"},
                ),
                self,
            )

        try:
            triggered = False
            if self.condition_type == "sparql":
                result = graph.query(self.trigger_condition)
                triggered = bool(result.askAnswer) if hasattr(result, "askAnswer") else False
            else:
                triggered = bool(eval(self.trigger_condition, {"__builtins__": {}}, event))

            if not triggered:
                not_triggered_result = TriggerResult(
                    triggered=False,
                    target_task=None,
                    timestamp=time.time(),
                    fire_count=self.fire_count,
                    metadata={"reason": "condition_not_met"},
                )
                return not_triggered_result, self

            # Trigger fired - increment count
            new_count = self.fire_count + 1
            timestamp = time.time()

            logger.info(
                "Persistent trigger fired",
                extra={"pattern": self.name, "fire_count": new_count, "timestamp": timestamp},
            )

            triggered_result = TriggerResult(
                triggered=True,
                target_task=event.get("target_task"),
                timestamp=timestamp,
                fire_count=new_count,
                metadata={"trigger_type": "persistent", "event": event},
            )

            # Create new instance with incremented count
            new_trigger = replace(self, fire_count=new_count)

            return triggered_result, new_trigger

        except Exception as e:
            logger.exception("Persistent trigger evaluation failed", extra={"pattern": self.name, "error": str(e)})
            error_result = TriggerResult(
                triggered=False,
                target_task=None,
                timestamp=time.time(),
                fire_count=self.fire_count,
                metadata={"reason": "error", "error": str(e)},
            )
            return error_result, self

    def disable(self) -> PersistentTrigger:
        """Disable the trigger (stops firing on events).

        Returns
        -------
        PersistentTrigger
            New trigger instance with enabled=False

        Examples
        --------
        >>> trigger = PersistentTrigger(trigger_condition="count > 10")
        >>> disabled = trigger.disable()
        >>> assert not disabled.enabled
        """
        return replace(self, enabled=False)

    def enable(self) -> PersistentTrigger:
        """Enable the trigger (resumes firing on events).

        Returns
        -------
        PersistentTrigger
            New trigger instance with enabled=True

        Examples
        --------
        >>> trigger = PersistentTrigger(enabled=False)
        >>> enabled = trigger.enable()
        >>> assert enabled.enabled
        """
        return replace(self, enabled=True)


@dataclass(frozen=True)
class CancelMIActivity:
    """Pattern 27: Cancel Multiple Instance Activity.

    Cancels all spawned instances of a multi-instance task, terminating
    parallel execution immediately. Used for emergency stops, timeouts,
    and workflow cancellations.

    Use Cases
    ---------
    - Emergency stop (kill all parallel workers)
    - Timeout cancellation (abort long-running instances)
    - Resource cleanup (terminate all child processes)
    - Workflow rollback (cancel distributed transaction)

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (27)
    name : str
        Human-readable pattern name

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> # ... create MI task with instances ...
    >>> cancel = CancelMIActivity()
    >>> result = cancel.cancel_all_instances(graph, URIRef("urn:task:mi"))
    >>> assert result.cancelled_count > 0
    """

    pattern_id: int = 27
    name: str = "Cancel Multiple Instance Activity"

    def cancel_all_instances(self, graph: Graph, mi_task: URIRef) -> CancellationResult:
        """Cancel all instances of a multi-instance task.

        Parameters
        ----------
        graph : Graph
            RDF graph containing task instances
        mi_task : URIRef
            URI of the multi-instance task to cancel

        Returns
        -------
        CancellationResult
            Summary of cancellation operation with counts and errors

        Examples
        --------
        >>> graph = Graph()
        >>> # Add MI task instances
        >>> graph.add((URIRef("urn:task:mi:1"), YAWL.instanceOf, mi_task))
        >>> graph.add((URIRef("urn:task:mi:2"), YAWL.instanceOf, mi_task))
        >>> cancel = CancelMIActivity()
        >>> result = cancel.cancel_all_instances(graph, mi_task)
        >>> assert result.cancelled_count == 2
        """
        cancelled: list[str] = []
        errors: list[str] = []
        timestamp = time.time()

        try:
            # SPARQL query to find all instances
            query = f"""
            PREFIX yawl: <{YAWL}>
            SELECT ?instance WHERE {{
                ?instance yawl:instanceOf <{mi_task}> .
                OPTIONAL {{ ?instance yawl:status ?status }}
                FILTER (!bound(?status) || ?status != "cancelled")
            }}
            """

            results = graph.query(query)

            for row in results:
                if not hasattr(row, "instance"):
                    continue

                instance = row.instance  # type: ignore[union-attr]
                try:
                    # Mark instance as cancelled
                    graph.add((instance, YAWL.status, Literal("cancelled")))
                    graph.add((instance, YAWL.cancelledAt, Literal(timestamp)))
                    graph.add((instance, YAWL.cancellationReason, Literal("mi_cancellation")))

                    cancelled.append(str(instance))

                    logger.info(
                        "MI instance cancelled",
                        extra={"pattern": self.name, "mi_task": str(mi_task), "instance": str(instance)},
                    )

                except Exception as e:
                    error_msg = f"Failed to cancel {instance}: {e}"
                    errors.append(error_msg)
                    logger.exception(
                        "MI instance cancellation failed", extra={"instance": str(instance), "error": str(e)}
                    )

            # Mark MI task itself as cancelled
            graph.add((mi_task, YAWL.status, Literal("cancelled")))
            graph.add((mi_task, YAWL.cancelledAt, Literal(timestamp)))

            logger.info(
                "MI activity cancelled",
                extra={
                    "pattern": self.name,
                    "mi_task": str(mi_task),
                    "cancelled_count": len(cancelled),
                    "failed_count": len(errors),
                },
            )

            return CancellationResult(
                cancelled_count=len(cancelled),
                failed_count=len(errors),
                cancelled_instances=cancelled,
                errors=errors,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.exception("MI cancellation failed", extra={"mi_task": str(mi_task), "error": str(e)})
            return CancellationResult(
                cancelled_count=0,
                failed_count=1,
                cancelled_instances=[],
                errors=[f"MI cancellation failed: {e}"],
                timestamp=timestamp,
            )
