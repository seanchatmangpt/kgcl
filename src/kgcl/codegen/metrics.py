"""Performance metrics for ultra-optimized TTL2DSPy transpiler.

This module provides comprehensive performance tracking including cache
efficiency, parsing time, parallel execution metrics, and OpenTelemetry
integration.
"""

from dataclasses import dataclass, field


@dataclass
class UltraMetrics:
    """Ultra-performance metrics with OpenTelemetry integration.

    Tracks all critical performance indicators for the transpilation
    process, including caching efficiency, parsing overhead, and
    parallel execution performance.

    Attributes
    ----------
    signatures_generated : int
        Total number of DSPy signatures generated
    processing_time : float
        Total end-to-end processing time in seconds
    parsing_time : float
        Time spent parsing RDF graphs in seconds
    cache_hits : int
        Number of successful cache retrievals
    cache_misses : int
        Number of cache misses requiring new parsing
    graph_size : int
        Total number of RDF triples in parsed graphs
    memory_saved_mb : float
        Estimated memory saved through caching in MB
    parallel_workers : int
        Number of parallel workers used for processing

    Examples
    --------
    >>> metrics = UltraMetrics()
    >>> metrics.cache_hits = 10
    >>> metrics.cache_misses = 2
    >>> metrics.cache_efficiency
    0.8333333333333334
    """

    signatures_generated: int = 0
    processing_time: float = 0.0
    parsing_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    graph_size: int = 0
    memory_saved_mb: float = 0.0
    parallel_workers: int = 0

    @property
    def cache_efficiency(self) -> float:
        """Calculate cache hit rate as a percentage.

        Returns
        -------
        float
            Cache efficiency ratio (0.0 to 1.0), where 1.0 means 100% hits

        Examples
        --------
        >>> metrics = UltraMetrics(cache_hits=8, cache_misses=2)
        >>> metrics.cache_efficiency
        0.8
        """
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def parsing_percentage(self) -> float:
        """Calculate parsing time as percentage of total processing time.

        Returns
        -------
        float
            Parsing time percentage (0.0 to 100.0)

        Examples
        --------
        >>> metrics = UltraMetrics(processing_time=10.0, parsing_time=2.0)
        >>> metrics.parsing_percentage
        20.0
        """
        if self.processing_time > 0:
            return (self.parsing_time / self.processing_time) * 100
        return 0.0

    def to_dict(self) -> dict[str, int | float]:
        """Export metrics as dictionary for serialization.

        Returns
        -------
        dict[str, int | float]
            All metrics including computed properties

        Examples
        --------
        >>> metrics = UltraMetrics(signatures_generated=5)
        >>> metrics.to_dict()["signatures_generated"]
        5
        """
        return {
            "signatures_generated": self.signatures_generated,
            "processing_time_ms": self.processing_time * 1000,
            "parsing_time_ms": self.parsing_time * 1000,
            "parsing_percentage": self.parsing_percentage,
            "cache_efficiency": self.cache_efficiency,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "graph_size": self.graph_size,
            "parallel_workers": self.parallel_workers,
            "memory_saved_mb": self.memory_saved_mb,
        }
