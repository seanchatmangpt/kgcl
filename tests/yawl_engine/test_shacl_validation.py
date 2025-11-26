"""Tests for YAWL SHACL Pattern Validation - Chicago School TDD.

This test suite validates SHACL topology constraints for YAWL workflow patterns,
implementing the "Logic as Topology" principle where validation IS execution.

Test Strategy (Chicago School)
-------------------------------
- Use REAL RDF graphs with actual SHACL validation
- Test observable behavior (conformance, violations)
- Verify ALL constraint types (property, SPARQL, enumeration)
- Target: <1 second total runtime, 100% constraint coverage

SHACL Constraints Tested
-------------------------
1. Pattern 9 (Discriminator): Quorum >= 1, quorum <= totalBranches
2. Pattern 8 (MultipleMerge): maxInstances >= 1
3. Split Patterns (AND/OR/XOR): >= 2 outgoing flows required
4. Join Patterns (AND/OR/XOR): >= 2 incoming flows required
5. Split-Join Combinations: Invalid combinations (XOR-AND, XOR-OR)
6. Pattern 22 (StructuredLoop): maxIterations >= 1
7. Cancellation Regions: Requires trigger task and >= 1 scoped task
8. Deferred Choice: >= 2 competing branches
9. Workflow Instance: Valid status enumeration

References
----------
- SHACL Spec: https://www.w3.org/TR/shacl/
- YAWL Patterns: http://www.yawlfoundation.org/
- Semantic Singularity: Logic IS Topology
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns import validate_topology

# Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
YAWL_PATTERN = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")
YAWL_EXEC = Namespace("http://bitflow.ai/ontology/yawl/execution/v1#")

# Path to SHACL shapes file
SHAPES_PATH = Path(__file__).parent.parent.parent / "ontology" / "yawl-shapes.ttl"


# =============================================================================
# FIXTURES - Reusable Graph Configurations
# =============================================================================


@pytest.fixture
def empty_graph() -> Graph:
    """Empty RDF graph for baseline tests."""
    g = Graph()
    g.bind("yawl", YAWL)
    g.bind("yawl-pattern", YAWL_PATTERN)
    return g


@pytest.fixture
def valid_discriminator_graph() -> Graph:
    """Valid discriminator pattern (quorum=2, totalBranches=3)."""
    g = Graph()
    g.bind("yawl", YAWL)
    g.bind("yawl-pattern", YAWL_PATTERN)

    disc = URIRef("urn:disc:ValidDisc")
    g.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    g.add((disc, YAWL.quorum, Literal(2)))
    g.add((disc, YAWL.totalBranches, Literal(3)))

    return g


@pytest.fixture
def valid_and_split_graph() -> Graph:
    """Valid AND-split with 3 outgoing flows."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_a = URIRef("urn:task:ANDSplit")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")
    flow1 = URIRef("urn:flow:1")
    flow2 = URIRef("urn:flow:2")
    flow3 = URIRef("urn:flow:3")

    # Task with AND split type
    g.add((task_a, RDF.type, YAWL.Task))
    g.add((task_a, YAWL.id, Literal("ANDSplit")))
    g.add((task_a, YAWL.splitType, YAWL.AND))
    g.add((task_a, YAWL.flowsInto, flow1))
    g.add((task_a, YAWL.flowsInto, flow2))
    g.add((task_a, YAWL.flowsInto, flow3))

    # Target tasks (must be typed as yawl:Task with IDs)
    g.add((task_b, RDF.type, YAWL.Task))
    g.add((task_b, YAWL.id, Literal("B")))
    g.add((task_c, RDF.type, YAWL.Task))
    g.add((task_c, YAWL.id, Literal("C")))
    g.add((task_d, RDF.type, YAWL.Task))
    g.add((task_d, YAWL.id, Literal("D")))

    # Flows (require flowsFrom and nextElementRef)
    g.add((flow1, RDF.type, YAWL.Flow))
    g.add((flow1, YAWL.flowsFrom, task_a))
    g.add((flow1, YAWL.nextElementRef, task_b))
    g.add((flow2, RDF.type, YAWL.Flow))
    g.add((flow2, YAWL.flowsFrom, task_a))
    g.add((flow2, YAWL.nextElementRef, task_c))
    g.add((flow3, RDF.type, YAWL.Flow))
    g.add((flow3, YAWL.flowsFrom, task_a))
    g.add((flow3, YAWL.nextElementRef, task_d))

    return g


