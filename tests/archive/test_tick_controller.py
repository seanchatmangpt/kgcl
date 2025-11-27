"""Tests for tick controller."""

from dataclasses import dataclass
from typing import Any

import pytest
from rdflib import Graph, Namespace, URIRef

from kgcl.hybrid.tick_controller import DebugHook, ProvenanceHook, TickController, TickHook, TickPhase, TickResult

# Test namespace
EX = Namespace("http://example.org/")


@dataclass
class MockRule:
    """Mock rule for testing."""

    id: str
    changes: int

    def execute(self, graph: Graph) -> int:
        """Execute mock rule."""
        if self.changes > 0:
            # Add dummy triples
            for i in range(self.changes):
                graph.add((EX[f"s{i}"], EX.p, EX[f"o{i}"]))
        return self.changes


@dataclass
class MockEngine:
    """Mock hybrid engine for testing."""

    graph: Graph
    rules: list[MockRule]


def test_tick_phase_enum() -> None:
    """Test TickPhase enum has required values."""
    assert TickPhase.PRE_TICK
    assert TickPhase.APPLY_RULES
    assert TickPhase.POST_TICK
    assert len(list(TickPhase)) == 3


def test_tick_result_creation() -> None:
    """Test TickResult dataclass creation."""
    result = TickResult(
        tick_number=1, rules_fired=3, triples_added=10, triples_removed=2, duration_ms=15.5, converged=False
    )

    assert result.tick_number == 1
    assert result.rules_fired == 3
    assert result.triples_added == 10
    assert result.triples_removed == 2
    assert result.duration_ms == 15.5
    assert not result.converged
    assert result.metadata == {}


def test_tick_result_with_metadata() -> None:
    """Test TickResult with custom metadata."""
    metadata = {"custom": "value", "count": 42}
    result = TickResult(
        tick_number=1,
        rules_fired=0,
        triples_added=0,
        triples_removed=0,
        duration_ms=0.0,
        converged=True,
        metadata=metadata,
    )

    assert result.metadata == metadata
    assert result.metadata["custom"] == "value"


def test_tick_controller_initialization() -> None:
    """Test TickController initialization."""
    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    assert controller.tick_count == 0
    assert controller.total_rules_fired == 0


def test_tick_controller_register_hook() -> None:
    """Test hook registration."""
    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    hook = ProvenanceHook()
    controller.register_hook(hook)

    # Verify hook is registered (internal state check)
    assert len(controller._hooks) == 1
    assert controller._hooks[0] is hook


def test_execute_tick_no_rules() -> None:
    """Test tick execution with no rules."""
    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    result = controller.execute_tick()

    assert result.tick_number == 1
    assert result.rules_fired == 0
    assert result.triples_added == 0
    assert result.triples_removed == 0
    assert result.converged is True
    assert result.duration_ms >= 0
    assert controller.tick_count == 1


def test_execute_tick_with_rules() -> None:
    """Test tick execution with rules that fire."""
    graph = Graph()

    @dataclass
    class UniqueRule:
        """Mock rule that adds unique triples."""

        id: str
        changes: int
        offset: int = 0

        def execute(self, graph: Graph) -> int:
            """Execute mock rule with unique triples."""
            if self.changes > 0:
                for i in range(self.changes):
                    idx = i + self.offset
                    graph.add((EX[f"s{idx}"], EX.p, EX[f"o{idx}"]))
            return self.changes

    rules = [UniqueRule(id="rule1", changes=3, offset=0), UniqueRule(id="rule2", changes=2, offset=3)]
    engine = MockEngine(graph=graph, rules=rules)
    controller = TickController(engine)

    result = controller.execute_tick()

    assert result.tick_number == 1
    assert result.rules_fired == 2
    assert result.triples_added == 5
    assert result.triples_removed == 0
    assert result.converged is False
    assert len(graph) == 5


