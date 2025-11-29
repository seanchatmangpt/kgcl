# Product Requirements Document: MCP Server for Code Analysis Tools

## Executive Summary

Build a comprehensive Model Context Protocol (MCP) server that exposes all KGCL code analysis capabilities as queryable tools and resources for AI assistants. This includes:
- **Codebase Index** (863 Java classes, 133 packages) - Fast lookups and navigation
- **Ontology Explorer** - SPARQL-based architecture analysis
- **Gap Analysis** - Java → Python porting gap detection
- **Call Graph Analysis** - Method call graph comparison and delta detection
- **Semantic Detection** - AST fingerprinting and algorithm comparison
- **Dependency Analysis** - Class dependency graph analysis
- **Performance Analysis** - Complexity and optimization analysis
- **Type Flow Analysis** - Type safety and flow tracking
- **Exception Analysis** - Exception handling patterns
- **Test Mapping** - Test coverage and mapping

This enables AI assistants to perform comprehensive code analysis, architecture exploration, and migration planning through natural language queries.

**Status**: Proposed  
**Priority**: High  
**Target Release**: v0.2.0  
**Estimated Effort**: 5-7 days

---

## Background & Context

### Existing Infrastructure

#### 1. Codebase Index (`src/kgcl/ontology/codebase_index.py`)
   - RDF-based index with 863 classes, 133 packages
   - Fast lookups: `find_class()`, `find_classes_in_package()`, `get_inheritance_hierarchy()`
   - Full-text search: `search_classes()`
   - Method/field indexing: `find_classes_with_method()`, `find_classes_with_field()`

#### 2. Ontology Explorer (`src/kgcl/yawl_ontology/explorer.py`)
   - SPARQL-based ontology exploration using PyOxigraph
   - Architecture analysis: `analyze_decomposition_hierarchy()`, `get_class_methods()`
   - High-performance queries with timing metrics
   - Class hierarchy and API surface analysis

#### 3. Gap Analysis (`src/kgcl/yawl_ontology/gap_analyzer.py`)
   - Java → Python porting gap detection
   - Missing classes, methods, incomplete implementations
   - Coverage percentage calculation
   - Stub detection and partial implementation analysis

#### 4. Call Graph Analysis (`src/kgcl/yawl_ontology/call_graph_analyzer.py`)
   - Method call graph extraction from Java and Python
   - Delta detection: missing paths, new paths, orphaned methods
   - Call site analysis and path comparison

#### 5. Semantic Detection (`src/kgcl/yawl_ontology/semantic_detector.py`)
   - AST fingerprinting for semantic comparison
   - Algorithm delta detection
   - Control flow graph (CFG) comparison
   - Data flow analysis

#### 6. Dependency Analysis (`src/kgcl/yawl_ontology/dependency_analyzer.py`)
   - Class dependency extraction (imports, fields, parameters)
   - Dependency graph building and comparison
   - Circular dependency detection
   - Missing/new dependency identification

#### 7. Performance Analysis (`src/kgcl/yawl_ontology/performance_analyzer.py`)
   - Algorithmic complexity analysis
   - Loop structure and recursion pattern detection
   - Performance regression identification
   - Optimization opportunity detection

#### 8. Type Flow Analysis (`src/kgcl/yawl_ontology/type_flow_analyzer.py`)
   - Type transformation tracking through method chains
   - Java vs Python type system comparison
   - Type safety regression detection
   - Incompatible return type identification

#### 9. Enhanced Parsers
   - `EnhancedJavaParser` - Java parsing with method bodies and call sites
   - `EnhancedPythonCodeAnalyzer` - Python AST analysis with semantic extraction

#### 10. Query Infrastructure
   - CLI query command (`src/kgcl/cli/query.py`) - SPARQL queries via command line
   - Daemon query API (`src/kgcl/daemon/kgcld.py`) - Async SPARQL queries with time-travel
   - Index builder (`scripts/build_codebase_index.py`) - Generates `index.ttl` from codebase

#### 11. API Patterns (from UNRDF vendors)
   - HTTP/REST endpoints for SPARQL queries (`/api/query`)
   - OpenAPI specifications
   - Authentication and rate limiting patterns

#### 12. MCP Context
   - FastMCP framework available for Python MCP servers
   - Existing MCP references in codebase (Claude Flow, AgentDB patterns)
   - Pattern: Expose tools (functions) and resources (data) via MCP

### Problem Statement

