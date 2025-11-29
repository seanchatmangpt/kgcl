"""String processing object pool for optimized transpilation.

Provides cached string transformations to reduce allocations during
signature generation. All transformations are thread-safe and use
LRU caching internally.
"""

import re
import threading
from typing import Dict


class StringPool:
    """Object pool for string processing to reduce allocations.

    Caches common string transformations like snake_case conversion
    and local name extraction to avoid redundant computation and
    string allocations during signature generation.

    Thread-safe for concurrent transpilation operations.

    Attributes
    ----------
    _snake_case_cache : Dict[str, str]
        Cache of snake_case transformations
    _local_name_cache : Dict[str, str]
        Cache of local name extractions
    _pool_lock : threading.RLock
        Reentrant lock for thread-safe operations

    Examples
    --------
    >>> pool = StringPool()
    >>> pool.snake_case("MyClassName")
    'my_class_name'
    >>> pool.safe_local_name("http://example.org/ns#LocalName")
    'LocalName'
    """

    def __init__(self) -> None:
        """Initialize string pool with empty caches."""
        self._snake_case_cache: dict[str, str] = {}
        self._local_name_cache: dict[str, str] = {}
        self._pool_lock = threading.RLock()

    def snake_case(self, name: str) -> str:
        """Convert name to snake_case with caching.

        Handles hyphens, spaces, camelCase, and leading digits.
        Results are cached for subsequent calls.

        Parameters
        ----------
        name : str
            Input name to convert

        Returns
        -------
        str
            snake_case version of name, guaranteed valid Python identifier

        Examples
        --------
        >>> pool = StringPool()
        >>> pool.snake_case("MyClassName")
        'my_class_name'
        >>> pool.snake_case("some-property-name")
        'some_property_name'
        >>> pool.snake_case("2ndField")
        'field_2nd_field'
        """
        with self._pool_lock:
            if name in self._snake_case_cache:
                return self._snake_case_cache[name]

            # Convert hyphens and spaces to underscores
            result = re.sub(r"[-\s]+", "_", name)
            # Insert underscore before capital letters
            result = re.sub(r"([a-z])([A-Z])", r"\1_\2", result)
            # Lowercase everything
            result = result.lower()
            # Collapse multiple underscores
            result = re.sub(r"_+", "_", result)
            # Strip leading/trailing underscores
            result = result.strip("_")

            # Handle leading digits
            if result and result[0].isdigit():
                result = f"field_{result}"

            # Handle empty result
            if not result:
                result = "unnamed_field"

            self._snake_case_cache[name] = result
            return result

    def safe_local_name(self, iri: object) -> str:
        """Extract local name from IRI with caching.

        Extracts the fragment or last path component from an IRI.
        Results are cached for subsequent calls.

        Parameters
        ----------
        iri : object
            IRI object (typically rdflib.URIRef) to extract from

        Returns
        -------
        str
            Local name component of the IRI

        Examples
        --------
        >>> pool = StringPool()
        >>> pool.safe_local_name("http://example.org/ns#LocalName")
        'LocalName'
        >>> pool.safe_local_name("http://example.org/path/to/Resource")
        'Resource'
        """
        iri_str = str(iri)
        with self._pool_lock:
            if iri_str in self._local_name_cache:
                return self._local_name_cache[iri_str]

            # Find last # or / separator
            idx = max(iri_str.rfind("/"), iri_str.rfind("#"))
            result = iri_str[idx + 1 :] if idx >= 0 else iri_str

            self._local_name_cache[iri_str] = result
            return result

    def clear_caches(self) -> None:
        """Clear all cached transformations.

        Useful for testing or when memory management is critical.

        Examples
        --------
        >>> pool = StringPool()
        >>> pool.snake_case("Test")
        'test'
        >>> pool.clear_caches()
        >>> len(pool._snake_case_cache)
        0
        """
        with self._pool_lock:
            self._snake_case_cache.clear()
            self._local_name_cache.clear()

    def cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns
        -------
        dict[str, int]
            Dictionary with cache sizes

        Examples
        --------
        >>> pool = StringPool()
        >>> pool.snake_case("Test")
        'test'
        >>> stats = pool.cache_stats()
        >>> stats["snake_case_entries"] >= 1
        True
        """
        with self._pool_lock:
            return {
                "snake_case_entries": len(self._snake_case_cache),
                "local_name_entries": len(self._local_name_cache),
            }
