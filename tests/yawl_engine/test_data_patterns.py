"""Tests for YAWL Data Patterns (28-35): Data Visibility and Interaction.

This test suite validates all 8 YAWL data patterns with comprehensive
coverage of scoping rules, data transfer mechanisms, and edge cases.

Test Coverage
-------------
- Pattern 28: Task Data (task-scoped variables)
- Pattern 29: Block Data (block-scoped variables)
- Pattern 30: Case Data (case-scoped variables)
- Pattern 31: Workflow Data (global variables)
- Pattern 32: Environment Data (external sources)
- Pattern 33: Task-to-Task Data Interaction
- Pattern 34: Block-to-Sub-Workflow Data Interaction
- Pattern 35: Case-to-Case Data Interaction
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.data_patterns import (
    BlockData,
    CaseData,
    DataContext,
    DataInteractionBlockToSubWorkflow,
    DataInteractionCaseToCase,
    DataInteractionTaskToTask,
    DataScope,
    EnvironmentData,
    TaskData,
    WorkflowData,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# YAWL Namespace
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")


# ============================================================================
# VISIBILITY PATTERNS (28-32)
# ============================================================================


class TestPattern28TaskData:
    """Test Pattern 28: Task Data - Variables scoped to single task instance."""

    def test_task_scoped_isolation(self) -> None:
        """Task variables are isolated - not visible to other tasks."""
        task_data = TaskData()
        task1 = URIRef("urn:task:T1")
        task2 = URIRef("urn:task:T2")

        task_data.set(task1, "order_id", "ORDER-001")
        task_data.set(task2, "order_id", "ORDER-002")

        assert task_data.get(task1, "order_id") == "ORDER-001"
        assert task_data.get(task2, "order_id") == "ORDER-002"
        assert task_data.get(task1, "order_id") != task_data.get(task2, "order_id")

    def test_task_data_lifecycle(self) -> None:
        """Task data is destroyed when task completes."""
        task_data = TaskData()
        task = URIRef("urn:task:ProcessOrder")

        task_data.set(task, "temp_var", "temporary_value")
        assert task_data.get(task, "temp_var") == "temporary_value"

        task_data.clear_task(task)
        assert task_data.get(task, "temp_var") is None

    def test_pattern_id_and_scope(self) -> None:
        """Pattern 28 has correct ID and scope."""
        task_data = TaskData()
        assert task_data.pattern_id == 28
        assert task_data.scope == DataScope.TASK

    def test_complex_type_storage(self) -> None:
        """Task data supports complex types (lists, dicts, objects)."""
        task_data = TaskData()
        task = URIRef("urn:task:T1")

        task_data.set(task, "items", [1, 2, 3, 4, 5])
        task_data.set(task, "metadata", {"created": "2025-11-25", "author": "user1"})

        assert task_data.get(task, "items") == [1, 2, 3, 4, 5]
        assert task_data.get(task, "metadata")["author"] == "user1"

    def test_nonexistent_variable(self) -> None:
        """Getting nonexistent variable returns None."""
        task_data = TaskData()
        task = URIRef("urn:task:T1")

        assert task_data.get(task, "nonexistent") is None


class TestPattern29BlockData:
    """Test Pattern 29: Block Data - Variables scoped to structured block."""

    def test_block_scoped_visibility(self) -> None:
        """Block variables are visible to all tasks in the block."""
        block_data = BlockData()
        block = URIRef("urn:block:OrderProcessing")

        block_data.set(block, "customer_id", "CUST-999")
        block_data.set(block, "order_total", 1500.0)

        assert block_data.get(block, "customer_id") == "CUST-999"
        assert block_data.get(block, "order_total") == 1500.0

    def test_block_isolation(self) -> None:
        """Different blocks have isolated data."""
        block_data = BlockData()
        block1 = URIRef("urn:block:B1")
        block2 = URIRef("urn:block:B2")

        block_data.set(block1, "var", "value1")
        block_data.set(block2, "var", "value2")

        assert block_data.get(block1, "var") == "value1"
        assert block_data.get(block2, "var") == "value2"

    def test_pattern_id_and_scope(self) -> None:
        """Pattern 29 has correct ID and scope."""
        block_data = BlockData()
        assert block_data.pattern_id == 29
        assert block_data.scope == DataScope.BLOCK


class TestPattern30CaseData:
    """Test Pattern 30: Case Data - Variables scoped to workflow case instance."""

    def test_case_scoped_visibility(self) -> None:
        """Case variables are visible across all tasks in the case."""
        case_data = CaseData()
        case_id = "case-12345"

        case_data.set(case_id, "customer_id", "CUST-999")
        case_data.set(case_id, "order_total", 2000.0)
        case_data.set(case_id, "status", "PROCESSING")

        assert case_data.get(case_id, "customer_id") == "CUST-999"
        assert case_data.get(case_id, "order_total") == 2000.0
        assert case_data.get(case_id, "status") == "PROCESSING"

    def test_case_isolation(self) -> None:
        """Different cases have isolated data."""
        case_data = CaseData()

        case_data.set("case-001", "customer", "CUST-A")
        case_data.set("case-002", "customer", "CUST-B")

        assert case_data.get("case-001", "customer") == "CUST-A"
        assert case_data.get("case-002", "customer") == "CUST-B"

    def test_get_all_variables(self) -> None:
        """Can retrieve all variables for a case."""
        case_data = CaseData()
        case_id = "case-123"

        case_data.set(case_id, "var1", "value1")
        case_data.set(case_id, "var2", "value2")
        case_data.set(case_id, "var3", "value3")

        all_vars = case_data.get_all(case_id)
        assert all_vars == {"var1": "value1", "var2": "value2", "var3": "value3"}

    def test_pattern_id_and_scope(self) -> None:
        """Pattern 30 has correct ID and scope."""
        case_data = CaseData()
        assert case_data.pattern_id == 30
        assert case_data.scope == DataScope.CASE


class TestPattern31WorkflowData:
    """Test Pattern 31: Workflow Data - Global variables across all instances."""

    def test_global_visibility(self) -> None:
        """Workflow data is shared across all cases."""
        workflow_data = WorkflowData()

        workflow_data.set("global_counter", 0)
        workflow_data.set("system_config", {"max_retries": 3})

        assert workflow_data.get("global_counter") == 0
        assert workflow_data.get("system_config")["max_retries"] == 3

    def test_atomic_increment(self) -> None:
        """Atomic increment for global counters."""
        workflow_data = WorkflowData()

        workflow_data.set("counter", 10)
        new_value = workflow_data.increment("counter", 5)

        assert new_value == 15
        assert workflow_data.get("counter") == 15

    def test_increment_uninitialized(self) -> None:
        """Increment initializes variable to 0 if not set."""
        workflow_data = WorkflowData()

        new_value = workflow_data.increment("new_counter", 1)
        assert new_value == 1

    def test_pattern_id_and_scope(self) -> None:
        """Pattern 31 has correct ID and scope."""
        workflow_data = WorkflowData()
        assert workflow_data.pattern_id == 31
        assert workflow_data.scope == DataScope.WORKFLOW


class TestPattern32EnvironmentData:
    """Test Pattern 32: Environment Data - External data sources."""

    def test_environment_variable_provider(self) -> None:
        """Can fetch environment variables."""
        env_data = EnvironmentData()

        # Mock environment variable
        os.environ["TEST_API_KEY"] = "secret-key-123"

        env_data.register_provider("api_key", lambda: os.getenv("TEST_API_KEY"))
        assert env_data.get("api_key") == "secret-key-123"

        # Cleanup
        del os.environ["TEST_API_KEY"]

    def test_custom_provider(self) -> None:
        """Can register custom data providers."""
        env_data = EnvironmentData()

        # Simulate database config provider
        def fetch_db_config() -> dict[str, str]:
            return {"host": "localhost", "port": "5432", "database": "testdb"}

        env_data.register_provider("db_config", fetch_db_config)
        db_config = env_data.get("db_config")

        assert db_config["host"] == "localhost"
        assert db_config["port"] == "5432"

    def test_nonexistent_provider(self) -> None:
        """Getting nonexistent provider returns None."""
        env_data = EnvironmentData()
        assert env_data.get("nonexistent") is None

    def test_provider_error_handling(self) -> None:
        """Provider errors are propagated with clear messages."""
        env_data = EnvironmentData()

        def failing_provider() -> None:
            msg = "External service unavailable"
            raise ConnectionError(msg)

        env_data.register_provider("failing", failing_provider)

        with pytest.raises(RuntimeError, match="Failed to fetch environment data"):
            env_data.get("failing")

    def test_pattern_id_and_scope(self) -> None:
        """Pattern 32 has correct ID and scope."""
        env_data = EnvironmentData()
        assert env_data.pattern_id == 32
        assert env_data.scope == DataScope.ENVIRONMENT


# ============================================================================
# INTERACTION PATTERNS (33-35)
# ============================================================================


class TestPattern33TaskToTaskInteraction:
    """Test Pattern 33: Task-to-Task Data Interaction - Direct data passing."""

    def test_basic_data_transfer(self) -> None:
        """Data is transferred from source to target task."""
        interaction = DataInteractionTaskToTask(
            source_task="urn:task:T1",
            target_task="urn:task:T2",
            mappings={"output_x": "input_x", "output_y": "input_y"},
        )

        source_context = {"output_x": 100, "output_y": 200}
        target_context = interaction.transfer(Graph(), source_context)

        assert target_context["input_x"] == 100
        assert target_context["input_y"] == 200

    def test_partial_mappings(self) -> None:
        """Only mapped variables are transferred."""
        interaction = DataInteractionTaskToTask(
            source_task="T1", target_task="T2", mappings={"price": "total_price"}
        )

        source_context = {"price": 500.0, "quantity": 10}
        target_context = interaction.transfer(Graph(), source_context)

        assert target_context["total_price"] == 500.0
        assert "quantity" not in target_context

    def test_missing_source_variable(self) -> None:
        """Missing source variables are not transferred."""
        interaction = DataInteractionTaskToTask(
            source_task="T1",
            target_task="T2",
            mappings={"var1": "var2", "missing": "also_missing"},
        )

        source_context = {"var1": "value1"}
        target_context = interaction.transfer(Graph(), source_context)

        assert target_context["var2"] == "value1"
        assert "also_missing" not in target_context

    def test_extract_from_graph(self) -> None:
        """Can extract mappings from RDF graph."""
        graph = Graph()
        graph.bind("yawl", YAWL)

        source = URIRef("urn:task:Source")
        target = URIRef("urn:task:Target")

        graph.add((source, YAWL.outputMapping, Literal("price -> total_price")))
        graph.add((source, YAWL.outputMapping, Literal("quantity -> order_qty")))

        interaction = DataInteractionTaskToTask.extract_from_graph(
            graph, source, target
        )

        assert interaction.mappings == {"price": "total_price", "quantity": "order_qty"}

    def test_pattern_id(self) -> None:
        """Pattern 33 has correct ID."""
        interaction = DataInteractionTaskToTask(
            source_task="T1", target_task="T2", mappings={}
        )
        assert interaction.pattern_id == 33


class TestPattern34BlockToSubWorkflowInteraction:
    """Test Pattern 34: Block-to-Sub-Workflow Data Interaction."""

    def test_input_data_transfer(self) -> None:
        """Parent data is transferred to sub-workflow."""
        interaction = DataInteractionBlockToSubWorkflow(
            parent_block="urn:workflow:Main",
            sub_workflow="urn:workflow:CreditCheck",
            input_mappings={"customer_id": "input_customer", "amount": "check_amount"},
            output_mappings={"credit_score": "output_score"},
        )

        parent_context = {"customer_id": "CUST-123", "amount": 5000.0}
        sub_inputs = interaction.transfer_to_sub(parent_context)

        assert sub_inputs["input_customer"] == "CUST-123"
        assert sub_inputs["check_amount"] == 5000.0

    def test_output_data_transfer(self) -> None:
        """Sub-workflow results are transferred back to parent."""
        interaction = DataInteractionBlockToSubWorkflow(
            parent_block="Main",
            sub_workflow="Sub",
            input_mappings={},
            output_mappings={
                "credit_score": "customer_score",
                "approval_status": "approved",
            },
        )

        sub_context = {"credit_score": 750, "approval_status": "APPROVED"}
        parent_updates = interaction.transfer_to_parent(sub_context)

        assert parent_updates["customer_score"] == 750
        assert parent_updates["approved"] == "APPROVED"

    def test_bidirectional_transfer(self) -> None:
        """Can transfer data both ways (parent→sub→parent)."""
        interaction = DataInteractionBlockToSubWorkflow(
            parent_block="Parent",
            sub_workflow="Child",
            input_mappings={"order_id": "process_order"},
            output_mappings={"result": "order_result"},
        )

        # Parent → Sub
        parent_data = {"order_id": "ORD-999"}
        sub_inputs = interaction.transfer_to_sub(parent_data)
        assert sub_inputs["process_order"] == "ORD-999"

        # Sub → Parent
        sub_outputs = {"result": "COMPLETED"}
        parent_updates = interaction.transfer_to_parent(sub_outputs)
        assert parent_updates["order_result"] == "COMPLETED"

    def test_pattern_id(self) -> None:
        """Pattern 34 has correct ID."""
        interaction = DataInteractionBlockToSubWorkflow(
            parent_block="P", sub_workflow="S", input_mappings={}, output_mappings={}
        )
        assert interaction.pattern_id == 34


class TestPattern35CaseToCaseInteraction:
    """Test Pattern 35: Case-to-Case Data Interaction - Inter-instance communication."""

    def test_data_copy_interaction(self) -> None:
        """Data is copied from source case to target case."""
        interaction = DataInteractionCaseToCase(
            source_case="case-001",
            target_case="case-002",
            shared_variables={"order_status": "upstream_status", "amount": "total"},
            interaction_type="data_copy",
        )

        source_context = {"order_status": "APPROVED", "amount": 1500.0}
        target_updates = interaction.transfer(source_context)

        assert target_updates["upstream_status"] == "APPROVED"
        assert target_updates["total"] == 1500.0

    def test_event_based_interaction(self) -> None:
        """Event-based interactions are identified correctly."""
        event_interaction = DataInteractionCaseToCase(
            source_case="C1",
            target_case="C2",
            shared_variables={"event_data": "notification"},
            interaction_type="event",
        )

        assert event_interaction.is_event_based() is True

    def test_signal_based_interaction(self) -> None:
        """Signal-based interactions are identified correctly."""
        signal_interaction = DataInteractionCaseToCase(
            source_case="C1",
            target_case="C2",
            shared_variables={"signal": "trigger"},
            interaction_type="signal",
        )

        assert signal_interaction.is_event_based() is True

    def test_data_copy_not_event_based(self) -> None:
        """Data copy is not event-based."""
        data_copy = DataInteractionCaseToCase(
            source_case="C1",
            target_case="C2",
            shared_variables={"var": "var"},
            interaction_type="data_copy",
        )

        assert data_copy.is_event_based() is False

    def test_pattern_id(self) -> None:
        """Pattern 35 has correct ID."""
        interaction = DataInteractionCaseToCase(
            source_case="C1", target_case="C2", shared_variables={}
        )
        assert interaction.pattern_id == 35


# ============================================================================
# UNIFIED DATA CONTEXT - Integration Tests
# ============================================================================


class TestDataContext:
    """Test unified DataContext integrating all 8 patterns."""

    def test_scope_precedence_resolution(self) -> None:
        """Variables resolved with scope precedence (task > block > case > workflow > env)."""
        context = DataContext()

        case_id = "case-123"
        task = URIRef("urn:task:T1")
        block = URIRef("urn:block:B1")

        # Set variable at all scopes
        context.task_data.set(task, "var", "task_value")
        context.block_data.set(block, "var", "block_value")
        context.case_data.set(case_id, "var", "case_value")
        context.workflow_data.set("var", "workflow_value")

        # Task scope has highest priority
        resolved = context.resolve_variable(case_id, task, block, "var")
        assert resolved == "task_value"

        # Clear task scope → block scope wins
        context.task_data.clear_task(task)
        resolved = context.resolve_variable(case_id, task, block, "var")
        assert resolved == "block_value"

    def test_scope_precedence_without_block(self) -> None:
        """Variables are resolved correctly when no block scope exists."""
        context = DataContext()

        case_id = "case-456"
        task = URIRef("urn:task:T2")

        context.case_data.set(case_id, "var", "case_value")
        context.workflow_data.set("var", "workflow_value")

        # No task or block scope → case scope wins
        resolved = context.resolve_variable(case_id, task, None, "var")
        assert resolved == "case_value"

    def test_environment_fallback(self) -> None:
        """Environment data is used as last resort."""
        context = DataContext()

        case_id = "case-789"
        task = URIRef("urn:task:T3")

        # Only environment data available
        context.env_data.register_provider("api_url", lambda: "https://api.example.com")

        resolved = context.resolve_variable(case_id, task, None, "api_url")
        assert resolved == "https://api.example.com"

    def test_nonexistent_variable_returns_none(self) -> None:
        """Resolving nonexistent variable returns None."""
        context = DataContext()

        case_id = "case-999"
        task = URIRef("urn:task:T4")

        resolved = context.resolve_variable(case_id, task, None, "nonexistent")
        assert resolved is None


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling across all patterns."""

    def test_immutability_enforcement(self) -> None:
        """All pattern classes are frozen (immutable)."""
        task_data = TaskData()
        case_data = CaseData()

        # Cannot directly modify frozen attributes
        with pytest.raises((AttributeError, TypeError)):
            task_data.pattern_id = 999  # type: ignore[misc]

        with pytest.raises((AttributeError, TypeError)):
            case_data.scope = DataScope.WORKFLOW  # type: ignore[misc]

    def test_unicode_variable_names(self) -> None:
        """Support Unicode variable names."""
        case_data = CaseData()

        case_data.set("case-unicode", "変数", "日本語値")
        case_data.set("case-unicode", "переменная", "русский")

        assert case_data.get("case-unicode", "変数") == "日本語値"
        assert case_data.get("case-unicode", "переменная") == "русский"

    def test_very_large_values(self) -> None:
        """Can store very large data structures."""
        workflow_data = WorkflowData()

        large_list = list(range(100000))
        workflow_data.set("large_data", large_list)

        assert len(workflow_data.get("large_data")) == 100000

    def test_circular_reference_handling(self) -> None:
        """Can handle circular references in data structures."""
        case_data = CaseData()

        circular: dict[str, object] = {"name": "root"}
        circular["self"] = circular  # Circular reference

        case_data.set("case-circular", "circular_data", circular)
        retrieved = case_data.get("case-circular", "circular_data")

        assert retrieved["name"] == "root"
        assert retrieved["self"] is retrieved
