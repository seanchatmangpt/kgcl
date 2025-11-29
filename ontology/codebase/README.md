# YAWL Java Codebase Ontology

This directory contains the Java codebase structure extracted from the YAWL Java implementation, organized as a knowledge graph.

## Overview

The codebase ontology is a code-centric representation of the YAWL Java source code, containing:
- **863 Java classes** across **133 packages**
- Class definitions with methods, fields, inheritance, and implementations
- Package structure mirroring the original Java organization

This is separate from the domain-centric ontologies in `core/` (which define workflow concepts) - this directory represents the actual implementation structure.

## Structure

```
codebase/
├── yawl-java-schema.ttl     # Meta-model: defines yawl:Package, yawl:Class, yawl:Method, yawl:Field
└── org/
    └── yawlfoundation/
        └── yawl/
            ├── controlpanel/
            │   ├── YControlPanel.ttl
            │   └── YControlPanelBootstrap.ttl
            ├── monitor/
            │   ├── MonitorServlet.ttl
            │   └── MonitorClient.ttl
            ├── util/
            │   ├── HttpURLValidator.ttl
            │   ├── OnlineChecker.ttl
            │   └── ...
            └── ...
```

## Schema

The `yawl-java-schema.ttl` file defines the meta-model:

- **Classes**: `yawl:Package`, `yawl:Class`, `yawl:Method`, `yawl:Field`
- **Properties**:
  - `yawl:inPackage` - Class belongs to package
  - `yawl:hasMethod` - Class has method
  - `yawl:hasField` - Class has field
  - `yawl:extends` - Class inheritance
  - `yawl:implements` - Interface implementation
  - `yawl:filePath` - Source file path
  - `yawl:signature` - Method signature
  - `yawl:returnType` - Method return type
  - `yawl:modifiers` - Access modifiers (public, private, static, etc.)

## Class Files

Each Java class is represented as a separate `.ttl` file in the directory structure matching its package:

- **Location**: `codebase/org/yawlfoundation/yawl/package/ClassName.ttl`
- **Content**: Class definition, all methods, all fields, package reference
- **Format**: Standard Turtle with RDF prefixes

Example (`YControlPanel.ttl`):
```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# Package: org.yawlfoundation.yawl.controlpanel
yawl:org_yawlfoundation_yawl_controlpanel a yawl:Package ;
    rdfs:label "org.yawlfoundation.yawl.controlpanel" .

# Class: org.yawlfoundation.yawl.controlpanel.YControlPanel
yawl:YControlPanel a yawl:Class ;
    rdfs:label "YControlPanel" ;
    yawl:inPackage yawl:org_yawlfoundation_yawl_controlpanel ;
    yawl:filePath "vendors/yawl-v5.2/src/..."^^xsd:string ;
    yawl:extends yawl:JFrame ;
    yawl:hasMethod yawl:YControlPanel_main_1 ;
    .
```

## Usage

### Loading Individual Class

```python
from rdflib import Graph
from pathlib import Path

g = Graph()
class_file = Path("ontology/codebase/org/yawlfoundation/yawl/controlpanel/YControlPanel.ttl")
g.parse(str(class_file), format="turtle")
```

### Loading Entire Codebase

```python
from rdflib import Graph
from pathlib import Path

g = Graph()

# Load schema first
schema_file = Path("ontology/codebase/yawl-java-schema.ttl")
g.parse(str(schema_file), format="turtle")

# Load all class files
codebase_dir = Path("ontology/codebase")
for ttl_file in codebase_dir.rglob("*.ttl"):
    if ttl_file.name != "yawl-java-schema.ttl":
        g.parse(str(ttl_file), format="turtle")
```

### Querying Classes

```python
from rdflib import Graph, Namespace

g = Graph()
# ... load ontology ...

YAWL = Namespace("http://yawlfoundation.org/ontology/")

# Find all classes in a package
for class_uri in g.subjects(YAWL.inPackage, YAWL.org_yawlfoundation_yawl_controlpanel):
    print(f"Class: {g.value(class_uri, None, None)}")

# Find all methods of a class
for method_uri in g.objects(YAWL.YControlPanel, YAWL.hasMethod):
    signature = g.value(method_uri, YAWL.signature, None)
    print(f"Method: {signature}")
```

## Generation

This directory structure is generated from the monolithic `docs/yawl_full_ontology.ttl` file using:

```bash
uv run python scripts/split_yawl_ontology.py \
    --input docs/yawl_full_ontology.ttl \
    --output ontology/codebase
```

The script:
1. Extracts schema definitions to `yawl-java-schema.ttl`
2. Parses class blocks from the monolithic file
3. Creates directory structure matching Java packages
4. Writes individual class files with proper prefixes

## Relationship to Core Ontologies

- **`core/yawl.ttl`**: Domain-centric YAWL workflow vocabulary (tasks, conditions, flows)
- **`codebase/`**: Code-centric Java implementation structure (classes, methods, packages)

These serve different purposes:
- `core/` defines **what** YAWL workflows are (domain concepts)
- `codebase/` defines **how** YAWL is implemented (code structure)

## Statistics

- **Total classes**: 863
- **Total packages**: 133
- **Schema lines**: ~55 (meta-model definitions)
- **Total triples**: ~163,000+ (preserved from original file)

## Indexing

The codebase ontology includes a comprehensive RDF index for fast lookups and navigation:

- **`index.ttl`** - Main index file with all lookup structures
- **`index-schema.ttl`** - Index ontology schema definitions
- **`queries.sparql`** - Pre-defined SPARQL query templates

### Building the Index

```bash
uv run python scripts/build_codebase_index.py \
    --codebase-dir ontology/codebase \
    --output ontology/codebase/index.ttl
```

### Using the Index

```python
from kgcl.ontology.codebase_index import CodebaseIndex

index = CodebaseIndex("ontology/codebase/index.ttl")

# Find class by name
class_info = index.find_class("YControlPanel")

# Find all classes in package
classes = index.find_classes_in_package("org.yawlfoundation.yawl.controlpanel")

# Get inheritance hierarchy
hierarchy = index.get_inheritance_hierarchy("JMXMemoryStatistics")

# Find classes with method
classes = index.find_classes_with_method("toString")

# Full-text search
results = index.search("memory statistics")
```

See `src/kgcl/ontology/codebase_index.py` for the complete API.

## See Also

- `scripts/split_yawl_ontology.py` - Script used to generate this structure
- `scripts/build_codebase_index.py` - Script used to build the index
- `tests/scripts/test_split_yawl_ontology.py` - Test suite for the splitter
- `tests/ontology/test_codebase_index.py` - Test suite for the index
- `ontology/core/yawl.ttl` - Domain-centric YAWL vocabulary
- `docs/yawl_full_ontology.ttl` - Original monolithic file (163K+ lines)

