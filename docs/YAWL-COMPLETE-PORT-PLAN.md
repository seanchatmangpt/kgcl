# YAWL Complete Port - Comprehensive Implementation Plan

## Executive Summary

**Goal**: Complete 100% port of Java YAWL v5.2 to Python - all classes, all methods, full feature parity using automated code generation, RAG/LLM assistance, and systematic batch processing.

**Total Scope**:
- **7 Critical Classes**: 926 missing methods
- **65 Missing Classes**: Complete implementations from scratch
- **1 Stub Class**: CalendarEntry (24 methods)
- **Additional Partial Classes**: AbstractCodelet, YExternalNetElement, and others
- **Total Estimated Methods**: ~2,500+ methods across ~75 classes

**Approach**: 
- **Automated Generation**: Use existing codegen framework for method stubs and structure
- **RAG/LLM-Assisted**: Claude API for complex business logic translation
- **Template-Based**: Jinja2 templates for common patterns (getters, setters, DTOs)
- **Batch Processing**: Parallel processing of multiple classes/methods
- **Chicago School TDD**: All implementations tested with factory_boy

---

## Architecture: Multi-Layer Code Generation

### Layer 1: Automated Structure Generation
**Tool**: Existing `scripts/codegen/` framework
**Input**: Java source files from `vendors/yawl-v5.2/src/`
**Output**: Python class skeletons with method signatures, type hints, docstrings

### Layer 2: Template-Based Method Bodies
**Tool**: Jinja2 templates for common patterns
**Patterns**: Getters/setters, simple queries, data transformations
**Coverage**: ~40% of methods (simple patterns)

### Layer 3: RAG/LLM-Assisted Complex Logic
**Tool**: Claude API with semantic codegen strategy
**Input**: Java method bodies + context + examples
**Output**: Python method implementations with business logic
**Coverage**: ~50% of methods (complex business logic)

### Layer 4: Manual Refinement
**Tool**: Human review for edge cases
**Coverage**: ~10% of methods (critical paths, performance-sensitive)

---

## JIRA Ticket Structure (Expanded with Automation)

### Epic: YAWL-2000 - Automated Code Generation Infrastructure
**Description**: Set up automated code generation pipeline for systematic porting.

**Tickets**:
- YAWL-2001: Enhance Java Parser for Method Body Extraction
- YAWL-2002: Create Method Body Templates Library (50+ patterns)
- YAWL-2003: Integrate Claude API for LLM-Assisted Generation
- YAWL-2004: Build RAG System for Java→Python Pattern Retrieval
- YAWL-2005: Create Batch Processing Pipeline (parallel execution)
- YAWL-2006: Implement Quality Validation Pipeline (mypy, ruff, tests)
- YAWL-2007: Build FastMCP Server for Code Generation Tools (NEW)

---

## Sprint 1: Foundation Classes (Automated + Manual)

### YAWL-1001: YCondition - Complete Implementation (21 methods)
**Priority**: CRITICAL  
**Assignee**: Agent 1 + Codegen Pipeline  
**Story Points**: 5  
**Dependencies**: None

**Automation Strategy**:
1. **Structure Generation**: Use codegen to extract method signatures from Java
2. **Template Generation**: Use templates for token operations (add, remove, contains)
3. **LLM Generation**: Use Claude for complex logic (clone with net container handling)
4. **Manual Review**: Verify token storage matches Java YIdentifierBag behavior

**Files**:
- `src/kgcl/yawl/elements/y_condition.py` (enhance existing)
- `tests/yawl/elements/test_y_condition.py` (generate + enhance)
- Reference: `vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/YCondition.java`

**Acceptance Criteria**:
- All 21 methods implemented
- Tests verify token operations match Java behavior
- Gap analyzer shows 0 missing methods

---

### YAWL-1002: YVariable Part 1 - Automated Generation (25 methods)
**Priority**: CRITICAL  
**Assignee**: Agent 2 + Codegen Pipeline  
**Story Points**: 8  
**Dependencies**: None

