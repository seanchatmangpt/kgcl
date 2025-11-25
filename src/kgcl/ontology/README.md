# KGC OS Graph Agent Ontology

Complete RDF/SHACL ontology for the Knowledge Graph Comprehension OS Graph Agent system.

## Overview

This ontology models the complete lifecycle of behavioral feature extraction from macOS system interactions:

1. **Capabilities** - Atomic system operations discovered via PyObjC framework introspection
2. **Feature Templates** - Reusable definitions for computing behavioral features from observations
3. **Feature Instances** - Concrete feature values computed over temporal windows
4. **Observations** - Raw data points collected from system monitoring
5. **Events** - Significant occurrences detected through pattern matching

## Files

### Core Ontology Files

- **`core.ttl`** - Main ontology defining all classes, properties, and relationships
- **`shapes.ttl`** - SHACL validation shapes ensuring data quality and consistency
- **`features.ttl`** - Catalog of feature templates with examples (timeInApp, switchCount, etc.)
- **`capabilities.ttl`** - Registry of macOS capabilities with PyObjC bindings and SLOs

### Supporting Files

- **`examples.ttl`** - Instance data examples demonstrating usage patterns
- **`README.md`** - This documentation file

## Namespace Prefixes

```turtle
@prefix : <http://kgcl.dev/ontology/core#> .
@prefix shapes: <http://kgcl.dev/ontology/shapes#> .
@prefix ft: <http://kgcl.dev/ontology/features#> .
@prefix cap: <http://kgcl.dev/ontology/capabilities#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
```

## Class Hierarchy

### Top-Level Organization

```
:Entity (abstract root)
├── :StructuralEntity (templates, definitions, schemas)
│   ├── :Capability
│   ├── :CapabilityType
│   ├── :Framework
│   ├── :Plugin
│   ├── :FeatureTemplate
│   ├── :FeatureCategory
│   ├── :AggregationFunction
│   ├── :EventPattern
│   ├── :App
│   ├── :AppCategory
│   ├── :Domain
│   ├── :DomainCategory
│   ├── :ServiceLevelObjective
│   └── :FeatureParameter
│
└── :TemporalEntity (instances with temporal extent)
    ├── :ObservationWindow
    ├── :Observation
    ├── :FeatureInstance
    ├── :Event
    └── :QualityMetric
```

## Key Concepts

### 1. Capabilities

**Capabilities** represent atomic system operations discovered through PyObjC framework introspection.

#### Key Properties:
- `:pyobjcSymbol` - Fully-qualified PyObjC symbol (e.g., `"Cocoa.NSWorkspace.activeApplication"`)
- `:sourceFramework` - Links to the macOS framework providing this capability
- `:capabilityType` - Functional classification (UI, System, Data, Input, Process)
- `:requiresPermission` - macOS permissions needed (Accessibility, ScreenRecording, etc.)
- `:hasSLO` - Service level objectives for performance/quality

#### Example:
```turtle
cap:ActiveApplicationCapability
    a :Capability ;
    rdfs:label "Active Application Monitoring"@en ;
    :pyobjcSymbol "Cocoa.NSWorkspace.sharedWorkspace.activeApplication" ;
    :sourceFramework cap:CocoaFramework ;
    :capabilityType cap:UICapabilityType ;
    :requiresPermission "Accessibility" ;
    :hasSLO cap:RealtimeSLO .
```

### 2. Feature Templates

**Feature Templates** define how to compute behavioral features from raw observations.

#### Key Properties:
- `:hasInputType` - Type of observations consumed (e.g., `"AppWindowObservation"`)
- `:hasOutputType` - Data type of computed value (e.g., `"xsd:float"`)
- `:sourceCapability` - Capabilities required to collect input data
- `:aggregationFunction` - Mathematical function for aggregation (sum, count, avg, etc.)
- `:windowDuration` - Default temporal window (ISO 8601 duration)
- `:featureCategory` - Functional categorization (Attention, Productivity, etc.)
- `:hasParameter` - Configurable parameters for the template

