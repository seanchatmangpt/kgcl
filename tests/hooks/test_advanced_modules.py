"""
Comprehensive tests for advanced UNRDF modules.

Tests for dark matter optimization, streaming processing, and federation.
"""

from datetime import UTC, datetime

import pytest

from kgcl.hooks.dark_matter import DarkMatterOptimizer, OptimizedPlan
from kgcl.hooks.federation import FederationCoordinator, GossipProtocol, Node, NodeStatus
from kgcl.hooks.streaming import Change, ChangeFeed, ChangeType, StreamProcessor, WindowedStreamProcessor

# ============================================================================
# Dark Matter Optimizer Tests
# ============================================================================


class TestDarkMatterOptimizer:
    """Tests for query optimization."""

    def test_optimizer_initialization(self) -> None:
        """Test optimizer initializes with rules."""
        optimizer = DarkMatterOptimizer()
        assert len(optimizer.optimization_rules) > 0
        assert len(optimizer.cost_model) > 0

    def test_simple_plan_optimization(self) -> None:
        """Test basic query plan optimization."""
        optimizer = DarkMatterOptimizer()

        plan = {
            "steps": [
                {"step_id": 1, "operation": "scan", "cost": 100.0, "cardinality": 1000},
                {"step_id": 2, "operation": "filter", "cost": 10.0, "cardinality": 100, "dependencies": [1]},
                {"step_id": 3, "operation": "project", "cost": 5.0, "cardinality": 100, "dependencies": [2]},
            ]
        }

        result = optimizer.optimize_query_plan(plan)
        assert isinstance(result, OptimizedPlan)
        assert result.original_cost > 0
        assert result.optimized_cost > 0

    def test_filter_pushdown(self) -> None:
        """Test filter pushdown optimization."""
        optimizer = DarkMatterOptimizer()

        steps = [
            {"step_id": 1, "operation": "scan", "cost": 100.0},
            {"step_id": 2, "operation": "join", "cost": 50.0, "dependencies": [1]},
            {"step_id": 3, "operation": "filter", "cost": 10.0, "dependencies": [1], "predicate": "x > 10"},
        ]

        result = optimizer._apply_filter_pushdown(steps)
        # Filter should be applied, might be reordered
        assert "applied" in result

    def test_join_reordering(self) -> None:
        """Test join reordering optimization."""
        optimizer = DarkMatterOptimizer()

        steps = [
            {"step_id": 1, "operation": "join", "cost": 100.0, "cardinality": 10000},
            {"step_id": 2, "operation": "join", "cost": 50.0, "cardinality": 100},
        ]

        result = optimizer._apply_join_reordering(steps)
        assert "applied" in result
        assert "steps" in result

    def test_predicate_elimination(self) -> None:
        """Test redundant predicate elimination."""
        optimizer = DarkMatterOptimizer()

        steps = [
            {"step_id": 1, "operation": "filter", "predicate": "x > 10", "cost": 10.0},
            {"step_id": 2, "operation": "filter", "predicate": "x > 10", "cost": 10.0},  # Duplicate
            {"step_id": 3, "operation": "scan", "cost": 100.0},
        ]

        result = optimizer._apply_predicate_elimination(steps)
        assert result["applied"] is True
        assert len(result["steps"]) < len(steps)

    def test_critical_path_analysis(self) -> None:
        """Test critical path computation."""
        optimizer = DarkMatterOptimizer()

        steps = [
            {"step_id": 1, "operation": "scan", "cost": 10.0, "dependencies": []},
            {"step_id": 2, "operation": "filter", "cost": 5.0, "dependencies": [1]},
            {"step_id": 3, "operation": "join", "cost": 20.0, "dependencies": [2]},
            {"step_id": 4, "operation": "project", "cost": 3.0, "dependencies": [3]},
        ]

        critical_path = optimizer.analyze_critical_path(steps)
        assert len(critical_path) > 0
        # Should include all steps since they're sequential
        assert 1 in critical_path
        assert 4 in critical_path

    def test_parallelization_suggestions(self) -> None:
        """Test parallel execution suggestions."""
        optimizer = DarkMatterOptimizer()

        plan = {
            "steps": [
                {"step_id": 1, "operation": "scan", "cost": 10.0, "dependencies": []},
                {"step_id": 2, "operation": "scan", "cost": 10.0, "dependencies": []},
                {"step_id": 3, "operation": "join", "cost": 20.0, "dependencies": [1, 2]},
            ]
        }

        suggestions = optimizer.suggest_parallelization(plan)
        assert len(suggestions) > 0
        # Steps 1 and 2 should be parallelizable
        assert (1, 2) in suggestions

    def test_speedup_estimation(self) -> None:
        """Test speedup estimation."""
        optimizer = DarkMatterOptimizer()

        plan = {
            "steps": [
                {"step_id": 1, "operation": "scan", "cost": 10.0, "dependencies": []},
                {"step_id": 2, "operation": "scan", "cost": 10.0, "dependencies": []},
                {"step_id": 3, "operation": "join", "cost": 20.0, "dependencies": [1, 2]},
            ]
        }

        speedup = optimizer.estimate_speedup(plan, parallel_degree=4)
        assert speedup >= 1.0  # Should have some speedup
        assert speedup <= 4.0  # Can't exceed parallel degree

    def test_empty_plan_optimization(self) -> None:
        """Test optimization with empty plan."""
        optimizer = DarkMatterOptimizer()

        plan = {"steps": []}
        result = optimizer.optimize_query_plan(plan)
        assert result.original_cost == 0.0
        assert result.optimized_cost == 0.0

    def test_projection_pushdown(self) -> None:
        """Test projection pushdown optimization."""
        optimizer = DarkMatterOptimizer()

        steps = [
            {"step_id": 1, "operation": "scan", "cost": 100.0, "output_columns": ["a", "b", "c"]},
            {"step_id": 2, "operation": "project", "cost": 5.0, "columns": ["a", "b"], "dependencies": [1]},
        ]

        result = optimizer._apply_projection_pushdown(steps)
        assert "applied" in result