**Automation Strategy**:
1. **Batch Generate**: Use codegen to generate all getter/setter methods from Java
2. **Template Fill**: Use templates for attribute management, type name parsing
3. **LLM Fill**: Use Claude for validation logic (checkValue, checkDataTypeValue)
4. **Verify**: Run gap analyzer to confirm all methods present

**Methods** (Auto-generated via templates):
- `addAttribute()`, `getAttributes()`, `setAttributes()`, `hasAttributes()`
- `getDataTypeName()`, `getDataTypeNameSpace()`, `getDataTypeNameUnprefixed()`, `getDataTypePrefix()`
- `getDefaultValue()`, `setDefaultValue()`, `getInitialValue()`, `setInitialValue()`
- `getDocumentation()`, `setDocumentation()`, `getElementName()`, `setElementName()`
- `getName()`, `setName()`, `getOrdering()`, `setOrdering()`
- `getPreferredName()`, `getParentDecomposition()`, `setParentDecomposition()`

**Files**:
- `src/kgcl/yawl/elements/y_decomposition.py` (YVariable class)
- `tests/yawl/elements/test_y_variable.py` (generated)
- Reference: `vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/data/YVariable.java`

**Acceptance Criteria**:
- 25 methods auto-generated and implemented
- All type hints correct
- Tests generated and passing

---

### YAWL-1003: YVariable Part 2 - LLM-Assisted (25 methods)
**Priority**: CRITICAL  
**Assignee**: Agent 3 + LLM Pipeline  
**Story Points**: 10  
**Dependencies**: YAWL-1002

**Automation Strategy**:
1. **LLM Generation**: Use Claude API to translate complex validation logic
2. **RAG Context**: Provide Java YVariable.verify() and related methods as context
3. **Pattern Matching**: Use existing Python validation patterns as examples
4. **Manual Review**: Verify XML serialization matches Java output

**Methods** (LLM-assisted):
- `checkDataTypeValue()`, `checkValue()` - Complex validation logic
- `clone()`, `compareTo()` - Deep copy and comparison
- `isMandatory()`, `setMandatory()`, `isOptional()`, `setOptional()`, `isRequired()`
- `isEmptyTyped()`, `setEmptyTyped()`, `isUntyped()`, `setUntyped()`, `isUserDefinedType()`
- `getLogPredicate()`, `setLogPredicate()`
- `toXML()`, `toXMLGuts()`, `toString()` - XML serialization
- `usesElementDeclaration()`, `usesTypeDeclaration()`
- `verify()` - Complex validation with schema checking

**Files**:
- `src/kgcl/yawl/elements/y_decomposition.py` (YVariable class)
- `tests/yawl/elements/test_y_variable.py` (enhanced)
- Reference: `vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/data/YVariable.java`

**LLM Prompt Template**:
```
Translate Java YVariable method to Python:

Java Context:
- Class: YVariable (data container for workflow variables)
- Fields: _dataTypeName, _name, _initialValue, _defaultValue, _attributes
- Related: YDecomposition, YAttributeMap, XSDType, YInternalType

Java Method:
{method_signature}
{method_body}

Python Requirements:
- Use frozen dataclasses where appropriate
- Full type hints (Python 3.13+)
- Match Java behavior exactly
- Use existing Python utilities (jdom_util, saxon_util)
- No TODOs or stubs

Examples:
{similar_transformations}
```

**Acceptance Criteria**:
- 25 methods implemented via LLM + manual review
- Validation logic matches Java behavior
- XML serialization produces identical output
- Gap analyzer shows 0 missing methods

---

## Sprint 2: Task and Work Item Classes (Batch Processing)

### YAWL-1004: YTask Lifecycle - Batch Generation (60 methods)
**Priority**: CRITICAL  
**Assignee**: Agent 4 + Batch Processor  
**Story Points**: 15  
**Dependencies**: None

**Automation Strategy**:
1. **Batch Parse**: Extract all 60 method signatures from Java YTask.java
2. **Template Generation**: Generate method stubs with correct signatures
3. **Pattern Classification**: Categorize methods (simple vs complex)
4. **Parallel LLM**: Use Claude API in parallel for complex methods
5. **Batch Validation**: Run mypy, ruff, tests in parallel

