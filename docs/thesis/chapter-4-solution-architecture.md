# Chapter 4: The Ontology-Based Solution—Architecture and Innovation

[← Previous: Chapter 3](./chapter-3-challenges.md) | [Back to Contents](./README.md) | [Next: Chapter 5 →](./chapter-5-implementation.md)

---

## 4.1 Core Insight: Codebases as Knowledge Graphs

The breakthrough came from recognizing that **codebases are knowledge graphs**, not text files. This insight enabled semantic analysis impossible with text-based approaches.

### RDF/Turtle Representation

Every Java class becomes an RDF entity:

```turtle
# RDF/Turtle representation of YTask
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

yawl:YTask a yawl:Class ;
    yawl:extends yawl:YExternalNetElement ;
    yawl:implements yawl:YWorkItemProvider, yawl:Cancellable ;
    yawl:hasMethod yawl:YTask_fire, yawl:YTask_cancel, ... ;
    yawl:methodCount 242 .

yawl:YTask_fire a yawl:Method ;
    yawl:name "fire" ;
    yawl:returnType "void" ;
    yawl:parameter [
        yawl:name "enabledSet" ;
        yawl:type "Set<YIdentifier>"
    ] ;
    yawl:calls yawl:YNetRunner_continueIfPossible ;
    yawl:throws yawl:YStateException .
```

This representation enables **SPARQL queries** for semantic analysis:

```sparql
# Find all methods that call fire() directly or transitively
SELECT ?caller ?depth WHERE {
    ?caller yawl:calls+ yawl:YTask_fire .
    ?caller yawl:name ?name .
    # Calculate call depth
}
```

## 4.2 Delta Detector: Multi-Dimensional Analysis

We developed a **10-dimensional Delta Detector** system coordinating specialized analyzers. The implementation is in [`delta_detector.py`](../../src/kgcl/yawl_ontology/delta_detector.py).

### Architecture Overview

```python
class DeltaDetector:
    """Main orchestrator for 10-dimensional delta detection."""
    
    def __init__(
        self,
        java_root: Path,
        python_root: Path,
        ontology_path: Path | None = None,
    ) -> None:
        # Initialize parsers
        self.java_parser = EnhancedJavaParser()
        self.python_analyzer = EnhancedPythonCodeAnalyzer(python_root)
        
        # Initialize 10 specialized analyzers
        self.semantic_detector = SemanticDetector(...)
        self.call_graph_analyzer = CallGraphAnalyzer(...)
        self.type_flow_analyzer = TypeFlowAnalyzer(...)
        self.exception_analyzer = ExceptionAnalyzer(...)
        self.dependency_analyzer = DependencyAnalyzer(...)
        self.performance_analyzer = PerformanceAnalyzer(...)
        self.test_mapper = TestMapper(...)
        # ... more analyzers
```

### Dimension 1: Structural Deltas

Detects missing/mismatched classes, methods, signatures using the gap analyzer:

```python
def _detect_structural_deltas(
    self, 
    java_classes: list[JavaClass],
    python_classes: dict[str, PythonClass]
) -> StructuralDeltas:
    """Detect structural differences."""
    missing_classes = []
    missing_methods = []
    
    for java_cls in java_classes:
        py_cls = python_classes.get(java_cls.name)
        
        if not py_cls:
            missing_classes.append(ClassDelta(
                java_class=java_cls.name,
                severity=DeltaSeverity.HIGH,
                reason="Class not found in Python"
            ))
            continue
        
        # Compare methods with snake_case translation
        java_methods = {m.name for m in java_cls.methods}
        py_methods = {m.name for m in py_cls.methods}
        
        # Try both camelCase and snake_case
        java_methods_snake = {camel_to_snake(m) for m in java_methods}
        all_java = java_methods | java_methods_snake
        
        missing = all_java - py_methods
        if missing:
            for method in missing:
                missing_methods.append(MethodDelta(
                    java_class=java_cls.name,
                    java_method=method,
                    severity=DeltaSeverity.MEDIUM,
                    reason="Method not found"
                ))
```

