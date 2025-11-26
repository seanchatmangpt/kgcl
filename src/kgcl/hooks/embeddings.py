"""
Embeddings Manager for semantic search and text similarity.

This module provides text embedding generation and similarity computation
for semantic search operations in KGCL.
"""

import hashlib
import math
import time
from dataclasses import dataclass, field


@dataclass
class Embedding:
    """Vector embedding for text."""

    text: str
    vector: list[float]
    model: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)


class EmbeddingsManager:
    """
    Manage text embeddings for semantic search.

    Provides embedding generation, caching, and similarity computation
    for semantic operations on knowledge graph content.
    """

    def __init__(self, model: str = "simple-hash", cache_size: int = 1000):
        """
        Initialize embeddings manager.

        Args:
            model: Embedding model to use (simple-hash, tfidf, etc.)
            cache_size: Maximum number of embeddings to cache
        """
        self.model = model
        self.cache_size = cache_size
        self.embeddings_cache: dict[str, Embedding] = {}
        self.vocabulary: dict[str, int] = {}
        self.idf_scores: dict[str, float] = {}
        self._stats = {"cache_hits": 0, "cache_misses": 0, "embeddings_generated": 0}

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _simple_tokenize(self, text: str) -> list[str]:
        """Simple word tokenization."""
        # Lowercase and split on whitespace/punctuation
        text = text.lower()
        tokens = []
        current = []

        for char in text:
            if char.isalnum():
                current.append(char)
            elif current:
                tokens.append("".join(current))
                current = []

        if current:
            tokens.append("".join(current))

        return tokens

    def _build_vocabulary(self, texts: list[str]) -> None:
        """Build vocabulary from texts for TF-IDF."""
        word_doc_count: dict[str, int] = {}

        for text in texts:
            tokens = set(self._simple_tokenize(text))
            for token in tokens:
                word_doc_count[token] = word_doc_count.get(token, 0) + 1

        # Build vocabulary index
        self.vocabulary = {
            word: idx for idx, word in enumerate(sorted(word_doc_count.keys()))
        }

        # Calculate IDF scores
        num_docs = len(texts)
        for word, doc_count in word_doc_count.items():
            self.idf_scores[word] = math.log(num_docs / (1 + doc_count))

    def _hash_embedding(self, text: str, dim: int = 128) -> list[float]:
        """
        Generate hash-based embedding.
        Fast, deterministic embedding using hashing trick.
        """
        tokens = self._simple_tokenize(text)
        vector = [0.0] * dim

        for token in tokens:
            # Use hash to determine which dimensions to activate
            hash_val = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = hash_val % dim
            sign = 1 if (hash_val // dim) % 2 == 0 else -1
            vector[idx] += sign

        # Normalize
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    def _tfidf_embedding(self, text: str) -> list[float]:
        """
        Generate TF-IDF based embedding.
        Requires vocabulary to be built first.
        """
        if not self.vocabulary:
            # Fallback to hash embedding
            return self._hash_embedding(text)

        tokens = self._simple_tokenize(text)
        token_counts: dict[str, int] = {}

        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        # Calculate TF-IDF vector
        vector = [0.0] * len(self.vocabulary)
        total_tokens = len(tokens)

        for token, count in token_counts.items():
            if token in self.vocabulary:
                tf = count / total_tokens
                idf = self.idf_scores.get(token, 0.0)
                idx = self.vocabulary[token]
                vector[idx] = tf * idf

        # Normalize
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    def embed_text(self, text: str, use_cache: bool = True) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns
        -------
            Embedding vector
        """
        cache_key = self._get_cache_key(text)

        # Check cache
        if use_cache and cache_key in self.embeddings_cache:
            self._stats["cache_hits"] += 1
            return self.embeddings_cache[cache_key].vector

        self._stats["cache_misses"] += 1

        # Generate embedding based on model
        if self.model == "tfidf":
            vector = self._tfidf_embedding(text)
        else:  # Default to simple-hash
            vector = self._hash_embedding(text)

        # Cache the embedding
        if use_cache:
            # Evict oldest if cache full
            if len(self.embeddings_cache) >= self.cache_size:
                oldest_key = min(
                    self.embeddings_cache.keys(),
                    key=lambda k: self.embeddings_cache[k].timestamp,
                )
                del self.embeddings_cache[oldest_key]

            self.embeddings_cache[cache_key] = Embedding(
                text=text, vector=vector, model=self.model, timestamp=time.time()
            )

        self._stats["embeddings_generated"] += 1
        return vector

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Compute cosine similarity between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns
        -------
            Similarity score between -1 and 1
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimension")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(x * x for x in vec1))
        mag2 = math.sqrt(sum(x * x for x in vec2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def euclidean_distance(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Compute Euclidean distance between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns
        -------
            Distance value (lower is more similar)
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimension")

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))

    def find_similar(
        self, query: str, candidates: list[str], top_k: int = 5, metric: str = "cosine"
    ) -> list[tuple[str, float]]:
        """
        Find most similar candidates to query.

        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of results to return
            metric: Similarity metric ('cosine' or 'euclidean')

        Returns
        -------
            List of (text, score) tuples sorted by similarity
        """
        query_embedding = self.embed_text(query)
        similarities = []

        for candidate in candidates:
            candidate_embedding = self.embed_text(candidate)

            if metric == "cosine":
                score = self.cosine_similarity(query_embedding, candidate_embedding)
                similarities.append((candidate, score))
            elif metric == "euclidean":
                distance = self.euclidean_distance(query_embedding, candidate_embedding)
                # Convert distance to similarity (invert and normalize)
                score = 1.0 / (1.0 + distance)
                similarities.append((candidate, score))
            else:
                raise ValueError(f"Unknown metric: {metric}")

        # Sort by score (higher is better for both metrics after conversion)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns
        -------
            List of embedding vectors
        """
        # Build vocabulary if using TF-IDF
        if self.model == "tfidf" and not self.vocabulary:
            self._build_vocabulary(texts)

        return [self.embed_text(text) for text in texts]

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            **self._stats,
            "cache_size": len(self.embeddings_cache),
            "vocabulary_size": len(self.vocabulary),
        }

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self.embeddings_cache.clear()
        self._stats["cache_hits"] = 0
        self._stats["cache_misses"] = 0