#### Example:
```turtle
ft:TimeInAppTemplate
    a :FeatureTemplate ;
    rdfs:label "Time in Application" ;
    :hasInputType "AppWindowObservation" ;
    :hasOutputType "xsd:float" ;
    :aggregationFunction ft:SumFunction ;
    :windowDuration "PT1H"^^xsd:duration ;
    :featureCategory ft:AttentionCategory ;
    :hasParameter ft:TimeInAppTemplate_AppBundleIdParam .
```

### 3. Feature Instances

**Feature Instances** are concrete realizations of templates, computed over specific windows.

#### Key Properties:
- `:instanceOf` - Links to the parent template
- `:hasValue` - The computed feature value
- `:observationWindow` - Temporal window for computation
- `:computedFrom` - Source observations used in computation
- `:confidence` - Confidence score (0.0-1.0)
- `:timestamp` - When the feature was computed

#### Example:
```turtle
:featureInstance_001
    a :FeatureInstance ;
    :instanceOf ft:TimeInAppTemplate ;
    :hasValue 45.3 ;  # minutes
    :observationWindow :window_20251124_1400 ;
    :confidence 0.98 ;
    :timestamp "2025-11-24T15:00:00Z"^^xsd:dateTime .
```

### 4. Observation Windows

**Observation Windows** define temporal intervals for feature computation.

#### Key Properties:
- `:startTime` - Window start (ISO 8601 dateTime)
- `:endTime` - Window end (ISO 8601 dateTime)
- `:duration` - Optional explicit duration

#### Validation:
SHACL ensures `endTime > startTime` for all windows.

#### Example:
```turtle
:window_20251124_1400
    a :ObservationWindow ;
    :startTime "2025-11-24T14:00:00Z"^^xsd:dateTime ;
    :endTime "2025-11-24T15:00:00Z"^^xsd:dateTime ;
    :duration "PT1H"^^xsd:duration .
```

### 5. Events

**Events** represent significant occurrences detected through pattern matching on feature streams.

#### Key Properties:
- `:eventType` - Classification (StateTransition, Anomaly, Threshold, Pattern)
- `:severity` - Importance level (info, warning, critical)
- `:detectedBy` - Pattern that identified this event
- `:triggeredBy` - Feature instances that triggered detection
- `:timestamp` - When the event occurred

#### Example:
```turtle
:event_deepWorkEntry_001
    a :Event ;
    :eventType "StateTransition" ;
    :severity "info" ;
    :detectedBy :deepWorkPattern ;
    :triggeredBy :featureInstance_timeInIDE_001 ;
    :timestamp "2025-11-24T14:45:00Z"^^xsd:dateTime .
```

## Feature Template Catalog

The ontology includes 10 production-ready feature templates:

### Attention & Focus
1. **`timeInApp`** - Minutes spent in an application per window
2. **`deepWorkSession`** - Longest uninterrupted focus session duration
3. **`switchCount`** - Number of application switches per window

### Productivity
4. **`keyboardActivityRate`** - Keystrokes per minute
5. **`codeCommitFrequency`** - Git commits per hour
6. **`meetingFragmentation`** - Number of separate calendar events

### Communication
7. **`communicationBurstiness`** - Stddev of time gaps between comm app activations

### Browser Activity
8. **`domainVisitCount`** - Visits to a specific domain
9. **`uniqueDomainsVisited`** - Distinct domains visited per window

### Calendar
10. **`calendarBusyHours`** - Total scheduled meeting time

Each template includes:
- Input/output type specifications
- Aggregation function
- Default window duration
- Configurable parameters
- Usage examples

## Capability Registry

The ontology includes 13 macOS capabilities with PyObjC bindings:

### UI Capabilities
- **Active Application Monitoring** - Track focused app via NSWorkspace
- **Window Title Monitoring** - Read window titles via Accessibility API
- **Browser URL Monitoring** - Capture active browser URLs
- **Screen Content Access** - Screenshot/screen region capture

