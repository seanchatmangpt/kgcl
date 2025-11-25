"""Ingestion pipeline for the UNRDF engine.

Converts JSON events/features to RDF, applies feature templates, and executes hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opentelemetry import trace
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from kgcl.unrdf_engine.engine import Transaction, UnrdfEngine
from kgcl.unrdf_engine.hooks import HookContext, HookExecutor, HookPhase
from kgcl.unrdf_engine.validation import ShaclValidator

tracer = trace.get_tracer(__name__)

UNRDF = Namespace("http://unrdf.org/ontology/")


@dataclass
class IngestionResult:
    """Result of an ingestion operation.

    Parameters
    ----------
    success : bool
        Whether ingestion succeeded
    triples_added : int
        Number of triples added
    transaction_id : str
        Transaction identifier
    validation_result : dict[str, Any] | None
        SHACL validation result if validation was performed
    hook_results : list[dict[str, Any]]
        Results from hook executions
    error : str | None
        Error message if ingestion failed

    """

    success: bool
    triples_added: int
    transaction_id: str
    validation_result: dict[str, Any] | None = None
    hook_results: list[dict[str, Any]] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Result as dictionary

        """
        return {
            "success": self.success,
            "triples_added": self.triples_added,
            "transaction_id": self.transaction_id,
            "validation_result": self.validation_result,
            "hook_results": self.hook_results,
            "error": self.error,
        }