The comprehensive code analysis tools are currently only accessible via:
- Python APIs (various analyzer classes)
- CLI commands (`kgc-yawl-ontology`)
- Direct SPARQL queries
- Programmatic Python scripts

AI assistants cannot naturally access these analysis capabilities, making it difficult to:
- Navigate Java class hierarchies and understand architecture
- Perform gap analysis for Java → Python porting
- Compare call graphs and detect missing implementations
- Analyze semantic differences between implementations
- Track dependencies and detect circular dependencies
- Assess performance characteristics and optimization opportunities
- Understand type flows and type safety
- Plan migrations and identify critical gaps

### Solution

Expose all code analysis tools as an MCP server, enabling AI assistants to:
- Query codebase structure via natural language (index tools)
- Explore ontology and architecture (explorer tools)
- Perform gap analysis for porting projects (gap analysis tools)
- Compare implementations and detect deltas (call graph, semantic, dependency tools)
- Analyze performance and type safety (performance, type flow tools)
- Access analysis results as resources
- Get comprehensive migration planning insights

---

## Goals & Success Criteria

### Primary Goals

1. **MCP Server Implementation**
   - FastMCP-based server exposing all code analysis tools
   - Resources for analysis results, class definitions, reports
   - Full integration with existing analyzer APIs

2. **Comprehensive Tool Coverage**
   - Codebase Index tools (8 tools)
   - Ontology Explorer tools (5+ tools)
   - Gap Analysis tools (3+ tools)
   - Call Graph Analysis tools (3+ tools)
   - Semantic Detection tools (4+ tools)
   - Dependency Analysis tools (3+ tools)
   - Performance Analysis tools (2+ tools)
   - Type Flow Analysis tools (2+ tools)
   - Natural language-friendly parameter descriptions
   - Comprehensive error handling

3. **Resource Exposure**
   - Individual class definitions as resources
   - Analysis reports as resources
   - Gap analysis results as resources
   - Call graph visualizations as resources
   - Dependency graphs as resources

### Success Criteria

- [ ] MCP server starts and connects successfully
- [ ] All codebase index tools exposed (8 tools)
- [ ] All ontology explorer tools exposed (5+ tools)
- [ ] All gap analysis tools exposed (3+ tools)
- [ ] All call graph analysis tools exposed (3+ tools)
- [ ] All semantic detection tools exposed (4+ tools)
- [ ] All dependency analysis tools exposed (3+ tools)
- [ ] All performance analysis tools exposed (2+ tools)
- [ ] All type flow analysis tools exposed (2+ tools)
- [ ] Resources accessible for all 863 classes
- [ ] Analysis reports available as resources
- [ ] Query latency < 100ms for index lookups
- [ ] Analysis latency < 5s for complex analyses
- [ ] Full test coverage (>90%)
- [ ] Documentation with usage examples for each tool category
- [ ] Integration tests with MCP client

---

## Requirements

### Functional Requirements

#### FR1: MCP Server Core
- **FR1.1**: Server built with FastMCP framework
- **FR1.2**: Server loads `ontology/codebase/index.ttl` on startup
- **FR1.3**: Server exposes `CodebaseIndex` instance
- **FR1.4**: Server supports stdio transport (default for MCP)
- **FR1.5**: Server supports HTTP transport (optional, for web deployments)

#### FR2: MCP Tools (Functions)

##### FR2.1: Codebase Index Tools

Expose all `CodebaseIndex` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `find_class` | Find class by name (simple or FQN) | `class_name: str` | Class info dict |
| `find_classes_in_package` | List all classes in package | `package_name: str` | List of FQN strings |
| `get_inheritance_hierarchy` | Get extends/implements/subclasses | `class_name: str` | Hierarchy dict |
| `find_classes_with_method` | Find classes implementing method | `method_name: str` | List of FQN strings |
| `find_classes_with_field` | Find classes containing field | `field_name: str` | List of FQN strings |
| `find_references` | Find classes referencing target | `class_name: str` | List of FQN strings |
| `search_classes` | Full-text search on class metadata | `search_term: str` | List of class info dicts |
| `query_index` | Execute custom SPARQL query | `sparql: str` | Query results |

##### FR2.2: Ontology Explorer Tools

