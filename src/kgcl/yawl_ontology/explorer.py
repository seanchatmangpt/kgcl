"""YAWL ontology explorer using PyOxigraph for high-performance SPARQL queries.

Analyzes YAWL Java architecture to guide Python implementation:
- Class hierarchies (inheritance trees)
- Method signatures (API surface)
- Dependencies (field types, composition)
- Architecture patterns (decomposition types, net relationships)
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import pyoxigraph
from pyoxigraph import Variable


@dataclass
class QueryResult:
    """SPARQL query result with performance metrics."""

    data: list[dict[str, str]]
    duration_ms: float
    count: int


@dataclass
class ClassInfo:
    """Class metadata from ontology."""

    name: str
    package: str
    extends: str | None = None
    implements: list[str] = field(default_factory=list)


@dataclass
class MethodSignature:
    """Method signature from ontology."""

    name: str
    return_type: str
    parameters: str
    modifiers: list[str] = field(default_factory=list)


class YawlOntologyExplorer:
    """Explore YAWL ontology using PyOxigraph for architecture analysis."""

    def __init__(self, ttl_path: Path) -> None:
        """Initialize explorer with YAWL ontology file.

        Parameters
        ----------
        ttl_path : Path
            Path to YAWL ontology Turtle file
        """
        self.store = pyoxigraph.Store()
        self._load_ontology(ttl_path)

    def _load_ontology(self, ttl_path: Path) -> None:
        """Load ontology into PyOxigraph store."""
        if not ttl_path.exists():
            msg = f"Ontology file not found: {ttl_path}"
            raise FileNotFoundError(msg)

        with ttl_path.open("rb") as f:
            self.store.load(f, "text/turtle", base_iri="http://yawlfoundation.org/ontology/")

        triple_count = len(self.store)
        print(f"Loaded ontology: {triple_count:,} triples from {ttl_path.name}")

    def query(self, sparql: str, description: str = "") -> QueryResult:
        """Execute SPARQL query and return results with timing.

        Parameters
        ----------
        sparql : str
            SPARQL query string
        description : str
            Human-readable query description

        Returns
        -------
        QueryResult
            Query results with performance metrics
        """
        if description:
            print(f"\n[Query] {description}")

        start_time = time.time()
        results = list(self.store.query(sparql))
        duration_ms = (time.time() - start_time) * 1000

        # Extract variable names from SPARQL query
        var_names = []
        select_match = re.search(r"SELECT\s+(.*?)\s+WHERE", sparql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            var_names = [v.strip("?") for v in re.findall(r"\?(\w+)", select_clause)]

        data = []
        for solution in results:
            row = {}
            for var_name in var_names:
                value = solution[Variable(var_name)]
                # Clean up RDF literal quotes
                str_value = str(value).strip('"') if value else None
                row[var_name] = str_value
            data.append(row)

        return QueryResult(data=data, duration_ms=duration_ms, count=len(data))

    def find_subclasses(self, base_class: str) -> list[ClassInfo]:
        """Find all classes that extend a given base class.

        Parameters
        ----------
        base_class : str
            Base class name (e.g., "YDecomposition")

        Returns
        -------
        list[ClassInfo]
            List of subclasses with package info
        """
        query = f"""
        PREFIX yawl: <http://yawlfoundation.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?className ?package
        WHERE {{
            ?class yawl:extends yawl:{base_class} .
            ?class rdfs:label ?className .
            ?class yawl:inPackage ?pkg .
            ?pkg rdfs:label ?package .
        }}
        ORDER BY ?package
        """

        result = self.query(query, f"Finding subclasses of {base_class}")
        return [ClassInfo(name=row["className"], package=row["package"], extends=base_class) for row in result.data]

    def get_class_methods(self, class_name: str) -> list[MethodSignature]:
        """Get all methods for a specific class.

        Parameters
        ----------
        class_name : str
            Class name (e.g., "YEngine")

        Returns
        -------
        list[MethodSignature]
            List of method signatures
        """
        query = f"""
        PREFIX yawl: <http://yawlfoundation.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?methodName ?returnType ?signature
        WHERE {{
            yawl:{class_name} yawl:hasMethod ?method .
            ?method rdfs:label ?methodName .
            ?method yawl:returnType ?returnType .
            ?method yawl:signature ?signature .
        }}
        ORDER BY ?methodName
        """

        result = self.query(query, f"Analyzing API surface of {class_name}")
        methods = []
        for row in result.data:
            # The signature field contains full method signature
            # But we already have methodName and returnType separately
            # Parameters come from parsing the signature or using a separate query
            # For now, we'll just use what we have
            methods.append(
                MethodSignature(
                    name=row["methodName"],
                    return_type=row["returnType"],
                    parameters=row.get("signature", ""),  # Full signature as parameters for now
                )
            )
        return methods

    def find_classes_using_type(self, type_name: str) -> list[dict[str, str]]:
        """Find classes that depend on a specific type (field dependencies).

        Parameters
        ----------
        type_name : str
            Type name to search for (e.g., "YNet")

        Returns
        -------
        list[dict[str, str]]
            List of classes and their fields that use this type
        """
        query = f"""
        PREFIX yawl: <http://yawlfoundation.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?className ?package
        WHERE {{
            ?class yawl:hasField ?field .
            ?class rdfs:label ?className .
            ?class yawl:inPackage ?pkg .
            ?pkg rdfs:label ?package .
            ?field rdfs:label ?fieldName .
            FILTER(CONTAINS(LCASE(?fieldName), LCASE("{type_name}")))
        }}
        ORDER BY ?package
        """

        result = self.query(query, f"Finding classes that use {type_name}")
        return result.data

    def analyze_decomposition_hierarchy(self) -> dict[str, list[ClassInfo]]:
        """Analyze YAWL decomposition hierarchy (core architecture pattern).

        Returns
        -------
        dict[str, list[ClassInfo]]
            Decomposition types mapped to their subclasses
        """
        print("\n" + "=" * 80)
        print("YAWL Decomposition Hierarchy Analysis")
        print("=" * 80)

        # Find all YDecomposition subclasses
        subclasses = self.find_subclasses("YDecomposition")

        hierarchy = {"YDecomposition": subclasses}

        # Recursively find subclasses of each subclass
        for subclass in subclasses:
            children = self.find_subclasses(subclass.name)
            if children:
                hierarchy[subclass.name] = children

        return hierarchy

    def generate_implementation_plan(self, class_name: str) -> dict[str, list[MethodSignature]]:
        """Generate Python implementation plan for a Java class.

        Parameters
        ----------
        class_name : str
            Java class name (e.g., "YEngine")

        Returns
        -------
        dict[str, list[MethodSignature]]
            Implementation plan with categorized methods
        """
        print(f"\n{'=' * 80}")
        print(f"Implementation Plan for {class_name}")
        print("=" * 80)

        methods = self.get_class_methods(class_name)

        # Categorize methods by return type
        plan: dict[str, list[MethodSignature]] = {"lifecycle": [], "queries": [], "mutations": [], "utilities": []}

        for method in methods:
            if method.return_type == "void":
                plan["mutations"].append(method)
            elif "get" in method.name.lower() or "is" in method.name.lower():
                plan["queries"].append(method)
            elif "start" in method.name.lower() or "stop" in method.name.lower():
                plan["lifecycle"].append(method)
            else:
                plan["utilities"].append(method)

        return plan

    def export_architecture_summary(self, output_path: Path) -> None:
        """Export comprehensive architecture analysis to markdown.

        Parameters
        ----------
        output_path : Path
            Output markdown file path
        """
        lines = ["# YAWL Architecture Summary", "", f"*Generated from ontology: {len(self.store):,} triples*", ""]

        # 1. Decomposition hierarchy
        lines.append("## Decomposition Hierarchy")
        hierarchy = self.analyze_decomposition_hierarchy()
        for base, children in hierarchy.items():
            lines.append(f"\n### {base}")
            for child in children:
                lines.append(f"- `{child.name}` ({child.package})")

        # 2. Core classes
        lines.append("\n## Core Engine Classes")
        core_classes = ["YEngine", "YWorkItem", "YSpecification", "YNet", "YTask"]
        for cls in core_classes:
            methods = self.get_class_methods(cls)
            if methods:
                lines.append(f"\n### {cls}")
                lines.append(f"**Methods:** {len(methods)}")
                for m in methods[:5]:  # Show first 5
                    lines.append(f"- `{m.signature}`")

        output_path.write_text("\n".join(lines))
        print(f"\n✓ Exported architecture summary: {output_path}")
