# KGCL System Architecture

## Table of Contents

- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Module Organization](#module-organization)
- [Interface Definitions](#interface-definitions)
- [Layer Architecture](#layer-architecture)
- [Dependency Graph](#dependency-graph)
- [Design Patterns](#design-patterns)
- [Performance Characteristics](#performance-characteristics)

## Overview

KGCL (Knowledge Geometry Calculus for Life) is an OS Graph Agent system that collects macOS events, stores them in an RDF knowledge graph, materializes features, and generates natural language insights using DSPy reasoning.

### System Purpose

The system enables:
- **Automated OS Event Collection**: PyObjC-based collectors capture app usage, browser history, calendar events
- **Knowledge Graph Storage**: RDF triple store with SPARQL queries, transactions, and provenance
- **Feature Materialization**: Transform raw events into meaningful temporal features
- **LLM Reasoning**: DSPy signatures generate daily briefs and weekly retrospectives
- **Observability**: OpenTelemetry instrumentation across all components

### Key Design Principles

1. **Separation of Concerns**: Each subsystem has clear boundaries
2. **Data Provenance**: Full lineage tracking from events to insights
3. **Extensibility**: Plugin-based architecture for collectors and features
4. **Privacy-First**: Local-only processing, configurable exclusions
5. **Observable**: OpenTelemetry traces, metrics, and structured logging

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         KGCL System                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌──────────────┐   │
│  │  PyObjC     │─────▶│   UNRDF     │─────▶│  TTL2DSPy    │   │
│  │  Agent      │      │   Engine    │      │  Generator   │   │
│  │             │      │             │      │              │   │
│  │ - AppKit    │      │ - RDF Store │      │ - Parser     │   │
│  │ - WebKit    │      │ - SPARQL    │      │ - CodeGen    │   │
│  │ - EventKit  │      │ - Provenance│      │              │   │
│  └─────────────┘      └─────────────┘      └──────────────┘   │
│        │                     │                     │           │
│        │                     │                     │           │
│        ▼                     ▼                     ▼           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Ingestion & Materialization                │  │
│  │  - Event Collectors                                     │  │
│  │  - RDF Converters                                       │  │
│  │  - Feature Templates                                    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │               DSPy Runtime Bridge                       │  │
│  │  - Signature Invoker                                    │  │
│  │  - Receipt Generator                                    │  │
│  │  - Ollama Integration                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    CLI Layer                            │  │
│  │  - Daily Brief    - Weekly Retro    - Query            │  │
│  │  - Feature List   - Config                             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            Observability (OpenTelemetry)                │  │
│  │  - Tracing    - Metrics    - Logging    - Health       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. PyObjC Agent

**Location**: `src/kgcl/pyobjc_agent/`

**Purpose**: Discover and collect macOS system events using PyObjC frameworks.

```
pyobjc_agent/
├── crawler.py           # Framework capability discovery
├── agent.py             # Main agent orchestrator
├── collectors/          # Event collection plugins
│   ├── base.py          # Base collector interface
│   ├── frontmost_app_collector.py
│   ├── browser_history_collector.py
│   └── calendar_collector.py
├── plugins/             # Framework-specific plugins
│   ├── base.py
│   ├── appkit_plugin.py
│   ├── webkit_plugin.py
│   ├── browser_plugin.py
│   └── calendar_plugin.py
└── aggregators.py       # Event aggregation logic
```

**Key Responsibilities**:
- Load PyObjC frameworks dynamically (AppKit, WebKit, EventKit, etc.)
- Enumerate classes, protocols, and methods
- Filter for observable/queryable state methods
- Collect events at configured intervals
- Generate JSON-LD capability metadata

**Interfaces**:
```python
class Collector(ABC):
    @abstractmethod
    async def collect(self) -> List[Event]:
        """Collect events from the system."""

class Plugin(ABC):
    @abstractmethod
    def discover_capabilities(self) -> List[Capability]:
        """Discover available capabilities."""
```

### 2. UNRDF Engine

**Location**: `src/kgcl/unrdf_engine/`

**Purpose**: RDF triple store with SPARQL, transactions, and provenance tracking.

```
unrdf_engine/
├── engine.py            # Core RDF graph operations
├── ingestion.py         # Event-to-RDF ingestion
├── hooks.py             # Pre/post-operation hooks
├── validation.py        # SHACL validation
├── externals.py         # External capability interface
├── cli.py               # CLI commands
└── server.py            # Flask HTTP API
```

**Key Responsibilities**:
- In-memory RDF graph with file-backed persistence (Turtle format)
- SPARQL 1.1 query support
- Transaction support with rollback capability
- Full provenance tracking (who/when/why for each triple)
- SHACL validation
- External capability interface for extensions

**Core Classes**:
```python
class UnrdfEngine:
    """RDF triple store with SPARQL, transactions, and provenance."""

    def transaction(agent: str, reason: str) -> Transaction
    def add_triple(subject, predicate, obj, transaction) -> None
    def query(sparql: str) -> Result
    def get_provenance(subject, predicate, obj) -> ProvenanceRecord

class Transaction:
    """Transaction context for atomic RDF operations."""
    transaction_id: str
    added_triples: List[Triple]
    removed_triples: List[Triple]
    provenance: ProvenanceRecord
```

### 3. Ingestion System

**Location**: `src/kgcl/ingestion/`

**Purpose**: Transform events into RDF and materialize features.

```
ingestion/
├── config.py            # Configuration management
├── models.py            # Event and feature models
├── converters.py        # JSON-to-RDF conversion
├── materializer.py      # Feature materialization
├── service.py           # Ingestion service orchestrator
└── collectors/
    ├── base.py          # Base collector interface
    └── batch.py         # Batch processing
```

**Key Responsibilities**:
- Convert JSON-LD events to RDF triples
- Validate against SHACL shapes
- Materialize features from raw events
- Batch processing for performance
- Transaction management

**Pipeline**:
```
JSON Events → Converters → RDF Triples → Validation → UNRDF Engine
                                            ↓
                                    Feature Templates
                                            ↓
                                    Materialized Features
```

### 4. TTL2DSPy

**Location**: `src/kgcl/ttl2dspy/`

**Purpose**: Generate DSPy signatures from SHACL/Turtle ontologies.

```
ttl2dspy/
├── parser.py            # Parse SHACL shapes
├── generator.py         # Generate DSPy signature code
├── writer.py            # Write Python modules
├── ultra.py             # Caching and optimization
├── hooks.py             # UNRDF integration hooks
└── cli.py               # CLI interface
```

**Key Responsibilities**:
- Parse Turtle/SHACL ontologies
- Identify input/output properties
- Generate DSPy Signature classes
- Write Python modules with imports
- Cache parsing and generation
- Provide UNRDF hook interface

**Generation Flow**:
```
SHACL Shape → Parser → PropertyShapes → Generator → SignatureDefinition → Python Code
                            ↓
                     Categorization
                     (input vs output)
```

### 5. DSPy Runtime

**Location**: `src/kgcl/dspy_runtime/`

**Purpose**: Execute DSPy signatures with Ollama and generate receipts.

```
dspy_runtime/
├── ollama_config.py     # Ollama LM configuration
├── invoker.py           # Signature invocation
├── receipts.py          # Receipt generation and storage
├── unrdf_bridge.py      # UNRDF integration
└── __main__.py          # CLI entry point
```

**Key Responsibilities**:
- Configure Ollama LM for DSPy
- Dynamically load and invoke DSPy signatures
- Track invocation metrics (latency, tokens, model)
- Generate RDF receipts with provenance
- Store receipts in RDF graph
- Provide batch invocation support

**Invocation Flow**:
```
Feature Data → UNRDF Bridge → Signature Invoker → DSPy Predict → LLM
                                                        ↓
                                                   Completion
                                                        ↓
                                              Receipt Generator
                                                        ↓
                                                 RDF Receipt
                                                        ↓
                                                  UNRDF Store
```

### 6. CLI Layer

**Location**: `src/kgcl/cli/`

**Purpose**: User-facing command-line interface.

```
cli/
├── daily_brief.py       # Generate daily briefs
├── weekly_retro.py      # Generate weekly retrospectives
├── feature_list.py      # Browse and explore features
├── query.py             # Execute SPARQL queries
├── config.py            # Manage configuration
└── utils.py             # Shared utilities
```

**Key Responsibilities**:
- Orchestrate end-to-end workflows
- Query UNRDF for feature data
- Invoke DSPy signatures via bridge
- Format and output results
- Manage user configuration
- Provide rich CLI experience

**Commands**:
```bash
kgc-daily-brief     # Generate daily brief
kgc-weekly-retro    # Generate weekly retrospective
kgc-feature-list    # List and explore features
kgc-query           # Execute SPARQL queries
kgc-config          # Manage configuration
kgc-health          # Check system health
```

### 7. Observability

**Location**: `src/kgcl/observability/`

**Purpose**: OpenTelemetry instrumentation across all components.

```
observability/
├── config.py            # Observability configuration
├── tracing.py           # Trace configuration
├── metrics.py           # Metrics configuration
├── logging.py           # Structured logging
├── health.py            # Health checks
├── cli.py               # Observability CLI
└── instruments/
    ├── pyobjc_agent.py
    ├── unrdf_engine.py
    ├── ttl2dspy.py
    └── dspy_runtime.py
```

**Key Responsibilities**:
- Configure OpenTelemetry SDK
- Instrument all major operations
- Export traces to OTLP/Jaeger/Zipkin
- Collect and export metrics
- Structured logging with context
- Health checks and diagnostics

## Data Flow

### End-to-End Event Processing

```
┌────────────────┐
│   macOS APIs   │
│  (PyObjC)      │
└────────┬───────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 1: Event Collection                            │
│  - PyObjC collectors poll system state                │
│  - Generate JSON-LD events                            │
│  - Batch and buffer events                            │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 2: Ingestion                                   │
│  - Convert JSON-LD to RDF triples                     │
│  - Validate against SHACL shapes                      │
│  - Create transaction                                 │
│  - Add triples to UNRDF engine                        │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 3: Storage                                     │
│  - UNRDF engine stores triples                        │
│  - Add provenance metadata                            │
│  - Commit transaction                                 │
│  - Persist to Turtle file                             │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 4: Feature Materialization                     │
│  - Query raw events via SPARQL                        │
│  - Apply feature templates                            │
│  - Compute aggregations (time windows)                │
│  - Store feature instances                            │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 5: Reasoning                                   │
│  - Query features via SPARQL                          │
│  - Load DSPy signature                                │
│  - Invoke with Ollama LM                              │
│  - Generate natural language output                   │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 6: Receipt Generation                          │
│  - Create receipt with provenance                     │
│  - Link to source features                            │
│  - Link to signature definition                       │
│  - Store receipt in UNRDF                             │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────┐
│   User Output  │
│  (CLI/API)     │
└────────────────┘
```

### Example: Daily Brief Generation

```
1. User invokes: kgc-daily-brief --date 2024-01-15

2. CLI queries UNRDF for features:
   SPARQL: SELECT ?feature WHERE {
     ?feature kgcl:date "2024-01-15" .
     ?feature a kgcl:FeatureInstance .
   }

3. Feature results:
   - app_usage_time: {"Chrome": 180, "VSCode": 120}
   - browser_domains: {"github.com": 50, "stackoverflow.com": 20}
   - meeting_count: 3
   - context_switches: 45

4. CLI loads DSPy signature:
   from generated.signatures import DailyBriefSignature

5. CLI invokes via UNRDF Bridge:
   bridge.invoke(
     module_path="generated.signatures",
     signature_name="DailyBriefSignature",
     inputs={
       "date": "2024-01-15",
       "app_usage": {...},
       "browser_domains": {...},
       "meetings": 3,
       "context_switches": 45
     }
   )

6. DSPy Runtime:
   - Configures Ollama LM
   - Creates Predict module
   - Invokes LLM with formatted prompt
   - Parses completion into output fields

7. Receipt Generation:
   - receipt:r-abc123 rdf:type kgcl:Receipt
   - receipt:r-abc123 kgcl:signature "DailyBriefSignature"
   - receipt:r-abc123 kgcl:sourceFeature feature:f-xyz
   - receipt:r-abc123 kgcl:output "Your day focused on..."

8. Output to user:
   # Daily Brief for 2024-01-15

   Your day focused on software development...
```

## Module Organization

### Package Structure

```
kgcl/
├── __init__.py
├── pyobjc_agent/           # macOS event collection
│   ├── __init__.py
│   ├── agent.py
│   ├── crawler.py
│   ├── aggregators.py
│   ├── collectors/
│   └── plugins/
├── unrdf_engine/           # RDF triple store
│   ├── __init__.py
│   ├── engine.py
│   ├── ingestion.py
│   ├── hooks.py
│   ├── validation.py
│   ├── externals.py
│   ├── cli.py
│   └── server.py
├── ingestion/              # Event-to-RDF ingestion
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── converters.py
│   ├── materializer.py
│   ├── service.py
│   └── collectors/
├── ttl2dspy/               # DSPy signature generation
│   ├── __init__.py
│   ├── parser.py
│   ├── generator.py
│   ├── writer.py
│   ├── ultra.py
│   ├── hooks.py
│   └── cli.py
├── dspy_runtime/           # DSPy execution
│   ├── __init__.py
│   ├── ollama_config.py
│   ├── invoker.py
│   ├── receipts.py
│   └── unrdf_bridge.py
├── cli/                    # CLI commands
│   ├── __init__.py
│   ├── daily_brief.py
│   ├── weekly_retro.py
│   ├── feature_list.py
│   ├── query.py
│   ├── config.py
│   └── utils.py
├── observability/          # OpenTelemetry
│   ├── __init__.py
│   ├── config.py
│   ├── tracing.py
│   ├── metrics.py
│   ├── logging.py
│   ├── health.py
│   ├── cli.py
│   └── instruments/
└── ontology/               # RDF ontologies
    └── __init__.py
```

### Subsystem Dependencies

```
CLI Layer
  ↓
DSPy Runtime ←→ UNRDF Engine ←→ Ingestion
  ↓                  ↓              ↓
TTL2DSPy         Validation    PyObjC Agent
                     ↓
                Observability (cross-cutting)
```

## Interface Definitions

### 1. JSON-LD Event Schema

Events use JSON-LD format with context:

```json
{
  "@context": {
    "@vocab": "http://kgcl.io/ontology#",
    "timestamp": {
      "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
    }
  },
  "@type": "AppUsageEvent",
  "@id": "event:e-12345",
  "timestamp": "2024-01-15T10:30:00Z",
  "bundleId": "com.google.Chrome",
  "appName": "Chrome",
  "duration": 180,
  "url": "https://github.com",
  "title": "GitHub Repository"
}
```

### 2. RDF Triple Format

Stored in UNRDF as triples:

```turtle
@prefix kgcl: <http://kgcl.io/ontology#> .
@prefix event: <http://kgcl.io/events#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

event:e-12345
  a kgcl:AppUsageEvent ;
  kgcl:timestamp "2024-01-15T10:30:00Z"^^xsd:dateTime ;
  kgcl:bundleId "com.google.Chrome" ;
  kgcl:appName "Chrome" ;
  kgcl:duration 180 ;
  kgcl:url "https://github.com" ;
  kgcl:title "GitHub Repository" ;
  prov:generatedBy agent:pyobjc ;
  prov:generatedAtTime "2024-01-15T10:30:05Z"^^xsd:dateTime .
```

### 3. Feature Template Schema (SHACL)

Define features using SHACL:

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix kgcl: <http://kgcl.io/ontology#> .

kgcl:AppUsageTimeShape
  a sh:NodeShape ;
  rdfs:comment "Total time spent per application in a time window" ;
  sh:targetClass kgcl:AppUsageTimeFeature ;
  sh:property [
    sh:path kgcl:appName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:totalSeconds ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:windowStart ;
    sh:datatype xsd:dateTime ;
  ] ;
  sh:property [
    sh:path kgcl:windowEnd ;
    sh:datatype xsd:dateTime ;
  ] .
```

### 4. DSPy Signature Interface

Generated from SHACL:

```python
class DailyBriefSignature(dspy.Signature):
    """Generate a daily brief from activity features."""

    # Input fields
    date: str = dspy.InputField(desc="Date for the brief")
    app_usage: str = dspy.InputField(desc="Application usage summary")
    browser_domains: str = dspy.InputField(desc="Browser domains visited")
    meetings: int = dspy.InputField(desc="Number of meetings")
    context_switches: int = dspy.InputField(desc="Context switch count")

    # Output fields
    brief: str = dspy.OutputField(desc="Natural language daily brief")
    productivity_score: int = dspy.OutputField(desc="Productivity score 1-10")
    recommendations: str = dspy.OutputField(desc="Recommendations for tomorrow")
```

### 5. Receipt RDF Schema

Provenance tracking:

```turtle
@prefix receipt: <http://kgcl.io/receipts#> .
@prefix sig: <http://kgcl.io/signatures#> .
@prefix feature: <http://kgcl.io/features#> .

receipt:r-abc123
  a kgcl:Receipt ;
  kgcl:signature sig:DailyBriefSignature ;
  kgcl:model "llama3.3:latest" ;
  kgcl:latency 2.5 ;
  kgcl:success true ;
  kgcl:timestamp "2024-01-15T11:00:00Z"^^xsd:dateTime ;
  kgcl:sourceFeature feature:f-app-usage-001 ;
  kgcl:sourceFeature feature:f-browser-001 ;
  kgcl:input "date: 2024-01-15, app_usage: {...}" ;
  kgcl:output "Your day focused on software development..." .
```

### 6. Python API

Core API patterns:

```python
# UNRDF Engine
from kgcl.unrdf_engine import UnrdfEngine

engine = UnrdfEngine(file_path="data/knowledge.ttl")
with engine.transaction("agent", "reason") as txn:
    engine.add_triple(subject, predicate, obj, txn)
    engine.commit(txn)
results = engine.query("SELECT * WHERE { ?s ?p ?o }")

# DSPy Runtime
from kgcl.dspy_runtime import UNRDFBridge

bridge = UNRDFBridge()
bridge.initialize()
result = bridge.invoke(
    module_path="signatures.py",
    signature_name="DailyBriefSignature",
    inputs={"date": "2024-01-15", ...},
    source_features=["feature:f-001"]
)

# TTL2DSPy
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter

optimizer = UltraOptimizer()
shapes = optimizer.parse_with_cache("ontology.ttl")
code = optimizer.generate_with_cache(shapes)
writer = ModuleWriter()
writer.write_module(code, "signatures.py")
```

## Layer Architecture

### Layer 1: Data Collection

**Responsibility**: Gather raw events from macOS

**Components**:
- PyObjC Agent
- Event Collectors
- Plugins

**Output**: JSON-LD events

**Characteristics**:
- Poll-based collection (1-300 second intervals)
- Buffered and batched writes
- Error recovery and retries
- Privacy filtering

### Layer 2: Storage

**Responsibility**: Persist events as RDF triples

**Components**:
- UNRDF Engine
- Ingestion System
- Converters

**Output**: RDF triples in graph

**Characteristics**:
- ACID transactions
- Provenance tracking
- File-backed persistence
- SPARQL 1.1 queries

### Layer 3: Reasoning

**Responsibility**: Generate insights from features

**Components**:
- DSPy Runtime
- TTL2DSPy
- Feature Templates

**Output**: Natural language insights

**Characteristics**:
- LLM-based reasoning
- Template-driven feature extraction
- Receipt generation
- Batch processing

### Layer 4: User Interface

**Responsibility**: Provide access to insights

**Components**:
- CLI Commands
- HTTP API (optional)
- Configuration

**Output**: Formatted output

**Characteristics**:
- Multiple output formats (JSON, Markdown, CSV)
- Rich terminal UI
- Clipboard integration
- Configuration management

## Dependency Graph

### Build-time Dependencies

```
pyproject.toml
  ├── rdflib (>=7.0.0)           # RDF graph operations
  ├── pyshacl (>=0.25.0)         # SHACL validation
  ├── dspy-ai (>=2.4.0)          # DSPy signatures
  ├── pydantic (>=2.5.0)         # Configuration validation
  ├── click (>=8.1.7)            # CLI framework
  ├── rich (>=13.7.0)            # Terminal UI
  ├── flask (>=3.0.0)            # HTTP API
  ├── opentelemetry-api          # Tracing API
  ├── opentelemetry-sdk          # Tracing SDK
  └── opentelemetry-exporter-otlp # OTLP exporter
```

### Runtime Dependencies

```
External Services (Optional):
  ├── Ollama                    # Local LLM (required for reasoning)
  ├── OTLP Collector            # Trace collection
  ├── Jaeger/Zipkin             # Trace visualization
  └── Prometheus/Grafana        # Metrics visualization

macOS Frameworks (via PyObjC):
  ├── AppKit                    # Application events
  ├── WebKit                    # Browser history
  ├── EventKit                  # Calendar events
  ├── Foundation                # Core types
  └── CoreLocation              # Location (future)
```

### Internal Dependencies

```
kgcl.cli
  ├── kgcl.dspy_runtime
  │   ├── kgcl.ttl2dspy
  │   └── dspy-ai
  ├── kgcl.unrdf_engine
  │   ├── rdflib
  │   └── pyshacl
  └── kgcl.observability

kgcl.ingestion
  ├── kgcl.unrdf_engine
  └── kgcl.pyobjc_agent

kgcl.pyobjc_agent
  └── PyObjC frameworks

kgcl.observability
  └── opentelemetry-*
```

## Design Patterns

### 1. Repository Pattern

UNRDF Engine abstracts RDF storage:

```python
class UnrdfEngine:
    """Repository for RDF triples."""

    def add_triple(self, s, p, o, txn):
        """Add to repository."""

    def query(self, sparql):
        """Query repository."""

    def transaction(self, agent, reason):
        """Transaction context."""
```

### 2. Strategy Pattern

Collectors use strategy pattern:

```python
class Collector(ABC):
    @abstractmethod
    async def collect(self) -> List[Event]:
        """Collection strategy."""

class FrontmostAppCollector(Collector):
    async def collect(self):
        # AppKit-based collection

class BrowserHistoryCollector(Collector):
    async def collect(self):
        # WebKit-based collection
```

### 3. Bridge Pattern

UNRDF Bridge decouples DSPy from storage:

```python
class UNRDFBridge:
    """Bridge between UNRDF and DSPy runtime."""

    def invoke(self, signature, inputs):
        result = self.invoker.invoke(signature, inputs)
        receipt = self.receipt_generator.generate(result)
        self.store_receipt(receipt)
        return result
```

### 4. Template Method Pattern

Feature materialization:

```python
class FeatureMaterializer:
    def materialize(self, template):
        events = self.query_events(template)
        features = self.compute_features(events, template)
        self.store_features(features)
```

### 5. Observer Pattern

Hooks for extensibility:

```python
class HookManager:
    def register_hook(self, event, callback):
        self.hooks[event].append(callback)

    def trigger(self, event, context):
        for callback in self.hooks[event]:
            callback(context)
```

## Performance Characteristics

### UNRDF Engine

| Operation | Complexity | Performance |
|-----------|------------|-------------|
| Add triple | O(1) | < 1ms |
| SPARQL query | O(n) | 10-100ms (1K-100K triples) |
| Transaction commit | O(m) | m = triples in txn |
| File persistence | O(n) | Linear in graph size |
| Provenance lookup | O(1) | HashMap lookup |

**Scalability**:
- Tested up to 1M triples in memory
- Query performance degrades linearly
- Consider external triple store (Fuseki) for >10M triples

### Event Collection

| Collector | Interval | Batch Size | Latency |
|-----------|----------|------------|---------|
| Frontmost App | 1s | 50 events | < 10ms |
| Browser History | 5min | 10 events | 100-500ms |
| Calendar | 5min | 10 events | 50-200ms |

**Throughput**:
- ~3,600 events/hour (frontmost app)
- ~12 events/hour (browser)
- ~12 events/hour (calendar)
- Total: ~3,600 events/hour sustained

### DSPy Runtime

| Operation | Latency | Notes |
|-----------|---------|-------|
| Signature load | 10-50ms | Cached after first load |
| Ollama invoke (llama3.3) | 1-5s | Depends on prompt length |
| Receipt generation | < 10ms | RDF serialization |

**Optimization**:
- Signature caching reduces load time by 90%
- Batch invocation reduces overhead
- Ollama keep-alive reduces cold start

### TTL2DSPy

| Operation | Input Size | Time | Cache Hit |
|-----------|------------|------|-----------|
| Parse ontology | 100 shapes | 500ms | 5ms |
| Generate code | 100 shapes | 200ms | 2ms |
| Write module | 100 shapes | 50ms | N/A |

**Caching Strategy**:
- Memory cache: 99% hit rate for repeated operations
- Disk cache: Persistent across runs
- Redis cache: Shared across processes

### Memory Usage

| Component | Idle | Active (1 day) | Active (1 week) |
|-----------|------|----------------|-----------------|
| UNRDF Engine | 50 MB | 200 MB | 500 MB |
| PyObjC Agent | 30 MB | 50 MB | 50 MB |
| DSPy Runtime | 20 MB | 100 MB | 100 MB |
| Total | 100 MB | 350 MB | 650 MB |

**Growth Rate**:
- ~100 MB/day for typical usage
- Garbage collection recommended weekly
- Archive old data for long-term storage

### Disk Usage

| Component | Size (1 day) | Size (1 week) | Size (1 month) |
|-----------|--------------|---------------|----------------|
| Event logs | 10 MB | 70 MB | 300 MB |
| RDF graph | 20 MB | 140 MB | 600 MB |
| Receipts | 5 MB | 35 MB | 150 MB |
| Total | 35 MB | 245 MB | 1.05 GB |

**Compression**:
- Turtle format: ~2x more compact than JSON-LD
- GZIP compression: Additional 3-5x reduction
- Recommended: Archive monthly data with compression

## Observability Integration

### Trace Hierarchy

```
kgc-daily-brief
  ├── unrdf.query (fetch features)
  ├── unrdf.bridge.invoke
  │   ├── dspy.signature.load
  │   ├── ollama.predict
  │   │   └── http.post (Ollama API)
  │   └── receipt.generate
  │       └── unrdf.add_triple
  └── cli.format_output
```

### Key Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| `kgcl.events.collected` | Counter | Events collected |
| `kgcl.triples.stored` | Counter | RDF triples stored |
| `kgcl.queries.executed` | Counter | SPARQL queries |
| `kgcl.signatures.invoked` | Counter | DSPy invocations |
| `kgcl.ollama.latency` | Histogram | LLM latency |
| `kgcl.features.materialized` | Counter | Features created |

### Health Checks

Available via `kgc-health`:

```bash
kgc-health check
# ✓ UNRDF Engine: 250K triples, 50 queries/min
# ✓ Ollama: llama3.3:latest available
# ✓ PyObjC Agent: 3 collectors active
# ✗ OTLP Exporter: Connection refused
```

## Future Enhancements

### Planned Features

1. **Distributed Triple Store**: Integrate with Apache Fuseki for scalability
2. **Real-time Streaming**: WebSocket API for live event streaming
3. **Multi-user Support**: Isolation and access control
4. **Advanced Analytics**: Statistical analysis and anomaly detection
5. **Mobile Integration**: iOS companion app via shared iCloud knowledge graph

### Architecture Evolution

```
Current: Single-node, in-memory RDF
  ↓
Phase 2: External triple store (Fuseki)
  ↓
Phase 3: Distributed processing (Spark)
  ↓
Phase 4: Multi-tenant cloud deployment
```

## References

- [UNRDF Engine Documentation](./API_REFERENCE.md#unrdf-engine)
- [DSPy Runtime Guide](./REASONING_PIPELINE.md)
- [TTL2DSPy Integration](./ttl2dspy-integration.md)
- [Observability Guide](./OBSERVABILITY_GUIDE.md)
- [Performance Tuning](./TROUBLESHOOTING.md#performance)
