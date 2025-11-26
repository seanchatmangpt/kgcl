"""
Semantic Analysis for entity and relation extraction.

This module provides semantic entity recognition, relation extraction,
and sentiment analysis for knowledge graph content.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(Enum):
    """Semantic entity types."""

    PERSON = "person"
    PLACE = "place"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    ACTION = "action"
    PROPERTY = "property"
    CLASS = "class"
    UNKNOWN = "unknown"


class RelationType(Enum):
    """Semantic relation types."""

    IS_A = "is_a"
    HAS_A = "has_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    SUBCLASS_OF = "subclass_of"
    INSTANCE_OF = "instance_of"
    CAUSES = "causes"
    AFFECTS = "affects"


@dataclass
class SemanticEntity:
    """Identified semantic entity."""

    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int = 0
    end_pos: int = 0
    properties: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "type": self.entity_type.value,
            "confidence": self.confidence,
            "start": self.start_pos,
            "end": self.end_pos,
            "properties": self.properties,
        }


@dataclass
class SemanticRelation:
    """Semantic relation between entities."""

    subject: SemanticEntity
    relation: RelationType
    object: SemanticEntity
    confidence: float

    def to_triple(self) -> tuple[str, str, str]:
        """Convert to RDF-style triple."""
        return (self.subject.text, self.relation.value, self.object.text)


class SemanticAnalyzer:
    """
    Analyze semantic meaning of text.

    Provides entity recognition, relation extraction, and sentiment analysis
    for knowledge graph content understanding.
    """

    def __init__(self) -> None:
        """Initialize semantic analyzer."""
        self.entity_patterns: dict[EntityType, list[re.Pattern[str]]] = {}
        self.relation_patterns: dict[RelationType, list[re.Pattern[str]]] = {}
        self.sentiment_keywords: dict[str, list[str]] = {}
        self._init_patterns()

    def _init_patterns(self) -> None:
        """Initialize entity and relation recognition patterns.

        Uses regex-based pattern matching for entity recognition.
        For production, consider NLP libraries like spaCy or NLTK.
        """
        # Entity patterns using regex for basic recognition
        self.entity_patterns = {
            EntityType.PERSON: [
                re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"),  # John Smith
                re.compile(r"\b(Mr|Mrs|Ms|Dr|Prof)\. [A-Z][a-z]+\b"),
            ],
            EntityType.ORGANIZATION: [
                re.compile(r"\b[A-Z][a-z]+ (Inc|Corp|Ltd|LLC|University|Institute)\b"),
                re.compile(r"\bThe [A-Z][a-z]+ (Company|Foundation|Association)\b"),
            ],
            EntityType.PLACE: [
                re.compile(r"\b[A-Z][a-z]+, [A-Z]{2}\b"),  # City, ST
                re.compile(r"\b(New York|Los Angeles|Chicago|Houston|Phoenix)\b"),
            ],
            EntityType.CONCEPT: [
                re.compile(
                    r"\b(knowledge|ontology|taxonomy|schema|graph)\b", re.IGNORECASE
                )
            ],
            EntityType.ACTION: [
                re.compile(
                    r"\b(create|delete|update|modify|change|add|remove)\b",
                    re.IGNORECASE,
                )
            ],
            EntityType.PROPERTY: [
                re.compile(r"\b[a-z_]+:[a-z_]+\b"),  # namespace:property
                re.compile(r"\brdf:(type|label|comment|seeAlso)\b"),
            ],
            EntityType.CLASS: [
                re.compile(r"\b[A-Z][a-zA-Z]+\b"),  # PascalCase
                re.compile(r"\bowl:(Class|Thing|ObjectProperty)\b"),
            ],
        }

        # Relation patterns
        self.relation_patterns = {
            RelationType.IS_A: [
                re.compile(r"(\w+)\s+is\s+an?\s+(\w+)"),
                re.compile(r"(\w+)\s+are\s+(\w+)"),
            ],
            RelationType.HAS_A: [
                re.compile(r"(\w+)\s+has\s+(\w+)"),
                re.compile(r"(\w+)\s+contains\s+(\w+)"),
            ],
            RelationType.PART_OF: [
                re.compile(r"(\w+)\s+(?:is\s+)?part\s+of\s+(\w+)"),
                re.compile(r"(\w+)\s+belongs\s+to\s+(\w+)"),
            ],
            RelationType.SUBCLASS_OF: [
                re.compile(r"(\w+)\s+(?:is\s+a\s+)?subclass\s+of\s+(\w+)"),
                re.compile(r"(\w+)\s+extends\s+(\w+)"),
            ],
            RelationType.CAUSES: [
                re.compile(r"(\w+)\s+causes\s+(\w+)"),
                re.compile(r"(\w+)\s+results\s+in\s+(\w+)"),
            ],
        }

        # Sentiment keywords
        self.sentiment_keywords = {
            "positive": [
                "good",
                "great",
                "excellent",
                "perfect",
                "amazing",
                "wonderful",
                "fantastic",
                "positive",
                "success",
                "improve",
            ],
            "negative": [
                "bad",
                "poor",
                "terrible",
                "awful",
                "horrible",
                "negative",
                "failure",
                "error",
                "problem",
                "issue",
            ],
            "neutral": [
                "okay",
                "fine",
                "normal",
                "standard",
                "average",
                "typical",
                "regular",
                "common",
            ],
        }

    def extract_entities(
        self, text: str, min_confidence: float = 0.5
    ) -> list[SemanticEntity]:
        """
        Extract semantic entities from text.

        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold

        Returns
        -------
            List of extracted entities
        """
        entities = []
        seen_spans: set[tuple[int, int]] = set()

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    span = (match.start(), match.end())

                    # Avoid overlapping entities
                    if span in seen_spans:
                        continue

                    # Calculate confidence based on pattern specificity
                    confidence = (
                        0.8
                        if entity_type in [EntityType.PERSON, EntityType.ORGANIZATION]
                        else 0.6
                    )

                    if confidence >= min_confidence:
                        entities.append(
                            SemanticEntity(
                                text=match.group(0),
                                entity_type=entity_type,
                                confidence=confidence,
                                start_pos=match.start(),
                                end_pos=match.end(),
                            )
                        )
                        seen_spans.add(span)

        # Sort by position
        entities.sort(key=lambda e: e.start_pos)
        return entities

    def extract_relations(
        self, text: str, entities: list[SemanticEntity] | None = None
    ) -> list[SemanticRelation]:
        """
        Extract semantic relations between entities.

        Args:
            text: Text to analyze
            entities: Pre-extracted entities (optional)

        Returns
        -------
            List of extracted relations
        """
        if entities is None:
            entities = self.extract_entities(text)

        relations = []

        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    if len(groups) >= 2:
                        subject_text = groups[0]
                        object_text = groups[1]

                        # Find matching entities
                        subject = self._find_entity(subject_text, entities)
                        obj = self._find_entity(object_text, entities)

                        # Create relation
                        confidence = 0.7
                        relations.append(
                            SemanticRelation(
                                subject=subject,
                                relation=relation_type,
                                object=obj,
                                confidence=confidence,
                            )
                        )

        return relations

    def _find_entity(self, text: str, entities: list[SemanticEntity]) -> SemanticEntity:
        """Find or create entity matching text."""
        # Look for exact match
        for entity in entities:
            if entity.text.lower() == text.lower():
                return entity

        # Create new entity
        return SemanticEntity(text=text, entity_type=EntityType.UNKNOWN, confidence=0.5)

    def analyze_sentiment(self, text: str) -> dict[str, float]:
        """
        Analyze text sentiment.

        Args:
            text: Text to analyze

        Returns
        -------
            Sentiment scores (positive, negative, neutral)
        """
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        if not words:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

        scores = {"positive": 0, "negative": 0, "neutral": 0}

        for word in words:
            for sentiment, keywords in self.sentiment_keywords.items():
                if word in keywords:
                    scores[sentiment] += 1

        # Normalize
        total = sum(scores.values())
        if total > 0:
            return {k: v / total for k, v in scores.items()}

        # Default to neutral
        return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

    def extract_keywords(self, text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """
        Extract keywords from text.

        Args:
            text: Text to analyze
            top_k: Number of keywords to return

        Returns
        -------
            List of (keyword, score) tuples
        """
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter stopwords (simple list)
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "are",
            "was",
        }
        words = [w for w in words if w not in stopwords and len(w) > 2]

        # Count frequencies
        word_freq: dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Normalize scores
        max_freq = sorted_words[0][1] if sorted_words else 1
        keywords = [(word, freq / max_freq) for word, freq in sorted_words[:top_k]]

        return keywords

    def classify_text(self, text: str) -> dict[str, float]:
        """
        Classify text into categories.

        Args:
            text: Text to classify

        Returns
        -------
            Category scores
        """
        categories = {
            "technical": ["code", "function", "class", "method", "api", "database"],
            "documentation": [
                "guide",
                "tutorial",
                "example",
                "documentation",
                "readme",
            ],
            "query": ["select", "where", "from", "sparql", "query"],
            "ontology": ["class", "property", "relation", "ontology", "schema"],
        }

        text_lower = text.lower()
        scores = {}

        for category, keywords in categories.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = count / len(keywords) if keywords else 0.0

        return scores
