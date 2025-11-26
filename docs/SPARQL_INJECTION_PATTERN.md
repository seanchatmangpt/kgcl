# SPARQL Injection Pattern for Pure Kernel Verbs

**Mission**: Design a pattern where Kernel verbs execute SPARQL templates from the ontology, eliminating Python if/else parameter interpretation.

**Status**: DESIGN COMPLETE
**Date**: 2025-11-25

---

## Executive Summary

This pattern achieves **true RDF-driven execution** by injecting parameterized SPARQL templates from the ontology into Kernel verbs. The ontology defines ALL execution logic; Python code merely retrieves and executes templates with variable bindings.

**Key Principle**: `A = μ(O)` where:
- O = RDF graph (observation)
- μ = SPARQL query engine (operator)
- A = QuadDelta (action)

**No Python if/else interprets parameters.** All logic is in SPARQL.

---

## Problem: Current State (IMPURE)

```python
# BEFORE: Python if/else interprets parameters
def copy(graph: Graph, subject: URIRef, ctx: Context, config: VerbConfig) -> QuadDelta:
    """Copy operation with parameter interpretation in Python."""

    # ❌ Python interprets cardinality parameter
    if config.cardinality == "topology":
        query = """
        SELECT ?p ?o WHERE {
            ?subject ?p ?o .
            FILTER(?p != rdf:type)
        }
        """
    elif config.cardinality == "dynamic":
        query = """
        SELECT ?p ?o WHERE {
            ?subject ?p ?o .
            ?p rdfs:subPropertyOf :dynamicProperty .
        }
        """
    else:
        raise ValueError(f"Unknown cardinality: {config.cardinality}")

    # ❌ Python builds and executes query
    results = graph.query(query.replace("?subject", f"<{subject}>"))
    return QuadDelta(additions=tuple(results))
```

**Issues**:
1. Python if/else encodes business logic
2. Query templates hardcoded in Python
3. Adding new cardinality requires Python changes
4. Not discoverable from ontology

---

## Solution: SPARQL Injection Pattern (PURE)

### 1. Evolved VerbConfig with Execution Template

```python
from dataclasses import dataclass
from rdflib import URIRef


@dataclass(frozen=True)
class VerbConfig:
    """Configuration for a Kernel verb, including execution template URI.

    All execution logic is defined in the ontology as SPARQL templates.
    Python code retrieves and executes templates with variable bindings.

    Parameters
    ----------
    verb_uri : URIRef
        URI identifying the verb in the ontology
    execution_template_uri : URIRef
        URI of the SPARQL template to execute (from ontology)
    parameters : dict[str, str]
        Parameters to bind in the template (e.g., {"cardinality": "topology"})
    timeout_ms : int
        Execution timeout in milliseconds
    """

    verb_uri: URIRef
    execution_template_uri: URIRef
    parameters: dict[str, str]
    timeout_ms: int = 100
```

### 2. Evolved Kernel.copy() Using Template Execution

