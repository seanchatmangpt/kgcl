"""
Hyper-Advanced Semantic Analysis Prototype.

This prototype demonstrates cutting-edge Python techniques for natural language processing:
1. Trie data structure for O(m) pattern matching
2. Aho-Corasick multi-pattern search algorithm
3. Generator pipelines for streaming analysis
4. Context managers with ExitStack
5. Sliding window analysis with deque
6. Weighted voting for sentiment aggregation
7. Protocol-based pluggable extractors
8. LRU caching for performance
9. Span-based entity resolution
10. Relation extraction with dependency patterns
11. Async generators for parallel analysis
12. N-gram generation with itertools

Run: python examples/proto_semantic_analysis.py
"""

import asyncio
import re
from collections import deque
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import lru_cache
from itertools import chain, islice, tee
from typing import (
    Any,
    AsyncIterator,
    ClassVar,
    Iterable,
    Iterator,
    Protocol,
    Sequence,
)


# ============================================================================
# Core Data Types
# ============================================================================


class EntityType(Enum):
    """Entity classification types."""

    PERSON = auto()
    ORGANIZATION = auto()
    LOCATION = auto()
    DATE = auto()
    TECHNOLOGY = auto()
    CONCEPT = auto()


class SentimentPolarity(Enum):
    """Sentiment classification."""

    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


@dataclass(frozen=True, slots=True)
class Span:
    """Text span with efficient overlap detection."""

    start: int
    end: int

    def overlaps(self, other: "Span") -> bool:
        """Check if spans overlap - O(1)."""
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Span") -> bool:
        """Check if this span contains another - O(1)."""
        return self.start <= other.start and other.end <= self.end

    @property
    def length(self) -> int:
        """Span length."""
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class Entity:
    """Named entity with span and type."""

    text: str
    span: Span
    entity_type: EntityType
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class Relation:
    """Relation between two entities."""

    subject: Entity
    predicate: str
    object_entity: Entity
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class WeightedVote:
    """Sentiment vote with confidence weight."""

    sentiment: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Sentiment analysis result."""

    polarity: SentimentPolarity
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Complete semantic analysis result."""

    text: str
    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]
    sentiment: SentimentResult
    ngrams: tuple[tuple[str, ...], ...]


# ============================================================================
# Technique 1: Trie Data Structure for Fast Pattern Matching
# ============================================================================


@dataclass
class TrieNode:
    """Trie node with entity type annotation."""

    children: dict[str, "TrieNode"] = field(default_factory=dict)
    is_end: bool = False
    entity_type: EntityType | None = None


class EntityTrie:
    """Trie for O(m) entity recognition where m = pattern length."""

    def __init__(self) -> None:
        """Initialize empty trie."""
        self.root = TrieNode()

    def insert(self, pattern: str, entity_type: EntityType) -> None:
        """Insert pattern into trie - O(m) where m = len(pattern)."""
        node = self.root
        for char in pattern.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.entity_type = entity_type

    def search(self, text: str) -> Iterator[tuple[int, int, EntityType]]:
        """Yield (start, end, type) for all matches - O(n*m) worst case."""
        text_lower = text.lower()
        for start in range(len(text)):
            node = self.root
            for end in range(start, len(text)):
                char = text_lower[end]
                if char not in node.children:
                    break
                node = node.children[char]
                if node.is_end and node.entity_type:
                    yield (start, end + 1, node.entity_type)


# ============================================================================
# Technique 2: Aho-Corasick for Multi-Pattern Search
# ============================================================================


@dataclass(frozen=True, slots=True)
class Match:
    """Pattern match result."""

    position: int
    pattern: str
    entity_type: EntityType


