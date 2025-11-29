# Semantic Code Generation Strategy: Java to Python/TypeScript

**Document Version**: 1.0
**Date**: 2025-11-28
**Purpose**: Comprehensive research and recommendations for semantic code generation from Java to Python/TypeScript for YAWL migration

---

## Executive Summary

This document provides a complete strategy for semantic code generation from Java to Python (backend/engine) and TypeScript/React (frontend). After analyzing **YAWL v5.2** codebase (100+ Java classes, ~763 lines per file average) and evaluating parsing libraries, generation patterns, and quality assurance approaches, we recommend a **hybrid approach**:

- **Backend (Java → Python)**: Tree-sitter-java parsing + AST-based generation + LLM-assisted complex logic
- **Frontend (Java/Vaadin → TypeScript/React)**: Template-based component mapping + manual business logic extraction
- **Quality Assurance**: Type checking + automated tests + pattern verification

**Key Finding**: Semantic code generation requires understanding *behavior*, not just syntax. Tools that only parse syntax (javalang, tree-sitter) must be augmented with semantic analysis (type resolution, call graphs, control flow) to generate correct Python/TypeScript.

---

## 1. Java Parsing Libraries: Evaluation

### 1.1 Library Comparison

| Library | Type | Semantic Capabilities | Best For | Limitations |
|---------|------|----------------------|----------|-------------|
| **tree-sitter-java** | Grammar-based parser | ✅ Full AST, Fast, Incremental | Large codebases, performance-critical | ❌ No type resolution, no symbol table |
| **javalang** | Pure Python parser | ✅ Simple API, AST access | Small scripts, quick prototypes | ❌ Incomplete Java 11+ support, no type inference |
| **py4j** | Java-Python bridge | ✅ Full Java semantics (uses JDT) | Complex semantic analysis | ❌ Requires JVM runtime, heavy dependency |
| **srcML** | Multi-language parser | ✅ XML AST, language-agnostic | Cross-language analysis | ❌ XML overhead, no semantic info |

### 1.2 Recommended Choice: **tree-sitter-java**

**Rationale:**
1. **Performance**: Incremental parsing, handles 100+ file codebases efficiently
2. **Accuracy**: Tree-sitter grammar is battle-tested, supports Java 11-17 features
3. **Python Integration**: `py-tree-sitter` bindings work seamlessly
4. **Ecosystem**: Growing ecosystem of tree-sitter tools

**Example Usage:**

```python
from tree_sitter import Language, Parser
import tree_sitter_java as tsjava

# Load Java grammar
JAVA_LANGUAGE = Language(tsjava.language())
parser = Parser(JAVA_LANGUAGE)

# Parse Java source
source_code = b"""
package org.yawlfoundation.yawl.authentication;

import java.util.UUID;

public class YSession extends YAbstractSession {
    private YClient _client;

    public YSession(long timeOutSeconds) {
        super(timeOutSeconds);
    }

    public String getURI() {
        return null;
    }
}
"""

tree = parser.parse(source_code)
root_node = tree.root_node

# Traverse AST
def traverse(node, depth=0):
    print("  " * depth + node.type, node.text[:50] if node.text else "")
    for child in node.children:
        traverse(child, depth + 1)

traverse(root_node)
```

**Output:**
```
program
  package_declaration
    scoped_identifier org.yawlfoundation.yawl.authentication
  import_declaration
    scoped_identifier java.util.UUID
  class_declaration
    modifiers public
    identifier YSession
    superclass YAbstractSession
    class_body
      field_declaration
        modifiers private
        type_identifier YClient
        variable_declarator _client
      method_declaration
        modifiers public
        constructor_declaration
        ...
```

### 1.3 Semantic Extraction with Tree-Sitter

**Challenge**: Tree-sitter provides syntax tree, NOT semantic information (types, symbols, call graphs).

**Solution**: Build semantic analyzer on top of tree-sitter:

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class JavaClass:
    """Semantic representation of Java class."""
    package: str
    name: str
    extends: Optional[str]
    implements: List[str]
    fields: List['JavaField']
    methods: List['JavaMethod']
    modifiers: List[str]

@dataclass(frozen=True)
class JavaMethod:
    """Semantic representation of Java method."""
    name: str
    return_type: str
    parameters: List['JavaParameter']
    modifiers: List[str]
    throws: List[str]
    body_ast: Any  # Tree-sitter node

@dataclass(frozen=True)
class JavaField:
    """Semantic representation of Java field."""
    name: str
    type: str
    modifiers: List[str]
    initializer: Optional[str]

