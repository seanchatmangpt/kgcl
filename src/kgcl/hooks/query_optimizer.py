"""
Query Optimizer for SPARQL queries.

This module provides query analysis, optimization, and index suggestions
for improving SPARQL query performance.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryPlan:
    """
    Execution plan for SPARQL query.

    Parameters
    ----------
    query : str
        Original SPARQL query
    estimated_selectivity : float
        Estimated result selectivity (0.0-1.0)
    estimated_cost : float
        Estimated execution cost in milliseconds
    execution_path : List[str]
        Step-by-step execution plan
    uses_index : bool
        Whether query can use indexes
    parallelizable : bool
        Whether query can be parallelized
    optimized_query : Optional[str]
        Optimized version of query
    index_hints : List[str]
        Suggested indexes for optimization
    """

    query: str
    estimated_selectivity: float
    estimated_cost: float
    execution_path: list[str]
    uses_index: bool = False
    parallelizable: bool = False
    optimized_query: str | None = None
    index_hints: list[str] = field(default_factory=list)


class QueryOptimizer:
    """
    Optimize SPARQL query execution.

    Analyzes queries, estimates costs, suggests indexes, and produces
    optimized query plans.
    """

    def __init__(self) -> None:
        """Initialize optimizer."""
        self.query_stats: dict[str, dict[str, Any]] = {}
        self.index_hints: dict[str, str] = {}
        self._known_indexes: set[str] = set()

    def analyze_query(self, query: str) -> QueryPlan:
        """
        Analyze query and create execution plan.

        Parameters
        ----------
        query : str
            SPARQL query to analyze

        Returns
        -------
        QueryPlan
            Execution plan with cost estimates
        """
        query_normalized = self._normalize_query(query)
        query_hash = self._hash_query(query_normalized)

        # Parse query structure
        has_union = "UNION" in query.upper()
        has_optional = "OPTIONAL" in query.upper()
        has_filter = "FILTER" in query.upper()
        has_limit = "LIMIT" in query.upper()
        has_order_by = "ORDER BY" in query.upper()

        # Count triple patterns
        triple_count = len(re.findall(r"\?[a-zA-Z0-9_]+ [^\s]+ [^\s.]+", query))

        # Estimate selectivity (lower = more selective)
        selectivity = self._estimate_selectivity(query, triple_count, has_filter)

        # Estimate cost (milliseconds)
        base_cost = triple_count * 10.0
        if has_union:
            base_cost *= 2.0
        if has_optional:
            base_cost *= 1.5
        if has_order_by and not has_limit:
            base_cost *= 3.0

        estimated_cost = base_cost

        # Build execution path
        execution_path = self._build_execution_path(
            query, triple_count, has_union, has_optional, has_filter
        )

        # Check for index usage
        uses_index = self._can_use_index(query)

        # Check if parallelizable
        parallelizable = has_union and not has_order_by

        # Generate index hints
        index_hints = self.suggest_indexes(query)

        # Create optimized query
        optimized_query = self.optimize(query)

        plan = QueryPlan(
            query=query,
            estimated_selectivity=selectivity,
            estimated_cost=estimated_cost,
            execution_path=execution_path,
            uses_index=uses_index,
            parallelizable=parallelizable,
            optimized_query=optimized_query,
            index_hints=index_hints,
        )

        # Store stats
        self.query_stats[query_hash] = {
            "query": query_normalized,
            "plan": plan,
            "executions": 0,
            "avg_time_ms": 0.0,
        }

        return plan

    def optimize(self, query: str) -> str:
        """
        Return optimized query.

        Parameters
        ----------
        query : str
            Original query

        Returns
        -------
        str
            Optimized query
        """
        optimized = query

        # Optimization 1: Move filters closer to triple patterns
        optimized = self._push_down_filters(optimized)

        # Optimization 2: Reorder triple patterns for selectivity
        optimized = self._reorder_triple_patterns(optimized)

        # Optimization 3: Add LIMIT if missing and has ORDER BY
        if "ORDER BY" in optimized.upper() and "LIMIT" not in optimized.upper():
            optimized = optimized.rstrip() + " LIMIT 1000"

        return optimized

    def suggest_indexes(self, query: str) -> list[str]:
        """
        Suggest index creation for query optimization.

        Parameters
        ----------
        query : str
            Query to analyze

        Returns
        -------
        List[str]
            Suggested index definitions
        """
        suggestions = []

        # Extract predicates
        predicates = re.findall(r"<([^>]+)>", query)

        # Suggest indexes for common predicates
        for predicate in predicates:
            index_name = f"idx_{hashlib.md5(predicate.encode()).hexdigest()[:8]}"
            if index_name not in self._known_indexes:
                suggestions.append(f"CREATE INDEX {index_name} ON triples(predicate)")
                self._known_indexes.add(index_name)

        # Suggest index for subject lookups
        if re.search(r"\?s [<a-z]", query) and "idx_subject" not in self._known_indexes:
            suggestions.append("CREATE INDEX idx_subject ON triples(subject)")
            self._known_indexes.add("idx_subject")

        # Suggest index for object lookups
        if re.search(r"[<a-z]+ \?o", query) and "idx_object" not in self._known_indexes:
            suggestions.append("CREATE INDEX idx_object ON triples(object)")
            self._known_indexes.add("idx_object")

        return suggestions

    def record_execution(self, query: str, execution_time_ms: float) -> None:
        """
        Record actual execution time for query.

        Parameters
        ----------
        query : str
            Executed query
        execution_time_ms : float
            Actual execution time in milliseconds
        """
        query_hash = self._hash_query(self._normalize_query(query))
        if query_hash in self.query_stats:
            stats = self.query_stats[query_hash]
            stats["executions"] += 1
            # Update rolling average
            prev_avg = stats["avg_time_ms"]
            stats["avg_time_ms"] = (
                prev_avg * (stats["executions"] - 1) + execution_time_ms
            ) / stats["executions"]

    def get_stats(self, query: str) -> dict[str, Any] | None:
        """
        Get statistics for a query.

        Parameters
        ----------
        query : str
            Query to get stats for

        Returns
        -------
        Optional[Dict]
            Query statistics or None if not found
        """
        query_hash = self._hash_query(self._normalize_query(query))
        return self.query_stats.get(query_hash)

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing extra whitespace."""
        return " ".join(query.split())

    def _hash_query(self, query: str) -> str:
        """Create hash of query for identification."""
        return hashlib.md5(query.encode()).hexdigest()

    def _estimate_selectivity(
        self, query: str, triple_count: int, has_filter: bool
    ) -> float:
        """
        Estimate query selectivity (0.0 = very selective, 1.0 = returns all).
        """
        # Start with base selectivity
        selectivity = 0.5

        # More triples = more selective
        selectivity *= 0.8**triple_count

        # Filters increase selectivity
        if has_filter:
            filter_count = query.upper().count("FILTER")
            selectivity *= 0.7**filter_count

        # Ensure in range [0.0, 1.0]
        return max(0.0, min(1.0, selectivity))

    def _build_execution_path(
        self,
        query: str,
        triple_count: int,
        has_union: bool,
        has_optional: bool,
        has_filter: bool,
    ) -> list[str]:
        """Build step-by-step execution plan."""
        path = []

        path.append("Parse query")
        path.append(f"Execute {triple_count} triple pattern(s)")

        if has_filter:
            path.append("Apply filter conditions")

        if has_optional:
            path.append("Execute optional patterns")

        if has_union:
            path.append("Execute UNION branches")

        if "ORDER BY" in query.upper():
            path.append("Sort results")

        if "LIMIT" in query.upper():
            path.append("Apply LIMIT")

        path.append("Return results")

        return path

    def _can_use_index(self, query: str) -> bool:
        """Check if query can benefit from indexes."""
        # Check for bound predicates
        if re.search(r"<[^>]+>", query):
            return True

        # Check for specific subject/object patterns
        return bool(re.search(r"<[^>]+> \?[a-z]", query))

    def _push_down_filters(self, query: str) -> str:
        """
        Push FILTER clauses closer to triple patterns that produce filtered variables.

        Algorithm:
        1. Parse query to extract FILTER clauses and their positions
        2. For each FILTER, identify which variables it references
        3. Find the triple pattern that produces each variable
        4. Move FILTER to immediately after the last producing triple

        Parameters
        ----------
        query : str
            Original SPARQL query

        Returns
        -------
        str
            Query with filters pushed down closer to producing patterns

        Note
        ----
        Implementation uses regex-based parsing. Production systems should use
        proper SPARQL parser for complete query transformation.
        """
        # Extract FILTER clauses and their conditions using regex
        filter_pattern = re.compile(r"FILTER\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
        filters = filter_pattern.findall(query)

        if not filters:
            return query

        # Remove existing FILTER clauses temporarily
        query_without_filters = filter_pattern.sub("", query)

        # Extract triple patterns (simplified: match ?var predicate object)
        triple_pattern = re.compile(r"\?[a-zA-Z0-9_]+\s+[^\s]+\s+[^\s.;]+")
        triples = triple_pattern.findall(query_without_filters)

        if not triples:
            return query

        # For each FILTER, find variables it references
        for filter_cond in filters:
            # Extract variables from filter condition (?varname)
            var_pattern = re.compile(r"\?([a-zA-Z0-9_]+)")
            filter_vars = set(var_pattern.findall(filter_cond))

            if not filter_vars:
                continue

            # Find the last triple that produces any of these variables
            last_producing_triple_idx = -1
            for idx, triple in enumerate(triples):
                triple_vars = set(var_pattern.findall(triple))
                if filter_vars & triple_vars:  # Intersection
                    last_producing_triple_idx = idx

            # If found, insert FILTER after that triple
            if last_producing_triple_idx >= 0 and last_producing_triple_idx < len(
                triples
            ):
                # Find position of triple in query
                triple_text = triples[last_producing_triple_idx]
                triple_pos = query_without_filters.find(triple_text)

                if triple_pos >= 0:
                    # Insert FILTER after triple (after period or semicolon)
                    insert_pos = triple_pos + len(triple_text)

                    # Find next period/semicolon/closing brace
                    while (
                        insert_pos < len(query_without_filters)
                        and query_without_filters[insert_pos] not in ".;}"
                    ):
                        insert_pos += 1

                    if insert_pos < len(query_without_filters):
                        insert_pos += 1  # After period/semicolon

                    # Insert FILTER
                    filter_text = f" FILTER({filter_cond}) "
                    query_without_filters = (
                        query_without_filters[:insert_pos]
                        + filter_text
                        + query_without_filters[insert_pos:]
                    )

        return query_without_filters

    def _reorder_triple_patterns(self, query: str) -> str:
        """
        Reorder triple patterns by estimated selectivity.

        Algorithm:
        1. Parse query to extract triple patterns
        2. Estimate selectivity for each pattern:
           - Literal objects: 0.1 (most selective)
           - URI predicates with rdf:type: 0.2
           - Bound subjects: 0.3
           - All variables: 0.9 (least selective)
        3. Sort patterns by selectivity (most selective first)
        4. Reconstruct query with reordered patterns

        Parameters
        ----------
        query : str
            Original SPARQL query

        Returns
        -------
        str
            Query with triple patterns reordered by selectivity
        """
        # Extract WHERE clause
        where_pattern = re.compile(r"WHERE\s*\{(.*?)\}", re.IGNORECASE | re.DOTALL)
        where_match = where_pattern.search(query)

        if not where_match:
            return query

        where_content = where_match.group(1)

        # Extract triple patterns (subject predicate object)
        triple_pattern = re.compile(r"([^\s.;]+)\s+([^\s.;]+)\s+([^\s.;]+)")
        triples = triple_pattern.findall(where_content)

        if len(triples) <= 1:
            return query  # No reordering needed

        # Estimate selectivity for each triple
        selectivities: list[tuple[tuple[str, str, str], float]] = []

        for subject, predicate, obj in triples:
            selectivity = 0.5  # Default

            # Literal objects (quoted strings or numbers) - most selective
            if obj.startswith('"') or obj.isdigit():
                selectivity = 0.1
            # URI predicate with rdf:type - very selective
            elif "rdf:type" in predicate or ":type" in predicate:
                selectivity = 0.2
            # Bound subject (URI or literal)
            elif subject.startswith("<") or subject.startswith('"'):
                selectivity = 0.3
            # URI predicate (bound)
            elif predicate.startswith("<") or (
                ":" in predicate and not predicate.startswith("?")
            ):
                selectivity = 0.4
            # All variables - least selective (full scan)
            elif (
                subject.startswith("?")
                and predicate.startswith("?")
                and obj.startswith("?")
            ):
                selectivity = 0.9

            selectivities.append(((subject, predicate, obj), selectivity))

        # Sort by selectivity (most selective first)
        sorted_triples = [t for t, _ in sorted(selectivities, key=lambda x: x[1])]

        # Reconstruct WHERE clause
        new_where_content = " .\n    ".join(
            f"{s} {p} {o}" for s, p, o in sorted_triples
        )

        # Replace WHERE clause in query
        new_query = where_pattern.sub(f"WHERE {{\n    {new_where_content}\n}}", query)

        return new_query
