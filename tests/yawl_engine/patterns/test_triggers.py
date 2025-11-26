"""Chicago School TDD tests for YAWL trigger patterns (24-27).

These tests verify observable behavior of trigger patterns using real RDF graphs
and SPARQL queries. No mocking of domain objects.

Test Organization (AAA Pattern)
--------------------------------
- Arrange: Create real Graph, trigger instances, test data
- Act: Call trigger methods with real collaborators
- Assert: Verify observable state changes in graph and results
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.triggers import CancelMIActivity, PersistentTrigger, TransientTrigger

YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")


# ============================================================================
# Pattern 25: Transient Trigger Tests
# ============================================================================


def test_transient_trigger_fires_once_on_condition() -> None:
    """Transient trigger fires exactly once when condition is met."""
    # Arrange
    graph = Graph()
    trigger = TransientTrigger(trigger_condition="count > 10", condition_type="expression")
    task = URIRef("urn:task:threshold")
    context: dict[str, Any] = {"count": 15}

    # Act
    can_fire = trigger.check_trigger(graph, context)
    result, new_trigger = trigger.fire(graph, task, context)

    # Assert
    assert can_fire, "Trigger condition should be met"
    assert result.triggered, "Trigger should have fired"
    assert result.target_task == str(task), "Target task should match"
    assert result.fire_count == 1, "Fire count should be 1"
    assert new_trigger.fired, "New trigger instance should be marked as fired"

    # Verify RDF state
    assert (task, YAWL.triggeredBy, Literal(trigger.name)) in graph
    assert (task, YAWL.triggerType, Literal("transient")) in graph


def test_transient_trigger_deactivates_after_firing() -> None:
    """Transient trigger becomes permanently inactive after first firing."""
    # Arrange
    graph = Graph()
    trigger = TransientTrigger(trigger_condition="count > 10")
    task = URIRef("urn:task:once")
    context: dict[str, Any] = {"count": 15}

    # Act - fire once
    _, fired_trigger = trigger.fire(graph, task, context)

    # Act - try to check condition again
    can_fire_again = fired_trigger.check_trigger(graph, {"count": 20})

    # Assert
    assert not can_fire_again, "Fired trigger should not activate again"
    assert fired_trigger.fired, "Trigger should remain fired"


def test_transient_trigger_rejects_double_fire() -> None:
    """Transient trigger raises error if fired twice."""
    # Arrange
    graph = Graph()
    trigger = TransientTrigger(trigger_condition="count > 10")
    task = URIRef("urn:task:double")
    context: dict[str, Any] = {"count": 15}

    # Act - fire once
    _, fired_trigger = trigger.fire(graph, task, context)

    # Act & Assert - attempt second fire
    with pytest.raises(RuntimeError, match="already fired"):
        fired_trigger.fire(graph, task, context)


def test_transient_trigger_sparql_condition() -> None:
    """Transient trigger evaluates SPARQL ASK queries correctly."""
    # Arrange
    graph = Graph()
    graph.add((URIRef("urn:task:1"), URIRef("urn:prop:status"), Literal("active")))

    trigger = TransientTrigger(
        trigger_condition="""
        ASK { <urn:task:1> <urn:prop:status> "active" }
        """,
        condition_type="sparql",
    )
    task = URIRef("urn:task:trigger")

    # Act
    can_fire = trigger.check_trigger(graph, {})
    result, new_trigger = trigger.fire(graph, task, {})

    # Assert
    assert can_fire, "SPARQL condition should be met"
    assert result.triggered, "Trigger should have fired"
    assert new_trigger.fired, "Trigger should be deactivated"


def test_transient_trigger_condition_not_met() -> None:
    """Transient trigger remains inactive when condition is not met."""
    # Arrange
    graph = Graph()
    trigger = TransientTrigger(trigger_condition="count > 100")
    context: dict[str, Any] = {"count": 50}

    # Act
    can_fire = trigger.check_trigger(graph, context)

    # Assert
    assert not can_fire, "Trigger should not activate when condition fails"
    assert not trigger.fired, "Trigger should remain unfired"


# ============================================================================
# Pattern 26: Persistent Trigger Tests
# ============================================================================


def test_persistent_trigger_fires_multiple_times() -> None:
    """Persistent trigger fires on every event that meets condition."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="temperature > 100")

    events = [
        {"temperature": 95},  # No fire
        {"temperature": 105},  # Fire 1
        {"temperature": 110},  # Fire 2
        {"temperature": 90},  # No fire
        {"temperature": 120},  # Fire 3
    ]

    fire_count = 0

    # Act
    for event in events:
        result, trigger = trigger.on_event(graph, event)
        if result.triggered:
            fire_count += 1

    # Assert
    assert fire_count == 3, "Should have fired 3 times"
    assert trigger.fire_count == 3, "Trigger state should track fire count"