class JavaSemanticAnalyzer:
    """Extracts semantic information from tree-sitter AST."""

    def __init__(self, parser: Parser):
        self.parser = parser
        self.symbol_table: Dict[str, JavaClass] = {}

    def analyze_file(self, source: bytes) -> JavaClass:
        """Parse Java file and extract semantic class representation."""
        tree = self.parser.parse(source)
        root = tree.root_node

        # Extract package
        package = self._extract_package(root)

        # Extract imports (for type resolution)
        imports = self._extract_imports(root)

        # Extract class declaration
        class_node = self._find_class_declaration(root)
        if not class_node:
            raise ValueError("No class declaration found")

        # Extract class metadata
        class_name = self._get_class_name(class_node)
        extends = self._get_superclass(class_node)
        implements = self._get_interfaces(class_node)
        modifiers = self._get_modifiers(class_node)

        # Extract fields
        fields = self._extract_fields(class_node)

        # Extract methods
        methods = self._extract_methods(class_node)

        return JavaClass(
            package=package,
            name=class_name,
            extends=extends,
            implements=implements,
            fields=fields,
            methods=methods,
            modifiers=modifiers
        )

    def _extract_package(self, root) -> str:
        """Extract package declaration."""
        for node in root.children:
            if node.type == "package_declaration":
                # Find scoped_identifier child
                for child in node.children:
                    if child.type == "scoped_identifier":
                        return child.text.decode('utf-8')
        return ""

    def _extract_imports(self, root) -> List[str]:
        """Extract import statements for type resolution."""
        imports = []
        for node in root.children:
            if node.type == "import_declaration":
                for child in node.children:
                    if child.type == "scoped_identifier":
                        imports.append(child.text.decode('utf-8'))
        return imports

    def _find_class_declaration(self, root):
        """Find class declaration node."""
        for node in root.children:
            if node.type == "class_declaration":
                return node
        return None

    def _get_class_name(self, class_node) -> str:
        """Extract class name."""
        for child in class_node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return ""

    def _get_superclass(self, class_node) -> Optional[str]:
        """Extract superclass (extends clause)."""
        for child in class_node.children:
            if child.type == "superclass":
                # Find type_identifier
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        return subchild.text.decode('utf-8')
        return None

    def _get_interfaces(self, class_node) -> List[str]:
        """Extract interfaces (implements clause)."""
        interfaces = []
        for child in class_node.children:
            if child.type == "super_interfaces":
                # Find type_list
                for subchild in child.children:
                    if subchild.type == "type_list":
                        for type_node in subchild.children:
                            if type_node.type == "type_identifier":
                                interfaces.append(type_node.text.decode('utf-8'))
        return interfaces

    def _get_modifiers(self, node) -> List[str]:
        """Extract modifiers (public, private, static, etc.)."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    modifiers.append(mod.text.decode('utf-8'))
        return modifiers

    def _extract_fields(self, class_node) -> List[JavaField]:
        """Extract field declarations."""
        fields = []
        class_body = self._find_class_body(class_node)
        if not class_body:
            return fields

        for child in class_body.children:
            if child.type == "field_declaration":
                modifiers = self._get_modifiers(child)
                type_str = self._get_field_type(child)

                # Extract variable declarators
                for subchild in child.children:
                    if subchild.type == "variable_declarator":
                        name = self._get_variable_name(subchild)
                        initializer = self._get_initializer(subchild)
                        fields.append(JavaField(
                            name=name,
                            type=type_str,
                            modifiers=modifiers,
                            initializer=initializer
                        ))

        return fields

    def _extract_methods(self, class_node) -> List[JavaMethod]:
        """Extract method declarations."""
        methods = []
        class_body = self._find_class_body(class_node)
        if not class_body:
            return methods

        for child in class_body.children:
            if child.type == "method_declaration":
                modifiers = self._get_modifiers(child)
                return_type = self._get_return_type(child)
                name = self._get_method_name(child)
                parameters = self._get_parameters(child)
                throws = self._get_throws(child)
                body_ast = self._get_method_body(child)

                methods.append(JavaMethod(
                    name=name,
                    return_type=return_type,
                    parameters=parameters,
                    modifiers=modifiers,
                    throws=throws,
                    body_ast=body_ast
                ))
            elif child.type == "constructor_declaration":
                # Treat constructor as special method
                modifiers = self._get_modifiers(child)
                parameters = self._get_parameters(child)
                body_ast = self._get_method_body(child)

                methods.append(JavaMethod(
                    name="__init__",  # Python constructor
                    return_type="None",
                    parameters=parameters,
                    modifiers=modifiers,
                    throws=[],
                    body_ast=body_ast
                ))

        return methods

    def _find_class_body(self, class_node):
        """Find class body node."""
        for child in class_node.children:
            if child.type == "class_body":
                return child
        return None

    def _get_field_type(self, field_node) -> str:
        """Extract field type."""
        for child in field_node.children:
            if child.type in ("type_identifier", "generic_type"):
                return child.text.decode('utf-8')
        return "Any"

    def _get_variable_name(self, declarator) -> str:
        """Extract variable name from declarator."""
        for child in declarator.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return ""

    def _get_initializer(self, declarator) -> Optional[str]:
        """Extract initializer expression."""
        for i, child in enumerate(declarator.children):
            if child.type == "=":
                # Next sibling is initializer
                if i + 1 < len(declarator.children):
                    return declarator.children[i + 1].text.decode('utf-8')
        return None

    def _get_return_type(self, method_node) -> str:
        """Extract method return type."""
        for child in method_node.children:
            if child.type in ("type_identifier", "generic_type", "void_type"):
                return child.text.decode('utf-8')
        return "None"

    def _get_method_name(self, method_node) -> str:
        """Extract method name."""
        for child in method_node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return ""

    def _get_parameters(self, method_node) -> List['JavaParameter']:
        """Extract method parameters."""
        parameters = []
        for child in method_node.children:
            if child.type == "formal_parameters":
                for param_node in child.children:
                    if param_node.type == "formal_parameter":
                        param_type = self._get_param_type(param_node)
                        param_name = self._get_param_name(param_node)
                        parameters.append(JavaParameter(
                            name=param_name,
                            type=param_type
                        ))
        return parameters

    def _get_param_type(self, param_node) -> str:
        """Extract parameter type."""
        for child in param_node.children:
            if child.type in ("type_identifier", "generic_type"):
                return child.text.decode('utf-8')
        return "Any"

    def _get_param_name(self, param_node) -> str:
        """Extract parameter name."""
        for child in param_node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return ""

    def _get_throws(self, method_node) -> List[str]:
        """Extract throws clause."""
        throws = []
        for child in method_node.children:
            if child.type == "throws":
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        throws.append(subchild.text.decode('utf-8'))
        return throws

    def _get_method_body(self, method_node):
        """Extract method body AST node."""
        for child in method_node.children:
            if child.type == "block":
                return child
        return None

@dataclass(frozen=True)
class JavaParameter:
    """Method parameter."""
    name: str
    type: str
```

**Usage Example:**

```python
analyzer = JavaSemanticAnalyzer(parser)
java_class = analyzer.analyze_file(source_code)

print(f"Class: {java_class.package}.{java_class.name}")
print(f"Extends: {java_class.extends}")
print(f"Modifiers: {java_class.modifiers}")
print(f"\nFields ({len(java_class.fields)}):")
for field in java_class.fields:
    print(f"  {' '.join(field.modifiers)} {field.type} {field.name}")
print(f"\nMethods ({len(java_class.methods)}):")
for method in java_class.methods:
    params = ', '.join(f"{p.type} {p.name}" for p in method.parameters)
    print(f"  {' '.join(method.modifiers)} {method.return_type} {method.name}({params})")
```

**Output:**
```
Class: org.yawlfoundation.yawl.authentication.YSession
Extends: YAbstractSession
Modifiers: ['public']

Fields (1):
  private YClient _client

Methods (2):
  public None __init__(long timeOutSeconds)
  public String getURI()
```

---

## 2. Code Generation Patterns: Analysis

### 2.1 Pattern Comparison

| Pattern | Complexity | Maintainability | Best For | Limitations |
|---------|-----------|----------------|----------|-------------|
| **Template-based** | Low | ✅ High (declarative) | Straightforward mappings, UI components | ❌ Limited expressiveness for complex logic |
| **AST-based** | High | ⚠️ Medium (imperative code) | Accurate transformations, preserving structure | ❌ Requires deep AST knowledge |
| **LLM-assisted** | Medium | ✅ High (human-readable prompts) | Complex business logic, ambiguous patterns | ❌ Non-deterministic, requires validation |
| **Hybrid** | Medium-High | ✅ High (best of all) | Real-world codebases with mixed patterns | ❌ More initial setup |

### 2.2 Recommended Approach: **Hybrid**

**Strategy**: Combine strengths of each pattern based on code complexity:

1. **Template-based** → Simple patterns (getters, setters, DTOs, Vaadin components)
2. **AST-based** → Structural transformations (class hierarchies, method signatures)
3. **LLM-assisted** → Complex business logic (state machines, validation rules)

**Architecture:**

```
Java Source
    ↓
[tree-sitter parser]
    ↓
Semantic AST
    ↓
[Pattern Classifier]
    ↓
    ├─→ Simple Pattern? → [Template Generator] → Python/TS Code
    ├─→ Structural Pattern? → [AST Transformer] → Python/TS Code
    └─→ Complex Logic? → [LLM Generator] → Python/TS Code (+ tests)
    ↓
[Quality Validator]
    ↓
Final Code + Tests
```

### 2.3 Template-Based Generation

**Use Case**: Vaadin components → React components

**Example Template** (Jinja2):

```jinja2
{# templates/vaadin_to_react.j2 #}
{% macro vaadin_textfield(java_field) %}
// Vaadin: private final TextField {{ java_field.name }} = new TextField("{{ java_field.label }}");

// React + MUI:
const [{{ java_field.name | to_camelcase }}, set{{ java_field.name | to_pascalcase }}] = useState('');

<TextField
  label="{{ java_field.label }}"
  value={ {{ java_field.name | to_camelcase }} }
  onChange={(e) => set{{ java_field.name | to_pascalcase }}(e.target.value)}
  {% if java_field.required %}required{% endif %}
  {% if java_field.placeholder %}placeholder="{{ java_field.placeholder }}"{% endif %}
/>
{% endmacro %}

{% macro vaadin_grid(java_grid) %}
// Vaadin: Grid<{{ java_grid.type }}> grid = new Grid<>();

// React + MUI DataGrid:
import { DataGrid } from '@mui/x-data-grid';

const columns = [
  {% for column in java_grid.columns %}
  { field: '{{ column.field }}', headerName: '{{ column.header }}', width: {{ column.width | default(150) }} },
  {% endfor %}
];

<DataGrid
  rows={ {{ java_grid.data_source | to_camelcase }} }
  columns={columns}
  {% if java_grid.selection_mode == 'MULTI' %}checkboxSelection{% endif %}
/>
{% endmacro %}
```

**Python Generator:**

```python
from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass
from typing import List

@dataclass
class VaadinFieldConfig:
    """Configuration extracted from Vaadin field declaration."""
    name: str
    label: str
    type: str  # TextField, ComboBox, DatePicker, etc.
    required: bool = False
    placeholder: str | None = None

@dataclass
class VaadinGridConfig:
    """Configuration extracted from Vaadin Grid."""
    type: str  # Participant, WorkItemRecord, etc.
    columns: List['GridColumn']
    data_source: str
    selection_mode: str  # SINGLE, MULTI, NONE

@dataclass
class GridColumn:
    """Grid column configuration."""
    field: str
    header: str
    width: int | None = None

class TemplateBasedGenerator:
    """Generate code using Jinja2 templates."""

    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.env.filters['to_camelcase'] = self._to_camelcase
        self.env.filters['to_pascalcase'] = self._to_pascalcase

    def generate_react_textfield(self, config: VaadinFieldConfig) -> str:
        """Generate React TextField from Vaadin config."""
        template = self.env.get_template('vaadin_to_react.j2')
        return template.module.vaadin_textfield(config)

    def generate_react_grid(self, config: VaadinGridConfig) -> str:
        """Generate React DataGrid from Vaadin Grid."""
        template = self.env.get_template('vaadin_to_react.j2')
        return template.module.vaadin_grid(config)

    def _to_camelcase(self, text: str) -> str:
        """Convert to camelCase."""
        if '_' in text:
            parts = text.split('_')
            return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
        return text[0].lower() + text[1:] if text else text

    def _to_pascalcase(self, text: str) -> str:
        """Convert to PascalCase."""
        if '_' in text:
            return ''.join(p.capitalize() for p in text.split('_'))
        return text[0].upper() + text[1:] if text else text
```

**Usage:**

```python
generator = TemplateBasedGenerator('templates/')

# Extract config from Java AST (using semantic analyzer)
field_config = VaadinFieldConfig(
    name="nameField",
    label="Name",
    type="TextField",
    required=True,
    placeholder="Enter name"
)

react_code = generator.generate_react_textfield(field_config)
print(react_code)
```

**Output:**

```typescript
// React + MUI:
const [nameField, setNameField] = useState('');

<TextField
  label="Name"
  value={nameField}
  onChange={(e) => setNameField(e.target.value)}
  required
  placeholder="Enter name"
/>
```

### 2.4 AST-Based Generation

**Use Case**: Java class structure → Python class structure

**Example:**

```python
class ASTBasedGenerator:
    """Generate Python code by transforming Java AST."""

    def generate_python_class(self, java_class: JavaClass) -> str:
        """Transform Java class to Python class."""
        lines = []

        # Add imports
        lines.append(self._generate_imports(java_class))
        lines.append("")

        # Class definition
        if java_class.extends:
            lines.append(f"class {java_class.name}({java_class.extends}):")
        else:
            lines.append(f"class {java_class.name}:")

        # Docstring
        lines.append(f'    """{java_class.name} - converted from Java."""')
        lines.append("")

        # Fields as type annotations
        for field in java_class.fields:
            py_type = self._map_type(field.type)
            lines.append(f"    {field.name}: {py_type}")

        if java_class.fields:
            lines.append("")

        # Constructor
        constructor = next((m for m in java_class.methods if m.name == "__init__"), None)
        if constructor:
            lines.append(self._generate_constructor(constructor, java_class))
            lines.append("")

        # Methods
        for method in java_class.methods:
            if method.name != "__init__":
                lines.append(self._generate_method(method))
                lines.append("")

        return "\n".join(lines)

    def _generate_imports(self, java_class: JavaClass) -> str:
        """Generate Python imports based on Java types used."""
        imports = set()

        # Check all field types and method types
        for field in java_class.fields:
            if self._needs_import(field.type):
                imports.add(self._get_import(field.type))

        for method in java_class.methods:
            if self._needs_import(method.return_type):
                imports.add(self._get_import(method.return_type))
            for param in method.parameters:
                if self._needs_import(param.type):
                    imports.add(self._get_import(param.type))

        if imports:
            return "\n".join(sorted(imports))
        return ""

    def _generate_constructor(self, method: JavaMethod, java_class: JavaClass) -> str:
        """Generate Python __init__ method."""
        params = ", ".join(
            f"{p.name}: {self._map_type(p.type)}" for p in method.parameters
        )

        lines = [f"    def __init__(self, {params}) -> None:"]

        # Call super if has parent
        if java_class.extends:
            super_params = self._get_super_params(method)
            if super_params:
                lines.append(f"        super().__init__({super_params})")

        # Assign fields
        for field in java_class.fields:
            field_name = field.name.lstrip('_')  # Remove leading underscore
            if any(p.name == field_name or p.name == field.name for p in method.parameters):
                lines.append(f"        self.{field.name} = {field_name}")
            elif field.initializer:
                init_value = self._map_initializer(field.initializer)
                lines.append(f"        self.{field.name} = {init_value}")
            else:
                lines.append(f"        self.{field.name} = None")

        return "\n".join(lines)

    def _generate_method(self, method: JavaMethod) -> str:
        """Generate Python method."""
        params = ", ".join(
            f"{p.name}: {self._map_type(p.type)}" for p in method.parameters
        )
        return_type = self._map_type(method.return_type)

        lines = [f"    def {method.name}(self, {params}) -> {return_type}:"]
        lines.append(f'        """TODO: Implement {method.name}."""')

        # Add method body (simplified - would need AST transformation)
        if method.body_ast:
            # For now, raise NotImplementedError (LLM would fill this in)
            lines.append(f"        raise NotImplementedError('{method.name} not yet implemented')")
        else:
            # Abstract method
            lines.append("        pass")

        return "\n".join(lines)

    def _map_type(self, java_type: str) -> str:
        """Map Java type to Python type."""
        type_map = {
            "String": "str",
            "int": "int",
            "long": "int",
            "double": "float",
            "float": "float",
            "boolean": "bool",
            "void": "None",
            "List": "list",
            "Map": "dict",
            "Set": "set",
            "UUID": "str",  # or use uuid.UUID
            "YClient": "YClient",  # Preserve custom types
        }
        return type_map.get(java_type, java_type)

    def _map_initializer(self, init_expr: str) -> str:
        """Map Java initializer to Python."""
        init_map = {
            "null": "None",
            "true": "True",
            "false": "False",
        }
        return init_map.get(init_expr, init_expr)

    def _needs_import(self, type_str: str) -> bool:
        """Check if type needs import."""
        # Simple heuristic: custom types need imports
        builtin_types = {"str", "int", "float", "bool", "None", "list", "dict", "set"}
        return type_str not in builtin_types

    def _get_import(self, type_str: str) -> str:
        """Get import statement for type."""
        # Map to likely import location
        # In real implementation, would use symbol table
        return f"from yawl.types import {type_str}"

    def _get_super_params(self, method: JavaMethod) -> str:
        """Extract parameters passed to super() call."""
        # Would need to analyze method body AST
        # For now, pass first parameter (common pattern)
        if method.parameters:
            return method.parameters[0].name
        return ""
```

**Usage:**

```python
generator = ASTBasedGenerator()
python_code = generator.generate_python_class(java_class)
print(python_code)
```

**Output:**

```python
from yawl.types import YClient

class YSession(YAbstractSession):
    """YSession - converted from Java."""

    _client: YClient

    def __init__(self, timeOutSeconds: int) -> None:
        super().__init__(timeOutSeconds)
        self._client = None

    def getURI(self) -> str:
        """TODO: Implement getURI."""
        raise NotImplementedError('getURI not yet implemented')
```

### 2.5 LLM-Assisted Generation

**Use Case**: Complex business logic (work queue state transitions, privilege checking)

**Strategy**: Use Claude API to transform Java method bodies to Python, with context and examples.

```python
import anthropic
from dataclasses import dataclass

@dataclass
class LLMGenerationContext:
    """Context for LLM generation."""
    java_class: JavaClass
    java_method: JavaMethod
    symbol_table: Dict[str, str]  # Variable name → type
    example_transformations: List['CodeExample']

@dataclass
class CodeExample:
    """Example Java → Python transformation."""
    java_snippet: str
    python_snippet: str
    explanation: str

class LLMAssistedGenerator:
    """Generate complex code using LLM."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_method_body(
        self,
        method: JavaMethod,
        context: LLMGenerationContext
    ) -> str:
        """Generate Python method body using LLM."""

        # Build prompt with context
        prompt = self._build_prompt(method, context)

        # Call Claude API
        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract code from response
        python_code = self._extract_code(message.content[0].text)

        return python_code

    def _build_prompt(self, method: JavaMethod, context: LLMGenerationContext) -> str:
        """Build prompt for LLM."""

        # Get Java method body
        java_body = method.body_ast.text.decode('utf-8') if method.body_ast else ""

        # Build context section
        context_section = f"""
**Class Context:**
- Package: {context.java_class.package}
- Class: {context.java_class.name}
- Extends: {context.java_class.extends}

**Available Fields:**
{self._format_fields(context.java_class.fields)}

**Type Mappings:**
{self._format_type_mappings(context.symbol_table)}
"""

        # Build examples section
        examples_section = "\n\n".join(
            f"**Example {i+1}: {ex.explanation}**\n\nJava:\n```java\n{ex.java_snippet}\n```\n\nPython:\n```python\n{ex.python_snippet}\n```"
            for i, ex in enumerate(context.example_transformations)
        )

        # Build main prompt
        prompt = f"""
You are translating Java code to Python for the YAWL workflow system migration.

{context_section}

**Examples of similar transformations:**

{examples_section}

**Task:**
Translate the following Java method to Python:

```java
{self._format_method_signature(method)}
{java_body}
}}
```

**Requirements:**
1. Use Python 3.13+ type hints (int, str, bool, list, dict, None)
2. Map Java exceptions to Python exceptions
3. Use Pythonic idioms (list comprehensions, with statements, etc.)
4. Preserve business logic exactly
5. Add docstring with business logic explanation
6. Handle None checks appropriately
7. Use frozen dataclasses for value objects

**Output only the Python method implementation (def ... to end), no explanations.**
"""

        return prompt

    def _format_fields(self, fields: List[JavaField]) -> str:
        """Format fields for context."""
        return "\n".join(
            f"- {field.name}: {field.type}"
            for field in fields
        )

    def _format_type_mappings(self, symbol_table: Dict[str, str]) -> str:
        """Format type mappings."""
        return "\n".join(
            f"- {k} → {v}"
            for k, v in symbol_table.items()
        )

    def _format_method_signature(self, method: JavaMethod) -> str:
        """Format Java method signature."""
        params = ", ".join(f"{p.type} {p.name}" for p in method.parameters)
        modifiers = " ".join(method.modifiers)
        return f"{modifiers} {method.return_type} {method.name}({params}) {{"

    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Find code block
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + len("```")
            end = response.find("```", start)
            return response[start:end].strip()
        else:
            # No code block, return as-is
            return response.strip()
