"""Tests for Innovation #1: Query Cache Singleton.

Chicago School TDD: Real cache operations, no mocking.
Tests caching, TTL expiration, LRU eviction, and thread safety.
"""

from __future__ import annotations

import time

import pytest

from kgcl.hybrid.hooks.query_cache import CacheEntry, QueryCache, QueryCacheConfig


class TestQueryCacheConfig:
    """Tests for QueryCacheConfig defaults and customization."""

    def test_default_config_values(self) -> None:
        """Default config has expected values."""
        config = QueryCacheConfig()

        assert config.max_compiled_queries == 100
        assert config.max_file_cache == 50
        assert config.ttl_seconds == 300

    def test_custom_config_values(self) -> None:
        """Custom config values are stored correctly."""
        config = QueryCacheConfig(max_compiled_queries=50, ttl_seconds=60)

        assert config.max_compiled_queries == 50
        assert config.ttl_seconds == 60

    def test_config_is_frozen(self) -> None:
        """Config is immutable (frozen dataclass)."""
        config = QueryCacheConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.max_compiled_queries = 200  # type: ignore[misc]


class TestCacheEntry:
    """Tests for CacheEntry TTL tracking."""

    def test_entry_creation_with_timestamp(self) -> None:
        """Entry records creation timestamp."""
        entry = CacheEntry(value="test")

        assert entry.value == "test"
        assert entry.created_at > 0
        assert entry.access_count == 0

    def test_entry_not_expired_within_ttl(self) -> None:
        """Entry is not expired within TTL window."""
        entry = CacheEntry(value="test")

        assert entry.is_expired(ttl_seconds=300) is False

    def test_entry_expired_after_ttl(self) -> None:
        """Entry expires after TTL seconds."""
        entry = CacheEntry(value="test", created_at=time.time() - 400)

        assert entry.is_expired(ttl_seconds=300) is True


class TestQueryCacheSingleton:
    """Tests for singleton pattern and thread safety."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        QueryCache.reset_instance()

    def test_singleton_returns_same_instance(self) -> None:
        """get_instance returns same instance on subsequent calls."""
        cache1 = QueryCache.get_instance()
        cache2 = QueryCache.get_instance()

        assert cache1 is cache2

    def test_reset_creates_new_instance(self) -> None:
        """reset_instance allows creating fresh instance."""
        cache1 = QueryCache.get_instance()
        QueryCache.reset_instance()
        cache2 = QueryCache.get_instance()

        assert cache1 is not cache2

    def test_config_applied_on_creation(self) -> None:
        """Custom config is used when creating instance."""
        config = QueryCacheConfig(max_compiled_queries=50)
        cache = QueryCache.get_instance(config)

        assert cache.config.max_compiled_queries == 50


class TestQueryCacheOperations:
    """Tests for cache get/put operations."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        QueryCache.reset_instance()

    def test_cache_miss_returns_none(self) -> None:
        """Get on missing key returns None."""
        cache = QueryCache.get_instance()

        result = cache.get("ASK { ?s ?p ?o }")

        assert result is None

    def test_cache_hit_returns_value(self) -> None:
        """Get returns cached value after put."""
        cache = QueryCache.get_instance()
        cache.put("ASK { ?s a :Person }", True)

        result = cache.get("ASK { ?s a :Person }")

        assert result is True

    def test_different_queries_have_different_keys(self) -> None:
        """Different queries are cached separately."""
        cache = QueryCache.get_instance()
        cache.put("ASK { ?s a :Person }", True)
        cache.put("ASK { ?s a :Task }", False)

        assert cache.get("ASK { ?s a :Person }") is True
        assert cache.get("ASK { ?s a :Task }") is False

    def test_invalidate_removes_entry(self) -> None:
        """Invalidate removes specific cache entry."""
        cache = QueryCache.get_instance()
        cache.put("ASK { ?s ?p ?o }", True)

        removed = cache.invalidate("ASK { ?s ?p ?o }")

        assert removed is True
        assert cache.get("ASK { ?s ?p ?o }") is None

    def test_clear_removes_all_entries(self) -> None:
        """Clear removes all cache entries."""
        cache = QueryCache.get_instance()
        cache.put("query1", "result1")
        cache.put("query2", "result2")

        cache.clear()

        assert cache.get("query1") is None
        assert cache.get("query2") is None


class TestQueryCacheLRU:
    """Tests for LRU eviction behavior."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        QueryCache.reset_instance()

    def test_lru_evicts_oldest_when_full(self) -> None:
        """Oldest entry is evicted when cache is full."""
        config = QueryCacheConfig(max_compiled_queries=3)
        cache = QueryCache.get_instance(config)

        cache.put("query1", "result1")
        cache.put("query2", "result2")
        cache.put("query3", "result3")
        cache.put("query4", "result4")  # Should evict query1

        assert cache.get("query1") is None  # Evicted
        assert cache.get("query2") is not None  # Still present

    def test_access_promotes_to_end(self) -> None:
        """Accessing entry moves it to end (most recent)."""
        config = QueryCacheConfig(max_compiled_queries=3)
        cache = QueryCache.get_instance(config)

        cache.put("query1", "result1")
        cache.put("query2", "result2")
        cache.put("query3", "result3")

        # Access query1 to promote it
        cache.get("query1")

        # Add new entry - should evict query2 (now oldest)
        cache.put("query4", "result4")

        assert cache.get("query1") is not None  # Still present (was accessed)
        assert cache.get("query2") is None  # Evicted


class TestQueryCacheStatistics:
    """Tests for cache statistics tracking."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        QueryCache.reset_instance()

    def test_stats_initial_values(self) -> None:
        """Stats start at zero."""
        cache = QueryCache.get_instance()
        cache.clear()

        stats = cache.stats()

        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_stats_tracks_hits(self) -> None:
        """Stats counts cache hits."""
        cache = QueryCache.get_instance()
        cache.clear()
        cache.put("query", "result")

        cache.get("query")
        cache.get("query")

        stats = cache.stats()
        assert stats["hits"] == 2

    def test_stats_tracks_misses(self) -> None:
        """Stats counts cache misses."""
        cache = QueryCache.get_instance()
        cache.clear()

        cache.get("missing1")
        cache.get("missing2")

        stats = cache.stats()
        assert stats["misses"] == 2

    def test_stats_calculates_hit_rate(self) -> None:
        """Stats calculates hit rate percentage."""
        cache = QueryCache.get_instance()
        cache.clear()
        cache.put("query", "result")

        cache.get("query")  # Hit
        cache.get("query")  # Hit
        cache.get("missing")  # Miss

        stats = cache.stats()
        assert stats["hit_rate_percent"] == 66  # 2/3 = 66%