```python
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.plugins.sparql.processor import prepareQuery


# Define namespace for Kernel ontology
KERNEL = Namespace("http://kgcl.dev/ontology/kernel#")


@dataclass(frozen=True)
class QuadDelta:
    """Immutable quad delta result from kernel verb execution."""

    additions: tuple[tuple[URIRef, URIRef, URIRef | Literal], ...]
    deletions: tuple[tuple[URIRef, URIRef, URIRef | Literal], ...] = ()


def copy(graph: Graph, subject: URIRef, ctx: dict[str, URIRef], config: VerbConfig) -> QuadDelta:
    """Execute copy verb using SPARQL template from ontology.

    Pure function: All logic in SPARQL template, NO Python if/else.

    Parameters
    ----------
    graph : Graph
        RDF graph containing the data
    subject : URIRef
        Subject node to copy from
    ctx : dict[str, URIRef]
        Context variables (target, namespace, etc.)
    config : VerbConfig
        Configuration with execution_template_uri

    Returns
    -------
    QuadDelta
        Additions/deletions to apply

    Notes
    -----
    This function NEVER changes. New copy behaviors are added by:
    1. Creating new SPARQL template in ontology
    2. Updating VerbConfig to reference new template

    NO Python code changes required.
    """
    # Retrieve SPARQL template from ontology (defined as kernel:sparqlTemplate)
    template_query = """
    SELECT ?template WHERE {
        ?template_uri kernel:sparqlTemplate ?template .
    }
    """
    template_results = graph.query(
        template_query,
        initNs={"kernel": KERNEL},
        initBindings={"template_uri": config.execution_template_uri}
    )

    # Extract template string
    template_str = next(iter(template_results), None)
    if not template_str:
        raise ValueError(f"No template found for {config.execution_template_uri}")

    # Prepare query with variable bindings
    # Template uses placeholders: ?subject, ?target, ?cardinality, etc.
    bindings = {
        "subject": subject,
        **ctx,  # Add context variables (target, namespace, etc.)
        **{k: Literal(v) for k, v in config.parameters.items()}  # Add config parameters
    }

    # Execute template with bindings
    prepared_query = prepareQuery(str(template_str[0]), initNs={"kernel": KERNEL, "rdf": RDF, "rdfs": RDFS})
    results = graph.query(prepared_query, initBindings=bindings)

    # Convert results to QuadDelta
    additions = tuple(
        (subject, row.predicate, row.object)
        for row in results
    )

    return QuadDelta(additions=additions)
```

### 3. Ontology: SPARQL Templates

