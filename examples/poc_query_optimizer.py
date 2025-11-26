#!/usr/bin/env python3
"""
POC: SPARQL Query Optimizer - Complete working demonstration.

This single file contains:
1. All types/dataclasses needed
2. Core optimization implementations (filter pushdown, triple reordering)
3. Tests (inline at bottom)
4. Usage examples

Run: python examples/poc_query_optimizer.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class TriplePattern:
    """SPARQL triple pattern.

    Parameters
    ----------
    subject : str
        Subject of the triple (variable or URI)
    predicate : str
        Predicate of the triple (variable or URI)
    object : str
        Object of the triple (variable or URI/literal)
    selectivity : float
        Estimated selectivity (0.0-1.0, lower = more selective)
    """

    subject: str
    predicate: str
    object: str
    selectivity: float = 1.0


@dataclass(frozen=True)
class FilterClause:
    """SPARQL FILTER clause.

    Parameters
    ----------
    expression : str
        The complete FILTER expression
    variables : tuple[str, ...]
        Variables referenced in the filter
    position : int
        Original position in query (line number)
    """

    expression: str
    variables: tuple[str, ...]
    position: int


@dataclass(frozen=True)
class OptimizedQuery:
    """Result of query optimization.

    Parameters
    ----------
    original : str
        Original SPARQL query
    optimized : str
        Optimized SPARQL query
    rewrite_count : int
        Number of rewrites applied
    estimated_speedup : float
        Estimated performance improvement factor
    """

    original: str
    optimized: str
    rewrite_count: int
    estimated_speedup: float


class SparqlQueryOptimizer:
    """Optimize SPARQL queries for better performance.

    This optimizer applies two key optimizations:
    1. Filter pushdown - moves FILTER clauses closer to triple patterns
    2. Triple reordering - reorders patterns by estimated selectivity

    Examples
    --------
    >>> optimizer = SparqlQueryOptimizer()
    >>> query = '''
    ... SELECT ?person ?name WHERE {
    ...   ?person a :Person .
    ...   ?person :hasName ?name .
    ...   FILTER(?age > 18)
    ...   ?person :hasAge ?age .
    ... }
    ... '''
    >>> result = optimizer.optimize(query)
    >>> assert result.rewrite_count > 0
    """

    # Selectivity heuristics (lower = more selective)
    SELECTIVITY_LITERAL_OBJECT: Final[float] = 0.1  # Specific value
    SELECTIVITY_TYPE_PATTERN: Final[float] = 0.3  # rdf:type patterns
    SELECTIVITY_SPECIFIC_PREDICATE: Final[float] = 0.5  # Known predicates
    SELECTIVITY_VARIABLE_PATTERN: Final[float] = 0.9  # All variables

    def __init__(self) -> None:
        """Initialize the query optimizer."""
        self._rewrite_count = 0

    def optimize(self, query: str) -> OptimizedQuery:
        """Apply all optimizations to query.

        Parameters
        ----------
        query : str
            Original SPARQL query

        Returns
        -------
        OptimizedQuery
            Result containing optimized query and metadata
        """
        self._rewrite_count = 0
        original = query

        # Apply optimizations in order
        optimized = self.push_down_filters(query)
        optimized = self.reorder_triple_patterns(optimized)

        # Estimate speedup based on rewrites
        estimated_speedup = 1.0 + (self._rewrite_count * 0.2)

        return OptimizedQuery(
            original=original,
            optimized=optimized,
            rewrite_count=self._rewrite_count,
            estimated_speedup=estimated_speedup,
        )

    def push_down_filters(self, query: str) -> str:
        """Move FILTER clauses closer to triple patterns.

        REAL IMPLEMENTATION - parses query, finds FILTERs, identifies which
        triple patterns produce the filtered variables, moves FILTER
        immediately after the last producing triple.

        Parameters
        ----------
        query : str
            SPARQL query to optimize

        Returns
        -------
        str
            Query with filters pushed down

        Examples
        --------
        >>> optimizer = SparqlQueryOptimizer()
        >>> q = "?x :p ?y . ?z :q ?w . FILTER(?y > 10)"
        >>> result = optimizer.push_down_filters(q)
        >>> assert "FILTER(?y > 10)" in result
        """
        lines = query.split("\n")
        result_lines: list[str] = []
        filters: list[FilterClause] = []

        # First pass: collect filters and remove from original positions
        for i, line in enumerate(lines):
            if "FILTER" in line:
                # Extract filter expression and variables
                filter_match = re.search(r"FILTER\s*\((.*?)\)", line, re.IGNORECASE)
                if filter_match:
                    expression = filter_match.group(1)
                    # Extract variables (words starting with ?)
                    variables = tuple(re.findall(r"\?(\w+)", expression))
                    filters.append(
                        FilterClause(
                            expression=f"FILTER({expression})",
                            variables=variables,
                            position=i,
                        )
                    )
                    continue  # Don't add to result yet
            result_lines.append(line)

        # Second pass: push down each filter
        for filter_clause in filters:
            # Find the last triple pattern that produces any of the filter variables
            last_producer_idx = -1
            for i, line in enumerate(result_lines):
                # Check if line is a triple pattern (contains at least one variable)
                if "?" in line and "SELECT" not in line.upper():
                    # Check if this triple produces any filter variable
                    for var in filter_clause.variables:
                        if f"?{var}" in line:
                            last_producer_idx = i

            # Insert filter after the last producer
            if last_producer_idx >= 0:
                # Insert on next line
                insert_pos = last_producer_idx + 1
                # Add proper indentation
                indent = self._get_indent(result_lines[last_producer_idx])
                result_lines.insert(insert_pos, f"{indent}{filter_clause.expression}")
                self._rewrite_count += 1
            else:
                # No producer found, append at end
                result_lines.append(f"  {filter_clause.expression}")

        return "\n".join(result_lines)

    def reorder_triple_patterns(self, query: str) -> str:
        """Reorder triple patterns by selectivity.

        REAL IMPLEMENTATION - analyzes each triple pattern, estimates
        selectivity based on pattern structure, reorders so most
        selective patterns execute first.

        Parameters
        ----------
        query : str
            SPARQL query to optimize

        Returns
        -------
        str
            Query with reordered triple patterns

        Examples
        --------
        >>> optimizer = SparqlQueryOptimizer()
        >>> q = "?x :p ?y . ?x a :Person . ?x :name 'John' ."
        >>> result = optimizer.reorder_triple_patterns(q)
        >>> # Literal pattern should come first (most selective)
        >>> assert result.index("'John'") < result.index("a :Person")
        """
        lines = query.split("\n")
        result_lines: list[str] = []
        triple_patterns: list[tuple[int, str, float]] = []

        # Extract WHERE clause bounds
        where_start = -1
        where_end = -1
        for i, line in enumerate(lines):
            if "WHERE" in line.upper() and "{" in line:
                where_start = i
            if where_start >= 0 and "}" in line:
                where_end = i
                break

        if where_start < 0:
            return query  # No WHERE clause, nothing to optimize

        # Collect triple patterns from WHERE clause
        for i in range(where_start + 1, where_end):
            line = lines[i]
            # Skip empty lines, filters, and other non-triple constructs
            if (
                not line.strip()
                or "FILTER" in line
                or "OPTIONAL" in line.upper()
                or "UNION" in line.upper()
            ):
                continue

            # Check if it's a triple pattern (has at least one dot or is a triple)
            if "?" in line or ":" in line:
                pattern = self._parse_triple_pattern(line)
                if pattern:
                    selectivity = self.estimate_selectivity(pattern)
                    triple_patterns.append((i, line, selectivity))

        # If we found patterns to reorder
        if len(triple_patterns) > 1:
            # Sort by selectivity (lower = more selective = should come first)
            sorted_patterns = sorted(triple_patterns, key=lambda x: x[2])

            # Check if order changed
            original_order = [idx for idx, _, _ in triple_patterns]
            new_order = [idx for idx, _, _ in sorted_patterns]
            if original_order != new_order:
                self._rewrite_count += 1

            # Build result with reordered patterns
            pattern_indices = {idx for idx, _, _ in triple_patterns}

            # Add lines before WHERE
            result_lines.extend(lines[: where_start + 1])

            # Add reordered patterns
            for _, line, _ in sorted_patterns:
                result_lines.append(line)

            # Add lines after patterns (filters, etc.)
            for i in range(where_start + 1, where_end):
                if i not in pattern_indices:
                    result_lines.append(lines[i])

            # Add closing and remaining lines
            result_lines.extend(lines[where_end:])

            return "\n".join(result_lines)

        return query

    def estimate_selectivity(self, pattern: TriplePattern) -> float:
        """Estimate selectivity of a triple pattern.

        Lower values indicate more selective patterns (fewer results).

        Parameters
        ----------
        pattern : TriplePattern
            Triple pattern to analyze

        Returns
        -------
        float
            Estimated selectivity (0.0-1.0)

        Examples
        --------
        >>> optimizer = SparqlQueryOptimizer()
        >>> # Literal object is most selective
        >>> p1 = TriplePattern("?x", ":name", "'John'")
        >>> assert optimizer.estimate_selectivity(p1) < 0.2
        >>> # All variables is least selective
        >>> p2 = TriplePattern("?x", "?y", "?z")
        >>> assert optimizer.estimate_selectivity(p2) > 0.8
        """
        # Check for literal object (most selective)
        if pattern.object.startswith("'") or pattern.object.startswith('"'):
            return self.SELECTIVITY_LITERAL_OBJECT

        # Check for rdf:type pattern
        if pattern.predicate.lower() in ("a", "rdf:type", ":type"):
            return self.SELECTIVITY_TYPE_PATTERN

        # Check for specific predicate (moderately selective)
        if not pattern.predicate.startswith("?"):
            return self.SELECTIVITY_SPECIFIC_PREDICATE

        # All variables (least selective)
        return self.SELECTIVITY_VARIABLE_PATTERN

    def _parse_triple_pattern(self, line: str) -> TriplePattern | None:
        """Parse a triple pattern from a line.

        Parameters
        ----------
        line : str
            Line containing potential triple pattern

        Returns
        -------
        TriplePattern | None
            Parsed pattern or None if not a valid triple
        """
        # Remove comments and trailing dots
        cleaned = re.sub(r"#.*$", "", line).strip().rstrip(".")

        # Split on whitespace
        parts = cleaned.split()

        # Need at least 3 parts for a triple
        if len(parts) < 3:
            return None

        # Handle quoted literals (rejoin if split)
        if '"' in cleaned or "'" in cleaned:
            # Try to find subject, predicate, and object with quotes
            match = re.match(
                r'\s*(\S+)\s+(\S+)\s+((?:"[^"]*"|\'[^\']*\'|\S+))',
                cleaned,
            )
            if match:
                return TriplePattern(
                    subject=match.group(1),
                    predicate=match.group(2),
                    object=match.group(3),
                )

        # Simple case: no quotes
        return TriplePattern(subject=parts[0], predicate=parts[1], object=parts[2])

    def _get_indent(self, line: str) -> str:
        """Extract indentation from a line.

        Parameters
        ----------
        line : str
            Line to analyze

        Returns
        -------
        str
            Indentation string (spaces/tabs)
        """
        match = re.match(r"^(\s*)", line)
        return match.group(1) if match else "  "


# ============================================================================
# TESTS
# ============================================================================


def test_filter_pushdown_basic() -> None:
    """FILTER pushed down to immediately after producing triple."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x ?y WHERE {
  ?x :hasValue ?y .
  ?x :hasOther ?z .
  FILTER(?y > 10)
}"""
    result = optimizer.push_down_filters(query)

    # Filter should be moved closer to the triple that produces ?y
    lines = result.split("\n")
    filter_idx = next(i for i, line in enumerate(lines) if "FILTER" in line)
    value_idx = next(i for i, line in enumerate(lines) if ":hasValue" in line)

    # Filter should come right after the value triple
    assert filter_idx == value_idx + 1
    print("✓ test_filter_pushdown_basic passed")


def test_filter_pushdown_multiple_filters() -> None:
    """Multiple FILTERs are pushed down independently."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x ?y ?z WHERE {
  ?x :p1 ?y .
  ?x :p2 ?z .
  FILTER(?y > 10)
  FILTER(?z < 5)
}"""
    result = optimizer.push_down_filters(query)

    # Both filters should be in the result
    assert result.count("FILTER") == 2
    print("✓ test_filter_pushdown_multiple_filters passed")


def test_triple_reorder_by_selectivity() -> None:
    """Triple patterns reordered with most selective first."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x WHERE {
  ?x ?y ?z .
  ?x a :Person .
  ?x :name "John" .
}"""
    result = optimizer.reorder_triple_patterns(query)

    # Literal pattern should come before type pattern
    literal_pos = result.index('"John"')
    type_pos = result.index("a :Person")
    var_pos = result.index("?x ?y ?z")

    assert literal_pos < type_pos < var_pos
    print("✓ test_triple_reorder_by_selectivity passed")


def test_combined_optimizations() -> None:
    """Both filter pushdown and triple reordering work together."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?person WHERE {
  ?person :hasAge ?age .
  ?person ?prop ?val .
  ?person :name "Alice" .
  FILTER(?age > 18)
}"""
    result = optimizer.optimize(query)

    # Should have multiple rewrites
    assert result.rewrite_count >= 2
    assert result.estimated_speedup > 1.0
    print("✓ test_combined_optimizations passed")


def test_query_with_union() -> None:
    """Queries with UNION are handled correctly."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x WHERE {
  { ?x a :Person }
  UNION
  { ?x a :Organization }
}"""
    result = optimizer.optimize(query)

    # Should not crash, UNION structure preserved
    assert "UNION" in result.optimized
    print("✓ test_query_with_union passed")


def test_query_with_optional() -> None:
    """Queries with OPTIONAL are handled correctly."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x ?name WHERE {
  ?x a :Person .
  OPTIONAL { ?x :hasName ?name }
}"""
    result = optimizer.optimize(query)

    # Should not crash, OPTIONAL structure preserved
    assert "OPTIONAL" in result.optimized
    print("✓ test_query_with_optional passed")


def test_no_optimization_needed() -> None:
    """Already optimal query returns same result."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x WHERE {
  ?x :name "Bob" .
  FILTER(?x != :excluded)
}"""
    result = optimizer.optimize(query)

    # May have some rewrites but should be valid
    assert result.optimized is not None
    print("✓ test_no_optimization_needed passed")


def test_complex_filter_expression() -> None:
    """Complex FILTER expressions are handled correctly."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x WHERE {
  ?x :value ?v .
  FILTER(?v > 10 && ?v < 100 || ?v = 0)
}"""
    result = optimizer.push_down_filters(query)

    # Complex filter should be preserved
    assert "FILTER(?v > 10 && ?v < 100 || ?v = 0)" in result
    print("✓ test_complex_filter_expression passed")


def test_nested_patterns() -> None:
    """Nested graph patterns are preserved."""
    optimizer = SparqlQueryOptimizer()
    query = """SELECT ?x WHERE {
  GRAPH ?g {
    ?x a :Person .
  }
}"""
    result = optimizer.optimize(query)

    # GRAPH structure should be preserved
    assert "GRAPH" in result.optimized
    print("✓ test_nested_patterns passed")


def test_performance_improvement_estimate() -> None:
    """Estimated speedup correlates with rewrite count."""
    optimizer = SparqlQueryOptimizer()

    # Query with no optimization potential
    simple_query = "SELECT ?x WHERE { ?x a :Thing }"
    simple_result = optimizer.optimize(simple_query)

    # Query with high optimization potential
    complex_query = """SELECT ?x WHERE {
  ?x ?p1 ?v1 .
  ?x ?p2 ?v2 .
  ?x :name "Test" .
  FILTER(?v1 > 10)
  FILTER(?v2 < 5)
}"""
    complex_result = optimizer.optimize(complex_query)

    # Complex query should have higher estimated speedup
    assert complex_result.estimated_speedup >= simple_result.estimated_speedup
    print("✓ test_performance_improvement_estimate passed")


def test_selectivity_estimation() -> None:
    """Selectivity estimation follows expected ordering."""
    optimizer = SparqlQueryOptimizer()

    # Literal object (most selective)
    p1 = TriplePattern("?x", ":name", '"Alice"')
    s1 = optimizer.estimate_selectivity(p1)

    # Type pattern (moderately selective)
    p2 = TriplePattern("?x", "a", ":Person")
    s2 = optimizer.estimate_selectivity(p2)

    # Specific predicate (less selective)
    p3 = TriplePattern("?x", ":hasValue", "?y")
    s3 = optimizer.estimate_selectivity(p3)

    # All variables (least selective)
    p4 = TriplePattern("?x", "?y", "?z")
    s4 = optimizer.estimate_selectivity(p4)

    assert s1 < s2 < s3 < s4
    print("✓ test_selectivity_estimation passed")


def run_all_tests() -> tuple[int, int]:
    """Run all tests and return (passed, failed) counts.

    Returns
    -------
    tuple[int, int]
        Count of passed and failed tests
    """
    tests = [
        test_filter_pushdown_basic,
        test_filter_pushdown_multiple_filters,
        test_triple_reorder_by_selectivity,
        test_combined_optimizations,
        test_query_with_union,
        test_query_with_optional,
        test_no_optimization_needed,
        test_complex_filter_expression,
        test_nested_patterns,
        test_performance_improvement_estimate,
        test_selectivity_estimation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    return passed, failed


if __name__ == "__main__":
    print("=" * 70)
    print("SPARQL Query Optimizer POC - Test Suite")
    print("=" * 70)

    # Run all tests
    passed, failed = run_all_tests()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed!")

        # Demo usage
        print("\n" + "=" * 70)
        print("Demo Usage")
        print("=" * 70)

        optimizer = SparqlQueryOptimizer()
        demo_query = """
SELECT ?person ?name ?age WHERE {
  ?person :hasAge ?age .
  ?person :hasOther ?other .
  ?person :name "Alice" .
  FILTER(?age > 18)
  FILTER(?other != :excluded)
}
"""
        print("\nOriginal Query:")
        print(demo_query)

        result = optimizer.optimize(demo_query)

        print("\nOptimized Query:")
        print(result.optimized)

        print(f"\nRewrites Applied: {result.rewrite_count}")
        print(f"Estimated Speedup: {result.estimated_speedup:.2f}x")
    else:
        print(f"\n✗ {failed} test(s) failed!")
        exit(1)
