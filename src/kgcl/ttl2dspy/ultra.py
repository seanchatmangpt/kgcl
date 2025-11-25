"""Ultra-optimized caching and performance system."""

import hashlib
import json
import logging
import pickle
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rdflib import Graph

from .parser import OntologyParser, SHACLShape
from .generator import DSPyGenerator, SignatureDefinition

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for caching system."""

    # Memory cache
    memory_cache_enabled: bool = True
    max_memory_cache_size: int = 100  # Max items

    # Disk cache
    disk_cache_enabled: bool = True
    disk_cache_dir: Optional[Path] = None
    max_disk_cache_age: int = 86400  # 24 hours in seconds

    # Redis cache (optional)
    redis_enabled: bool = False
    redis_url: Optional[str] = None
    redis_prefix: str = "ttl2dspy:"
    redis_ttl: int = 3600  # 1 hour

    # Lazy loading
    lazy_loading_enabled: bool = True

    # Indexing
    shape_indexing_enabled: bool = True

    def __post_init__(self):
        """Set default disk cache directory."""
        if self.disk_cache_enabled and self.disk_cache_dir is None:
            self.disk_cache_dir = Path.home() / ".cache" / "ttl2dspy"

        if self.disk_cache_dir:
            self.disk_cache_dir = Path(self.disk_cache_dir)
            self.disk_cache_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class CacheStats:
    """Cache performance statistics."""

    memory_hits: int = 0
    memory_misses: int = 0
    disk_hits: int = 0
    disk_misses: int = 0
    redis_hits: int = 0
    redis_misses: int = 0
    total_parse_time: float = 0.0
    total_generate_time: float = 0.0
    total_write_time: float = 0.0

    @property
    def memory_hit_rate(self) -> float:
        """Calculate memory cache hit rate."""
        total = self.memory_hits + self.memory_misses
        return self.memory_hits / total if total > 0 else 0.0

    @property
    def disk_hit_rate(self) -> float:
        """Calculate disk cache hit rate."""
        total = self.disk_hits + self.disk_misses
        return self.disk_hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "memory_hit_rate": self.memory_hit_rate,
            "disk_hit_rate": self.disk_hit_rate,
        }


class ShapeIndex:
    """Fast lookup index for SHACL shapes."""

    def __init__(self):
        """Initialize index."""
        self._by_name: Dict[str, SHACLShape] = {}
        self._by_uri: Dict[str, SHACLShape] = {}
        self._by_target_class: Dict[str, List[SHACLShape]] = {}

    def add(self, shape: SHACLShape):
        """Add a shape to the index."""
        self._by_name[shape.name] = shape
        self._by_uri[str(shape.uri)] = shape

        if shape.target_class:
            target_key = str(shape.target_class)
            if target_key not in self._by_target_class:
                self._by_target_class[target_key] = []
            self._by_target_class[target_key].append(shape)

    def find_by_name(self, name: str) -> Optional[SHACLShape]:
        """Find shape by name."""
        return self._by_name.get(name)

    def find_by_uri(self, uri: str) -> Optional[SHACLShape]:
        """Find shape by URI."""
        return self._by_uri.get(uri)

    def find_by_target_class(self, target_class: str) -> List[SHACLShape]:
        """Find shapes by target class."""
        return self._by_target_class.get(target_class, [])

    def clear(self):
        """Clear the index."""
        self._by_name.clear()
        self._by_uri.clear()
        self._by_target_class.clear()


class UltraOptimizer:
    """Ultra-optimized caching and performance system."""

    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize optimizer.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self.stats = CacheStats()

        # Components
        self.parser = OntologyParser(cache_enabled=self.config.memory_cache_enabled)
        self.generator = DSPyGenerator()

        # Indexes
        self.shape_index = ShapeIndex()

        # Caches
        self._memory_cache: Dict[str, Any] = {}
        self._redis_client = None

        # Initialize Redis if enabled
        if self.config.redis_enabled:
            self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            self._redis_client = redis.from_url(
                self.config.redis_url or "redis://localhost:6379"
            )
            self._redis_client.ping()
            logger.info("Redis cache initialized")
        except ImportError:
            logger.warning("Redis library not installed, disabling Redis cache")
            self.config.redis_enabled = False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.config.redis_enabled = False

    def parse_with_cache(self, ttl_path: Union[str, Path]) -> List[SHACLShape]:
        """Parse TTL file with multi-level caching.

        Args:
            ttl_path: Path to TTL file

        Returns:
            List of SHACL shapes
        """
        ttl_path = Path(ttl_path)
        cache_key = self._get_file_cache_key(ttl_path)

        start_time = time.time()

        # Try memory cache
        if self.config.memory_cache_enabled:
            cached = self._memory_cache.get(cache_key)
            if cached:
                self.stats.memory_hits += 1
                logger.debug(f"Memory cache hit for {ttl_path.name}")
                return cached
            self.stats.memory_misses += 1

        # Try Redis cache
        if self.config.redis_enabled:
            cached = self._redis_get(cache_key)
            if cached:
                self.stats.redis_hits += 1
                logger.debug(f"Redis cache hit for {ttl_path.name}")
                # Store in memory cache
                if self.config.memory_cache_enabled:
                    self._memory_cache[cache_key] = cached
                return cached
            self.stats.redis_misses += 1

        # Try disk cache
        if self.config.disk_cache_enabled:
            cached = self._disk_get(cache_key)
            if cached:
                self.stats.disk_hits += 1
                logger.debug(f"Disk cache hit for {ttl_path.name}")
                # Store in higher-level caches
                if self.config.memory_cache_enabled:
                    self._memory_cache[cache_key] = cached
                if self.config.redis_enabled:
                    self._redis_set(cache_key, cached)
                return cached
            self.stats.disk_misses += 1

        # Parse from source
        logger.info(f"Parsing {ttl_path.name} from source")
        graph = self.parser.parse_file(ttl_path)
        shapes = self.parser.extract_shapes(graph)

        # Index shapes
        if self.config.shape_indexing_enabled:
            for shape in shapes:
                self.shape_index.add(shape)

        # Cache at all levels
        if self.config.memory_cache_enabled:
            self._memory_cache[cache_key] = shapes
        if self.config.disk_cache_enabled:
            self._disk_set(cache_key, shapes)
        if self.config.redis_enabled:
            self._redis_set(cache_key, shapes)

        parse_time = time.time() - start_time
        self.stats.total_parse_time += parse_time
        logger.info(f"Parsed {len(shapes)} shapes in {parse_time:.3f}s")

        return shapes

    def generate_with_cache(self, shapes: List[SHACLShape]) -> str:
        """Generate code with caching.

        Args:
            shapes: List of SHACL shapes

        Returns:
            Generated Python code
        """
        start_time = time.time()

        # Generate cache key from shapes
        cache_key = self._get_shapes_cache_key(shapes)

        # Try memory cache
        if self.config.memory_cache_enabled:
            cached = self._memory_cache.get(cache_key)
            if cached:
                self.stats.memory_hits += 1
                logger.debug("Memory cache hit for generated code")
                return cached
            self.stats.memory_misses += 1

        # Try disk cache
        if self.config.disk_cache_enabled:
            cached = self._disk_get(cache_key)
            if cached:
                self.stats.disk_hits += 1
                logger.debug("Disk cache hit for generated code")
                if self.config.memory_cache_enabled:
                    self._memory_cache[cache_key] = cached
                return cached
            self.stats.disk_misses += 1

        # Generate from scratch
        logger.info(f"Generating code for {len(shapes)} shapes")
        code = self.generator.generate_module(shapes)

        # Cache it
        if self.config.memory_cache_enabled:
            self._memory_cache[cache_key] = code
        if self.config.disk_cache_enabled:
            self._disk_set(cache_key, code)

        generate_time = time.time() - start_time
        self.stats.total_generate_time += generate_time
        logger.info(f"Generated code in {generate_time:.3f}s")

        return code

    def batch_parse(self, ttl_paths: List[Union[str, Path]]) -> Dict[str, List[SHACLShape]]:
        """Parse multiple TTL files in batch.

        Args:
            ttl_paths: List of TTL file paths

        Returns:
            Dictionary mapping file path to shapes
        """
        results = {}
        for ttl_path in ttl_paths:
            ttl_path = Path(ttl_path)
            try:
                shapes = self.parse_with_cache(ttl_path)
                results[str(ttl_path)] = shapes
            except Exception as e:
                logger.error(f"Failed to parse {ttl_path}: {e}")
                results[str(ttl_path)] = []

        return results

    def _get_file_cache_key(self, path: Path) -> str:
        """Generate cache key for a file."""
        stat = path.stat()
        return f"parse:{path}:{stat.st_mtime}:{stat.st_size}"

    def _get_shapes_cache_key(self, shapes: List[SHACLShape]) -> str:
        """Generate cache key for shapes."""
        # Use shape URIs and properties
        shape_data = [
            (str(s.uri), len(s.properties), len(s.input_properties), len(s.output_properties))
            for s in shapes
        ]
        data_str = json.dumps(shape_data, sort_keys=True)
        hash_val = hashlib.sha256(data_str.encode()).hexdigest()
        return f"generate:{hash_val}"

    def _disk_get(self, key: str) -> Optional[Any]:
        """Get from disk cache."""
        if not self.config.disk_cache_dir:
            return None

        cache_file = self.config.disk_cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.pkl"

        if not cache_file.exists():
            return None

        # Check age
        age = time.time() - cache_file.stat().st_mtime
        if age > self.config.max_disk_cache_age:
            logger.debug(f"Disk cache expired for {key}")
            cache_file.unlink()
            return None

        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load disk cache: {e}")
            return None

    def _disk_set(self, key: str, value: Any):
        """Set to disk cache."""
        if not self.config.disk_cache_dir:
            return

        cache_file = self.config.disk_cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.pkl"

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"Failed to save disk cache: {e}")

    def _redis_get(self, key: str) -> Optional[Any]:
        """Get from Redis cache."""
        if not self._redis_client:
            return None

        try:
            redis_key = f"{self.config.redis_prefix}{key}"
            data = self._redis_client.get(redis_key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")

        return None

    def _redis_set(self, key: str, value: Any):
        """Set to Redis cache."""
        if not self._redis_client:
            return

        try:
            redis_key = f"{self.config.redis_prefix}{key}"
            data = pickle.dumps(value)
            self._redis_client.setex(redis_key, self.config.redis_ttl, data)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    def clear_all_caches(self):
        """Clear all caches."""
        # Memory cache
        self._memory_cache.clear()

        # Parser and generator caches
        self.parser.clear_cache()
        self.generator.clear_cache()

        # Shape index
        self.shape_index.clear()

        # Disk cache
        if self.config.disk_cache_dir and self.config.disk_cache_dir.exists():
            for cache_file in self.config.disk_cache_dir.glob("*.pkl"):
                cache_file.unlink()

        # Redis cache
        if self._redis_client:
            try:
                pattern = f"{self.config.redis_prefix}*"
                for key in self._redis_client.scan_iter(match=pattern):
                    self._redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

        logger.info("Cleared all caches")

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return {
            "cache": self.stats.to_dict(),
            "parser": self.parser.get_cache_stats(),
            "generator": self.generator.get_cache_stats(),
            "index": {
                "shapes_by_name": len(self.shape_index._by_name),
                "shapes_by_uri": len(self.shape_index._by_uri),
                "target_classes": len(self.shape_index._by_target_class),
            },
        }