# ============================================================================
# Streaming Tests
# ============================================================================


class TestChangeFeed:
    """Tests for change feed."""

    def test_feed_initialization(self) -> None:
        """Test feed initialization."""
        feed = ChangeFeed(max_buffer_size=100)
        assert len(feed.changes) == 0
        assert len(feed.subscribers) == 0

    def test_publish_change(self) -> None:
        """Test publishing changes."""
        feed = ChangeFeed()

        change = Change(
            change_type=ChangeType.ADDED,
            triple=("s1", "p1", "o1"),
            timestamp=datetime.now(UTC).timestamp(),
            source="test",
        )

        feed.publish_change(change)
        assert len(feed.changes) == 1
        assert feed.changes[0] == change

    def test_subscribe_notifications(self) -> None:
        """Test subscriber notifications."""
        feed = ChangeFeed()
        received = []

        def callback(change: Change) -> None:
            received.append(change)

        feed.subscribe(callback)

        change = Change(
            change_type=ChangeType.ADDED,
            triple=("s1", "p1", "o1"),
            timestamp=datetime.now(UTC).timestamp(),
            source="test",
        )

        feed.publish_change(change)
        assert len(received) == 1
        assert received[0] == change

    def test_unsubscribe(self) -> None:
        """Test unsubscribe."""
        feed = ChangeFeed()
        received = []

        def callback(change: Change) -> None:
            received.append(change)

        feed.subscribe(callback)
        assert feed.unsubscribe(callback) is True
        assert feed.unsubscribe(callback) is False  # Already removed

    def test_get_changes_since(self) -> None:
        """Test retrieving changes after timestamp."""
        feed = ChangeFeed()

        ts1 = datetime.now(UTC).timestamp()
        change1 = Change(ChangeType.ADDED, ("s1", "p1", "o1"), ts1, "test")
        feed.publish_change(change1)

        ts2 = ts1 + 1.0
        change2 = Change(ChangeType.ADDED, ("s2", "p2", "o2"), ts2, "test")
        feed.publish_change(change2)

        recent = feed.get_changes_since(ts1 + 0.5)
        assert len(recent) == 1
        assert recent[0] == change2

    def test_get_changes_by_type(self) -> None:
        """Test filtering changes by type."""
        feed = ChangeFeed()

        ts = datetime.now(UTC).timestamp()
        feed.publish_change(Change(ChangeType.ADDED, ("s1", "p1", "o1"), ts, "test"))
        feed.publish_change(Change(ChangeType.REMOVED, ("s2", "p2", "o2"), ts, "test"))
        feed.publish_change(Change(ChangeType.ADDED, ("s3", "p3", "o3"), ts, "test"))

        added = feed.get_changes_by_type(ChangeType.ADDED)
        assert len(added) == 2

    def test_buffer_size_limit(self) -> None:
        """Test buffer size limit enforcement."""
        feed = ChangeFeed(max_buffer_size=10)

        ts = datetime.now(UTC).timestamp()
        for i in range(20):
            change = Change(ChangeType.ADDED, (f"s{i}", "p", "o"), ts, "test")
            feed.publish_change(change)

        assert len(feed.changes) == 10  # Should cap at max_buffer_size

    def test_feed_stats(self) -> None:
        """Test feed statistics."""
        feed = ChangeFeed()

        ts = datetime.now(UTC).timestamp()
        feed.publish_change(Change(ChangeType.ADDED, ("s1", "p1", "o1"), ts, "test"))

        stats = feed.get_stats()
        assert stats["buffer_size"] == 1
        assert stats["total_changes"] == 1
        assert stats["subscriber_count"] == 0


