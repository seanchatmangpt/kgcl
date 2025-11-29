"""Tests for kgcl.codegen.cache module.

Chicago School TDD tests verifying graph caching behavior with
memory, disk, and optional Redis tiers.
"""

import tempfile
from pathlib import Path

import pytest
from rdflib import Graph, Namespace

from kgcl.codegen.cache import GraphCache


@pytest.fixture
def temp_ttl_file() -> Path:
    """Create a temporary TTL file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
        f.write(
            """
@prefix ex: <http://example.org/> .

ex:TestClass a ex:Class .
"""
        )
        return Path(f.name)


def test_cache_initialization() -> None:
    """Test cache initializes with correct defaults."""
    cache = GraphCache(max_size=50, enable_disk_cache=False)

    assert len(cache.memory_cache) == 0
    assert cache.max_size == 50


def test_cache_miss_returns_none(temp_ttl_file: Path) -> None:
    """Test cache miss returns None for uncached file."""
    cache = GraphCache(enable_disk_cache=False)

    result = cache.get(temp_ttl_file)

    assert result is None


def test_cache_put_and_get(temp_ttl_file: Path) -> None:
    """Test putting and getting graph from cache."""
    cache = GraphCache(enable_disk_cache=False)
    graph = Graph()

    cache.put(temp_ttl_file, graph)
    result = cache.get(temp_ttl_file)

    assert result is not None
    assert isinstance(result, Graph)


def test_cache_hit_after_put(temp_ttl_file: Path) -> None:
    """Test cache returns same graph instance after put."""
    cache = GraphCache(enable_disk_cache=False)
    graph = Graph()

    cache.put(temp_ttl_file, graph)
    cached = cache.get(temp_ttl_file)

    assert cached is graph


def test_lru_eviction_when_max_size_exceeded() -> None:
    """Test LRU eviction when cache reaches max size."""
    cache = GraphCache(max_size=2, enable_disk_cache=False)

    file1 = Path("test1.ttl")
    file1.write_text("@prefix ex: <http://example.org/> .\nex:Class1 a ex:Class .")

    file2 = Path("test2.ttl")
    file2.write_text("@prefix ex: <http://example.org/> .\nex:Class2 a ex:Class .")

    file3 = Path("test3.ttl")
    file3.write_text("@prefix ex: <http://example.org/> .\nex:Class3 a ex:Class .")

    try:
        cache.put(file1, Graph())
        cache.put(file2, Graph())
        cache.put(file3, Graph())

        assert len(cache.memory_cache) == 2

    finally:
        file1.unlink(missing_ok=True)
        file2.unlink(missing_ok=True)
        file3.unlink(missing_ok=True)


def test_cache_invalidation_on_file_change(temp_ttl_file: Path) -> None:
    """Test cache key changes when file content changes."""
    cache = GraphCache(enable_disk_cache=False)

    original_key = cache._get_cache_key(temp_ttl_file)

    temp_ttl_file.write_text("@prefix ex: <http://example.org/> .\nex:Modified a ex:Class .")

    new_key = cache._get_cache_key(temp_ttl_file)

    assert original_key != new_key


def test_disk_cache_persistence() -> None:
    """Test disk cache persists across cache instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".cache"

        file = Path(tmpdir) / "test.ttl"
        file.write_text("@prefix ex: <http://example.org/> .\nex:Test a ex:Class .")

        cache1 = GraphCache(max_size=10, enable_disk_cache=True)
        cache1.cache_dir = cache_dir
        cache1.cache_dir.mkdir(exist_ok=True)

        graph = Graph()
        cache1.put(file, graph)

        cache2 = GraphCache(max_size=10, enable_disk_cache=True)
        cache2.cache_dir = cache_dir

        result = cache2.get(file)

        assert result is not None


def test_clear_removes_all_entries(temp_ttl_file: Path) -> None:
    """Test clear removes all cache entries."""
    cache = GraphCache(enable_disk_cache=False)

    cache.put(temp_ttl_file, Graph())
    cache.clear()

    assert len(cache.memory_cache) == 0
    assert len(cache.access_times) == 0


def test_stats_returns_correct_counts(temp_ttl_file: Path) -> None:
    """Test stats returns accurate cache statistics."""
    cache = GraphCache(max_size=10, enable_disk_cache=False)

    cache.put(temp_ttl_file, Graph())
    stats = cache.stats()

    assert stats["memory_entries"] == 1
    assert stats["max_size"] == 10


def test_cache_with_disk_disabled_has_zero_disk_entries() -> None:
    """Test disk_entries is zero when disk cache disabled."""
    cache = GraphCache(enable_disk_cache=False)

    stats = cache.stats()

    assert stats["disk_entries"] == 0


def test_access_time_updates_on_cache_hit(temp_ttl_file: Path) -> None:
    """Test access time updates when cache hit occurs."""
    cache = GraphCache(enable_disk_cache=False)

    cache.put(temp_ttl_file, Graph())

    cache_key = cache._get_cache_key(temp_ttl_file)
    first_access_time = cache.access_times[cache_key]

    import time

    time.sleep(0.01)

    cache.get(temp_ttl_file)
    second_access_time = cache.access_times[cache_key]

    assert second_access_time > first_access_time
