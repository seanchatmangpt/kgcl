# KGC Ontology Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    KGC OS Graph Agent System                     │
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   PyObjC    │───▶│ Capabilities │───▶│ Observations │       │
│  │ Discovery   │    │   Registry   │    │  Collection  │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                │                  │
│                                                ▼                  │
│                                          ┌──────────────┐        │
│                                          │ Observation  │        │
│                                          │   Windows    │        │
│                                          └──────────────┘        │
│                                                │                  │
│                                                ▼                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Feature    │───▶│   Feature    │◀───│ Aggregation  │       │
│  │  Templates  │    │  Instances   │    │  Functions   │       │
│  └─────────────┘    └──────────────┘    └──────────────┘       │
│                                                │                  │
│                                                ▼                  │
│                                          ┌──────────────┐        │
│                                          │   Pattern    │        │
│                                          │   Matching   │        │
│                                          └──────────────┘        │
│                                                │                  │
│                                                ▼                  │
│                                          ┌──────────────┐        │
│                                          │   Events     │        │
│                                          │  Detection   │        │
│                                          └──────────────┘        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Class Hierarchy Diagram

```
Entity (abstract)
│
├── StructuralEntity (templates, definitions)
│   │
│   ├── Capability
│   │   └── attributes: pyobjcSymbol, requiresPermission
│   │   └── links: sourceFramework, hasSLO
│   │
│   ├── FeatureTemplate
│   │   └── attributes: hasInputType, hasOutputType, windowDuration
│   │   └── links: sourceCapability, aggregationFunction, featureCategory
│   │
│   ├── Framework
│   │   └── attributes: version, description
│   │
│   ├── App
│   │   └── attributes: appBundleId, appName
│   │   └── links: appCategory
│   │
│   ├── Domain
│   │   └── attributes: domainName
│   │   └── links: domainCategory
│   │
│   ├── EventPattern
│   │   └── attributes: description, criteria
│   │
│   └── ServiceLevelObjective
│       └── attributes: description, metrics
│
└── TemporalEntity (instances with time)
    │
    ├── ObservationWindow
    │   └── attributes: startTime, endTime, duration
    │
    ├── Observation
    │   └── attributes: timestamp
    │   └── links: observationWindow
    │
    ├── FeatureInstance
    │   └── attributes: hasValue, confidence, timestamp
    │   └── links: instanceOf, observationWindow, computedFrom
    │
    └── Event
        └── attributes: eventType, severity, timestamp
        └── links: detectedBy, triggeredBy
```

