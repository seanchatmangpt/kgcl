"""
Tests for semantic AI modules.

Covers embeddings, semantic analysis, and NLP query building.
"""

import math

import pytest

from kgcl.hooks.embeddings import EmbeddingsManager
from kgcl.hooks.nlp_query_builder import NLPQuery, NLPQueryBuilder
from kgcl.hooks.semantic_analysis import (
    EntityType,
    RelationType,
    SemanticAnalyzer,
    SemanticEntity,
)


class TestEmbeddingsManager:
    """Test embeddings manager functionality."""

    def test_init(self):
        """Test embeddings manager initialization."""
        manager = EmbeddingsManager(model="simple-hash", cache_size=100)
        assert manager.model == "simple-hash"
        assert manager.cache_size == 100
        assert len(manager.embeddings_cache) == 0

    def test_embed_text_hash(self):
        """Test hash-based embedding generation."""
        manager = EmbeddingsManager(model="simple-hash")
        text = "knowledge graph semantic search"

        embedding = manager.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 128  # Default dimension
        assert all(isinstance(x, float) for x in embedding)

        # Check normalization (unit vector)
        magnitude = math.sqrt(sum(x * x for x in embedding))
        assert abs(magnitude - 1.0) < 0.01

    def test_embed_text_caching(self):
        """Test embedding caching."""
        manager = EmbeddingsManager()
        text = "test caching"

        # First call - cache miss
        embedding1 = manager.embed_text(text)
        assert manager._stats["cache_misses"] == 1
        assert manager._stats["cache_hits"] == 0

        # Second call - cache hit
        embedding2 = manager.embed_text(text)
        assert manager._stats["cache_hits"] == 1
        assert embedding1 == embedding2

    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        manager = EmbeddingsManager()

        # Identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        sim = manager.cosine_similarity(vec1, vec2)
        assert abs(sim - 1.0) < 0.01

        # Orthogonal vectors
        vec3 = [1.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0]
        sim = manager.cosine_similarity(vec3, vec4)
        assert abs(sim - 0.0) < 0.01

        # Opposite vectors
        vec5 = [1.0, 0.0, 0.0]
        vec6 = [-1.0, 0.0, 0.0]
        sim = manager.cosine_similarity(vec5, vec6)
        assert abs(sim - (-1.0)) < 0.01

    def test_euclidean_distance(self):
        """Test Euclidean distance computation."""
        manager = EmbeddingsManager()

        # Identical vectors
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        dist = manager.euclidean_distance(vec1, vec2)
        assert abs(dist - 0.0) < 0.01

        # Different vectors
        vec3 = [0.0, 0.0, 0.0]
        vec4 = [3.0, 4.0, 0.0]
        dist = manager.euclidean_distance(vec3, vec4)
        assert abs(dist - 5.0) < 0.01  # 3-4-5 triangle

    def test_find_similar(self):
        """Test finding similar texts."""
        manager = EmbeddingsManager()

        query = "semantic search"
        candidates = [
            "semantic search algorithm",
            "knowledge graph query",
            "unrelated topic here",
            "semantic analysis tools",
        ]

        results = manager.find_similar(query, candidates, top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)

        # First result should be most similar
        text1, score1 = results[0]
        _text2, score2 = results[1]
        assert score1 >= score2

        # Should find semantically related texts
        assert "semantic" in text1.lower() or "search" in text1.lower()

    def test_batch_embed(self):
        """Test batch embedding generation."""
        manager = EmbeddingsManager()

        texts = ["first text", "second text", "third text"]

        embeddings = manager.batch_embed(texts)

        assert len(embeddings) == 3
        assert all(isinstance(e, list) for e in embeddings)
        assert all(len(e) == 128 for e in embeddings)

    def test_tfidf_embedding(self):
        """Test TF-IDF based embeddings."""
        manager = EmbeddingsManager(model="tfidf")

        texts = [
            "knowledge graph semantic search",
            "database query optimization",
            "semantic web ontology",
        ]

        # Build vocabulary
        embeddings = manager.batch_embed(texts)

        assert len(embeddings) == 3
        assert manager.vocabulary  # Vocabulary built
        assert manager.idf_scores  # IDF scores computed

    def test_cache_eviction(self):
        """Test cache eviction when full."""
        manager = EmbeddingsManager(cache_size=2)

        # Fill cache
        manager.embed_text("text1")
        manager.embed_text("text2")
        assert len(manager.embeddings_cache) == 2

        # Trigger eviction
        manager.embed_text("text3")
        assert len(manager.embeddings_cache) == 2  # Still at limit

    def test_get_stats(self):
        """Test statistics retrieval."""
        manager = EmbeddingsManager()

        manager.embed_text("test1")
        manager.embed_text("test1")  # Cache hit
        manager.embed_text("test2")

        stats = manager.get_stats()

        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["embeddings_generated"] == 2
        assert stats["cache_size"] == 2

    def test_clear_cache(self):
        """Test cache clearing."""
        manager = EmbeddingsManager()

        manager.embed_text("test1")
        manager.embed_text("test2")
        assert len(manager.embeddings_cache) > 0

        manager.clear_cache()
        assert len(manager.embeddings_cache) == 0
        assert manager._stats["cache_hits"] == 0


