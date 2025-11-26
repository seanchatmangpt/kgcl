"""
Query Cache for SPARQL Results with TTL-based Invalidation.

Implements LRU eviction, hit/miss tracking, and cache statistics.
Ported from UNRDF query-cache.mjs.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""

    result: Any
    timestamp: datetime
    ttl_seconds: int
    query_hash: str

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        age_seconds = (datetime.now(UTC) - self.timestamp).total_seconds()
        return age_seconds > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.now(UTC) - self.timestamp).total_seconds()


class QueryCache:
    """Cache SPARQL query results with TTL-based invalidation.

    Features:
    - TTL-based invalidation (configurable per entry)
    - LRU eviction when cache is full
    - Hit/miss tracking
    - Cache statistics
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize query cache.

        Parameters
        ----------
        max_size : int
            Maximum number of entries in cache
        ttl_seconds : int
            Default TTL in seconds
        """
        self.cache: dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        self.query_stats: dict[str, dict[str, int | str]] = {}
        self.access_order: list[str] = []  # For LRU tracking

    def _compute_hash(self, query: str) -> str:
        """Compute SHA256 hash of query.

        Parameters
        ----------
        query : str
            SPARQL query string

        Returns
        -------
        str
            SHA256 hex digest
        """
        return sha256(query.encode()).hexdigest()

    def get(self, query: str) -> Any | None:
        """Get cached result if fresh.

        Parameters
        ----------
        query : str
            SPARQL query string

        Returns
        -------
        Optional[Any]
            Cached result or None
        """
        query_hash = self._compute_hash(query)

        if query_hash not in self.cache:
            self._record_miss(query_hash, query)
            return None

        entry = self.cache[query_hash]

        # Check if expired
        if entry.is_expired():
            del self.cache[query_hash]
            if query_hash in self.access_order:
                self.access_order.remove(query_hash)
            self._record_miss(query_hash, query)
            return None

        # Update access order for LRU
        if query_hash in self.access_order:
            self.access_order.remove(query_hash)
        self.access_order.append(query_hash)

        self._record_hit(query_hash)
        return entry.result

    def set(self, query: str, result: Any, ttl_seconds: int | None = None) -> None:
        """Cache a query result.

        Parameters
        ----------
        query : str
            SPARQL query string
        result : Any
            Query result to cache
        ttl_seconds : Optional[int]
            Optional TTL override
        """
        query_hash = self._compute_hash(query)
        ttl = ttl_seconds or self.ttl

        # Evict LRU item if cache is full
        if len(self.cache) >= self.max_size and query_hash not in self.cache:
            if self.access_order:
                lru_hash = self.access_order.pop(0)
                del self.cache[lru_hash]

        # Store entry
        self.cache[query_hash] = CacheEntry(
            result=result, timestamp=datetime.now(UTC), ttl_seconds=ttl, query_hash=query_hash
        )

        # Update access order
        if query_hash in self.access_order:
            self.access_order.remove(query_hash)
        self.access_order.append(query_hash)

    def invalidate(self, query: str) -> None:
        """Remove specific query from cache.

        Parameters
        ----------
        query : str
            SPARQL query string
        """
        query_hash = self._compute_hash(query)
        if query_hash in self.cache:
            del self.cache[query_hash]
            if query_hash in self.access_order:
                self.access_order.remove(query_hash)

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.access_order.clear()
        self.hits = 0
        self.misses = 0
        self.query_stats.clear()

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate.

        Returns
        -------
        float
            Hit rate as percentage (0.0-1.0)
        """
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_stats(self, query: str | None = None) -> dict[str, Any]:
        """Get cache statistics, optionally scoped to a specific query."""
        total = self.hits + self.misses

        # Analyze entries
        expired_count = sum(1 for e in self.cache.values() if e.is_expired())

        stats = {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": self.hit_rate,
            "expired_entries": expired_count,
            "ttl_default": self.ttl,
        }

        if query:
            query_hash = self._compute_hash(query)
            scoped = self.query_stats.get(query_hash, {"hits": 0, "misses": 0})
            stats.update(
                {
                    "query_hits": scoped["hits"],
                    "query_misses": scoped["misses"],
                    "hits": scoped["hits"],
                    "misses": scoped["misses"],
                }
            )

        return stats

    def _record_hit(self, query_hash: str) -> None:
        """Record cache hit for query."""
        self.hits += 1
        stats = self.query_stats.setdefault(query_hash, {"hits": 0, "misses": 0})
        stats["hits"] += 1

    def _record_miss(self, query_hash: str, query: str | None = None) -> None:
        """Record cache miss for query."""
        self.misses += 1
        stats = self.query_stats.setdefault(query_hash, {"hits": 0, "misses": 0})
        stats["misses"] += 1
        if query is not None and "fingerprint" not in stats:
            stats["fingerprint"] = sha256(f"{query_hash}:{query}".encode()).hexdigest()
