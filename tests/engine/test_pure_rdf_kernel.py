"""Tests for L5 Pure RDF Kernel - SPARQL templates ARE the logic.

This test suite verifies that the PureRDFKernel executes verb behavior
entirely from SPARQL templates stored in the ontology, with ZERO Python
if/else logic.

The Semantic Singularity: "Logic IS Data"
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import GENESIS_HASH, KGC, YAWL, PureRDFKernel, TransactionContext, VerbConfig


@pytest.fixture
def physics_ontology() -> Graph:
    """Load the physics ontology with SPARQL templates.

    Returns
    -------
    Graph
        The KGC physics ontology.
    """
    ontology = Graph()
    ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def pure_kernel(physics_ontology: Graph) -> PureRDFKernel:
    """Create a Pure RDF Kernel instance.

    Parameters
    ----------
    physics_ontology : Graph
        The physics ontology.

    Returns
    -------
    PureRDFKernel
        L5 kernel instance.
    """
    return PureRDFKernel(physics_ontology)


@pytest.fixture
def base_context() -> TransactionContext:
    """Create base transaction context.

    Returns
    -------
    TransactionContext
        Transaction context for test execution.
    """
    return TransactionContext(tx_id="tx-l5-test", actor="l5-test-system", prev_hash=GENESIS_HASH, data={})


class TestPureRDFKernelL5:
    """Tests for L5 Pure RDF execution - SPARQL templates only."""

    def test_transmute_via_template(self, pure_kernel: PureRDFKernel, base_context: TransactionContext) -> None:
        """Test WCP-1 Sequence via execution template.

        The template should:
        1. Find next element via yawl:flowsInto/yawl:nextElementRef
        2. Add token to next element
        3. Mark subject as completed
        """
        # Arrange: Simple sequence A → B
        workflow = Graph()
        task_a = URIRef("urn:task:a")
        task_b = URIRef("urn:task:b")
        flow = URIRef("urn:flow:a_to_b")

        workflow.add((task_a, YAWL.flowsInto, flow))
        workflow.add((flow, YAWL.nextElementRef, task_b))
        workflow.add((task_a, KGC.hasToken, Literal(True)))

        # WCP-1 execution template from ontology
        execution_template = """
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?next kgc:hasToken true .
                ?subject kgc:completedAt ?txId .
            }
            WHERE {
                ?subject yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """
        removal_template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            DELETE WHERE { ?subject kgc:hasToken true }
        """

        config = VerbConfig(verb="transmute", execution_template=execution_template, removal_template=removal_template)

        # Act: Execute via Pure RDF Kernel
        delta = pure_kernel.execute(workflow, task_a, base_context, config)

        # Assert: Token moved via template (no Python logic)
        assert (task_b, KGC.hasToken, Literal(True)) in delta.additions
        assert (task_a, KGC.completedAt, Literal(base_context.tx_id)) in delta.additions

    def test_copy_topology_via_template(self, pure_kernel: PureRDFKernel, base_context: TransactionContext) -> None:
        """Test WCP-2 Parallel Split via execution template.

        The template should:
        1. Find ALL next elements via yawl:flowsInto
        2. Add token to ALL of them (AND-split)
        3. Mark subject as completed
        """
        # Arrange: Parallel split A → {B, C}
        workflow = Graph()
        task_a = URIRef("urn:task:a")
        task_b = URIRef("urn:task:b")
        task_c = URIRef("urn:task:c")
        flow_b = URIRef("urn:flow:a_to_b")
        flow_c = URIRef("urn:flow:a_to_c")

        workflow.add((task_a, YAWL.flowsInto, flow_b))
        workflow.add((flow_b, YAWL.nextElementRef, task_b))
        workflow.add((task_a, YAWL.flowsInto, flow_c))
        workflow.add((flow_c, YAWL.nextElementRef, task_c))
        workflow.add((task_a, KGC.hasToken, Literal(True)))

        # WCP-2 execution template (topology copy)
        execution_template = """
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?next kgc:hasToken true .
                ?subject kgc:completedAt ?txId .
            }
            WHERE {
                ?subject yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """
        removal_template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            DELETE WHERE { ?subject kgc:hasToken true }
        """

        config = VerbConfig(verb="copy", execution_template=execution_template, removal_template=removal_template)

        # Act: Execute via Pure RDF Kernel
        delta = pure_kernel.execute(workflow, task_a, base_context, config)

        # Assert: Both branches get tokens (AND-split)
        assert (task_b, KGC.hasToken, Literal(True)) in delta.additions
        assert (task_c, KGC.hasToken, Literal(True)) in delta.additions
        assert (task_a, KGC.completedAt, Literal(base_context.tx_id)) in delta.additions

    def test_void_case_via_template(self, pure_kernel: PureRDFKernel, base_context: TransactionContext) -> None:
        """Test WCP-43 Explicit Termination via execution template.

        The template should:
        1. Find ALL nodes with tokens
        2. Mark them all as voided
        """
        # Arrange: Multiple active tasks
        workflow = Graph()
        end_node = URIRef("urn:workflow:end")
        task1 = URIRef("urn:task:1")
        task2 = URIRef("urn:task:2")

        workflow.add((task1, KGC.hasToken, Literal(True)))
        workflow.add((task2, KGC.hasToken, Literal(True)))

        # WCP-43 execution template (void case)
        execution_template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?task kgc:voidedAt ?txId .
                ?task kgc:terminatedReason "explicit" .
                ?subject kgc:cancellationScope "case" .
            }
            WHERE {
                ?task kgc:hasToken true .
            }
        """
        removal_template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            DELETE WHERE { ?task kgc:hasToken true }
        """

        config = VerbConfig(
            verb="void",
            execution_template=execution_template,
            removal_template=removal_template,
            cancellation_scope="case",
        )

        # Act: Execute via Pure RDF Kernel
        delta = pure_kernel.execute(workflow, end_node, base_context, config)

        # Assert: Both tasks voided
        assert (task1, KGC.voidedAt, Literal(base_context.tx_id)) in delta.additions
        assert (task2, KGC.voidedAt, Literal(base_context.tx_id)) in delta.additions

    def test_no_template_returns_empty_delta(
        self, pure_kernel: PureRDFKernel, base_context: TransactionContext
    ) -> None:
        """Test that missing template returns empty delta (identity)."""
        # Arrange
        workflow = Graph()
        task = URIRef("urn:task:no_template")

        config = VerbConfig(
            verb="transmute",
            execution_template=None,  # No template
        )

        # Act
        delta = pure_kernel.execute(workflow, task, base_context, config)

        # Assert: Empty delta
        assert len(delta.additions) == 0
        assert len(delta.removals) == 0


class TestPureRDFKernelVariableBinding:
    """Tests for template variable binding."""

    def test_subject_binding(self, pure_kernel: PureRDFKernel, base_context: TransactionContext) -> None:
        """Test that ?subject is correctly bound."""
        workflow = Graph()
        task = URIRef("urn:task:specific")
        next_task = URIRef("urn:task:next")
        flow = URIRef("urn:flow:1")

        workflow.add((task, YAWL.flowsInto, flow))
        workflow.add((flow, YAWL.nextElementRef, next_task))

        template = """
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?next kgc:hasToken true .
            }
            WHERE {
                ?subject yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """

        config = VerbConfig(verb="transmute", execution_template=template)
        delta = pure_kernel.execute(workflow, task, base_context, config)

        # Should find next_task via the specific subject binding
        assert (next_task, KGC.hasToken, Literal(True)) in delta.additions

    def test_txid_binding(self, pure_kernel: PureRDFKernel) -> None:
        """Test that ?txId is correctly bound from context."""
        workflow = Graph()
        task = URIRef("urn:task:tx_test")
        next_task = URIRef("urn:task:next")
        flow = URIRef("urn:flow:1")

        workflow.add((task, YAWL.flowsInto, flow))
        workflow.add((flow, YAWL.nextElementRef, next_task))

        ctx = TransactionContext(tx_id="tx-unique-12345", actor="test", prev_hash=GENESIS_HASH, data={})

        template = """
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?next kgc:hasToken true .
                ?subject kgc:completedAt ?txId .
            }
            WHERE {
                ?subject yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """

        config = VerbConfig(verb="transmute", execution_template=template)
        delta = pure_kernel.execute(workflow, task, ctx, config)

        # Should have tx_id in completedAt
        assert (task, KGC.completedAt, Literal("tx-unique-12345")) in delta.additions

    def test_data_binding(self, pure_kernel: PureRDFKernel) -> None:
        """Test that ctx.data values are bound to ?data_KEY placeholders."""
        workflow = Graph()
        task = URIRef("urn:task:data_test")

        ctx = TransactionContext(
            tx_id="tx-data", actor="test", prev_hash=GENESIS_HASH, data={"threshold": 5, "enabled": True}
        )

        # Template that uses data binding
        # Note: This is a simplified test - real predicate evaluation needs more work
        template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT {
                ?subject kgc:configuredThreshold ?data_threshold .
            }
            WHERE {
                BIND(?data_threshold AS ?data_threshold)
            }
        """

        config = VerbConfig(verb="test", execution_template=template)

        # Verify binding happens (even if SPARQL execution is complex)
        bound = pure_kernel._bind_variables(template, task, ctx, workflow)
        assert "5" in bound  # threshold value bound
        assert "?data_threshold" not in bound  # placeholder replaced


class TestPureRDFKernelZeroLogic:
    """Tests verifying ZERO Python logic in execution path."""

    def test_kernel_has_no_conditionals_in_execute(self, pure_kernel: PureRDFKernel) -> None:
        """Verify execute method has no pattern-specific conditionals.

        The execute method should ONLY:
        1. Get template from config
        2. Bind variables
        3. Execute SPARQL
        4. Collect results

        NO if/else on verb types, pattern names, or config flags.
        """
        import inspect

        source = inspect.getsource(pure_kernel.execute)

        # Should NOT contain verb-specific conditionals
        forbidden_patterns = [
            "if config.verb",
            'if verb == "',
            "if selection_mode",
            "if threshold",
            "if cardinality",
            "if cancellation_scope",
            "if stop_on_first",
            "if is_deferred",
            "if is_mutex",
            "if use_dynamic",
            "if use_active",
            "elif cardinality_value",
            "elif threshold_value",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in source, f"Found forbidden pattern: {pattern}"

    def test_all_behavior_from_template(self, pure_kernel: PureRDFKernel, base_context: TransactionContext) -> None:
        """Test that different behaviors come from different templates.

        Same kernel.execute(), different templates → different behavior.
        This proves logic is in RDF, not Python.
        """
        workflow = Graph()
        task = URIRef("urn:task:multi")
        next_task = URIRef("urn:task:next")
        flow = URIRef("urn:flow:1")

        workflow.add((task, YAWL.flowsInto, flow))
        workflow.add((flow, YAWL.nextElementRef, next_task))
        workflow.add((task, KGC.hasToken, Literal(True)))

        # Template 1: Add token to next
        template_add_token = """
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT { ?next kgc:hasToken true . }
            WHERE {
                ?subject yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """

        # Template 2: Mark as voided instead
        template_void = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT { ?subject kgc:voidedAt ?txId . }
            WHERE { ?subject kgc:hasToken true . }
        """

        # Execute with template 1
        config1 = VerbConfig(verb="transmute", execution_template=template_add_token)
        delta1 = pure_kernel.execute(workflow, task, base_context, config1)

        # Execute with template 2 (same kernel, same subject)
        config2 = VerbConfig(verb="void", execution_template=template_void)
        delta2 = pure_kernel.execute(workflow, task, base_context, config2)

        # Different templates → different results
        assert (next_task, KGC.hasToken, Literal(True)) in delta1.additions
        assert (next_task, KGC.hasToken, Literal(True)) not in delta2.additions

        assert (task, KGC.voidedAt, Literal(base_context.tx_id)) in delta2.additions
        assert (task, KGC.voidedAt, Literal(base_context.tx_id)) not in delta1.additions