**Method Categories**:
- **Template-Based** (30 methods): Simple getters, setters, state queries
- **LLM-Assisted** (25 methods): Complex lifecycle logic, cancellation, completion
- **Manual** (5 methods): Critical path methods requiring performance optimization

**Batch Processing Script**:
```python
from scripts.codegen.batch_process import BatchProcessor
from scripts.codegen.llm_generator import LLMAssistedGenerator

# 1. Parse all methods from Java
java_file = Path("vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/YTask.java")
methods = java_parser.extract_methods(java_file)

# 2. Classify by complexity
simple_methods = [m for m in methods if is_simple_pattern(m)]
complex_methods = [m for m in methods if is_complex_logic(m)]

# 3. Generate simple methods via templates
for method in simple_methods:
    python_code = template_generator.generate(method)
    write_method(python_code)

# 4. Generate complex methods via LLM (parallel)
llm_gen = LLMAssistedGenerator(api_key=os.getenv("ANTHROPIC_API_KEY"))
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(llm_gen.generate_method_body, m, context): m
        for m in complex_methods
    }
    for future in as_completed(futures):
        method = futures[future]
        python_code = future.result()
        write_method(python_code)

# 5. Batch validate
batch_validate(generated_files)
```

**Files**:
- `src/kgcl/yawl/elements/y_task.py` (enhance existing)
- `tests/yawl/elements/test_y_task_lifecycle.py` (generated)
- Reference: `vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/YTask.java`

**Acceptance Criteria**:
- 60 methods generated and implemented
- All methods pass type checking and linting
- Tests verify lifecycle behavior matches Java

---

### YAWL-1005-1007: YTask Validation/Query/Mutation - Batch LLM (180 methods)
**Priority**: CRITICAL  
**Assignee**: Agents 5-7 + LLM Pipeline  
**Story Points**: 45 (15 each)  
**Dependencies**: YAWL-1004

**Automation Strategy**: Same as YAWL-1004 but for validation, query, and mutation methods.

---

### YAWL-1008-1011: YWorkItem - Batch Processing (229 methods)
**Priority**: CRITICAL  
**Assignee**: Agents 8-11 + Batch Processor  
**Story Points**: 60 (15 each)  
**Dependencies**: YAWL-1004

**Automation Strategy**: 
- Use batch processor to generate all 229 methods in parallel
- LLM-assisted for complex timer/deadline logic
- Template-based for simple data operations

---

## Sprint 3: Engine and Runner Classes (RAG-Enhanced)

### YAWL-1012-1014: YNetRunner - RAG-Assisted Generation (173 methods)
**Priority**: CRITICAL  
**Assignee**: Agents 12-14 + RAG System  
**Story Points**: 50  
**Dependencies**: YAWL-1004

**RAG Strategy**:
1. **Build Knowledge Base**: Index all Java YNetRunner methods with semantic embeddings
2. **Retrieve Similar Patterns**: For each missing method, find similar Java methods
3. **LLM Generation with RAG**: Provide retrieved examples as context to Claude
4. **Verify Against Java**: Compare generated Python with Java behavior

**RAG Implementation**:
```python
from kgcl.codegen.rag import RAGCodeGenerator

rag_gen = RAGCodeGenerator(
    java_source_dir=Path("vendors/yawl-v5.2/src"),
    python_source_dir=Path("src/kgcl/yawl"),
    embedding_model="text-embedding-3-small"
)

# For each missing method
for method in missing_methods:
    # 1. Retrieve similar Java methods
    similar_methods = rag_gen.retrieve_similar(
        method_signature=method.signature,
        top_k=5
    )
    
    # 2. Retrieve similar Python implementations (if any)
    similar_python = rag_gen.retrieve_python_examples(
        method_pattern=method.pattern,
        top_k=3
    )
    
    # 3. Generate with RAG context
    python_code = rag_gen.generate_with_rag(
        java_method=method,
        java_examples=similar_methods,
        python_examples=similar_python
    )
    
    # 4. Validate and write
    validate_and_write(python_code)
```