def test_execute_tick_convergence() -> None:
    """Test tick execution reaches convergence."""
    graph = Graph()
    rules = [MockRule(id="rule1", changes=0)]
    engine = MockEngine(graph=graph, rules=rules)
    controller = TickController(engine)

    result = controller.execute_tick()

    assert result.rules_fired == 0
    assert result.converged is True


def test_execute_multiple_ticks() -> None:
    """Test multiple tick executions increment counter."""
    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    result1 = controller.execute_tick()
    result2 = controller.execute_tick()
    result3 = controller.execute_tick()

    assert result1.tick_number == 1
    assert result2.tick_number == 2
    assert result3.tick_number == 3
    assert controller.tick_count == 3


def test_should_continue_not_converged() -> None:
    """Test should_continue returns True when not converged."""
    result = TickResult(
        tick_number=1, rules_fired=5, triples_added=10, triples_removed=0, duration_ms=10.0, converged=False
    )

    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    assert controller.should_continue(result) is True


def test_should_continue_converged() -> None:
    """Test should_continue returns False when converged."""
    result = TickResult(
        tick_number=1, rules_fired=0, triples_added=0, triples_removed=0, duration_ms=5.0, converged=True
    )

    engine = MockEngine(graph=Graph(), rules=[])
    controller = TickController(engine)

    assert controller.should_continue(result) is False


def test_total_rules_fired_accumulation() -> None:
    """Test total_rules_fired accumulates across ticks."""
    graph = Graph()
    rules = [MockRule(id="rule1", changes=1)]
    engine = MockEngine(graph=graph, rules=rules)
    controller = TickController(engine)

    controller.execute_tick()  # 1 rule fired
    assert controller.total_rules_fired == 1

    controller.execute_tick()  # 1 more rule fired
    assert controller.total_rules_fired == 2


class TestProvenanceHook:
    """Tests for ProvenanceHook."""

    def test_initialization(self) -> None:
        """Test ProvenanceHook initialization."""
        hook = ProvenanceHook()

        assert hook.get_history() == []
        assert hook.get_rule_counts() == {}

    def test_on_pre_tick_always_returns_true(self) -> None:
        """Test on_pre_tick validation always succeeds."""
        hook = ProvenanceHook()
        engine = MockEngine(graph=Graph(), rules=[])

        assert hook.on_pre_tick(engine, 1) is True
        assert hook.on_pre_tick(engine, 2) is True

    def test_on_rule_fired_records_count(self) -> None:
        """Test on_rule_fired records rule firing counts."""
        hook = ProvenanceHook()
        engine = MockEngine(graph=Graph(), rules=[])
        rule1 = MockRule(id="rule1", changes=1)
        rule2 = MockRule(id="rule2", changes=1)

        hook.on_rule_fired(engine, rule1, 1)
        hook.on_rule_fired(engine, rule1, 1)
        hook.on_rule_fired(engine, rule2, 1)

        counts = hook.get_rule_counts()
        assert counts["rule1"] == 2
        assert counts["rule2"] == 1

    def test_on_post_tick_records_history(self) -> None:
        """Test on_post_tick records tick history."""
        hook = ProvenanceHook()
        engine = MockEngine(graph=Graph(), rules=[])

        result = TickResult(
            tick_number=1, rules_fired=3, triples_added=5, triples_removed=0, duration_ms=12.5, converged=False
        )

        hook.on_post_tick(engine, result)

        history = hook.get_history()
        assert len(history) == 1
        assert history[0].tick_number == 1
        assert history[0].rules_fired == 3
        assert history[0].duration_ms == 12.5
        assert history[0].timestamp > 0

    def test_compute_statistics_empty(self) -> None:
        """Test compute_statistics with no history."""
        hook = ProvenanceHook()

        stats = hook.compute_statistics()

        assert stats["total_ticks"] == 0
        assert stats["total_rules_fired"] == 0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["avg_rules_per_tick"] == 0.0
        assert stats["most_fired_rule"] is None

    def test_compute_statistics_with_data(self) -> None:
        """Test compute_statistics with tick history."""
        hook = ProvenanceHook()
        engine = MockEngine(graph=Graph(), rules=[])

        # Record some ticks
        result1 = TickResult(
            tick_number=1, rules_fired=3, triples_added=5, triples_removed=0, duration_ms=10.0, converged=False
        )
        result2 = TickResult(
            tick_number=2, rules_fired=1, triples_added=2, triples_removed=0, duration_ms=5.0, converged=False
        )

        hook.on_post_tick(engine, result1)
        hook.on_post_tick(engine, result2)

        # Record rule firings
        rule1 = MockRule(id="rule1", changes=1)
        rule2 = MockRule(id="rule2", changes=1)
        hook.on_rule_fired(engine, rule1, 1)
        hook.on_rule_fired(engine, rule1, 1)
        hook.on_rule_fired(engine, rule1, 1)
        hook.on_rule_fired(engine, rule2, 2)

        stats = hook.compute_statistics()

        assert stats["total_ticks"] == 2
        assert stats["total_rules_fired"] == 4
        assert stats["avg_duration_ms"] == 7.5
        assert stats["avg_rules_per_tick"] == 2.0
        assert stats["most_fired_rule"] == "rule1"
        assert stats["most_fired_count"] == 3


