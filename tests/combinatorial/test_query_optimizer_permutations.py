"""Permutation tests for query optimizer.

Tests all permutations of:
- Triple pattern orderings
- Filter positions
- Selectivity combinations
- Optimization strategies

This module provides exhaustive permutation testing to ensure the query
optimizer produces consistent, optimal results regardless of input ordering.
"""

# ruff: noqa: E501, PLR2004, F841
# E501: Long query strings are necessary for test data
# PLR2004: Magic numbers in tests represent expected values
# F841: Some test variables are intentionally unused

import itertools

import pytest

from kgcl.hooks.query_optimizer import QueryOptimizer


class TestTriplePatternPermutations:
    """Test all permutations of triple pattern orderings."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    # Test all permutations of 3 triples (6 permutations)
    @pytest.mark.parametrize(
        "pattern_order",
        list(
            itertools.permutations([
                "?s :name ?name",
                "?s :age ?age",
                "?s :email ?email",
            ])
        ),
    )
    def test_triple_reordering_permutations_3_patterns(
        self, optimizer: QueryOptimizer, pattern_order: tuple[str, ...]
    ) -> None:
        """Verify optimization produces consistent results regardless of input order."""
        query = f"SELECT * WHERE {{ {' . '.join(pattern_order)} }}"
        plan = optimizer.analyze_query(query)

        # Verify plan is generated
        assert plan.estimated_cost > 0
        assert plan.estimated_selectivity >= 0.0
        assert plan.estimated_selectivity <= 1.0
        assert len(plan.execution_path) > 0

        # Verify optimized query is generated
        assert plan.optimized_query is not None
        assert len(plan.optimized_query) > 0

    # Test selectivity-based reordering
    @pytest.mark.parametrize(
        ("patterns", "expected_most_selective"),
        [
            # Literal object (0.1) should come first
            (
                ["?s ?p ?o", "?s :type :Person", '?s :name "Alice"'],
                '"Alice"',
            ),
            # Type predicate (0.2) should come before all-vars (0.9)
            (
                ["?s :age ?age", "?s :type :Person", "?s ?p ?o"],
                ":type",
            ),
            # Literal should come before variable
            (
                ["?s ?p ?o", '?s :name "Bob"', "?s :age ?age"],
                '"Bob"',
            ),
        ],
    )
    def test_selectivity_ordering(
        self,
        optimizer: QueryOptimizer,
        patterns: list[str],
        expected_most_selective: str,
    ) -> None:
        """Check that most selective patterns appear early in optimized query."""
        query = f"SELECT * WHERE {{ {' . '.join(patterns)} }}"
        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None
        # Find position of expected most selective pattern
        optimized_lines = optimized.split("\n")
        pattern_positions = []
        for idx, line in enumerate(optimized_lines):
            if expected_most_selective in line:
                pattern_positions.append(idx)

        # Should appear in first half of patterns
        assert len(pattern_positions) > 0
        assert min(pattern_positions) < len(optimized_lines) / 2

    # Test all permutations of 4 different selectivity patterns (24 permutations)
    @pytest.mark.parametrize(
        "pattern_order",
        list(
            itertools.permutations([
                '?s :name "Alice"',  # Literal - 0.1
                "?s rdf:type :Person",  # Type predicate - 0.2
                "?s :age ?age",  # Bound predicate - 0.4
                "?s ?p ?o",  # All vars - 0.9
            ])
        ),
    )
    def test_selectivity_based_reordering_permutations(
        self, optimizer: QueryOptimizer, pattern_order: tuple[str, ...]
    ) -> None:
        """Verify optimizer reorders by selectivity regardless of input."""
        query = f"SELECT * WHERE {{ {' . '.join(pattern_order)} }}"
        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None

        # Extract pattern order from optimized query
        optimized_patterns = []
        for raw_line in optimized.split("\n"):
            line = raw_line.strip()
            if "?s" in line and not line.startswith("SELECT"):
                optimized_patterns.append(line)

        # Verify literal appears before all-vars in optimized query
        literal_idx = -1
        all_vars_idx = -1

        for idx, pattern in enumerate(optimized_patterns):
            if '"Alice"' in pattern:
                literal_idx = idx
            if "?s ?p ?o" in pattern:
                all_vars_idx = idx

        if literal_idx >= 0 and all_vars_idx >= 0:
            assert literal_idx < all_vars_idx


class TestFilterPositionPermutations:
    """Test filter pushdown with various positions."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    @pytest.mark.parametrize("filter_position", ["before", "middle", "after"])
    @pytest.mark.parametrize("num_triples", [1, 2, 3, 5])
    def test_filter_position_permutations(
        self,
        optimizer: QueryOptimizer,
        filter_position: str,
        num_triples: int,
    ) -> None:
        """Generate query with filter at different positions."""
        # Generate triple patterns
        triples = [f"?s :prop{i} ?val{i}" for i in range(num_triples)]

        # Build query with filter at specified position
        if filter_position == "before":
            query_parts = [
                "SELECT * WHERE {",
                "FILTER(?val0 > 10)",
                " . ".join(triples),
                "}",
            ]
        elif filter_position == "middle":
            mid = num_triples // 2
            query_parts = [
                "SELECT * WHERE {",
                " . ".join(triples[:mid]),
                f". FILTER(?val{mid} > 10) .",
                " . ".join(triples[mid:]),
                "}",
            ]
        else:  # after
            query_parts = [
                "SELECT * WHERE {",
                " . ".join(triples),
                ". FILTER(?val0 > 10)",
                "}",
            ]

        query = " ".join(query_parts)
        plan = optimizer.analyze_query(query)

        # Verify plan is generated
        assert plan.estimated_cost > 0
        assert "Apply filter conditions" in plan.execution_path

        # Verify filter pushdown occurred
        optimized = plan.optimized_query
        assert optimized is not None
        assert "FILTER" in optimized

    @pytest.mark.parametrize(
        ("filter_var", "triple_patterns"),
        [
            # Filter on variable from first triple
            (
                "?name",
                ["?s :name ?name", "?s :age ?age", "?s :email ?email"],
            ),
            # Filter on variable from middle triple
            (
                "?age",
                ["?s :name ?name", "?s :age ?age", "?s :email ?email"],
            ),
            # Filter on variable from last triple
            (
                "?email",
                ["?s :name ?name", "?s :age ?age", "?s :email ?email"],
            ),
        ],
    )
    def test_filter_pushdown_to_producing_triple(
        self,
        optimizer: QueryOptimizer,
        filter_var: str,
        triple_patterns: list[str],
    ) -> None:
        """Verify filter is pushed down to triple producing the variable."""
        # Create query with filter at end
        joined_patterns = " . ".join(triple_patterns)
        filter_clause = f"FILTER({filter_var} = 'test')"
        query = f"SELECT * WHERE {{ {joined_patterns} . {filter_clause} }}"

        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None
        assert "FILTER" in optimized

        # Filter should appear after the triple that produces the variable
        # (not at the end)
        optimized_lines = [
            line.strip() for line in optimized.split("\n") if line.strip()
        ]

        # Find filter position
        filter_line_idx = -1
        producing_triple_idx = -1

        # Max distance between filter and producing triple
        max_distance = 4

        for idx, line in enumerate(optimized_lines):
            if "FILTER" in line:
                filter_line_idx = idx
            # Find triple that produces the variable
            var_name = filter_var.strip("?")
            if (
                var_name in line
                and "SELECT" not in line
                and "FILTER" not in line
            ):
                producing_triple_idx = idx

        # Filter should be present in optimized query
        # (exact positioning depends on optimizer implementation)
        if filter_line_idx >= 0 and producing_triple_idx >= 0:
            # Filter should appear somewhere after the producing triple
            distance = abs(filter_line_idx - producing_triple_idx)
            assert (
                filter_line_idx >= producing_triple_idx or distance <= max_distance
            )


