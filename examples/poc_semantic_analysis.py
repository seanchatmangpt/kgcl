"""
POC: Semantic Analysis - Advanced NLP for Knowledge Graph Content.

This single file contains:
1. Complete entity recognition with context-aware patterns
2. Relation extraction between entities
3. Sentiment analysis
4. Comprehensive inline tests

Run: python examples/poc_semantic_analysis.py
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern


class EntityType(Enum):
    """Types of entities recognized in text."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    CONCEPT = "concept"
    ACTION = "action"


@dataclass(frozen=True)
class Entity:
    """Recognized entity in text.

    Parameters
    ----------
    text : str
        The actual text of the entity
    entity_type : EntityType
        Classification of the entity
    start : int
        Starting character position in original text
    end : int
        Ending character position in original text
    confidence : float
        Recognition confidence score (0.0 to 1.0)
    """

    text: str
    entity_type: EntityType
    start: int
    end: int
    confidence: float

    def __post_init__(self) -> None:
        """Validate entity constraints."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid positions: start={self.start}, end={self.end}")


@dataclass(frozen=True)
class Relation:
    """Relation between two entities.

    Parameters
    ----------
    subject : Entity
        The subject entity
    predicate : str
        The relation type/verb
    object : Entity
        The object entity
    confidence : float
        Relation confidence score (0.0 to 1.0)
    """

    subject: Entity
    predicate: str
    object: Entity
    confidence: float

    def __post_init__(self) -> None:
        """Validate relation constraints."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")


@dataclass(frozen=True)
class SemanticAnalysisResult:
    """Result of semantic analysis.

    Parameters
    ----------
    entities : tuple[Entity, ...]
        All recognized entities
    relations : tuple[Relation, ...]
        All extracted relations
    sentiment : float
        Overall sentiment score (-1.0 to 1.0)
    """

    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]
    sentiment: float

    def __post_init__(self) -> None:
        """Validate result constraints."""
        if not -1.0 <= self.sentiment <= 1.0:
            raise ValueError(f"Sentiment must be -1.0 to 1.0, got {self.sentiment}")