class TestDebugHook:
    """Tests for DebugHook."""

    def test_initialization_default(self) -> None:
        """Test DebugHook initialization with defaults."""
        hook = DebugHook()

        assert hook._log_fn is not None
        assert hook._verbose is False

    def test_initialization_custom_log(self) -> None:
        """Test DebugHook initialization with custom logger."""
        logs: list[str] = []

        def custom_log(msg: str) -> None:
            logs.append(msg)

        hook = DebugHook(log_fn=custom_log, verbose=True)

        assert hook._log_fn is custom_log
        assert hook._verbose is True

    def test_on_pre_tick_logs_state(self) -> None:
        """Test on_pre_tick logs graph state."""
        logs: list[str] = []

        def capture_log(msg: str) -> None:
            logs.append(msg)

        hook = DebugHook(log_fn=capture_log)
        graph = Graph()
        graph.add((EX.s, EX.p, EX.o))
        engine = MockEngine(graph=graph, rules=[])

        result = hook.on_pre_tick(engine, 1)

        assert result is True
        assert len(logs) == 1
        assert "[TICK 1] PRE: Graph size = 1" in logs[0]

    def test_on_pre_tick_verbose_logs_graph(self) -> None:
        """Test on_pre_tick in verbose mode logs graph preview."""
        logs: list[str] = []

        def capture_log(msg: str) -> None:
            logs.append(msg)

        hook = DebugHook(log_fn=capture_log, verbose=True)
        graph = Graph()
        graph.add((EX.s, EX.p, EX.o))
        engine = MockEngine(graph=graph, rules=[])

        hook.on_pre_tick(engine, 1)

        assert len(logs) >= 2
        assert any("[TICK 1] Graph preview:" in log for log in logs)

    def test_on_rule_fired_logs_rule(self) -> None:
        """Test on_rule_fired logs rule firing."""
        logs: list[str] = []

        def capture_log(msg: str) -> None:
            logs.append(msg)

        hook = DebugHook(log_fn=capture_log)
        engine = MockEngine(graph=Graph(), rules=[])
        rule = MockRule(id="test_rule", changes=1)

        hook.on_rule_fired(engine, rule, 1)

        assert len(logs) == 1
        assert "[TICK 1] RULE FIRED: test_rule" in logs[0]

    def test_on_post_tick_logs_results(self) -> None:
        """Test on_post_tick logs execution results."""
        logs: list[str] = []

        def capture_log(msg: str) -> None:
            logs.append(msg)

        hook = DebugHook(log_fn=capture_log)
        engine = MockEngine(graph=Graph(), rules=[])

        result = TickResult(
            tick_number=1, rules_fired=3, triples_added=10, triples_removed=2, duration_ms=15.5, converged=False
        )

        hook.on_post_tick(engine, result)

        assert len(logs) == 1
        log = logs[0]
        assert "[TICK 1] POST:" in log
        assert "rules_fired=3" in log
        assert "added=10" in log
        assert "removed=2" in log
        assert "duration=15.50ms" in log
        assert "converged=False" in log


