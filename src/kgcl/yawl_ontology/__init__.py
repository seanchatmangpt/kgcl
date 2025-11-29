"""YAWL Java codebase ontology generation and exploration.

This module generates RDF/Turtle ontologies from YAWL Java source code,
and provides high-performance SPARQL queries for architecture analysis
and Python stub generation.
"""

from kgcl.yawl_ontology.explorer import YawlOntologyExplorer
from kgcl.yawl_ontology.generator import YawlOntologyGenerator
from kgcl.yawl_ontology.parser import JavaParser
from kgcl.yawl_ontology.stub_generator import StubGenerator

__all__ = ["YawlOntologyGenerator", "JavaParser", "YawlOntologyExplorer", "StubGenerator"]
