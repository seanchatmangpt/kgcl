"""RDF Store container definitions for testcontainers.

Provides OxigraphContainer and FusekiContainer classes for SPARQL endpoint testing.
These containers implement shared RDF stores for multi-engine coordination tests.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

if TYPE_CHECKING:
    from typing import Self


class OxigraphContainer(DockerContainer):
    """Oxigraph Server container for SPARQL endpoint testing.

    Provides a full SPARQL 1.1 endpoint with:
    - Query endpoint: /query (GET/POST)
    - Update endpoint: /update (POST)
    - Store endpoint: /store (GET/POST/DELETE)

    Examples
    --------
    >>> with OxigraphContainer() as oxigraph:
    ...     endpoint = oxigraph.get_sparql_endpoint()
    ...     # Use endpoint for SPARQL queries
    """

    OXIGRAPH_PORT = 7878
    IMAGE = "ghcr.io/oxigraph/oxigraph:latest"

    def __init__(self, image: str = IMAGE) -> None:
        """Initialize Oxigraph container.

        Parameters
        ----------
        image : str
            Docker image to use. Defaults to latest Oxigraph.
        """
        super().__init__(image)
        self.with_exposed_ports(self.OXIGRAPH_PORT)
        self.with_command("serve --location /data --bind 0.0.0.0:7878")

    def get_container_host_ip(self) -> str:
        """Get container host IP address."""
        return self.get_container_host_ip()

    def get_sparql_endpoint(self) -> str:
        """Get SPARQL query endpoint URL.

        Returns
        -------
        str
            Full URL to the SPARQL query endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.OXIGRAPH_PORT)
        return f"http://{host}:{port}/query"

    def get_update_endpoint(self) -> str:
        """Get SPARQL update endpoint URL.

        Returns
        -------
        str
            Full URL to the SPARQL update endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.OXIGRAPH_PORT)
        return f"http://{host}:{port}/update"

    def get_store_endpoint(self) -> str:
        """Get RDF store endpoint URL (for direct graph operations).

        Returns
        -------
        str
            Full URL to the store endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.OXIGRAPH_PORT)
        return f"http://{host}:{port}/store"

    def start(self) -> Self:
        """Start container and wait for readiness.

        Returns
        -------
        Self
            The started container instance.
        """
        super().start()
        self._wait_for_ready()
        return self

    def _wait_for_ready(self, timeout: float = 30.0) -> None:
        """Wait for Oxigraph to be ready to accept connections.

        Parameters
        ----------
        timeout : float
            Maximum seconds to wait for readiness.

        Raises
        ------
        TimeoutError
            If container doesn't become ready within timeout.
        """
        start_time = time.time()
        endpoint = self.get_sparql_endpoint()

        while time.time() - start_time < timeout:
            try:
                response = httpx.get(
                    endpoint,
                    params={"query": "ASK { ?s ?p ?o }"},
                    timeout=2.0,
                )
                if response.status_code in (200, 204):
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)

        msg = f"Oxigraph container not ready after {timeout}s"
        raise TimeoutError(msg)


class FusekiContainer(DockerContainer):
    """Apache Jena Fuseki container for SPARQL 1.1 compliance testing.

    Provides a full SPARQL 1.1 endpoint with:
    - Query endpoint: /{dataset}/query
    - Update endpoint: /{dataset}/update
    - Data endpoint: /{dataset}/data
    - Management UI at /

    Examples
    --------
    >>> with FusekiContainer(dataset_name="kgcl") as fuseki:
    ...     endpoint = fuseki.get_sparql_endpoint()
    ...     # Use endpoint for SPARQL queries
    """

    FUSEKI_PORT = 3030
    IMAGE = "stain/jena-fuseki:4.9.0"

    def __init__(self, dataset_name: str = "kgcl", image: str = IMAGE) -> None:
        """Initialize Fuseki container.

        Parameters
        ----------
        dataset_name : str
            Name of the dataset to create. Defaults to "kgcl".
        image : str
            Docker image to use. Defaults to Fuseki 4.9.0.
        """
        super().__init__(image)
        self.dataset_name = dataset_name
        self.with_exposed_ports(self.FUSEKI_PORT)
        self.with_env("FUSEKI_DATASET_1", dataset_name)
        self.with_env("ADMIN_PASSWORD", "admin")

    def get_sparql_endpoint(self) -> str:
        """Get SPARQL query endpoint URL.

        Returns
        -------
        str
            Full URL to the SPARQL query endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.FUSEKI_PORT)
        return f"http://{host}:{port}/{self.dataset_name}/query"

    def get_update_endpoint(self) -> str:
        """Get SPARQL update endpoint URL.

        Returns
        -------
        str
            Full URL to the SPARQL update endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.FUSEKI_PORT)
        return f"http://{host}:{port}/{self.dataset_name}/update"

    def get_data_endpoint(self) -> str:
        """Get RDF data endpoint URL (for Graph Store Protocol).

        Returns
        -------
        str
            Full URL to the data endpoint.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.FUSEKI_PORT)
        return f"http://{host}:{port}/{self.dataset_name}/data"

    def start(self) -> Self:
        """Start container and wait for readiness.

        Returns
        -------
        Self
            The started container instance.
        """
        super().start()
        wait_for_logs(self, "Started", timeout=60)
        self._wait_for_ready()
        return self

    def _wait_for_ready(self, timeout: float = 30.0) -> None:
        """Wait for Fuseki to be ready to accept connections.

        Parameters
        ----------
        timeout : float
            Maximum seconds to wait for readiness.

        Raises
        ------
        TimeoutError
            If container doesn't become ready within timeout.
        """
        start_time = time.time()
        endpoint = self.get_sparql_endpoint()

        while time.time() - start_time < timeout:
            try:
                response = httpx.post(
                    endpoint,
                    data={"query": "ASK { ?s ?p ?o }"},
                    timeout=2.0,
                )
                if response.status_code in (200, 204):
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)

        msg = f"Fuseki container not ready after {timeout}s"
        raise TimeoutError(msg)