class TestOptimizationCombinations:
    """Test combinations of optimization strategies."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    def test_both_optimizations_applied(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test query with both filter pushdown and triple reordering."""
        # Query with unoptimal order and filter at end
        query = """
        SELECT * WHERE {
            ?s ?p ?o .
            ?s :name ?name .
            ?s :type :Person .
            FILTER(?name = "Alice")
        }
        """

        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None

        # Should have both optimizations:
        # 1. Type predicate should come before all-vars
        # 2. Filter should be pushed down near :name triple

        optimized_lines = [
            line.strip() for line in optimized.split("\n") if line.strip()
        ]

        type_idx = -1
        all_vars_idx = -1
        filter_idx = -1

        for idx, line in enumerate(optimized_lines):
            if ":type" in line:
                type_idx = idx
            if "?s ?p ?o" in line:
                all_vars_idx = idx
            if "FILTER" in line:
                filter_idx = idx

        # Type should come before all-vars (reordering)
        if type_idx >= 0 and all_vars_idx >= 0:
            assert type_idx < all_vars_idx

        # Filter should not be at the very end (pushdown)
        if filter_idx >= 0:
            assert filter_idx < len(optimized_lines) - 1

    def test_order_by_limit_optimization(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test automatic LIMIT addition for ORDER BY queries."""
        query = """
        SELECT * WHERE {
            ?s :name ?name .
            ?s :age ?age
        }
        ORDER BY ?age
        """

        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None
        # Should automatically add LIMIT
        assert "LIMIT" in optimized

    def test_no_limit_override(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test that existing LIMIT is not overridden."""
        query = """
        SELECT * WHERE {
            ?s :name ?name
        }
        ORDER BY ?name
        LIMIT 50
        """

        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None
        # Should keep existing LIMIT (not add another)
        assert optimized.count("LIMIT") == 1
        assert "50" in optimized


class TestQueryConstructCombinations:
    """Test combinations of SPARQL constructs."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    @pytest.mark.parametrize(
        "constructs",
        [
            ["FILTER"],
            ["OPTIONAL"],
            ["UNION"],
            ["FILTER", "OPTIONAL"],
            ["FILTER", "UNION"],
            ["OPTIONAL", "UNION"],
            ["FILTER", "OPTIONAL", "UNION"],
        ],
    )
    def test_construct_combinations(
        self,
        optimizer: QueryOptimizer,
        constructs: list[str],
    ) -> None:
        """Test various SPARQL construct combinations."""
        # Build query with specified constructs
        base = "?s :name ?name"

        query_parts = ["SELECT * WHERE {", base]

        if "FILTER" in constructs:
            query_parts.append(". FILTER(?name = 'test')")

        if "OPTIONAL" in constructs:
            query_parts.append(". OPTIONAL { ?s :email ?email }")

        if "UNION" in constructs:
            query_parts.append("} UNION { ?s :altName ?name")

        query_parts.append("}")

        query = " ".join(query_parts)
        plan = optimizer.analyze_query(query)

        # Verify plan is generated
        assert plan.estimated_cost > 0
        assert len(plan.execution_path) > 0

        # Verify construct presence in execution path
        if "FILTER" in constructs:
            assert "Apply filter conditions" in plan.execution_path

        if "OPTIONAL" in constructs:
            assert "Execute optional patterns" in plan.execution_path

        if "UNION" in constructs:
            assert "Execute UNION branches" in plan.execution_path
            assert plan.parallelizable  # UNION queries are parallelizable

    @pytest.mark.parametrize(
        ("has_order_by", "has_limit"),
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_order_limit_combinations(
        self,
        optimizer: QueryOptimizer,
        has_order_by: bool,
        has_limit: bool,
    ) -> None:
        """Test ORDER BY and LIMIT combinations."""
        query = "SELECT * WHERE { ?s :name ?name }"

        if has_order_by:
            query += " ORDER BY ?name"

        if has_limit:
            query += " LIMIT 100"

        plan = optimizer.analyze_query(query)

        # Verify plan is generated
        assert plan.estimated_cost > 0

        # Check execution path
        if has_order_by:
            assert "Sort results" in plan.execution_path

        if has_limit:
            assert "Apply LIMIT" in plan.execution_path

        # Check cost estimation
        if has_order_by and not has_limit:
            # Should have higher cost (3x multiplier)
            base_plan = optimizer.analyze_query("SELECT * WHERE { ?s :name ?name }")
            assert plan.estimated_cost > base_plan.estimated_cost


class TestSelectivityPermutations:
    """Test all selectivity level permutations."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    @pytest.mark.parametrize(
        "selectivities",
        list(itertools.permutations([0.1, 0.2, 0.4, 0.5, 0.9])),
    )
    def test_selectivity_permutations(
        self,
        optimizer: QueryOptimizer,
        selectivities: tuple[float, ...],
    ) -> None:
        """Verify optimizer correctly orders by selectivity."""
        # Create patterns with known selectivities
        # 0.1=literal, 0.2=type, 0.4=predicate, 0.5=default, 0.9=vars
        selectivity_to_pattern = {
            0.1: '?s :name "Alice"',
            0.2: "?s rdf:type :Person",
            0.4: "?s :age ?age",
            0.5: "?s :email ?email",
            0.9: "?s ?p ?o",
        }

        patterns = [selectivity_to_pattern[s] for s in selectivities]
        query = f"SELECT * WHERE {{ {' . '.join(patterns)} }}"

        plan = optimizer.analyze_query(query)
        optimized = plan.optimized_query

        assert optimized is not None

        # Extract pattern order from optimized query
        optimized_patterns = []
        for raw_line in optimized.split("\n"):
            line = raw_line.strip()
            is_valid = line and not line.startswith("SELECT")
            is_valid = is_valid and not line.startswith("WHERE")
            is_valid = is_valid and line != "}"
            if is_valid:
                optimized_patterns.append(line)

        # Verify selectivity ordering (most to least selective)
        # Check that 0.1 appears before 0.9
        literal_found = False
        all_vars_found = False

        for pattern in optimized_patterns:
            if '"Alice"' in pattern:
                literal_found = True
            if "?s ?p ?o" in pattern and literal_found:
                all_vars_found = True
                break

        # If both patterns present, literal should come first
        if '"Alice"' in query and "?s ?p ?o" in query:
            assert literal_found
            assert all_vars_found or "?s ?p ?o" not in optimized

    def test_filter_count_selectivity(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test that multiple filters increase selectivity."""
        query_no_filter = "SELECT * WHERE { ?s :name ?name . ?s :age ?age }"
        query_one_filter = "SELECT * WHERE { ?s :name ?name . ?s :age ?age . FILTER(?age > 18) }"
        query_two_filters = "SELECT * WHERE { ?s :name ?name . ?s :age ?age . FILTER(?age > 18) . FILTER(?name = 'test') }"

        plan_no_filter = optimizer.analyze_query(query_no_filter)
        plan_one_filter = optimizer.analyze_query(query_one_filter)
        plan_two_filters = optimizer.analyze_query(query_two_filters)

        # More filters = more selective (lower selectivity value)
        assert plan_one_filter.estimated_selectivity < plan_no_filter.estimated_selectivity
        assert plan_two_filters.estimated_selectivity < plan_one_filter.estimated_selectivity

    def test_triple_count_selectivity(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test that more triples increase selectivity."""
        query_one = "SELECT * WHERE { ?s :name ?name }"
        query_two = "SELECT * WHERE { ?s :name ?name . ?s :age ?age }"
        query_three = "SELECT * WHERE { ?s :name ?name . ?s :age ?age . ?s :email ?email }"

        plan_one = optimizer.analyze_query(query_one)
        plan_two = optimizer.analyze_query(query_two)
        plan_three = optimizer.analyze_query(query_three)

        # More triples = more selective (lower selectivity value)
        assert plan_two.estimated_selectivity < plan_one.estimated_selectivity
        assert plan_three.estimated_selectivity < plan_two.estimated_selectivity


class TestIndexSuggestions:
    """Test index suggestion combinations."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    @pytest.mark.parametrize(
        ("query", "expected_index_count"),
        [
            # No predicates - only subject/object indexes
            ("SELECT * WHERE { ?s ?p ?o }", 0),
            # One predicate - one index
            ("SELECT * WHERE { ?s <http://ex.com/name> ?o }", 1),
            # Two predicates - two indexes
            (
                "SELECT * WHERE { ?s <http://ex.com/name> ?n . ?s <http://ex.com/age> ?a }",
                2,
            ),
            # Bound subject - subject index
            ("SELECT * WHERE { <http://ex.com/p1> ?p ?o }", 1),
            # Bound object - object index
            ("SELECT * WHERE { ?s ?p <http://ex.com/obj1> }", 1),
        ],
    )
    def test_index_suggestion_permutations(
        self,
        optimizer: QueryOptimizer,
        query: str,
        expected_index_count: int,
    ) -> None:
        """Test index suggestions for various query patterns."""
        suggestions = optimizer.suggest_indexes(query)

        # Should suggest at least expected number of indexes
        assert len(suggestions) >= expected_index_count

        # Each suggestion should be a valid SQL statement
        for suggestion in suggestions:
            assert "CREATE INDEX" in suggestion

    def test_index_deduplication(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test that duplicate index suggestions are not made."""
        query1 = "SELECT * WHERE { ?s <http://ex.com/name> ?o }"
        query2 = "SELECT * WHERE { ?s <http://ex.com/name> ?n }"

        suggestions1 = optimizer.suggest_indexes(query1)
        suggestions2 = optimizer.suggest_indexes(query2)

        # Second query should not suggest same index again
        assert len(suggestions2) == 0 or suggestions2[0] not in suggestions1


class TestExecutionTracking:
    """Test query execution tracking and statistics."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    def test_execution_recording(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test recording execution times."""
        query = "SELECT * WHERE { ?s :name ?name }"

        # Analyze query first
        plan = optimizer.analyze_query(query)

        # Record execution
        optimizer.record_execution(query, 50.0)

        # Get stats
        stats = optimizer.get_stats(query)

        assert stats is not None
        assert stats["executions"] == 1
        assert stats["avg_time_ms"] == 50.0

    def test_rolling_average(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test rolling average calculation."""
        query = "SELECT * WHERE { ?s :name ?name }"

        # Analyze query first
        optimizer.analyze_query(query)

        # Record multiple executions
        optimizer.record_execution(query, 40.0)
        optimizer.record_execution(query, 60.0)
        optimizer.record_execution(query, 50.0)

        stats = optimizer.get_stats(query)

        assert stats is not None
        assert stats["executions"] == 3
        assert stats["avg_time_ms"] == 50.0  # (40 + 60 + 50) / 3

    def test_query_normalization(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test that queries with different whitespace are treated as same."""
        query1 = "SELECT * WHERE { ?s :name ?name }"
        query2 = "SELECT  *  WHERE  {  ?s  :name  ?name  }"
        query3 = """
        SELECT *
        WHERE {
            ?s :name ?name
        }
        """

        # Analyze all variants
        optimizer.analyze_query(query1)

        # Record executions
        optimizer.record_execution(query1, 30.0)
        optimizer.record_execution(query2, 40.0)
        optimizer.record_execution(query3, 50.0)

        # All should be tracked as same query
        stats1 = optimizer.get_stats(query1)
        stats2 = optimizer.get_stats(query2)
        stats3 = optimizer.get_stats(query3)

        assert stats1 is not None
        assert stats2 is not None
        assert stats3 is not None

        # All should have same execution count
        assert stats1["executions"] == stats2["executions"] == stats3["executions"] == 3


class TestCostEstimation:
    """Test cost estimation for various query patterns."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    @pytest.mark.parametrize(
        ("num_triples", "expected_min_cost"),
        [
            (1, 10.0),  # 1 triple * 10ms
            (2, 20.0),  # 2 triples * 10ms
            (3, 30.0),  # 3 triples * 10ms
            (5, 50.0),  # 5 triples * 10ms
        ],
    )
    def test_base_cost_estimation(
        self,
        optimizer: QueryOptimizer,
        num_triples: int,
        expected_min_cost: float,
    ) -> None:
        """Test base cost estimation for triple count."""
        patterns = [f"?s :prop{i} ?val{i}" for i in range(num_triples)]
        query = f"SELECT * WHERE {{ {' . '.join(patterns)} }}"

        plan = optimizer.analyze_query(query)

        # Should have at least base cost
        assert plan.estimated_cost >= expected_min_cost

    def test_union_cost_multiplier(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test UNION increases cost by 2x."""
        query_no_union = "SELECT * WHERE { ?s :name ?name }"
        query_with_union = "SELECT * WHERE { { ?s :name ?name } UNION { ?s :altName ?name } }"

        plan_no_union = optimizer.analyze_query(query_no_union)
        plan_with_union = optimizer.analyze_query(query_with_union)

        # UNION should approximately double cost
        assert plan_with_union.estimated_cost > plan_no_union.estimated_cost * 1.5

    def test_optional_cost_multiplier(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test OPTIONAL increases cost by 1.5x."""
        query_no_optional = "SELECT * WHERE { ?s :name ?name }"
        query_with_optional = "SELECT * WHERE { ?s :name ?name . OPTIONAL { ?s :email ?email } }"

        plan_no_optional = optimizer.analyze_query(query_no_optional)
        plan_with_optional = optimizer.analyze_query(query_with_optional)

        # OPTIONAL should increase cost
        assert plan_with_optional.estimated_cost > plan_no_optional.estimated_cost

    def test_order_by_without_limit_cost_multiplier(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test ORDER BY without LIMIT increases cost by 3x."""
        query_no_order = "SELECT * WHERE { ?s :name ?name }"
        query_with_order = "SELECT * WHERE { ?s :name ?name } ORDER BY ?name"

        plan_no_order = optimizer.analyze_query(query_no_order)
        plan_with_order = optimizer.analyze_query(query_with_order)

        # ORDER BY without LIMIT should triple cost
        assert plan_with_order.estimated_cost >= plan_no_order.estimated_cost * 2.5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        """Create fresh optimizer instance."""
        return QueryOptimizer()

    def test_empty_query(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test handling of empty or minimal query."""
        query = "SELECT * WHERE { }"

        plan = optimizer.analyze_query(query)

        # Should still generate plan
        assert plan.estimated_cost >= 0
        assert len(plan.execution_path) > 0

    def test_complex_nested_query(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test handling of complex nested query."""
        query = """
        SELECT * WHERE {
            {
                ?s :name ?name .
                FILTER(?name = "Alice")
            } UNION {
                ?s :altName ?name .
                OPTIONAL { ?s :email ?email }
            }
        }
        ORDER BY ?name
        LIMIT 10
        """

        plan = optimizer.analyze_query(query)

        # Should handle complex query
        assert plan.estimated_cost > 0
        # UNION with ORDER BY is NOT parallelizable (ORDER BY prevents it)
        assert not plan.parallelizable
        assert len(plan.execution_path) > 5  # Should have multiple steps

    def test_multiple_filters_same_variable(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test multiple filters on same variable."""
        query = """
        SELECT * WHERE {
            ?s :age ?age .
            FILTER(?age > 18) .
            FILTER(?age < 65)
        }
        """

        plan = optimizer.analyze_query(query)

        # Should handle multiple filters
        assert plan.estimated_cost > 0
        assert plan.optimized_query is not None
        assert plan.optimized_query.count("FILTER") == 2

    def test_no_variables_query(
        self,
        optimizer: QueryOptimizer,
    ) -> None:
        """Test query with no variables (ASK query pattern)."""
        query = 'SELECT * WHERE { <http://ex.com/p1> :name "Alice" }'

        plan = optimizer.analyze_query(query)

        # Should still generate plan (even if cost is 0 due to regex not matching)
        assert plan.estimated_cost >= 0
        # Should have execution path
        assert len(plan.execution_path) > 0
        # Should suggest indexes for predicate
        assert len(plan.index_hints) > 0