Expose `YawlOntologyExplorer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `explore_class` | Get class methods and API surface | `class_name: str` | Class methods list |
| `analyze_hierarchy` | Analyze decomposition hierarchy | `base_class: str \| None` | Hierarchy dict |
| `query_ontology` | Execute SPARQL query on ontology | `sparql: str` | Query results with timing |
| `get_class_info` | Get comprehensive class information | `class_name: str` | ClassInfo object |
| `export_architecture` | Export architecture summary | `output_path: str \| None` | Architecture report path |

##### FR2.3: Gap Analysis Tools

Expose `YawlGapAnalyzer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `analyze_gaps` | Analyze gaps between Java and Python | `ontology_file: str`, `python_root: str` | GapAnalysis object |
| `get_missing_classes` | Get list of missing classes | `ontology_file: str`, `python_root: str` | List of ClassInfo |
| `get_missing_methods` | Get missing methods by class | `class_name: str`, `ontology_file: str`, `python_root: str` | Dict of missing methods |
| `get_coverage` | Get implementation coverage percentage | `ontology_file: str`, `python_root: str` | Coverage percentage |

##### FR2.4: Call Graph Analysis Tools

Expose `CallGraphAnalyzer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `analyze_call_graph` | Build and compare call graphs | `java_root: str`, `python_root: str` | CallGraphDeltas object |
| `find_missing_paths` | Find missing call paths in Python | `java_root: str`, `python_root: str` | List of CallPath |
| `find_orphaned_methods` | Find orphaned methods | `java_root: str`, `python_root: str` | List of method names |

##### FR2.5: Semantic Detection Tools

Expose `SemanticDetector` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `detect_semantic_deltas` | Detect semantic differences | `java_root: str`, `python_root: str` | SemanticDeltas object |
| `compare_algorithms` | Compare algorithm implementations | `class_name: str`, `method_name: str`, `java_root: str`, `python_root: str` | AlgorithmDelta |
| `analyze_control_flow` | Analyze control flow differences | `class_name: str`, `method_name: str`, `java_root: str`, `python_root: str` | CFGDelta |

##### FR2.6: Dependency Analysis Tools

Expose `DependencyAnalyzer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `analyze_dependencies` | Analyze class dependencies | `java_root: str`, `python_root: str` | DependencyDeltas object |
| `find_circular_dependencies` | Find circular dependency differences | `java_root: str`, `python_root: str` | List of DependencyDelta |
| `get_missing_dependencies` | Get missing dependencies in Python | `java_root: str`, `python_root: str` | List of DependencyDelta |

##### FR2.7: Performance Analysis Tools

Expose `PerformanceAnalyzer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `analyze_performance` | Analyze performance characteristics | `java_root: str`, `python_root: str` | PerformanceDeltas object |
| `detect_complexity_regressions` | Detect algorithmic complexity regressions | `java_root: str`, `python_root: str` | List of PerformanceDelta |

##### FR2.8: Type Flow Analysis Tools

Expose `TypeFlowAnalyzer` methods as MCP tools:

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `analyze_type_flow` | Analyze type flows | `java_root: str`, `python_root: str` | TypeFlowDeltas object |
| `detect_type_mismatches` | Detect type mismatches | `java_root: str`, `python_root: str` | List of TypeFlowDelta |

#### FR3: MCP Resources (Data)

Expose codebase data and analysis results as MCP resources:

| Resource URI | Description | Content |
|--------------|-------------|---------|
| `codebase://class/{fqn}` | Individual class definition | Class metadata JSON |
| `codebase://package/{package}` | Package listing | List of classes in package |
| `codebase://index/stats` | Index statistics | Counts, metadata |
| `codebase://index/schema` | Index schema | RDF schema definitions |
| `analysis://gap/{report_id}` | Gap analysis report | GapAnalysis JSON |
| `analysis://callgraph/{report_id}` | Call graph analysis | CallGraphDeltas JSON |
| `analysis://semantic/{report_id}` | Semantic delta analysis | SemanticDeltas JSON |
| `analysis://dependencies/{report_id}` | Dependency analysis | DependencyDeltas JSON |
| `analysis://performance/{report_id}` | Performance analysis | PerformanceDeltas JSON |
| `analysis://typeflow/{report_id}` | Type flow analysis | TypeFlowDeltas JSON |
| `ontology://architecture` | Architecture summary | Architecture report markdown |

#### FR4: Error Handling
- **FR4.1**: Invalid class/package names return clear error messages
- **FR4.2**: Missing index file handled gracefully
- **FR4.3**: SPARQL query errors return structured error responses
- **FR4.4**: All errors include error codes and context