class AhoCorasick:
    """Aho-Corasick automaton for O(n + m + z) multi-pattern search."""

    def __init__(self) -> None:
        """Initialize automaton."""
        self.goto: dict[int, dict[str, int]] = {0: {}}
        self.fail: dict[int, int] = {0: 0}
        self.output: dict[int, list[tuple[str, EntityType]]] = {}
        self._state_counter = 0

    def add_pattern(self, pattern: str, entity_type: EntityType) -> None:
        """Add pattern to automaton."""
        state = 0
        for char in pattern.lower():
            if char not in self.goto[state]:
                self._state_counter += 1
                new_state = self._state_counter
                self.goto[state][char] = new_state
                self.goto[new_state] = {}
            state = self.goto[state][char]
        if state not in self.output:
            self.output[state] = []
        self.output[state].append((pattern, entity_type))

    def build_failure_links(self) -> None:
        """Build failure function for automaton."""
        queue: deque[int] = deque()
        for char, state in self.goto[0].items():
            self.fail[state] = 0
            queue.append(state)

        while queue:
            current = queue.popleft()
            for char, next_state in self.goto[current].items():
                queue.append(next_state)
                fail_state = self.fail[current]
                while fail_state != 0 and char not in self.goto[fail_state]:
                    fail_state = self.fail[fail_state]
                self.fail[next_state] = self.goto[fail_state].get(char, 0)
                # Merge outputs
                if self.fail[next_state] in self.output:
                    if next_state not in self.output:
                        self.output[next_state] = []
                    self.output[next_state].extend(self.output[self.fail[next_state]])

    def search(self, text: str) -> Iterator[Match]:
        """Search for all patterns in text - O(n + z)."""
        state = 0
        for i, char in enumerate(text.lower()):
            while state != 0 and char not in self.goto[state]:
                state = self.fail[state]
            state = self.goto[state].get(char, 0)
            if state in self.output:
                for pattern, entity_type in self.output[state]:
                    yield Match(
                        position=i - len(pattern) + 1,
                        pattern=pattern,
                        entity_type=entity_type,
                    )


# ============================================================================
# Technique 7: Protocol for Pluggable Entity Extractors
# ============================================================================


class EntityExtractor(Protocol):
    """Protocol for pluggable entity extractors."""

    def extract(self, text: str) -> Sequence[Entity]:
        """Extract entities from text."""
        ...

    def supports(self, entity_type: EntityType) -> bool:
        """Check if extractor supports entity type."""
        ...


class TrieEntityExtractor:
    """Entity extractor using trie."""

    def __init__(self) -> None:
        """Initialize with predefined patterns."""
        self.trie = EntityTrie()
        # Add sample patterns
        patterns = [
            ("python", EntityType.TECHNOLOGY),
            ("rust", EntityType.TECHNOLOGY),
            ("javascript", EntityType.TECHNOLOGY),
            ("new york", EntityType.LOCATION),
            ("san francisco", EntityType.LOCATION),
            ("google", EntityType.ORGANIZATION),
            ("microsoft", EntityType.ORGANIZATION),
        ]
        for pattern, entity_type in patterns:
            self.trie.insert(pattern, entity_type)

    def extract(self, text: str) -> Sequence[Entity]:
        """Extract entities using trie search."""
        entities: list[Entity] = []
        for start, end, entity_type in self.trie.search(text):
            span = Span(start, end)
            entities.append(
                Entity(
                    text=text[start:end],
                    span=span,
                    entity_type=entity_type,
                    confidence=0.9,
                )
            )
        return entities

    def supports(self, entity_type: EntityType) -> bool:
        """Support technology, location, and organization."""
        return entity_type in {
            EntityType.TECHNOLOGY,
            EntityType.LOCATION,
            EntityType.ORGANIZATION,
        }


class AhoCorasickExtractor:
    """Entity extractor using Aho-Corasick."""

    def __init__(self) -> None:
        """Initialize with predefined patterns."""
        self.automaton = AhoCorasick()
        patterns = [
            ("ai", EntityType.CONCEPT),
            ("machine learning", EntityType.CONCEPT),
            ("deep learning", EntityType.CONCEPT),
            ("alice", EntityType.PERSON),
            ("bob", EntityType.PERSON),
        ]
        for pattern, entity_type in patterns:
            self.automaton.add_pattern(pattern, entity_type)
        self.automaton.build_failure_links()

    def extract(self, text: str) -> Sequence[Entity]:
        """Extract entities using Aho-Corasick."""
        entities: list[Entity] = []
        for match in self.automaton.search(text):
            span = Span(match.position, match.position + len(match.pattern))
            entities.append(
                Entity(
                    text=text[span.start : span.end],
                    span=span,
                    entity_type=match.entity_type,
                    confidence=0.85,
                )
            )
        return entities

    def supports(self, entity_type: EntityType) -> bool:
        """Support person and concept types."""
        return entity_type in {EntityType.PERSON, EntityType.CONCEPT}


class CompositeExtractor:
    """Composite extractor combining multiple strategies."""

    def __init__(self, extractors: Sequence[EntityExtractor]) -> None:
        """Initialize with extractors."""
        self._extractors = extractors

    def extract(self, text: str) -> list[Entity]:
        """Extract using all extractors."""
        return list(chain.from_iterable(e.extract(text) for e in self._extractors))