class TestSemanticAnalyzer:
    """Test semantic analyzer functionality."""

    def test_init(self):
        """Test semantic analyzer initialization."""
        analyzer = SemanticAnalyzer()

        assert analyzer.entity_patterns
        assert analyzer.relation_patterns
        assert analyzer.sentiment_keywords

    def test_extract_entities(self):
        """Test entity extraction."""
        analyzer = SemanticAnalyzer()

        text = "John Smith works at Microsoft Corporation in Seattle, WA."

        entities = analyzer.extract_entities(text)

        assert len(entities) > 0
        assert all(isinstance(e, SemanticEntity) for e in entities)

        # Check for person entity
        person_entities = [e for e in entities if e.entity_type == EntityType.PERSON]
        assert len(person_entities) > 0

    def test_extract_entities_confidence(self):
        """Test entity confidence scores."""
        analyzer = SemanticAnalyzer()

        text = "Dr. Watson is a person."

        entities = analyzer.extract_entities(text, min_confidence=0.5)

        assert all(e.confidence >= 0.5 for e in entities)

    def test_extract_relations(self):
        """Test relation extraction."""
        analyzer = SemanticAnalyzer()

        text = "A dog is an animal. A car has wheels."

        relations = analyzer.extract_relations(text)

        assert len(relations) > 0

        # Check for is_a relation
        is_a_relations = [r for r in relations if r.relation == RelationType.IS_A]
        assert len(is_a_relations) > 0

    def test_analyze_sentiment_positive(self):
        """Test positive sentiment analysis."""
        analyzer = SemanticAnalyzer()

        text = "This is a great and excellent solution. Perfect success!"

        sentiment = analyzer.analyze_sentiment(text)

        assert sentiment["positive"] > sentiment["negative"]

    def test_analyze_sentiment_negative(self):
        """Test negative sentiment analysis."""
        analyzer = SemanticAnalyzer()

        text = "This is terrible and awful. Complete failure with errors."

        sentiment = analyzer.analyze_sentiment(text)

        assert sentiment["negative"] > sentiment["positive"]

    def test_analyze_sentiment_neutral(self):
        """Test neutral sentiment analysis."""
        analyzer = SemanticAnalyzer()

        text = "The system operates in a standard manner."

        sentiment = analyzer.analyze_sentiment(text)

        # Should have some neutral score
        assert "neutral" in sentiment

    def test_extract_keywords(self):
        """Test keyword extraction."""
        analyzer = SemanticAnalyzer()

        text = "semantic web ontology knowledge graph reasoning inference"

        keywords = analyzer.extract_keywords(text, top_k=3)

        assert len(keywords) <= 3
        assert all(isinstance(kw, tuple) for kw in keywords)
        assert all(len(kw) == 2 for kw in keywords)

        # Check scores are normalized
        assert all(0.0 <= score <= 1.0 for _, score in keywords)

    def test_classify_text(self):
        """Test text classification."""
        analyzer = SemanticAnalyzer()

        # Technical text
        text = "This function implements the API method for database queries."
        categories = analyzer.classify_text(text)

        assert "technical" in categories
        assert categories["technical"] > 0

        # Ontology text
        text2 = "The ontology defines classes and properties with relations."
        categories2 = analyzer.classify_text(text2)

        assert categories2["ontology"] > 0

    def test_entity_to_dict(self):
        """Test entity serialization."""
        entity = SemanticEntity(
            text="TestEntity",
            entity_type=EntityType.CONCEPT,
            confidence=0.9,
            start_pos=0,
            end_pos=10,
        )

        entity_dict = entity.to_dict()

        assert entity_dict["text"] == "TestEntity"
        assert entity_dict["type"] == "concept"
        assert entity_dict["confidence"] == 0.9