```

**Usage:**

```python
# Example transformations to provide context
examples = [
    CodeExample(
        java_snippet="""
if (StringUtil.isNullOrEmpty(xml)) {
    return null;
}
return StringUtil.unwrap(xml);
""",
        python_snippet="""
if not xml or xml.strip() == "":
    return None
return unwrap(xml)
""",
        explanation="Null/empty string checking and utility method calls"
    ),
    CodeExample(
        java_snippet="""
try {
    resourceClient.startItem(wir.getID(), pid);
    wir.setResourceStatus(WorkItemRecord.statusResourceStarted);
} catch (IOException e) {
    throw new ResourceGatewayException("Failed to start item", e);
}
""",
        python_snippet="""
try:
    resource_client.start_item(wir.id, pid)
    wir.resource_status = WorkItemRecord.STATUS_RESOURCE_STARTED
except IOError as e:
    raise ResourceGatewayException("Failed to start item") from e
""",
        explanation="Exception handling and method calls"
    )
]

context = LLMGenerationContext(
    java_class=java_class,
    java_method=complex_method,
    symbol_table={"wir": "WorkItemRecord", "pid": "str"},
    example_transformations=examples
)

llm_gen = LLMAssistedGenerator(api_key="...")
python_method = llm_gen.generate_method_body(complex_method, context)
print(python_method)
```

---

## 3. Java to Python Type and Pattern Mappings

### 3.1 Type Mapping Table

| Java Type | Python Type | Notes |
|-----------|------------|-------|
| `String` | `str` | Direct mapping |
| `int`, `Integer` | `int` | Python int is arbitrary precision |
| `long`, `Long` | `int` | No separate long type in Python |
| `double`, `Double` | `float` | IEEE 754 double precision |
| `float`, `Float` | `float` | Less precision, but Python float is double |
| `boolean`, `Boolean` | `bool` | Direct mapping |
| `void` | `None` | Return type only |
| `char`, `Character` | `str` | Single-character string |
| `byte[]` | `bytes` | Immutable byte array |
| `List<T>` | `list[T]` | Python 3.9+ generic syntax |
| `Set<T>` | `set[T]` | Python 3.9+ generic syntax |
| `Map<K, V>` | `dict[K, V]` | Python 3.9+ generic syntax |
| `ArrayList<T>` | `list[T]` | ArrayList is mutable list |
| `HashMap<K, V>` | `dict[K, V]` | HashMap is dict |
| `HashSet<T>` | `set[T]` | HashSet is set |
| `Optional<T>` | `T \| None` | Python 3.10+ union syntax |
| `UUID` | `uuid.UUID` | Use standard library uuid |
| `Date` | `datetime.datetime` | java.util.Date → datetime |
| `LocalDateTime` | `datetime.datetime` | Java 8+ time API |
| `BigDecimal` | `decimal.Decimal` | Arbitrary precision decimal |
| `InputStream` | `io.BytesIO` | Binary stream |
| `OutputStream` | `io.BytesIO` | Binary stream |
| `File` | `pathlib.Path` | Modern path handling |
| `Exception` | `Exception` | Base exception class |
| `IOException` | `IOError` | I/O related exceptions |
| `RuntimeException` | `RuntimeError` | Unchecked exceptions |

### 3.2 Pattern Mappings

#### 3.2.1 Getters/Setters → Properties

**Java:**
```java
public class Participant {
    private String name;
    private String email;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }
}
```

**Python (Dataclass - Recommended):**
```python
from dataclasses import dataclass