# ============================================================================
# Technique 9: Span-based Entity Resolution
# ============================================================================


def resolve_overlapping(entities: list[Entity]) -> list[Entity]:
    """Resolve overlapping entities by keeping longest span."""
    if not entities:
        return []

    # Sort by start position, then by length (descending)
    sorted_entities = sorted(
        entities, key=lambda e: (e.span.start, -e.span.length)
    )

    result: list[Entity] = []
    for entity in sorted_entities:
        # Keep entity if not contained by any existing result
        if not any(r.span.contains(entity.span) for r in result):
            # Remove any results contained by this entity
            result = [r for r in result if not entity.span.contains(r.span)]
            result.append(entity)

    return sorted(result, key=lambda e: e.span.start)


# ============================================================================
# Technique 10: Relation Extraction with Dependency Patterns
# ============================================================================


@dataclass(frozen=True, slots=True)
class RelationPattern:
    """Pattern for extracting relations."""

    subject_type: EntityType
    predicate: str
    object_type: EntityType
    pattern: re.Pattern[str]


class RelationExtractor:
    """Extract relations using pattern matching."""

    patterns: ClassVar[list[RelationPattern]] = [
        RelationPattern(
            EntityType.PERSON,
            "works_at",
            EntityType.ORGANIZATION,
            re.compile(r"(\w+)\s+works\s+at\s+(\w+)", re.IGNORECASE),
        ),
        RelationPattern(
            EntityType.ORGANIZATION,
            "located_in",
            EntityType.LOCATION,
            re.compile(
                r"(\w+)\s+(?:is\s+|are\s+)?(?:located\s+|based\s+)in\s+(\w+)",
                re.IGNORECASE,
            ),
        ),
        RelationPattern(
            EntityType.PERSON,
            "uses",
            EntityType.TECHNOLOGY,
            re.compile(r"(\w+)\s+uses\s+(\w+)", re.IGNORECASE),
        ),
    ]

    def extract(self, text: str, entities: Sequence[Entity]) -> list[Relation]:
        """Extract relations from text and entities."""
        relations: list[Relation] = []
        entity_map: dict[str, Entity] = {e.text.lower(): e for e in entities}

        for pattern in self.patterns:
            for match in pattern.pattern.finditer(text):
                subject_text = match.group(1).lower()
                object_text = match.group(2).lower()

                subject_entity = entity_map.get(subject_text)
                object_entity = entity_map.get(object_text)

                if (
                    subject_entity
                    and object_entity
                    and subject_entity.entity_type == pattern.subject_type
                    and object_entity.entity_type == pattern.object_type
                ):
                    relations.append(
                        Relation(
                            subject=subject_entity,
                            predicate=pattern.predicate,
                            object_entity=object_entity,
                            confidence=0.8,
                        )
                    )

        return relations


# ============================================================================
# Technique 5: Sliding Window with deque
# ============================================================================


@dataclass(frozen=True, slots=True)
class ContextualToken:
    """Token with surrounding context window."""

    token: str
    context: tuple[str, ...]


class SlidingWindowAnalyzer:
    """Analyze text in sliding windows for context."""

    def __init__(self, window_size: int = 5) -> None:
        """Initialize with window size."""
        self.window_size = window_size

    def process(self, tokens: Iterable[str]) -> Iterator[ContextualToken]:
        """Process tokens with sliding window context."""
        window: deque[str] = deque(maxlen=self.window_size)
        for token in tokens:
            window.append(token)
            context = tuple(window)
            yield ContextualToken(token, context)


# ============================================================================
# Technique 6: Sentiment with Weighted Voting
# ============================================================================