### Data Capabilities
- **Calendar Event Access** - Read calendar events via EventKit

### Input Capabilities
- **Keyboard Monitoring** - Count keystrokes and detect modifiers
- **Mouse Activity Monitoring** - Track clicks, movement, scrolling

### System/Process Capabilities
- **Running Applications List** - Enumerate all active processes
- **Process Execution Monitoring** - Detect process launches/terminations
- **Notification Monitoring** - Observe system and app notifications
- **Idle Time Detection** - Measure time since last user input
- **Network Activity Monitoring** - Track network usage per app

Each capability includes:
- PyObjC symbol path
- Source framework attribution
- Required macOS permissions
- Service level objectives (latency, throughput, availability)
- Usage examples and notes

## SHACL Validation

The `shapes.ttl` file provides comprehensive validation:

### Structural Validation
- **Required properties** - Ensures mandatory fields are present
- **Cardinality constraints** - Enforces min/max counts
- **Type constraints** - Validates datatypes and class references
- **Pattern matching** - Validates formats (bundle IDs, versions, domains)

### Semantic Validation
- **Temporal consistency** - Feature timestamps must fall within observation windows
- **Type matching** - Feature instance values must match template output types
- **Event causality** - Events must occur at/after their triggering features
- **Deprecation policy** - Deprecated capabilities should reference replacements

### Examples of Validation Rules

```turtle
# FeatureTemplate must specify input/output types and source capabilities
shapes:FeatureTemplateShape
    sh:property [
        sh:path :hasInputType ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path :sourceCapability ;
        sh:minCount 1 ;
        sh:class :Capability ;
    ] .

# ObservationWindow end time must be after start time
shapes:ObservationWindowShape
    sh:sparql [
        sh:message "End time must be after start time" ;
        sh:select """
            SELECT $this WHERE {
                $this :startTime ?start ; :endTime ?end .
                FILTER (?end <= ?start)
            }
        """ ;
    ] .
```

## Usage with TTL2DSPy

This ontology is designed for consumption by TTL2DSPy for automatic Python class generation.

### Recommended Workflow

1. **Load ontology files** into TTL2DSPy:
   ```python
   from ttl2dspy import TTLParser

   parser = TTLParser()
   parser.parse_file('core.ttl')
   parser.parse_file('shapes.ttl')
   parser.parse_file('features.ttl')
   parser.parse_file('capabilities.ttl')
   ```

2. **Generate Python classes** for core entities:
   ```python
   # Generates Python classes for:
   # - Capability, FeatureTemplate, FeatureInstance
   # - ObservationWindow, Observation, Event
   # - App, Domain, and all supporting classes

   classes = parser.generate_python_classes()
   ```

3. **Validate instance data** using SHACL shapes:
   ```python
   from pyshacl import validate

   data_graph = parser.load_instance_data('my_data.ttl')
   shapes_graph = parser.load_shapes('shapes.ttl')

   conforms, report, message = validate(
       data_graph,
       shacl_graph=shapes_graph
   )
   ```

4. **Create feature instances** programmatically:
   ```python
   # Generated class from TTL2DSPy
   instance = FeatureInstance(
       instanceOf=TimeInAppTemplate,
       hasValue=45.3,
       observationWindow=window,
       timestamp=datetime.now()
   )
   ```

## Architecture Patterns

### Feature Computation Pipeline

```
1. Capability Discovery (PyObjC introspection)
   └─> Register capabilities with SLOs

2. Observation Collection (real-time monitoring)
   └─> Raw observations with timestamps

3. Window Segmentation (temporal grouping)
   └─> Create observation windows

4. Feature Computation (template instantiation)
   └─> Apply aggregation functions
   └─> Create feature instances with values

5. Event Detection (pattern matching)
   └─> Analyze feature streams
   └─> Generate events when patterns match

6. Knowledge Graph Update (RDF persistence)
   └─> Store entities and relationships
   └─> Enable semantic queries
```