class IngestionPipeline:
    """Pipeline for ingesting JSON data into RDF with validation and hooks.

    Handles:
    - JSON to RDF conversion
    - Batch processing with transactions
    - SHACL validation
    - Hook execution at lifecycle phases
    - Feature template materialization

    Examples
    --------
    >>> engine = UnrdfEngine()
    >>> validator = ShaclValidator()
    >>> hook_executor = HookExecutor(hook_registry)
    >>> pipeline = IngestionPipeline(engine, validator, hook_executor)
    >>>
    >>> result = pipeline.ingest_json(
    ...     data={"type": "Event", "name": "user_login", "userId": "123"},
    ...     agent="ingestion_service"
    ... )

    """

    def __init__(
        self,
        engine: UnrdfEngine,
        validator: ShaclValidator | None = None,
        hook_executor: HookExecutor | None = None,
        validate_on_ingest: bool = True,
    ) -> None:
        """Initialize ingestion pipeline.

        Parameters
        ----------
        engine : UnrdfEngine
            RDF engine to ingest into
        validator : ShaclValidator, optional
            SHACL validator for data validation
        hook_executor : HookExecutor, optional
            Hook executor for lifecycle hooks
        validate_on_ingest : bool, default=True
            Whether to validate data before committing

        """
        self.engine = engine
        self.validator = validator
        self.hook_executor = hook_executor
        self.validate_on_ingest = validate_on_ingest

    @tracer.start_as_current_span("ingestion.ingest_json")
    def ingest_json(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        agent: str,
        reason: str | None = None,
        base_uri: str = "http://unrdf.org/data/",
    ) -> IngestionResult:
        """Ingest JSON data as RDF.

        Parameters
        ----------
        data : dict[str, Any] | list[dict[str, Any]]
            JSON data to ingest (single object or array)
        agent : str
            Agent performing ingestion
        reason : str, optional
            Reason for ingestion
        base_uri : str, default="http://unrdf.org/data/"
            Base URI for generated entities

        Returns
        -------
        IngestionResult
            Ingestion result with status and metrics

        """
        span = trace.get_current_span()

        # Normalize to list
        items = data if isinstance(data, list) else [data]
        span.set_attribute("items.count", len(items))

        # Create transaction
        txn = self.engine.transaction(agent=agent, reason=reason)
        span.set_attribute("transaction.id", txn.transaction_id)

        try:
            # Create delta graph for new triples
            delta = Graph()
            delta.bind("unrdf", UNRDF)

            # PRE_INGESTION hooks
            if self.hook_executor:
                context = HookContext(
                    phase=HookPhase.PRE_INGESTION,
                    graph=self.engine.graph,
                    delta=delta,
                    transaction_id=txn.transaction_id,
                    metadata={"items": items},
                )
                self.hook_executor.execute_phase(HookPhase.PRE_INGESTION, context)

            # Convert JSON to RDF
            for item in items:
                self._json_to_rdf(item, delta, base_uri)

            span.set_attribute("delta.triples", len(delta))

            # Add triples to transaction
            for s, p, o in delta:
                self.engine.add_triple(s, p, o, txn)

            # ON_CHANGE hooks
            if self.hook_executor:
                context = HookContext(
                    phase=HookPhase.ON_CHANGE,
                    graph=self.engine.graph,
                    delta=delta,
                    transaction_id=txn.transaction_id,
                )
                self.hook_executor.execute_phase(HookPhase.ON_CHANGE, context)

            # PRE_VALIDATION hooks
            validation_result = None
            if self.validate_on_ingest and self.validator and self.validator.has_shapes():
                if self.hook_executor:
                    context = HookContext(
                        phase=HookPhase.PRE_VALIDATION,
                        graph=self.engine.graph,
                        delta=delta,
                        transaction_id=txn.transaction_id,
                    )
                    self.hook_executor.execute_phase(HookPhase.PRE_VALIDATION, context)

                # Validate delta
                validation = self.validator.validate(delta)
                validation_result = validation.to_dict()

                # POST_VALIDATION hooks
                if self.hook_executor:
                    context = HookContext(
                        phase=HookPhase.POST_VALIDATION,
                        graph=self.engine.graph,
                        delta=delta,
                        transaction_id=txn.transaction_id,
                        metadata={"validation_report": validation_result},
                    )
                    self.hook_executor.execute_phase(HookPhase.POST_VALIDATION, context)

                    # Check if hooks signaled rollback
                    if context.metadata.get("should_rollback"):
                        self.engine.rollback(txn)
                        return IngestionResult(
                            success=False,
                            triples_added=0,
                            transaction_id=txn.transaction_id,
                            validation_result=validation_result,
                            error=context.metadata.get(
                                "rollback_reason", "Validation failed"
                            ),
                        )

                if not validation.conforms:
                    self.engine.rollback(txn)
                    return IngestionResult(
                        success=False,
                        triples_added=0,
                        transaction_id=txn.transaction_id,
                        validation_result=validation_result,
                        error="SHACL validation failed",
                    )

            # Commit transaction
            self.engine.commit(txn)

            # POST_COMMIT hooks
            hook_results = []
            if self.hook_executor:
                context = HookContext(
                    phase=HookPhase.POST_COMMIT,
                    graph=self.engine.graph,
                    delta=delta,
                    transaction_id=txn.transaction_id,
                )
                hook_results = self.hook_executor.execute_phase(HookPhase.POST_COMMIT, context)

            return IngestionResult(
                success=True,
                triples_added=len(delta),
                transaction_id=txn.transaction_id,
                validation_result=validation_result,
                hook_results=hook_results,
            )

        except Exception as e:
            # Rollback on error
            if txn.can_modify():
                self.engine.rollback(txn)

            span.record_exception(e)
            return IngestionResult(
                success=False,
                triples_added=0,
                transaction_id=txn.transaction_id,
                error=str(e),
            )

    def _json_to_rdf(
        self, data: dict[str, Any], graph: Graph, base_uri: str
    ) -> URIRef:
        """Convert JSON object to RDF triples.

        Parameters
        ----------
        data : dict[str, Any]
            JSON object
        graph : Graph
            Target RDF graph
        base_uri : str
            Base URI for entities

        Returns
        -------
        URIRef
            Subject URI of created entity

        """
        # Generate entity URI
        entity_id = data.get("id", data.get("_id", self._generate_id()))
        subject = URIRef(f"{base_uri}{entity_id}")

        # Add type if specified
        if "type" in data:
            type_uri = (
                URIRef(data["type"])
                if data["type"].startswith("http")
                else UNRDF[data["type"]]
            )
            graph.add((subject, RDF.type, type_uri))

        # Convert properties to RDF
        for key, value in data.items():
            if key in ("id", "_id", "type"):
                continue

            predicate = UNRDF[key]

            if isinstance(value, dict):
                # Nested object - recurse
                obj = self._json_to_rdf(value, graph, base_uri)
                graph.add((subject, predicate, obj))

            elif isinstance(value, list):
                # Array - create multiple triples
                for item in value:
                    if isinstance(item, dict):
                        obj = self._json_to_rdf(item, graph, base_uri)
                        graph.add((subject, predicate, obj))
                    else:
                        obj = self._python_to_literal(item)
                        graph.add((subject, predicate, obj))

            else:
                # Primitive value
                obj = self._python_to_literal(value)
                graph.add((subject, predicate, obj))

        return subject

    def _python_to_literal(self, value: Any) -> Literal:
        """Convert Python value to RDF literal.

        Parameters
        ----------
        value : Any
            Python value

        Returns
        -------
        Literal
            RDF literal with appropriate datatype

        """
        if isinstance(value, bool):
            return Literal(value, datatype=XSD.boolean)
        if isinstance(value, int):
            return Literal(value, datatype=XSD.integer)
        if isinstance(value, float):
            return Literal(value, datatype=XSD.double)
        return Literal(str(value))

    def _generate_id(self) -> str:
        """Generate unique ID for entity.

        Returns
        -------
        str
            Unique identifier

        """
        import uuid

        return str(uuid.uuid4())

    @tracer.start_as_current_span("ingestion.ingest_batch")
    def ingest_batch(
        self,
        items: list[dict[str, Any]],
        agent: str,
        reason: str | None = None,
        batch_size: int = 100,
    ) -> list[IngestionResult]:
        """Ingest multiple items in batches.

        Parameters
        ----------
        items : list[dict[str, Any]]
            Items to ingest
        agent : str
            Agent performing ingestion
        reason : str, optional
            Reason for ingestion
        batch_size : int, default=100
            Number of items per batch

        Returns
        -------
        list[IngestionResult]
            Results for each batch

        """
        span = trace.get_current_span()
        span.set_attribute("total_items", len(items))
        span.set_attribute("batch_size", batch_size)

        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            result = self.ingest_json(data=batch, agent=agent, reason=reason)
            results.append(result)

        successful = sum(1 for r in results if r.success)
        span.set_attribute("batches.total", len(results))
        span.set_attribute("batches.successful", successful)

        return results

    @tracer.start_as_current_span("ingestion.materialize_features")
    def materialize_features(
        self,
        template_uri: URIRef,
        target_pattern: str,
        agent: str,
    ) -> IngestionResult:
        """Materialize features from a template.

        Applies a feature template to all entities matching the target pattern.

        Parameters
        ----------
        template_uri : URIRef
            URI of feature template
        target_pattern : str
            SPARQL pattern matching target entities
        agent : str
            Agent performing materialization

        Returns
        -------
        IngestionResult
            Materialization result

        """
        span = trace.get_current_span()
        span.set_attribute("template.uri", str(template_uri))

        # Query for template definition
        query = f"""
        PREFIX unrdf: <{UNRDF}>
        SELECT ?property ?transform WHERE {{
            <{template_uri}> unrdf:property ?property .
            OPTIONAL {{ <{template_uri}> unrdf:transform ?transform }}
        }}
        """

        template_props = list(self.engine.query(query))
        if not template_props:
            return IngestionResult(
                success=False,
                triples_added=0,
                transaction_id="",
                error=f"Template not found: {template_uri}",
            )

        # Query for target entities
        target_query = f"""
        SELECT ?target WHERE {{
            {target_pattern}
        }}
        """

        targets = list(self.engine.query(target_query))
        span.set_attribute("targets.count", len(targets))

        # Create transaction
        txn = self.engine.transaction(agent=agent, reason=f"Materialize {template_uri}")

        # Apply template to each target
        for target_row in targets:
            target = target_row[0]

            for prop_row in template_props:
                property_uri = prop_row[0]
                # In a real implementation, would apply transforms here
                # For now, just copy property values

                # This is a simplified version - real implementation would
                # execute the transform logic
                self.engine.add_triple(
                    target, property_uri, Literal("materialized"), txn
                )

        self.engine.commit(txn)

        return IngestionResult(
            success=True,
            triples_added=len(targets) * len(template_props),
            transaction_id=txn.transaction_id,
        )