**Files**:
- `src/kgcl/yawl/engine/y_net_runner.py` (enhance existing)
- `tests/yawl/engine/test_y_net_runner_*.py` (generated)
- Reference: `vendors/yawl-v5.2/src/org/yawlfoundation/yawl/engine/YNetRunner.java`

**Acceptance Criteria**:
- 173 methods generated via RAG + LLM
- All methods match Java behavior
- Performance within 2x of Java

---

### YAWL-1015-1019: YDecomposition, YEngine - RAG Batch (148 methods)
**Priority**: HIGH  
**Assignee**: Agents 15-19 + RAG Pipeline  
**Story Points**: 45  
**Dependencies**: YAWL-1002, YAWL-1003, YAWL-1014

**Same RAG strategy as YAWL-1012-1014**

---

## Sprint 4: Missing Classes (Complete New Implementations)

### YAWL-1020-1084: 65 Missing Classes - Automated Generation
**Priority**: HIGH  
**Assignee**: Multiple Agents + Full Automation Pipeline  
**Story Points**: 200 (3 per class average)  
**Dependencies**: Sprint 1-3 foundation

**Automation Strategy**:
1. **Class Discovery**: Use gap analyzer to identify all 65 missing classes
2. **Java Parsing**: Parse each Java class to extract full structure
3. **Python Generation**: Use codegen to generate complete Python class
4. **LLM Implementation**: Use Claude to implement all methods
5. **Batch Validation**: Validate all classes in parallel

**Batch Processing**:
```python
from scripts.codegen.batch_process import BatchProcessor
from scripts.codegen.llm_generator import LLMAssistedGenerator

# 1. Discover missing classes
gap_analyzer = YawlGapAnalyzer(ontology_path, python_root)
missing_classes = gap_analyzer.get_missing_classes()

# 2. Process in batches of 10
batch_processor = BatchProcessor(max_workers=10)
for batch in chunk(missing_classes, 10):
    results = batch_processor.process_batch(
        java_files=[find_java_file(c) for c in batch],
        generator=LLMAssistedGenerator(),
        output_dir=Path("src/kgcl/yawl")
    )
    
    # 3. Validate batch
    validate_batch(results)
```

**Classes to Generate** (prioritized):
1. **High Priority** (20 classes): Core engine classes
   - YNetElement, YEvent, YAWLException, YSession, etc.
2. **Medium Priority** (25 classes): Service/Client classes
   - DocumentStoreClient, MailServiceClient, ResourceGatewayClient, etc.
3. **Low Priority** (20 classes): UI/Utility classes
   - DesignInternalFrame, ProgressPanel, UpdateTableModel, etc.

**Acceptance Criteria**:
- All 65 classes generated with complete implementations
- All methods match Java signatures
- All classes pass type checking and linting
- Integration tests verify behavior

---

## Automation Infrastructure Tickets

### YAWL-2001: Enhance Java Parser for Method Body Extraction
**Priority**: CRITICAL  
**Assignee**: Infrastructure Team  
**Story Points**: 8

**Tasks**:
1. Extend `scripts/codegen/java_parser.py` to extract method bodies (not just signatures)
2. Parse control flow (if/else, loops, try/catch)
3. Extract variable declarations and types
4. Build symbol table for method context

**Files**:
- `scripts/codegen/java_parser.py` (enhance)
- `scripts/codegen/semantic_analyzer.py` (new)
- `tests/codegen/test_java_parser.py` (enhance)

---

### YAWL-2002: Create Method Body Templates Library
**Priority**: CRITICAL  
**Assignee**: Infrastructure Team  
**Story Points**: 13

**Tasks**:
1. Create 50+ Jinja2 templates for common patterns:
   - Getter methods: `get{Field}() → {field}`
   - Setter methods: `set{Field}(value) → self.{field} = value`
   - Query methods: `is{State}() → return self.{state}`
   - Collection operations: `add{Item}()`, `remove{Item}()`, `get{Items}()`
   - Validation methods: `check{Constraint}()`, `validate{Type}()`