```turtle
@prefix kernel: <http://kgcl.dev/ontology/kernel#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .


# ============================================================================
# KERNEL VERB DEFINITIONS
# ============================================================================

kernel:Verb
    a owl:Class ;
    rdfs:label "Kernel Verb" ;
    rdfs:comment "Abstract class for all kernel verbs (transmute, copy, filter, await, void)" .

kernel:Copy
    a owl:Class ;
    rdfs:subClassOf kernel:Verb ;
    rdfs:label "Copy Verb" ;
    rdfs:comment "Copies quads from source to target according to template logic" .


# ============================================================================
# EXECUTION TEMPLATE CLASS & PROPERTIES
# ============================================================================

kernel:ExecutionTemplate
    a owl:Class ;
    rdfs:label "Execution Template" ;
    rdfs:comment "SPARQL query template that defines verb execution logic" .

kernel:sparqlTemplate
    a owl:DatatypeProperty ;
    rdfs:label "SPARQL template" ;
    rdfs:comment "SPARQL query string with placeholders for variable binding" ;
    rdfs:domain kernel:ExecutionTemplate ;
    rdfs:range xsd:string .

kernel:requiresParameter
    a owl:DatatypeProperty ;
    rdfs:label "requires parameter" ;
    rdfs:comment "Parameter name that must be bound when executing this template" ;
    rdfs:domain kernel:ExecutionTemplate ;
    rdfs:range xsd:string .

kernel:templateVersion
    a owl:DatatypeProperty ;
    rdfs:label "template version" ;
    rdfs:comment "Semantic version of this template (allows evolution)" ;
    rdfs:domain kernel:ExecutionTemplate ;
    rdfs:range xsd:string .


# ============================================================================
# COPY VERB TEMPLATES - TOPOLOGY CARDINALITY
# ============================================================================

kernel:CopyTopologyTemplate
    a kernel:ExecutionTemplate ;
    rdfs:label "Copy Topology Template" ;
    rdfs:comment "Copies all structural properties (excludes rdf:type and metadata)" ;
    kernel:templateVersion "1.0.0" ;
    kernel:requiresParameter "subject" ;
    kernel:requiresParameter "target" ;
    kernel:sparqlTemplate """
        # Copy topology: structural properties only
        SELECT ?predicate ?object WHERE {
            ?subject ?predicate ?object .

            # Exclude type assertions
            FILTER(?predicate != rdf:type)

            # Exclude metadata predicates
            FILTER(?predicate NOT IN (
                kernel:createdAt,
                kernel:updatedAt,
                kernel:version
            ))

            # Only include properties with structural semantics
            FILTER EXISTS {
                ?predicate rdfs:subPropertyOf* kernel:structuralProperty .
            }
        }
    """ .


# ============================================================================
# COPY VERB TEMPLATES - DYNAMIC CARDINALITY
# ============================================================================

kernel:CopyDynamicTemplate
    a kernel:ExecutionTemplate ;
    rdfs:label "Copy Dynamic Template" ;
    rdfs:comment "Copies only dynamic/runtime properties (excludes static structure)" ;
    kernel:templateVersion "1.0.0" ;
    kernel:requiresParameter "subject" ;
    kernel:requiresParameter "target" ;
    kernel:sparqlTemplate """
        # Copy dynamic: runtime properties only
        SELECT ?predicate ?object WHERE {
            ?subject ?predicate ?object .

            # Only include dynamic properties
            ?predicate rdfs:subPropertyOf+ kernel:dynamicProperty .

            # Exclude deprecated dynamic properties
            FILTER NOT EXISTS {
                ?predicate kernel:deprecated true .
            }
        }
    """ .


# ============================================================================
# COPY VERB TEMPLATES - SHALLOW CARDINALITY
# ============================================================================

kernel:CopyShallowTemplate
    a kernel:ExecutionTemplate ;
    rdfs:label "Copy Shallow Template" ;
    rdfs:comment "Copies only direct properties (no recursion)" ;
    kernel:templateVersion "1.0.0" ;
    kernel:requiresParameter "subject" ;
    kernel:requiresParameter "target" ;
    kernel:sparqlTemplate """
        # Copy shallow: direct properties only (max depth 1)
        SELECT ?predicate ?object WHERE {
            ?subject ?predicate ?object .

            # Exclude type assertions
            FILTER(?predicate != rdf:type)

            # Only literal values or blank nodes (no deep traversal)
            FILTER(isLiteral(?object) || isBlank(?object))
        }
    """ .


# ============================================================================
# COPY VERB TEMPLATES - DEEP CARDINALITY
# ============================================================================

kernel:CopyDeepTemplate
    a kernel:ExecutionTemplate ;
    rdfs:label "Copy Deep Template" ;
    rdfs:comment "Copies properties recursively (follows object references)" ;
    kernel:templateVersion "1.0.0" ;
    kernel:requiresParameter "subject" ;
    kernel:requiresParameter "target" ;
    kernel:requiresParameter "maxDepth" ;
    kernel:sparqlTemplate """
        # Copy deep: recursive property traversal
        SELECT ?predicate ?object WHERE {
            {
                # Depth 0: direct properties
                ?subject ?predicate ?object .
            }
            UNION
            {
                # Depth 1+: recursive traversal via property paths
                ?subject ?p1 ?intermediate .
                ?intermediate ?predicate ?object .

                # Limit recursion depth (via maxDepth parameter)
                FILTER(?maxDepth > 1)
            }

            # Exclude metadata
            FILTER(?predicate NOT IN (
                kernel:createdAt,
                kernel:updatedAt,
                kernel:version
            ))
        }
    """ .


# ============================================================================
# PROPERTY CLASSIFICATION (used by templates)
# ============================================================================

kernel:structuralProperty
    a owl:ObjectProperty ;
    rdfs:label "structural property" ;
    rdfs:comment "Properties that define static structure/topology" .

kernel:dynamicProperty
    a owl:ObjectProperty ;
    rdfs:label "dynamic property" ;
    rdfs:comment "Properties that represent runtime state/behavior" .

kernel:flowsInto
    rdfs:subPropertyOf kernel:structuralProperty ;
    rdfs:label "flows into" ;
    rdfs:comment "Control flow edge in workflow topology" .

kernel:currentState
    rdfs:subPropertyOf kernel:dynamicProperty ;
    rdfs:label "current state" ;
    rdfs:comment "Current execution state (runtime property)" .


# ============================================================================
# EXAMPLE USAGE IN WORKFLOW SPECIFICATION
# ============================================================================

<http://example.org/workflow/task123>
    a kernel:Task ;
    kernel:flowsInto <http://example.org/workflow/task456> ;  # Structural
    kernel:currentState "enabled" ;  # Dynamic
    kernel:createdAt "2025-11-25T10:00:00Z"^^xsd:dateTime .  # Metadata
```

