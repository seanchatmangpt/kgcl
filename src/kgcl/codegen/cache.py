"""Ultra-fast graph caching with memory and disk persistence.

Provides LRU-based caching of parsed RDF graphs with optional disk
persistence and Redis backend support for distributed caching.
"""

import hashlib
import os
import pickle
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from rdflib import Graph


class GraphCache:
    """Ultra-fast graph caching with memory management.

    Implements a two-tier caching strategy:
    1. In-memory LRU cache for fast access
    2. Optional disk-based cache for persistence
    3. Optional Redis backend for distributed caching

    Cache keys are derived from file content hashes to ensure
    automatic invalidation when source files change.

    Parameters
    ----------
    max_size : int, default=100
        Maximum number of graphs to keep in memory cache
    enable_disk_cache : bool, default=True
        Whether to use disk-based persistence

    Attributes
    ----------
    memory_cache : Dict[str, Graph]
        In-memory LRU cache
    cache_dir : Path
        Directory for disk cache storage
    access_times : Dict[str, float]
        Timestamps for LRU eviction

    Examples
    --------
    >>> cache = GraphCache(max_size=50)
    >>> graph = Graph()
    >>> test_file = Path("test.ttl")
    >>> cache.put(test_file, graph)
    >>> cached = cache.get(test_file)
    >>> cached is not None
    True
    """

    def __init__(self, max_size: int = 100, enable_disk_cache: bool = True) -> None:
        """Initialize graph cache with specified configuration."""
        self.memory_cache: dict[str, Graph] = {}
        self.max_size = max_size
        self.enable_disk_cache = enable_disk_cache
        self.cache_dir = Path(".ttl2dspy_cache")
        self.access_times: dict[str, float] = {}
        self._lock = threading.RLock()
        self.redis_url = os.getenv("REDIS_URL")
        self._redis: object | None = None

        if enable_disk_cache:
            self.cache_dir.mkdir(exist_ok=True)

        if self.redis_url:
            try:
                import redis  # type: ignore[import-untyped]

                self._redis = redis.from_url(self.redis_url)
            except Exception:
                self._redis = None

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key from file content hash.

        Parameters
        ----------
        file_path : Path
            Path to file to generate key for

        Returns
        -------
        str
            SHA-256 hash of file contents
        """
        with open(file_path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()

    def get(self, file_path: Path) -> Graph | None:
        """Get cached graph with multi-tier lookup.

        Checks memory cache, then Redis, then disk cache in order.
        Promotes disk/Redis hits to memory cache.

        Parameters
        ----------
        file_path : Path
            Path to file to retrieve graph for

        Returns
        -------
        Optional[Graph]
            Cached graph if found, None otherwise

        Examples
        --------
        >>> cache = GraphCache()
        >>> result = cache.get(Path("nonexistent.ttl"))
        >>> result is None
        True
        """
        cache_key = self._get_cache_key(file_path)

        with self._lock:
            if cache_key in self.memory_cache:
                self.access_times[cache_key] = time.time()
                return self.memory_cache[cache_key]

            if self._redis is not None:
                try:
                    raw = self._redis.get(cache_key)  # type: ignore[attr-defined]
                    if raw:
                        graph: Graph = pickle.loads(raw)  # type: ignore[arg-type]
                        self._add_to_memory_cache(cache_key, graph)
                        return graph
                except Exception:
                    pass

            if self.enable_disk_cache:
                disk_path = self.cache_dir / f"{cache_key}.pkl"
                if disk_path.exists():
                    try:
                        with open(disk_path, "rb") as f:
                            graph = pickle.load(f)

                        self._add_to_memory_cache(cache_key, graph)
                        return graph
                    except Exception:
                        disk_path.unlink(missing_ok=True)

            return None

    def put(self, file_path: Path, graph: Graph) -> None:
        """Cache graph with write-through to all tiers.

        Stores graph in memory cache and optionally writes to
        disk cache and Redis for persistence.

        Parameters
        ----------
        file_path : Path
            Path to file being cached
        graph : Graph
            RDF graph to cache

        Examples
        --------
        >>> cache = GraphCache()
        >>> graph = Graph()
        >>> cache.put(Path("test.ttl"), graph)
        """
        cache_key = self._get_cache_key(file_path)

        with self._lock:
            self._add_to_memory_cache(cache_key, graph)

            if self._redis is not None:
                try:
                    ttl = int(os.getenv("CACHE_TTL", "86400"))
                    self._redis.setex(  # type: ignore[attr-defined]
                        cache_key, ttl, pickle.dumps(graph)
                    )
                except Exception:
                    pass

            if self.enable_disk_cache:
                disk_path = self.cache_dir / f"{cache_key}.pkl"
                try:
                    with open(disk_path, "wb") as f:
                        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
                except Exception:
                    pass

    def _add_to_memory_cache(self, cache_key: str, graph: Graph) -> None:
        """Add to memory cache with LRU eviction.

        Parameters
        ----------
        cache_key : str
            Cache key
        graph : Graph
            Graph to cache
        """
        if len(self.memory_cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.memory_cache[oldest_key]
            del self.access_times[oldest_key]

        self.memory_cache[cache_key] = graph
        self.access_times[cache_key] = time.time()

    def clear(self) -> None:
        """Clear all caches (memory, disk, Redis).

        Examples
        --------
        >>> cache = GraphCache()
        >>> cache.clear()
        >>> len(cache.memory_cache)
        0
        """
        with self._lock:
            self.memory_cache.clear()
            self.access_times.clear()

            if self.enable_disk_cache and self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.pkl"):
                    cache_file.unlink()

            if self._redis is not None:
                try:
                    self._redis.flushdb()  # type: ignore[attr-defined]
                except Exception:
                    pass

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns
        -------
        dict[str, int]
            Cache size statistics

        Examples
        --------
        >>> cache = GraphCache()
        >>> stats = cache.stats()
        >>> "memory_entries" in stats
        True
        """
        with self._lock:
            disk_entries = 0
            if self.enable_disk_cache and self.cache_dir.exists():
                disk_entries = len(list(self.cache_dir.glob("*.pkl")))

            return {"memory_entries": len(self.memory_cache), "disk_entries": disk_entries, "max_size": self.max_size}
