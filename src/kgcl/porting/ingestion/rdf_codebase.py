"""RDF codebase wrapper for PyOxigraph storage.

Provides codebase-specific queries and operations on RDF-encoded code.
Uses OxigraphAdapter pattern from hybrid engine.
"""

from pathlib import Path
from typing import Any

from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter
from kgcl.porting.ingestion.java_ingester import JavaIngester
from kgcl.porting.ingestion.python_ingester import PythonIngester


class RDFCodebase:
    """RDF codebase store with codebase-specific queries.

    Wraps OxigraphAdapter to provide codebase-specific operations
    for storing and querying code structures as RDF.

    Parameters
    ----------
    store_path : Path | None, optional
        Path for persistent storage. If None, uses in-memory store.

    Attributes
    ----------
    adapter : OxigraphAdapter
        Oxigraph adapter for RDF operations.
    store : ox.Store
        PyOxigraph triple store (via adapter.raw_store).
    """

    def __init__(self, store_path: Path | None = None) -> None:
        """Initialize RDF codebase store.

        Parameters
        ----------
        store_path : Path | None, optional
            Path for persistent storage. If None, uses in-memory store.
        """
        self.adapter = OxigraphAdapter(str(store_path) if store_path else None)
        self.store = self.adapter.raw_store

    def ingest_java_codebase(self, java_root: Path) -> int:
        """Ingest Java codebase into RDF store.

        Parameters
        ----------
        java_root : Path
            Root directory of Java source code

        Returns
        -------
        int
            Number of classes ingested
        """
        ingester = JavaIngester()
        count = 0

        for java_file in java_root.rglob("*.java"):
            try:
                classes = ingester.parse_file(java_file)
                for class_info in classes:
                    self._store_java_class(class_info)
                    count += 1
            except Exception as e:
                print(f"Warning: Could not ingest {java_file}: {e}")

        return count

    def ingest_python_codebase(self, python_root: Path) -> int:
        """Ingest Python codebase into RDF store.

        Parameters
        ----------
        python_root : Path
            Root directory of Python source code

        Returns
        -------
        int
            Number of classes ingested
        """
        ingester = PythonIngester()
        ingester.analyze_codebase(python_root)

        count = 0
        for class_info in ingester.classes.values():
            self._store_python_class(class_info)
            count += 1

        return count

    def _store_java_class(self, class_info: Any) -> None:
        """Store Java class as RDF triples.

        Parameters
        ----------
        class_info : Any
            Enhanced Java class info
        """
        from rdflib import Literal, Namespace, URIRef

        CODE = Namespace("http://kgcl.dev/ontology/codebase#")

        class_uri = URIRef(f"http://kgcl.dev/codebase/java/{class_info.package}/{class_info.name}")

        # Class type
        self.store.add((class_uri, CODE["a"], CODE["Class"]))

        # Class properties
        self.store.add((class_uri, CODE["name"], Literal(class_info.name)))
        self.store.add((class_uri, CODE["filePath"], Literal(class_info.file_path)))

        # Package
        if class_info.package:
            pkg_uri = URIRef(f"http://kgcl.dev/codebase/java/package/{class_info.package}")
            self.store.add((pkg_uri, CODE["a"], CODE["Package"]))
            self.store.add((pkg_uri, CODE["name"], Literal(class_info.package)))
            self.store.add((class_uri, CODE["inPackage"], pkg_uri))

        # Inheritance
        if class_info.extends:
            extends_uri = URIRef(f"http://kgcl.dev/codebase/java/{class_info.extends}")
            self.store.add((class_uri, CODE["extends"], extends_uri))

        # Methods
        for method in class_info.methods:
            method_uri = URIRef(f"{class_uri}/method/{method.name}")
            self.store.add((method_uri, CODE["a"], CODE["Method"]))
            self.store.add((method_uri, CODE["name"], Literal(method.name)))
            self.store.add((method_uri, CODE["returnType"], Literal(method.return_type)))
            self.store.add((method_uri, CODE["signature"], Literal(method.signature)))
            self.store.add((method_uri, CODE["bodyText"], Literal(method.body_text)))
            self.store.add((method_uri, CODE["complexity"], Literal(method.complexity)))
            self.store.add((method_uri, CODE["hasLoops"], Literal(method.has_loops)))
            self.store.add((method_uri, CODE["hasRecursion"], Literal(method.has_recursion)))
            self.store.add((class_uri, CODE["hasMethod"], method_uri))

            # Call sites
            for call_site in method.call_sites:
                call_uri = URIRef(f"{method_uri}/call/{call_site.line_number}")
                self.store.add((call_uri, CODE["a"], CODE["CallSite"]))
                self.store.add((call_uri, CODE["calleeName"], Literal(call_site.callee_name)))
                if call_site.callee_class:
                    self.store.add((call_uri, CODE["calleeClass"], Literal(call_site.callee_class)))
                self.store.add((call_uri, CODE["lineNumber"], Literal(call_site.line_number)))
                self.store.add((method_uri, CODE["hasCallSite"], call_uri))

            # Exceptions
            for exc in method.exceptions:
                exc_uri = URIRef(f"{method_uri}/exception/{exc.exception_type}")
                self.store.add((exc_uri, CODE["a"], CODE["ExceptionPattern"]))
                self.store.add((exc_uri, CODE["exceptionType"], Literal(exc.exception_type)))
                self.store.add((exc_uri, CODE["isThrown"], Literal(exc.is_thrown)))
                self.store.add((exc_uri, CODE["isCaught"], Literal(exc.is_caught)))
                self.store.add((method_uri, CODE["hasException"], exc_uri))

    def _store_python_class(self, class_info: Any) -> None:
        """Store Python class as RDF triples.

        Parameters
        ----------
        class_info : Any
            Enhanced Python class info
        """
        from rdflib import Literal, Namespace, URIRef

        CODE = Namespace("http://kgcl.dev/ontology/codebase#")

        class_uri = URIRef(f"http://kgcl.dev/codebase/python/{class_info.name}")

        # Class type
        self.store.add((class_uri, CODE["a"], CODE["Class"]))

        # Class properties
        self.store.add((class_uri, CODE["name"], Literal(class_info.name)))
        self.store.add((class_uri, CODE["filePath"], Literal(class_info.file_path)))

        # Methods
        for method in class_info.methods:
            method_uri = URIRef(f"{class_uri}/method/{method.name}")
            self.store.add((method_uri, CODE["a"], CODE["Method"]))
            self.store.add((method_uri, CODE["name"], Literal(method.name)))
            if method.return_type:
                self.store.add((method_uri, CODE["returnType"], Literal(method.return_type)))
            self.store.add((method_uri, CODE["bodyText"], Literal(method.body_text)))
            self.store.add((method_uri, CODE["complexity"], Literal(method.complexity)))
            self.store.add((method_uri, CODE["hasLoops"], Literal(method.has_loops)))
            self.store.add((method_uri, CODE["hasRecursion"], Literal(method.has_recursion)))
            self.store.add((class_uri, CODE["hasMethod"], method_uri))

            # Call sites
            for call_site in method.call_sites:
                call_uri = URIRef(f"{method_uri}/call/{call_site.line_number}")
                self.store.add((call_uri, CODE["a"], CODE["CallSite"]))
                self.store.add((call_uri, CODE["calleeName"], Literal(call_site.callee_name)))
                if call_site.callee_attr:
                    self.store.add((call_uri, CODE["calleeClass"], Literal(call_site.callee_attr)))
                self.store.add((call_uri, CODE["lineNumber"], Literal(call_site.line_number)))
                self.store.add((method_uri, CODE["hasCallSite"], call_uri))

            # Exceptions
            for exc in method.exceptions:
                exc_uri = URIRef(f"{method_uri}/exception/{exc.exception_type}")
                self.store.add((exc_uri, CODE["a"], CODE["ExceptionPattern"]))
                self.store.add((exc_uri, CODE["exceptionType"], Literal(exc.exception_type)))
                self.store.add((exc_uri, CODE["isThrown"], Literal(exc.is_raised)))
                self.store.add((exc_uri, CODE["isCaught"], Literal(exc.is_caught)))
                self.store.add((method_uri, CODE["hasException"], exc_uri))

    def query_classes(self, language: str | None = None) -> list[dict[str, str]]:
        """Query classes in the codebase.

        Parameters
        ----------
        language : str | None, optional
            Filter by language (java, python). If None, returns all.

        Returns
        -------
        list[dict[str, str]]
            List of class information dictionaries
        """
        CODE = "http://kgcl.dev/ontology/codebase#"

        query = f"""
        PREFIX code: <{CODE}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?class ?name ?filePath
        WHERE {{
            ?class a code:Class .
            ?class code:name ?name .
            ?class code:filePath ?filePath .
        }}
        ORDER BY ?name
        """

        results = list(self.store.query(query))
        classes = []
        for solution in results:
            class_uri = str(solution["class"])
            if language:
                if f"/{language}/" not in class_uri:
                    continue
            classes.append(
                {
                    "uri": class_uri,
                    "name": str(solution["name"]),
                    "filePath": str(solution["filePath"]),
                }
            )
        return classes

    def query_methods(self, class_name: str | None = None) -> list[dict[str, str]]:
        """Query methods in the codebase.

        Parameters
        ----------
        class_name : str | None, optional
            Filter by class name. If None, returns all.

        Returns
        -------
        list[dict[str, str]]
            List of method information dictionaries
        """
        CODE = "http://kgcl.dev/ontology/codebase#"

        query = f"""
        PREFIX code: <{CODE}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?method ?name ?returnType ?signature ?class
        WHERE {{
            ?class code:hasMethod ?method .
            ?method code:name ?name .
            ?method code:returnType ?returnType .
            ?method code:signature ?signature .
        }}
        ORDER BY ?name
        """

        results = list(self.store.query(query))
        methods = []
        for solution in results:
            if class_name and class_name not in str(solution["class"]):
                continue
            methods.append(
                {
                    "uri": str(solution["method"]),
                    "name": str(solution["name"]),
                    "returnType": str(solution["returnType"]),
                    "signature": str(solution["signature"]),
                    "class": str(solution["class"]),
                }
            )
        return methods

    def _export_state(self) -> str:
        """Export current PyOxigraph state as Turtle.

        Returns
        -------
        str
            State as Turtle string
        """
        # Use adapter's dump method for consistent serialization
        return self.adapter.dump()

