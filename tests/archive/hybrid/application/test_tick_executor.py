"""Tests for TickExecutor - single tick execution logic.

Coverage tests for tick_executor.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pyoxigraph as ox
import pytest

from kgcl.hybrid.application.tick_executor import TickExecutor
from kgcl.hybrid.domain.exceptions import ReasonerError
from kgcl.hybrid.ports.reasoner_port import Reasoner, ReasoningOutput
from kgcl.hybrid.ports.rules_port import RulesProvider
from kgcl.hybrid.ports.store_port import RDFStore


class TestTickExecutorInitialization:
    """Test TickExecutor initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Test TickExecutor accepts store, reasoner, and rules provider."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        executor = TickExecutor(store, reasoner, rules)

        assert executor._store == store
        assert executor._reasoner == reasoner
        assert executor._rules == rules


class TestTickExecutorExecuteTick:
    """Test execute_tick method."""

    def test_executes_full_cycle(self) -> None:
        """Test full tick cycle: export, reason, ingest."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.triple_count.side_effect = [10, 15]  # Before, after
        store.dump.return_value = "@prefix ex: <http://example.org/> ."
        rules.get_rules.return_value = "{ ?x a ex:Task } => { ?x ex:done true } ."
        reasoner.reason.return_value = ReasoningOutput(
            success=True,
            output="@prefix ex: <http://example.org/> . <urn:task:1> ex:done true .",
            error=None,
            duration_ms=5.0,
        )

        executor = TickExecutor(store, reasoner, rules)
        result = executor.execute_tick(1)

        assert result.tick_number == 1
        assert result.delta == 5  # 15 - 10
        assert result.triples_before == 10
        assert result.triples_after == 15
        assert result.duration_ms > 0

    def test_raises_reasoner_error_on_failure(self) -> None:
        """Test ReasonerError raised when reasoning fails."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.triple_count.return_value = 10
        store.dump.return_value = "@prefix ex: <http://example.org/> ."
        rules.get_rules.return_value = "{ ?x a ex:Task } => { ?x ex:done true } ."
        reasoner.reason.return_value = ReasoningOutput(
            success=False, output="", error="Parse error in rules", duration_ms=0.0
        )

        executor = TickExecutor(store, reasoner, rules)

        with pytest.raises(ReasonerError) as exc_info:
            executor.execute_tick(1)

        assert "Parse error in rules" in str(exc_info.value)

    def test_caches_rules_across_ticks(self) -> None:
        """Test rules are cached after first tick."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.triple_count.side_effect = [10, 10, 10, 10]  # Two ticks, before/after each
        store.dump.return_value = "@prefix ex: <http://example.org/> ."
        rules.get_rules.return_value = "{ ?x a ex:Task } => { ?x ex:done true } ."
        reasoner.reason.return_value = ReasoningOutput(
            success=True, output="@prefix ex: <http://example.org/> .", error=None, duration_ms=1.0
        )

        executor = TickExecutor(store, reasoner, rules)
        executor.execute_tick(1)
        executor.execute_tick(2)

        # get_rules should only be called once (cached)
        rules.get_rules.assert_called_once()


class TestTickExecutorGetState:
    """Test _get_state method."""

    def test_uses_dump_trig_if_available(self) -> None:
        """Test TriG format is preferred when available."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.dump_trig = MagicMock(return_value="@prefix ex: <http://example.org/> .")
        store.dump.return_value = "should not be called"

        executor = TickExecutor(store, reasoner, rules)
        state = executor._get_state()

        store.dump_trig.assert_called_once()
        store.dump.assert_not_called()
        assert state == "@prefix ex: <http://example.org/> ."

    def test_falls_back_to_dump(self) -> None:
        """Test falls back to dump() when dump_trig unavailable."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.dump.return_value = "@prefix ex: <http://example.org/> ."

        executor = TickExecutor(store, reasoner, rules)
        state = executor._get_state()

        store.dump.assert_called_once()
        assert state == "@prefix ex: <http://example.org/> ."


class TestTickExecutorLoadDeductions:
    """Test _load_deductions method."""

    def test_uses_load_raw_if_available(self) -> None:
        """Test load_raw is preferred when available."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.load_raw = MagicMock()
        store.load_n3 = MagicMock()

        executor = TickExecutor(store, reasoner, rules)
        output = "@prefix ex: <http://example.org/> . <urn:task:1> ex:done true ."
        executor._load_deductions(output)

        store.load_raw.assert_called_once_with(output.encode("utf-8"), ox.RdfFormat.N3)
        store.load_n3.assert_not_called()

    def test_falls_back_to_load_n3(self) -> None:
        """Test falls back to load_n3 when load_raw unavailable."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.load_n3 = MagicMock()

        executor = TickExecutor(store, reasoner, rules)
        output = "@prefix ex: <http://example.org/> . <urn:task:1> ex:done true ."
        executor._load_deductions(output)

        store.load_n3.assert_called_once_with(output)


class TestTickExecutorEdgeCases:
    """Test edge cases for TickExecutor."""

    def test_zero_delta_when_no_changes(self) -> None:
        """Test delta is zero when reasoning produces no new triples."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.triple_count.return_value = 10  # Same before and after
        store.dump.return_value = "@prefix ex: <http://example.org/> ."
        rules.get_rules.return_value = "{ ?x a ex:Task } => { ?x ex:done true } ."
        reasoner.reason.return_value = ReasoningOutput(success=True, output="", error=None, duration_ms=2.0)

        executor = TickExecutor(store, reasoner, rules)
        result = executor.execute_tick(1)

        assert result.delta == 0

    def test_reasoner_error_without_message(self) -> None:
        """Test ReasonerError with None error message."""
        store = MagicMock(spec=RDFStore)
        reasoner = MagicMock(spec=Reasoner)
        rules = MagicMock(spec=RulesProvider)

        store.triple_count.return_value = 10
        store.dump.return_value = "@prefix ex: <http://example.org/> ."
        rules.get_rules.return_value = "{ ?x a ex:Task } => { ?x ex:done true } ."
        reasoner.reason.return_value = ReasoningOutput(success=False, output="", error=None, duration_ms=0.0)

        executor = TickExecutor(store, reasoner, rules)

        with pytest.raises(ReasonerError) as exc_info:
            executor.execute_tick(1)

        assert "Unknown reasoning error" in str(exc_info.value)