def test_persistent_trigger_remains_enabled() -> None:
    """Persistent trigger remains enabled after firing."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="value > 50")

    # Act - fire multiple times
    result1, trigger = trigger.on_event(graph, {"value": 60})
    result2, trigger = trigger.on_event(graph, {"value": 70})
    result3, trigger = trigger.on_event(graph, {"value": 80})

    # Assert
    assert result1.triggered and result2.triggered and result3.triggered
    assert trigger.enabled, "Trigger should remain enabled"
    assert trigger.fire_count == 3, "Should track all firings"


def test_persistent_trigger_can_be_disabled() -> None:
    """Persistent trigger can be disabled to stop firing."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="count > 10")

    # Act - fire once, then disable
    result1, trigger = trigger.on_event(graph, {"count": 15})
    disabled = trigger.disable()
    result2, disabled = disabled.on_event(graph, {"count": 20})

    # Assert
    assert result1.triggered, "Should fire when enabled"
    assert not result2.triggered, "Should not fire when disabled"
    assert not disabled.enabled, "Trigger should be disabled"
    assert disabled.fire_count == 1, "Fire count should not increase when disabled"


def test_persistent_trigger_can_be_reenabled() -> None:
    """Persistent trigger can be re-enabled after disabling."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="count > 10")

    # Act - disable, then re-enable
    disabled = trigger.disable()
    result1, disabled = disabled.on_event(graph, {"count": 15})
    reenabled = disabled.enable()
    result2, reenabled = reenabled.on_event(graph, {"count": 20})

    # Assert
    assert not result1.triggered, "Should not fire when disabled"
    assert result2.triggered, "Should fire when re-enabled"
    assert reenabled.enabled, "Trigger should be enabled"
    assert reenabled.fire_count == 1, "Should increment count after re-enable"


def test_persistent_trigger_sparql_evaluation() -> None:
    """Persistent trigger evaluates SPARQL conditions correctly."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(
        trigger_condition="""
        ASK { <urn:sensor:temp> <urn:prop:value> ?v
              FILTER (?v > 100) }
        """,
        condition_type="sparql",
    )

    # Act - add data that meets condition
    graph.add((URIRef("urn:sensor:temp"), URIRef("urn:prop:value"), Literal(105)))
    result, trigger = trigger.on_event(graph, {})

    # Assert
    assert result.triggered, "SPARQL condition should trigger"
    assert trigger.fire_count == 1


def test_persistent_trigger_tracks_fire_count() -> None:
    """Persistent trigger maintains accurate fire count across events."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="count > 10")

    events = [{"count": i} for i in range(5, 25, 2)]  # 5, 7, 9, 11, 13, ..., 23

    # Act
    for event in events:
        _, trigger = trigger.on_event(graph, event)

    # Assert
    # Events with count > 10: 11, 13, 15, 17, 19, 21, 23 = 7 events
    assert trigger.fire_count == 7, "Should track all firings"


# ============================================================================
# Pattern 27: Cancel MI Activity Tests
# ============================================================================


def test_cancel_mi_activity_cancels_all_instances() -> None:
    """Cancel MI activity marks all instances as cancelled."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:parallel")
    instances = [URIRef("urn:task:mi:parallel:1"), URIRef("urn:task:mi:parallel:2"), URIRef("urn:task:mi:parallel:3")]

    # Add MI instances to graph
    for instance in instances:
        graph.add((instance, YAWL.instanceOf, mi_task))
        graph.add((instance, YAWL.status, Literal("running")))

    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 3, "Should cancel all 3 instances"
    assert result.failed_count == 0, "No failures expected"
    assert len(result.cancelled_instances) == 3

    # Verify RDF state
    for instance in instances:
        assert (instance, YAWL.status, Literal("cancelled")) in graph, f"Instance {instance} should be cancelled"

    assert (mi_task, YAWL.status, Literal("cancelled")) in graph