---

## How It Works: Execution Flow

```
1. User calls: copy(graph, subject, ctx, config)
   ├─ config.execution_template_uri = kernel:CopyTopologyTemplate
   └─ config.parameters = {"cardinality": "topology"}

2. Kernel.copy() retrieves template:
   ├─ Queries graph for kernel:sparqlTemplate property
   └─ Gets SPARQL string: "SELECT ?predicate ?object WHERE { ... }"

3. Kernel.copy() binds variables:
   ├─ ?subject = <http://example.org/workflow/task123>
   ├─ ?target = <http://example.org/workflow/task789>
   └─ Other context variables...

4. SPARQL engine executes template:
   ├─ Filters predicates based on SPARQL logic (NOT Python if/else)
   └─ Returns results: [(kernel:flowsInto, task456), ...]

5. Kernel.copy() converts to QuadDelta:
   └─ QuadDelta(additions=((subject, kernel:flowsInto, task456),))

6. Return QuadDelta to caller
```

**KEY**: Steps 1-6 contain ZERO Python if/else for parameter interpretation.

---

## Benefits

### 1. **Pure RDF-Driven Execution**
- ALL logic in SPARQL templates (ontology)
- Python code is pure: retrieve + execute
- No if/else in Kernel verbs

### 2. **Immutable Kernel**
- `Kernel.copy()` NEVER changes
- New cardinalities = new templates in ontology
- No Python code edits required

### 3. **Discoverable Behavior**
- `SELECT * WHERE { ?t a kernel:ExecutionTemplate }` → all behaviors
- Templates are first-class RDF entities
- Can query, version, deprecate templates

### 4. **Template Evolution**
```turtle
# V1: Simple topology copy
kernel:CopyTopologyTemplate_v1
    kernel:templateVersion "1.0.0" ;
    kernel:sparqlTemplate "SELECT ?p ?o WHERE { ?subject ?p ?o }" .

# V2: Exclude metadata (breaking change)
kernel:CopyTopologyTemplate_v2
    kernel:templateVersion "2.0.0" ;
    kernel:sparqlTemplate """
        SELECT ?p ?o WHERE {
            ?subject ?p ?o .
            FILTER(?p NOT IN (kernel:createdAt, kernel:updatedAt))
        }
    """ .

# V2.1: Add deprecation filter (patch)
kernel:CopyTopologyTemplate_v2_1
    kernel:templateVersion "2.1.0" ;
    kernel:sparqlTemplate """
        SELECT ?p ?o WHERE {
            ?subject ?p ?o .
            FILTER(?p NOT IN (kernel:createdAt, kernel:updatedAt))
            FILTER NOT EXISTS { ?p kernel:deprecated true . }
        }
    """ .
```

### 5. **SHACL Validation Integration**
```turtle
# Validate that CopyTopologyTemplate only returns structural properties
kernel:CopyTopologyShape
    a sh:NodeShape ;
    sh:targetClass kernel:CopyTopologyTemplate ;
    sh:sparql [
        sh:message "Template must only return structural properties" ;
        sh:select """
            SELECT $this WHERE {
                $this kernel:sparqlTemplate ?template .

                # Execute template and check results
                # (simplified - actual implementation would use SHACL-SPARQL validation)
                FILTER(regex(?template, "kernel:structuralProperty"))
            }
        """
    ] .
```