2. Template matching logic (classify method by pattern)
3. Template application pipeline

**Files**:
- `scripts/codegen/templates/method_bodies/` (new directory)
- `scripts/codegen/template_matcher.py` (new)
- `tests/codegen/test_template_matcher.py` (new)

---

### YAWL-2003: Integrate Claude API for LLM-Assisted Generation
**Priority**: CRITICAL  
**Assignee**: Infrastructure Team  
**Story Points**: 13

**Tasks**:
1. Create `scripts/codegen/llm_generator.py` based on semantic-codegen-strategy.md
2. Implement prompt building with context and examples
3. Add retry logic and error handling
4. Implement code extraction from LLM responses
5. Add rate limiting and cost tracking

**Files**:
- `scripts/codegen/llm_generator.py` (new)
- `scripts/codegen/prompt_builder.py` (new)
- `tests/codegen/test_llm_generator.py` (new)

**LLM Integration**:
```python
from anthropic import Anthropic
from scripts.codegen.llm_generator import LLMAssistedGenerator

generator = LLMAssistedGenerator(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-4-5-20250929"
)

python_code = generator.generate_method_body(
    java_method=method,
    context=LLMGenerationContext(
        java_class=java_class,
        symbol_table=symbol_table,
        example_transformations=examples
    )
)
```

---

### YAWL-2004: Build RAG System for Java→Python Pattern Retrieval
**Priority**: HIGH  
**Assignee**: Infrastructure Team  
**Story Points**: 21

**Tasks**:
1. Create vector database (ChromaDB or similar) for Java method embeddings
2. Index all Java methods from `vendors/yawl-v5.2/src/`
3. Index existing Python implementations for pattern matching
4. Implement semantic search (find similar methods)
5. Build RAG pipeline (retrieve → augment → generate)

**Files**:
- `scripts/codegen/rag/` (new directory)
- `scripts/codegen/rag/vector_store.py` (new)
- `scripts/codegen/rag/retriever.py` (new)
- `scripts/codegen/rag/generator.py` (new)
- `tests/codegen/rag/` (new)

**RAG Architecture**:
```
Java Source Files
    ↓
[Semantic Analyzer] → Method Embeddings
    ↓
[Vector Store] → ChromaDB/FAISS
    ↓
[Query] → Missing Method Signature
    ↓
[Retriever] → Top-K Similar Methods
    ↓
[LLM Generator] → Python Implementation
    ↓
[Validator] → Type Check + Lint + Test
    ↓
Generated Python Code
```

---

### YAWL-2005: Create Batch Processing Pipeline
**Priority**: HIGH  
**Assignee**: Infrastructure Team  
**Story Points**: 13

**Tasks**:
1. Enhance `scripts/codegen/batch_process.py` for method-level processing
2. Add parallel LLM generation (rate-limited)
3. Implement progress tracking and error recovery
4. Add batch validation (mypy, ruff, tests in parallel)

**Files**:
- `scripts/codegen/batch_process.py` (enhance)
- `scripts/codegen/parallel_llm.py` (new)
- `tests/codegen/test_batch_process.py` (enhance)

---

### YAWL-2006: Implement Quality Validation Pipeline
**Priority**: CRITICAL  
**Assignee**: Infrastructure Team  
**Story Points**: 8

**Tasks**:
1. Integrate existing `scripts/codegen/validator.py` into generation pipeline
2. Add automatic fixes (ruff format, type narrowing)
3. Add behavior verification (compare with Java output)
4. Create quality dashboard (metrics tracking)

**Files**:
- `scripts/codegen/validator.py` (enhance)
- `scripts/codegen/quality_dashboard.py` (new)
- `tests/codegen/test_validator.py` (enhance)

---

### YAWL-2007: Build FastMCP Server for Code Generation Tools
**Priority**: HIGH  
**Assignee**: Infrastructure Team  
**Story Points**: 13  
**Dependencies**: YAWL-2001, YAWL-2003, YAWL-2004

**Description**: Create FastMCP server that exposes code generation tools as MCP tools, enabling multiple agents to interact with the generation pipeline via standardized MCP protocol.

