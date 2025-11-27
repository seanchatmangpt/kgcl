#!/usr/bin/env python3
"""Demo: RDF Ontology → Next.js App Generation.

This script demonstrates the full A = μ_proj(O) projection formula:

    O (RDF Ontology) → μ_proj (Templates + SPARQL) → A (Next.js Artifacts)

Run this script to see:
1. Loading an e-commerce ontology
2. Generating TypeScript types, API routes, components
3. Mutating the ontology (adding a new entity)
4. Regenerating to show the diff

Usage:
    cd examples/nextjs_projection
    python demo.py

Prerequisites:
    pip install rdflib
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from rdflib import RDF, RDFS, OWL, XSD, Graph, Literal, Namespace

from kgcl.projection.adapters.rdflib_adapter import RDFLibAdapter
from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.engine.projection_engine import ProjectionConfig, ProjectionEngine
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry


SHOP = Namespace("http://example.org/ecommerce#")


def create_ecommerce_ontology() -> Graph:
    """Create sample e-commerce RDF ontology."""
    g = Graph()
    g.bind("shop", SHOP)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    # Product entity
    g.add((SHOP.Product, RDF.type, OWL.Class))
    g.add((SHOP.Product, RDFS.label, Literal("Product")))
    g.add((SHOP.Product, RDFS.comment, Literal("A product available for purchase")))
    g.add((SHOP.Product, SHOP.slug, Literal("product")))
    g.add((SHOP.Product, SHOP.plural, Literal("products")))

    # Product properties
    for prop, label, range_type, required in [
        (SHOP.name, "name", XSD.string, True),
        (SHOP.price, "price", XSD.decimal, True),
        (SHOP.description, "description", XSD.string, False),
        (SHOP.inStock, "inStock", XSD.boolean, False),
    ]:
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.domain, SHOP.Product))
        g.add((prop, RDFS.range, range_type))
        g.add((prop, RDFS.label, Literal(label)))
        if required:
            g.add((prop, SHOP.required, Literal("true")))

    # Customer entity
    g.add((SHOP.Customer, RDF.type, OWL.Class))
    g.add((SHOP.Customer, RDFS.label, Literal("Customer")))
    g.add((SHOP.Customer, SHOP.slug, Literal("customer")))
    g.add((SHOP.Customer, SHOP.plural, Literal("customers")))

    # Customer properties
    g.add((SHOP.email, RDF.type, OWL.DatatypeProperty))
    g.add((SHOP.email, RDFS.domain, SHOP.Customer))
    g.add((SHOP.email, RDFS.range, XSD.string))
    g.add((SHOP.email, RDFS.label, Literal("email")))
    g.add((SHOP.email, SHOP.required, Literal("true")))

    return g


def create_typescript_template() -> TemplateDescriptor:
    """Create TypeScript interface template."""
    return TemplateDescriptor(
        id="ts-entity",
        engine="jinja2",
        language="typescript",
        framework="nextjs",
        version="1.0.0",
        ontology=OntologyConfig(graph_id="ecommerce", base_iri=str(SHOP)),
        queries=(
            QueryDescriptor(
                name="entities",
                purpose="Get all domain entities",
                source=QuerySource.INLINE,
                content=dedent("""
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?uri ?label ?slug ?comment WHERE {
                        ?uri a owl:Class ;
                             rdfs:label ?label ;
                             shop:slug ?slug .
                        OPTIONAL { ?uri rdfs:comment ?comment }
                        FILTER(STRSTARTS(STR(?uri), "http://example.org/ecommerce#"))
                    }
                    ORDER BY ?label
                """).strip(),
            ),
            QueryDescriptor(
                name="all_properties",
                purpose="Get all properties",
                source=QuerySource.INLINE,
                content=dedent("""
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?prop ?label ?domain ?range ?required WHERE {
                        ?prop a owl:DatatypeProperty ;
                              rdfs:domain ?domain ;
                              rdfs:range ?range ;
                              rdfs:label ?label .
                        OPTIONAL { ?prop shop:required ?required }
                    }
                    ORDER BY ?domain ?label
                """).strip(),
            ),
        ),
        n3_rules=(),
        metadata=TemplateMetadata(
            author="kgcl-demo",
            description="TypeScript interfaces for all entities",
            tags=("typescript", "nextjs"),
        ),
        template_path="entities.ts.j2",
        raw_content=dedent("""
            /**
             * E-Commerce Domain Types
             * @generated from RDF ontology via KGCL projection
             */

            {% for entity in sparql.entities %}
            /**
             * {{ entity.label }} - {{ entity.comment | default('Domain entity') }}
             * @see {{ entity.uri }}
             */
            export interface {{ entity.label }} {
              id: string;
            {% for prop in sparql.all_properties %}
            {% if prop.domain | uri_local_name == entity.label %}
              {{ prop.label | camel_case }}{% if prop.required != 'true' %}?{% endif %}: {{ prop.range | xsd_to_typescript }};
            {% endif %}
            {% endfor %}
              createdAt: Date;
              updatedAt: Date;
            }

            {% endfor %}
            // Total entities: {{ sparql.entities | length }}
        """).strip(),
    )


def create_api_route_template() -> TemplateDescriptor:
    """Create Next.js API route template."""
    return TemplateDescriptor(
        id="api-routes-index",
        engine="jinja2",
        language="typescript",
        framework="nextjs",
        version="1.0.0",
        ontology=OntologyConfig(graph_id="ecommerce", base_iri=str(SHOP)),
        queries=(
            QueryDescriptor(
                name="entities",
                purpose="Get entities for API routes",
                source=QuerySource.INLINE,
                content=dedent("""
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX shop: <http://example.org/ecommerce#>
                    SELECT ?label ?slug ?plural WHERE {
                        ?uri a owl:Class ;
                             rdfs:label ?label ;
                             shop:slug ?slug ;
                             shop:plural ?plural .
                        FILTER(STRSTARTS(STR(?uri), "http://example.org/ecommerce#"))
                    }
                    ORDER BY ?label
                """).strip(),
            ),
        ),
        n3_rules=(),
        metadata=TemplateMetadata(
            author="kgcl-demo",
            description="API routes summary",
            tags=("api", "nextjs"),
        ),
        template_path="api-index.ts.j2",
        raw_content=dedent("""
            /**
             * E-Commerce API Routes
             * @generated from RDF ontology via KGCL projection
             */

            // Available API endpoints:
            {% for entity in sparql.entities %}
            // GET/POST   /api/{{ entity.plural }}
            // GET/PUT/DELETE /api/{{ entity.plural }}/[id]
            {% endfor %}

            export const API_ENDPOINTS = {
            {% for entity in sparql.entities %}
              {{ entity.slug | upper }}: '/api/{{ entity.plural }}',
            {% endfor %}
            } as const;

            export type ApiEndpoint = typeof API_ENDPOINTS[keyof typeof API_ENDPOINTS];
        """).strip(),
    )


def print_section(title: str) -> None:
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main() -> None:
    """Run the projection demo."""
    print_section("KGCL Projection Demo: RDF → Next.js")
    print("\nFormula: A = μ_proj(O)")
    print("  O = RDF Ontology (e-commerce domain)")
    print("  μ_proj = Projection operator (Jinja + SPARQL)")
    print("  A = Artifacts (TypeScript, API routes, components)")

    # Create ontology
    print_section("Phase 1: Create RDF Ontology")
    graph = create_ecommerce_ontology()
    print(f"Created ontology with {len(graph)} triples")
    print("Entities: Product, Customer")

    # Setup projection engine
    client = RDFLibAdapter(graph, graph_id="ecommerce")
    graph_clients = {client.graph_id: client}

    template_registry = InMemoryTemplateRegistry()
    ts_template = create_typescript_template()
    api_template = create_api_route_template()
    template_registry.add(ts_template)
    template_registry.add(api_template)

    engine = ProjectionEngine(
        template_registry=template_registry,
        graph_clients=graph_clients,
        config=ProjectionConfig(strict_mode=False),
    )

    # Generate TypeScript
    print_section("Phase 2: Generate TypeScript Types")
    ts_result = engine.render(ts_template.template_path)
    print(ts_result.content)
    print(f"\n[Rendered in {ts_result.render_time_ms:.2f}ms, {ts_result.query_count} queries]")

    # Generate API routes
    print_section("Phase 3: Generate API Routes Index")
    api_result = engine.render(api_template.template_path)
    print(api_result.content)

    # Mutate ontology
    print_section("Phase 4: Mutate RDF - Add 'Order' Entity")
    graph.add((SHOP.Order, RDF.type, OWL.Class))
    graph.add((SHOP.Order, RDFS.label, Literal("Order")))
    graph.add((SHOP.Order, RDFS.comment, Literal("A customer order")))
    graph.add((SHOP.Order, SHOP.slug, Literal("order")))
    graph.add((SHOP.Order, SHOP.plural, Literal("orders")))

    # Order properties
    graph.add((SHOP.orderDate, RDF.type, OWL.DatatypeProperty))
    graph.add((SHOP.orderDate, RDFS.domain, SHOP.Order))
    graph.add((SHOP.orderDate, RDFS.range, XSD.dateTime))
    graph.add((SHOP.orderDate, RDFS.label, Literal("orderDate")))
    graph.add((SHOP.orderDate, SHOP.required, Literal("true")))

    graph.add((SHOP.totalAmount, RDF.type, OWL.DatatypeProperty))
    graph.add((SHOP.totalAmount, RDFS.domain, SHOP.Order))
    graph.add((SHOP.totalAmount, RDFS.range, XSD.decimal))
    graph.add((SHOP.totalAmount, RDFS.label, Literal("totalAmount")))

    print(f"Ontology now has {len(graph)} triples")
    print("Entities: Product, Customer, Order (NEW!)")

    # Regenerate
    print_section("Phase 5: Regenerate - Order Now Appears!")
    ts_result2 = engine.render(ts_template.template_path)
    print(ts_result2.content)

    print_section("Phase 6: API Routes Updated")
    api_result2 = engine.render(api_template.template_path)
    print(api_result2.content)

    print_section("Demo Complete!")
    print("\nKey takeaways:")
    print("  ✓ RDF ontology defines domain schema")
    print("  ✓ SPARQL queries extract entity metadata")
    print("  ✓ Jinja templates generate type-safe code")
    print("  ✓ Mutations to RDF automatically propagate")
    print("  ✓ Next.js app stays in sync with ontology")
    print("\nIn production, the KGCL daemon watches the ontology")
    print("and triggers regeneration on any RDF change.")


if __name__ == "__main__":
    main()
