"""SHACL pattern indexing for optimized graph traversal.

Pre-computes indexes of SHACL patterns to enable O(1) lookups instead
of expensive graph traversals during signature generation.
"""

from typing import Dict, List, Optional, Set

from rdflib import Graph
from rdflib.namespace import SH


class SHACLIndex:
    """Pre-computed index for SHACL patterns to optimize graph traversal.

    Builds comprehensive indexes of SHACL shapes at initialization time
    to enable O(1) lookups during signature generation, avoiding repeated
    graph traversals.

    Three main indexes:
    1. Target class → Property shapes
    2. Node shapes → Property shapes
    3. Property shapes → Datatypes

    Parameters
    ----------
    graph : Graph
        RDF graph containing SHACL shapes to index

    Attributes
    ----------
    target_class_index : Dict[str, Set[str]]
        Maps target class URIs to property shape URIs
    property_shape_index : Dict[str, List[str]]
        Maps class URIs to property shapes via node shapes
    datatype_index : Dict[str, str]
        Maps property shape URIs to datatype URIs

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> from rdflib.namespace import SH
    >>> graph = Graph()
    >>> index = SHACLIndex(graph)
    >>> shapes = index.get_property_shapes_for_class("http://example.org/Person")
    >>> isinstance(shapes, list)
    True
    """

    def __init__(self, graph: Graph) -> None:
        """Initialize SHACL index by building all lookup tables."""
        self.graph = graph
        self.target_class_index: dict[str, set[str]] = {}
        self.property_shape_index: dict[str, list[str]] = {}
        self.datatype_index: dict[str, str] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build comprehensive SHACL index for O(1) lookups.

        Scans entire graph once to build all three index structures.
        This upfront cost enables fast lookups during signature generation.
        """
        for prop_shape in self.graph.subjects(SH.path, None):
            for target_class in self.graph.objects(prop_shape, SH.targetClass):
                cls_key = str(target_class)
                if cls_key not in self.target_class_index:
                    self.target_class_index[cls_key] = set()
                self.target_class_index[cls_key].add(str(prop_shape))

        for node_shape in self.graph.subjects(SH.targetClass, None):
            for target_class in self.graph.objects(node_shape, SH.targetClass):
                cls_key = str(target_class)
                if cls_key not in self.property_shape_index:
                    self.property_shape_index[cls_key] = []

                for prop_shape in self.graph.objects(node_shape, SH.property):
                    if self.graph.value(prop_shape, SH.path):
                        self.property_shape_index[cls_key].append(str(prop_shape))

        for prop_shape in self.graph.subjects(SH.path, None):
            datatype = self.graph.value(prop_shape, SH.datatype)
            if datatype:
                self.datatype_index[str(prop_shape)] = str(datatype)

    def get_property_shapes_for_class(self, cls_uri: str) -> list[str]:
        """Get all property shapes for a class with O(1) lookup.

        Combines results from both direct target classes and node shapes
        to provide comprehensive property shape list.

        Parameters
        ----------
        cls_uri : str
            URI of the class to get property shapes for

        Returns
        -------
        List[str]
            List of property shape URIs (deduplicated)

        Examples
        --------
        >>> from rdflib import Graph
        >>> index = SHACLIndex(Graph())
        >>> shapes = index.get_property_shapes_for_class("http://example.org/Person")
        >>> isinstance(shapes, list)
        True
        """
        result: list[str] = []

        if cls_uri in self.target_class_index:
            result.extend(self.target_class_index[cls_uri])

        if cls_uri in self.property_shape_index:
            result.extend(self.property_shape_index[cls_uri])

        return list(set(result))

    def get_datatype_for_shape(self, shape_uri: str) -> str | None:
        """Get datatype for property shape with O(1) lookup.

        Parameters
        ----------
        shape_uri : str
            URI of the property shape

        Returns
        -------
        Optional[str]
            Datatype URI if found, None otherwise

        Examples
        --------
        >>> from rdflib import Graph
        >>> index = SHACLIndex(Graph())
        >>> dtype = index.get_datatype_for_shape("http://example.org/nameShape")
        >>> dtype is None or isinstance(dtype, str)
        True
        """
        return self.datatype_index.get(shape_uri)

    def stats(self) -> dict[str, int]:
        """Get index statistics.

        Returns
        -------
        dict[str, int]
            Statistics about indexed elements

        Examples
        --------
        >>> from rdflib import Graph
        >>> index = SHACLIndex(Graph())
        >>> stats = index.stats()
        >>> stats["target_classes"] == 0
        True
        """
        return {
            "target_classes": len(self.target_class_index),
            "property_shape_mappings": len(self.property_shape_index),
            "datatype_mappings": len(self.datatype_index),
        }