**Why FastMCP**:
- **Unified Interface**: Single MCP server exposes all codegen tools (parser, LLM, RAG, validator)
- **Multi-Agent Support**: Multiple coding agents can use the same tools concurrently
- **Composable Architecture**: Mount different generators as separate MCP servers
- **Production-Ready**: FastMCP provides authentication, deployment, and monitoring out-of-the-box

**Tasks**:
1. Install FastMCP: `uv add fastmcp`
2. Create `src/kgcl/codegen/mcp_server.py` with FastMCP server
3. Expose code generation tools as MCP tools:
   - `parse_java_class` - Parse Java file and extract methods
   - `generate_method_stub` - Generate Python method signature
   - `generate_method_body_template` - Fill method body from template
   - `generate_method_body_llm` - Generate method body via Claude API
   - `generate_method_body_rag` - Generate method body via RAG + LLM
   - `validate_generated_code` - Run mypy, ruff, tests
   - `batch_generate_methods` - Process multiple methods in parallel
4. Create FastMCP client wrapper for existing codegen scripts
5. Add authentication (optional, for production deployment)
6. Deploy as HTTP/SSE server for remote access

**FastMCP Server Implementation**:
```python
# src/kgcl/codegen/mcp_server.py
from fastmcp import FastMCP
from pathlib import Path
from typing import Any

from kgcl.codegen.parsers.java_parser import JavaParser
from kgcl.codegen.llm_generator import LLMAssistedGenerator
from kgcl.codegen.rag.generator import RAGCodeGenerator
from kgcl.codegen.validator import CodeValidator

mcp = FastMCP("YAWL Code Generation Server")

# Initialize components
java_parser = JavaParser()
llm_generator = LLMAssistedGenerator(api_key=os.getenv("ANTHROPIC_API_KEY"))
rag_generator = RAGCodeGenerator()
validator = CodeValidator(strict=True)

@mcp.tool
def parse_java_class(java_file: str) -> dict[str, Any]:
    """Parse Java class and extract method signatures.
    
    Parameters
    ----------
    java_file : str
        Path to Java source file
        
    Returns
    -------
    dict[str, Any]
        Parsed class metadata with methods, fields, etc.
    """
    java_path = Path(java_file)
    java_class = java_parser.parse_file(java_path)
    return java_parser.to_dict(java_class)

@mcp.tool
def generate_method_stub(
    class_name: str,
    method_name: str,
    return_type: str,
    parameters: list[dict[str, str]]
) -> str:
    """Generate Python method stub with type hints.
    
    Parameters
    ----------
    class_name : str
        Python class name
    method_name : str
        Method name (snake_case)
    return_type : str
        Return type (Python type hint)
    parameters : list[dict[str, str]]
        List of parameter dicts with 'name' and 'type'
        
    Returns
    -------
    str
        Python method stub code
    """
    params_str = ", ".join(f"{p['name']}: {p['type']}" for p in parameters)
    return f"    def {method_name}(self, {params_str}) -> {return_type}:\n        \"\"\"TODO: Implement {method_name}.\"\"\"\n        raise NotImplementedError()"

@mcp.tool
def generate_method_body_llm(
    java_method_body: str,
    java_class_context: dict[str, Any],
    python_method_signature: str
) -> str:
    """Generate Python method body using Claude API.
    
    Parameters
    ----------
    java_method_body : str
        Java method body source code
    java_class_context : dict[str, Any]
        Java class context (fields, imports, etc.)
    python_method_signature : str
        Python method signature to implement
        
    Returns
    -------
    str
        Generated Python method body
    """
    from kgcl.codegen.models import JavaMethod, JavaClass, LLMGenerationContext
    
    java_method = JavaMethod(
        name=python_method_signature.split("(")[0].split("def ")[1],
        body_ast=None,  # Simplified
        return_type="str",  # Would extract from signature
        parameters=[]
    )
    
    java_class = JavaClass(**java_class_context)
    context = LLMGenerationContext(
        java_class=java_class,
        java_method=java_method,
        symbol_table={},
        example_transformations=[]
    )
    
    return llm_generator.generate_method_body(java_method, context)

@mcp.tool
def generate_method_body_rag(
    java_method_signature: str,
    java_file: str,
    top_k: int = 5
) -> str:
    """Generate Python method body using RAG + LLM.
    
    Parameters
    ----------
    java_method_signature : str
        Java method signature
    java_file : str
        Path to Java source file
    top_k : int, default=5
        Number of similar methods to retrieve
        
    Returns
    -------
    str
        Generated Python method body
    """
    return rag_generator.generate_with_rag(
        java_method_signature=java_method_signature,
        java_file=Path(java_file),
        top_k=top_k
    )

@mcp.tool
def validate_generated_code(
    python_file: str,
    check_types: bool = True,
    check_lint: bool = True,
    check_tests: bool = True
) -> dict[str, Any]:
    """Validate generated Python code.
    
    Parameters
    ----------
    python_file : str
        Path to generated Python file
    check_types : bool, default=True
        Run mypy type checking
    check_lint : bool, default=True
        Run ruff linting
    check_tests : bool, default=True
        Run pytest tests
        
    Returns
    -------
    dict[str, Any]
        Validation results with pass/fail status and errors
    """
    result = validator.validate_file(
        Path(python_file),
        check_types=check_types,
        check_lint=check_lint,
        check_tests=check_tests
    )
    return {
        "passed": result.passed,
        "type_errors": result.type_errors,
        "lint_errors": result.lint_errors,
        "test_failures": result.test_failures
    }

@mcp.tool
def batch_generate_methods(
    java_file: str,
    method_names: list[str],
    generation_strategy: str = "auto"
) -> dict[str, Any]:
    """Batch generate multiple methods from Java class.
    
    Parameters
    ----------
    java_file : str
        Path to Java source file
    method_names : list[str]
        List of method names to generate
    generation_strategy : str, default="auto"
        Strategy: "template", "llm", "rag", or "auto"
        
    Returns
    -------
    dict[str, Any]
        Results for each method with generated code and validation status
    """
    # Implementation would use batch processor
    from kgcl.codegen.batch_process import BatchProcessor
    
    processor = BatchProcessor(max_workers=10)
    results = processor.process_methods(
        java_file=Path(java_file),
        method_names=method_names,
        strategy=generation_strategy
    )
    
    return {
        method_name: {
            "code": result.python_code,
            "validated": result.validated,
            "errors": result.errors
        }
        for method_name, result in results.items()
    }

if __name__ == "__main__":
    # Run as HTTP server for remote access
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
    
    # Or as stdio for local CLI usage
    # mcp.run(transport="stdio")
```