class TestStreamProcessor:
    """Tests for stream processor."""

    def test_processor_initialization(self) -> None:
        """Test processor initialization."""
        processor = StreamProcessor()
        assert len(processor.processors) == 0

    def test_register_processor(self) -> None:
        """Test processor registration."""
        processor = StreamProcessor()
        calls = []

        def test_proc(change: Change) -> None:
            calls.append(change)

        processor.register_processor("test", test_proc)
        assert "test" in processor.processors

    def test_process_change(self) -> None:
        """Test change processing."""
        processor = StreamProcessor()
        results = []

        def test_proc(change: Change) -> str:
            return f"Processed: {change.triple[0]}"

        processor.register_processor("test", test_proc)

        ts = datetime.now(UTC).timestamp()
        change = Change(ChangeType.ADDED, ("s1", "p1", "o1"), ts, "test")

        result = processor.process_change(change)
        assert "test" in result
        assert result["test"] == "Processed: s1"

    def test_process_batch(self) -> None:
        """Test batch processing."""
        processor = StreamProcessor()
        count = [0]

        def counter(change: Change) -> int:
            count[0] += 1
            return count[0]

        processor.register_processor("counter", counter)

        ts = datetime.now(UTC).timestamp()
        changes = [Change(ChangeType.ADDED, (f"s{i}", "p", "o"), ts, "test") for i in range(5)]

        results = processor.process_batch(changes)
        assert len(results) == 5
        assert count[0] == 5

    def test_processor_error_handling(self) -> None:
        """Test processor error handling."""
        processor = StreamProcessor()

        def failing_proc(change: Change) -> None:
            raise ValueError("Test error")

        processor.register_processor("failer", failing_proc)

        ts = datetime.now(UTC).timestamp()
        change = Change(ChangeType.ADDED, ("s1", "p1", "o1"), ts, "test")

        result = processor.process_change(change)
        assert "failer" in result
        assert "error" in result["failer"]

    def test_filter_processor(self) -> None:
        """Test filter processor creation."""
        processor = StreamProcessor()
        filtered = []

        def predicate(change: Change) -> bool:
            return change.change_type == ChangeType.ADDED

        def action(change: Change) -> None:
            filtered.append(change)

        processor.create_filter_processor("filter", predicate, action)

        ts = datetime.now(UTC).timestamp()
        processor.process_change(Change(ChangeType.ADDED, ("s1", "p", "o"), ts, "test"))
        processor.process_change(Change(ChangeType.REMOVED, ("s2", "p", "o"), ts, "test"))

        assert len(filtered) == 1