## Data Flow Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: Capability Discovery (PyObjC)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  macOS Frameworks (Cocoa, ApplicationServices, EventKit)       │
│         │                                                       │
│         │ PyObjC introspection                                 │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────┐          │
│  │ Capability Registry (capabilities.ttl)          │          │
│  │  - 12 capabilities with PyObjC bindings         │          │
│  │  - 5 frameworks                                 │          │
│  │  - SLO definitions                              │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ enables
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: Observation Collection (Real-time)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Capability.execute() → Raw Observations                       │
│                                                                 │
│  Examples:                                                     │
│  • Window title changed: "index.html - VS Code"                │
│  • App switch: VS Code → Slack                                │
│  • URL visit: https://github.com/user/repo                    │
│  • Calendar event: "Daily Standup" 09:00-09:30                │
│  • Keyboard: 450 keystrokes in 15 minutes                     │
│                                                                 │
│  Each observation has:                                         │
│  • timestamp (when)                                            │
│  • payload (what)                                              │
│  • source capability (how)                                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ collected into
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3: Temporal Windowing                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ObservationWindow [14:00:00 → 15:00:00]                      │
│    │                                                            │
│    ├── Observation @ 14:05:00                                  │
│    ├── Observation @ 14:12:00                                  │
│    ├── Observation @ 14:25:00                                  │
│    └── Observation @ 14:48:00                                  │
│                                                                 │
│  Window types:                                                 │
│  • Fixed (hourly, daily)                                       │
│  • Sliding (15-min slide, 1-hour span)                         │
│  • Session-based (until idle threshold)                        │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ feeds into
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 4: Feature Computation (features.ttl)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FeatureTemplate.compute(window) → FeatureInstance            │
│                                                                 │
│  Template: timeInApp                                           │
│    ├── Input: AppWindowObservation                            │
│    ├── Aggregation: sum(duration)                             │
│    ├── Output: float (minutes)                                │
│    └── Parameters: {appBundleId: "com.microsoft.VSCode"}      │
│         │                                                       │
│         ▼                                                       │
│  Instance: 45.3 minutes in VS Code (14:00-15:00)              │
│         │                                                       │
│         │                                                       │
│  10 templates available:                                       │
│  • timeInApp, switchCount, domainVisitCount                   │
│  • deepWorkSession, calendarBusyHours                         │
│  • keyboardActivityRate, uniqueDomainsVisited                 │
│  • meetingFragmentation, communicationBurstiness              │
│  • codeCommitFrequency                                         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ analyzed by
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 5: Event Detection (Pattern Matching)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EventPattern.match(features) → Event                          │
│                                                                 │
│  Pattern: Deep Work Entry                                      │
│    ├── Conditions:                                             │
│    │   • timeInIDE > 60 minutes                               │
│    │   • switchCount < 3                                       │
│    │   • communicationAppTime < 5 minutes                     │
│    │                                                            │
│    ▼                                                            │
│  Event: "Deep Work State Entered"                             │
│    ├── Type: StateTransition                                   │
│    ├── Severity: info                                          │
│    ├── Timestamp: 2025-11-24T14:45:00Z                        │
│    └── Triggered by: [featureInstance_001, ...]               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ stored in
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 6: Knowledge Graph (RDF Triple Store)                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  All entities persisted as RDF triples                         │
│                                                                 │
│  Query examples:                                               │
│  • "Find all deep work sessions > 1 hour this week"           │
│  • "What apps correlate with high productivity?"              │
│  • "When do I get the most interruptions?"                    │
│  • "Predict my focus time based on calendar"                  │
│                                                                 │
│  SPARQL endpoint enables:                                      │
│  • Semantic queries                                            │
│  • Pattern discovery                                           │
│  • Correlation analysis                                        │
│  • Trend visualization                                         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Validation Architecture (SHACL)

```
┌────────────────────────────────────────────────────────────────┐
│                   SHACL Validation Pipeline                     │
└────────────────────────────────────────────────────────────────┘

Instance Data (RDF Graph)
    │
    │ validate against
    ▼
shapes.ttl (22 NodeShapes)
    │
    ├─▶ Structural Validation
    │      • Required properties
    │      • Cardinality constraints
    │      • Type checking
    │      • Pattern matching (regex)
    │
    ├─▶ Semantic Validation
    │      • Temporal consistency
    │      • Type matching
    │      • Referential integrity
    │      • Business rules
    │
    └─▶ Custom SPARQL Constraints
           • Cross-entity validation
           • Complex business logic
           • Temporal relationships

           Examples:
           • endTime > startTime
           • featureInstance.timestamp ∈ observationWindow
           • event.timestamp ≥ feature.timestamp
           • deprecated capability → has replacement

    │
    ▼
Validation Report
    • conforms: true/false
    • violations: [...]
    • warnings: [...]
    • informational: [...]
```

## Integration with TTL2DSPy

