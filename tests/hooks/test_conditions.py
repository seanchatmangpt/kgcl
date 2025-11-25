"""
Chicago School TDD Tests for Condition System.

These tests define condition evaluation behaviors without mocking domain objects.
Real condition evaluation with actual SPARQL/SHACL where possible.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest

from kgcl.hooks.conditions import (
    CompositeCondition,
    CompositeOperator,
    Condition,
    ConditionResult,
    DeltaCondition,
    DeltaType,
    ShaclCondition,
    SparqlAskCondition,
    SparqlSelectCondition,
    ThresholdCondition,
    ThresholdOperator,
    WindowAggregation,
    WindowCondition,
)


class TestConditionBase:
    """Test base condition behaviors."""

    def test_condition_base_class_is_abstract(self):
        """Condition base class is abstract."""
        with pytest.raises(TypeError):
            Condition()  # Cannot instantiate abstract class

    @pytest.mark.asyncio
    async def test_condition_returns_condition_result(self):
        """Conditions return ConditionResult with (triggered: bool, metadata: dict)."""

        class SimpleCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=True, metadata={"test": "value"})

        condition = SimpleCondition()
        result = await condition.evaluate({})

        assert isinstance(result, ConditionResult)
        assert result.triggered is True
        assert result.metadata == {"test": "value"}


class TestSparqlConditions:
    """Test SPARQL-based condition behaviors."""

    @pytest.mark.asyncio
    async def test_sparql_ask_condition_evaluates_ask_queries(self):
        """SparqlAskCondition evaluates SPARQL ASK queries."""
        # ASK query that should return true
        ask_query = """
        ASK {
            ?s ?p ?o .
        }
        """

        condition = SparqlAskCondition(query=ask_query)

        # Mock endpoint that returns true
        context = {
            "sparql_endpoint": "http://test.example.org/sparql",
            "test_result": True,  # Simulate ASK true
        }

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert "query" in result.metadata

    @pytest.mark.asyncio
    async def test_sparql_select_condition_evaluates_select_queries(self):
        """SparqlSelectCondition evaluates SPARQL SELECT (returns true if results > 0)."""
        select_query = """
        SELECT ?s WHERE {
            ?s a <http://example.org/Person> .
        }
        """

        condition = SparqlSelectCondition(query=select_query)

        # Context with results
        context = {
            "sparql_endpoint": "http://test.example.org/sparql",
            "test_results": [{"s": "http://example.org/person1"}],
        }

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert "result_count" in result.metadata

    @pytest.mark.asyncio
    async def test_sparql_select_returns_false_when_no_results(self):
        """SparqlSelectCondition returns false when no results."""
        select_query = """
        SELECT ?s WHERE {
            ?s a <http://example.org/NonExistent> .
        }
        """

        condition = SparqlSelectCondition(query=select_query)

        context = {
            "sparql_endpoint": "http://test.example.org/sparql",
            "test_results": [],  # No results
        }

        result = await condition.evaluate(context)

        assert result.triggered is False
        assert result.metadata["result_count"] == 0


class TestShaclCondition:
    """Test SHACL validation condition behaviors."""

    @pytest.mark.asyncio
    async def test_shacl_condition_validates_rdf_against_shapes(self):
        """ShaclCondition validates RDF against SHACL shapes."""
        shapes = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:PersonShape
            a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
            ] .
        """

        condition = ShaclCondition(shapes=shapes)

        # Valid data
        valid_context = {
            "data_graph": """
                @prefix ex: <http://example.org/> .
                ex:person1 a ex:Person ;
                    ex:name "Alice" .
            """
        }

        result = await condition.evaluate(valid_context)

        assert result.triggered is True  # Valid = triggered
        assert "conforms" in result.metadata

    @pytest.mark.asyncio
    async def test_shacl_condition_fails_on_invalid_data(self):
        """ShaclCondition returns false on validation failure."""
        shapes = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:PersonShape
            a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
            ] .
        """

        condition = ShaclCondition(shapes=shapes)

        # Invalid data (missing name)
        invalid_context = {
            "data_graph": """
                @prefix ex: <http://example.org/> .
                ex:person1 a ex:Person .
            """
        }

        result = await condition.evaluate(invalid_context)

        assert result.triggered is False
        assert "violations" in result.metadata


class TestDeltaCondition:
    """Test graph change detection condition behaviors."""

    @pytest.mark.asyncio
    async def test_delta_condition_detects_any_changes(self):
        """DeltaCondition detects graph changes (any/increase/decrease)."""
        condition = DeltaCondition(
            delta_type=DeltaType.ANY, query="SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        )

        context = {"previous_count": 100, "current_count": 110}

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert "delta" in result.metadata

    @pytest.mark.asyncio
    async def test_delta_condition_detects_increase(self):
        """DeltaCondition detects increase in values."""
        condition = DeltaCondition(
            delta_type=DeltaType.INCREASE, query="SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        )

        context = {"previous_count": 100, "current_count": 110}

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert result.metadata["delta"] > 0

    @pytest.mark.asyncio
    async def test_delta_condition_detects_decrease(self):
        """DeltaCondition detects decrease in values."""
        condition = DeltaCondition(
            delta_type=DeltaType.DECREASE, query="SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        )

        context = {"previous_count": 110, "current_count": 100}

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert result.metadata["delta"] < 0


class TestThresholdCondition:
    """Test numeric threshold condition behaviors."""

    @pytest.mark.asyncio
    async def test_threshold_condition_greater_than(self):
        """ThresholdCondition (numeric var op value: e.g., 'count > 5')."""
        condition = ThresholdCondition(
            variable="count", operator=ThresholdOperator.GREATER_THAN, value=5
        )

        context = {"count": 10}
        result = await condition.evaluate(context)

        assert result.triggered is True
        assert result.metadata["actual_value"] == 10

    @pytest.mark.asyncio
    async def test_threshold_condition_less_than(self):
        """ThresholdCondition evaluates less than."""
        condition = ThresholdCondition(
            variable="count", operator=ThresholdOperator.LESS_THAN, value=100
        )

        context = {"count": 50}
        result = await condition.evaluate(context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_threshold_condition_equals(self):
        """ThresholdCondition evaluates equality."""
        condition = ThresholdCondition(
            variable="status_code", operator=ThresholdOperator.EQUALS, value=200
        )

        context = {"status_code": 200}
        result = await condition.evaluate(context)

        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_threshold_condition_not_equals(self):
        """ThresholdCondition evaluates inequality."""
        condition = ThresholdCondition(
            variable="status_code", operator=ThresholdOperator.NOT_EQUALS, value=500
        )

        context = {"status_code": 200}
        result = await condition.evaluate(context)

        assert result.triggered is True


class TestWindowCondition:
    """Test time window aggregation condition behaviors."""

    @pytest.mark.asyncio
    async def test_window_condition_aggregates_sum(self):
        """WindowCondition aggregates values over time (sum, avg, min, max)."""
        condition = WindowCondition(
            variable="requests",
            window_seconds=60,
            aggregation=WindowAggregation.SUM,
            threshold=100,
            operator=ThresholdOperator.GREATER_THAN,
        )

        context = {
            "time_series": [
                {"timestamp": datetime.utcnow() - timedelta(seconds=30), "requests": 40},
                {"timestamp": datetime.utcnow() - timedelta(seconds=15), "requests": 35},
                {"timestamp": datetime.utcnow(), "requests": 30},
            ]
        }

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert result.metadata["aggregated_value"] == 105

    @pytest.mark.asyncio
    async def test_window_condition_aggregates_average(self):
        """WindowCondition computes average over time window."""
        condition = WindowCondition(
            variable="response_time",
            window_seconds=60,
            aggregation=WindowAggregation.AVG,
            threshold=500,
            operator=ThresholdOperator.GREATER_THAN,
        )

        context = {
            "time_series": [
                {"timestamp": datetime.utcnow() - timedelta(seconds=30), "response_time": 600},
                {"timestamp": datetime.utcnow() - timedelta(seconds=15), "response_time": 700},
                {"timestamp": datetime.utcnow(), "response_time": 800},
            ]
        }

        result = await condition.evaluate(context)

        assert result.triggered is True
        assert result.metadata["aggregated_value"] == 700  # Average

    @pytest.mark.asyncio
    async def test_window_condition_aggregates_min_max(self):
        """WindowCondition computes min and max."""
        min_condition = WindowCondition(
            variable="value",
            window_seconds=60,
            aggregation=WindowAggregation.MIN,
            threshold=10,
            operator=ThresholdOperator.GREATER_THAN,
        )

        max_condition = WindowCondition(
            variable="value",
            window_seconds=60,
            aggregation=WindowAggregation.MAX,
            threshold=90,
            operator=ThresholdOperator.GREATER_THAN,
        )

        context = {
            "time_series": [
                {"timestamp": datetime.utcnow() - timedelta(seconds=30), "value": 20},
                {"timestamp": datetime.utcnow() - timedelta(seconds=15), "value": 50},
                {"timestamp": datetime.utcnow(), "value": 100},
            ]
        }

        min_result = await min_condition.evaluate(context)
        max_result = await max_condition.evaluate(context)

        assert min_result.triggered is True
        assert min_result.metadata["aggregated_value"] == 20

        assert max_result.triggered is True
        assert max_result.metadata["aggregated_value"] == 100


class TestConditionTimeout:
    """Test condition timeout behaviors."""

    @pytest.mark.asyncio
    async def test_conditions_support_timeout(self):
        """Conditions support timeout."""

        class SlowCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                await asyncio.sleep(2.0)
                return ConditionResult(triggered=True, metadata={})

        condition = SlowCondition(timeout=0.5)

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await condition.evaluate_with_timeout({})


class TestConditionCaching:
    """Test condition result caching behaviors."""

    @pytest.mark.asyncio
    async def test_conditions_cache_evaluation_results_within_ttl(self):
        """Conditions cache evaluation results within TTL."""

        class CountingCondition(Condition):
            def __init__(self):
                super().__init__(cache_ttl=2.0)
                self.call_count = 0

            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                self.call_count += 1
                return ConditionResult(triggered=True, metadata={"count": self.call_count})

        condition = CountingCondition()

        # First call
        result1 = await condition.evaluate_with_cache({})
        assert result1.metadata["count"] == 1

        # Second call (should be cached)
        result2 = await condition.evaluate_with_cache({})
        assert result2.metadata["count"] == 1  # Same result, not re-evaluated

        # Wait for TTL to expire
        await asyncio.sleep(2.1)

        # Third call (cache expired, re-evaluate)
        result3 = await condition.evaluate_with_cache({})
        assert result3.metadata["count"] == 2


class TestCompositeConditions:
    """Test complex condition composition behaviors."""

    @pytest.mark.asyncio
    async def test_composite_condition_and_operator(self):
        """Complex conditions: AND composition."""

        class TrueCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=True, metadata={})

        class FalseCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=False, metadata={})

        # True AND True = True
        and_true = CompositeCondition(
            operator=CompositeOperator.AND, conditions=[TrueCondition(), TrueCondition()]
        )
        result = await and_true.evaluate({})
        assert result.triggered is True

        # True AND False = False
        and_false = CompositeCondition(
            operator=CompositeOperator.AND, conditions=[TrueCondition(), FalseCondition()]
        )
        result = await and_false.evaluate({})
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_composite_condition_or_operator(self):
        """Complex conditions: OR composition."""

        class TrueCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=True, metadata={})

        class FalseCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=False, metadata={})

        # False OR False = False
        or_false = CompositeCondition(
            operator=CompositeOperator.OR, conditions=[FalseCondition(), FalseCondition()]
        )
        result = await or_false.evaluate({})
        assert result.triggered is False

        # True OR False = True
        or_true = CompositeCondition(
            operator=CompositeOperator.OR, conditions=[TrueCondition(), FalseCondition()]
        )
        result = await or_true.evaluate({})
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_composite_condition_not_operator(self):
        """Complex conditions: NOT composition."""

        class TrueCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=True, metadata={})

        class FalseCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=False, metadata={})

        # NOT True = False
        not_true = CompositeCondition(operator=CompositeOperator.NOT, conditions=[TrueCondition()])
        result = await not_true.evaluate({})
        assert result.triggered is False

        # NOT False = True
        not_false = CompositeCondition(
            operator=CompositeOperator.NOT, conditions=[FalseCondition()]
        )
        result = await not_false.evaluate({})
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_composite_conditions_can_be_nested(self):
        """Composite conditions can be nested: (A AND B) OR (C AND D)."""

        class TrueCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=True, metadata={})

        class FalseCondition(Condition):
            async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
                return ConditionResult(triggered=False, metadata={})

        # (False AND True) OR (True AND True) = False OR True = True
        complex_condition = CompositeCondition(
            operator=CompositeOperator.OR,
            conditions=[
                CompositeCondition(
                    operator=CompositeOperator.AND, conditions=[FalseCondition(), TrueCondition()]
                ),
                CompositeCondition(
                    operator=CompositeOperator.AND, conditions=[TrueCondition(), TrueCondition()]
                ),
            ],
        )

        result = await complex_condition.evaluate({})
        assert result.triggered is True
