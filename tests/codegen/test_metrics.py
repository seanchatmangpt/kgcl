"""Tests for kgcl.codegen.metrics module.

Chicago School TDD tests that verify actual behavior of metrics tracking,
not just data structures.
"""

import pytest

from kgcl.codegen.metrics import UltraMetrics


def test_metrics_initialization() -> None:
    """Test metrics initialize with zero values."""
    metrics = UltraMetrics()

    assert metrics.signatures_generated == 0
    assert metrics.processing_time == 0.0
    assert metrics.parsing_time == 0.0
    assert metrics.cache_hits == 0
    assert metrics.cache_misses == 0
    assert metrics.graph_size == 0
    assert metrics.memory_saved_mb == 0.0
    assert metrics.parallel_workers == 0


def test_cache_efficiency_with_no_accesses() -> None:
    """Test cache efficiency returns 0.0 when no cache accesses."""
    metrics = UltraMetrics()

    assert metrics.cache_efficiency == 0.0


def test_cache_efficiency_with_all_hits() -> None:
    """Test cache efficiency returns 1.0 with 100% hit rate."""
    metrics = UltraMetrics(cache_hits=10, cache_misses=0)

    assert metrics.cache_efficiency == 1.0


def test_cache_efficiency_with_mixed_results() -> None:
    """Test cache efficiency calculates correct ratio."""
    metrics = UltraMetrics(cache_hits=8, cache_misses=2)

    assert metrics.cache_efficiency == 0.8


def test_cache_efficiency_with_all_misses() -> None:
    """Test cache efficiency returns 0.0 with 100% miss rate."""
    metrics = UltraMetrics(cache_hits=0, cache_misses=10)

    assert metrics.cache_efficiency == 0.0


def test_parsing_percentage_with_no_processing_time() -> None:
    """Test parsing percentage returns 0.0 when processing time is zero."""
    metrics = UltraMetrics(parsing_time=5.0, processing_time=0.0)

    assert metrics.parsing_percentage == 0.0


def test_parsing_percentage_calculation() -> None:
    """Test parsing percentage calculates correctly."""
    metrics = UltraMetrics(parsing_time=2.0, processing_time=10.0)

    assert metrics.parsing_percentage == 20.0


def test_parsing_percentage_with_full_parsing() -> None:
    """Test parsing percentage with 100% parsing time."""
    metrics = UltraMetrics(parsing_time=10.0, processing_time=10.0)

    assert metrics.parsing_percentage == 100.0


def test_to_dict_includes_all_metrics() -> None:
    """Test to_dict includes all metrics including computed properties."""
    metrics = UltraMetrics(
        signatures_generated=5,
        processing_time=1.0,
        parsing_time=0.2,
        cache_hits=8,
        cache_misses=2,
        graph_size=100,
        parallel_workers=4,
        memory_saved_mb=10.5,
    )

    result = metrics.to_dict()

    assert result["signatures_generated"] == 5
    assert result["processing_time_ms"] == 1000.0
    assert result["parsing_time_ms"] == 200.0
    assert result["parsing_percentage"] == 20.0
    assert result["cache_efficiency"] == 0.8
    assert result["cache_hits"] == 8
    assert result["cache_misses"] == 2
    assert result["graph_size"] == 100
    assert result["parallel_workers"] == 4
    assert result["memory_saved_mb"] == 10.5


def test_to_dict_with_zero_values() -> None:
    """Test to_dict handles zero values correctly."""
    metrics = UltraMetrics()

    result = metrics.to_dict()

    assert result["signatures_generated"] == 0
    assert result["cache_efficiency"] == 0.0
    assert result["parsing_percentage"] == 0.0


def test_metrics_are_mutable() -> None:
    """Test metrics can be updated after initialization."""
    metrics = UltraMetrics()

    metrics.signatures_generated = 10
    metrics.cache_hits = 5

    assert metrics.signatures_generated == 10
    assert metrics.cache_hits == 5


def test_realistic_transpilation_metrics() -> None:
    """Test metrics with realistic transpilation scenario values."""
    metrics = UltraMetrics(
        signatures_generated=25,
        processing_time=5.5,
        parsing_time=1.2,
        cache_hits=15,
        cache_misses=3,
        graph_size=5000,
        parallel_workers=4,
    )

    assert metrics.cache_efficiency > 0.8
    assert metrics.parsing_percentage < 25.0
    assert metrics.signatures_generated > 0

    result_dict = metrics.to_dict()
    assert "signatures_generated" in result_dict
    assert "cache_efficiency" in result_dict
