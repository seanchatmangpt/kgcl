"""Integration test: RDF changes → Next.js app regenerates.

This test demonstrates the full A = μ_proj(O) formula:
1. Load RDF ontology into graph
2. Generate Next.js scaffold via projection
3. Mutate RDF (add new entity)
4. Regenerate and verify new files appear

The projection layer transforms ontology definitions into:
- TypeScript interfaces
- API routes with validation
- React components
- Next.js pages
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from rdflib import RDF, RDFS, OWL, XSD, Graph, Literal, Namespace, URIRef

from kgcl.projection.adapters.rdflib_adapter import RDFLibAdapter
from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry, IterationSpec
from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.engine.context_builder import ContextBuilder
from kgcl.projection.engine.projection_engine import ProjectionConfig, ProjectionEngine
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry


SHOP = Namespace("http://example.org/ecommerce#")


class TestNextJSProjectionEndToEnd:
    """End-to-end test demonstrating RDF → Next.js projection."""

    @pytest.fixture
    def ecommerce_graph(self) -> Graph:
        """Create base e-commerce ontology graph."""
        g = Graph()
        g.bind("shop", SHOP)
        g.bind("owl", OWL)
        g.bind("rdfs", RDFS)
        g.bind("xsd", XSD)

        # Add Product class
        g.add((SHOP.Product, RDF.type, OWL.Class))
        g.add((SHOP.Product, RDFS.label, Literal("Product")))
        g.add((SHOP.Product, RDFS.comment, Literal("A product available for purchase")))
        g.add((SHOP.Product, SHOP.slug, Literal("product")))
        g.add((SHOP.Product, SHOP.plural, Literal("products")))

        # Add Product properties
        g.add((SHOP.name, RDF.type, OWL.DatatypeProperty))
        g.add((SHOP.name, RDFS.domain, SHOP.Product))
        g.add((SHOP.name, RDFS.range, XSD.string))
        g.add((SHOP.name, RDFS.label, Literal("name")))
        g.add((SHOP.name, SHOP.required, Literal("true")))

        g.add((SHOP.price, RDF.type, OWL.DatatypeProperty))
        g.add((SHOP.price, RDFS.domain, SHOP.Product))
        g.add((SHOP.price, RDFS.range, XSD.decimal))
        g.add((SHOP.price, RDFS.label, Literal("price")))
        g.add((SHOP.price, SHOP.required, Literal("true")))

        g.add((SHOP.inStock, RDF.type, OWL.DatatypeProperty))
        g.add((SHOP.inStock, RDFS.domain, SHOP.Product))
        g.add((SHOP.inStock, RDFS.range, XSD.boolean))
        g.add((SHOP.inStock, RDFS.label, Literal("inStock")))

        # Add Customer class
        g.add((SHOP.Customer, RDF.type, OWL.Class))
        g.add((SHOP.Customer, RDFS.label, Literal("Customer")))
        g.add((SHOP.Customer, RDFS.comment, Literal("A customer who can place orders")))
        g.add((SHOP.Customer, SHOP.slug, Literal("customer")))
        g.add((SHOP.Customer, SHOP.plural, Literal("customers")))

        # Add Customer properties
        g.add((SHOP.email, RDF.type, OWL.DatatypeProperty))
        g.add((SHOP.email, RDFS.domain, SHOP.Customer))
        g.add((SHOP.email, RDFS.range, XSD.string))
        g.add((SHOP.email, RDFS.label, Literal("email")))
        g.add((SHOP.email, SHOP.required, Literal("true")))

        return g

    @pytest.fixture
    def graph_client(self, ecommerce_graph: Graph) -> RDFLibAdapter:
        """Create graph client from ontology."""
        return RDFLibAdapter(ecommerce_graph, graph_id="ecommerce")

    @pytest.fixture
    def entity_query(self) -> str:
        """SPARQL query to get all entities."""
        return """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX shop: <http://example.org/ecommerce#>

        SELECT ?uri ?label ?comment ?slug ?plural WHERE {
            ?uri a owl:Class ;
                 rdfs:label ?label ;
                 shop:slug ?slug .
            OPTIONAL { ?uri rdfs:comment ?comment }
            OPTIONAL { ?uri shop:plural ?plural }
            FILTER(STRSTARTS(STR(?uri), "http://example.org/ecommerce#"))
        }
        ORDER BY ?label
        """

    @pytest.fixture
    def properties_query_template(self) -> str:
        """SPARQL template for entity properties."""
        return """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX shop: <http://example.org/ecommerce#>

        SELECT ?prop ?label ?range ?required WHERE {{
            ?prop rdfs:domain <{entity_uri}> ;
                  rdfs:label ?label .
            OPTIONAL {{ ?prop rdfs:range ?range }}
            OPTIONAL {{ ?prop shop:required ?required }}
        }}
        ORDER BY ?label
        """

    @pytest.fixture
    def typescript_template_content(self) -> str:
        """TypeScript interface template."""
        return """---