**Key Innovation**: Snake_case translation eliminates false negatives (YVariable from 100% gap to 80% complete).

### Dimension 2: Semantic Deltas

Implemented in [`semantic_detector.py`](../../src/kgcl/yawl_ontology/semantic_detector.py). Uses AST fingerprinting to detect behavioral differences:

```python
class SemanticDetector:
    """Detect semantic differences using AST fingerprinting."""
    
    def _generate_fingerprint(
        self, 
        method: JavaMethodBody | PythonMethodBody, 
        is_java: bool
    ) -> str:
        """Generate semantic fingerprint from method body."""
        # Normalize the method body
        normalized = self._normalize_method_body(method, is_java)
        
        # Generate hash
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _normalize_method_body(self, method, is_java) -> str:
        """Normalize: remove variable names, preserve control flow."""
        # Use structural fingerprint
        return "|".join([
            f"complexity:{method.complexity}",
            f"loops:{method.has_loops}",
            f"recursion:{method.has_recursion}",
            f"calls:{len(method.call_sites)}",
        ])
```

**Example Detection**:

```java
// Java: Uses recursion
public void traverse(YNet net) {
    for (YExternalNetElement e : net.getElements()) {
        if (e instanceof YNet) {
            traverse((YNet) e);  // Recursive
        }
    }
}

# Python: Uses iteration (different algorithm!)
def traverse(net: YNet) -> None:
    stack = [net]
    while stack:
        current = stack.pop()
        if isinstance(current, YNet):
            stack.extend(current.elements)  # Iterative
```

**Delta Report**: "Algorithm change: `YNet.traverse()` changed from recursive to iterative. Verify stack overflow behavior matches."

**Similarity Comparison**:

```python
def _compare_fingerprints(self, fp1: str, fp2: str) -> float:
    """Jaccard similarity on character n-grams."""
    n = 3
    set1 = {fp1[i:i+n] for i in range(len(fp1) - n + 1)}
    set2 = {fp2[i:i+n] for i in range(len(fp2) - n + 1)}
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0
```

### Dimension 3: Call Graph Analysis

Implemented in [`call_graph_analyzer.py`](../../src/kgcl/yawl_ontology/call_graph_analyzer.py). Builds complete method call graphs:

```python
class CallGraphAnalyzer:
    """Analyze and compare call graphs."""
    
    def _build_call_graph(
        self, 
        classes: list[Any], 
        is_java: bool
    ) -> dict[tuple[str, str], set[tuple[str, str]]]:
        """Build call graph: (class, method) -> set of callees."""
        graph = defaultdict(set)
        
        for class_info in classes:
            for method in class_info.methods:
                caller_key = (class_info.name, method.name)
                
                for call_site in method.call_sites:
                    callee_class = call_site.callee_class or class_info.name
                    callee_name = call_site.callee_name
                    graph[caller_key].add((callee_class, callee_name))
        
        return dict(graph)
```

**Example Detection**:

```python
# Python method
def fire_work_item(item_id: str) -> None:
    item = get_work_item(item_id)  # Calls get_work_item()
    item.execute()

# Delta Report:
# "Orphaned call: fire_work_item() calls get_work_item(),
#  but get_work_item() is not implemented (stub only)"
```

**Impact**: Identified 47 broken call chains before runtime failures.

### Dimension 4: Type Flow Analysis

Implemented in [`type_flow_analyzer.py`](../../src/kgcl/yawl_ontology/type_flow_analyzer.py). Tracks type transformations:

```python
class TypeFlowAnalyzer:
    """Track type flows through method chains."""
    
    def _extract_type_flow(
        self, 
        class_name: str, 
        method: Any, 
        is_java: bool
    ) -> TypeFlow:
        """Extract type flow: inputs → transformations → output."""
        input_types = self._extract_parameter_types(method, is_java)
        output_type = self._normalize_type(method.return_type, is_java)
        
        # Extract transformations from call sites
        transformations = [
            f"calls:{call_site.callee_name}"
            for call_site in method.call_sites
        ]
        
        return TypeFlow(
            class_name=class_name,
            method_name=method.name,
            input_types=input_types,
            output_type=output_type,
            transformations=transformations,
        )
```

**Type Compatibility Checking**:

```python
def _are_compatible_types(self, java_type: str, python_type: str) -> bool:
    """Check Java/Python type compatibility."""
    # Direct match
    if java_type == python_type:
        return True
    
    # Numeric types compatible
    numeric_java = {"int", "long", "float", "double"}
    numeric_python = {"int", "float"}
    if java_type in numeric_java and python_type in numeric_python:
        return True
    
    # Collection types compatible
    collection_java = {"List", "Set", "Map"}
    collection_python = {"list", "set", "dict"}
    if java_type in collection_java and python_type in collection_python:
        return True
    
    return False
```

**Example Detection**:

```python
def get_enabled_tasks(net: YNet) -> list[YTask]:
    # Returns Set<YTask> in Java, list[YTask] in Python
    return list(net.get_tasks_by_state(TaskState.ENABLED))

# Delta Report:
# "Type flow change: Java returns Set<YTask>, Python returns list[YTask].
#  Verify callers don't rely on set uniqueness semantics."
```

**Impact**: Found 31 type mismatches, 8 would have caused runtime failures.

### Dimension 5: Exception Handling Deltas

Compares exception hierarchies and handling patterns:

```python
class ExceptionAnalyzer:
    """Compare exception handling between Java and Python."""
    
    def detect_deltas(
        self, 
        java_classes: list[Any], 
        python_classes: dict[str, Any]
    ) -> ExceptionDeltas:
        """Detect exception-related differences."""
        java_exceptions = self._extract_exception_hierarchy(java_classes)
        python_exceptions = self._extract_exception_hierarchy(python_classes)
        
        missing = java_exceptions.keys() - python_exceptions.keys()
        uncaught = self._find_uncaught_exceptions(...)
        
        return ExceptionDeltas(
            missing_exceptions=list(missing),
            uncaught_exceptions=uncaught
        )
```

**Example Detection**:

```java
// Java
public void loadSpec() throws YSpecificationException, IOException {
    if (!file.exists()) {
        throw new YSpecificationException("File not found");
    }
}

# Python: Wrong exception type!
def load_spec() -> None:
    if not file.exists():
        raise FileNotFoundError("File not found")  # Should be YSpecificationException

# Delta Report:
# "Exception hierarchy mismatch: Java throws YSpecificationException,
#  Python throws FileNotFoundError. Callers expecting YSpecificationException
#  will not catch this."
```

**Impact**: Fixed 19 exception handling mismatches.

### Dimensions 6-10: Additional Analyzers

**6. Dependency Analysis** (`dependency_analyzer.py`):
- Tracks import dependencies
- Detects circular dependencies
- Identifies missing transitive dependencies

**7. Performance Analysis** (`performance_analyzer.py`):
- Estimates algorithmic complexity (O(1), O(n), O(n²))
- Detects nested loops, recursion depth
- Compares Java vs Python performance characteristics

**8. Test Coverage Mapping** (`test_mapper.py`):
- Maps Java tests → Python tests
- Identifies untested methods
- Calculates coverage gaps

**9. Enhanced Java Parsing** (`enhanced_java_parser.py`):
- Extracts method bodies (AST nodes)
- Identifies call sites
- Tracks exception patterns
- Calculates cyclomatic complexity

**10. Enhanced Python Analysis** (`enhanced_python_analyzer.py`):
- Extracts type hints
- Analyzes method bodies
- Detects stubs and incomplete implementations
- Tracks call sites and exceptions