**FastMCP Client Usage** (for agents):
```python
# Example: Agent using FastMCP client to generate code
from fastmcp import Client

async def generate_yvariable_methods():
    async with Client("http://localhost:8000/mcp") as client:
        # 1. Parse Java class
        java_class = await client.call_tool(
            "parse_java_class",
            {"java_file": "vendors/yawl-v5.2/src/.../YVariable.java"}
        )
        
        # 2. Generate methods in batch
        results = await client.call_tool(
            "batch_generate_methods",
            {
                "java_file": "vendors/yawl-v5.2/src/.../YVariable.java",
                "method_names": ["getDefaultValue", "setDefaultValue", "checkValue"],
                "generation_strategy": "auto"
            }
        )
        
        # 3. Validate generated code
        for method_name, result in results.items():
            validation = await client.call_tool(
                "validate_generated_code",
                {"python_file": result["output_file"]}
            )
            print(f"{method_name}: {validation['passed']}")
```

**Files**:
- `src/kgcl/codegen/mcp_server.py` (new)
- `src/kgcl/codegen/mcp_client.py` (new, wrapper)
- `tests/codegen/test_mcp_server.py` (new)
- `pyproject.toml` (add fastmcp dependency)

**Benefits**:
- **Multi-Agent Coordination**: Multiple agents can use the same codegen tools
- **Standardized Interface**: MCP protocol ensures consistent tool interface
- **Remote Access**: Deploy as HTTP server for distributed teams
- **Composable**: Mount different generators as separate servers
- **Production-Ready**: FastMCP handles auth, deployment, monitoring

