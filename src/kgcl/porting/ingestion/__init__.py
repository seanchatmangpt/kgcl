"""Code ingestion layer - converts source code to RDF."""

from kgcl.porting.ingestion.java_ingester import JavaIngester
from kgcl.porting.ingestion.python_ingester import PythonIngester
from kgcl.porting.ingestion.rdf_codebase import RDFCodebase

__all__ = ["JavaIngester", "PythonIngester", "RDFCodebase"]

