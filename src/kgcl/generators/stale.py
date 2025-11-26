"""Stale items generator for identifying outdated knowledge graph entries.

Finds items not updated in 30+ days, completed items not archived,
and suggests decommissioning with cleanup savings estimates.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, RDF, RDFS

from .base import ProjectionGenerator

# Define namespaces
KGC = Namespace("http://example.org/kgc/")


@dataclass
class StaleItem:
    """Domain object for stale knowledge graph items."""

    uri: str
    label: str
    item_type: str
    last_modified: datetime
    days_stale: int
    status: str | None = None
    size_estimate: int = 0  # Size in triples

    def staleness_level(self) -> str:
        """Get staleness level (stale, very_stale, ancient)."""
        if self.days_stale > 180:
            return "ancient"
        if self.days_stale > 90:
            return "very_stale"
        return "stale"


@dataclass
class CompletedItem:
    """Domain object for completed but unarchived items."""

    uri: str
    label: str
    item_type: str
    completed_date: datetime
    days_unarchived: int


@dataclass
class CleanupEstimate:
    """Domain object for cleanup savings estimate."""

    total_stale_items: int
    total_completed_items: int
    estimated_triples_saved: int
    storage_reduction_mb: float
    query_performance_gain: str  # "low", "medium", "high"


class StaleItemsGenerator(ProjectionGenerator):
    """Generate reports for stale and outdated knowledge graph items.

    Identifies:
    - Items not updated in 30+ days
    - Completed items not archived
    - Potential cleanup candidates

    Provides cleanup recommendations and savings estimates.
    """

    STALE_THRESHOLD_DAYS = 30
    TRIPLE_SIZE_BYTES = 100  # Average bytes per triple

    def __init__(self, graph: Graph, stale_threshold: int = 30) -> None:
        """Initialize stale items generator.

        Args:
            graph: RDF graph containing knowledge base
            stale_threshold: Days before item considered stale
        """
        super().__init__(graph)
        self.stale_threshold = stale_threshold
        self.cutoff_date = datetime.now(tz=UTC) - timedelta(days=stale_threshold)

    def gather_data(self) -> dict[str, Any]:
        """Gather stale items from RDF graph.

        Returns
        -------
            Dictionary with stale items, completed items, and cleanup estimates
        """
        stale_items = self._query_stale_items()
        completed_items = self._query_completed_items()
        cleanup_estimate = self._calculate_cleanup_estimate(stale_items, completed_items)

        return {
            "cutoff_date": self.cutoff_date,
            "stale_items": sorted(stale_items, key=lambda i: i.days_stale, reverse=True),
            "completed_items": sorted(completed_items, key=lambda i: i.days_unarchived, reverse=True),
            "cleanup_estimate": cleanup_estimate,
            "total_items": len(stale_items) + len(completed_items),
        }

    def _query_stale_items(self) -> list[StaleItem]:
        """Query RDF graph for stale items."""
        stale_items = []

        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX dcterms: <{DCTERMS}>
        PREFIX rdfs: <{RDFS}>

        SELECT ?item ?label ?type ?modified ?status
        WHERE {{
            ?item a ?type .
            ?item rdfs:label ?label .
            OPTIONAL {{ ?item dcterms:modified ?modified }}
            OPTIONAL {{ ?item kgc:status ?status }}
            FILTER(?type != <{RDF.Property}> && ?type != <{RDFS.Class}>)
        }}
        """

        results = self.graph.query(query)

        for row in results:
            # Get last modified date, default to very old if missing
            if row.modified:
                last_modified = self._parse_datetime(row.modified)
            else:
                last_modified = datetime(2000, 1, 1, tzinfo=UTC)

            # Calculate days since last modification
            days_stale = (datetime.now(tz=UTC) - last_modified).days

            # Only include items past threshold
            if days_stale < self.stale_threshold:
                continue

            # Estimate size (count related triples)
            size_estimate = self._estimate_item_size(row.item)

            stale_items.append(
                StaleItem(
                    uri=str(row.item),
                    label=str(row.label),
                    item_type=self._format_type(row.type),
                    last_modified=last_modified,
                    days_stale=days_stale,
                    status=str(row.status) if row.status else None,
                    size_estimate=size_estimate,
                )
            )

        return stale_items

    def _query_completed_items(self) -> list[CompletedItem]:
        """Query RDF graph for completed but unarchived items."""
        completed_items = []

        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX rdfs: <{RDFS}>

        SELECT ?item ?label ?type ?completedDate
        WHERE {{
            ?item a ?type .
            ?item rdfs:label ?label .
            ?item kgc:status "completed" .
            ?item kgc:completedDate ?completedDate .
            FILTER NOT EXISTS {{ ?item kgc:archived true }}
        }}
        """

        results = self.graph.query(query)

        for row in results:
            completed_date = self._parse_datetime(row.completedDate)
            days_unarchived = (datetime.now(tz=UTC) - completed_date).days

            # Only include items completed > 7 days ago
            if days_unarchived < 7:
                continue

            completed_items.append(
                CompletedItem(
                    uri=str(row.item),
                    label=str(row.label),
                    item_type=self._format_type(row.type),
                    completed_date=completed_date,
                    days_unarchived=days_unarchived,
                )
            )

        return completed_items

    def _estimate_item_size(self, item_uri: str) -> int:
        """Estimate size of item in triples.

        Args:
            item_uri: URI of item to measure

        Returns
        -------
            Estimated number of triples related to item
        """
        # Count triples where item is subject or object
        count_query = f"""
        SELECT (COUNT(*) as ?count)
        WHERE {{
            {{ <{item_uri}> ?p ?o }}
            UNION
            {{ ?s ?p <{item_uri}> }}
        }}
        """

        results = self.graph.query(count_query)
        for row in results:
            return int(row.count)

        return 0

    def _calculate_cleanup_estimate(
        self, stale_items: list[StaleItem], completed_items: list[CompletedItem]
    ) -> CleanupEstimate:
        """Calculate estimated savings from cleanup.

        Args:
            stale_items: List of stale items
            completed_items: List of completed items

        Returns
        -------
            Cleanup estimate with savings projections
        """
        total_triples = sum(item.size_estimate for item in stale_items)

        # Estimate storage reduction (100 bytes per triple average)
        storage_mb = (total_triples * self.TRIPLE_SIZE_BYTES) / (1024 * 1024)

        # Estimate query performance gain
        if total_triples > 10000:
            perf_gain = "high"
        elif total_triples > 1000:
            perf_gain = "medium"
        else:
            perf_gain = "low"

        return CleanupEstimate(
            total_stale_items=len(stale_items),
            total_completed_items=len(completed_items),
            estimated_triples_saved=total_triples,
            storage_reduction_mb=storage_mb,
            query_performance_gain=perf_gain,
        )

    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from RDF literal."""
        if isinstance(value, Literal):
            return value.toPython()
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _format_type(self, type_uri: Any) -> str:
        """Format type URI for display."""
        uri_str = str(type_uri)
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        if "/" in uri_str:
            return uri_str.split("/")[-1]
        return uri_str

    def generate(self, template_name: str = "default.md") -> str:
        """Generate stale items report artifact.

        Args:
            template_name: Template file name

        Returns
        -------
            Rendered markdown stale items report
        """
        data = self.gather_data()
        self.validate_data(data, ["stale_items", "completed_items", "cleanup_estimate"])
        return self.render_template(template_name, data)