**Acceptance Criteria**:
- FastMCP server exposes all codegen tools as MCP tools
- Multiple agents can use tools concurrently
- Server can run as stdio (local) or HTTP (remote)
- All tools have comprehensive tests
- Documentation for agent usage

---

## Implementation Workflow

### For Each Class/Method:

1. **Discovery**: Gap analyzer identifies missing methods
2. **Classification**: Pattern matcher categorizes method complexity
3. **Generation**:
   - Simple → Template-based generation
   - Medium → LLM-assisted generation
   - Complex → RAG + LLM generation
4. **Validation**: Automatic type check, lint, format, test
5. **Review**: Human review for critical paths
6. **Integration**: Merge into main codebase

### Batch Processing Example:

```bash
# Generate all YTask methods
uv run python scripts/codegen/batch_generate_methods.py \
    --class YTask \
    --java-file vendors/yawl-v5.2/src/org/yawlfoundation/yawl/elements/YTask.java \
    --output-dir src/kgcl/yawl/elements \
    --use-llm \
    --use-rag \
    --parallel 10

# Validate generated code
uv run poe validate-code src/kgcl/yawl/elements/y_task.py

# Run tests
uv run poe test tests/yawl/elements/test_y_task*.py
```

---

## Success Metrics

- **Coverage**: 100% of 2,500+ methods implemented
- **Automation**: 80%+ generated automatically (templates + LLM)
- **Quality**: 100% type coverage, all Ruff rules pass
- **Tests**: 80%+ test coverage, all tests passing
- **Performance**: Within 2x of Java execution time
- **Java Parity**: 100% behavior equivalence

---

## Dependencies and Sequencing

**Infrastructure First** (can run in parallel):
- YAWL-2001 → YAWL-2002 → YAWL-2003 → YAWL-2004 → YAWL-2005 → YAWL-2006

**Then Implementation** (can use automation):
- Sprint 1: Foundation (YAWL-1001, 1002, 1003) - Manual + Templates
- Sprint 2: Task/WorkItem (YAWL-1004-1011) - Batch LLM
- Sprint 3: Engine/Runner (YAWL-1012-1019) - RAG + LLM
- Sprint 4: Missing Classes (YAWL-1020-1084) - Full Automation

**Maximum Parallelism**: 
- Infrastructure: 6 agents (one per ticket)
- Implementation: 19 agents (one per ticket) + automation pipeline

---

## Cost Estimation

**LLM API Costs** (Claude Sonnet 4.5):
- Average method: ~500 tokens input, ~200 tokens output
- 1,500 complex methods × $0.003/1K input + $0.015/1K output = ~$15
- **Total LLM Cost**: ~$20-30 for complete port

**Infrastructure**:
- Vector database: Free (ChromaDB local) or ~$50/month (cloud)
- Compute: Existing infrastructure

**Total Automation Cost**: <$100 for complete 2,500+ method port

---

## Risk Mitigation

**Risk**: LLM generates incorrect code
- **Mitigation**: Comprehensive test suite + behavior verification + human review

**Risk**: Template patterns don't match all methods
- **Mitigation**: Expand template library iteratively, fallback to LLM

**Risk**: RAG retrieval returns irrelevant examples
- **Mitigation**: Fine-tune embeddings, use hybrid search (semantic + keyword)

**Risk**: Batch processing causes rate limits
- **Mitigation**: Implement exponential backoff, queue system, parallel workers with limits

---

## Success Criteria

✅ **Automation Coverage**: 80%+ methods generated automatically  
✅ **Code Quality**: 100% type coverage, all Ruff rules pass  
✅ **Test Coverage**: 80%+ coverage, all tests passing  
✅ **Java Parity**: 100% behavior equivalence  
✅ **Performance**: Within 2x of Java  
✅ **Zero Technical Debt**: No TODOs, stubs, or placeholders