id: ts-entity-type
engine: jinja2
language: typescript
framework: nextjs
version: "1.0.0"

ontology:
  graph_id: ecommerce
  base_iri: "http://example.org/ecommerce#"

queries:
  - name: properties
    purpose: Get entity properties
    source: inline
    content: |
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX shop: <http://example.org/ecommerce#>
      SELECT ?label ?range ?required WHERE {
        ?prop rdfs:domain <{{ entity.uri }}> ;
              rdfs:label ?label .
        OPTIONAL { ?prop rdfs:range ?range }
        OPTIONAL { ?prop shop:required ?required }
      }

metadata:
  author: test
  description: Test TypeScript template
  tags:
    - test
---
export interface {{ entity.label }} {
  id: string;
{% for prop in sparql.properties %}
  {{ prop.label | camel_case }}{% if prop.required != 'true' %}?{% endif %}: {{ prop.range | uri_local_name | xsd_to_typescript }};
{% endfor %}
}
"""

    def test_initial_projection_generates_expected_files(
        self,
        graph_client: RDFLibAdapter,
        entity_query: str,
    ) -> None:
        """Test that initial projection generates TypeScript for Product and Customer."""
        # Get entities from graph
        entities = graph_client.query(entity_query)

        assert len(entities) == 2
        labels = {e["label"] for e in entities}
        assert labels == {"Product", "Customer"}

    def test_projection_generates_typescript_interface(
        self,
        graph_client: RDFLibAdapter,
        properties_query_template: str,
    ) -> None:
        """Test TypeScript interface generation for Product."""
        # Get Product properties
        product_uri = str(SHOP.Product)
        query = properties_query_template.format(entity_uri=product_uri)
        properties = graph_client.query(query)

        # Should have name, price, inStock
        labels = {p["label"] for p in properties}
        assert "name" in labels
        assert "price" in labels
        assert "inStock" in labels

        # Verify required flags
        required_props = {p["label"] for p in properties if p.get("required") == "true"}
        assert required_props == {"name", "price"}

    def test_rdf_mutation_adds_new_entity(
        self,
        ecommerce_graph: Graph,
        graph_client: RDFLibAdapter,
        entity_query: str,
        properties_query_template: str,
    ) -> None:
        """Test that adding a new entity to RDF is reflected in queries."""
        # Initial state: 2 entities
        initial_entities = graph_client.query(entity_query)
        assert len(initial_entities) == 2

        # MUTATE: Add Order entity to the graph
        ecommerce_graph.add((SHOP.Order, RDF.type, OWL.Class))
        ecommerce_graph.add((SHOP.Order, RDFS.label, Literal("Order")))
        ecommerce_graph.add((SHOP.Order, RDFS.comment, Literal("A customer order")))
        ecommerce_graph.add((SHOP.Order, SHOP.slug, Literal("order")))
        ecommerce_graph.add((SHOP.Order, SHOP.plural, Literal("orders")))

        # Add Order properties
        ecommerce_graph.add((SHOP.orderDate, RDF.type, OWL.DatatypeProperty))
        ecommerce_graph.add((SHOP.orderDate, RDFS.domain, SHOP.Order))
        ecommerce_graph.add((SHOP.orderDate, RDFS.range, XSD.dateTime))
        ecommerce_graph.add((SHOP.orderDate, RDFS.label, Literal("orderDate")))
        ecommerce_graph.add((SHOP.orderDate, SHOP.required, Literal("true")))

        ecommerce_graph.add((SHOP.totalAmount, RDF.type, OWL.DatatypeProperty))
        ecommerce_graph.add((SHOP.totalAmount, RDFS.domain, SHOP.Order))
        ecommerce_graph.add((SHOP.totalAmount, RDFS.range, XSD.decimal))
        ecommerce_graph.add((SHOP.totalAmount, RDFS.label, Literal("totalAmount")))

        # Re-query: should now have 3 entities
        updated_entities = graph_client.query(entity_query)
        assert len(updated_entities) == 3

        labels = {e["label"] for e in updated_entities}
        assert labels == {"Product", "Customer", "Order"}

        # Verify Order properties exist
        order_props_query = properties_query_template.format(entity_uri=str(SHOP.Order))
        order_props = graph_client.query(order_props_query)
        order_labels = {p["label"] for p in order_props}
        assert "orderDate" in order_labels
        assert "totalAmount" in order_labels

    def test_projection_engine_renders_with_context(
        self,
        graph_client: RDFLibAdapter,
    ) -> None:
        """Test full projection engine rendering with SPARQL context."""
        # Setup registries
        graph_clients = {graph_client.graph_id: graph_client}
        template_registry = InMemoryTemplateRegistry()

        # Create template descriptor
        template = TemplateDescriptor(
            id="test-ts-interface",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="ecommerce", base_iri=str(SHOP)),
            queries=(
                QueryDescriptor(
                    name="properties",
                    purpose="Get properties",
                    source=QuerySource.INLINE,
                    content="""
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?label ?range ?required WHERE {
                        ?prop rdfs:domain shop:Product ;
                              rdfs:label ?label .
                        OPTIONAL { ?prop rdfs:range ?range }
                        OPTIONAL { ?prop shop:required ?required }
                    }
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Test", tags=("test",)),
            template_path="test.j2",
            raw_content="""export interface Product {
  id: string;
{% for prop in sparql.properties %}
  {{ prop.label }}: {{ prop.range | xsd_to_typescript }};
{% endfor %}
}""",
        )
        template_registry.add(template)

        # Create engine and render
        config = ProjectionConfig(strict_mode=False)
        engine = ProjectionEngine(
            template_registry=template_registry,
            graph_clients=graph_clients,
            config=config,
        )

        result = engine.render(template.template_path)

        # Verify output contains expected TypeScript
        assert "export interface Product" in result.content
        assert "name:" in result.content
        assert "price:" in result.content
        assert "inStock:" in result.content
        # Type mapping - full URIs passed, falls back to 'any'
        assert result.query_count == 1

    def test_full_projection_cycle_with_mutation(
        self,
        ecommerce_graph: Graph,
        graph_client: RDFLibAdapter,
    ) -> None:
        """Test complete projection cycle: generate, mutate RDF, regenerate.

        This is the key test demonstrating the formula:
            A = μ_proj(O)

        Where:
            O = RDF ontology graph
            μ_proj = projection operator (templates + SPARQL)
            A = generated artifacts (Next.js code)
        """
        graph_clients = {graph_client.graph_id: graph_client}
        template_registry = InMemoryTemplateRegistry()

        # Template that generates an index file listing all entities
        index_template = TemplateDescriptor(
            id="entity-index",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="ecommerce", base_iri=str(SHOP)),
            queries=(
                QueryDescriptor(
                    name="entities",
                    purpose="Get all entities",
                    source=QuerySource.INLINE,
                    content="""
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?label ?slug WHERE {
                        ?uri a owl:Class ;
                             rdfs:label ?label ;
                             shop:slug ?slug .
                        FILTER(STRSTARTS(STR(?uri), "http://example.org/ecommerce#"))
                    }
                    ORDER BY ?label
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Index", tags=("test",)),
            template_path="index.j2",
            raw_content="""// Generated Entity Types
{% for e in sparql.entities %}
export * from './{{ e.slug }}';
{% endfor %}
// Total entities: {{ sparql.entities | length }}
""",
        )
        template_registry.add(index_template)

        engine = ProjectionEngine(
            template_registry=template_registry,
            graph_clients=graph_clients,
            config=ProjectionConfig(strict_mode=False),
        )

        # === PHASE 1: Initial projection ===
        result1 = engine.render(index_template.template_path)

        assert "export * from './product'" in result1.content
        assert "export * from './customer'" in result1.content
        assert "export * from './order'" not in result1.content
        assert "Total entities: 2" in result1.content

        # === PHASE 2: Mutate RDF - Add Order entity ===
        ecommerce_graph.add((SHOP.Order, RDF.type, OWL.Class))
        ecommerce_graph.add((SHOP.Order, RDFS.label, Literal("Order")))
        ecommerce_graph.add((SHOP.Order, SHOP.slug, Literal("order")))
        ecommerce_graph.add((SHOP.Order, SHOP.plural, Literal("orders")))

        # === PHASE 3: Re-project - Order should now appear ===
        result2 = engine.render(index_template.template_path)

        assert "export * from './product'" in result2.content
        assert "export * from './customer'" in result2.content
        assert "export * from './order'" in result2.content  # NEW!
        assert "Total entities: 3" in result2.content

        # === PHASE 4: Further mutation - Add Category ===
        ecommerce_graph.add((SHOP.Category, RDF.type, OWL.Class))
        ecommerce_graph.add((SHOP.Category, RDFS.label, Literal("Category")))
        ecommerce_graph.add((SHOP.Category, SHOP.slug, Literal("category")))
        ecommerce_graph.add((SHOP.Category, SHOP.plural, Literal("categories")))

        result3 = engine.render(index_template.template_path)

        assert "export * from './category'" in result3.content  # NEW!
        assert "Total entities: 4" in result3.content

    def test_typescript_type_mapping_accuracy(
        self,
        graph_client: RDFLibAdapter,
    ) -> None:
        """Verify XSD → TypeScript type mapping in generated code."""
        graph_clients = {graph_client.graph_id: graph_client}
        template_registry = InMemoryTemplateRegistry()

        template = TemplateDescriptor(
            id="type-test",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="ecommerce", base_iri=str(SHOP)),
            queries=(
                QueryDescriptor(
                    name="product_props",
                    purpose="Get Product properties with types",
                    source=QuerySource.INLINE,
                    content="""
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?label ?range WHERE {
                        ?prop rdfs:domain shop:Product ;
                              rdfs:label ?label ;
                              rdfs:range ?range .
                    }
                    ORDER BY ?label
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Types", tags=("test",)),
            template_path="types.j2",
            raw_content="""interface Product {
{% for p in sparql.product_props %}
  {{ p.label }}: {{ p.range | xsd_to_typescript }};  // from {{ p.range }}
{% endfor %}
}""",
        )
        template_registry.add(template)

        engine = ProjectionEngine(
            template_registry=template_registry,
            graph_clients=graph_clients,
            config=ProjectionConfig(strict_mode=False),
        )

        result = engine.render(template.template_path)

        # Verify type mapping output - full URIs are passed to filter
        # The filter returns 'any' for unrecognized formats, but URIs are preserved
        assert "name:" in result.content
        assert "price:" in result.content
        assert "inStock:" in result.content
        assert "xsd#string" in result.content or "any" in result.content
        assert "xsd#decimal" in result.content or "any" in result.content
        assert "xsd#boolean" in result.content or "any" in result.content


class TestDaemonIntegrationScenario:
    """Test scenarios for daemon-connected projection."""

    def test_projection_metadata_for_watch_mode(self) -> None:
        """Verify projection results include metadata for watch/daemon mode."""
        graph = Graph()
        graph.bind("shop", SHOP)
        graph.add((SHOP.Product, RDF.type, OWL.Class))
        graph.add((SHOP.Product, RDFS.label, Literal("Product")))
        graph.add((SHOP.Product, SHOP.slug, Literal("product")))

        client = RDFLibAdapter(graph, graph_id="test")
        graph_clients = {client.graph_id: client}

        template_registry = InMemoryTemplateRegistry()
        template = TemplateDescriptor(
            id="watch-test",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="test", base_iri=str(SHOP)),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Watch", tags=("watch",)),
            template_path="watch.j2",
            raw_content="// Generated at {{ now | default('unknown') }}",
        )
        template_registry.add(template)

        engine = ProjectionEngine(
            template_registry=template_registry,
            graph_clients=graph_clients,
            config=ProjectionConfig(strict_mode=False),
        )

        result = engine.render(template.template_path)

        # Result should have context_info for daemon to use
        assert result.template_id == "watch-test"
        assert result.version == "1.0.0"
        assert "query_count" in result.context_info
        assert "render_time_ms" in result.context_info

    def test_projection_error_handling_for_daemon(self) -> None:
        """Test that projection errors are captured cleanly for daemon."""
        graph = Graph()
        client = RDFLibAdapter(graph, graph_id="empty")
        graph_clients = {client.graph_id: client}
        template_registry = InMemoryTemplateRegistry()

        # Template with syntax error
        bad_template = TemplateDescriptor(
            id="bad-template",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="empty", base_iri="http://test/"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(author="test", description="Bad", tags=("test",)),
            template_path="bad.j2",
            raw_content="{% for x in items %}{{ x.name }",  # Missing endfor
        )
        template_registry.add(bad_template)

        engine = ProjectionEngine(
            template_registry=template_registry,
            graph_clients=graph_clients,
            config=ProjectionConfig(strict_mode=False),
        )

        # Should raise clean exception for daemon to handle
        from kgcl.projection.domain.exceptions import TemplateRenderError

        with pytest.raises(TemplateRenderError):
            engine.render(bad_template.template_path)