#### FR5: Performance
- **FR5.1**: Index load time < 2 seconds
- **FR5.2**: Index tool execution < 100ms (p99)
- **FR5.3**: Explorer tool execution < 500ms (p99)
- **FR5.4**: Analysis tool execution < 5s (p99) for complex analyses
- **FR5.5**: Resource access < 50ms (p99)
- **FR5.6**: Support concurrent requests
- **FR5.7**: Cache analysis results for repeated queries

### Non-Functional Requirements

#### NFR1: Code Quality
- Full type hints (mypy strict)
- NumPy docstrings for all public APIs
- Line length ≤ 88 characters
- No unused imports/variables
- Chicago School TDD (test-first)

#### NFR2: Testing
- Unit tests for all tools
- Integration tests with MCP client
- Test fixtures for sample codebase
- Coverage > 90%

#### NFR3: Documentation
- README with setup instructions
- Usage examples for each tool
- Integration guide for AI assistants
- API reference documentation

#### NFR4: Dependencies
- FastMCP as optional dependency
- No breaking changes to existing code
- Backward compatible with current `CodebaseIndex` API

---

## Architecture

### Component Structure

```
src/kgcl/mcp/
├── __init__.py
├── codebase_server.py       # Main MCP server implementation
├── tools/
│   ├── __init__.py
│   ├── index_tools.py      # CodebaseIndex tool wrappers
│   ├── explorer_tools.py   # YawlOntologyExplorer tool wrappers
│   ├── gap_tools.py        # GapAnalysis tool wrappers
│   ├── callgraph_tools.py  # CallGraphAnalyzer tool wrappers
│   ├── semantic_tools.py   # SemanticDetector tool wrappers
│   ├── dependency_tools.py # DependencyAnalyzer tool wrappers
│   ├── performance_tools.py # PerformanceAnalyzer tool wrappers
│   └── typeflow_tools.py   # TypeFlowAnalyzer tool wrappers
├── resources.py            # Resource handlers
├── types.py                # MCP-specific types
└── cache.py                # Analysis result caching

tests/mcp/
├── __init__.py
├── test_codebase_server.py  # Unit tests
├── test_index_tools.py      # Index tool tests
├── test_explorer_tools.py   # Explorer tool tests
├── test_gap_tools.py        # Gap analysis tool tests
├── test_callgraph_tools.py  # Call graph tool tests
├── test_semantic_tools.py    # Semantic detection tool tests
├── test_dependency_tools.py # Dependency tool tests
├── test_performance_tools.py # Performance tool tests
├── test_typeflow_tools.py   # Type flow tool tests
├── test_resources.py        # Resource tests
└── test_integration.py      # MCP client integration tests

scripts/
└── run_mcp_server.py        # CLI script to start MCP server
```

### Data Flow

```
AI Assistant (Claude/ChatGPT)
    ↓ MCP Protocol
FastMCP Server
    ↓
CodebaseIndex (existing)
    ↓
RDF Graph (index.ttl)
    ↓
Codebase Ontology Files
```

### Integration Points

1. **CodebaseIndex** (`src/kgcl/ontology/codebase_index.py`)
   - No changes required
   - MCP server wraps existing API

2. **Index Builder** (`scripts/build_codebase_index.py`)
   - No changes required
   - MCP server reads generated `index.ttl`

3. **CLI** (`src/kgcl/cli/`)
   - Optional: Add `kgc-mcp-server` command to start server

---

## Implementation Plan

### Phase 1: Core Server & Index Tools (Day 1-2)

1. **Setup FastMCP**
   - Add `fastmcp` to `[project.optional-dependencies]`
   - Create `src/kgcl/mcp/` directory structure
   - Basic server skeleton with stdio transport

2. **Index Tools Implementation**
   - Implement all 8 codebase index tools
   - Basic error handling
   - Resource handlers for index data

3. **Testing**
   - Unit tests for server initialization
   - Unit tests for all index tools
   - Test fixtures with sample index

### Phase 2: Ontology Explorer Tools (Day 2-3)

1. **Explorer Tools Implementation**
   - Implement all 5 ontology explorer tools
   - SPARQL query execution
   - Architecture export

2. **Resources**
   - `codebase://class/{fqn}` resource handler
   - `codebase://package/{package}` resource handler
   - `codebase://index/stats` resource handler
   - `ontology://architecture` resource handler

3. **Testing**
   - Unit tests for explorer tools
   - Integration tests with sample ontology

### Phase 3: Analysis Tools - Gap & Call Graph (Day 3-4)