def test_cancel_mi_activity_skips_already_cancelled() -> None:
    """Cancel MI activity skips instances already cancelled."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:mixed")

    # Add instances: some running, some already cancelled
    running = URIRef("urn:task:mi:mixed:1")
    graph.add((running, YAWL.instanceOf, mi_task))
    graph.add((running, YAWL.status, Literal("running")))

    already_cancelled = URIRef("urn:task:mi:mixed:2")
    graph.add((already_cancelled, YAWL.instanceOf, mi_task))
    graph.add((already_cancelled, YAWL.status, Literal("cancelled")))

    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 1, "Should only cancel the running instance"
    assert result.failed_count == 0


def test_cancel_mi_activity_handles_empty_instances() -> None:
    """Cancel MI activity handles case with no instances gracefully."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:empty")
    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 0, "No instances to cancel"
    assert result.failed_count == 0
    assert len(result.cancelled_instances) == 0

    # MI task itself should still be marked cancelled
    assert (mi_task, YAWL.status, Literal("cancelled")) in graph


def test_cancel_mi_activity_records_timestamp() -> None:
    """Cancel MI activity records cancellation timestamp."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:time")
    instance = URIRef("urn:task:mi:time:1")
    graph.add((instance, YAWL.instanceOf, mi_task))

    cancel = CancelMIActivity()
    before = time.time()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)
    after = time.time()

    # Assert
    assert before <= result.timestamp <= after, "Timestamp should be in valid range"

    # Verify timestamp in graph
    timestamps = list(graph.objects(instance, YAWL.cancelledAt))
    assert len(timestamps) > 0, "Should have cancellation timestamp"


def test_cancel_mi_activity_preserves_metadata() -> None:
    """Cancel MI activity adds cancellation reason to graph."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:meta")
    instance = URIRef("urn:task:mi:meta:1")
    graph.add((instance, YAWL.instanceOf, mi_task))

    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 1

    # Verify cancellation reason
    reasons = list(graph.objects(instance, YAWL.cancellationReason))
    assert len(reasons) > 0, "Should have cancellation reason"
    assert str(reasons[0]) == "mi_cancellation"


# ============================================================================
# Integration Tests (Cross-Pattern Behavior)
# ============================================================================


def test_transient_and_persistent_triggers_coexist() -> None:
    """Transient and persistent triggers can operate independently."""
    # Arrange
    graph = Graph()
    transient = TransientTrigger(trigger_condition="count == 10")
    persistent = PersistentTrigger(trigger_condition="count > 5")

    events = [{"count": i} for i in [3, 6, 10, 15, 20]]

    # Act
    for event in events:
        if transient.check_trigger(graph, event):
            _, transient = transient.fire(graph, URIRef("urn:task:transient"), event)
        _, persistent = persistent.on_event(graph, event)

    # Assert
    assert transient.fired, "Transient should have fired on count=10"
    assert persistent.fire_count == 4, "Persistent should fire on 6,10,15,20"


def test_cancel_mi_activity_with_trigger_fired_instances() -> None:
    """Cancel MI activity cancels instances that have trigger state."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:trigger")
    instance = URIRef("urn:task:mi:trigger:1")

    graph.add((instance, YAWL.instanceOf, mi_task))
    graph.add((instance, YAWL.triggeredBy, Literal("TransientTrigger")))

    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 1
    assert (instance, YAWL.status, Literal("cancelled")) in graph
    # Trigger state should be preserved
    assert (instance, YAWL.triggeredBy, Literal("TransientTrigger")) in graph


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_transient_trigger_invalid_expression_returns_false() -> None:
    """Transient trigger returns False on invalid expression."""
    # Arrange
    graph = Graph()
    trigger = TransientTrigger(trigger_condition="invalid python syntax +++")

    # Act
    can_fire = trigger.check_trigger(graph, {})

    # Assert
    assert not can_fire, "Invalid expression should not trigger"


def test_persistent_trigger_handles_evaluation_errors() -> None:
    """Persistent trigger handles errors gracefully without crashing."""
    # Arrange
    graph = Graph()
    trigger = PersistentTrigger(trigger_condition="undefined_var > 10")

    # Act
    result, trigger = trigger.on_event(graph, {})

    # Assert
    assert not result.triggered, "Error should prevent triggering"
    assert "error" in result.metadata, "Should include error metadata"
    assert trigger.fire_count == 0, "Error should not increment count"


def test_cancel_mi_activity_handles_malformed_graph() -> None:
    """Cancel MI activity handles malformed RDF data gracefully."""
    # Arrange
    graph = Graph()
    mi_task = URIRef("urn:task:mi:malformed")
    # Don't add any instanceOf triples

    cancel = CancelMIActivity()

    # Act
    result = cancel.cancel_all_instances(graph, mi_task)

    # Assert
    assert result.cancelled_count == 0, "Should handle empty query result"
    assert result.failed_count == 0