class TestNLPQueryBuilder:
    """Test NLP query builder functionality."""

    def test_init(self):
        """Test NLP query builder initialization."""
        builder = NLPQueryBuilder()

        assert builder.templates
        assert builder.semantic_analyzer

    def test_parse_what_is_question(self):
        """Test 'what is' question parsing."""
        builder = NLPQueryBuilder()

        question = "What is a Person?"

        result = builder.parse_question(question)

        assert isinstance(result, NLPQuery)
        assert result.original_text == question.lower()
        assert "SELECT" in result.sparql_query
        assert result.confidence > 0

    def test_parse_find_all_question(self):
        """Test 'find all' question parsing."""
        builder = NLPQueryBuilder()

        question = "Find all classes"

        result = builder.parse_question(question)

        assert "SELECT" in result.sparql_query
        assert "classes" in result.original_text

    def test_parse_count_question(self):
        """Test 'count' question parsing."""
        builder = NLPQueryBuilder()

        question = "How many people are there?"

        result = builder.parse_question(question)

        assert "COUNT" in result.sparql_query.upper()
        assert result.query_type == "SELECT"

    def test_parse_show_properties(self):
        """Test 'show properties' question."""
        builder = NLPQueryBuilder()

        question = "Show properties"

        result = builder.parse_question(question)

        assert "property" in result.sparql_query.lower()
        assert result.confidence > 0.8  # High confidence pattern

    def test_build_sparql_from_entities(self):
        """Test SPARQL building from entities."""
        builder = NLPQueryBuilder()

        entities = ["Person", "Organization"]
        relations = ["works_at"]

        sparql = builder.build_sparql(entities, relations)

        assert isinstance(sparql, str)
        assert "SELECT" in sparql

    def test_query_to_dict(self):
        """Test NLP query serialization."""
        query = NLPQuery(
            original_text="test question",
            sparql_query="SELECT * WHERE { ?s ?p ?o }",
            confidence=0.8,
            entities=["Entity1"],
            relations=["relation1"],
            query_type="SELECT",
            variables=["?s", "?p", "?o"],
        )

        query_dict = query.to_dict()

        assert query_dict["original"] == "test question"
        assert query_dict["confidence"] == 0.8
        assert len(query_dict["variables"]) == 3

    def test_add_custom_template(self):
        """Test adding custom query template."""
        builder = NLPQueryBuilder()

        initial_count = len(builder.templates)

        builder.add_template(
            name="custom_pattern",
            patterns=[r"custom\s+query\s+(\w+)"],
            sparql_template="SELECT ?x WHERE { ?x :prop {entity} }",
            confidence=0.7,
        )

        assert len(builder.templates) == initial_count + 1
        assert "custom_pattern" in builder.templates

    def test_get_suggestions(self):
        """Test query suggestions."""
        builder = NLPQueryBuilder()

        suggestions = builder.get_suggestions("wha")

        assert len(suggestions) > 0
        assert any("What" in s for s in suggestions)

    def test_extract_variables(self):
        """Test variable extraction from SPARQL."""
        builder = NLPQueryBuilder()

        sparql = "SELECT ?person ?name ?age WHERE { ?person :hasName ?name }"

        variables = builder._extract_variables(sparql)

        assert len(variables) == 3
        assert "person" in variables
        assert "name" in variables
        assert "age" in variables

    def test_fallback_generic_query(self):
        """Test fallback to generic query."""
        builder = NLPQueryBuilder()

        # Completely unrecognized question
        question = "zxcvbnm qwertyuiop"

        result = builder.parse_question(question)

        # Should still generate some query
        assert result.sparql_query
        assert result.confidence < 0.5  # Low confidence


class TestIntegration:
    """Integration tests for semantic modules."""

    def test_semantic_search_workflow(self):
        """Test complete semantic search workflow."""
        # Setup
        embeddings = EmbeddingsManager()
        analyzer = SemanticAnalyzer()

        # Analyze text
        text = "Semantic web technologies enable knowledge graphs."
        entities = analyzer.extract_entities(text)

        # Create embeddings for entities
        entity_texts = [e.text for e in entities if e.confidence > 0.5]
        if entity_texts:
            entity_embeddings = embeddings.batch_embed(entity_texts)
            assert len(entity_embeddings) == len(entity_texts)

        # Find similar concepts
        query = "knowledge representation"
        candidates = ["semantic web", "database systems", "graph theory"]

        results = embeddings.find_similar(query, candidates, top_k=2)
        assert len(results) == 2

    def test_nlp_to_sparql_workflow(self):
        """Test NLP to SPARQL conversion workflow."""
        builder = NLPQueryBuilder()

        # Parse question
        question = "What is a Person?"
        result = builder.parse_question(question)

        assert result.sparql_query
        assert result.confidence > 0
        assert result.query_type == "SELECT"

        # Verify SPARQL is well-formed
        assert "SELECT" in result.sparql_query
        assert "WHERE" in result.sparql_query

    def test_combined_semantic_analysis(self):
        """Test combined semantic analysis."""
        analyzer = SemanticAnalyzer()
        embeddings = EmbeddingsManager()

        text = "The ontology describes classes and their properties."

        # Extract entities
        entities = analyzer.extract_entities(text)

        # Classify text
        categories = analyzer.classify_text(text)
        assert categories["ontology"] > 0

        # Sentiment
        sentiment = analyzer.analyze_sentiment(text)
        assert sum(sentiment.values()) > 0

        # Keywords
        keywords = analyzer.extract_keywords(text)
        assert len(keywords) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
