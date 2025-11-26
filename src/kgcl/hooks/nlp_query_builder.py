"""
NLP Query Builder for natural language to SPARQL conversion.

This module converts natural language questions into SPARQL queries
for knowledge graph querying.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from .semantic_analysis import SemanticAnalyzer


@dataclass
class NLPQuery:
    """Result of NLP query parsing."""

    original_text: str
    sparql_query: str
    confidence: float
    entities: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    query_type: str = "SELECT"
    variables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original": self.original_text,
            "sparql": self.sparql_query,
            "confidence": self.confidence,
            "entities": self.entities,
            "relations": self.relations,
            "type": self.query_type,
            "variables": self.variables,
        }


class NLPQueryBuilder:
    """
    Convert natural language to SPARQL.

    Provides pattern-based translation of natural language questions
    into SPARQL queries for knowledge graph querying.
    """

    def __init__(self) -> None:
        """Initialize NLP query builder."""
        self.templates: dict[str, dict[str, Any]] = {}
        self.semantic_analyzer = SemanticAnalyzer()
        self._load_templates()

    def _load_templates(self) -> None:
        """Load SPARQL templates for common patterns."""
        self.templates = {
            # "What is X?" pattern
            "what_is": {
                "patterns": [
                    r"what\s+is\s+(?:a|an|the)?\s*(\w+)",
                    r"describe\s+(\w+)",
                    r"tell\s+me\s+about\s+(\w+)",
                ],
                "sparql": """
                    SELECT ?property ?value
                    WHERE {{
                        {entity} ?property ?value .
                    }}
                    LIMIT 100
                """,
                "confidence": 0.8,
            },
            # "Find all X" pattern
            "find_all": {
                "patterns": [
                    r"(?:find|list|show)\s+(?:all|the)?\s*(\w+)",
                    r"what\s+are\s+(?:all|the)?\s*(\w+)",
                ],
                "sparql": """
                    SELECT ?item ?label
                    WHERE {{
                        ?item a {class} .
                        OPTIONAL {{ ?item rdfs:label ?label }}
                    }}
                    LIMIT 100
                """,
                "confidence": 0.7,
            },
            # "Count X" pattern
            "count": {
                "patterns": [r"how\s+many\s+(\w+)", r"count\s+(?:all|the)?\s*(\w+)"],
                "sparql": """
                    SELECT (COUNT(?item) as ?count)
                    WHERE {{
                        ?item a {class} .
                    }}
                """,
                "confidence": 0.8,
            },
            # "Which X has Y" pattern
            "which_has": {
                "patterns": [
                    r"which\s+(\w+)\s+(?:has|have)\s+(\w+)",
                    r"(\w+)\s+with\s+(\w+)",
                ],
                "sparql": """
                    SELECT ?item ?label
                    WHERE {{
                        ?item a {class1} .
                        ?item {property} {class2} .
                        OPTIONAL {{ ?item rdfs:label ?label }}
                    }}
                    LIMIT 100
                """,
                "confidence": 0.6,
            },
            # "X of Y" pattern
            "property_of": {
                "patterns": [
                    r"(\w+)\s+of\s+(\w+)",
                    r"what\s+is\s+the\s+(\w+)\s+of\s+(\w+)",
                ],
                "sparql": """
                    SELECT ?value
                    WHERE {{
                        {entity} {property} ?value .
                    }}
                    LIMIT 100
                """,
                "confidence": 0.7,
            },
            # "Show properties" pattern
            "show_properties": {
                "patterns": [r"(?:show|list)\s+properties", r"what\s+properties"],
                "sparql": """
                    SELECT DISTINCT ?property ?count
                    WHERE {{
                        ?s ?property ?o .
                    }}
                    GROUP BY ?property
                    ORDER BY DESC(?count)
                    LIMIT 100
                """,
                "confidence": 0.9,
            },
            # "Show classes" pattern
            "show_classes": {
                "patterns": [
                    r"(?:show|list)\s+classes",
                    r"what\s+classes",
                    r"all\s+types",
                ],
                "sparql": """
                    SELECT DISTINCT ?class (COUNT(?instance) as ?count)
                    WHERE {{
                        ?instance a ?class .
                    }}
                    GROUP BY ?class
                    ORDER BY DESC(?count)
                    LIMIT 100
                """,
                "confidence": 0.9,
            },
        }

    def parse_question(self, question: str) -> NLPQuery:
        """
        Parse natural language question to SPARQL.

        Args:
            question: Natural language question

        Returns
        -------
            NLPQuery with SPARQL translation
        """
        question = question.strip().lower()

        # Step 1: Entity extraction
        entities = self.semantic_analyzer.extract_entities(question)
        entity_texts = [e.text for e in entities]

        # Step 2: Relation extraction
        relations = self.semantic_analyzer.extract_relations(question, entities)
        relation_texts = [r.relation.value for r in relations]

        # Step 3: Pattern matching
        best_match = None
        best_confidence = 0.0
        matched_groups = []

        for template_name, template in self.templates.items():
            for pattern_str in template["patterns"]:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                match = pattern.search(question)

                if match:
                    confidence = template["confidence"]
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = template_name
                        matched_groups = list(match.groups())

        # Step 4: SPARQL construction
        if best_match:
            sparql = self._build_sparql_from_template(
                best_match, matched_groups, entity_texts, relation_texts
            )
            query_type = self._extract_query_type(sparql)
            variables = self._extract_variables(sparql)
        else:
            # Fallback: generic query
            sparql = self._build_generic_query(entity_texts, relation_texts)
            query_type = "SELECT"
            variables = ["?s", "?p", "?o"]
            best_confidence = 0.3

        return NLPQuery(
            original_text=question,
            sparql_query=sparql,
            confidence=best_confidence,
            entities=entity_texts,
            relations=relation_texts,
            query_type=query_type,
            variables=variables,
        )

    def _build_sparql_from_template(
        self,
        template_name: str,
        groups: list[str],
        entities: list[str],
        relations: list[str],
    ) -> str:
        """Build SPARQL query from template."""
        template = self.templates[template_name]
        sparql = template["sparql"]

        # Fill in placeholders
        if template_name == "what_is":
            entity = groups[0] if groups else "?unknown"
            sparql = sparql.replace("{entity}", f":{entity}")

        elif template_name == "find_all" or template_name == "count":
            class_name = groups[0] if groups else "Thing"
            sparql = sparql.replace("{class}", f":{class_name}")

        elif template_name == "which_has":
            class1 = groups[0] if len(groups) > 0 else "Thing"
            class2 = groups[1] if len(groups) > 1 else "Thing"
            sparql = sparql.replace("{class1}", f":{class1}")
            sparql = sparql.replace("{class2}", f":{class2}")
            sparql = sparql.replace("{property}", "?prop")

        elif template_name == "property_of":
            property_name = groups[0] if len(groups) > 0 else "property"
            entity = groups[1] if len(groups) > 1 else "entity"
            sparql = sparql.replace("{property}", f":{property_name}")
            sparql = sparql.replace("{entity}", f":{entity}")

        return sparql.strip()

    def _build_generic_query(self, entities: list[str], relations: list[str]) -> str:
        """Build generic SPARQL query as fallback."""
        if entities:
            # Query about specific entity
            entity = entities[0]
            return f"""
                SELECT ?property ?value
                WHERE {{
                    :{entity} ?property ?value .
                }}
                LIMIT 100
            """.strip()
        # Very generic query
        return """
                SELECT ?s ?p ?o
                WHERE {
                    ?s ?p ?o .
                }
                LIMIT 100
            """.strip()

    def _extract_query_type(self, sparql: str) -> str:
        """Extract query type from SPARQL."""
        sparql_upper = sparql.upper()

        if "SELECT" in sparql_upper:
            return "SELECT"
        if "CONSTRUCT" in sparql_upper:
            return "CONSTRUCT"
        if "ASK" in sparql_upper:
            return "ASK"
        if "DESCRIBE" in sparql_upper:
            return "DESCRIBE"
        return "UNKNOWN"

    def _extract_variables(self, sparql: str) -> list[str]:
        """Extract variables from SPARQL query."""
        # Find all ?variable patterns
        pattern = re.compile(r"\?(\w+)")
        matches = pattern.findall(sparql)
        return list(set(matches))  # Remove duplicates

    def build_sparql(
        self, entities: list[str], relations: list[str], query_type: str = "SELECT"
    ) -> str:
        """
        Build SPARQL query from entities and relations.

        Args:
            entities: List of entity names
            relations: List of relation types
            query_type: Type of SPARQL query

        Returns
        -------
            SPARQL query string
        """
        if not entities and not relations:
            return "SELECT * WHERE { ?s ?p ?o } LIMIT 100"

        if len(entities) == 1 and not relations:
            # Simple entity query
            return f"""
                SELECT ?property ?value
                WHERE {{
                    :{entities[0]} ?property ?value .
                }}
                LIMIT 100
            """.strip()

        if len(entities) >= 2 and relations:
            # Relation query
            subject = entities[0]
            obj = entities[1]
            relation = relations[0] if relations else "?relation"

            return f"""
                SELECT ?s ?p ?o
                WHERE {{
                    ?s a :{subject} .
                    ?o a :{obj} .
                    ?s :{relation} ?o .
                }}
                LIMIT 100
            """.strip()

        # Default
        return self._build_generic_query(entities, relations)

    def add_template(
        self,
        name: str,
        patterns: list[str],
        sparql_template: str,
        confidence: float = 0.5,
    ) -> None:
        """
        Add custom query template.

        Args:
            name: Template name
            patterns: List of regex patterns
            sparql_template: SPARQL template with placeholders
            confidence: Confidence score for matches
        """
        self.templates[name] = {
            "patterns": patterns,
            "sparql": sparql_template,
            "confidence": confidence,
        }

    def get_suggestions(self, partial_query: str) -> list[str]:
        """
        Get query suggestions for partial input.

        Args:
            partial_query: Partial query text

        Returns
        -------
            List of suggested completions
        """
        suggestions = []

        # Common question starters
        starters = [
            "What is",
            "Find all",
            "How many",
            "Which",
            "Show me",
            "List all",
            "Count",
            "Describe",
        ]

        partial_lower = partial_query.lower()

        for starter in starters:
            if starter.lower().startswith(partial_lower):
                suggestions.append(starter)

        return suggestions[:5]