1. **Gap Analysis Tools**
   - Implement all 4 gap analysis tools
   - Java/Python comparison logic
   - Coverage calculation

2. **Call Graph Analysis Tools**
   - Implement all 3 call graph tools
   - Call path detection
   - Orphaned method detection

3. **Testing**
   - Unit tests for gap analysis
   - Unit tests for call graph analysis
   - Test fixtures with sample Java/Python code

### Phase 4: Analysis Tools - Semantic & Dependency (Day 4-5)

1. **Semantic Detection Tools**
   - Implement all 3 semantic detection tools
   - AST fingerprinting integration
   - Algorithm comparison

2. **Dependency Analysis Tools**
   - Implement all 3 dependency tools
   - Dependency graph building
   - Circular dependency detection

3. **Testing**
   - Unit tests for semantic detection
   - Unit tests for dependency analysis

### Phase 5: Analysis Tools - Performance & Type Flow (Day 5-6)

1. **Performance Analysis Tools**
   - Implement all 2 performance tools
   - Complexity analysis
   - Regression detection

2. **Type Flow Analysis Tools**
   - Implement all 2 type flow tools
   - Type mapping logic
   - Type mismatch detection

3. **Testing**
   - Unit tests for performance analysis
   - Unit tests for type flow analysis

### Phase 6: Caching, CLI & Documentation (Day 6-7)

1. **Caching Layer**
   - Analysis result caching
   - Cache invalidation logic
   - Performance optimization

2. **CLI Integration**
   - `kgc-mcp-server` command
   - Configuration options (paths, transport, cache)

3. **Documentation**
   - README with setup guide
   - Usage examples for each tool category
   - Integration guide for AI assistants
   - API reference

4. **Final Testing**
   - End-to-end tests with all tools
   - Integration tests with MCP client
   - Performance benchmarks
   - Documentation review
   - Code quality checks (lint, type-check)

---

## API Specification

### Tool: `find_class`

**Description**: Find a Java class by its simple name or fully qualified name.

**Parameters**:
```json
{
  "class_name": {
    "type": "string",
    "description": "Class name (simple like 'YControlPanel' or fully qualified like 'org.yawlfoundation.yawl.controlpanel.YControlPanel')"
  }
}
```

**Returns**:
```json
{
  "fully_qualified": "org.yawlfoundation.yawl.controlpanel.YControlPanel",
  "class_name": "YControlPanel",
  "package_name": "org.yawlfoundation.yawl.controlpanel",
  "file_path": "org/yawlfoundation/yawl/controlpanel/YControlPanel.ttl",
  "comment": "Control panel for YAWL engine"
}
```

**Example**:
```python
# AI Assistant request
mcp__codebase__find_class({"class_name": "YControlPanel"})

# Response
{
  "fully_qualified": "org.yawlfoundation.yawl.controlpanel.YControlPanel",
  "class_name": "YControlPanel",
  "package_name": "org.yawlfoundation.yawl.controlpanel",
  "file_path": "org/yawlfoundation/yawl/controlpanel/YControlPanel.ttl"
}
```

### Tool: `get_inheritance_hierarchy`

**Description**: Get inheritance relationships for a class (extends, implements, subclasses).

**Parameters**:
```json
{
  "class_name": {
    "type": "string",
    "description": "Class name (simple or fully qualified)"
  }
}
```

**Returns**:
```json
{
  "extends": "JFrame",
  "implements": ["Serializable", "ActionListener"],
  "subclasses": ["YControlPanelExtended"]
}
```

### Resource: `codebase://class/{fqn}`

**URI Pattern**: `codebase://class/org.yawlfoundation.yawl.controlpanel.YControlPanel`

**Content Type**: `application/json`

**Content**:
```json
{
  "fully_qualified": "org.yawlfoundation.yawl.controlpanel.YControlPanel",
  "class_name": "YControlPanel",
  "package_name": "org.yawlfoundation.yawl.controlpanel",
  "file_path": "org/yawlfoundation/yawl/controlpanel/YControlPanel.ttl",
  "extends": "JFrame",
  "implements": [],
  "methods": ["main", "getComponentsPane", "showComponentsPane"],
  "fields": ["componentsPane", "outputPane"],
  "comment": "Control panel for YAWL engine"
}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/mcp/test_codebase_server.py
def test_server_initialization():
    """Server loads index on startup."""
    
def test_find_class_tool():
    """find_class tool returns correct class info."""
    
def test_find_classes_in_package_tool():
    """find_classes_in_package returns all classes."""
```

