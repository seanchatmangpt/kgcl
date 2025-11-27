"""RemoteStoreAdapter - RDFStore implementation for remote SPARQL endpoints.

This adapter allows the hybrid engine to work with remote RDF stores
(Oxigraph Server, Fuseki, Virtuoso, etc.) via SPARQL 1.1 Protocol.

Examples
--------
>>> adapter = RemoteStoreAdapter(
...     query_endpoint="http://localhost:7878/query", update_endpoint="http://localhost:7878/update"
... )
>>> adapter.triple_count()  # doctest: +SKIP
0
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RemoteStoreAdapter:
    """Adapter implementing RDFStore protocol for remote SPARQL endpoints.

    This adapter provides the RDFStore interface for remote SPARQL 1.1
    endpoints, enabling multi-engine coordination through shared state.

    Parameters
    ----------
    query_endpoint : str
        URL for SPARQL query operations (SELECT, ASK, CONSTRUCT).
    update_endpoint : str
        URL for SPARQL update operations (INSERT, DELETE).
    store_endpoint : str | None, optional
        URL for Graph Store Protocol operations. If None, uses update_endpoint.
    timeout : float, optional
        Request timeout in seconds. Defaults to 30.0.

    Attributes
    ----------
    query_endpoint : str
        SPARQL query endpoint URL.
    update_endpoint : str
        SPARQL update endpoint URL.

    Examples
    --------
    Create adapter for Oxigraph Server:

    >>> adapter = RemoteStoreAdapter(
    ...     query_endpoint="http://localhost:7878/query", update_endpoint="http://localhost:7878/update"
    ... )

    Create adapter for Fuseki:

    >>> adapter = RemoteStoreAdapter(
    ...     query_endpoint="http://localhost:3030/dataset/query", update_endpoint="http://localhost:3030/dataset/update"
    ... )
    """

    def __init__(
        self, query_endpoint: str, update_endpoint: str, store_endpoint: str | None = None, timeout: float = 30.0
    ) -> None:
        """Initialize RemoteStoreAdapter.

        Parameters
        ----------
        query_endpoint : str
            URL for SPARQL query operations.
        update_endpoint : str
            URL for SPARQL update operations.
        store_endpoint : str | None, optional
            URL for Graph Store Protocol. If None, derived from endpoints.
        timeout : float, optional
            Request timeout in seconds. Defaults to 30.0.
        """
        self.query_endpoint = query_endpoint
        self.update_endpoint = update_endpoint
        self.store_endpoint = store_endpoint
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        logger.info(f"RemoteStoreAdapter initialized: query={query_endpoint}")

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        if hasattr(self, "_client"):
            self._client.close()

    def load_turtle(self, data: str) -> int:
        """Load Turtle (TTL) format RDF data via SPARQL INSERT DATA.

        Parameters
        ----------
        data : str
            Turtle format RDF data.

        Returns
        -------
        int
            Estimated number of triples loaded (based on data size).

        Raises
        ------
        RuntimeError
            If the SPARQL update fails.

        Examples
        --------
        >>> adapter = RemoteStoreAdapter(...)  # doctest: +SKIP
        >>> adapter.load_turtle('''
        ...     @prefix ex: <http://example.org/> .
        ...     ex:task1 ex:status "Active" .
        ... ''')  # doctest: +SKIP
        1
        """
        # Convert Turtle to SPARQL INSERT DATA
        # First, try direct POST to store endpoint if available
        if self.store_endpoint:
            try:
                response = self._client.post(
                    self.store_endpoint, content=data.encode("utf-8"), headers={"Content-Type": "text/turtle"}
                )
                if response.status_code in (200, 201, 204):
                    # Estimate triples from data (rough heuristic)
                    return data.count(";") + data.count(".") - data.count("@prefix")
            except httpx.RequestError:
                pass  # Fall through to SPARQL INSERT

        # Fall back to SPARQL INSERT DATA
        # Parse Turtle to extract triples and convert to INSERT DATA
        sparql = self._turtle_to_insert_data(data)
        if not sparql:
            return 0

        try:
            response = self._client.post(
                self.update_endpoint,
                data={"update": sparql},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            # Estimate triples from data
            return data.count(";") + data.count(".") - data.count("@prefix")
        except httpx.HTTPStatusError as e:
            msg = f"SPARQL INSERT failed: {e.response.status_code} - {e.response.text}"
            raise RuntimeError(msg) from e

    def _turtle_to_insert_data(self, turtle: str) -> str:
        """Convert Turtle data to SPARQL INSERT DATA statement.

        Parameters
        ----------
        turtle : str
            Turtle format RDF data.

        Returns
        -------
        str
            SPARQL INSERT DATA statement.
        """
        # Extract prefixes
        prefixes = []
        triples = []
        lines = turtle.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("@prefix") or line.startswith("PREFIX"):
                # Convert Turtle @prefix to SPARQL PREFIX
                if line.startswith("@prefix"):
                    # @prefix ex: <http://...> . -> PREFIX ex: <http://...>
                    prefix_line = line.replace("@prefix", "PREFIX").rstrip(" .")
                else:
                    prefix_line = line
                prefixes.append(prefix_line)
            elif line and not line.startswith("#"):
                triples.append(line)

        if not triples:
            return ""

        prefix_block = "\n".join(prefixes)
        triples_block = "\n".join(triples)

        # Ensure triples end with proper termination
        if not triples_block.rstrip().endswith("."):
            triples_block = triples_block.rstrip() + " ."

        return f"{prefix_block}\nINSERT DATA {{\n{triples_block}\n}}"

    def load_n3(self, data: str) -> int:
        """Load N3 format RDF data.

        N3 is a superset of Turtle, so we attempt to load it the same way.
        Note: Full N3 semantics (rules, implications) are not supported.

        Parameters
        ----------
        data : str
            N3 format RDF data.

        Returns
        -------
        int
            Number of triples loaded.
        """
        # N3 is a superset of Turtle, try loading as Turtle
        return self.load_turtle(data)

    def dump(self) -> str:
        """Dump entire store as serialized RDF (Turtle format).

        Returns
        -------
        str
            All triples serialized in Turtle format.

        Raises
        ------
        RuntimeError
            If the CONSTRUCT query fails.

        Examples
        --------
        >>> adapter = RemoteStoreAdapter(...)  # doctest: +SKIP
        >>> output = adapter.dump()  # doctest: +SKIP
        >>> isinstance(output, str)  # doctest: +SKIP
        True
        """
        # Use CONSTRUCT to get all triples
        sparql = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"

        try:
            response = self._client.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/turtle"},
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            msg = f"SPARQL CONSTRUCT failed: {e.response.status_code}"
            raise RuntimeError(msg) from e

    def triple_count(self) -> int:
        """Count total triples in store.

        Returns
        -------
        int
            Number of triples.

        Examples
        --------
        >>> adapter = RemoteStoreAdapter(...)  # doctest: +SKIP
        >>> adapter.triple_count()  # doctest: +SKIP
        0
        """
        sparql = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"

        try:
            response = self._client.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/sparql-results+json",
                },
            )
            response.raise_for_status()
            result = response.json()
            bindings = result.get("results", {}).get("bindings", [])
            if bindings:
                count_value = bindings[0].get("count", {}).get("value", "0")
                return int(count_value)
            return 0
        except (httpx.HTTPStatusError, KeyError, ValueError):
            return 0

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query.

        Returns
        -------
        list[dict[str, Any]]
            List of variable bindings from query results.

        Raises
        ------
        RuntimeError
            If the query fails.

        Examples
        --------
        >>> adapter = RemoteStoreAdapter(...)  # doctest: +SKIP
        >>> results = adapter.query("SELECT * WHERE { ?s ?p ?o } LIMIT 10")  # doctest: +SKIP
        >>> isinstance(results, list)  # doctest: +SKIP
        True
        """
        try:
            response = self._client.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/sparql-results+json",
                },
            )
            response.raise_for_status()
            result = response.json()
            return self._parse_sparql_results(result)
        except httpx.HTTPStatusError as e:
            msg = f"SPARQL query failed: {e.response.status_code} - {e.response.text}"
            raise RuntimeError(msg) from e

    def _parse_sparql_results(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse SPARQL JSON results into list of dicts.

        Parameters
        ----------
        result : dict[str, Any]
            SPARQL JSON result format.

        Returns
        -------
        list[dict[str, Any]]
            List of variable bindings.
        """
        bindings = result.get("results", {}).get("bindings", [])
        parsed = []

        for binding in bindings:
            row = {}
            for var, value_obj in binding.items():
                value_type = value_obj.get("type")
                value = value_obj.get("value")

                if value_type == "uri":
                    row[var] = value  # Keep as string URI
                elif value_type == "literal":
                    # Check for datatype
                    datatype = value_obj.get("datatype")
                    if datatype == "http://www.w3.org/2001/XMLSchema#integer":
                        row[var] = int(value)
                    elif datatype == "http://www.w3.org/2001/XMLSchema#decimal":
                        row[var] = float(value)
                    elif datatype == "http://www.w3.org/2001/XMLSchema#boolean":
                        row[var] = value.lower() == "true"
                    else:
                        row[var] = value
                elif value_type == "bnode":
                    row[var] = f"_:{value}"
                else:
                    row[var] = value

            parsed.append(row)

        return parsed

    def ask(self, sparql: str) -> bool:
        """Execute SPARQL ASK query.

        Parameters
        ----------
        sparql : str
            SPARQL ASK query.

        Returns
        -------
        bool
            True if the pattern matches, False otherwise.
        """
        try:
            response = self._client.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/sparql-results+json",
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("boolean", False)
        except (httpx.HTTPStatusError, KeyError):
            return False

    def clear(self) -> None:
        """Clear all triples from store.

        Uses SPARQL DROP ALL or DELETE WHERE { ?s ?p ?o } depending on endpoint support.

        Examples
        --------
        >>> adapter = RemoteStoreAdapter(...)  # doctest: +SKIP
        >>> adapter.clear()  # doctest: +SKIP
        """
        # Try DROP ALL first (faster)
        try:
            response = self._client.post(
                self.update_endpoint,
                data={"update": "DROP ALL"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code in (200, 204):
                return
        except httpx.HTTPStatusError:
            pass

        # Fall back to DELETE WHERE
        try:
            response = self._client.post(
                self.update_endpoint,
                data={"update": "DELETE WHERE { ?s ?p ?o }"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to clear store: {e}")

    def update(self, sparql: str) -> None:
        """Execute SPARQL UPDATE operation.

        Parameters
        ----------
        sparql : str
            SPARQL UPDATE statement (INSERT, DELETE, etc.).

        Raises
        ------
        RuntimeError
            If the update fails.
        """
        try:
            response = self._client.post(
                self.update_endpoint,
                data={"update": sparql},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"SPARQL update failed: {e.response.status_code} - {e.response.text}"
            raise RuntimeError(msg) from e
