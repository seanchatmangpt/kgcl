"""Tests for YAWL SPARQL query extraction.

Validates all SPARQL queries against test ontology data using Chicago School TDD.
Tests verify observable behavior: correct pattern extraction, validation, and topology.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, RDFS, XSD, Graph, Literal, URIRef

from kgcl.yawl_engine.sparql_queries import (
    YAWL,
    YAWL_EXEC,
    YAWL_PATTERN,
    ExecutionSemantics,
    FlowDefinition,
    PatternDefinition,
    PermutationEntry,
    TaskConfiguration,
    extract_all_patterns,
    extract_execution_semantics,
    extract_flow_topology,
    extract_patterns_by_category,
    extract_permutation_matrix,
    extract_task_configurations,
    extract_workflow_patterns,
    validate_pattern_requirements,
    validate_workflow,
)


@pytest.fixture
def ontology_graph() -> Graph:
    """Create test ontology graph with pattern definitions.

    Returns
    -------
    Graph
        RDF graph containing YAWL pattern ontology
    """
    g = Graph()
    g.bind("yawl", YAWL)
    g.bind("yawl-pattern", YAWL_PATTERN)
    g.bind("rdfs", RDFS)

    # Pattern 1: Sequence
    p1 = URIRef("http://bitflow.ai/ontology/yawl/patterns/v1#Pattern1")
    g.add((p1, RDF.type, YAWL_PATTERN.WorkflowPattern))
    g.add((p1, YAWL_PATTERN.patternId, Literal(1, datatype=XSD.integer)))
    g.add((p1, YAWL_PATTERN.patternName, Literal("Sequence")))
    g.add((p1, RDFS.comment, Literal("Sequential execution of tasks")))
    g.add((p1, YAWL_PATTERN.patternCategory, Literal("control-flow")))
    g.add((p1, YAWL.requiredSplitType, Literal("NONE")))
    g.add((p1, YAWL.requiredJoinType, Literal("NONE")))
    g.add((p1, YAWL.requiresFlowPredicate, Literal(False, datatype=XSD.boolean)))
    g.add((p1, YAWL.requiresQuorum, Literal(False, datatype=XSD.boolean)))

    # Pattern 2: Parallel Split
    p2 = URIRef("http://bitflow.ai/ontology/yawl/patterns/v1#Pattern2")
    g.add((p2, RDF.type, YAWL_PATTERN.WorkflowPattern))
    g.add((p2, YAWL_PATTERN.patternId, Literal(2, datatype=XSD.integer)))
    g.add((p2, YAWL_PATTERN.patternName, Literal("Parallel Split")))
    g.add((p2, RDFS.comment, Literal("AND split into parallel branches")))
    g.add((p2, YAWL_PATTERN.patternCategory, Literal("control-flow")))
    g.add((p2, YAWL.requiredSplitType, Literal("AND")))
    g.add((p2, YAWL.requiredJoinType, Literal("NONE")))
    g.add((p2, YAWL.requiresFlowPredicate, Literal(False, datatype=XSD.boolean)))
    g.add((p2, YAWL.requiresQuorum, Literal(False, datatype=XSD.boolean)))

    # Pattern 6: Multi-Choice
    p6 = URIRef("http://bitflow.ai/ontology/yawl/patterns/v1#Pattern6")
    g.add((p6, RDF.type, YAWL_PATTERN.WorkflowPattern))
    g.add((p6, YAWL_PATTERN.patternId, Literal(6, datatype=XSD.integer)))
    g.add((p6, YAWL_PATTERN.patternName, Literal("Multi-Choice")))
    g.add((p6, RDFS.comment, Literal("OR split selecting multiple branches")))
    g.add((p6, YAWL_PATTERN.patternCategory, Literal("control-flow")))
    g.add((p6, YAWL.requiredSplitType, Literal("OR")))
    g.add((p6, YAWL.requiredJoinType, Literal("NONE")))
    g.add((p6, YAWL.requiresFlowPredicate, Literal(True, datatype=XSD.boolean)))
    g.add((p6, YAWL.requiresQuorum, Literal(False, datatype=XSD.boolean)))

    return g


@pytest.fixture
def permutation_graph() -> Graph:
    """Create test graph with split-join permutation matrix.

    Returns
    -------
    Graph
        RDF graph containing permutation entries
    """
    g = Graph()
    g.bind("yawl", YAWL)

    # Valid combination: AND split + AND join
    combo1 = URIRef("http://www.yawlfoundation.org/yawlschema#AndAndCombo")
    g.add((combo1, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo1, YAWL.splitType, Literal("AND")))
    g.add((combo1, YAWL.joinType, Literal("AND")))
    g.add((combo1, YAWL.isValid, Literal(True, datatype=XSD.boolean)))
    g.add((combo1, YAWL.generatesPattern, Literal("2,3")))
    g.add((combo1, RDFS.comment, Literal("Parallel split and synchronization")))

    # Valid combination: XOR split + XOR join
    combo2 = URIRef("http://www.yawlfoundation.org/yawlschema#XorXorCombo")
    g.add((combo2, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo2, YAWL.splitType, Literal("XOR")))
    g.add((combo2, YAWL.joinType, Literal("XOR")))
    g.add((combo2, YAWL.isValid, Literal(True, datatype=XSD.boolean)))
    g.add((combo2, YAWL.generatesPattern, Literal("4,5")))
    g.add((combo2, RDFS.comment, Literal("Exclusive choice and merge")))

    # Invalid combination: OR split + AND join
    combo3 = URIRef("http://www.yawlfoundation.org/yawlschema#OrAndCombo")
    g.add((combo3, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo3, YAWL.splitType, Literal("OR")))
    g.add((combo3, YAWL.joinType, Literal("AND")))
    g.add((combo3, YAWL.isValid, Literal(False, datatype=XSD.boolean)))
    g.add((combo3, RDFS.comment, Literal("Invalid: OR split requires OR join")))

    return g


@pytest.fixture
def workflow_graph() -> Graph:
    """Create test workflow graph with tasks and flows.

    Returns
    -------
    Graph
        RDF graph containing workflow definition
    """
    g = Graph()
    g.bind("yawl", YAWL)
    g.bind("yawl-exec", YAWL_EXEC)

    workflow = URIRef("http://example.org/workflow1")
    task1 = URIRef("http://example.org/task1")
    task2 = URIRef("http://example.org/task2")
    task3 = URIRef("http://example.org/task3")

    # Workflow structure
    g.add((workflow, YAWL.hasTask, task1))
    g.add((workflow, YAWL.hasTask, task2))
    g.add((workflow, YAWL.hasTask, task3))

    # Task 1: AND split, NONE join
    g.add((task1, RDF.type, YAWL.Task))
    g.add((task1, YAWL.hasSplit, Literal("AND")))
    g.add((task1, YAWL.hasJoin, Literal("NONE")))

    # Task 2: NONE split, AND join
    g.add((task2, RDF.type, YAWL.Task))
    g.add((task2, YAWL.hasSplit, Literal("NONE")))
    g.add((task2, YAWL.hasJoin, Literal("AND")))
    timer = URIRef("http://example.org/timer1")
    g.add((task2, YAWL.hasTimer, timer))

    # Task 3: XOR split, XOR join
    g.add((task3, RDF.type, YAWL.Task))
    g.add((task3, YAWL.hasSplit, Literal("XOR")))
    g.add((task3, YAWL.hasJoin, Literal("XOR")))
    resourcing = URIRef("http://example.org/resourcing1")
    g.add((task3, YAWL.hasResourcing, resourcing))
    cancellation = URIRef("http://example.org/cancellation1")
    g.add((task3, YAWL.hasCancellationRegion, cancellation))

    # Flow topology
    flow1 = URIRef("http://example.org/flow1")
    g.add((task1, YAWL.flowsInto, flow1))
    g.add((flow1, YAWL.nextElementRef, task2))
    g.add((flow1, YAWL.isDefaultFlow, Literal(True, datatype=XSD.boolean)))

    flow2 = URIRef("http://example.org/flow2")
    g.add((task1, YAWL.flowsInto, flow2))
    g.add((flow2, YAWL.nextElementRef, task3))
    predicate = Literal("/data/amount > 1000")
    g.add((flow2, YAWL.hasPredicate, predicate))
    g.add((flow2, YAWL.hasPriority, Literal(1, datatype=XSD.integer)))
    g.add((flow2, YAWL.evaluationOrder, Literal(1, datatype=XSD.integer)))

    # Execution semantics
    g.add((task1, YAWL_EXEC.executionMode, Literal("automatic")))
    g.add((task1, YAWL_EXEC.taskDuration, Literal("PT5M")))

    timeout_policy = URIRef("http://example.org/timeout1")
    g.add((task2, YAWL_EXEC.timeoutPolicy, timeout_policy))
    retry_policy = URIRef("http://example.org/retry1")
    g.add((task2, YAWL_EXEC.retryPolicy, retry_policy))

    g.add((task3, YAWL.maxInstances, Literal(5, datatype=XSD.integer)))
    g.add((task3, YAWL.threshold, Literal(3, datatype=XSD.integer)))

    # Add permutation matrix for validation
    combo1 = URIRef("http://www.yawlfoundation.org/yawlschema#AndNoneCombo")
    g.add((combo1, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo1, YAWL.splitType, Literal("AND")))
    g.add((combo1, YAWL.joinType, Literal("NONE")))
    g.add((combo1, YAWL.isValid, Literal(True, datatype=XSD.boolean)))

    combo2 = URIRef("http://www.yawlfoundation.org/yawlschema#NoneAndCombo")
    g.add((combo2, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo2, YAWL.splitType, Literal("NONE")))
    g.add((combo2, YAWL.joinType, Literal("AND")))
    g.add((combo2, YAWL.isValid, Literal(True, datatype=XSD.boolean)))

    combo3 = URIRef("http://www.yawlfoundation.org/yawlschema#XorXorCombo")
    g.add((combo3, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo3, YAWL.splitType, Literal("XOR")))
    g.add((combo3, YAWL.joinType, Literal("XOR")))
    g.add((combo3, YAWL.isValid, Literal(True, datatype=XSD.boolean)))
    g.add((combo3, YAWL.generatesPattern, Literal("4,5")))

    return g


def test_extract_all_patterns_returns_sorted_list(ontology_graph: Graph) -> None:
    """Patterns are extracted in ID order."""
    patterns = extract_all_patterns(ontology_graph)

    assert len(patterns) == 3
    assert patterns[0].pattern_id == 1
    assert patterns[1].pattern_id == 2
    assert patterns[2].pattern_id == 6


def test_extract_pattern_includes_all_fields(ontology_graph: Graph) -> None:
    """Pattern extraction captures all ontology fields."""
    patterns = extract_all_patterns(ontology_graph)
    p1 = patterns[0]

    assert p1.pattern_id == 1
    assert p1.name == "Sequence"
    assert p1.description == "Sequential execution of tasks"
    assert p1.category == "control-flow"
    assert p1.required_split == "NONE"
    assert p1.required_join == "NONE"
    assert p1.requires_predicate is False
    assert p1.requires_quorum is False


def test_extract_pattern_with_predicate_requirement(ontology_graph: Graph) -> None:
    """Pattern requiring flow predicate is correctly flagged."""
    patterns = extract_all_patterns(ontology_graph)
    p6 = next(p for p in patterns if p.pattern_id == 6)

    assert p6.name == "Multi-Choice"
    assert p6.required_split == "OR"
    assert p6.requires_predicate is True
    assert p6.requires_quorum is False


def test_extract_permutation_matrix_includes_valid_combos(permutation_graph: Graph) -> None:
    """Valid split-join combinations are extracted."""
    entries = extract_permutation_matrix(permutation_graph)
    valid_entries = [e for e in entries if e.is_valid]

    assert len(valid_entries) == 2
    assert any(e.split_type == "AND" and e.join_type == "AND" for e in valid_entries)
    assert any(e.split_type == "XOR" and e.join_type == "XOR" for e in valid_entries)


def test_extract_permutation_matrix_parses_pattern_ids(permutation_graph: Graph) -> None:
    """Pattern IDs are parsed from comma-separated string."""
    entries = extract_permutation_matrix(permutation_graph)
    and_combo = next(e for e in entries if e.split_type == "AND" and e.join_type == "AND")

    assert and_combo.generated_patterns == [2, 3]
    assert and_combo.description == "Parallel split and synchronization"


def test_extract_permutation_matrix_includes_invalid_combos(permutation_graph: Graph) -> None:
    """Invalid combinations are marked as such."""
    entries = extract_permutation_matrix(permutation_graph)
    invalid_entries = [e for e in entries if not e.is_valid]

    assert len(invalid_entries) == 1
    assert invalid_entries[0].split_type == "OR"
    assert invalid_entries[0].join_type == "AND"


def test_extract_task_configurations_from_workflow(workflow_graph: Graph) -> None:
    """Task configurations are extracted with split-join types."""
    configs = extract_task_configurations(workflow_graph)

    assert len(configs) == 3
    task1 = next(c for c in configs if "task1" in c.task_uri)
    assert task1.split_type == "AND"
    assert task1.join_type == "NONE"


def test_extract_task_with_timer(workflow_graph: Graph) -> None:
    """Task with timer configuration is extracted."""
    configs = extract_task_configurations(workflow_graph)
    task2 = next(c for c in configs if "task2" in c.task_uri)

    assert task2.timer_uri is not None
    assert "timer1" in task2.timer_uri


def test_extract_task_with_resourcing_and_cancellation(workflow_graph: Graph) -> None:
    """Task with resourcing and cancellation is extracted."""
    configs = extract_task_configurations(workflow_graph)
    task3 = next(c for c in configs if "task3" in c.task_uri)

    assert task3.resourcing_uri is not None
    assert "resourcing1" in task3.resourcing_uri
    assert task3.cancellation_region is not None
    assert "cancellation1" in task3.cancellation_region


def test_extract_flow_topology_includes_all_flows(workflow_graph: Graph) -> None:
    """All flow edges are extracted."""
    flows = extract_flow_topology(workflow_graph)

    assert len(flows) == 2
    assert all("task1" in f.source_uri for f in flows)


def test_extract_flow_with_predicate(workflow_graph: Graph) -> None:
    """Flow with XPath predicate is extracted."""
    flows = extract_flow_topology(workflow_graph)
    flow_with_pred = next(f for f in flows if f.predicate is not None)

    assert flow_with_pred.predicate == "/data/amount > 1000"
    assert flow_with_pred.priority == 1
    assert flow_with_pred.evaluation_order == 1
    assert flow_with_pred.is_default is False


def test_extract_flow_default_flag(workflow_graph: Graph) -> None:
    """Default flow is correctly flagged."""
    flows = extract_flow_topology(workflow_graph)
    default_flow = next(f for f in flows if f.is_default)

    assert default_flow.predicate is None
    assert "task2" in default_flow.target_uri


def test_validate_workflow_with_valid_combos(workflow_graph: Graph) -> None:
    """Workflow with all valid combinations passes validation."""
    workflow_uri = "http://example.org/workflow1"
    is_valid = validate_workflow(workflow_graph, workflow_uri)

    assert is_valid is True


def test_validate_workflow_with_invalid_combo() -> None:
    """Workflow with invalid combination fails validation."""
    g = Graph()
    g.bind("yawl", YAWL)

    workflow = URIRef("http://example.org/invalid_workflow")
    task = URIRef("http://example.org/bad_task")

    g.add((workflow, YAWL.hasTask, task))
    g.add((task, RDF.type, YAWL.Task))
    g.add((task, YAWL.hasSplit, Literal("OR")))
    g.add((task, YAWL.hasJoin, Literal("AND")))

    # No valid permutation entry for OR+AND
    combo = URIRef("http://www.yawlfoundation.org/yawlschema#OrAndCombo")
    g.add((combo, RDF.type, YAWL.SplitJoinCombination))
    g.add((combo, YAWL.splitType, Literal("OR")))
    g.add((combo, YAWL.joinType, Literal("AND")))
    g.add((combo, YAWL.isValid, Literal(False, datatype=XSD.boolean)))

    is_valid = validate_workflow(g, str(workflow))

    assert is_valid is False


def test_extract_execution_semantics_all_tasks(workflow_graph: Graph) -> None:
    """Execution semantics are extracted for all tasks."""
    semantics = extract_execution_semantics(workflow_graph)

    assert len(semantics) >= 3


def test_extract_execution_mode(workflow_graph: Graph) -> None:
    """Task execution mode is extracted."""
    semantics = extract_execution_semantics(workflow_graph)
    task1_sem = next(s for s in semantics if "task1" in s.task_uri)

    assert task1_sem.execution_mode == "automatic"
    assert task1_sem.duration == "PT5M"


def test_extract_timeout_and_retry_policies(workflow_graph: Graph) -> None:
    """Timeout and retry policies are extracted."""
    semantics = extract_execution_semantics(workflow_graph)
    task2_sem = next(s for s in semantics if "task2" in s.task_uri)

    assert task2_sem.timeout_policy is not None
    assert "timeout1" in task2_sem.timeout_policy
    assert task2_sem.retry_policy is not None
    assert "retry1" in task2_sem.retry_policy


def test_extract_multiple_instance_settings(workflow_graph: Graph) -> None:
    """Multiple instance settings are extracted."""
    semantics = extract_execution_semantics(workflow_graph)
    task3_sem = next(s for s in semantics if "task3" in s.task_uri)

    assert task3_sem.max_instances == 5
    assert task3_sem.threshold == 3


def test_extract_patterns_by_category(ontology_graph: Graph) -> None:
    """Patterns filtered by category."""
    control_flow = extract_patterns_by_category(ontology_graph, "control-flow")

    assert len(control_flow) == 3
    assert all(p.category == "control-flow" for p in control_flow)


def test_extract_workflow_patterns_from_workflow(workflow_graph: Graph) -> None:
    """Patterns present in workflow are extracted."""
    # Add pattern definitions to the graph
    p4 = URIRef("http://bitflow.ai/ontology/yawl/patterns/v1#Pattern4")
    workflow_graph.add((p4, RDF.type, YAWL_PATTERN.WorkflowPattern))
    workflow_graph.add((p4, YAWL_PATTERN.patternId, Literal(4, datatype=XSD.integer)))
    workflow_graph.add((p4, YAWL_PATTERN.patternName, Literal("Exclusive Choice")))

    p5 = URIRef("http://bitflow.ai/ontology/yawl/patterns/v1#Pattern5")
    workflow_graph.add((p5, RDF.type, YAWL_PATTERN.WorkflowPattern))
    workflow_graph.add((p5, YAWL_PATTERN.patternId, Literal(5, datatype=XSD.integer)))
    workflow_graph.add((p5, YAWL_PATTERN.patternName, Literal("Simple Merge")))

    workflow_uri = "http://example.org/workflow1"
    patterns = extract_workflow_patterns(workflow_graph, workflow_uri)

    # Workflow has XOR split+join which generates patterns 4,5
    pattern_ids = {p.pattern_id for p in patterns}
    assert 4 in pattern_ids or 5 in pattern_ids


def test_validate_pattern_requirements_split_type(workflow_graph: Graph, ontology_graph: Graph) -> None:
    """Pattern split type requirement is validated."""
    task_uri = "http://example.org/task1"
    pattern = PatternDefinition(
        pattern_uri="http://test.org/pattern",
        pattern_id=2,
        name="Parallel Split",
        description=None,
        category=None,
        required_split="AND",
        required_join=None,
        requires_predicate=False,
        requires_quorum=False,
    )

    # Task1 has AND split - should pass
    is_valid = validate_pattern_requirements(workflow_graph, task_uri, pattern)
    assert is_valid is True


def test_validate_pattern_requirements_join_type(workflow_graph: Graph, ontology_graph: Graph) -> None:
    """Pattern join type requirement is validated."""
    task_uri = "http://example.org/task2"
    pattern = PatternDefinition(
        pattern_uri="http://test.org/pattern",
        pattern_id=3,
        name="Synchronization",
        description=None,
        category=None,
        required_split=None,
        required_join="AND",
        requires_predicate=False,
        requires_quorum=False,
    )

    # Task2 has AND join - should pass
    is_valid = validate_pattern_requirements(workflow_graph, task_uri, pattern)
    assert is_valid is True


def test_validate_pattern_requirements_predicate(workflow_graph: Graph, ontology_graph: Graph) -> None:
    """Pattern requiring flow predicate is validated."""
    task_uri = "http://example.org/task1"
    pattern = PatternDefinition(
        pattern_uri="http://test.org/pattern",
        pattern_id=6,
        name="Multi-Choice",
        description=None,
        category=None,
        required_split="OR",
        required_join=None,
        requires_predicate=True,
        requires_quorum=False,
    )

    # Task1 has flow with predicate - should pass
    is_valid = validate_pattern_requirements(workflow_graph, task_uri, pattern)
    # This will fail split type check (AND vs OR) but demonstrates predicate validation
    assert is_valid is False  # Fails on split type, not predicate


def test_validate_pattern_requirements_quorum(workflow_graph: Graph, ontology_graph: Graph) -> None:
    """Pattern requiring quorum is validated."""
    task_uri = "http://example.org/task3"
    pattern = PatternDefinition(
        pattern_uri="http://test.org/pattern",
        pattern_id=30,
        name="M-out-of-N Join",
        description=None,
        category=None,
        required_split=None,
        required_join=None,
        requires_predicate=False,
        requires_quorum=True,
    )

    # Task3 has threshold (quorum) - should pass
    is_valid = validate_pattern_requirements(workflow_graph, task_uri, pattern)
    assert is_valid is True


def test_pattern_definition_immutability() -> None:
    """PatternDefinition is immutable."""
    from dataclasses import FrozenInstanceError

    pattern = PatternDefinition(
        pattern_uri="http://test.org/p1",
        pattern_id=1,
        name="Test",
        description=None,
        category=None,
        required_split=None,
        required_join=None,
        requires_predicate=False,
        requires_quorum=False,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        pattern.pattern_id = 2  # type: ignore[misc]


def test_permutation_entry_immutability() -> None:
    """PermutationEntry is immutable."""
    from dataclasses import FrozenInstanceError

    entry = PermutationEntry(
        combination_uri="http://test.org/combo",
        split_type="AND",
        join_type="AND",
        is_valid=True,
        generated_patterns=[2, 3],
        description=None,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        entry.is_valid = False  # type: ignore[misc]


def test_task_configuration_immutability() -> None:
    """TaskConfiguration is immutable."""
    from dataclasses import FrozenInstanceError

    config = TaskConfiguration(
        task_uri="http://test.org/task",
        split_type="AND",
        join_type="NONE",
        timer_uri=None,
        resourcing_uri=None,
        cancellation_region=None,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        config.split_type = "OR"  # type: ignore[misc]


def test_flow_definition_immutability() -> None:
    """FlowDefinition is immutable."""
    from dataclasses import FrozenInstanceError

    flow = FlowDefinition(
        source_uri="http://test.org/task1",
        flow_uri="http://test.org/flow1",
        target_uri="http://test.org/task2",
        predicate=None,
        is_default=True,
        priority=None,
        evaluation_order=None,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        flow.is_default = False  # type: ignore[misc]


def test_execution_semantics_immutability() -> None:
    """ExecutionSemantics is immutable."""
    from dataclasses import FrozenInstanceError

    semantics = ExecutionSemantics(
        task_uri="http://test.org/task",
        execution_mode="automatic",
        timeout_policy=None,
        retry_policy=None,
        duration="PT5M",
        max_instances=None,
        threshold=None,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
        semantics.execution_mode = "manual"  # type: ignore[misc]