class TestWindowedStreamProcessor:
    """Tests for windowed stream processor."""

    def test_windowed_initialization(self) -> None:
        """Test windowed processor initialization."""
        processor = WindowedStreamProcessor(window_size_ms=1000)
        assert processor.window_size_ms == 1000

    def test_window_aggregation(self) -> None:
        """Test window aggregation."""
        processor = WindowedStreamProcessor(window_size_ms=100)
        windows = []

        def window_callback(changes: list) -> None:
            windows.append(len(changes))

        processor.register_window_callback(window_callback)

        ts = datetime.now(UTC).timestamp()

        # Add changes in first window
        for i in range(3):
            change = Change(ChangeType.ADDED, (f"s{i}", "p", "o"), ts, "test")
            processor.process_change(change)

        # Trigger new window with later timestamp
        ts2 = ts + 0.2  # 200ms later
        change = Change(ChangeType.ADDED, ("s4", "p", "o"), ts2, "test")
        processor.process_change(change)

        assert len(windows) == 1
        assert windows[0] == 3

    def test_flush_window(self) -> None:
        """Test manual window flushing."""
        processor = WindowedStreamProcessor(window_size_ms=1000)
        windows = []

        processor.register_window_callback(lambda changes: windows.append(len(changes)))

        ts = datetime.now(UTC).timestamp()
        processor.process_change(Change(ChangeType.ADDED, ("s1", "p", "o"), ts, "test"))

        processor.flush_window()
        assert len(windows) == 1


# ============================================================================
# Federation Tests
# ============================================================================


class TestNode:
    """Tests for federation node."""

    def test_node_creation(self) -> None:
        """Test node creation."""
        node = Node(node_id="node1", address="localhost:8001")
        assert node.node_id == "node1"
        assert node.is_healthy is True
        assert node.status == NodeStatus.HEALTHY

    def test_heartbeat_update(self) -> None:
        """Test heartbeat update."""
        node = Node(node_id="node1", address="localhost:8001", is_healthy=False)
        node.status = NodeStatus.FAILED

        ts = datetime.now(UTC).timestamp()
        node.update_heartbeat(ts)

        assert node.last_heartbeat == ts
        assert node.is_healthy is True
        assert node.status == NodeStatus.HEALTHY