@dataclass
class Participant:
    """Participant entity."""
    name: str
    email: str
```

**Python (Property Pattern - For Validation):**
```python
class Participant:
    """Participant with validation."""

    def __init__(self, name: str, email: str):
        self._name = name
        self._email = email

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value:
            raise ValueError("Name cannot be empty")
        self._name = value

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if '@' not in value:
            raise ValueError("Invalid email format")
        self._email = value
```

#### 3.2.2 Singleton Pattern → Module-Level

**Java:**
```java
public class Clients {
    private static final ResourceClient _resClient = new ResourceClient();
    private static final EngineClient _engClient = new EngineClient();

    public static ResourceClient getResourceClient() {
        return _resClient;
    }

    public static EngineClient getEngineClient() {
        return _engClient;
    }
}
```

**Python:**
```python
# clients.py (module-level singletons)
from yawl.api.resource_client import ResourceClient
from yawl.api.engine_client import EngineClient

_res_client = ResourceClient()
_eng_client = EngineClient()

def get_resource_client() -> ResourceClient:
    """Get singleton ResourceClient instance."""
    return _res_client

def get_engine_client() -> EngineClient:
    """Get singleton EngineClient instance."""
    return _eng_client
```

#### 3.2.3 Observer Pattern → Event Emitters

**Java:**
```java
public abstract class AbstractClient {
    private static final Set<ClientEventListener> listeners = new HashSet<>();

    public void addEventListener(ClientEventListener listener) {
        listeners.add(listener);
    }

    protected void announceEvent(ClientEvent.Action action, Object object) {
        ClientEvent event = new ClientEvent(action, object);
        for (ClientEventListener listener : listeners) {
            listener.onClientEvent(event);
        }
    }
}
```

**Python:**
```python
from typing import Callable, Any
from dataclasses import dataclass
from enum import Enum

class ClientEventAction(Enum):
    """Client event actions."""
    SERVICE_ADD = "service_add"
    SERVICE_REMOVE = "service_remove"
    CONNECTION_LOST = "connection_lost"

@dataclass(frozen=True)
class ClientEvent:
    """Client event data."""
    action: ClientEventAction
    payload: Any

class AbstractClient:
    """Base client with event system."""

    _listeners: list[Callable[[ClientEvent], None]] = []

    def add_event_listener(self, listener: Callable[[ClientEvent], None]) -> None:
        """Add event listener."""
        self._listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[ClientEvent], None]) -> None:
        """Remove event listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _announce_event(self, action: ClientEventAction, payload: Any) -> None:
        """Announce event to all listeners."""
        event = ClientEvent(action=action, payload=payload)
        for listener in self._listeners:
            listener(event)
```

#### 3.2.4 Builder Pattern → Fluent Interface

**Java:**
```java
public class ActionRibbon extends HorizontalLayout {
    public ActionRibbon add(VaadinIcon icon, String label, ComponentEventListener<ClickEvent<Button>> listener) {
        Button button = new Button(label, icon.create(), listener);
        add(button);
        return this;
    }
}

// Usage
ActionRibbon ribbon = new ActionRibbon();
ribbon.add(VaadinIcon.CHECK, "Accept", e -> accept())
      .add(VaadinIcon.PLAY, "Start", e -> start());
```

**Python:**
```python
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class Action:
    """Action button configuration."""
    icon: str
    label: str
    handler: Callable[[], None]

class ActionRibbon:
    """Fluent action ribbon builder."""

    def __init__(self):
        self.actions: list[Action] = []

    def add(self, icon: str, label: str, handler: Callable[[], None]) -> 'ActionRibbon':
        """Add action button (fluent interface)."""
        self.actions.append(Action(icon=icon, label=label, handler=handler))
        return self

    def build(self) -> list[Action]:
        """Build final action list."""
        return self.actions

# Usage
ribbon = (ActionRibbon()
          .add("check", "Accept", accept)
          .add("play", "Start", start))
actions = ribbon.build()
```

#### 3.2.5 Exception Handling → Context Managers

**Java:**
```java
try {
    InputStream is = new FileInputStream("spec.yawl");
    try {
        String content = readStream(is);
        return content;
    } finally {
        is.close();
    }
} catch (IOException e) {
    throw new RuntimeException("Failed to read file", e);
}
```

**Python:**
```python
from pathlib import Path

try:
    with Path("spec.yawl").open("r") as f:
        content = f.read()
        return content
except IOError as e:
    raise RuntimeError("Failed to read file") from e
```

#### 3.2.6 Collections → List Comprehensions

**Java:**
```java
List<WorkItemRecord> startedItems = new ArrayList<>();
for (WorkItemRecord wir : allItems) {
    if (wir.getResourceStatus().equals("Started")) {
        startedItems.add(wir);
    }
}
```

**Python:**
```python
started_items = [
    wir for wir in all_items
    if wir.resource_status == "Started"
]
```

#### 3.2.7 Streams → Functional Operations

**Java:**
```java
List<String> names = participants.stream()
    .filter(p -> p.isActive())
    .map(Participant::getName)
    .sorted()
    .collect(Collectors.toList());
```

**Python:**
```python
names = sorted(
    p.name for p in participants
    if p.is_active()
)
```

#### 3.2.8 Enums → Enums

**Java:**
```java
public enum WorkQueue {
    OFFERED,
    ALLOCATED,
    STARTED,
    SUSPENDED
}
```

**Python:**
```python
from enum import Enum

class WorkQueue(Enum):
    """Work queue types."""
    OFFERED = "offered"
    ALLOCATED = "allocated"
    STARTED = "started"
    SUSPENDED = "suspended"
```

#### 3.2.9 Annotations → Decorators

**Java:**
```java
@Override
public String toString() {
    return "Participant[" + name + "]";
}
```

**Python:**
```python
def __str__(self) -> str:
    """String representation."""
    return f"Participant[{self.name}]"
```

#### 3.2.10 Abstract Classes → ABC

**Java:**
```java
public abstract class AbstractClient {
    protected String _handle;

    public abstract void connect() throws IOException;
    public abstract void disconnect() throws IOException;
    public abstract boolean connected() throws IOException;
}
```

**Python:**
```python
from abc import ABC, abstractmethod

class AbstractClient(ABC):
    """Base client with abstract methods."""

    def __init__(self):
        self._handle: str | None = None

    @abstractmethod
    def connect(self) -> None:
        """Connect to service."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from service."""
        ...

    @abstractmethod
    def connected(self) -> bool:
        """Check if connected."""
        ...