### Temporal Relationships

```
ObservationWindow [14:00 - 15:00]
   │
   ├─> contains multiple Observations
   │   ├─> Observation @ 14:05 (VS Code active)
   │   ├─> Observation @ 14:12 (VS Code active)
   │   └─> Observation @ 14:33 (VS Code active)
   │
   └─> produces FeatureInstance @ 15:00
       └─> value: 45.3 minutes in VS Code
       └─> may trigger Event (e.g., "Deep work detected")
```

## Extensibility

### Adding New Feature Templates

1. Define the template in `features.ttl`:
```turtle
ft:MyNewFeatureTemplate
    a :FeatureTemplate ;
    rdfs:label "My Feature" ;
    :hasInputType "MyObservationType" ;
    :hasOutputType "xsd:float" ;
    :aggregationFunction ft:SumFunction ;
    :windowDuration "PT1H"^^xsd:duration ;
    :featureCategory ft:ProductivityCategory .
```

2. Add SHACL validation (if needed) in `shapes.ttl`

3. Document usage in this README

### Adding New Capabilities

1. Define the capability in `capabilities.ttl`:
```turtle
cap:MyNewCapability
    a :Capability ;
    rdfs:label "My Capability" ;
    :pyobjcSymbol "MyFramework.MyClass.myMethod" ;
    :sourceFramework cap:MyFramework ;
    :capabilityType cap:UICapabilityType ;
    :requiresPermission "Accessibility" ;
    :hasSLO cap:RealtimeSLO .
```

2. Ensure the PyObjC symbol is accessible

3. Test permission requirements

### Adding Custom SHACL Rules

Add custom validation in `shapes.ttl`:
```turtle
shapes:MyCustomValidation
    a sh:NodeShape ;
    sh:targetClass :MyClass ;
    sh:sparql [
        sh:message "My validation message" ;
        sh:select """
            SELECT $this WHERE {
                # Your SPARQL validation logic
            }
        """ ;
    ] .
```

## Standards Compliance

This ontology follows W3C standards:

- **RDF 1.1** - Resource Description Framework
- **RDFS** - RDF Schema for class/property definitions
- **OWL 2** - Web Ontology Language for rich semantics
- **SHACL** - Shapes Constraint Language for validation
- **SKOS** - Simple Knowledge Organization System for documentation
- **Dublin Core** - Metadata terms (dcterms)

### Validation Tools

Validate TTL syntax and semantics:

```bash
# Using rapper (part of Raptor RDF)
rapper -i turtle -o turtle core.ttl

# Using Apache Jena riot
riot --validate core.ttl

# Using pyshacl for SHACL validation
pyshacl -s shapes.ttl -df turtle instance_data.ttl
```

## Performance Considerations

### Query Optimization

For efficient SPARQL queries over large datasets:

1. **Index key properties**: `:timestamp`, `:observationWindow`, `:instanceOf`
2. **Use property paths wisely**: Avoid deep recursive paths
3. **Leverage aggregation**: Pre-compute summaries at ingestion time
4. **Partition by time**: Split data by day/week for temporal queries

### Storage Recommendations

- **Triple Store**: Apache Jena TDB, Blazegraph, or Virtuoso for large-scale deployments
- **Graph Database**: Neo4j with RDF plugin for graph traversal queries
- **Time-Series DB**: Hybrid approach with InfluxDB for raw observations + RDF for metadata

## Examples

See `examples.ttl` for complete instance data examples demonstrating:

- Capability registration and SLO definition
- Feature template instantiation with parameters
- Observation collection and window segmentation
- Feature computation from observations
- Event detection from feature patterns
- Complete temporal relationship chains

## License

This ontology is part of the KGC OS Graph Agent system.

## Version History

- **1.0.0** (2025-11-24) - Initial release
  - Core class hierarchy and properties
  - SHACL validation shapes
  - 10 feature templates
  - 13 capability definitions
  - Complete documentation

## Contact

For questions or contributions, please open an issue in the KGC repository.