class SentimentAnalyzer:
    """Sentiment analysis with weighted voting."""

    # Simple lexicon for demonstration
    positive_words: ClassVar[set[str]] = {
        "good",
        "great",
        "excellent",
        "amazing",
        "wonderful",
        "love",
        "best",
    }
    negative_words: ClassVar[set[str]] = {
        "bad",
        "terrible",
        "awful",
        "horrible",
        "hate",
        "worst",
        "poor",
    }

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using weighted voting."""
        words = text.lower().split()
        votes: list[WeightedVote] = []

        for word in words:
            if word in self.positive_words:
                votes.append(WeightedVote(sentiment=1.0, confidence=0.8))
            elif word in self.negative_words:
                votes.append(WeightedVote(sentiment=-1.0, confidence=0.8))

        if not votes:
            return SentimentResult(
                polarity=SentimentPolarity.NEUTRAL, score=0.0, confidence=1.0
            )

        score = self._aggregate_sentiment(votes)
        polarity = (
            SentimentPolarity.POSITIVE
            if score > 0.2
            else SentimentPolarity.NEGATIVE
            if score < -0.2
            else SentimentPolarity.NEUTRAL
        )

        return SentimentResult(
            polarity=polarity, score=score, confidence=abs(score)
        )

    @staticmethod
    def _aggregate_sentiment(votes: Iterable[WeightedVote]) -> float:
        """Weighted average of sentiment votes."""
        total_weight = 0.0
        weighted_sum = 0.0
        for vote in votes:
            weighted_sum += vote.sentiment * vote.confidence
            total_weight += vote.confidence
        return weighted_sum / total_weight if total_weight > 0 else 0.0


# ============================================================================
# Technique 12: N-gram Generation with itertools
# ============================================================================


def ngrams(tokens: Sequence[str], n: int) -> Iterator[tuple[str, ...]]:
    """Generate n-grams from token sequence."""
    if n < 1 or len(tokens) < n:
        return
    iterators = tee(iter(tokens), n)
    for i, it in enumerate(iterators):
        # Advance iterator by i positions
        for _ in range(i):
            next(it, None)
    yield from zip(*iterators)


# ============================================================================
# Technique 8: LRU Cache for Repeated Analysis
# ============================================================================


class CachingAnalyzer:
    """Analyzer with LRU cache for repeated text."""

    def __init__(self, max_cache_size: int = 128) -> None:
        """Initialize with cache size."""
        self.max_cache_size = max_cache_size
        self._entity_extractor = CompositeExtractor(
            [TrieEntityExtractor(), AhoCorasickExtractor()]
        )
        self._relation_extractor = RelationExtractor()
        self._sentiment_analyzer = SentimentAnalyzer()

    @lru_cache(maxsize=128)
    def _analyze_cached(self, text: str, text_hash: int) -> AnalysisResult:
        """Cached analysis implementation."""
        return self._analyze_impl(text)

    def _analyze_impl(self, text: str) -> AnalysisResult:
        """Core analysis implementation."""
        # Extract entities
        raw_entities = self._entity_extractor.extract(text)
        resolved_entities = resolve_overlapping(list(raw_entities))

        # Extract relations
        relations = self._relation_extractor.extract(text, resolved_entities)

        # Analyze sentiment
        sentiment = self._sentiment_analyzer.analyze(text)

        # Generate bigrams and trigrams
        tokens = text.lower().split()
        bigrams = list(ngrams(tokens, 2))
        trigrams = list(ngrams(tokens, 3))

        return AnalysisResult(
            text=text,
            entities=tuple(resolved_entities),
            relations=tuple(relations),
            sentiment=sentiment,
            ngrams=tuple(bigrams + trigrams),
        )

    def analyze(self, text: str) -> AnalysisResult:
        """Analyze text with caching."""
        return self._analyze_cached(text, hash(text))


# ============================================================================
# Technique 3: Generator Pipeline for Streaming Analysis
# ============================================================================


def analyze_stream(texts: Iterable[str]) -> Iterator[AnalysisResult]:
    """Memory-efficient streaming analysis."""
    analyzer = CachingAnalyzer()
    for text in texts:
        yield analyzer.analyze(text)


# ============================================================================
# Technique 4: Context Manager with ExitStack
# ============================================================================


class AnalyzerContext:
    """Context manager for analyzer."""

    def __init__(self, analyzer: CachingAnalyzer) -> None:
        """Initialize context."""
        self.analyzer = analyzer

    def __enter__(self) -> CachingAnalyzer:
        """Enter context."""
        return self.analyzer

    def __exit__(self, *args: Any) -> None:
        """Exit context."""
        # Clear cache on exit
        self.analyzer._analyze_cached.cache_clear()


@contextmanager
def analysis_pipeline(
    *analyzers: CachingAnalyzer,
) -> Iterator[tuple[CachingAnalyzer, ...]]:
    """Compose multiple analyzers with proper cleanup."""
    with ExitStack() as stack:
        initialized = tuple(
            stack.enter_context(AnalyzerContext(a)) for a in analyzers
        )
        yield initialized


# ============================================================================
# Technique 11: Async Generator for Parallel Analysis
# ============================================================================


async def analyze_parallel(
    texts: Sequence[str], max_concurrent: int = 10
) -> AsyncIterator[AnalysisResult]:
    """Analyze texts in parallel with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)
    analyzer = CachingAnalyzer()

    async def analyze_one(text: str) -> AnalysisResult:
        async with semaphore:
            return await asyncio.to_thread(analyzer.analyze, text)

    tasks = [asyncio.create_task(analyze_one(t)) for t in texts]
    for task in asyncio.as_completed(tasks):
        yield await task