class SemanticAnalyzer:
    """Advanced semantic analysis for knowledge graph content.

    Provides entity recognition, relation extraction, and sentiment analysis
    using pattern-based NLP with context awareness.

    Examples
    --------
    >>> analyzer = SemanticAnalyzer()
    >>> result = analyzer.analyze("Apple Inc. hired John Smith in January 2024.")
    >>> len(result.entities) >= 3  # Apple Inc., John Smith, January 2024
    True
    >>> len(result.relations) >= 1  # hired relation
    True
    """

    def __init__(self) -> None:
        """Initialize analyzer with entity and relation patterns."""
        self._entity_patterns = self._build_entity_patterns()
        self._relation_patterns = self._build_relation_patterns()
        self._sentiment_patterns = self._build_sentiment_patterns()

    def _build_entity_patterns(self) -> dict[EntityType, list[tuple[Pattern[str], float]]]:
        """Build comprehensive entity recognition patterns.

        Returns
        -------
        dict[EntityType, list[tuple[Pattern[str], float]]]
            Mapping of entity types to (pattern, confidence) pairs
        """
        return {
            EntityType.PERSON: [
                # Full names with titles
                (re.compile(r'\b(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'), 0.95),
                # First Last name
                (re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'), 0.75),
                # Three-part names
                (re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'), 0.85),
                # Names with middle initial
                (re.compile(r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b'), 0.90),
                # Possessive names
                (re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\'s\b'), 0.80),
            ],
            EntityType.ORGANIZATION: [
                # Companies with Inc/LLC/Corp
                (re.compile(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Inc|LLC|Corp|Ltd|Co)\.?\b'), 0.95),
                # University/College
                (re.compile(r'\b(?:University|College|Institute)\s+of\s+[A-Z][a-z]+\b'), 0.95),
                # The X Organization
                (re.compile(r'\bThe\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Organization|Foundation|Association)\b'), 0.90),
                # Government agencies
                (re.compile(r'\b(?:Department|Ministry|Agency|Bureau)\s+of\s+[A-Z][a-z]+\b'), 0.90),
                # Tech companies
                (re.compile(r'\b(?:Apple|Google|Microsoft|Amazon|Meta|Tesla|OpenAI|Anthropic)\b'), 0.98),
                # Multiple capital words (likely org)
                (re.compile(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){2,}\b'), 0.70),
            ],
            EntityType.LOCATION: [
                # Cities, States
                (re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?,\s+[A-Z]{2}\b'), 0.95),
                # Countries
                (re.compile(r'\b(?:United States|United Kingdom|Canada|Australia|France|Germany|Japan|China|India|Brazil)\b'), 0.98),
                # Cities
                (re.compile(r'\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose|Austin|Jacksonville|London|Paris|Tokyo|Beijing|Mumbai|Sydney)\b'), 0.95),
                # Generic location markers
                (re.compile(r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'), 0.60),
                # Street addresses
                (re.compile(r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Ave|Rd|Blvd|Dr|Ln)\.?\b'), 0.85),
            ],
            EntityType.DATE: [
                # Month Day, Year
                (re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'), 0.98),
                # Month Year
                (re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'), 0.95),
                # ISO dates
                (re.compile(r'\b\d{4}-\d{2}-\d{2}\b'), 0.98),
                # Relative dates
                (re.compile(r'\b(?:today|tomorrow|yesterday|last week|next month|this year)\b', re.IGNORECASE), 0.85),
                # Seasonal references
                (re.compile(r'\b(?:Spring|Summer|Fall|Autumn|Winter)\s+\d{4}\b'), 0.90),
                # Numeric dates
                (re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'), 0.90),
            ],
            EntityType.CONCEPT: [
                # Abstract concepts with "of"
                (re.compile(r'\b(?:theory|concept|principle|framework|paradigm|model)\s+of\s+[A-Z][a-z]+\b', re.IGNORECASE), 0.85),
                # Technical terms
                (re.compile(r'\b(?:algorithm|protocol|architecture|infrastructure|methodology|taxonomy)\b', re.IGNORECASE), 0.80),
                # Quoted concepts
                (re.compile(r'"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"'), 0.75),
                # Academic concepts
                (re.compile(r'\b(?:hypothesis|thesis|dissertation|research|study|analysis)\b', re.IGNORECASE), 0.70),
            ],
            EntityType.ACTION: [
                # Business actions
                (re.compile(r'\b(?:acquired|merged|launched|released|announced|implemented|developed)\b', re.IGNORECASE), 0.85),
                # Process actions
                (re.compile(r'\b(?:processing|analyzing|computing|calculating|optimizing)\b', re.IGNORECASE), 0.80),
                # Change actions
                (re.compile(r'\b(?:increased|decreased|improved|enhanced|reduced|expanded)\b', re.IGNORECASE), 0.80),
            ],
        }

    def _build_relation_patterns(self) -> list[tuple[Pattern[str], str, float]]:
        """Build relation extraction patterns.

        Returns
        -------
        list[tuple[Pattern[str], str, float]]
            List of (pattern, predicate, confidence) tuples
        """
        return [
            # Employment relations
            (re.compile(r'(.+?)\s+(?:hired|employed|recruited)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'employs', 0.90),
            (re.compile(r'(.+?)\s+works\s+(?:for|at)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'employed_by', 0.85),
            # Acquisition relations
            (re.compile(r'(.+?)\s+(?:acquired|bought|purchased)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'acquired', 0.90),
            # Location relations
            (re.compile(r'(.+?)\s+(?:located|based)\s+in\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'located_in', 0.85),
            (re.compile(r'(.+?)\s+in\s+(.+?)(?:\.|,|$)'), 'located_in', 0.60),
            # Creation relations
            (re.compile(r'(.+?)\s+(?:created|developed|built|designed)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'created', 0.85),
            # Ownership relations
            (re.compile(r'(.+?)\'s\s+(.+?)(?:\.|,|$)'), 'owns', 0.75),
            (re.compile(r'(.+?)\s+(?:owns|possesses)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'owns', 0.85),
            # Leadership relations
            (re.compile(r'(.+?)\s+(?:leads|manages|directs)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'leads', 0.85),
            (re.compile(r'(.+?)\s+(?:CEO|CTO|CFO|President|Director)\s+of\s+(.+?)(?:\.|,|$)'), 'leads', 0.90),
            # Partnership relations
            (re.compile(r'(.+?)\s+(?:partnered|collaborated)\s+with\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'partners_with', 0.85),
            # Investment relations
            (re.compile(r'(.+?)\s+(?:invested|funded)\s+(.+?)(?:\.|,|$)', re.IGNORECASE), 'invested_in', 0.85),
        ]

    def _build_sentiment_patterns(self) -> dict[str, float]:
        """Build sentiment analysis patterns.

        Returns
        -------
        dict[str, float]
            Mapping of words/patterns to sentiment scores
        """
        return {
            # Positive words
            'excellent': 0.8, 'outstanding': 0.9, 'amazing': 0.8, 'great': 0.6,
            'good': 0.5, 'wonderful': 0.7, 'fantastic': 0.8, 'superb': 0.9,
            'successful': 0.6, 'improved': 0.5, 'progress': 0.5, 'achievement': 0.6,
            'innovative': 0.6, 'revolutionary': 0.7, 'breakthrough': 0.8,
            # Negative words
            'terrible': -0.8, 'awful': -0.8, 'horrible': -0.9, 'bad': -0.6,
            'poor': -0.5, 'failed': -0.7, 'failure': -0.7, 'problem': -0.4,
            'issue': -0.3, 'crisis': -0.8, 'disaster': -0.9, 'decline': -0.5,
            'decreased': -0.4, 'loss': -0.5, 'concern': -0.3, 'risk': -0.4,
            # Neutral/context-dependent
            'change': 0.0, 'update': 0.0, 'announced': 0.0, 'reported': 0.0,
        }

    def analyze(self, text: str) -> SemanticAnalysisResult:
        """Perform full semantic analysis.

        Parameters
        ----------
        text : str
            Input text to analyze

        Returns
        -------
        SemanticAnalysisResult
            Complete analysis with entities, relations, and sentiment
        """
        entities = self.extract_entities(text)
        relations = self.extract_relations(text, entities)
        sentiment = self.analyze_sentiment(text)

        return SemanticAnalysisResult(
            entities=tuple(entities),
            relations=tuple(relations),
            sentiment=sentiment,
        )

    def extract_entities(self, text: str) -> list[Entity]:
        """Extract named entities with context awareness.

        Uses multi-pattern matching for each entity type with confidence scoring.
        Resolves overlapping entities by selecting highest confidence match.

        Parameters
        ----------
        text : str
            Input text to extract entities from

        Returns
        -------
        list[Entity]
            List of recognized entities sorted by position
        """
        raw_entities: list[Entity] = []
        seen_positions: set[tuple[int, int]] = set()

        # Extract entities using all patterns
        for entity_type, patterns in self._entity_patterns.items():
            for pattern, confidence in patterns:
                for match in pattern.finditer(text):
                    # Extract matched text (handle groups)
                    if match.groups():
                        matched_text = match.group(1)
                        start = match.start(1)
                        end = match.end(1)
                    else:
                        matched_text = match.group(0)
                        start = match.start()
                        end = match.end()

                    # Skip if matched text is empty or too short
                    if not matched_text or len(matched_text.strip()) < 2:
                        continue

                    # Quick deduplication check
                    pos_key = (start, end)
                    if pos_key in seen_positions:
                        continue
                    seen_positions.add(pos_key)

                    raw_entities.append(Entity(
                        text=matched_text.strip(),
                        entity_type=entity_type,
                        start=start,
                        end=end,
                        confidence=confidence,
                    ))

        # Resolve overlapping entities (keep highest confidence)
        return self._resolve_overlapping_entities(raw_entities)

    def _resolve_overlapping_entities(self, entities: list[Entity]) -> list[Entity]:
        """Resolve overlapping entities by selecting highest confidence.

        Parameters
        ----------
        entities : list[Entity]
            Raw entities that may overlap

        Returns
        -------
        list[Entity]
            Non-overlapping entities sorted by position
        """
        if not entities:
            return []

        # Sort by confidence (descending), then by start position
        sorted_entities = sorted(entities, key=lambda e: (-e.confidence, e.start))

        # Use interval-based filtering (much faster than nested loops)
        selected: list[Entity] = []
        occupied_ranges: list[tuple[int, int]] = []

        for entity in sorted_entities:
            # Check if this entity overlaps with any occupied range
            is_overlapping = any(
                not (entity.end <= start or entity.start >= end)
                for start, end in occupied_ranges
            )

            if not is_overlapping:
                selected.append(entity)
                occupied_ranges.append((entity.start, entity.end))

        # Return sorted by position
        return sorted(selected, key=lambda e: e.start)

    def _entities_overlap(self, e1: Entity, e2: Entity) -> bool:
        """Check if two entities overlap in position.

        Parameters
        ----------
        e1 : Entity
            First entity
        e2 : Entity
            Second entity

        Returns
        -------
        bool
            True if entities overlap
        """
        return not (e1.end <= e2.start or e2.end <= e1.start)

    def extract_relations(
        self,
        text: str,
        entities: list[Entity],
    ) -> list[Relation]:
        """Extract relations between entities.

        Identifies subject-verb-object patterns and maps to relation predicates.

        Parameters
        ----------
        text : str
            Input text
        entities : list[Entity]
            Recognized entities in the text

        Returns
        -------
        list[Relation]
            Extracted relations between entities
        """
        relations: list[Relation] = []

        # Try each relation pattern
        for pattern, predicate, confidence in self._relation_patterns:
            for match in pattern.finditer(text):
                if len(match.groups()) < 2:
                    continue

                subject_text = match.group(1).strip()
                object_text = match.group(2).strip()

                # Find matching entities
                subject_entity = self._find_entity_by_text(subject_text, entities)
                object_entity = self._find_entity_by_text(object_text, entities)

                if subject_entity and object_entity:
                    relations.append(Relation(
                        subject=subject_entity,
                        predicate=predicate,
                        object=object_entity,
                        confidence=confidence,
                    ))

        return relations

    def _find_entity_by_text(
        self,
        text: str,
        entities: list[Entity],
    ) -> Entity | None:
        """Find entity matching given text.

        Parameters
        ----------
        text : str
            Text to match
        entities : list[Entity]
            List of entities to search

        Returns
        -------
        Entity | None
            Matching entity or None
        """
        text_lower = text.lower()
        for entity in entities:
            if entity.text.lower() in text_lower or text_lower in entity.text.lower():
                return entity
        return None

    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text.

        Uses lexicon-based approach with word scoring.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        float
            Sentiment score from -1.0 (negative) to 1.0 (positive)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0

        scores: list[float] = []
        for word in words:
            if word in self._sentiment_patterns:
                scores.append(self._sentiment_patterns[word])

        if not scores:
            return 0.0

        # Average sentiment with normalization
        avg_sentiment = sum(scores) / len(words)  # Normalize by total words
        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, avg_sentiment * 10))  # Scale up for visibility


# ============================================================================
# INLINE TESTS
# ============================================================================


def test_extract_person_entities() -> None:
    """Test extraction of person entities."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("Dr. Jane Smith and John Doe met yesterday.")

    people = [e for e in result.entities if e.entity_type == EntityType.PERSON]
    assert len(people) >= 2, f"Expected 2+ people, got {len(people)}"

    texts = {p.text for p in people}
    assert any("Jane Smith" in t or "Dr. Jane Smith" in t for t in texts), f"Missing Jane Smith in {texts}"
    assert any("John Doe" in t for t in texts), f"Missing John Doe in {texts}"


def test_extract_organization_entities() -> None:
    """Test extraction of organization entities."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("Apple Inc. and Microsoft Corp. announced a partnership.")

    orgs = [e for e in result.entities if e.entity_type == EntityType.ORGANIZATION]
    assert len(orgs) >= 2, f"Expected 2+ organizations, got {len(orgs)}"

    texts = {o.text for o in orgs}
    assert any("Apple" in t for t in texts), f"Missing Apple in {texts}"
    assert any("Microsoft" in t for t in texts), f"Missing Microsoft in {texts}"


def test_extract_location_entities() -> None:
    """Test extraction of location entities."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("The conference was held in San Francisco, CA and Paris.")

    locations = [e for e in result.entities if e.entity_type == EntityType.LOCATION]
    assert len(locations) >= 2, f"Expected 2+ locations, got {len(locations)}"

    texts = {loc.text for loc in locations}
    assert any("San Francisco" in t or "CA" in t for t in texts), f"Missing San Francisco in {texts}"
    assert any("Paris" in t for t in texts), f"Missing Paris in {texts}"


def test_extract_date_entities() -> None:
    """Test extraction of date entities."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("The meeting is scheduled for January 15, 2024.")

    dates = [e for e in result.entities if e.entity_type == EntityType.DATE]
    assert len(dates) >= 1, f"Expected 1+ dates, got {len(dates)}"

    texts = {d.text for d in dates}
    assert any("January" in t and "2024" in t for t in texts), f"Missing January 2024 in {texts}"


def test_extract_relations_between_entities() -> None:
    """Test extraction of relations between entities."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("Apple Inc. hired John Smith in January 2024.")

    assert len(result.relations) >= 1, f"Expected 1+ relations, got {len(result.relations)}"

    # Check for employment relation
    employment_relations = [r for r in result.relations if 'employ' in r.predicate.lower()]
    assert len(employment_relations) >= 1, f"Expected employment relation, got {[r.predicate for r in result.relations]}"


def test_sentiment_positive() -> None:
    """Test positive sentiment detection."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("This is excellent work! Amazing progress and outstanding achievements.")

    assert result.sentiment > 0.1, f"Expected positive sentiment, got {result.sentiment}"


def test_sentiment_negative() -> None:
    """Test negative sentiment detection."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("This is terrible work with horrible results and complete failure.")

    assert result.sentiment < -0.1, f"Expected negative sentiment, got {result.sentiment}"


def test_sentiment_neutral() -> None:
    """Test neutral sentiment detection."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("The company announced an update to their system.")

    assert -0.15 <= result.sentiment <= 0.15, f"Expected neutral sentiment, got {result.sentiment}"


def test_overlapping_entity_resolution() -> None:
    """Test that overlapping entities are resolved correctly."""
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("Dr. John Smith works at Apple Inc.")

    # Should not have overlapping person entities
    people = [e for e in result.entities if e.entity_type == EntityType.PERSON]
    for i, p1 in enumerate(people):
        for p2 in people[i + 1:]:
            assert not analyzer._entities_overlap(p1, p2), f"Overlapping entities: {p1.text}, {p2.text}"


def test_complex_text_analysis() -> None:
    """Test full analysis on complex text."""
    analyzer = SemanticAnalyzer()
    text = """
    Apple Inc. announced today that CEO Tim Cook hired Dr. Jane Smith as the new CTO.
    The company, based in Cupertino, CA, made this excellent decision in January 2024.
    Dr. Smith previously worked at Google and brings outstanding expertise to the role.
    """

    result = analyzer.analyze(text)

    # Should extract multiple entity types
    entity_types = {e.entity_type for e in result.entities}
    assert EntityType.PERSON in entity_types, "Missing person entities"
    assert EntityType.ORGANIZATION in entity_types, "Missing organization entities"
    assert EntityType.LOCATION in entity_types, "Missing location entities"
    assert EntityType.DATE in entity_types, "Missing date entities"

    # Should extract relations
    assert len(result.relations) >= 1, "Missing relations"

    # Should detect positive sentiment
    assert result.sentiment > 0, f"Expected positive sentiment, got {result.sentiment}"


def run_all_tests() -> tuple[int, int]:
    """Run all tests and return pass/fail counts.

    Returns
    -------
    tuple[int, int]
        (passed_count, failed_count)
    """
    tests = [
        test_extract_person_entities,
        test_extract_organization_entities,
        test_extract_location_entities,
        test_extract_date_entities,
        test_extract_relations_between_entities,
        test_sentiment_positive,
        test_sentiment_negative,
        test_sentiment_neutral,
        test_overlapping_entity_resolution,
        test_complex_text_analysis,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    return passed, failed


if __name__ == "__main__":
    print("Running Semantic Analysis POC Tests...")
    print("=" * 60)

    passed, failed = run_all_tests()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n✓ All tests passed!")

        # Demo usage
        print("\n" + "=" * 60)
        print("Demo: Complex Text Analysis")
        print("=" * 60)

        analyzer = SemanticAnalyzer()
        demo_text = """
        Microsoft Corp. acquired GitHub in June 2018 for $7.5 billion.
        CEO Satya Nadella announced this excellent strategic move from
        their headquarters in Redmond, WA. This acquisition brought
        outstanding talent and revolutionary technology to Microsoft.
        """

        result = analyzer.analyze(demo_text)

        print(f"\nText: {demo_text.strip()}\n")
        print(f"Entities found: {len(result.entities)}")
        for entity in result.entities:
            print(f"  - {entity.text} ({entity.entity_type.value}, confidence={entity.confidence:.2f})")

        print(f"\nRelations found: {len(result.relations)}")
        for relation in result.relations:
            print(f"  - {relation.subject.text} --[{relation.predicate}]--> {relation.object.text} (confidence={relation.confidence:.2f})")

        print(f"\nSentiment: {result.sentiment:.2f} {'(positive)' if result.sentiment > 0 else '(negative)' if result.sentiment < 0 else '(neutral)'}")
    else:
        print(f"\n✗ {failed} test(s) failed")
        exit(1)
