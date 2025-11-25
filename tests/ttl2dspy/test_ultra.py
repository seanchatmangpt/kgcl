"""Tests for ultra-optimized caching system."""

import pytest
import time
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SH, XSD

from kgcl.ttl2dspy.ultra import UltraOptimizer, CacheConfig, ShapeIndex
from kgcl.ttl2dspy.parser import SHACLShape, PropertyShape


@pytest.fixture
def sample_ttl_file(tmp_path):
    """Create a sample TTL file."""
    g = Graph()
    EX = Namespace("http://example.org/")

    # Define a simple NodeShape
    shape_uri = EX.TestShape
    g.add((shape_uri, RDF.type, SH.NodeShape))
    g.add((shape_uri, RDFS.comment, Literal("Test shape")))

    prop = EX.TestShape_prop
    g.add((shape_uri, SH.property, prop))
    g.add((prop, SH.path, EX.prop))
    g.add((prop, SH.datatype, XSD.string))
    g.add((prop, SH.minCount, Literal(1)))

    ttl_file = tmp_path / "test.ttl"
    g.serialize(str(ttl_file), format="turtle")

    return ttl_file


class TestCacheConfig:
    """Tests for CacheConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = CacheConfig()

        assert config.memory_cache_enabled is True
        assert config.disk_cache_enabled is True
        assert config.disk_cache_dir is not None
        assert config.lazy_loading_enabled is True
        assert config.shape_indexing_enabled is True

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        config = CacheConfig(
            memory_cache_enabled=False,
            disk_cache_dir=tmp_path / "cache",
            max_disk_cache_age=3600,
        )

        assert config.memory_cache_enabled is False
        assert config.disk_cache_dir == tmp_path / "cache"
        assert config.max_disk_cache_age == 3600


class TestShapeIndex:
    """Tests for ShapeIndex class."""

    def test_add_and_find_by_name(self):
        """Test adding and finding shapes by name."""
        index = ShapeIndex()

        shape = SHACLShape(
            uri=URIRef("http://example.org/TestShape"),
            name="TestShape",
        )

        index.add(shape)

        found = index.find_by_name("TestShape")
        assert found is shape

    def test_find_by_uri(self):
        """Test finding shapes by URI."""
        index = ShapeIndex()

        shape = SHACLShape(
            uri=URIRef("http://example.org/TestShape"),
            name="TestShape",
        )

        index.add(shape)

        found = index.find_by_uri("http://example.org/TestShape")
        assert found is shape

    def test_find_by_target_class(self):
        """Test finding shapes by target class."""
        index = ShapeIndex()

        shape1 = SHACLShape(
            uri=URIRef("http://example.org/Shape1"),
            name="Shape1",
            target_class=URIRef("http://example.org/Person"),
        )

        shape2 = SHACLShape(
            uri=URIRef("http://example.org/Shape2"),
            name="Shape2",
            target_class=URIRef("http://example.org/Person"),
        )

        index.add(shape1)
        index.add(shape2)

        found = index.find_by_target_class("http://example.org/Person")
        assert len(found) == 2
        assert shape1 in found
        assert shape2 in found

    def test_clear(self):
        """Test clearing the index."""
        index = ShapeIndex()

        shape = SHACLShape(
            uri=URIRef("http://example.org/TestShape"),
            name="TestShape",
        )

        index.add(shape)
        assert len(index._by_name) == 1

        index.clear()
        assert len(index._by_name) == 0


class TestUltraOptimizer:
    """Tests for UltraOptimizer class."""

    def test_initialization(self):
        """Test optimizer initialization."""
        config = CacheConfig(memory_cache_enabled=True)
        optimizer = UltraOptimizer(config)

        assert optimizer.config is config
        assert optimizer.parser is not None
        assert optimizer.generator is not None
        assert optimizer.shape_index is not None

    def test_parse_with_cache(self, sample_ttl_file):
        """Test parsing with caching."""
        config = CacheConfig(memory_cache_enabled=True, disk_cache_enabled=False)
        optimizer = UltraOptimizer(config)

        # First parse
        shapes1 = optimizer.parse_with_cache(sample_ttl_file)
        assert len(shapes1) == 1
        assert optimizer.stats.memory_misses == 1

        # Second parse (should use cache)
        shapes2 = optimizer.parse_with_cache(sample_ttl_file)
        assert shapes1 is shapes2
        assert optimizer.stats.memory_hits == 1

    def test_disk_cache(self, sample_ttl_file, tmp_path):
        """Test disk caching."""
        config = CacheConfig(
            memory_cache_enabled=False,
            disk_cache_enabled=True,
            disk_cache_dir=tmp_path / "cache",
        )
        optimizer = UltraOptimizer(config)

        # First parse
        shapes1 = optimizer.parse_with_cache(sample_ttl_file)
        assert len(shapes1) == 1
        assert optimizer.stats.disk_misses == 1

        # Create new optimizer (no memory cache)
        optimizer2 = UltraOptimizer(config)

        # Second parse (should use disk cache)
        shapes2 = optimizer2.parse_with_cache(sample_ttl_file)
        assert len(shapes2) == 1
        assert optimizer2.stats.disk_hits == 1

    def test_generate_with_cache(self):
        """Test code generation with caching."""
        config = CacheConfig(memory_cache_enabled=True, disk_cache_enabled=False)
        optimizer = UltraOptimizer(config)

        shapes = [
            SHACLShape(
                uri=URIRef("http://example.org/TestShape"),
                name="TestShape",
                properties=[
                    PropertyShape(
                        path=URIRef("http://example.org/prop"),
                        name="prop",
                        datatype=XSD.string,
                        min_count=1,
                    ),
                ],
            ),
        ]
        shapes[0].categorize_properties()

        # First generation
        code1 = optimizer.generate_with_cache(shapes)
        assert "class TestShapeSignature(dspy.Signature):" in code1
        assert optimizer.stats.memory_misses == 1

        # Second generation (should use cache)
        code2 = optimizer.generate_with_cache(shapes)
        assert code1 == code2
        assert optimizer.stats.memory_hits == 1

    def test_batch_parse(self, tmp_path):
        """Test batch parsing."""
        # Create multiple TTL files
        files = []
        for i in range(3):
            g = Graph()
            EX = Namespace("http://example.org/")

            shape_uri = EX[f"Shape{i}"]
            g.add((shape_uri, RDF.type, SH.NodeShape))

            prop = EX[f"Shape{i}_prop"]
            g.add((shape_uri, SH.property, prop))
            g.add((prop, SH.path, EX.prop))
            g.add((prop, SH.datatype, XSD.string))
            g.add((prop, SH.minCount, Literal(1)))

            ttl_file = tmp_path / f"test{i}.ttl"
            g.serialize(str(ttl_file), format="turtle")
            files.append(ttl_file)

        optimizer = UltraOptimizer()
        results = optimizer.batch_parse(files)

        assert len(results) == 3
        for ttl_file in files:
            assert str(ttl_file) in results
            assert len(results[str(ttl_file)]) == 1

    def test_clear_all_caches(self, tmp_path):
        """Test clearing all caches."""
        config = CacheConfig(disk_cache_dir=tmp_path / "cache")
        optimizer = UltraOptimizer(config)

        # Add some data
        optimizer._memory_cache["test"] = "value"
        optimizer.parser._graph_cache["test"] = Graph()
        optimizer.shape_index.add(
            SHACLShape(
                uri=URIRef("http://example.org/Test"),
                name="Test",
            )
        )

        # Create a disk cache file
        cache_file = config.disk_cache_dir / "test.pkl"
        config.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("test")

        optimizer.clear_all_caches()

        assert len(optimizer._memory_cache) == 0
        assert len(optimizer.parser._graph_cache) == 0
        assert len(optimizer.shape_index._by_name) == 0
        assert not cache_file.exists()

    def test_get_stats(self):
        """Test getting statistics."""
        optimizer = UltraOptimizer()
        stats = optimizer.get_stats()

        assert stats.memory_hits == 0
        assert stats.memory_misses == 0
        assert stats.disk_hits == 0
        assert stats.disk_misses == 0

    def test_get_detailed_stats(self):
        """Test getting detailed statistics."""
        optimizer = UltraOptimizer()
        stats = optimizer.get_detailed_stats()

        assert "cache" in stats
        assert "parser" in stats
        assert "generator" in stats
        assert "index" in stats