# ============================================================================
# Tests
# ============================================================================


def test_trie_entity_extraction() -> None:
    """Test trie-based entity extraction."""
    extractor = TrieEntityExtractor()
    text = "Python and Rust are great. Google is in San Francisco."
    entities = extractor.extract(text)
    assert len(entities) >= 3  # python, rust, google, san francisco
    assert any(e.entity_type == EntityType.TECHNOLOGY for e in entities)
    assert any(e.entity_type == EntityType.ORGANIZATION for e in entities)


def test_aho_corasick_extraction() -> None:
    """Test Aho-Corasick multi-pattern extraction."""
    extractor = AhoCorasickExtractor()
    text = "Alice studies machine learning and deep learning AI."
    entities = extractor.extract(text)
    assert len(entities) >= 2  # alice, machine learning, deep learning, ai
    assert any(e.entity_type == EntityType.PERSON for e in entities)
    assert any(e.entity_type == EntityType.CONCEPT for e in entities)


def test_span_overlap_resolution() -> None:
    """Test span-based overlap resolution."""
    entities = [
        Entity("New", Span(0, 3), EntityType.LOCATION, 0.9),
        Entity("New York", Span(0, 8), EntityType.LOCATION, 0.95),
        Entity("York", Span(4, 8), EntityType.LOCATION, 0.8),
    ]
    resolved = resolve_overlapping(entities)
    assert len(resolved) == 1
    assert resolved[0].text == "New York"


def test_relation_extraction() -> None:
    """Test relation extraction with patterns."""
    entities = [
        Entity("alice", Span(0, 5), EntityType.PERSON, 1.0),
        Entity("google", Span(16, 22), EntityType.ORGANIZATION, 1.0),
        Entity("python", Span(34, 40), EntityType.TECHNOLOGY, 1.0),
    ]
    text = "Alice works at Google and Alice uses Python"
    extractor = RelationExtractor()
    relations = extractor.extract(text, entities)
    assert len(relations) >= 1
    assert any(r.predicate == "works_at" for r in relations)


def test_sentiment_analysis() -> None:
    """Test weighted sentiment voting."""
    analyzer = SentimentAnalyzer()

    positive = analyzer.analyze("This is great and excellent!")
    assert positive.polarity == SentimentPolarity.POSITIVE
    assert positive.score > 0

    negative = analyzer.analyze("This is terrible and awful!")
    assert negative.polarity == SentimentPolarity.NEGATIVE
    assert negative.score < 0

    neutral = analyzer.analyze("This is a thing.")
    assert neutral.polarity == SentimentPolarity.NEUTRAL


def test_ngram_generation() -> None:
    """Test n-gram generation."""
    tokens = ["the", "quick", "brown", "fox"]
    bigrams = list(ngrams(tokens, 2))
    assert len(bigrams) == 3
    assert bigrams[0] == ("the", "quick")

    trigrams = list(ngrams(tokens, 3))
    assert len(trigrams) == 2
    assert trigrams[0] == ("the", "quick", "brown")


def test_sliding_window_analyzer() -> None:
    """Test sliding window context."""
    analyzer = SlidingWindowAnalyzer(window_size=3)
    tokens = ["a", "b", "c", "d", "e"]
    results = list(analyzer.process(tokens))
    assert len(results) == 5
    assert results[2].context == ("a", "b", "c")
    assert results[4].context == ("c", "d", "e")


def test_caching_analyzer() -> None:
    """Test LRU cache functionality."""
    analyzer = CachingAnalyzer()
    text = "Python is great and Python is excellent"

    # First analysis
    result1 = analyzer.analyze(text)
    cache_info1 = analyzer._analyze_cached.cache_info()

    # Second analysis (should hit cache)
    result2 = analyzer.analyze(text)
    cache_info2 = analyzer._analyze_cached.cache_info()

    assert result1 == result2
    assert cache_info2.hits > cache_info1.hits