```

---

## 4. Java to TypeScript/React Mappings

### 4.1 Type Mapping Table

| Java Type | TypeScript Type | Notes |
|-----------|----------------|-------|
| `String` | `string` | Primitive |
| `int`, `long` | `number` | JS number is IEEE 754 double |
| `double`, `float` | `number` | All numeric types are number |
| `boolean` | `boolean` | Primitive |
| `void` | `void` | Return type only |
| `List<T>` | `T[]` or `Array<T>` | Generic array |
| `Set<T>` | `Set<T>` | ES6 Set |
| `Map<K, V>` | `Map<K, V>` | ES6 Map |
| `Optional<T>` | `T \| null` or `T \| undefined` | Union type |
| `UUID` | `string` | UUID as string |
| `Date` | `Date` | JavaScript Date |
| `LocalDateTime` | `Date` or `Temporal.PlainDateTime` | Temporal API (Stage 3) |
| `BigDecimal` | `bigint` or library | Native bigint or decimal.js |
| `Exception` | `Error` | JavaScript Error |
| Custom class | `interface` or `type` | TypeScript interface |

### 4.2 Vaadin Components → React Components

See `/docs/java-to-python-yawl/vaadin-to-react-mapping.md` for comprehensive 1000+ line mapping document.

**Quick Reference:**

| Vaadin | React (MUI) | React (Headless UI) |
|--------|------------|-------------------|
| `TextField` | `<TextField>` | `<input>` + styling |
| `Button` | `<Button>` | `<button>` + styling |
| `Grid<T>` | `<DataGrid>` | TanStack Table |
| `Dialog` | `<Dialog>` | `<Dialog>` (headlessui) |
| `VerticalLayout` | `<Stack direction="column">` | Flexbox div |
| `HorizontalLayout` | `<Stack direction="row">` | Flexbox div |

### 4.3 Event Handling Patterns

#### 4.3.1 Click Listeners → onClick

**Java:**
```java
Button button = new Button("Save", e -> {
    saveData();
    Notification.show("Saved");
});
```

**TypeScript/React:**
```typescript
import { Button } from '@mui/material';
import { useState } from 'react';
import { toast } from 'react-toastify';

function SaveButton({ onSave }: { onSave: () => void }) {
  const handleClick = () => {
    onSave();
    toast.success('Saved');
  };

  return <Button onClick={handleClick}>Save</Button>;
}
```

#### 4.3.2 Value Change Listeners → onChange

**Java:**
```java
TextField field = new TextField("Name");
field.addValueChangeListener(e -> {
    String newValue = e.getValue();
    updateState(newValue);
});
```

**TypeScript/React:**
```typescript
import { TextField } from '@mui/material';
import { useState } from 'react';

function NameField() {
  const [value, setValue] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    // Additional logic
  };

  return <TextField label="Name" value={value} onChange={handleChange} />;
}
```

#### 4.3.3 Grid Selection → Callbacks

**Java:**
```java
grid.addSelectionListener(e -> {
    Set<Participant> selected = e.getAllSelectedItems();
    updateSelection(selected);
});
```

**TypeScript/React:**
```typescript
import { DataGrid } from '@mui/x-data-grid';
import { useState } from 'react';

interface Participant {
  id: string;
  name: string;
}

function ParticipantGrid({ participants }: { participants: Participant[] }) {
  const [selected, setSelected] = useState<string[]>([]);

  const handleSelectionChange = (newSelection: string[]) => {
    setSelected(newSelection);
    // Additional logic
  };

  return (
    <DataGrid
      rows={participants}
      columns={columns}
      checkboxSelection
      onRowSelectionModelChange={handleSelectionChange}
      rowSelectionModel={selected}
    />
  );
}
```

### 4.4 State Management Patterns

#### 4.4.1 Component Fields → useState

**Java:**
```java
public class UserWorklistView extends VerticalLayout {
    private QueueSet queueSet;
    private Participant participant;

    public UserWorklistView(Participant p) {
        this.participant = p;
        this.queueSet = fetchQueueSet(p);
        createLayout();
    }
}
```

**TypeScript/React:**
```typescript
import { useState, useEffect } from 'react';

interface QueueSet {
  offered: WorkItemRecord[];
  allocated: WorkItemRecord[];
  started: WorkItemRecord[];
  suspended: WorkItemRecord[];
}

function UserWorklistView({ participant }: { participant: Participant }) {
  const [queueSet, setQueueSet] = useState<QueueSet | null>(null);

  useEffect(() => {
    fetchQueueSet(participant).then(setQueueSet);
  }, [participant]);

  if (!queueSet) return <div>Loading...</div>;

  return <div>{/* Layout */}</div>;
}
```

#### 4.4.2 Session Attributes → Context

**Java:**
```java
VaadinSession.getCurrent().setAttribute("user", participant);
```

**TypeScript/React:**
```typescript
import { createContext, useContext, useState, ReactNode } from 'react';

interface UserContextType {
  user: Participant | null;
  setUser: (user: Participant | null) => void;
}

const UserContext = createContext<UserContextType | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Participant | null>(null);

  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}

// Usage
function ProfileView() {
  const { user } = useUser();
  return <div>Welcome, {user?.name}</div>;
}
```

#### 4.4.3 Binder → React Hook Form

**Java:**
```java
Binder<Participant> binder = new Binder<>(Participant.class);
binder.forField(firstName).asRequired("Required").bind("firstName");
binder.forField(lastName).bind("lastName");
binder.setBean(participant);
```

**TypeScript/React:**
```typescript
import { useForm } from 'react-hook-form';
import { TextField, Button } from '@mui/material';

interface ParticipantForm {
  firstName: string;
  lastName: string;
}