class TestTickControllerWithHooks:
    """Integration tests for TickController with hooks."""

    def test_hooks_called_in_order(self) -> None:
        """Test hooks are called in correct order."""
        call_log: list[str] = []

        class OrderTrackingHook:
            def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
                call_log.append(f"pre_{tick_number}")
                return True

            def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
                call_log.append(f"rule_{rule.id}")

            def on_post_tick(self, engine: Any, result: TickResult) -> None:
                call_log.append(f"post_{result.tick_number}")

        graph = Graph()
        rules = [MockRule(id="rule1", changes=1)]
        engine = MockEngine(graph=graph, rules=rules)
        controller = TickController(engine)

        hook = OrderTrackingHook()
        controller.register_hook(hook)

        controller.execute_tick()

        assert call_log == ["pre_1", "rule_rule1", "post_1"]

    def test_pre_tick_failure_raises_error(self) -> None:
        """Test pre-tick validation failure raises RuntimeError."""

        class FailingHook:
            def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
                return False

            def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
                # Not called because pre_tick fails
                return None

            def on_post_tick(self, engine: Any, result: TickResult) -> None:
                # Not called because pre_tick fails
                return None

        engine = MockEngine(graph=Graph(), rules=[])
        controller = TickController(engine)
        controller.register_hook(FailingHook())

        with pytest.raises(RuntimeError, match="Pre-tick validation failed"):
            controller.execute_tick()

    def test_multiple_hooks_all_called(self) -> None:
        """Test multiple hooks all receive callbacks."""
        hook1 = ProvenanceHook()
        hook2 = ProvenanceHook()

        graph = Graph()
        rules = [MockRule(id="rule1", changes=1)]
        engine = MockEngine(graph=graph, rules=rules)
        controller = TickController(engine)

        controller.register_hook(hook1)
        controller.register_hook(hook2)

        result = controller.execute_tick()

        # Both hooks should have recorded the tick
        assert len(hook1.get_history()) == 1
        assert len(hook2.get_history()) == 1
        assert hook1.get_rule_counts()["rule1"] == 1
        assert hook2.get_rule_counts()["rule1"] == 1

    def test_complete_workflow(self) -> None:
        """Test complete tick workflow with provenance and debug hooks."""
        logs: list[str] = []

        def capture_log(msg: str) -> None:
            logs.append(msg)

        @dataclass
        class UniqueWorkflowRule:
            """Mock rule that adds unique triples."""

            id: str
            changes: int
            offset: int = 0

            def execute(self, graph: Graph) -> int:
                """Execute mock rule with unique triples."""
                if self.changes > 0:
                    for i in range(self.changes):
                        idx = i + self.offset
                        graph.add((EX[f"s{idx}"], EX.p, EX[f"o{idx}"]))
                return self.changes

        graph = Graph()
        rules = [
            UniqueWorkflowRule(id="rule1", changes=2, offset=0),
            UniqueWorkflowRule(id="rule2", changes=1, offset=2),
        ]
        engine = MockEngine(graph=graph, rules=rules)
        controller = TickController(engine)

        provenance = ProvenanceHook()
        debug = DebugHook(log_fn=capture_log)

        controller.register_hook(provenance)
        controller.register_hook(debug)

        result = controller.execute_tick()

        # Verify result
        assert result.tick_number == 1
        assert result.rules_fired == 2
        assert result.triples_added == 3

        # Verify provenance
        history = provenance.get_history()
        assert len(history) == 1
        counts = provenance.get_rule_counts()
        assert counts["rule1"] == 1
        assert counts["rule2"] == 1

        # Verify debug logs
        assert len(logs) >= 4  # pre, rule1, rule2, post
        assert any("PRE:" in log for log in logs)
        assert any("RULE FIRED: rule1" in log for log in logs)
        assert any("RULE FIRED: rule2" in log for log in logs)
        assert any("POST:" in log for log in logs)
