"""Temporal ontology loader for KGCL Hybrid Engine v2.

This module loads and exports all RDF ontology files for 4D temporal modeling,
event sourcing, and Linear Temporal Logic (LTL) validation.
"""

from pathlib import Path
from typing import Final

_ONTOLOGY_DIR: Final[Path] = Path(__file__).parent

# Load all ontology files
TEMPORAL_ONTOLOGY: Final[str] = (_ONTOLOGY_DIR / "temporal_ontology.ttl").read_text()
EVENT_TYPES: Final[str] = (_ONTOLOGY_DIR / "event_types.ttl").read_text()
TEMPORAL_SHAPES: Final[str] = (_ONTOLOGY_DIR / "temporal_shapes.ttl").read_text()
TEMPORAL_LOGIC: Final[str] = (_ONTOLOGY_DIR / "temporal_logic.n3").read_text()
PETRI_NET_ONTOLOGY: Final[Path] = _ONTOLOGY_DIR / "petri_net.ttl"
XES_ONTOLOGY: Final[Path] = _ONTOLOGY_DIR / "xes_rdf.ttl"
SOUNDNESS_SHAPES: Final[Path] = _ONTOLOGY_DIR / "soundness_shapes.ttl"

# Combined ontology graph (for convenience)
FULL_ONTOLOGY: Final[str] = f"{TEMPORAL_ONTOLOGY}\n\n{EVENT_TYPES}\n\n{TEMPORAL_SHAPES}"

__all__ = [
    "EVENT_TYPES",
    "FULL_ONTOLOGY",
    "PETRI_NET_ONTOLOGY",
    "SOUNDNESS_SHAPES",
    "TEMPORAL_LOGIC",
    "TEMPORAL_ONTOLOGY",
    "TEMPORAL_SHAPES",
    "XES_ONTOLOGY",
]