class TestFederationCoordinator:
    """Tests for federation coordinator."""

    def test_coordinator_initialization(self) -> None:
        """Test coordinator initialization."""
        coordinator = FederationCoordinator("local1")
        assert coordinator.local_node_id == "local1"
        assert len(coordinator.nodes) == 0

    def test_node_registration(self) -> None:
        """Test node registration."""
        coordinator = FederationCoordinator("local1")

        node = Node(node_id="node1", address="localhost:8001")
        coordinator.register_node(node)

        assert "node1" in coordinator.nodes
        assert coordinator.nodes["node1"] == node

    def test_node_unregistration(self) -> None:
        """Test node unregistration."""
        coordinator = FederationCoordinator("local1")

        node = Node(node_id="node1", address="localhost:8001")
        coordinator.register_node(node)

        assert coordinator.unregister_node("node1") is True
        assert coordinator.unregister_node("node1") is False

    def test_healthy_nodes_filter(self) -> None:
        """Test filtering healthy nodes."""
        coordinator = FederationCoordinator("local1")

        node1 = Node(node_id="node1", address="localhost:8001", is_healthy=True)
        node2 = Node(node_id="node2", address="localhost:8002", is_healthy=False)

        coordinator.register_node(node1)
        coordinator.register_node(node2)

        healthy = coordinator.get_healthy_nodes()
        assert len(healthy) == 1
        assert healthy[0].node_id == "node1"

    def test_heartbeat_checking(self) -> None:
        """Test heartbeat checking."""
        coordinator = FederationCoordinator("local1")

        node = Node(node_id="node1", address="localhost:8001", last_heartbeat=datetime.now(UTC).timestamp())
        coordinator.register_node(node)

        # Recent heartbeat should be valid
        assert coordinator.check_heartbeat("node1", max_age_ms=10000) is True

        # Old heartbeat should fail
        node.last_heartbeat = 0
        assert coordinator.check_heartbeat("node1", max_age_ms=1000) is False
        assert node.is_healthy is False

    @pytest.mark.asyncio
    async def test_replication(self) -> None:
        """Test data replication."""
        coordinator = FederationCoordinator("local1")

        # Register multiple nodes
        for i in range(5):
            node = Node(node_id=f"node{i}", address=f"localhost:800{i}", last_heartbeat=datetime.now(UTC).timestamp())
            coordinator.register_node(node)

        coordinator.replication_config.replication_factor = 3

        triple = ("subject", "predicate", "object")
        result = await coordinator.replicate_change(triple)

        assert isinstance(result.success, bool)
        assert len(result.nodes_confirmed) > 0

    @pytest.mark.asyncio
    async def test_consensus_write(self) -> None:
        """Test consensus write."""
        coordinator = FederationCoordinator("local1")

        # Register nodes
        for i in range(5):
            node = Node(node_id=f"node{i}", address=f"localhost:800{i}", last_heartbeat=datetime.now(UTC).timestamp())
            coordinator.register_node(node)

        triple = ("subject", "predicate", "object")
        result = await coordinator.consensus_write(triple)

        assert isinstance(result, object)
        assert hasattr(result, "success")

    def test_quorum_calculation(self) -> None:
        """Test quorum size calculation."""
        coordinator = FederationCoordinator("local1")

        # Register 5 nodes
        for i in range(5):
            coordinator.register_node(Node(f"node{i}", f"localhost:800{i}"))

        quorum_size = coordinator.get_quorum_size()
        assert quorum_size == 3  # Majority of 5

    def test_quorum_availability(self) -> None:
        """Test quorum availability check."""
        coordinator = FederationCoordinator("local1")

        # Register 5 nodes, 3 healthy
        for i in range(5):
            node = Node(
                f"node{i}", f"localhost:800{i}", is_healthy=(i < 3), last_heartbeat=datetime.now(UTC).timestamp()
            )
            coordinator.register_node(node)

        assert coordinator.has_quorum() is True

        # Mark more nodes unhealthy
        coordinator.mark_node_unhealthy("node1")
        coordinator.mark_node_unhealthy("node2")

        assert coordinator.has_quorum() is False

    def test_cluster_stats(self) -> None:
        """Test cluster statistics."""
        coordinator = FederationCoordinator("local1")

        for i in range(3):
            coordinator.register_node(Node(f"node{i}", f"localhost:800{i}"))

        coordinator.mark_node_unhealthy("node2")

        stats = coordinator.get_cluster_stats()
        assert stats["total_nodes"] == 3
        assert stats["healthy_nodes"] == 2
        assert stats["failed_nodes"] == 1


class TestGossipProtocol:
    """Tests for gossip protocol."""

    def test_gossip_initialization(self) -> None:
        """Test gossip protocol initialization."""
        coordinator = FederationCoordinator("local1")
        gossip = GossipProtocol(coordinator)

        assert gossip.coordinator == coordinator
        assert gossip.gossip_fanout > 0

    @pytest.mark.asyncio
    async def test_gossip_update(self) -> None:
        """Test gossip update dissemination."""
        coordinator = FederationCoordinator("local1")

        # Register nodes
        for i in range(5):
            node = Node(f"node{i}", f"localhost:800{i}", is_healthy=True, last_heartbeat=datetime.now(UTC).timestamp())
            coordinator.register_node(node)

        gossip = GossipProtocol(coordinator)
        gossip.gossip_fanout = 3

        update = {"type": "metadata", "data": "test"}
        notified = await gossip.gossip_update(update)

        assert len(notified) <= gossip.gossip_fanout
        assert len(notified) > 0
