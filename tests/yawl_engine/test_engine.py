"""Comprehensive tests for the YAWL (Yet Another Workflow Language) Engine.

Tests verify the 5 YAWL perspectives using London School TDD methodology:
- Data Perspective: XQuery transformations and data mappings
- Resource Perspective: Role-based authorization gates
- Service Perspective: External service interactions
- Exception Perspective: Timeout handling and compensation
- Control Flow: 5 kernel verbs (Transmute, Copy, Filter, Await, Void)

London School TDD: Tests drive design, use mocks for YAWL engine (doesn't exist yet),
but use real Atman components (QuadDelta, TransactionContext, etc.).

Performance targets (from Atman):
- p99 < 100ms per workflow step
- All operations must complete within SLA
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import pytest

from kgcl.engine import GENESIS_HASH, Atman, QuadDelta, TransactionContext

# Performance constants
P99_TARGET_MS: float = 100.0
TIMEOUT_DURATION_MS: int = 5000
SHA256_HEX_LENGTH: int = 64

# Test role constants
ROLE_GENERAL: str = "General"
ROLE_PRIVATE: str = "Private"
ROLE_PRESIDENT: str = "President"


# Mock YAWL Engine Components (London School: Mock what doesn't exist)
class MockYawlTask:
    """Mock YAWL task definition."""

    def __init__(
        self,
        task_id: str,
        verb: str,
        required_role: str | None = None,
        service_uri: str | None = None,
        timeout_ms: int | None = None,
        flows_into: list[str] | None = None,
    ) -> None:
        """Initialize mock YAWL task."""
        self.task_id = task_id
        self.verb = verb
        self.required_role = required_role
        self.service_uri = service_uri
        self.timeout_ms = timeout_ms
        self.flows_into = flows_into or []


class MockYawlEngine:
    """Mock YAWL workflow engine built on Atman."""

    def __init__(self, atman: Atman) -> None:
        """Initialize mock YAWL engine."""
        self.atman = atman
        self.tasks: dict[str, MockYawlTask] = {}
        self.active_tokens: set[str] = set()
        self.completed_tasks: set[str] = set()
        self.voided_tasks: set[str] = set()

    def register_task(self, task: MockYawlTask) -> None:
        """Register a YAWL task."""
        self.tasks[task.task_id] = task

    async def execute_task(
        self,
        task_id: str,
        case_data: dict[str, Any],
        context: TransactionContext | YawlContext,
    ) -> dict[str, Any]:
        """Execute a YAWL task with given context."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Extract role and elapsed from context
        if isinstance(context, YawlContext):
            actor_role = context.role
            simulated_elapsed = context.simulated_elapsed_ms
        else:
            actor_role = "system"
            simulated_elapsed = 0

        # Resource perspective: Check role authorization
        if task.required_role and actor_role != task.required_role:
            return {
                "success": False,
                "error": f"Unauthorized: {actor_role} cannot execute {task_id}",
                "status": "Blocked",
            }

        # Exception perspective: Check timeout
        if task.timeout_ms and simulated_elapsed > task.timeout_ms:
            self.voided_tasks.add(task_id)
            return {
                "success": False,
                "error": f"Timeout: {simulated_elapsed}ms > {task.timeout_ms}ms",
                "status": "Voided",
            }

        # Service perspective: Log external interaction
        service_response = None
        if task.service_uri:
            service_response = f"200 OK from {task.service_uri}"

        # Data perspective: Apply data transformations
        data_updates: dict[str, Any] = {}
        if "input_code" in case_data and task.verb == "Transmute":
            # Simulate XQuery transformation: hash the input
            input_code = case_data["input_code"]
            hashed = hashlib.sha256(input_code.encode()).hexdigest()
            data_updates["hashed_code"] = hashed

        if service_response:
            data_updates["service_response"] = service_response

        # Control flow: Execute verb
        verb_result = await self._execute_verb(task, case_data, context)

        # Mark task completed (unless voided)
        if task_id not in self.voided_tasks:
            self.completed_tasks.add(task_id)

        return {
            "success": True,
            "task_id": task_id,
            "verb": task.verb,
            "data_updates": data_updates,
            "verb_result": verb_result,
            "status": "Completed" if task_id not in self.voided_tasks else "Voided",
        }

    async def _execute_verb(  # noqa: PLR0911  # Verb dispatcher pattern
        self,
        task: MockYawlTask,
        case_data: dict[str, Any],
        context: TransactionContext | YawlContext,
    ) -> dict[str, Any]:
        """Execute YAWL verb (Transmute, Copy, Filter, Await, Void)."""
        if task.verb == "Transmute":
            # Move token to next task
            for next_task_id in task.flows_into:
                self.active_tokens.add(next_task_id)
            return {"next_tasks": task.flows_into}

        if task.verb == "Copy":
            # AND-split: Activate all parallel paths
            for next_task_id in task.flows_into:
                self.active_tokens.add(next_task_id)
            return {"parallel_paths": task.flows_into}

        if task.verb == "Filter":
            # XOR-split: Select single path based on predicate
            predicate = case_data.get("filter_predicate", lambda _: True)
            for next_task_id in task.flows_into:
                if predicate(next_task_id):
                    self.active_tokens.add(next_task_id)
                    return {"selected_path": next_task_id}
            return {"selected_path": None}

        if task.verb == "Await":
            # AND-join: Wait for all inputs
            required_inputs = case_data.get("required_inputs", [])
            all_completed = all(
                task_id in self.completed_tasks for task_id in required_inputs
            )
            if all_completed:
                for next_task_id in task.flows_into:
                    self.active_tokens.add(next_task_id)
                return {"all_inputs_ready": True, "next_tasks": task.flows_into}
            return {"all_inputs_ready": False, "waiting_for": required_inputs}

        if task.verb == "Void":
            # Cancel task and remove token
            self.voided_tasks.add(task.task_id)
            if task.task_id in self.active_tokens:
                self.active_tokens.remove(task.task_id)
            return {"voided": True}

        return {}


