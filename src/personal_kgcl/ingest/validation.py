"""SHACL validation support for Apple ingest graphs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

DEFAULT_KGC_DIR = Path(__file__).resolve().parents[3] / ".kgc"
DEFAULT_SHAPES = [DEFAULT_KGC_DIR / "types.ttl", DEFAULT_KGC_DIR / "invariants.shacl.ttl"]


@dataclass(frozen=True)
class ValidationReport:
    conforms: bool
    text: str


class AppleIngestValidator:
    """Wrapper around pyshacl for the `.kgc` shapes."""

    def __init__(self, shapes_paths: list[Path] | None = None) -> None:
        self.shapes_paths = shapes_paths or DEFAULT_SHAPES

    def _load_shapes(self) -> Graph:
        shapes_graph = Graph()
        for path in self.shapes_paths:
            if not path.exists():
                continue
            shapes_graph.parse(path, format="turtle")
        return shapes_graph

    def validate(self, graph: Graph) -> ValidationReport:
        shapes_graph = self._load_shapes()
        conforms, _, report_text = validate(
            data_graph=graph, shacl_graph=shapes_graph, inference="rdfs", allow_infos=True, allow_warnings=True
        )
        return ValidationReport(conforms=bool(conforms), text=str(report_text))