```
┌────────────────────────────────────────────────────────────────┐
│                    TTL2DSPy Code Generation                     │
└────────────────────────────────────────────────────────────────┘

Ontology TTL Files
    │
    │ parse
    ▼
TTL2DSPy Parser
    │
    ├─▶ Analyze Classes
    │      core:Capability → class Capability
    │      core:FeatureTemplate → class FeatureTemplate
    │      core:FeatureInstance → class FeatureInstance
    │      ...
    │
    ├─▶ Analyze Properties
    │      core:pyobjcSymbol → property pyobjc_symbol: str
    │      core:hasValue → property has_value: Any
    │      core:observationWindow → property observation_window: ObservationWindow
    │      ...
    │
    └─▶ Generate Python Classes
           • Type hints from xsd:* types
           • Relationships via references
           • Validation from SHACL shapes
           • Docstrings from rdfs:comment

    │
    ▼
Generated Python API

from kgcl.ontology.generated import (
    Capability,
    FeatureTemplate,
    FeatureInstance,
    ObservationWindow,
    Event
)

# Create capability
cap = Capability(
    pyobjc_symbol="Cocoa.NSWorkspace.activeApplication",
    source_framework=cocoa_framework,
    capability_type=ui_capability_type,
    requires_permission="Accessibility"
)

# Create feature template
template = FeatureTemplate(
    has_input_type="AppWindowObservation",
    has_output_type="xsd:float",
    aggregation_function=sum_function,
    window_duration=timedelta(hours=1)
)

# Create feature instance
instance = FeatureInstance(
    instance_of=template,
    has_value=45.3,
    observation_window=window,
    confidence=0.98
)

# Validate
from kgcl.ontology import validate_instance_data
conforms, report, text = validate_instance_data(instance.to_rdf())
```

## Temporal Relationship Graph

```
Time Axis ──────────────────────────────────────────────▶

14:00:00                                     15:00:00
   │                                            │
   │◀────── ObservationWindow ────────────────▶│
   │                                            │
   │   Observations:                            │
   │                                            │
   ├─▶ 14:05:00 VS Code active (5 min)         │
   │                                            │
   ├─▶ 14:12:00 VS Code active (13 min)        │
   │                                            │
   ├─▶ 14:25:00 VS Code active (27 min)        │
   │                                            │
   │                                            │
   │                           Feature computed │
   │                                at 15:00:01 │
   └────────────────────────────────────────────┼─▶ FeatureInstance
                                                │   value: 45.0 min
                                                │
                                                │ triggers
                                                │
                                                └─▶ Event
                                                    "High focus detected"
                                                    at 15:00:01

Constraints:
• observation.timestamp ∈ [window.startTime, window.endTime]
• feature.timestamp ≥ window.endTime
• event.timestamp ≥ feature.timestamp
```

## Capability Binding Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              PyObjC → RDF Capability Mapping                    │
└────────────────────────────────────────────────────────────────┘

macOS Framework                    RDF Capability
─────────────────                  ──────────────

Cocoa.framework                    cap:CocoaFramework
    │                                  │
    └─▶ NSWorkspace                    │
           │                           │
           └─▶ activeApplication()     └─▶ cap:ActiveApplicationCapability
                                              │
                                              ├─ pyobjcSymbol: "Cocoa.NSWorkspace..."
                                              ├─ requiresPermission: "Accessibility"
                                              ├─ hasSLO: RealtimeSLO (< 100ms)
                                              └─ capabilityType: UICapabilityType

Runtime Execution:
1. Discover: pyobj_introspect(Cocoa) → capabilities
2. Register: create RDF instances in triple store
3. Execute: capability.invoke() → observation
4. Monitor: track SLO metrics (latency, errors)
5. Validate: ensure permissions granted
```

## File Dependency Graph

```
core.ttl (foundation)
   │
   │ imported by
   │
   ├─▶ shapes.ttl (validation)
   │
   ├─▶ features.ttl (templates)
   │      │
   │      │ references
   │      └─▶ capabilities.ttl (capability instances)
   │
   └─▶ examples.ttl (instance data)
          │
          │ references all above
          └─▶ (demonstrates complete flow)

Each file is self-contained but references core.ttl
for class/property definitions.

Total: 1,458 triples across 5 files
```

## Summary Statistics

```
Ontology Metrics:
─────────────────────────────────────────
Classes:                     22
Object Properties:           15
Datatype Properties:         25
Total Properties:            40
SHACL Node Shapes:           22
Feature Templates:           10
Capabilities:                12
Frameworks:                   5
Total Triples:            1,458

W3C Standards:
─────────────────────────────────────────
✓ RDF 1.1
✓ RDFS
✓ OWL 2
✓ SHACL
✓ SKOS
✓ Dublin Core (dcterms)

Validation Status:
─────────────────────────────────────────
✓ Turtle syntax valid
✓ All prefixes bound
✓ No broken references
✓ SHACL constraints consistent
✓ TTL2DSPy compatible
```