function ParticipantEditForm({ participant }: { participant: Participant }) {
  const { register, handleSubmit, formState: { errors } } = useForm<ParticipantForm>({
    defaultValues: {
      firstName: participant.firstName,
      lastName: participant.lastName
    }
  });

  const onSubmit = (data: ParticipantForm) => {
    updateParticipant(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextField
        label="First Name"
        {...register('firstName', { required: 'Required' })}
        error={!!errors.firstName}
        helperText={errors.firstName?.message}
      />
      <TextField
        label="Last Name"
        {...register('lastName')}
      />
      <Button type="submit">Save</Button>
    </form>
  );
}
```

---

## 5. Existing Translation Tools: Research

### 5.1 Tool Analysis

| Tool | Approach | Strengths | Weaknesses | Lessons for YAWL |
|------|---------|-----------|------------|------------------|
| **j2objc** (Google) | AST-based (Eclipse JDT) | ✅ Preserves semantics, handles generics | ❌ Java → Objective-C only | Use semantic analyzer, not syntax parser |
| **GraalVM** | JVM-based compilation | ✅ Performance, polyglot interop | ❌ Native image, not code translation | Consider runtime interop for complex parts |
| **Jython** | JVM-Python bridge | ✅ Full Java interop | ❌ Python 2.7 only, unmaintained | Avoid runtime bridges for migration |
| **JTransc** | Kotlin-based transpiler | ✅ Multi-target (JS, C++, C#) | ❌ Unmaintained, incomplete | Template-based approach works for simple code |
| **Tangible** (Commercial) | Pattern-based | ✅ High-level patterns | ❌ Expensive, limited customization | Pattern libraries are valuable |

### 5.2 Key Lessons

1. **Semantic Analysis is Critical**: j2objc succeeds because it uses Eclipse JDT (full semantic analyzer), not just syntax parser.

2. **Template-Based Works for UI**: JTransc's template approach works well for framework code (Swing → HTML5), similar to our Vaadin → React needs.

3. **Runtime Bridges Are Not Migration**: Jython/GraalVM interop is useful for coexistence, NOT for clean migration.

4. **Type Erasure is Hard**: Java generics lose type info at runtime, making dynamic translation difficult. Need compile-time analysis.

5. **Business Logic Needs Manual Review**: No tool can translate complex domain logic automatically. LLM-assisted approach is reasonable.

---

## 6. Quality Assurance Strategies

### 6.1 Quality Assurance Checklist

**Code Quality Gates** (must pass before accepting generated code):

- [ ] **Type Safety**: All generated code passes `mypy --strict`
- [ ] **Linting**: Code passes `ruff check` with ALL 400+ rules
- [ ] **Formatting**: Code passes `ruff format` (auto-formatted)
- [ ] **Tests**: Generated tests pass with 80%+ coverage
- [ ] **Behavior Equivalence**: Output matches Java implementation on test cases
- [ ] **No TODOs**: All `raise NotImplementedError` replaced with real code
- [ ] **Docstrings**: All public APIs have NumPy-style docstrings
- [ ] **No Secrets**: No hardcoded credentials, passes `bandit` security scan

### 6.2 Automated Test Generation

**Strategy**: Generate tests from Java test methods

**Example:**

**Java Test:**
```java
@Test
public void testAuthenticate() {
    ResourceClient client = new ResourceClient();
    boolean result = client.authenticate("admin", "password");
    assertTrue(result);
    assertNotNull(client.getHandle());
}
```

**Generated Python Test:**
```python
import pytest
from yawl.api.resource_client import ResourceClient

def test_authenticate():
    """Test ResourceClient authentication."""
    client = ResourceClient()
    result = client.authenticate("admin", "password")
    assert result is True
    assert client.handle is not None
```

**Test Generation Tool:**

```python
class TestGenerator:
    """Generate Python tests from Java tests."""

    def generate_test(self, java_method: JavaMethod) -> str:
        """Generate pytest test from JUnit test method."""

        # Extract test name
        test_name = java_method.name.replace("test", "test_", 1).lower()

        # Extract assertions (simplified - would need AST traversal)
        assertions = self._extract_assertions(java_method.body_ast)

        # Generate pytest test
        lines = [f"def {test_name}():"]
        lines.append(f'    """{self._generate_docstring(java_method)}."""')

        # Generate test body
        for assertion in assertions:
            lines.append(f"    {assertion}")

        return "\n".join(lines)

    def _extract_assertions(self, body_ast) -> List[str]:
        """Extract assertions from Java test body."""
        # Simplified - real implementation would traverse AST
        assertions = []

        # Map Java assertions to Python
        assertion_map = {
            "assertTrue": "assert {expr}",
            "assertFalse": "assert not {expr}",
            "assertEquals": "assert {expected} == {actual}",
            "assertNotNull": "assert {expr} is not None",
            "assertNull": "assert {expr} is None",
        }

        # Would extract from AST
        return assertions

    def _generate_docstring(self, method: JavaMethod) -> str:
        """Generate docstring from test method name."""
        # Convert testFooBar → Test foo bar
        name = method.name.replace("test", "", 1)
        words = re.findall(r'[A-Z][a-z]*', name)
        return "Test " + " ".join(w.lower() for w in words)
```

### 6.3 Behavior Verification

**Strategy**: Generate property-based tests to verify equivalence

```python
from hypothesis import given, strategies as st
import pytest

class BehaviorVerifier:
    """Verify Python implementation matches Java behavior."""

    def __init__(self, java_jar_path: str):
        """Initialize with path to Java JAR for comparison."""
        self.java_jar = java_jar_path

    @given(st.text(), st.text())
    def test_authenticate_equivalence(self, username: str, password: str):
        """Verify Python authenticate() matches Java authenticate()."""

        # Call Python implementation
        python_result = resource_client.authenticate(username, password)

        # Call Java implementation via subprocess
        java_result = self._call_java_method(
            "org.yawlfoundation.yawl.resourcing.ResourceClient",
            "authenticate",
            [username, password]
        )

        # Verify equivalence
        assert python_result == java_result

    def _call_java_method(self, class_name: str, method_name: str, args: List[Any]) -> Any:
        """Call Java method via subprocess."""
        import subprocess
        import json

        # Build Java command
        cmd = [
            "java", "-cp", self.java_jar,
            "TestRunner",  # Custom Java test runner
            class_name,
            method_name,
            json.dumps(args)
        ]

        # Execute
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse result
        return json.loads(result.stdout)
```

### 6.4 Pattern Verification

**Strategy**: Verify generated code follows Python patterns

```python
import ast
from typing import List

class PatternVerifier:
    """Verify generated code follows Pythonic patterns."""

    def verify_file(self, python_file: str) -> List[str]:
        """Verify file follows patterns, return violations."""
        violations = []

        with open(python_file) as f:
            source = f.read()

        tree = ast.parse(source)

        # Check patterns
        violations.extend(self._check_type_hints(tree))
        violations.extend(self._check_docstrings(tree))
        violations.extend(self._check_dataclasses(tree))
        violations.extend(self._check_no_getters_setters(tree))

        return violations

    def _check_type_hints(self, tree: ast.Module) -> List[str]:
        """Check all functions have type hints."""
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check return type
                if node.returns is None and node.name != "__init__":
                    violations.append(f"Function {node.name} missing return type")

                # Check parameter types
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != "self":
                        violations.append(f"Parameter {arg.arg} in {node.name} missing type hint")

        return violations

    def _check_docstrings(self, tree: ast.Module) -> List[str]:
        """Check public functions have docstrings."""
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not node.name.startswith('_'):  # Public
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        violations.append(f"{node.__class__.__name__} {node.name} missing docstring")

        return violations

    def _check_dataclasses(self, tree: ast.Module) -> List[str]:
        """Check value objects use dataclasses."""
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class looks like value object (all fields, no methods)
                has_init = any(isinstance(n, ast.FunctionDef) and n.name == "__init__" for n in node.body)
                has_methods = any(isinstance(n, ast.FunctionDef) and n.name not in ("__init__", "__repr__", "__str__") for n in node.body)

                if has_init and not has_methods:
                    # Check if dataclass decorator
                    has_dataclass = any(
                        isinstance(d, ast.Name) and d.id == "dataclass" or
                        isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass"
                        for d in node.decorator_list
                    )

                    if not has_dataclass:
                        violations.append(f"Class {node.name} looks like value object but not using @dataclass")

        return violations

    def _check_no_getters_setters(self, tree: ast.Module) -> List[str]:
        """Check for Java-style getters/setters (anti-pattern)."""
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('get_') or node.name.startswith('set_'):
                    # Check if it's just returning/setting field
                    if len(node.body) == 1:
                        stmt = node.body[0]
                        if isinstance(stmt, ast.Return):
                            violations.append(f"Getter {node.name} should use @property instead")
                        elif isinstance(stmt, ast.Assign):
                            violations.append(f"Setter {node.name} should use @property.setter instead")

        return violations
```

### 6.5 Quality Metrics

**Measure and track**:

1. **Type Coverage**: % of functions with complete type hints → Target: 100%
2. **Test Coverage**: % of code covered by tests → Target: 80%+
3. **Behavior Equivalence**: % of tests passing against Java implementation → Target: 100%
4. **Pattern Compliance**: % of code following Python patterns → Target: 95%+
5. **Performance**: Python vs Java execution time → Target: Within 2x
6. **LOC Reduction**: Python LOC vs Java LOC → Expect: 30-50% reduction

**Tracking Dashboard:**

```python
@dataclass
class QualityMetrics:
    """Quality metrics for generated code."""
    type_coverage: float  # 0.0 to 1.0
    test_coverage: float  # 0.0 to 1.0
    behavior_equivalence: float  # 0.0 to 1.0
    pattern_compliance: float  # 0.0 to 1.0
    performance_ratio: float  # Python time / Java time
    loc_reduction: float  # (Java LOC - Python LOC) / Java LOC

    def passes_quality_gates(self) -> bool:
        """Check if metrics pass quality gates."""
        return (
            self.type_coverage >= 1.0 and
            self.test_coverage >= 0.8 and
            self.behavior_equivalence >= 1.0 and
            self.pattern_compliance >= 0.95 and
            self.performance_ratio <= 2.0
        )

    def __str__(self) -> str:
        """Generate report."""
        return f"""
Quality Metrics Report:
- Type Coverage: {self.type_coverage:.1%} {'✅' if self.type_coverage >= 1.0 else '❌'}
- Test Coverage: {self.test_coverage:.1%} {'✅' if self.test_coverage >= 0.8 else '❌'}
- Behavior Equivalence: {self.behavior_equivalence:.1%} {'✅' if self.behavior_equivalence >= 1.0 else '❌'}
- Pattern Compliance: {self.pattern_compliance:.1%} {'✅' if self.pattern_compliance >= 0.95 else '❌'}
- Performance Ratio: {self.performance_ratio:.2f}x {'✅' if self.performance_ratio <= 2.0 else '❌'}
- LOC Reduction: {self.loc_reduction:.1%}

Overall: {'✅ PASS' if self.passes_quality_gates() else '❌ FAIL'}
"""
```

---

## 7. Recommended Tool Stack

### 7.1 Backend (Java → Python)

**Parsing & Analysis:**
- **tree-sitter-java**: AST parsing (fast, accurate)
- **Custom semantic analyzer**: Built on tree-sitter (types, symbols, call graphs)

**Code Generation:**
- **Jinja2**: Template-based generation (simple patterns)
- **ast module**: AST construction for complex transformations
- **anthropic SDK**: LLM-assisted generation (complex logic)

**Quality Assurance:**
- **mypy**: Type checking with `--strict`
- **ruff**: Linting and formatting (ALL rules)
- **pytest**: Test framework
- **coverage.py**: Code coverage
- **hypothesis**: Property-based testing (behavior equivalence)
- **bandit**: Security scanning

**Project Structure:**
```
codegen/
├── parsers/
│   ├── java_parser.py          # tree-sitter wrapper
│   └── semantic_analyzer.py    # Semantic extraction
├── generators/
│   ├── template_generator.py   # Jinja2 templates
│   ├── ast_generator.py         # AST-based transformation
│   └── llm_generator.py         # LLM-assisted generation
├── mappers/
│   ├── type_mapper.py           # Java → Python types
│   └── pattern_mapper.py        # Java patterns → Python patterns
├── validators/
│   ├── behavior_verifier.py    # Equivalence testing
│   └── pattern_verifier.py     # Pattern compliance
├── templates/
│   ├── class.py.j2              # Class template
│   ├── method.py.j2             # Method template
│   └── test.py.j2               # Test template
└── cli.py                       # Command-line interface
```

### 7.2 Frontend (Java/Vaadin → TypeScript/React)

**Parsing & Analysis:**
- **tree-sitter-java**: Parse Vaadin UI code
- **Custom Vaadin analyzer**: Extract component hierarchy

**Code Generation:**
- **Jinja2**: Template-based React component generation
- **handlebars** (alternative): If prefer JS-based templates

**Quality Assurance:**
- **TypeScript compiler**: Type checking with `strict: true`
- **eslint**: Linting with recommended rules
- **prettier**: Code formatting
- **jest + React Testing Library**: Component testing
- **playwright**: E2E testing

**Project Structure:**
```
ui-codegen/
├── parsers/
│   ├── vaadin_parser.py         # Extract Vaadin components
│   └── ui_analyzer.py           # UI hierarchy analysis
├── generators/
│   ├── react_generator.py       # React component generation
│   └── mui_generator.py         # MUI-specific generation
├── mappers/
│   ├── component_mapper.py      # Vaadin → React mappings
│   └── event_mapper.py          # Listeners → callbacks
├── templates/
│   ├── component.tsx.j2         # React component template
│   ├── hook.ts.j2               # Custom hook template
│   └── test.tsx.j2              # Component test template
└── cli.py
```

---

## 8. Code Examples: Complete Transformation

### 8.1 Java to Python Example

**Input (Java):**
```java
package org.yawlfoundation.yawl.authentication;

import java.util.Timer;
import java.util.TimerTask;
import java.util.UUID;

/**
 * Base class which represents an active session between the engine and an external
 * service or application.
 *
 * @author Michael Adams
 * @since 2.1
 */
public class YSession extends YAbstractSession {

    private YClient _client;

    public YSession(long timeOutSeconds) {
        super(timeOutSeconds);
    }

    public YSession(YClient client, long timeOutSeconds) {
        super(timeOutSeconds);
        _client = client;
    }

    public String getURI() {
        return null;
    }

    public String getPassword() {
        return null;
    }

    public void setPassword(String password) throws YPersistenceException {
        if (_client.getUserName().equals("admin")) {
            YExternalClient client = YEngine.getInstance().getExternalClient("admin");
            if (client != null) {
                client.setPassword(password);
                YEngine.getInstance().updateObject(client);
            }
        }
    }

    public YClient getClient() {
        return _client;
    }
}
```

**Output (Python):**
```python
"""YAWL authentication session module."""

from typing import Optional
from yawl.engine.y_engine import YEngine
from yawl.authentication.y_abstract_session import YAbstractSession
from yawl.authentication.y_client import YClient
from yawl.authentication.y_external_client import YExternalClient
from yawl.exceptions.y_persistence_exception import YPersistenceException


class YSession(YAbstractSession):
    """Active session between engine and external service or application.

    Base class representing an authenticated session with the YAWL engine.

    Parameters
    ----------
    timeout_seconds : int
        Maximum idle time for this session in seconds.
    client : YClient, optional
        The external service or application requesting a session.

    Attributes
    ----------
    _client : YClient | None
        The client associated with this session.

    Notes
    -----
    This is the base implementation. Subclasses override getURI() and getPassword()
    for specific client types.

    Examples
    --------
    >>> session = YSession(client=my_client, timeout_seconds=3600)
    >>> session.get_client()
    <YClient instance>

    Since
    -----
    2.1

    Author
    ------
    Michael Adams
    """

    _client: Optional[YClient]

    def __init__(self, timeout_seconds: int, client: Optional[YClient] = None) -> None:
        """Initialize session with timeout and optional client.

        Parameters
        ----------
        timeout_seconds : int
            Maximum idle time in seconds.
        client : YClient, optional
            Client requesting the session.
        """
        super().__init__(timeout_seconds)
        self._client = client

    def get_uri(self) -> Optional[str]:
        """Get the URI for this session.

        Returns
        -------
        str | None
            Session URI, or None in base implementation (overridden in subclasses).
        """
        return None

    def get_password(self) -> Optional[str]:
        """Get the password for this session.

        Returns
        -------
        str | None
            Session password, or None in base implementation (overridden in subclasses).
        """
        return None

    def set_password(self, password: str) -> None:
        """Set password for admin user only.

        Parameters
        ----------
        password : str
            The (hashed) password to set for the admin user.

        Raises
        ------
        YPersistenceException
            If database update fails.

        Notes
        -----
        This base implementation only allows changing the admin user's password.
        Subclasses may override to provide different behavior.
        """
        if self._client and self._client.get_user_name() == "admin":
            engine = YEngine.get_instance()
            client = engine.get_external_client("admin")
            if client is not None:
                client.set_password(password)
                engine.update_object(client)

    def get_client(self) -> Optional[YClient]:
        """Get the client associated with this session.

        Returns
        -------
        YClient | None
            The session's client, or None if not set.
        """
        return self._client
```

**Generated Test:**
```python
"""Tests for YSession class."""

import pytest
from yawl.authentication.y_session import YSession
from yawl.authentication.y_client import YClient
from yawl.exceptions.y_persistence_exception import YPersistenceException


def test_init_with_timeout_only():
    """Test YSession initialization with timeout only."""
    session = YSession(timeout_seconds=3600)
    assert session._client is None


def test_init_with_client():
    """Test YSession initialization with client."""
    client = YClient(user_name="test_user")
    session = YSession(timeout_seconds=3600, client=client)
    assert session.get_client() == client


def test_get_uri_returns_none():
    """Test get_uri returns None in base implementation."""
    session = YSession(timeout_seconds=3600)
    assert session.get_uri() is None


def test_get_password_returns_none():
    """Test get_password returns None in base implementation."""
    session = YSession(timeout_seconds=3600)
    assert session.get_password() is None


def test_set_password_for_admin(mocker):
    """Test set_password changes admin password."""
    # Mock dependencies
    mock_engine = mocker.patch('yawl.engine.y_engine.YEngine.get_instance')
    mock_external_client = mocker.MagicMock()
    mock_engine.return_value.get_external_client.return_value = mock_external_client

    admin_client = YClient(user_name="admin")
    session = YSession(timeout_seconds=3600, client=admin_client)

    session.set_password("new_password_hash")

    mock_external_client.set_password.assert_called_once_with("new_password_hash")
    mock_engine.return_value.update_object.assert_called_once_with(mock_external_client)


def test_set_password_for_non_admin_does_nothing(mocker):
    """Test set_password does nothing for non-admin users."""
    mock_engine = mocker.patch('yawl.engine.y_engine.YEngine.get_instance')

    user_client = YClient(user_name="regular_user")
    session = YSession(timeout_seconds=3600, client=user_client)

    session.set_password("new_password_hash")

    # Should not call engine methods
    mock_engine.return_value.get_external_client.assert_not_called()
```

### 8.2 Vaadin to React Example

**Input (Java):**
```java
public class ParticipantEditDialog extends Dialog {
    private final ResourceClient client = Clients.getResourceClient();
    private final Participant participant;

    private final TextField firstNameField = new TextField("First Name");
    private final TextField lastNameField = new TextField("Last Name");
    private final TextField emailField = new TextField("Email");
    private final CheckboxGroup<String> rolesField = new CheckboxGroup<>();

    public ParticipantEditDialog(Participant p) {
        this.participant = p;
        setHeaderTitle("Edit Participant");

        firstNameField.setValue(p.getFirstName());
        firstNameField.setRequired(true);

        lastNameField.setValue(p.getLastName());

        emailField.setValue(p.getEmail());
        emailField.setRequiredIndicatorVisible(true);

        List<Role> allRoles = client.getRoles();
        rolesField.setLabel("Roles");
        rolesField.setItems(allRoles.stream().map(Role::getName).collect(Collectors.toList()));
        rolesField.setValue(p.getRoles().stream().map(Role::getName).collect(Collectors.toSet()));

        VerticalLayout layout = new VerticalLayout(
            firstNameField,
            lastNameField,
            emailField,
            rolesField
        );
        add(layout);

        Button saveButton = new Button("Save", e -> save());
        Button cancelButton = new Button("Cancel", e -> close());
        getFooter().add(cancelButton, saveButton);
    }

    private void save() {
        if (firstNameField.isEmpty() || emailField.isEmpty()) {
            Notification.show("Please fill required fields", 3000, Notification.Position.MIDDLE);
            return;
        }

        participant.setFirstName(firstNameField.getValue());
        participant.setLastName(lastNameField.getValue());
        participant.setEmail(emailField.getValue());

        try {
            client.updateParticipant(participant);
            Notification.show("Participant updated", 3000, Notification.Position.BOTTOM_END);
            close();
        } catch (IOException ex) {
            Notification.show("Failed to update: " + ex.getMessage(), 5000, Notification.Position.MIDDLE);
        }
    }
}
```

**Output (TypeScript/React):**
```typescript
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Stack,
} from '@mui/material';
import { toast } from 'react-toastify';
import { useClients } from '../api/ClientProvider';
import { Participant } from '../types/Participant';
import { Role } from '../types/Role';