# Extended context with role information
class YawlContext:
    """Extended transaction context with YAWL-specific metadata."""

    def __init__(self, base_ctx: TransactionContext, role: str) -> None:
        """Initialize YAWL context."""
        self.base_ctx = base_ctx
        self.role = role
        self.simulated_elapsed_ms = 0


# Fixtures
@pytest.fixture
def atman() -> Atman:
    """Create fresh Atman engine."""
    return Atman()


@pytest.fixture
def yawl_engine(atman: Atman) -> MockYawlEngine:
    """Create YAWL engine with loaded ontology."""
    return MockYawlEngine(atman)


@pytest.fixture
def case_data() -> dict[str, Any]:
    """Standard case data with input_code."""
    return {"input_code": "SECRET_LAUNCH_CODE_123"}


@pytest.fixture
def general_context() -> YawlContext:
    """TransactionContext with General role."""
    base = TransactionContext(prev_hash=GENESIS_HASH, actor="general_user")
    return YawlContext(base, ROLE_GENERAL)


@pytest.fixture
def private_context() -> YawlContext:
    """TransactionContext with Private role."""
    base = TransactionContext(prev_hash=GENESIS_HASH, actor="private_user")
    return YawlContext(base, ROLE_PRIVATE)


# Tests
class TestDataPerspective:
    """Tests for YAWL Data Perspective (XQuery transformations)."""

    @pytest.mark.asyncio
    async def test_transmute_applies_crypto_hash_mapping(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Data mapping transforms input_code -> hashed_code."""
        task = MockYawlTask(
            task_id="hash_transform", verb="Transmute", flows_into=["next_task"]
        )
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("hash_transform", case_data, ctx)

        assert result["success"] is True
        assert "data_updates" in result
        assert "hashed_code" in result["data_updates"]
        # Verify crypto hash is SHA256
        hashed = result["data_updates"]["hashed_code"]
        assert len(hashed) == SHA256_HEX_LENGTH
        assert isinstance(hashed, str)

    @pytest.mark.asyncio
    async def test_data_updates_propagate_through_context(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Data updates from QuadDelta merge into TransactionContext."""
        task = MockYawlTask(task_id="data_task", verb="Transmute")
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("data_task", case_data, ctx)

        # Verify data updates exist and can be propagated
        assert result["success"] is True
        data_updates = result.get("data_updates", {})
        assert isinstance(data_updates, dict)
        # In real YAWL, these would merge into next task's context

    @pytest.mark.asyncio
    async def test_xquery_simulation_handles_missing_input(
        self, yawl_engine: MockYawlEngine
    ) -> None:
        """Missing input_code doesn't crash, returns empty updates."""
        task = MockYawlTask(task_id="missing_input_task", verb="Transmute")
        yawl_engine.register_task(task)

        # Empty case data (no input_code)
        empty_data: dict[str, Any] = {}
        ctx = TransactionContext(prev_hash=GENESIS_HASH)

        result = await yawl_engine.execute_task("missing_input_task", empty_data, ctx)

        assert result["success"] is True
        # Should not crash, just no data updates
        data_updates = result.get("data_updates", {})
        assert "hashed_code" not in data_updates


class TestResourcePerspective:
    """Tests for YAWL Resource Perspective (role-based authorization)."""

    @pytest.mark.asyncio
    async def test_resource_gate_blocks_unauthorized_role(
        self,
        yawl_engine: MockYawlEngine,
        case_data: dict[str, Any],
        private_context: YawlContext,
    ) -> None:
        """Private cannot execute task requiring General role."""
        task = MockYawlTask(
            task_id="authorize_launch", verb="Transmute", required_role=ROLE_GENERAL
        )
        yawl_engine.register_task(task)

        result = await yawl_engine.execute_task(
            "authorize_launch", case_data, private_context
        )

        assert result["success"] is False
        assert "Unauthorized" in result["error"]
        assert result["status"] == "Blocked"

    @pytest.mark.asyncio
    async def test_resource_gate_allows_authorized_role(
        self,
        yawl_engine: MockYawlEngine,
        case_data: dict[str, Any],
        general_context: YawlContext,
    ) -> None:
        """General can execute task requiring General role."""
        task = MockYawlTask(
            task_id="authorize_launch", verb="Transmute", required_role=ROLE_GENERAL
        )
        yawl_engine.register_task(task)

        result = await yawl_engine.execute_task(
            "authorize_launch", case_data, general_context
        )

        assert result["success"] is True
        assert result.get("status") != "Blocked"

    @pytest.mark.asyncio
    async def test_resource_check_with_no_constraint_allows_all(
        self,
        yawl_engine: MockYawlEngine,
        case_data: dict[str, Any],
        private_context: YawlContext,
    ) -> None:
        """Tasks without yawl:hasResourcing allow any actor."""
        task = MockYawlTask(
            task_id="public_task",
            verb="Transmute",
            required_role=None,  # No role constraint
        )
        yawl_engine.register_task(task)

        result = await yawl_engine.execute_task(
            "public_task", case_data, private_context
        )

        assert result["success"] is True


class TestServicePerspective:
    """Tests for YAWL Service Perspective (external interactions)."""

    @pytest.mark.asyncio
    async def test_external_interaction_logs_service_call(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Tasks with yawl:hasExternalInteraction log service URI."""
        service_uri = "https://missile.defense.gov/api/validate"
        task = MockYawlTask(
            task_id="validate_codes", verb="Transmute", service_uri=service_uri
        )
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("validate_codes", case_data, ctx)

        assert result["success"] is True
        # Service interaction should be logged
        data_updates = result.get("data_updates", {})
        assert "service_response" in data_updates

    @pytest.mark.asyncio
    async def test_service_response_stored_in_data_updates(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Service response '200 OK' added to data_updates."""
        service_uri = "https://example.com/api/test"
        task = MockYawlTask(
            task_id="call_service", verb="Transmute", service_uri=service_uri
        )
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("call_service", case_data, ctx)

        data_updates = result.get("data_updates", {})
        assert "service_response" in data_updates
        assert "200 OK" in data_updates["service_response"]


class TestExceptionPerspective:
    """Tests for YAWL Exception Perspective (timeouts and compensation)."""

    @pytest.mark.asyncio
    async def test_timeout_voids_task_when_elapsed_exceeds_duration(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """simulated_elapsed > duration triggers Void verb."""
        task = MockYawlTask(
            task_id="timed_task", verb="Transmute", timeout_ms=TIMEOUT_DURATION_MS
        )
        yawl_engine.register_task(task)

        # Context with elapsed time exceeding timeout
        base_ctx = TransactionContext(prev_hash=GENESIS_HASH)
        ctx = YawlContext(base_ctx, "system")
        ctx.simulated_elapsed_ms = TIMEOUT_DURATION_MS + 1000

        result = await yawl_engine.execute_task("timed_task", case_data, ctx)

        assert result["success"] is False
        assert "Timeout" in result["error"]
        assert result["status"] == "Voided"
        assert "timed_task" in yawl_engine.voided_tasks

    @pytest.mark.asyncio
    async def test_timeout_does_not_void_within_duration(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """simulated_elapsed <= duration continues normally."""
        task = MockYawlTask(
            task_id="timed_task", verb="Transmute", timeout_ms=TIMEOUT_DURATION_MS
        )
        yawl_engine.register_task(task)

        # Context with elapsed time within timeout
        base_ctx = TransactionContext(prev_hash=GENESIS_HASH)
        ctx = YawlContext(base_ctx, "system")
        ctx.simulated_elapsed_ms = TIMEOUT_DURATION_MS - 1000

        result = await yawl_engine.execute_task("timed_task", case_data, ctx)

        assert result["success"] is True
        assert result["status"] == "Completed"
        assert "timed_task" not in yawl_engine.voided_tasks

    @pytest.mark.asyncio
    async def test_voided_task_marked_with_voided_status(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Voided tasks get status 'Voided' not 'Completed'."""
        task = MockYawlTask(task_id="void_task", verb="Void")
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("void_task", case_data, ctx)

        verb_result = result.get("verb_result", {})
        assert verb_result.get("voided") is True
        assert "void_task" in yawl_engine.voided_tasks


class TestKernelVerbs:
    """Tests for YAWL Control Flow (5 Kernel Verbs)."""

    @pytest.mark.asyncio
    async def test_transmute_moves_token_to_next_task(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Transmute advances token via yawl:flowsInto."""
        task = MockYawlTask(task_id="task_a", verb="Transmute", flows_into=["task_b"])
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("task_a", case_data, ctx)

        assert result["success"] is True
        verb_result = result.get("verb_result", {})
        assert "next_tasks" in verb_result
        assert "task_b" in verb_result["next_tasks"]
        assert "task_b" in yawl_engine.active_tokens

    @pytest.mark.asyncio
    async def test_copy_activates_multiple_parallel_paths(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """AND-split activates all outgoing flows."""
        task = MockYawlTask(
            task_id="and_split", verb="Copy", flows_into=["path_1", "path_2", "path_3"]
        )
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("and_split", case_data, ctx)

        assert result["success"] is True
        verb_result = result.get("verb_result", {})
        assert "parallel_paths" in verb_result
        # All paths should be activated
        for path in ["path_1", "path_2", "path_3"]:
            assert path in verb_result["parallel_paths"]
            assert path in yawl_engine.active_tokens

    @pytest.mark.asyncio
    async def test_filter_selects_single_path_based_on_predicate(
        self, yawl_engine: MockYawlEngine
    ) -> None:
        """XOR-split activates only matching flow."""
        task = MockYawlTask(
            task_id="xor_split",
            verb="Filter",
            flows_into=["approved_path", "rejected_path"],
        )
        yawl_engine.register_task(task)

        # Predicate selects "approved_path"
        case_data_with_filter: dict[str, Any] = {
            "filter_predicate": lambda task_id: task_id == "approved_path"
        }

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("xor_split", case_data_with_filter, ctx)

        assert result["success"] is True
        verb_result = result.get("verb_result", {})
        assert verb_result.get("selected_path") == "approved_path"
        # Only one path should be activated
        assert "approved_path" in yawl_engine.active_tokens
        assert "rejected_path" not in yawl_engine.active_tokens

    @pytest.mark.asyncio
    async def test_await_blocks_until_all_inputs_completed(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """AND-join waits for all incoming flows."""
        # First, complete some input tasks
        yawl_engine.completed_tasks.add("input_1")
        # input_2 is NOT completed

        task = MockYawlTask(task_id="and_join", verb="Await", flows_into=["next_task"])
        yawl_engine.register_task(task)

        # Case data specifies required inputs
        case_data_with_inputs: dict[str, Any] = {
            "required_inputs": ["input_1", "input_2"]
        }

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("and_join", case_data_with_inputs, ctx)

        # Should block because input_2 not completed
        verb_result = result.get("verb_result", {})
        assert verb_result.get("all_inputs_ready") is False
        assert "next_task" not in yawl_engine.active_tokens

    @pytest.mark.asyncio
    async def test_await_proceeds_when_all_inputs_ready(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """AND-join proceeds when all inputs completed."""
        # Complete all input tasks
        yawl_engine.completed_tasks.add("input_1")
        yawl_engine.completed_tasks.add("input_2")

        task = MockYawlTask(task_id="and_join", verb="Await", flows_into=["next_task"])
        yawl_engine.register_task(task)

        case_data_with_inputs: dict[str, Any] = {
            "required_inputs": ["input_1", "input_2"]
        }

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("and_join", case_data_with_inputs, ctx)

        verb_result = result.get("verb_result", {})
        assert verb_result.get("all_inputs_ready") is True
        assert "next_task" in yawl_engine.active_tokens

    @pytest.mark.asyncio
    async def test_void_removes_token_on_cancellation(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Void removes Active status, adds Voided status."""
        task = MockYawlTask(task_id="cancel_task", verb="Void")
        yawl_engine.register_task(task)

        # Add task to active tokens first
        yawl_engine.active_tokens.add("cancel_task")
        assert "cancel_task" in yawl_engine.active_tokens

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("cancel_task", case_data, ctx)

        assert result["success"] is True
        verb_result = result.get("verb_result", {})
        assert verb_result.get("voided") is True
        # Token should be removed
        assert "cancel_task" not in yawl_engine.active_tokens
        assert "cancel_task" in yawl_engine.voided_tasks


@pytest.mark.integration
class TestNuclearProtocol:
    """Integration tests for Nuclear Launch Protocol workflow."""

    @pytest.mark.asyncio
    async def test_full_nuclear_launch_protocol_happy_path(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Complete workflow: Start -> Split -> Auth+Validate -> Join -> Launch."""
        # Define workflow tasks
        start = MockYawlTask("start", "Transmute", flows_into=["and_split"])
        and_split = MockYawlTask(
            "and_split", "Copy", flows_into=["authorize", "validate"]
        )
        authorize = MockYawlTask(
            "authorize",
            "Transmute",
            required_role=ROLE_GENERAL,
            flows_into=["and_join"],
        )
        validate = MockYawlTask(
            "validate",
            "Transmute",
            service_uri="https://defense.gov/validate",
            flows_into=["and_join"],
        )
        and_join = MockYawlTask("and_join", "Await", flows_into=["launch"])
        launch = MockYawlTask("launch", "Transmute")

        for task in [start, and_split, authorize, validate, and_join, launch]:
            yawl_engine.register_task(task)

        # Execute workflow with General role
        base_ctx = TransactionContext(prev_hash=GENESIS_HASH)
        general_ctx = YawlContext(base_ctx, ROLE_GENERAL)

        # Step 1: Start
        r1 = await yawl_engine.execute_task("start", case_data, general_ctx)
        assert r1["success"] is True

        # Step 2: AND-split
        r2 = await yawl_engine.execute_task("and_split", case_data, general_ctx)
        assert r2["success"] is True
        assert "authorize" in yawl_engine.active_tokens
        assert "validate" in yawl_engine.active_tokens

        # Step 3a: Authorize
        r3a = await yawl_engine.execute_task("authorize", case_data, general_ctx)
        assert r3a["success"] is True

        # Step 3b: Validate
        r3b = await yawl_engine.execute_task("validate", case_data, general_ctx)
        assert r3b["success"] is True

        # Step 4: AND-join
        join_data = {"required_inputs": ["authorize", "validate"]}
        r4 = await yawl_engine.execute_task("and_join", join_data, general_ctx)
        assert r4["success"] is True
        assert "launch" in yawl_engine.active_tokens

        # Step 5: Launch
        r5 = await yawl_engine.execute_task("launch", case_data, general_ctx)
        assert r5["success"] is True
        assert "launch" in yawl_engine.completed_tasks

    @pytest.mark.asyncio
    async def test_nuclear_protocol_blocked_by_unauthorized_user(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Workflow halts when Private tries to authorize."""
        authorize = MockYawlTask("authorize", "Transmute", required_role=ROLE_GENERAL)
        yawl_engine.register_task(authorize)

        # Private context (not authorized)
        base_ctx = TransactionContext(prev_hash=GENESIS_HASH)
        private_ctx = YawlContext(base_ctx, ROLE_PRIVATE)

        result = await yawl_engine.execute_task("authorize", case_data, private_ctx)

        assert result["success"] is False
        assert "Unauthorized" in result["error"]
        assert "authorize" not in yawl_engine.completed_tasks

    @pytest.mark.asyncio
    async def test_nuclear_protocol_timeout_voids_authorization(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Timeout on Auth task cancels the region."""
        authorize = MockYawlTask(
            "authorize", "Transmute", required_role=ROLE_GENERAL, timeout_ms=5000
        )
        yawl_engine.register_task(authorize)

        # General context with timeout exceeded
        base_ctx = TransactionContext(prev_hash=GENESIS_HASH)
        general_ctx = YawlContext(base_ctx, ROLE_GENERAL)
        general_ctx.simulated_elapsed_ms = 6000

        result = await yawl_engine.execute_task("authorize", case_data, general_ctx)

        assert result["success"] is False
        assert "Timeout" in result["error"]
        assert result["status"] == "Voided"
        assert "authorize" in yawl_engine.voided_tasks


class TestProvenance:
    """Tests for YAWL provenance tracking (Lockchain integration)."""

    @pytest.mark.asyncio
    async def test_merkle_root_chains_transactions(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Each receipt.merkle_root includes prev_hash."""
        # Execute two tasks to create chain
        task1 = MockYawlTask("task_1", "Transmute", flows_into=["task_2"])
        task2 = MockYawlTask("task_2", "Transmute")
        yawl_engine.register_task(task1)
        yawl_engine.register_task(task2)

        # First transaction
        delta1 = QuadDelta(additions=[("urn:task1", "urn:executed", "urn:true")])
        receipt1 = await yawl_engine.atman.apply(delta1, actor="system")

        # Second transaction (prev_hash from first)
        delta2 = QuadDelta(additions=[("urn:task2", "urn:executed", "urn:true")])
        receipt2 = await yawl_engine.atman.apply(delta2, actor="system")

        # Verify chain
        assert receipt1.merkle_root != GENESIS_HASH
        assert receipt2.merkle_root != receipt1.merkle_root
        assert receipt1.committed is True
        assert receipt2.committed is True

    @pytest.mark.asyncio
    async def test_receipts_track_verb_executed(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Receipt metadata tracks which verb was executed."""
        task = MockYawlTask("test_verb", "Copy", flows_into=["a", "b"])
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        result = await yawl_engine.execute_task("test_verb", case_data, ctx)

        # Verify verb is tracked
        assert result["success"] is True
        assert result["verb"] == "Copy"
        # In real YAWL, this would be in Receipt.metadata


@pytest.mark.performance
class TestPerformance:
    """Performance tests against p99 targets."""

    @pytest.mark.asyncio
    async def test_task_execution_latency_p99(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """YAWL task execution completes within p99 target (<100ms)."""
        task = MockYawlTask(
            "perf_test", "Transmute", service_uri="https://fast.example.com"
        )
        yawl_engine.register_task(task)

        ctx = TransactionContext(prev_hash=GENESIS_HASH)

        start = time.perf_counter()
        await yawl_engine.execute_task("perf_test", case_data, ctx)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < P99_TARGET_MS, (
            f"Task took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_workflow_step_latency(
        self, yawl_engine: MockYawlEngine, case_data: dict[str, Any]
    ) -> None:
        """Each workflow step (verb execution) within p99 target."""
        verbs = ["Transmute", "Copy", "Filter", "Await", "Void"]

        for i, verb in enumerate(verbs):
            task = MockYawlTask(f"verb_{verb}", verb, flows_into=[f"next_{i}"])
            yawl_engine.register_task(task)

            ctx = TransactionContext(prev_hash=GENESIS_HASH)

            start = time.perf_counter()
            await yawl_engine.execute_task(f"verb_{verb}", case_data, ctx)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < P99_TARGET_MS, (
                f"{verb} took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"
            )