---

## Adding New Cardinality (NO Python Changes)

### Scenario: Add "security" cardinality

```turtle
# 1. Add template to ontology
kernel:CopySecurityTemplate
    a kernel:ExecutionTemplate ;
    rdfs:label "Copy Security Template" ;
    rdfs:comment "Copies only security-relevant properties" ;
    kernel:templateVersion "1.0.0" ;
    kernel:requiresParameter "subject" ;
    kernel:requiresParameter "target" ;
    kernel:sparqlTemplate """
        SELECT ?predicate ?object WHERE {
            ?subject ?predicate ?object .

            # Only security properties
            ?predicate rdfs:subPropertyOf+ kernel:securityProperty .
        }
    """ .

# 2. Classify security properties
kernel:securityProperty
    a owl:ObjectProperty ;
    rdfs:label "security property" .

kernel:hasPermission
    rdfs:subPropertyOf kernel:securityProperty .

kernel:accessControl
    rdfs:subPropertyOf kernel:securityProperty .

# 3. Use in VerbConfig (Python only changes config, NOT Kernel.copy())
config = VerbConfig(
    verb_uri=URIRef("http://kgcl.dev/ontology/kernel#Copy"),
    execution_template_uri=URIRef("http://kgcl.dev/ontology/kernel#CopySecurityTemplate"),
    parameters={"cardinality": "security"}
)

# 4. Execute (Kernel.copy() is unchanged!)
result = copy(graph, subject, ctx, config)
```

**ZERO Python changes to Kernel.copy().**

---

## Implementation Checklist

- [ ] Define `kernel:ExecutionTemplate` class in ontology
- [ ] Add `kernel:sparqlTemplate` property
- [ ] Create templates for existing cardinalities:
  - [ ] `kernel:CopyTopologyTemplate`
  - [ ] `kernel:CopyDynamicTemplate`
  - [ ] `kernel:CopyShallowTemplate`
  - [ ] `kernel:CopyDeepTemplate`
- [ ] Evolve `VerbConfig` dataclass with `execution_template_uri`
- [ ] Rewrite `Kernel.copy()` to retrieve + execute templates
- [ ] Add SHACL shapes to validate templates
- [ ] Update tests to use template-based execution
- [ ] Document pattern in `docs/KERNEL_ARCHITECTURE.md`

---

## Comparison: Before vs After

| Aspect | BEFORE (Impure) | AFTER (Pure) |
|--------|----------------|--------------|
| **Logic location** | Python if/else | SPARQL templates in ontology |
| **Kernel mutability** | Must edit Python for new cardinality | Kernel never changes |
| **Discoverability** | Must read Python code | Query ontology for templates |
| **Versioning** | Git commits | Semantic versioning in RDF |
| **Validation** | Unit tests only | SHACL shapes + unit tests |
| **Parameter interpretation** | Python conditionals | Variable binding in SPARQL |
| **Business logic** | Hardcoded in Python | Declarative in RDF |

---

## Architectural Guarantee

**THE KERNEL IS IMMUTABLE.**

Once `Kernel.copy()` is implemented with template retrieval, it NEVER changes. All new behaviors are added to the ontology as new `kernel:ExecutionTemplate` instances.

This is the **Semantic Singularity**: Validation (SHACL shapes) and Execution (SPARQL templates) are both RDF-native. Python is just the VM.

---

## Next Steps

1. **Implement in `examples/`**: Create single-file POC demonstrating pattern
2. **Port to `src/kgcl/kernel/`**: Replace existing Kernel verbs with template-based execution
3. **Expand to all verbs**: Apply pattern to `transmute`, `filter`, `await`, `void`
4. **Add SHACL validation**: Create shapes that validate template correctness
5. **Document**: Update `docs/KERNEL_ARCHITECTURE.md` with this pattern

---

**Report completed. Pattern ready for implementation.**
