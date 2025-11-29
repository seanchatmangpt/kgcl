"""Query helper for codebase ontology index.

Provides high-level API for querying the codebase ontology index
with fast lookups, navigation, and search capabilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

YAWL = Namespace("http://yawlfoundation.org/ontology/")
INDEX = Namespace("http://yawlfoundation.org/ontology/index#")


class CodebaseIndex:
    """Query helper for codebase ontology index.

    Provides high-level methods for common queries against the
    codebase ontology index, with fast lookups and navigation.

    Parameters
    ----------
    index_file : Path | str
        Path to the index.ttl file

    Examples
    --------
    >>> index = CodebaseIndex("ontology/codebase/index.ttl")
    >>> class_info = index.find_class("YControlPanel")
    >>> classes = index.find_classes_in_package("org.yawlfoundation.yawl.controlpanel")
    >>> hierarchy = index.get_inheritance_hierarchy("JMXMemoryStatistics")
    """

    def __init__(self, index_file: Path | str) -> None:
        """Initialize the index.

        Parameters
        ----------
        index_file : Path | str
            Path to the index.ttl file
        """
        self.index_file = Path(index_file)
        if not self.index_file.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_file}")

        self.graph = Graph()
        self.graph.parse(str(self.index_file), format="turtle")
        self.graph.bind("yawl", YAWL)
        self.graph.bind("index", INDEX)

    def find_class(self, class_name: str) -> dict[str, Any] | None:
        """Find class by name (simple or fully qualified).

        Parameters
        ----------
        class_name : str
            Class name (simple or fully qualified)

        Returns
        -------
        dict[str, Any] | None
            Class information or None if not found

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> info = index.find_class("YControlPanel")
        >>> info["file_path"]
        'org/yawlfoundation/yawl/controlpanel/YControlPanel.ttl'
        """
        # Try fully qualified first - match any literal with this value
        for index_uri in self.graph.subjects(INDEX.fullyQualifiedName, None):
            fq_name = self.graph.value(index_uri, INDEX.fullyQualifiedName)
            if fq_name and str(fq_name) == class_name:
                return self._extract_class_info(index_uri)

        # Try simple name - match any literal with this value
        for index_uri in self.graph.subjects(INDEX.className, None):
            cn = self.graph.value(index_uri, INDEX.className)
            if cn and str(cn) == class_name:
                return self._extract_class_info(index_uri)

        return None

    def find_classes_in_package(self, package_name: str) -> list[str]:
        """Find all classes in a package.

        Parameters
        ----------
        package_name : str
            Fully qualified package name

        Returns
        -------
        list[str]
            List of fully qualified class names

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> classes = index.find_classes_in_package("org.yawlfoundation.yawl.controlpanel")
        >>> "YControlPanel" in [c.split(".")[-1] for c in classes]
        True
        """
        classes: list[str] = []

        for package_index in self.graph.subjects(INDEX.packageName, None):
            pkg_name = self.graph.value(package_index, INDEX.packageName)
            if not pkg_name or str(pkg_name) != package_name:
                continue
            for class_index in self.graph.objects(package_index, INDEX.hasClass):
                fq_name = self.graph.value(class_index, INDEX.fullyQualifiedName)
                if fq_name:
                    classes.append(str(fq_name))

        return classes

    def get_inheritance_hierarchy(self, class_name: str) -> dict[str, Any]:
        """Get inheritance hierarchy for a class.

        Parameters
        ----------
        class_name : str
            Class name (simple or fully qualified)

        Returns
        -------
        dict[str, Any]
            Dictionary with 'extends', 'implements', and 'subclasses'

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> hierarchy = index.get_inheritance_hierarchy("JMXMemoryStatistics")
        >>> hierarchy["extends"]
        'JMXStatistics'
        """
        class_info = self.find_class(class_name)
        if not class_info:
            return {"extends": None, "implements": [], "subclasses": []}

        # Find class index URI by fully qualified name
        class_index_uri = None
        for index_uri in self.graph.subjects(INDEX.fullyQualifiedName, None):
            fq_name = self.graph.value(index_uri, INDEX.fullyQualifiedName)
            if fq_name and str(fq_name) == class_info["fully_qualified"]:
                class_index_uri = index_uri
                break

        if not class_index_uri:
            return {"extends": None, "implements": [], "subclasses": []}

        # Get extends
        extends = None
        extends_uri = self.graph.value(class_index_uri, INDEX.extendsClass)
        if extends_uri:
            # Extract class name from URI
            extends_str = str(extends_uri)
            # Handle different URI formats: yawl:ClassName, http://.../ClassName
            if ":" in extends_str and not extends_str.startswith("http"):
                # Namespace prefix format: yawl:ClassName
                extends = extends_str.split(":")[-1]
            elif "/" in extends_str:
                # Full URI format: http://.../ClassName
                extends = extends_str.split("/")[-1]
            else:
                extends = extends_str

        # Get implements
        implements: list[str] = []
        for impl_uri in self.graph.objects(class_index_uri, INDEX.implementsInterface):
            impl_name = str(impl_uri).split(":")[-1]
            implements.append(impl_name)

        # Get subclasses
        subclasses: list[str] = []
        for subclass_index in self.graph.objects(class_index_uri, INDEX.hasSubclass):
            subclass_fq = self.graph.value(subclass_index, INDEX.fullyQualifiedName)
            if subclass_fq:
                subclasses.append(str(subclass_fq))

        return {"extends": extends, "implements": implements, "subclasses": subclasses}

    def find_classes_with_method(self, method_name: str) -> list[str]:
        """Find all classes that have a method with the given name.

        Parameters
        ----------
        method_name : str
            Method name

        Returns
        -------
        list[str]
            List of fully qualified class names

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> classes = index.find_classes_with_method("toString")
        >>> len(classes) > 0
        True
        """
        classes: list[str] = []

        for method_index in self.graph.subjects(INDEX.methodName, None):
            m_name = self.graph.value(method_index, INDEX.methodName)
            if not m_name or str(m_name) != method_name:
                continue
            for class_index in self.graph.objects(method_index, INDEX.hasMethodNamed):
                fq_name = self.graph.value(class_index, INDEX.fullyQualifiedName)
                if fq_name:
                    classes.append(str(fq_name))

        return classes

    def find_classes_with_field(self, field_name: str) -> list[str]:
        """Find all classes that have a field with the given name.

        Parameters
        ----------
        field_name : str
            Field name

        Returns
        -------
        list[str]
            List of fully qualified class names

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> classes = index.find_classes_with_field("heap")
        >>> len(classes) > 0
        True
        """
        classes: list[str] = []

        for field_index in self.graph.subjects(INDEX.fieldName, None):
            f_name = self.graph.value(field_index, INDEX.fieldName)
            if not f_name or str(f_name) != field_name:
                continue
            for class_index in self.graph.objects(field_index, INDEX.hasFieldNamed):
                fq_name = self.graph.value(class_index, INDEX.fullyQualifiedName)
                if fq_name:
                    classes.append(str(fq_name))

        return classes

    def find_references(self, class_name: str) -> list[str]:
        """Find all classes that reference the given class.

        Parameters
        ----------
        class_name : str
            Class name (simple or fully qualified)

        Returns
        -------
        list[str]
            List of fully qualified class names that reference this class

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> refs = index.find_references("JMXStatistics")
        >>> len(refs) > 0
        True
        """
        class_info = self.find_class(class_name)
        if not class_info:
            return []

        # Find class index URI by fully qualified name
        class_index_uri = None
        for index_uri in self.graph.subjects(INDEX.fullyQualifiedName, None):
            fq_name = self.graph.value(index_uri, INDEX.fullyQualifiedName)
            if fq_name and str(fq_name) == class_info["fully_qualified"]:
                class_index_uri = index_uri
                break

        if not class_index_uri:
            return []

        references: list[str] = []

        # Find all reference entries that reference this class
        # Can reference by class index URI or by YAWL namespace URI
        class_uri = self.graph.value(class_index_uri, INDEX.indexedClass)
        if class_uri:
            # Find references by class URI (YAWL namespace)
            for ref_index in self.graph.subjects(INDEX.referencesClass, class_uri):
                ref_class_index = self.graph.value(ref_index, INDEX.referencedBy)
                if ref_class_index:
                    fq_name = self.graph.value(ref_class_index, INDEX.fullyQualifiedName)
                    if fq_name:
                        fq_str = str(fq_name)
                        if fq_str not in references:
                            references.append(fq_str)

        # Also check references by class index URI
        for ref_index in self.graph.subjects(INDEX.referencesClass, class_index_uri):
            ref_class_index = self.graph.value(ref_index, INDEX.referencedBy)
            if ref_class_index:
                fq_name = self.graph.value(ref_class_index, INDEX.fullyQualifiedName)
                if fq_name:
                    fq_str = str(fq_name)
                    if fq_str not in references:
                        references.append(fq_str)

        return references

    def search(self, text: str) -> list[dict[str, Any]]:
        """Full-text search across classes, methods, fields, and comments.

        Parameters
        ----------
        text : str
            Search text (case-insensitive)

        Returns
        -------
        list[dict[str, Any]]
            List of matching class information dictionaries

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> results = index.search("memory statistics")
        >>> len(results) > 0
        True
        """
        text_lower = text.lower()
        results: list[dict[str, Any]] = []

        for search_index in self.graph.subjects(RDF.type, INDEX.SearchIndex):
            searchable_text = self.graph.value(search_index, INDEX.searchableText)
            if searchable_text and text_lower in str(searchable_text).lower():
                class_index = self.graph.value(search_index, INDEX.searchableClass)
                if class_index:
                    class_info = self._extract_class_info(class_index)
                    if class_info:
                        results.append(class_info)

        return results

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute a custom SPARQL query against the index.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query

        Returns
        -------
        list[dict[str, Any]]
            Query results as list of binding dictionaries

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> results = index.query("SELECT ?class WHERE { ?idx index:className ?class } LIMIT 5")
        >>> len(results) > 0
        True
        """
        results: list[dict[str, Any]] = []

        query_results = self.graph.query(sparql)
        # Get variable names from the query result
        var_names = [str(var) for var in query_results.vars]

        for row in query_results:
            binding: dict[str, Any] = {}
            for var_name in var_names:
                # Access row by variable name (string)
                try:
                    value = row[var_name]
                    if value is not None:
                        binding[var_name] = str(value)
                except (KeyError, TypeError):
                    # Variable not bound in this row
                    pass
            if binding:  # Only add non-empty bindings
                results.append(binding)

        return results

    def _extract_class_info(self, index_uri: Any) -> dict[str, Any] | None:
        """Extract class information from index URI.

        Parameters
        ----------
        index_uri : Any
            Index URI

        Returns
        -------
        dict[str, Any] | None
            Class information dictionary
        """
        file_path = self.graph.value(index_uri, INDEX.filePath)
        package_name = self.graph.value(index_uri, INDEX.packageName)
        class_name = self.graph.value(index_uri, INDEX.className)
        fq_name = self.graph.value(index_uri, INDEX.fullyQualifiedName)

        if not fq_name:
            return None

        return {
            "class_name": str(class_name) if class_name else "",
            "package_name": str(package_name) if package_name else "",
            "fully_qualified": str(fq_name),
            "file_path": str(file_path) if file_path else "",
        }

    def stats(self) -> dict[str, int]:
        """Get index statistics.

        Returns
        -------
        dict[str, int]
            Statistics about the index

        Examples
        --------
        >>> index = CodebaseIndex("ontology/codebase/index.ttl")
        >>> stats = index.stats()
        >>> stats["classes"] > 0
        True
        """
        class_count = len(list(self.graph.subjects(RDF.type, INDEX.ClassIndex)))
        package_count = len(list(self.graph.subjects(RDF.type, INDEX.PackageIndex)))
        method_count = len(list(self.graph.subjects(RDF.type, INDEX.MethodIndex)))
        field_count = len(list(self.graph.subjects(RDF.type, INDEX.FieldIndex)))

        return {
            "classes": class_count,
            "packages": package_count,
            "methods": method_count,
            "fields": field_count,
            "triples": len(self.graph),
        }
