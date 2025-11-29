"""Tests for kgcl.codegen.string_pool module.

Chicago School TDD tests verifying cached string transformations
and thread-safe operations.
"""

import threading

import pytest

from kgcl.codegen.string_pool import StringPool


def test_snake_case_simple_camel_case() -> None:
    """Test snake_case converts CamelCase correctly."""
    pool = StringPool()

    result = pool.snake_case("MyClassName")

    assert result == "my_class_name"


def test_snake_case_with_hyphens() -> None:
    """Test snake_case handles hyphens."""
    pool = StringPool()

    result = pool.snake_case("some-property-name")

    assert result == "some_property_name"


def test_snake_case_with_spaces() -> None:
    """Test snake_case handles spaces."""
    pool = StringPool()

    result = pool.snake_case("some property name")

    assert result == "some_property_name"


def test_snake_case_with_leading_digit() -> None:
    """Test snake_case prefixes fields starting with digits."""
    pool = StringPool()

    result = pool.snake_case("2ndField")

    assert result.startswith("field_")
    assert "2nd" in result


def test_snake_case_with_empty_string() -> None:
    """Test snake_case handles empty string."""
    pool = StringPool()

    result = pool.snake_case("")

    assert result == "unnamed_field"


def test_snake_case_with_multiple_underscores() -> None:
    """Test snake_case collapses multiple underscores."""
    pool = StringPool()

    result = pool.snake_case("multiple___underscores")

    assert "___" not in result
    assert result == "multiple_underscores"


def test_snake_case_caching() -> None:
    """Test snake_case caches results for repeated calls."""
    pool = StringPool()

    first = pool.snake_case("TestName")
    second = pool.snake_case("TestName")

    assert first == second
    assert first is second


def test_safe_local_name_with_hash_separator() -> None:
    """Test safe_local_name extracts from hash separator."""
    pool = StringPool()

    result = pool.safe_local_name("http://example.org/ns#LocalName")

    assert result == "LocalName"


def test_safe_local_name_with_slash_separator() -> None:
    """Test safe_local_name extracts from slash separator."""
    pool = StringPool()

    result = pool.safe_local_name("http://example.org/path/to/Resource")

    assert result == "Resource"


def test_safe_local_name_with_no_separator() -> None:
    """Test safe_local_name returns full string when no separator."""
    pool = StringPool()

    result = pool.safe_local_name("LocalName")

    assert result == "LocalName"


def test_safe_local_name_caching() -> None:
    """Test safe_local_name caches results."""
    pool = StringPool()

    first = pool.safe_local_name("http://example.org#Test")
    second = pool.safe_local_name("http://example.org#Test")

    assert first == second
    assert first is second


def test_clear_caches_removes_all_entries() -> None:
    """Test clear_caches empties all caches."""
    pool = StringPool()

    pool.snake_case("Test")
    pool.safe_local_name("http://example.org#Test")

    pool.clear_caches()

    stats = pool.cache_stats()
    assert stats["snake_case_entries"] == 0
    assert stats["local_name_entries"] == 0


def test_cache_stats_counts_entries() -> None:
    """Test cache_stats returns correct counts."""
    pool = StringPool()

    pool.snake_case("First")
    pool.snake_case("Second")
    pool.safe_local_name("http://example.org#Test")

    stats = pool.cache_stats()

    assert stats["snake_case_entries"] == 2
    assert stats["local_name_entries"] == 1


def test_thread_safety_snake_case() -> None:
    """Test snake_case is thread-safe with concurrent access."""
    pool = StringPool()
    results: list[str] = []

    def worker() -> None:
        result = pool.snake_case("ThreadTest")
        results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert all(r == "thread_test" for r in results)


def test_thread_safety_safe_local_name() -> None:
    """Test safe_local_name is thread-safe with concurrent access."""
    pool = StringPool()
    results: list[str] = []

    def worker() -> None:
        result = pool.safe_local_name("http://example.org#Test")
        results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert all(r == "Test" for r in results)


def test_realistic_ontology_names() -> None:
    """Test realistic ontology property names."""
    pool = StringPool()

    assert pool.snake_case("hasValue") == "has_value"
    assert pool.snake_case("relatedTo") == "related_to"
    assert pool.snake_case("isPartOf") == "is_part_of"
    assert pool.safe_local_name("http://purl.org/dc/terms/creator") == "creator"