### Integration Tests

```python
# tests/mcp/test_integration.py
async def test_mcp_client_connection():
    """MCP client can connect to server."""
    
async def test_tool_execution():
    """Client can execute tools and get results."""
    
async def test_resource_access():
    """Client can access resources."""
```

### Performance Tests

```python
# tests/mcp/test_performance.py
def test_index_load_time():
    """Index loads in < 2 seconds."""
    
def test_tool_latency():
    """Tool execution < 100ms (p99)."""
```

---

## Dependencies

### New Dependencies

```toml
[project.optional-dependencies]
mcp = [
    "fastmcp>=2.0.0",  # MCP server framework
]
```

### Existing Dependencies (Already in Use)

- `rdflib>=7.0.0` - RDF graph operations
- `pyoxigraph>=0.5.2` - High-performance RDF store (for explorer)
- `javalang>=0.13.0` - Java parsing (for enhanced parsers)
- `click>=8.1.7` - CLI framework (for server command)

---

## Risks & Mitigations

### Risk 1: FastMCP API Changes
**Impact**: High - Core dependency  
**Mitigation**: Pin to stable version, monitor upstream changes

### Risk 2: Performance with Large Index
**Impact**: Medium - 863 classes may cause latency  
**Mitigation**: Benchmark early, optimize index loading, consider caching

### Risk 3: MCP Protocol Compatibility
**Impact**: Medium - Must work with Claude/ChatGPT  
**Mitigation**: Test with real MCP clients, follow MCP spec strictly

### Risk 4: Resource URI Conflicts
**Impact**: Low - URI patterns may conflict  
**Mitigation**: Use unique `codebase://` scheme, document clearly

---

## Future Enhancements

1. **Incremental Index Updates**
   - Watch for index file changes
   - Reload index automatically

2. **Caching Layer**
   - Cache frequently accessed classes
   - Reduce RDF graph queries

3. **WebSocket Transport**
   - Real-time updates for index changes
   - Streaming query results

4. **Advanced Search**
   - Semantic similarity search
   - Vector embeddings for classes

5. **Graph Visualization**
   - Export inheritance graphs
   - Visualize package relationships

---

## Success Metrics

- **Adoption**: MCP server used in 5+ AI assistant sessions
- **Performance**: 
  - 95% of index tool calls < 100ms
  - 95% of explorer tool calls < 500ms
  - 90% of analysis tool calls < 5s
- **Reliability**: 99.9% uptime for server
- **Coverage**: 
  - All 863 classes accessible via resources
  - All analysis tools functional
  - All tool categories documented
- **Documentation**: Complete with 10+ usage examples across all tool categories

---

## References

### External Documentation
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Spec](https://modelcontextprotocol.io)

### Codebase References

#### Index & Query Infrastructure
- `src/kgcl/ontology/codebase_index.py` - Codebase index API
- `scripts/build_codebase_index.py` - Index builder
- `ontology/codebase/README.md` - Codebase ontology documentation
- `src/kgcl/cli/query.py` - CLI query command
- `src/kgcl/daemon/kgcld.py` - Daemon query API

#### Analysis Tools
- `src/kgcl/yawl_ontology/explorer.py` - Ontology explorer
- `src/kgcl/yawl_ontology/gap_analyzer.py` - Gap analysis
- `src/kgcl/yawl_ontology/call_graph_analyzer.py` - Call graph analysis
- `src/kgcl/yawl_ontology/semantic_detector.py` - Semantic detection
- `src/kgcl/yawl_ontology/dependency_analyzer.py` - Dependency analysis
- `src/kgcl/yawl_ontology/performance_analyzer.py` - Performance analysis
- `src/kgcl/yawl_ontology/type_flow_analyzer.py` - Type flow analysis
- `src/kgcl/yawl_ontology/enhanced_java_parser.py` - Enhanced Java parser
- `src/kgcl/yawl_ontology/enhanced_python_analyzer.py` - Enhanced Python analyzer
- `src/kgcl/yawl_ontology/cli.py` - CLI for analysis tools

#### API Patterns
- `vendors/unrdf/sidecar/server/api/query.get.mjs` - Query API pattern
- `vendors/unrdf/docs/api/openapi.yaml` - OpenAPI specification pattern

---

## Approval

**Author**: AI Assistant  
**Date**: 2025-01-XX  
**Reviewers**: [TBD]  
**Status**: Draft → Review → Approved