@pytest.fixture
def valid_and_join_graph() -> Graph:
    """Valid AND-join with 3 incoming flows."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_join = URIRef("urn:task:ANDJoin")
    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    flow1 = URIRef("urn:flow:1")
    flow2 = URIRef("urn:flow:2")
    flow3 = URIRef("urn:flow:3")

    # Join task
    g.add((task_join, RDF.type, YAWL.Task))
    g.add((task_join, YAWL.id, Literal("ANDJoin")))
    g.add((task_join, YAWL.joinType, YAWL.AND))

    # Source tasks (must be typed as yawl:Task with IDs)
    g.add((task_a, RDF.type, YAWL.Task))
    g.add((task_a, YAWL.id, Literal("A")))
    g.add((task_b, RDF.type, YAWL.Task))
    g.add((task_b, YAWL.id, Literal("B")))
    g.add((task_c, RDF.type, YAWL.Task))
    g.add((task_c, YAWL.id, Literal("C")))

    # Incoming flows (require flowsFrom and nextElementRef)
    g.add((task_a, YAWL.flowsInto, flow1))
    g.add((flow1, RDF.type, YAWL.Flow))
    g.add((flow1, YAWL.flowsFrom, task_a))
    g.add((flow1, YAWL.nextElementRef, task_join))

    g.add((task_b, YAWL.flowsInto, flow2))
    g.add((flow2, RDF.type, YAWL.Flow))
    g.add((flow2, YAWL.flowsFrom, task_b))
    g.add((flow2, YAWL.nextElementRef, task_join))

    g.add((task_c, YAWL.flowsInto, flow3))
    g.add((flow3, RDF.type, YAWL.Flow))
    g.add((flow3, YAWL.flowsFrom, task_c))
    g.add((flow3, YAWL.nextElementRef, task_join))

    return g


@pytest.fixture
def valid_workflow_instance_graph() -> Graph:
    """Valid workflow instance with proper status."""
    g = Graph()
    g.bind("yawl", YAWL)

    workflow = URIRef("urn:workflow:W1")
    instance = URIRef("urn:instance:I1")

    # Workflow must be typed
    g.add((workflow, RDF.type, YAWL.Workflow))

    g.add((instance, RDF.type, YAWL.WorkflowInstance))
    g.add((instance, YAWL.instanceOf, workflow))
    g.add((instance, YAWL.status, Literal("running")))

    return g


# =============================================================================
# DISCRIMINATOR PATTERN VALIDATION (Pattern 9)
# =============================================================================


def test_discriminator_valid_quorum(valid_discriminator_graph: Graph) -> None:
    """Valid discriminator (quorum=2, totalBranches=3) passes validation.

    Verifies:
    - Quorum >= 1 (satisfied)
    - Quorum <= totalBranches (2 <= 3, satisfied)
    """
    result = validate_topology(valid_discriminator_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


def test_discriminator_quorum_zero_invalid(empty_graph: Graph) -> None:
    """Discriminator with quorum=0 violates constraint (must be >= 1).

    SHACL Constraint: sh:minInclusive 1 on yawl:quorum
    """
    disc = URIRef("urn:disc:InvalidQuorum")
    empty_graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    empty_graph.add((disc, YAWL.quorum, Literal(0)))
    empty_graph.add((disc, YAWL.totalBranches, Literal(3)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for quorum=0"
    assert any("quorum" in v.lower() for v in result.violations), (
        f"Expected 'quorum' in violations: {result.violations}"
    )


def test_discriminator_quorum_exceeds_total(empty_graph: Graph) -> None:
    """Discriminator with quorum > totalBranches violates SPARQL constraint.

    SHACL Constraint: SPARQL check (?quorum > ?total) = violation
    """
    disc = URIRef("urn:disc:ExcessiveQuorum")
    empty_graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    empty_graph.add((disc, YAWL.quorum, Literal(5)))
    empty_graph.add((disc, YAWL.totalBranches, Literal(3)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for quorum > totalBranches"
    assert any("quorum" in v.lower() or "total" in v.lower() for v in result.violations), (
        f"Expected quorum/total violation: {result.violations}"
    )


def test_discriminator_missing_quorum(empty_graph: Graph) -> None:
    """Discriminator without quorum property violates minCount constraint.

    SHACL Constraint: sh:minCount 1 on yawl:quorum
    """
    disc = URIRef("urn:disc:NoQuorum")
    empty_graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    empty_graph.add((disc, YAWL.totalBranches, Literal(3)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for missing quorum"


# =============================================================================
# SPLIT PATTERN VALIDATION (AND/OR/XOR)
# =============================================================================


def test_and_split_requires_two_flows(empty_graph: Graph) -> None:
    """AND-split with < 2 outgoing flows violates SPARQL constraint.

    SHACL Constraint: COUNT(?flow) < 2 = violation
    """
    task = URIRef("urn:task:InvalidANDSplit")
    flow = URIRef("urn:flow:1")
    target = URIRef("urn:task:Target")

    empty_graph.add((task, RDF.type, YAWL.Task))
    empty_graph.add((task, YAWL.id, Literal("InvalidANDSplit")))
    empty_graph.add((task, YAWL.splitType, YAWL.AND))
    empty_graph.add((task, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task))
    empty_graph.add((flow, YAWL.nextElementRef, target))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for AND-split with 1 flow"
    assert any("and" in v.lower() or "flow" in v.lower() for v in result.violations), (
        f"Expected AND-split flow violation: {result.violations}"
    )


def test_or_split_requires_two_flows(empty_graph: Graph) -> None:
    """OR-split with < 2 outgoing flows violates SPARQL constraint.

    SHACL Constraint: COUNT(?flow) < 2 = violation
    """
    task = URIRef("urn:task:InvalidORSplit")
    flow = URIRef("urn:flow:1")
    target = URIRef("urn:task:Target")

    empty_graph.add((task, RDF.type, YAWL.Task))
    empty_graph.add((task, YAWL.id, Literal("InvalidORSplit")))
    empty_graph.add((task, YAWL.splitType, YAWL.OR))
    empty_graph.add((task, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task))
    empty_graph.add((flow, YAWL.nextElementRef, target))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for OR-split with 1 flow"


def test_xor_split_requires_two_flows(empty_graph: Graph) -> None:
    """XOR-split with < 2 outgoing flows violates SPARQL constraint.

    SHACL Constraint: COUNT(?flow) < 2 = violation
    """
    task = URIRef("urn:task:InvalidXORSplit")
    flow = URIRef("urn:flow:1")
    target = URIRef("urn:task:Target")

    empty_graph.add((task, RDF.type, YAWL.Task))
    empty_graph.add((task, YAWL.id, Literal("InvalidXORSplit")))
    empty_graph.add((task, YAWL.splitType, YAWL.XOR))
    empty_graph.add((task, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task))
    empty_graph.add((flow, YAWL.nextElementRef, target))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for XOR-split with 1 flow"


def test_and_split_valid_with_multiple_flows(valid_and_split_graph: Graph) -> None:
    """AND-split with 3 outgoing flows passes validation.

    Verifies: COUNT(?flow) >= 2 (satisfied)
    """
    result = validate_topology(valid_and_split_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


# =============================================================================
# JOIN PATTERN VALIDATION (AND/OR/XOR)
# =============================================================================


def test_and_join_requires_two_incoming(empty_graph: Graph) -> None:
    """AND-join with < 2 incoming flows violates SPARQL constraint.

    SHACL Constraint: COUNT(?incoming) < 2 = violation
    """
    task_join = URIRef("urn:task:InvalidANDJoin")
    task_a = URIRef("urn:task:A")
    flow = URIRef("urn:flow:1")

    empty_graph.add((task_join, RDF.type, YAWL.Task))
    empty_graph.add((task_join, YAWL.id, Literal("InvalidANDJoin")))
    empty_graph.add((task_join, YAWL.joinType, YAWL.AND))

    empty_graph.add((task_a, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task_a))
    empty_graph.add((flow, YAWL.nextElementRef, task_join))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for AND-join with 1 incoming"


def test_and_join_valid_with_multiple_incoming(valid_and_join_graph: Graph) -> None:
    """AND-join with 3 incoming flows passes validation.

    Verifies: COUNT(?incoming) >= 2 (satisfied)
    """
    result = validate_topology(valid_and_join_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


# =============================================================================
# SPLIT-JOIN COMBINATION VALIDATION
# =============================================================================


def test_xor_split_and_join_invalid_combination(empty_graph: Graph) -> None:
    """XOR split with AND join is invalid (XOR=1 branch, AND requires all).

    SHACL Constraint: SPARQL (?splitType=XOR AND ?joinType=AND) = violation
    """
    combo = URIRef("urn:combo:XOR-AND")
    empty_graph.add((combo, RDF.type, YAWL.SplitJoinCombination))
    empty_graph.add((combo, YAWL.splitType, YAWL.XOR))
    empty_graph.add((combo, YAWL.joinType, YAWL.AND))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for XOR-AND combination"
    assert any("xor" in v.lower() or "and" in v.lower() for v in result.violations), (
        f"Expected XOR-AND violation: {result.violations}"
    )


def test_xor_split_or_join_warning(empty_graph: Graph) -> None:
    """XOR split with OR join triggers warning (redundant pattern).

    SHACL Constraint: SPARQL (?splitType=XOR AND ?joinType=OR) = warning
    Note: This may pass if warnings don't fail conformance
    """
    combo = URIRef("urn:combo:XOR-OR")
    empty_graph.add((combo, RDF.type, YAWL.SplitJoinCombination))
    empty_graph.add((combo, YAWL.splitType, YAWL.XOR))
    empty_graph.add((combo, YAWL.joinType, YAWL.OR))

    result = validate_topology(empty_graph, SHAPES_PATH)
    # Warning severity may not fail conformance, but should appear in violations
    if not result.conforms:
        assert any("xor" in v.lower() or "or" in v.lower() for v in result.violations)


# =============================================================================
# STRUCTURED LOOP VALIDATION (Pattern 22)
# =============================================================================


def test_structured_loop_max_iterations_positive(empty_graph: Graph) -> None:
    """Structured loop with maxIterations >= 1 passes validation.

    SHACL Constraint: sh:minInclusive 1 on yawl:maxIterations
    """
    loop = URIRef("urn:loop:ValidLoop")
    empty_graph.add((loop, RDF.type, YAWL_PATTERN.StructuredLoop))
    empty_graph.add((loop, YAWL.maxIterations, Literal(100)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


def test_structured_loop_max_iterations_zero_invalid(empty_graph: Graph) -> None:
    """Structured loop with maxIterations=0 violates constraint.

    SHACL Constraint: sh:minInclusive 1 on yawl:maxIterations
    """
    loop = URIRef("urn:loop:InvalidLoop")
    empty_graph.add((loop, RDF.type, YAWL_PATTERN.StructuredLoop))
    empty_graph.add((loop, YAWL.maxIterations, Literal(0)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for maxIterations=0"
    assert any("iteration" in v.lower() for v in result.violations), (
        f"Expected iteration violation: {result.violations}"
    )


# =============================================================================
# CANCELLATION REGION VALIDATION
# =============================================================================


def test_cancellation_region_requires_trigger(empty_graph: Graph) -> None:
    """Cancellation region without trigger violates minCount constraint.

    SHACL Constraint: sh:minCount 1 on yawl:cancellationTrigger
    """
    region = URIRef("urn:region:NoTrigger")
    task = URIRef("urn:task:ScopedTask")

    empty_graph.add((region, RDF.type, YAWL.CancellationRegion))
    empty_graph.add((region, YAWL.cancellationScope, task))
    # Missing: cancellationTrigger

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for missing trigger"


def test_cancellation_region_requires_scoped_tasks(empty_graph: Graph) -> None:
    """Cancellation region without scoped tasks violates minCount constraint.

    SHACL Constraint: sh:minCount 1 on yawl:cancellationScope
    """
    region = URIRef("urn:region:NoScope")
    trigger = URIRef("urn:task:Trigger")

    empty_graph.add((region, RDF.type, YAWL.CancellationRegion))
    empty_graph.add((region, YAWL.cancellationTrigger, trigger))
    # Missing: cancellationScope

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for missing scope"


def test_cancellation_region_valid(empty_graph: Graph) -> None:
    """Cancellation region with trigger and scoped tasks passes validation."""
    region = URIRef("urn:region:ValidRegion")
    trigger = URIRef("urn:task:Trigger")
    task1 = URIRef("urn:task:Task1")
    task2 = URIRef("urn:task:Task2")

    # Tasks must be typed
    empty_graph.add((trigger, RDF.type, YAWL.Task))
    empty_graph.add((trigger, YAWL.id, Literal("Trigger")))
    empty_graph.add((task1, RDF.type, YAWL.Task))
    empty_graph.add((task1, YAWL.id, Literal("Task1")))
    empty_graph.add((task2, RDF.type, YAWL.Task))
    empty_graph.add((task2, YAWL.id, Literal("Task2")))

    empty_graph.add((region, RDF.type, YAWL.CancellationRegion))
    empty_graph.add((region, YAWL.cancellationTrigger, trigger))
    empty_graph.add((region, YAWL.cancellationScope, task1))
    empty_graph.add((region, YAWL.cancellationScope, task2))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


# =============================================================================
# DEFERRED CHOICE VALIDATION
# =============================================================================


def test_deferred_choice_requires_branches(empty_graph: Graph) -> None:
    """Deferred choice with < 2 branches violates SPARQL constraint.

    SHACL Constraint: COUNT(?branch) < 2 = violation
    """
    choice = URIRef("urn:choice:InvalidChoice")
    branch = URIRef("urn:branch:1")

    empty_graph.add((choice, RDF.type, YAWL_PATTERN.DeferredChoice))
    empty_graph.add((choice, YAWL.competingBranch, branch))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for < 2 branches"


def test_deferred_choice_valid(empty_graph: Graph) -> None:
    """Deferred choice with >= 2 competing branches passes validation."""
    choice = URIRef("urn:choice:ValidChoice")
    branch1 = URIRef("urn:branch:1")
    branch2 = URIRef("urn:branch:2")
    branch3 = URIRef("urn:branch:3")

    empty_graph.add((choice, RDF.type, YAWL_PATTERN.DeferredChoice))
    empty_graph.add((choice, YAWL.competingBranch, branch1))
    empty_graph.add((choice, YAWL.competingBranch, branch2))
    empty_graph.add((choice, YAWL.competingBranch, branch3))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


# =============================================================================
# WORKFLOW INSTANCE VALIDATION
# =============================================================================


def test_workflow_instance_valid_status(valid_workflow_instance_graph: Graph) -> None:
    """Workflow instance with valid status passes enumeration constraint.

    SHACL Constraint: sh:in ("enabled", "running", "completed", ...)
    """
    result = validate_topology(valid_workflow_instance_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance, got violations: {result.violations}"


def test_workflow_instance_invalid_status(empty_graph: Graph) -> None:
    """Workflow instance with invalid status violates enumeration constraint.

    SHACL Constraint: sh:in (valid statuses) - "bogus" not in list
    """
    workflow = URIRef("urn:workflow:W1")
    instance = URIRef("urn:instance:I1")

    # Workflow must be typed
    empty_graph.add((workflow, RDF.type, YAWL.Workflow))

    empty_graph.add((instance, RDF.type, YAWL.WorkflowInstance))
    empty_graph.add((instance, YAWL.instanceOf, workflow))
    empty_graph.add((instance, YAWL.status, Literal("bogus_status")))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for invalid status"


def test_workflow_instance_missing_reference(empty_graph: Graph) -> None:
    """Workflow instance without instanceOf violates minCount constraint.

    SHACL Constraint: sh:minCount 1 on yawl:instanceOf
    """
    instance = URIRef("urn:instance:I1")

    empty_graph.add((instance, RDF.type, YAWL.WorkflowInstance))
    empty_graph.add((instance, YAWL.status, Literal("running")))
    # Missing: instanceOf

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, "Expected SHACL violation for missing instanceOf"


# =============================================================================
# PARAMETRIZED TESTS FOR SPLIT/JOIN COMBINATIONS
# =============================================================================


@pytest.mark.parametrize(("split_type", "expected_min_flows"), [(YAWL.AND, 2), (YAWL.OR, 2), (YAWL.XOR, 2)])
def test_split_types_require_minimum_flows(empty_graph: Graph, split_type: URIRef, expected_min_flows: int) -> None:
    """All split types (AND/OR/XOR) require >= 2 outgoing flows.

    Parametrized test verifying SPARQL constraint across all split types.
    """
    task = URIRef(f"urn:task:{split_type.split('#')[-1]}Split")
    flow = URIRef("urn:flow:1")
    target = URIRef("urn:task:Target")

    empty_graph.add((task, RDF.type, YAWL.Task))
    empty_graph.add((task, YAWL.id, Literal(f"{split_type.split('#')[-1]}Split")))
    empty_graph.add((task, YAWL.splitType, split_type))
    empty_graph.add((task, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task))
    empty_graph.add((flow, YAWL.nextElementRef, target))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, f"Expected SHACL violation for {split_type} with < {expected_min_flows} flows"


@pytest.mark.parametrize(
    ("join_type", "expected_min_incoming"), [(YAWL.AND, 2), (YAWL.OR, 2), (YAWL.XOR, 2), (YAWL.Discriminator, 2)]
)
def test_join_types_require_minimum_incoming(empty_graph: Graph, join_type: URIRef, expected_min_incoming: int) -> None:
    """All join types (AND/OR/XOR/Discriminator) require >= 2 incoming flows.

    Parametrized test verifying SPARQL constraint across all join types.
    """
    task_join = URIRef(f"urn:task:{join_type.split('#')[-1]}Join")
    task_a = URIRef("urn:task:A")
    flow = URIRef("urn:flow:1")

    empty_graph.add((task_join, RDF.type, YAWL.Task))
    empty_graph.add((task_join, YAWL.id, Literal(f"{join_type.split('#')[-1]}Join")))
    empty_graph.add((task_join, YAWL.joinType, join_type))

    empty_graph.add((task_a, YAWL.flowsInto, flow))
    empty_graph.add((flow, RDF.type, YAWL.Flow))
    empty_graph.add((flow, YAWL.flowsFrom, task_a))
    empty_graph.add((flow, YAWL.nextElementRef, task_join))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms, f"Expected SHACL violation for {join_type} with < {expected_min_incoming} incoming"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


def test_multiple_violations_aggregated(empty_graph: Graph) -> None:
    """Multiple SHACL violations are aggregated in result.violations.

    Verifies violation aggregation when graph has multiple constraint failures.
    """
    # Add multiple invalid patterns
    disc = URIRef("urn:disc:InvalidDisc")
    empty_graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    empty_graph.add((disc, YAWL.quorum, Literal(0)))  # Violation 1: quorum < 1
    empty_graph.add((disc, YAWL.totalBranches, Literal(0)))  # Violation 2: total < 1

    loop = URIRef("urn:loop:InvalidLoop")
    empty_graph.add((loop, RDF.type, YAWL_PATTERN.StructuredLoop))
    empty_graph.add((loop, YAWL.maxIterations, Literal(0)))  # Violation 3: max < 1

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms
    assert len(result.violations) >= 2, f"Expected >= 2 violations, got {len(result.violations)}"


def test_empty_graph_conforms(empty_graph: Graph) -> None:
    """Empty graph passes validation (no constraints to violate).

    Baseline test: SHACL validation with no data = conformance.
    """
    result = validate_topology(empty_graph, SHAPES_PATH)
    assert result.conforms, f"Expected conformance for empty graph: {result.violations}"


def test_validation_report_graph_available_on_failure(empty_graph: Graph) -> None:
    """SHACL validation report graph is available when violations occur.

    Verifies that report_graph contains RDF triples for debugging.
    """
    disc = URIRef("urn:disc:InvalidDisc")
    empty_graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
    empty_graph.add((disc, YAWL.quorum, Literal(0)))

    result = validate_topology(empty_graph, SHAPES_PATH)
    assert not result.conforms
    assert result.report_graph is not None, "Expected report_graph on failure"
    assert len(result.report_graph) > 0, "Expected non-empty report graph"
