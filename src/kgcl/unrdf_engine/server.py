"""HTTP server for the UNRDF engine.

Provides REST API for ingestion, querying, and graph management.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from flask import Flask, request
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from rdflib import URIRef

from kgcl.unrdf_engine.engine import UnrdfEngine
from kgcl.unrdf_engine.hooks import HookExecutor, HookRegistry
from kgcl.unrdf_engine.ingestion import IngestionPipeline
from kgcl.unrdf_engine.validation import ShaclValidator

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


def create_app(
    graph_file: Path | None = None,
    shapes_file: Path | None = None,
    enable_hooks: bool = True,
) -> Flask:
    """Create Flask application for UNRDF engine.

    Parameters
    ----------
    graph_file : Path, optional
        Path to RDF graph file for persistence
    shapes_file : Path, optional
        Path to SHACL shapes file for validation
    enable_hooks : bool, default=True
        Whether to enable hook system

    Returns
    -------
    Flask
        Configured Flask application

    """
    app = Flask(__name__)

    # Initialize engine
    engine = UnrdfEngine(file_path=graph_file)

    # Initialize validator
    validator = None
    if shapes_file:
        validator = ShaclValidator()
        validator.load_shapes(shapes_file)

    # Initialize hooks
    hook_executor = None
    if enable_hooks:
        registry = HookRegistry()
        hook_executor = HookExecutor(registry)

    # Initialize pipeline
    pipeline = IngestionPipeline(
        engine=engine, validator=validator, hook_executor=hook_executor
    )

    # Store in app context
    app.config["engine"] = engine
    app.config["pipeline"] = pipeline
    app.config["validator"] = validator
    app.config["hook_executor"] = hook_executor
    app.config["graph_file"] = graph_file

    # Instrument with OpenTelemetry
    FlaskInstrumentor().instrument_app(app)

    @app.route("/health", methods=["GET"])
    def health() -> tuple[dict[str, str], int]:
        """Health check endpoint."""
        return {"status": "healthy"}, 200

    @app.route("/metrics", methods=["GET"])
    def metrics() -> tuple[dict[str, Any], int]:
        """Metrics endpoint."""
        with tracer.start_as_current_span("api.metrics"):
            stats = engine.export_stats()

            # Add hook metrics if available
            if hook_executor:
                history = hook_executor.get_execution_history()
                stats["hooks_executed"] = len(history)
                stats["hooks_successful"] = sum(1 for h in history if h["success"])

            return stats, 200

    @app.route("/ingest", methods=["POST"])
    def ingest() -> tuple[dict[str, Any], int]:
        """Ingest JSON data endpoint.

        Request body:
        {
            "data": {...} or [...],
            "agent": "service_name",
            "reason": "optional reason",
            "base_uri": "optional base URI"
        }
        """
        with tracer.start_as_current_span("api.ingest") as span:
            data = request.get_json()

            if not data or "data" not in data:
                return {"error": "Missing 'data' field in request body"}, 400

            agent = data.get("agent", "api")
            reason = data.get("reason")
            base_uri = data.get("base_uri", "http://unrdf.org/data/")

            span.set_attribute("agent", agent)

            # Ingest data
            result = pipeline.ingest_json(
                data=data["data"], agent=agent, reason=reason, base_uri=base_uri
            )

            # Save graph if file-backed
            if result.success and graph_file:
                engine.save_to_file()

            status_code = 200 if result.success else 400
            return result.to_dict(), status_code

    @app.route("/query", methods=["POST"])
    def query() -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
        """SPARQL query endpoint.

        Request body:
        {
            "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
        }
        """
        with tracer.start_as_current_span("api.query") as span:
            data = request.get_json()

            if not data or "query" not in data:
                return {"error": "Missing 'query' field in request body"}, 400

            sparql_query = data["query"]
            span.set_attribute("query", sparql_query)

            try:
                results = engine.query(sparql_query)

                # Convert results to JSON
                output = []
                for row in results:
                    output.append({str(var): str(row[var]) for var in results.vars})

                return output, 200

            except Exception as e:
                logger.exception("Query failed")
                span.record_exception(e)
                return {"error": f"Query failed: {e}"}, 400

    @app.route("/provenance/<path:subject_uri>", methods=["GET"])
    def get_provenance(subject_uri: str) -> tuple[list[dict[str, Any]], int]:
        """Get provenance for a subject URI."""
        with tracer.start_as_current_span("api.provenance") as span:
            span.set_attribute("subject", subject_uri)

            subject = URIRef(subject_uri)
            provenance_data = []

            for s, p, o in engine.triples(subject=subject):
                prov = engine.get_provenance(s, p, o)
                if prov:
                    provenance_data.append(
                        {
                            "triple": {
                                "subject": str(s),
                                "predicate": str(p),
                                "object": str(o),
                            },
                            "provenance": prov.to_dict(),
                        }
                    )

            return provenance_data, 200

    @app.route("/validate", methods=["POST"])
    def validate() -> tuple[dict[str, Any], int]:
        """Validate data endpoint.

        Request body:
        {
            "data": {...} or [...],
            "base_uri": "optional base URI"
        }
        """
        with tracer.start_as_current_span("api.validate") as span:
            if not validator:
                return {"error": "Validator not configured"}, 400

            data = request.get_json()

            if not data or "data" not in data:
                return {"error": "Missing 'data' field in request body"}, 400

            # Convert JSON to RDF (reuse pipeline logic)
            from rdflib import Graph

            temp_graph = Graph()
            temp_graph.bind("unrdf", "http://unrdf.org/ontology/")

            # Use pipeline's JSON-to-RDF conversion
            base_uri = data.get("base_uri", "http://unrdf.org/data/")
            items = data["data"] if isinstance(data["data"], list) else [data["data"]]

            for item in items:
                pipeline._json_to_rdf(item, temp_graph, base_uri)

            # Validate
            result = validator.validate(temp_graph)

            return result.to_dict(), 200

    @app.route("/hooks", methods=["GET"])
    def list_hooks() -> tuple[dict[str, Any], int]:
        """List registered hooks."""
        with tracer.start_as_current_span("api.hooks.list"):
            if not hook_executor:
                return {"error": "Hooks not enabled"}, 400

            hooks = hook_executor.registry.list_all()
            hooks_data = [
                {
                    "name": h.name,
                    "phases": [p.value for p in h.phases],
                    "priority": h.priority,
                    "enabled": h.enabled,
                }
                for h in hooks
            ]

            return {"hooks": hooks_data}, 200

    @app.route("/hooks/history", methods=["GET"])
    def hook_history() -> tuple[dict[str, Any], int]:
        """Get hook execution history."""
        with tracer.start_as_current_span("api.hooks.history"):
            if not hook_executor:
                return {"error": "Hooks not enabled"}, 400

            history = hook_executor.get_execution_history()
            return {"history": history}, 200

    @app.errorhandler(Exception)
    def handle_error(error: Exception) -> tuple[dict[str, str], int]:
        """Global error handler."""
        logger.exception("Unhandled error")
        span = trace.get_current_span()
        span.record_exception(error)
        return {"error": str(error)}, 500

    return app


def main(
    host: str = "0.0.0.0",
    port: int = 8000,
    graph_file: Path | None = None,
    shapes_file: Path | None = None,
) -> None:
    """Run the UNRDF HTTP server.

    Parameters
    ----------
    host : str, default="0.0.0.0"
        Host to bind to
    port : int, default=8000
        Port to bind to
    graph_file : Path, optional
        Path to RDF graph file
    shapes_file : Path, optional
        Path to SHACL shapes file

    """
    app = create_app(graph_file=graph_file, shapes_file=shapes_file)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    import sys

    # Parse command line args
    graph_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    shapes_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    main(graph_file=graph_file, shapes_file=shapes_file)