interface ParticipantEditDialogProps {
  participant: Participant;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function ParticipantEditDialog({
  participant,
  open,
  onClose,
  onSaved,
}: ParticipantEditDialogProps) {
  const { resourceClient } = useClients();
  const [firstName, setFirstName] = useState(participant.firstName);
  const [lastName, setLastName] = useState(participant.lastName);
  const [email, setEmail] = useState(participant.email);
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(
    new Set(participant.roles.map((r) => r.name))
  );
  const [allRoles, setAllRoles] = useState<Role[]>([]);

  // Load roles on mount
  useEffect(() => {
    resourceClient.getRoles().then(setAllRoles);
  }, [resourceClient]);

  const handleRoleToggle = (roleName: string) => {
    setSelectedRoles((prev) => {
      const next = new Set(prev);
      if (next.has(roleName)) {
        next.delete(roleName);
      } else {
        next.add(roleName);
      }
      return next;
    });
  };

  const handleSave = async () => {
    // Validation
    if (!firstName || !email) {
      toast.error('Please fill required fields');
      return;
    }

    // Update participant object
    const updated: Participant = {
      ...participant,
      firstName,
      lastName,
      email,
      roles: allRoles.filter((r) => selectedRoles.has(r.name)),
    };

    try {
      await resourceClient.updateParticipant(updated);
      toast.success('Participant updated');
      onSaved();
      onClose();
    } catch (error) {
      toast.error(`Failed to update: ${(error as Error).message}`);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Participant</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="First Name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            required
            fullWidth
          />
          <TextField
            label="Last Name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            fullWidth
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            fullWidth
          />
          <FormGroup>
            <label>Roles</label>
            {allRoles.map((role) => (
              <FormControlLabel
                key={role.id}
                control={
                  <Checkbox
                    checked={selectedRoles.has(role.name)}
                    onChange={() => handleRoleToggle(role.name)}
                  />
                }
                label={role.name}
              />
            ))}
          </FormGroup>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

**Generated Test:**
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ParticipantEditDialog } from './ParticipantEditDialog';
import { ClientProvider } from '../api/ClientProvider';
import { toast } from 'react-toastify';

jest.mock('react-toastify');

const mockParticipant = {
  id: '123',
  firstName: 'John',
  lastName: 'Doe',
  email: 'john@example.com',
  roles: [{ id: '1', name: 'Developer' }],
};

const mockRoles = [
  { id: '1', name: 'Developer' },
  { id: '2', name: 'Manager' },
];

const mockResourceClient = {
  getRoles: jest.fn().mockResolvedValue(mockRoles),
  updateParticipant: jest.fn().mockResolvedValue(undefined),
};

describe('ParticipantEditDialog', () => {
  const renderDialog = (props = {}) => {
    return render(
      <ClientProvider value={{ resourceClient: mockResourceClient }}>
        <ParticipantEditDialog
          participant={mockParticipant}
          open={true}
          onClose={jest.fn()}
          onSaved={jest.fn()}
          {...props}
        />
      </ClientProvider>
    );
  };

  it('renders with participant data', async () => {
    renderDialog();

    await waitFor(() => {
      expect(screen.getByLabelText('First Name')).toHaveValue('John');
      expect(screen.getByLabelText('Last Name')).toHaveValue('Doe');
      expect(screen.getByLabelText('Email')).toHaveValue('john@example.com');
    });
  });

  it('shows validation error for empty required fields', async () => {
    renderDialog();

    const firstNameInput = screen.getByLabelText('First Name');
    fireEvent.change(firstNameInput, { target: { value: '' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Please fill required fields');
    });
  });

  it('updates participant on save', async () => {
    const onSaved = jest.fn();
    const onClose = jest.fn();

    renderDialog({ onSaved, onClose });

    const firstNameInput = screen.getByLabelText('First Name');
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockResourceClient.updateParticipant).toHaveBeenCalledWith(
        expect.objectContaining({
          firstName: 'Jane',
        })
      );
      expect(toast.success).toHaveBeenCalledWith('Participant updated');
      expect(onSaved).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('toggles roles', async () => {
    renderDialog();

    await waitFor(() => {
      expect(screen.getByLabelText('Developer')).toBeChecked();
      expect(screen.getByLabelText('Manager')).not.toBeChecked();
    });

    fireEvent.click(screen.getByLabelText('Manager'));

    await waitFor(() => {
      expect(screen.getByLabelText('Manager')).toBeChecked();
    });
  });

  it('shows error on save failure', async () => {
    mockResourceClient.updateParticipant.mockRejectedValueOnce(
      new Error('Network error')
    );

    renderDialog();

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update: Network error');
    });
  });
});
```

---

## 9. Decision Matrices

### 9.1 Parser Selection Matrix

**Criteria Weights:**
- Performance: 30%
- Semantic Capabilities: 40%
- Python Integration: 20%
- Maintenance Burden: 10%

| Library | Performance | Semantic | Python Integration | Maintenance | Weighted Score | Rank |
|---------|------------|----------|-------------------|-------------|----------------|------|
| **tree-sitter-java** | 9/10 (⭐⭐⭐) | 6/10 (⭐⭐) | 10/10 (⭐⭐⭐) | 9/10 (⭐⭐⭐) | **7.7/10** | **1st** |
| javalang | 6/10 (⭐⭐) | 5/10 (⭐) | 10/10 (⭐⭐⭐) | 7/10 (⭐⭐) | 6.2/10 | 3rd |
| py4j | 4/10 (⭐) | 10/10 (⭐⭐⭐) | 5/10 (⭐) | 3/10 (⭐) | 6.1/10 | 4th |
| srcML | 7/10 (⭐⭐) | 4/10 (⭐) | 8/10 (⭐⭐) | 8/10 (⭐⭐⭐) | 6.3/10 | 2nd |

**Recommendation**: **tree-sitter-java** + custom semantic analyzer

### 9.2 Code Generation Strategy Matrix

**Criteria Weights:**
- Code Quality: 35%
- Development Speed: 25%
- Maintainability: 25%
- Flexibility: 15%

| Strategy | Code Quality | Dev Speed | Maintainability | Flexibility | Weighted Score | Rank |
|----------|-------------|-----------|----------------|-------------|----------------|------|
| Template-only | 7/10 | 9/10 | 9/10 | 5/10 | 7.5/10 | 3rd |
| AST-only | 9/10 | 5/10 | 6/10 | 9/10 | 7.4/10 | 4th |
| LLM-only | 8/10 | 6/10 | 7/10 | 8/10 | 7.4/10 | 4th |
| **Hybrid (Template + AST + LLM)** | 9/10 | 7/10 | 8/10 | 9/10 | **8.25/10** | **1st** |

**Recommendation**: **Hybrid approach** using all three strategies

### 9.3 UI Component Library Matrix

**Criteria Weights:**
- Component Parity: 40%
- TypeScript Support: 20%
- Community: 20%
- Learning Curve: 10%
- Bundle Size: 10%

| Library | Component Parity | TypeScript | Community | Learning Curve | Bundle Size | Weighted Score | Rank |
|---------|-----------------|-----------|-----------|---------------|-------------|----------------|------|
| **Material-UI (MUI)** | 9/10 | 10/10 | 10/10 | 7/10 | 6/10 | **8.9/10** | **1st** |
| Ant Design | 8/10 | 10/10 | 9/10 | 7/10 | 5/10 | 8.0/10 | 3rd |
| Chakra UI | 7/10 | 10/10 | 8/10 | 9/10 | 8/10 | 8.1/10 | 2nd |
| shadcn/ui | 7/10 | 10/10 | 7/10 | 6/10 | 9/10 | 7.7/10 | 4th |

**Recommendation**: **Material-UI (MUI)** for closest Vaadin parity

---

## 10. Summary and Recommendations

### 10.1 Recommended Tool Stack

**Backend (Java → Python):**
1. **Parser**: tree-sitter-java with custom semantic analyzer
2. **Generator**: Hybrid (Jinja2 templates + AST transformation + Claude API)
3. **QA**: mypy (strict) + ruff (ALL rules) + pytest + hypothesis

**Frontend (Java/Vaadin → TypeScript/React):**
1. **Parser**: tree-sitter-java for Vaadin code extraction
2. **Generator**: Template-based (Jinja2) for component mapping
3. **UI Library**: Material-UI (MUI) v5 for component parity
4. **QA**: TypeScript (strict) + eslint + jest + playwright

### 10.2 Implementation Roadmap

**Phase 1: Foundation (Weeks 1-2)**
- Set up tree-sitter-java parser
- Build semantic analyzer
- Create type mapper (Java → Python/TypeScript)
- Build template library (10-15 common patterns)

**Phase 2: Backend Generation (Weeks 3-5)**
- Implement AST-based class generator
- Implement template-based method generator
- Integrate Claude API for complex logic
- Build test generator

**Phase 3: Frontend Generation (Weeks 6-8)**
- Build Vaadin component analyzer
- Create React component templates (20-30 components)
- Implement event handler mapper
- Build state management mapper

**Phase 4: Quality Assurance (Weeks 9-10)**
- Implement behavior verifier (compare Java vs Python)
- Build pattern verifier (Pythonic code checks)
- Create quality metrics dashboard
- Integration testing

**Phase 5: Production Migration (Weeks 11-15)**
- Migrate 100+ YAWL classes to Python
- Migrate 30+ Vaadin views to React
- Manual review and refinement
- Performance optimization

**Total Estimated Time**: 15 weeks (3.75 months)

### 10.3 Success Criteria

**Generated code must**:
- ✅ Pass mypy --strict (100% type coverage)
- ✅ Pass ruff check (ALL 400+ rules, no suppressions)
- ✅ Pass pytest (80%+ coverage)
- ✅ Match Java behavior (100% equivalence on test cases)
- ✅ Follow Python patterns (95%+ compliance)
- ✅ Perform within 2x of Java (execution time)
- ✅ Reduce LOC by 30-50% (compared to Java)

### 10.4 Risk Mitigation

**Risk**: Complex business logic translation fails
- **Mitigation**: LLM-assisted generation with human review + behavior verification tests

**Risk**: UI state management differs between Vaadin (server) and React (client)
- **Mitigation**: Comprehensive React Query caching + manual architecture review

**Risk**: Performance degradation in Python
- **Mitigation**: Profile hotspots, use PyPy/Cython for critical paths

**Risk**: Type mapping ambiguity (e.g., Java generics)
- **Mitigation**: Conservative typing (use Any when unsure) + manual refinement

---

## 11. References

### Documentation
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Tree-sitter Java Grammar](https://github.com/tree-sitter/tree-sitter-java)
- [py-tree-sitter Python Bindings](https://github.com/tree-sitter/py-tree-sitter)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

### Related Research
- [j2objc: Java to Objective-C Translator](https://developers.google.com/j2objc)
- [GraalVM Polyglot Programming](https://www.graalvm.org/)
- [JTransc: Kotlin-based Java Transpiler](https://github.com/jtransc/jtransc)

### YAWL Project
- [YAWL Foundation](https://yawlfoundation.github.io/)
- [YAWL v5.2 Source Code](https://github.com/yawlfoundation/yawl)

---

**End of Document**
