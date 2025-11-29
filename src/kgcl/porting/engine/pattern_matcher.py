"""Pattern matcher using SPARQL queries.

Provides SPARQL-based pattern matching for porting patterns
without requiring EYE reasoner.
"""

from kgcl.porting.ingestion.rdf_codebase import RDFCodebase


class PatternMatcher:
    """Match porting patterns using SPARQL queries.

    Provides pattern matching capabilities using SPARQL
    for cases where EYE reasoner is not needed or available.

    Parameters
    ----------
    codebase : RDFCodebase
        RDF codebase store
    """

    def __init__(self, codebase: RDFCodebase) -> None:
        """Initialize pattern matcher.

        Parameters
        ----------
        codebase : RDFCodebase
            RDF codebase store
        """
        self.codebase = codebase

    def find_missing_classes(self) -> list[dict[str, str]]:
        """Find Java classes without Python ports.

        Returns
        -------
        list[dict[str, str]]
            List of missing class information
        """
        query = """
        PREFIX code: <http://kgcl.dev/ontology/codebase#>
        PREFIX port: <http://kgcl.dev/ontology/porting#>

        SELECT ?javaClass ?name
        WHERE {
            ?javaClass a code:Class ;
                code:name ?name .
            
            FILTER(STRSTARTS(STR(?javaClass), "http://kgcl.dev/codebase/java/"))
            
            NOT EXISTS {
                ?javaClass port:hasPort ?pythonClass .
            }
        }
        ORDER BY ?name
        """

        results = list(self.codebase.store.query(query))
        missing = []
        for solution in results:
            missing.append(
                {
                    "uri": str(solution["javaClass"]),
                    "name": str(solution["name"]),
                }
            )
        return missing

    def find_missing_methods(self, class_name: str | None = None) -> list[dict[str, str]]:
        """Find Java methods without Python ports.

        Parameters
        ----------
        class_name : str | None, optional
            Filter by class name. If None, returns all.

        Returns
        -------
        list[dict[str, str]]
            List of missing method information
        """
        query = """
        PREFIX code: <http://kgcl.dev/ontology/codebase#>
        PREFIX port: <http://kgcl.dev/ontology/porting#>

        SELECT ?javaMethod ?methodName ?javaClass ?className
        WHERE {
            ?javaClass code:hasMethod ?javaMethod .
            ?javaMethod code:name ?methodName .
            ?javaClass code:name ?className .
            
            FILTER(STRSTARTS(STR(?javaClass), "http://kgcl.dev/codebase/java/"))
            
            NOT EXISTS {
                ?javaMethod port:hasPort ?pythonMethod .
            }
        }
        ORDER BY ?className ?methodName
        """

        results = list(self.codebase.store.query(query))
        missing = []
        for solution in results:
            if class_name and class_name not in str(solution["className"]):
                continue
            missing.append(
                {
                    "uri": str(solution["javaMethod"]),
                    "methodName": str(solution["methodName"]),
                    "classUri": str(solution["javaClass"]),
                    "className": str(solution["className"]),
                }
            )
        return missing

    def find_signature_mismatches(self) -> list[dict[str, str]]:
        """Find methods with signature mismatches.

        Returns
        -------
        list[dict[str, str]]
            List of signature mismatch information
        """
        query = """
        PREFIX code: <http://kgcl.dev/ontology/codebase#>
        PREFIX port: <http://kgcl.dev/ontology/porting#>

        SELECT ?javaMethod ?javaSignature ?pythonMethod ?pythonSignature
        WHERE {
            ?javaMethod port:hasPort ?pythonMethod .
            ?javaMethod code:signature ?javaSignature .
            ?pythonMethod code:signature ?pythonSignature .
            
            FILTER(?javaSignature != ?pythonSignature)
        }
        """

        results = list(self.codebase.store.query(query))
        mismatches = []
        for solution in results:
            mismatches.append(
                {
                    "javaMethod": str(solution["javaMethod"]),
                    "javaSignature": str(solution["javaSignature"]),
                    "pythonMethod": str(solution["pythonMethod"]),
                    "pythonSignature": str(solution["pythonSignature"]),
                }
            )
        return mismatches

    def find_semantic_deltas(self, min_similarity: float = 0.7) -> list[dict[str, Any]]:
        """Find methods with semantic differences.

        Parameters
        ----------
        min_similarity : float, optional
            Minimum similarity threshold. Default is 0.7.

        Returns
        -------
        list[dict[str, Any]]
            List of semantic delta information
        """
        query = """
        PREFIX code: <http://kgcl.dev/ontology/codebase#>
        PREFIX port: <http://kgcl.dev/ontology/porting#>

        SELECT ?javaMethod ?pythonMethod ?javaFp ?pythonFp
        WHERE {
            ?javaMethod port:hasPort ?pythonMethod .
            ?javaMethod code:hasFingerprint ?javaFp .
            ?pythonMethod code:hasFingerprint ?pythonFp .
            
            ?javaMethod port:semanticDivergence true .
        }
        """

        results = list(self.codebase.store.query(query))
        deltas = []
        for solution in results:
            deltas.append(
                {
                    "javaMethod": str(solution["javaMethod"]),
                    "pythonMethod": str(solution["pythonMethod"]),
                    "javaFingerprint": str(solution["javaFp"]),
                    "pythonFingerprint": str(solution["pythonFp"]),
                }
            )
        return deltas