def test_streaming_analysis() -> None:
    """Test generator pipeline for streaming."""
    texts = [
        "Python is great",
        "Rust is fast",
        "JavaScript is popular",
    ]
    results = list(analyze_stream(texts))
    assert len(results) == 3
    assert all(isinstance(r, AnalysisResult) for r in results)


def test_context_manager_pipeline() -> None:
    """Test context manager with ExitStack."""
    analyzer1 = CachingAnalyzer()
    analyzer2 = CachingAnalyzer()

    with analysis_pipeline(analyzer1, analyzer2) as (a1, a2):
        result1 = a1.analyze("Test text")
        result2 = a2.analyze("Test text")
        assert isinstance(result1, AnalysisResult)
        assert isinstance(result2, AnalysisResult)

    # Cache should be cleared after context exit
    assert analyzer1._analyze_cached.cache_info().currsize == 0


def test_composite_extractor() -> None:
    """Test composite extractor combining strategies."""
    extractor = CompositeExtractor([TrieEntityExtractor(), AhoCorasickExtractor()])
    text = "Alice uses Python for machine learning at Google"
    entities = extractor.extract(text)
    assert len(entities) >= 3  # alice, python, machine learning, google


def test_full_analysis_pipeline() -> None:
    """Test complete analysis pipeline with all techniques."""
    analyzer = CachingAnalyzer()
    text = "Alice works at Google in San Francisco using Python for machine learning"

    result = analyzer.analyze(text)

    # Check entities extracted
    assert len(result.entities) > 0
    entity_types = {e.entity_type for e in result.entities}
    assert EntityType.PERSON in entity_types or EntityType.ORGANIZATION in entity_types

    # Check sentiment
    assert isinstance(result.sentiment, SentimentResult)

    # Check n-grams
    assert len(result.ngrams) > 0


async def test_parallel_analysis() -> None:
    """Test async parallel analysis."""
    texts = [
        "Python is great",
        "Rust is fast",
        "JavaScript is popular",
        "Alice works at Google",
        "Machine learning is amazing",
    ]

    results = []
    async for result in analyze_parallel(texts, max_concurrent=3):
        results.append(result)

    assert len(results) == len(texts)
    assert all(isinstance(r, AnalysisResult) for r in results)


# ============================================================================
# Main Execution
# ============================================================================


def run_all_tests() -> tuple[int, int]:
    """Run all synchronous tests."""
    tests = [
        test_trie_entity_extraction,
        test_aho_corasick_extraction,
        test_span_overlap_resolution,
        test_relation_extraction,
        test_sentiment_analysis,
        test_ngram_generation,
        test_sliding_window_analyzer,
        test_caching_analyzer,
        test_streaming_analysis,
        test_context_manager_pipeline,
        test_composite_extractor,
        test_full_analysis_pipeline,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")

    return passed, failed


async def run_async_tests() -> tuple[int, int]:
    """Run all async tests."""
    tests = [test_parallel_analysis]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")

    return passed, failed


def main() -> None:
    """Run all tests and report results."""
    print("=" * 80)
    print("Hyper-Advanced Semantic Analysis Prototype")
    print("=" * 80)
    print()

    print("Running synchronous tests...")
    sync_passed, sync_failed = run_all_tests()
    print()

    print("Running async tests...")
    async_passed, async_failed = asyncio.run(run_async_tests())
    print()

    total_passed = sync_passed + async_passed
    total_failed = sync_failed + async_failed
    total_tests = total_passed + total_failed

    print("=" * 80)
    print(f"Test Results: {total_passed}/{total_tests} passed")
    if total_failed > 0:
        print(f"FAILED: {total_failed} tests failed")
    else:
        print("SUCCESS: All tests passed!")
    print()

    print("Advanced Techniques Demonstrated:")
    print("1. ✓ Trie data structure for O(m) pattern matching")
    print("2. ✓ Aho-Corasick multi-pattern search algorithm")
    print("3. ✓ Generator pipelines for streaming analysis")
    print("4. ✓ Context managers with ExitStack")
    print("5. ✓ Sliding window analysis with deque")
    print("6. ✓ Weighted voting for sentiment aggregation")
    print("7. ✓ Protocol-based pluggable extractors")
    print("8. ✓ LRU caching for performance optimization")
    print("9. ✓ Span-based entity resolution")
    print("10. ✓ Relation extraction with dependency patterns")
    print("11. ✓ Async generators for parallel analysis")
    print("12. ✓ N-gram generation with itertools")
    print("=" * 80)


if __name__ == "__main__":
    main()