## 4.3 Multi-Layer Code Generation Architecture

Manual porting proved unsustainable. We developed a **4-layer generation pipeline**:

```
Layer 1: Structure Generation (Codegen Framework)
         ↓
Layer 2: Template-Based Bodies (Jinja2) [40% of methods]
         ↓
Layer 3: LLM-Assisted Complex Logic (Claude API) [50% of methods]
         ↓
Layer 4: RAG-Enhanced Critical Paths (Vector DB + LLM) [10% of methods]
         ↓
Layer 5: Validation Gates (Mypy, Ruff, Pytest)
```

### Layer 1: Structure Generation

Uses enhanced Java parser to extract class/method signatures:

```python
class EnhancedJavaParser:
    """Parse Java files to extract structure."""
    
    def parse_class(self, java_file: Path) -> JavaClass:
        """Parse Java class structure."""
        tree = javalang.parse.parse(java_file.read_text())
        
        # Extract methods
        methods = []
        for method in class_decl.methods:
            signature = self._extract_signature(method)
            body_ast = self._parse_body(method)
            
            methods.append(JavaMethod(
                name=method.name,
                parameters=signature.parameters,
                return_type=signature.return_type,
                throws=signature.throws,
                body_ast=body_ast
            ))
```

**Output**: Python class skeleton with correct signatures:

```python
# Generated from YTask.java
class YTask(YExternalNetElement):
    """Auto-generated from org.yawlfoundation.yawl.elements.YTask"""
    
    def fire(self, enabled_set: set[YIdentifier]) -> None:
        """Fire task with enabled tokens."""
        raise NotImplementedError("Auto-generated stub")
```

**Coverage**: 100% of classes/methods get correct signatures.

### Layer 2: Template-Based Generation

For simple patterns (getters, setters, delegators), use Jinja2 templates:

```jinja2
{# templates/method_bodies/getter.py.j2 #}
def get_{{ field_name }}(self) -> {{ return_type }}:
    """Get {{ field_name }}."""
    return self._{{ field_name }}
```

**Pattern Matching**:

```python
def classify_method_pattern(method: JavaMethod) -> MethodPattern | None:
    """Classify method by pattern."""
    # Getter pattern
    if (method.name.startswith("get") and 
        method.return_type != "void" and
        not method.parameters):
        field_name = camel_to_snake(method.name[3:])
        return GetterPattern(field_name=field_name)
    
    # Setter pattern
    if (method.name.startswith("set") and
        method.return_type == "void" and
        len(method.parameters) == 1):
        field_name = camel_to_snake(method.name[3:])
        return SetterPattern(field_name=field_name)
```

**Coverage**: 40% of methods (simple patterns).

### Layer 3: LLM-Assisted Generation

For complex business logic, use Claude API with structured prompts:

```python
class LLMAssistedGenerator:
    """Generate Python methods using Claude API."""
    
    def generate_method_body(
        self, 
        java_method: JavaMethod,
        context: LLMGenerationContext
    ) -> str:
        """Generate Python method from Java."""
        prompt = self._build_prompt(java_method, context)
        
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._extract_code(response.content[0].text)
```

**Prompt Structure**:

```
Translate this Java method to Python:

**Java Context:**
- Class: {java_class.name}
- Package: {java_class.package}
- Fields: {java_class.fields}

**Java Method:**
{java_method.signature}
{java_method.body}

**Python Requirements:**
- Use type hints (Python 3.13+)
- Use frozen dataclasses for immutability
- Match Java behavior exactly
- No TODOs or stubs
- Follow existing Python patterns

**Generate:**
Only output the Python method body. No explanations.
```

**Coverage**: 50% of methods (complex business logic).

### Layer 4: RAG-Enhanced Generation

For critical paths, use Retrieval-Augmented Generation:

```python
class RAGCodeGenerator:
    """Generate code using RAG."""
    
    def __init__(self):
        self.vector_store = ChromaDB(collection="yawl-methods")
        self.llm_generator = LLMAssistedGenerator(...)
        
        # Index all Java methods with embeddings
        self._index_java_methods()
    
    def generate_with_rag(
        self, 
        target_method: JavaMethod,
        top_k: int = 5
    ) -> str:
        """Generate using similar method examples."""
        # Retrieve similar methods
        query_embedding = self._embed_method(target_method)
        similar = self.vector_store.query(query_embedding, n_results=top_k)
        
        # Find existing Python implementations
        python_examples = self._find_python_examples(similar)
        
        # Build enhanced context
        context = LLMGenerationContext(
            java_method=target_method,
            example_transformations=list(zip(similar, python_examples))
        )
        
        return self.llm_generator.generate_method_body(target_method, context)
```

**Example RAG Retrieval**:

Query: `YNetRunner.continueIfPossible(YIdentifier)`

Top-5 Similar Methods:
1. `YNetRunner.start(YCaseID)` - Similar control flow (score: 0.92)
2. `YNetRunner.cancel(YWorkItem)` - Similar state management (score: 0.89)
3. `YTask.fire(Set<YIdentifier>)` - Similar identifier handling (score: 0.87)

**Result**: Higher consistency with existing codebase, 15% fewer review iterations.

**Coverage**: 10% of methods (critical paths).

### Layer 5: Validation Gates

Every generated method passes through quality gates:

```python
def validate_generated_code(
    python_file: Path,
    java_file: Path
) -> ValidationResult:
    """Validate generated Python against Java."""
    # 1. Type checking (mypy --strict)
    mypy_result = run_mypy(python_file, strict=True)
    
    # 2. Linting (all 400+ Ruff rules)
    ruff_result = run_ruff(python_file)
    
    # 3. Implementation lies detection
    lies_result = detect_implementation_lies(python_file)
    
    # 4. Test coverage (must have tests)
    test_result = run_pytest_with_coverage(python_file)
    
    # 5. Behavioral equivalence
    equivalence_result = verify_behavioral_equivalence(java_file, python_file)
    
    return ValidationResult(...)
```

**Validation Criteria**:
- ✓ Zero type errors (mypy --strict)
- ✓ Zero lint errors (Ruff all rules)
- ✓ Zero implementation lies
- ✓ 80%+ test coverage
- ✓ Tests use factory_boy (no mocks)
- ✓ Behavioral equivalence verified

**Rejection Rate**:
- Layer 2 (Templates): 2% (mostly type errors)
- Layer 3 (LLM): 18% (missing edge cases)
- Layer 4 (RAG): 8% (higher quality from examples)

## 4.4 FastMCP Integration (Future Work)

We designed (but have not yet implemented) a FastMCP server to expose code generation tools:

```python
# src/kgcl/codegen/mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP("YAWL Code Generation Server")

@mcp.tool
def parse_java_class(java_file: str) -> dict[str, Any]:
    """Parse Java class and extract methods."""
    return java_parser.parse_file(Path(java_file)).to_dict()

@mcp.tool
def generate_method_body_rag(
    java_method_signature: str,
    java_file: str,
    top_k: int = 5
) -> str:
    """Generate Python method using RAG."""
    return rag_generator.generate_with_rag(...)

@mcp.tool
def validate_generated_code(python_file: str) -> dict[str, Any]:
    """Validate generated Python code."""
    return validator.validate_file(Path(python_file)).to_dict()
```

**Benefits**:
- Multi-agent coordination
- IDE integration (Cursor/VS Code)
- CI/CD integration
- Remote access for distributed teams

---

[← Previous: Chapter 3](./chapter-3-challenges.md) | [Back to Contents](./README.md) | [Next: Chapter 5 →](./chapter-5-implementation.md)
