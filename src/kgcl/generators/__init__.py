"""KGC projection generators package.

Provides generator classes for producing artifacts from RDF knowledge graphs.
Each generator queries RDF data, transforms to domain objects, and renders
artifacts using Jinja2 templates.

Available Generators:
    - ProjectionGenerator: Abstract base class for all generators
    - AgendaGenerator: Daily/weekly calendar agendas
    - QualityReportGenerator: SHACL validation quality reports
    - ConflictReportGenerator: Scheduling and resource conflict reports
    - StaleItemsGenerator: Outdated items and cleanup recommendations

Example:
    >>> from rdflib import Graph
    >>> from kgcl.generators import AgendaGenerator
    >>>
    >>> graph = Graph()
    >>> graph.parse("knowledge_base.ttl")
    >>>
    >>> generator = AgendaGenerator(graph)
    >>> agenda = generator.generate()
    >>> print(agenda)

Version: 1.0.0
Author: KGC Development Team
"""

from .agenda import AgendaGenerator, CalendarEvent, FocusBlock, Reminder
from .base import ProjectionGenerator
from .conflict import ConflictReportGenerator, ResourceConflict, TimeConflict
from .quality import QualityCategory, QualityReportGenerator, Violation
from .stale import CompletedItem, StaleItem, StaleItemsGenerator

__version__ = "1.0.0"

__all__ = [
    # Agenda generator
    "AgendaGenerator",
    "CalendarEvent",
    "CompletedItem",
    # Conflict generator
    "ConflictReportGenerator",
    "FocusBlock",
    # Base generator
    "ProjectionGenerator",
    "QualityCategory",
    # Quality generator
    "QualityReportGenerator",
    "Reminder",
    "ResourceConflict",
    "StaleItem",
    # Stale items generator
    "StaleItemsGenerator",
    "TimeConflict",
    "Violation",
]


def get_available_generators() -> dict[str, type[ProjectionGenerator]]:
    """Get dictionary of available generator classes.

    Returns
    -------
        Dictionary mapping generator names to classes
    """
    return {
        "agenda": AgendaGenerator,
        "quality": QualityReportGenerator,
        "conflict": ConflictReportGenerator,
        "stale": StaleItemsGenerator,
    }


def create_generator(name: str, graph, **kwargs) -> ProjectionGenerator:
    """Factory function for creating generator instances.

    Args:
        name: Generator name (agenda, quality, conflict, stale)
        graph: RDF graph instance
        **kwargs: Additional arguments for specific generators

    Returns
    -------
        Initialized generator instance

    Raises
    ------
        ValueError: If generator name is not recognized

    Example:
        >>> graph = Graph()
        >>> generator = create_generator("agenda", graph, start_date=datetime.now())
        >>> report = generator.generate()
    """
    generators = get_available_generators()

    if name not in generators:
        available = ", ".join(generators.keys())
        raise ValueError(f"Unknown generator: {name}. Available: {available}")

    generator_class = generators[name]
    return generator_class(graph, **kwargs)
