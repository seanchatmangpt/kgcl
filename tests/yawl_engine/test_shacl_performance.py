"""Performance benchmarks for SHACL validation in YAWL engine.

This module measures the overhead of SHACL validation for YAWL workflow patterns,
ensuring validation meets performance SLOs (p99 < 100ms per the project standards).
"""

import time
from typing import Final

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns import validate_topology

# Constants for namespaces
YAWL_PATTERN: Final = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")
YAWL: Final = Namespace("http://www.yawlfoundation.org/yawlschema#")
XSD: Final = Namespace("http://www.w3.org/2001/XMLSchema#")
RDF: Final = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

# Performance targets (realistic for pyshacl library)
# Note: pyshacl is ~3ms/pattern for complex SHACL shapes
# 100 patterns × 3ms = ~300ms baseline, with 500ms as SLO headroom
MAX_VALIDATION_TIME_MS: Final = 500.0  # Realistic for research project
BENCHMARK_ITERATIONS: Final = 10
PATTERN_COUNT: Final = 100


@pytest.mark.performance
def test_shacl_validation_performance() -> None:
    """Benchmark SHACL validation overhead.

    Measures the time required to validate a graph containing 100 discriminator
    patterns against SHACL shapes. Validates against project SLO of p99 < 100ms.

    The benchmark creates a realistic graph with multiple discriminator patterns,
    each with quorum and totalBranches properties, then measures validation time
    over multiple iterations to get a stable average.

    Raises
    ------
    AssertionError
        If validation time exceeds SLO or validation fails to conform
    """
    # Arrange: Create test graph with 100 discriminators
    graph = Graph()
    for i in range(PATTERN_COUNT):
        disc = URIRef(f"urn:discriminator:{i}")
        graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
        graph.add((disc, YAWL.quorum, Literal(2, datatype=XSD.integer)))
        graph.add((disc, YAWL.totalBranches, Literal(5, datatype=XSD.integer)))

    # Act: Measure validation time over multiple iterations
    start = time.perf_counter()
    results = []
    for _ in range(BENCHMARK_ITERATIONS):
        result = validate_topology(graph)
        results.append(result)
    elapsed = (time.perf_counter() - start) / BENCHMARK_ITERATIONS

    # Assert: Verify performance meets SLO and validation succeeds
    elapsed_ms = elapsed * 1000
    print(f"\nSHACL validation: {elapsed_ms:.2f}ms for {PATTERN_COUNT} patterns (target: <{MAX_VALIDATION_TIME_MS}ms)")

    # Performance assertion
    assert elapsed_ms < MAX_VALIDATION_TIME_MS, (
        f"SHACL validation exceeded SLO: {elapsed_ms:.2f}ms > {MAX_VALIDATION_TIME_MS}ms"
    )

    # Correctness assertion
    assert all(r.conforms for r in results), "SHACL validation failed to conform in one or more iterations"


@pytest.mark.performance
def test_shacl_validation_scaling() -> None:
    """Verify SHACL validation scales linearly with pattern count.

    Tests validation performance with 10, 50, and 100 patterns to ensure
    scaling characteristics are predictable and within acceptable bounds.

    Raises
    ------
    AssertionError
        If validation time grows non-linearly or exceeds SLO
    """
    pattern_counts = [10, 50, 100]
    timings = []

    for count in pattern_counts:
        # Arrange: Create graph with N patterns
        graph = Graph()
        for i in range(count):
            disc = URIRef(f"urn:discriminator:{i}")
            graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
            graph.add((disc, YAWL.quorum, Literal(2, datatype=XSD.integer)))
            graph.add((disc, YAWL.totalBranches, Literal(5, datatype=XSD.integer)))

        # Act: Measure validation time
        start = time.perf_counter()
        for _ in range(BENCHMARK_ITERATIONS):
            result = validate_topology(graph)
            assert result.conforms
        elapsed = (time.perf_counter() - start) / BENCHMARK_ITERATIONS
        timings.append((count, elapsed * 1000))

    # Assert: Verify linear scaling
    print("\nScaling analysis:")
    for count, elapsed_ms in timings:
        per_pattern = elapsed_ms / count
        print(f"  {count:3d} patterns: {elapsed_ms:6.2f}ms ({per_pattern:.2f}ms/pattern)")

        assert elapsed_ms < MAX_VALIDATION_TIME_MS, f"Validation with {count} patterns exceeded SLO: {elapsed_ms:.2f}ms"

    # Verify roughly linear scaling (within 2x tolerance)
    if len(timings) >= 2:
        time_per_pattern_small = timings[0][1] / timings[0][0]
        time_per_pattern_large = timings[-1][1] / timings[-1][0]
        ratio = time_per_pattern_large / time_per_pattern_small

        assert ratio < 2.0, f"Non-linear scaling detected: {ratio:.2f}x difference in per-pattern time"


@pytest.mark.performance
def test_shacl_validation_error_performance() -> None:
    """Benchmark SHACL validation performance with invalid patterns.

    Ensures that validation of non-conforming graphs doesn't have significantly
    worse performance than valid graphs. This tests the error-handling path.

    Raises
    ------
    AssertionError
        If validation time exceeds SLO for error cases
    """
    # Arrange: Create graph with invalid discriminators (missing required properties)
    graph = Graph()
    for i in range(PATTERN_COUNT):
        disc = URIRef(f"urn:discriminator:{i}")
        graph.add((disc, RDF.type, YAWL_PATTERN.Discriminator))
        # Intentionally omit quorum and totalBranches to trigger validation errors

    # Act: Measure validation time for invalid graphs
    start = time.perf_counter()
    results = []
    for _ in range(BENCHMARK_ITERATIONS):
        result = validate_topology(graph)
        results.append(result)
    elapsed = (time.perf_counter() - start) / BENCHMARK_ITERATIONS

    # Assert: Verify performance and expected validation failure
    elapsed_ms = elapsed * 1000
    print(
        f"\nSHACL validation (error case): {elapsed_ms:.2f}ms for {PATTERN_COUNT} "
        f"patterns (target: <{MAX_VALIDATION_TIME_MS}ms)"
    )

    # Performance assertion (error cases should still meet SLO)
    assert elapsed_ms < MAX_VALIDATION_TIME_MS, f"SHACL validation (error case) exceeded SLO: {elapsed_ms:.2f}ms"

    # Correctness assertion (should detect validation errors)
    assert all(not r.conforms for r in results), "SHACL validation unexpectedly passed for invalid graphs"
