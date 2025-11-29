# Semantic Code Generator Architecture (YAWL Java → Python/React)

**Status**: Architecture Design
**Target**: 122 Java files → Python/React migration
**Source**: `vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/`
**Scale**: ~18,243 lines of Java code

---

## Executive Summary

This document defines the architecture for a production-ready semantic code generator that converts 122 Java Vaadin UI files to Python FastAPI backend + React TypeScript frontend while maintaining:

- **100% type coverage** (Python typing, TypeScript interfaces)
- **80%+ test coverage** (pytest + Vitest)
- **Zero quality gate failures** (ruff, mypy, poe verify)
- **Semantic equivalence** (behavior preservation, not line-by-line translation)

**Key Insight**: This is NOT a line-by-line transpiler. This is a semantic migration that extracts domain logic from Java/Vaadin and re-implements it in Python/React using modern patterns.

---

## 1. System Architecture

### 1.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Batch Manager│→ │ Dependency   │→ │ Rollback     │         │
│  │              │  │ Resolver     │  │ Manager      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        PARSER LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Java AST     │→ │ Semantic     │→ │ Metadata     │         │
│  │ Parser       │  │ Analyzer     │  │ Extractor    │         │
│  │ (JavaParser) │  │              │  │ (JSON/dict)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       MAPPING LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Type Mapper  │→ │ Pattern      │→ │ API/UI       │         │
│  │ (Java→Py/TS) │  │ Translator   │  │ Splitter     │         │
│  │              │  │ (Vaadin→React│  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      TEMPLATE LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Python       │  │ TypeScript   │  │ Test         │         │
│  │ Generator    │  │ Generator    │  │ Generator    │         │
│  │ (Jinja2)     │  │ (Jinja2)     │  │ (Pytest)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     VALIDATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Type Check   │→ │ Lint         │→ │ Test         │         │
│  │ (mypy/tsc)   │  │ (ruff/eslint)│  │ Execution    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT ARTIFACTS                           │
│  src/kgcl/yawl_ui/   │   frontend/    │    tests/              │
│  - api/              │   - components/ │    - test_api.py      │
│  - models/           │   - hooks/      │    - *.test.tsx       │
│  - services/         │   - types/      │                       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Java Source Files
    ↓
[AST Parse] → Java AST
    ↓
[Semantic Analysis] → Domain Model (classes, methods, types, relationships)
    ↓
[Pattern Detection] → Categorization (View, Service, Model, Listener, etc.)
    ↓
[API/UI Split] → Backend Metadata + Frontend Metadata
    ↓
[Type Mapping] → Python types + TypeScript interfaces
    ↓
[Template Rendering] → Python files + React files + Test files
    ↓
[Validation] → mypy, ruff, pytest, tsc, eslint, vitest
    ↓
[Quality Gates] → PASS (commit) or FAIL (rollback)
```

---

## 2. Component Specifications

### 2.1 Parser Layer

**Technology**: `javalang` Python library (pure Python, no JDK dependency)

**Input**: Java source files (`.java`)
**Output**: Semantic metadata (JSON/dict)

**Responsibilities**:
1. Parse Java source to AST
2. Extract classes, methods, fields, annotations
3. Resolve types (including generics)
4. Identify inheritance/interface relationships
5. Extract Javadoc/comments

**Data Structure** (Python dataclass):

```python
@dataclass(frozen=True)
class JavaClass:
    """Semantic metadata for a Java class."""
    package: str
    name: str
    extends: str | None
    implements: list[str]
    fields: list[JavaField]
    methods: list[JavaMethod]
    annotations: list[JavaAnnotation]
    javadoc: str | None
    is_abstract: bool
    is_interface: bool
    category: ClassCategory  # View, Service, Model, Listener, etc.

@dataclass(frozen=True)
class JavaMethod:
    """Semantic metadata for a Java method."""
    name: str
    return_type: str
    parameters: list[JavaParameter]
    annotations: list[JavaAnnotation]
    throws: list[str]
    is_static: bool
    is_abstract: bool
    visibility: str  # public, private, protected
    javadoc: str | None

@dataclass(frozen=True)
class JavaField:
    """Semantic metadata for a Java field."""
    name: str
    type: str
    is_static: bool
    is_final: bool
    visibility: str
    default_value: str | None
```

**Pattern Detection** (14 packages):

| Package | Pattern | Python Target | React Target |
|---------|---------|---------------|--------------|
| `ui.announce` | Notification utility | FastAPI response models | Toast/Alert component |
| `ui.component` | Vaadin components | Data models | React components |
| `ui.dialog` | Modal dialogs | API endpoints | Modal components |
| `ui.dynform` | Dynamic forms | Form validation | Dynamic form builder |
| `ui.layout` | Layout components | N/A (frontend only) | Layout components |
| `ui.listener` | Event handlers | FastAPI dependencies | React hooks |
| `ui.menu` | Navigation | API routes | Navigation component |
| `ui.service` | Business logic | Service layer | API client |
| `ui.util` | Utilities | Utils module | Utils module |
| `ui.view` | Main views | API controllers | Page components |

### 2.2 Mapping Layer

**Type Mapper** (Java → Python/TypeScript):

| Java Type | Python Type | TypeScript Type |
|-----------|-------------|-----------------|
| `String` | `str` | `string` |
| `int`, `Integer` | `int` | `number` |
| `long`, `Long` | `int` | `number` |
| `boolean`, `Boolean` | `bool` | `boolean` |
| `List<T>` | `list[T]` | `T[]` |
| `Map<K, V>` | `dict[K, V]` | `Record<K, V>` |
| `Optional<T>` | `T \| None` | `T \| null` |
| `LocalDateTime` | `datetime` | `string (ISO 8601)` |
| `BigDecimal` | `Decimal` | `string` |
| Custom class | Pydantic model | TypeScript interface |

**Pattern Translator** (Vaadin → React):

| Vaadin Pattern | React Pattern |
|----------------|---------------|
| `Button` | `<Button>` component |
| `TextField` | `<Input>` component |
| `Grid<T>` | `<Table<T>>` component |
| `Dialog` | `<Modal>` component |
| `Notification.show()` | `toast()` from react-hot-toast |
| `@Route("/path")` | React Router route |
| `VerticalLayout` | Flexbox column |
| `HorizontalLayout` | Flexbox row |

**API/UI Splitter**:

```python
@dataclass(frozen=True)
class BackendMetadata:
    """Metadata for Python backend generation."""
    models: list[PydanticModel]
    services: list[ServiceClass]
    api_routes: list[APIRoute]
    dependencies: list[str]

@dataclass(frozen=True)
class FrontendMetadata:
    """Metadata for React frontend generation."""
    components: list[ReactComponent]
    hooks: list[ReactHook]
    types: list[TypeScriptInterface]
    api_client: APIClient
```

**Rules**:
- **Backend**: Business logic, data validation, state management
- **Frontend**: UI rendering, user interaction, local state
- **Shared**: Type definitions (Pydantic → TypeScript via datamodel-code-generator)

### 2.3 Template Layer

**Template Catalog** (Jinja2 templates):

#### Python Templates

| Template | Purpose | Output |
|----------|---------|--------|
| `api_route.py.j2` | FastAPI route handler | `src/kgcl/yawl_ui/api/routes/{name}.py` |
| `pydantic_model.py.j2` | Data model | `src/kgcl/yawl_ui/models/{name}.py` |
| `service.py.j2` | Business logic service | `src/kgcl/yawl_ui/services/{name}.py` |
| `client.py.j2` | External API client | `src/kgcl/yawl_ui/clients/{name}.py` |
| `test_api.py.j2` | Pytest test suite | `tests/yawl_ui/api/test_{name}.py` |
| `test_service.py.j2` | Service unit tests | `tests/yawl_ui/services/test_{name}.py` |

**Example** (`pydantic_model.py.j2`):

```jinja2
"""{{ model.description }}

Auto-generated from Java class: {{ model.java_source }}
"""

from __future__ import annotations

from pydantic import BaseModel, Field{% if model.has_validators %}, field_validator{% endif %}
{% for import in model.imports %}
{{ import }}
{% endfor %}

class {{ model.name }}(BaseModel):
    """{{ model.docstring }}"""

    {% for field in model.fields %}
    {{ field.name }}: {{ field.type }} = Field(
        {% if field.default %}default={{ field.default }}, {% endif %}
        description="{{ field.description }}"
    )
    {% endfor %}

    {% for validator in model.validators %}
    @field_validator("{{ validator.field_name }}")
    @classmethod
    def {{ validator.name }}(cls, value: {{ validator.type }}) -> {{ validator.type }}:
        """{{ validator.description }}"""
        {{ validator.body | indent(8) }}
        return value
    {% endfor %}
```

#### TypeScript Templates

| Template | Purpose | Output |
|----------|---------|--------|
| `component.tsx.j2` | React component | `frontend/src/components/{name}.tsx` |
| `hook.ts.j2` | React custom hook | `frontend/src/hooks/use{name}.ts` |
| `types.ts.j2` | TypeScript interfaces | `frontend/src/types/{name}.ts` |
| `api_client.ts.j2` | Axios API client | `frontend/src/api/{name}Client.ts` |
| `component.test.tsx.j2` | Vitest component test | `frontend/src/components/{name}.test.tsx` |

**Example** (`component.tsx.j2`):

```jinja2
/**
 * {{ component.description }}
 *
 * Auto-generated from Java class: {{ component.java_source }}
 */

import React from 'react';
{% for import in component.imports %}
{{ import }}
{% endfor %}

export interface {{ component.name }}Props {
    {% for prop in component.props %}
    {{ prop.name }}{{ '?' if prop.optional else '' }}: {{ prop.type }};
    {% endfor %}
}

export const {{ component.name }}: React.FC<{{ component.name }}Props> = ({
    {% for prop in component.props %}
    {{ prop.name }}{{ ', ' if not loop.last else '' }}
    {% endfor %}
}) => {
    {% for state in component.state %}
    const [{{ state.name }}, set{{ state.name | capitalize }}] = React.useState<{{ state.type }}>({{ state.default }});
    {% endfor %}

    {% for effect in component.effects %}
    React.useEffect(() => {
        {{ effect.body | indent(8) }}
    }, [{{ effect.dependencies | join(', ') }}]);
    {% endfor %}

    return (
        {{ component.jsx | indent(8) }}
    );
};
```

### 2.4 Validation Layer

**Quality Gates** (MANDATORY - no bypassing):

```python
@dataclass(frozen=True)
class QualityGate:
    """Quality gate validation result."""
    name: str
    command: str
    passed: bool
    output: str
    duration_ms: int

# Gates (in order)
QUALITY_GATES = [
    QualityGate(name="format", command="poe format", ...),
    QualityGate(name="lint", command="poe lint", ...),
    QualityGate(name="type-check", command="poe type-check", ...),
    QualityGate(name="test", command="poe test", ...),
    QualityGate(name="detect-lies", command="poe detect-lies", ...),
]
```

**Validation Workflow**:

1. **Format Check**: `poe format` (ruff format)
2. **Lint Check**: `poe lint` (ruff check --fix)
3. **Type Check**: `poe type-check` (mypy strict)
4. **Test Execution**: `poe test` (pytest with 80%+ coverage)
5. **Lie Detection**: `poe detect-lies` (no TODO/FIXME/stubs)

**Failure Handling**:
- If ANY gate fails: ROLLBACK all generated files
- Log failure details to `reports/codegen_failures.json`
- Return detailed error report to orchestrator
- DO NOT commit partially-working code

### 2.5 Orchestration Layer

**Batch Processing Strategy**: Package-by-Package with Dependency Resolution

**Rationale**:
- 14 packages with clear boundaries
- Some packages depend on others (e.g., `ui.view` depends on `ui.component`)
- Incremental validation reduces rollback scope
- Parallel processing within package (files independent)

**Processing Order** (topological sort):

```python
PACKAGE_ORDER = [
    # Tier 1: No dependencies
    "ui.util",          # 9 files - utilities
    "ui.announce",      # 2 files - notifications
    "ui.layout",        # 3 files - layout components

    # Tier 2: Depends on Tier 1
    "ui.listener",      # 4 files - event handlers
    "ui.component",     # 8 files - reusable components

    # Tier 3: Depends on Tier 2
    "ui.dynform",       # 25 files - dynamic forms
    "ui.dialog",        # 15 files - modal dialogs
    "ui.service",       # 12 files - business logic

    # Tier 4: Depends on Tier 3
    "ui.menu",          # 4 files - navigation
    "ui.view",          # 32 files - main views
    "ui.dialog.orgdata",     # 6 files - org data dialogs
    "ui.dialog.upload",      # 1 file - upload dialog
    "ui.dialog.worklet",     # 1 file - worklet dialog
    "ui.dynform.dynattributes",  # 1 file - dynamic attributes
]
```

**Parallel Execution** (within package):

```python
@dataclass(frozen=True)
class BatchJob:
    """Batch processing job."""
    package: str
    files: list[Path]
    dependencies: list[str]  # Package names this depends on
    max_parallel: int = 4    # Parallel file processing

async def process_package(job: BatchJob) -> PackageResult:
    """Process all files in package in parallel."""
    tasks = [
        generate_from_java_file(file, job.package)
        for file in job.files
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Validate entire package
    validation = await validate_package_output(job.package)

    if not validation.all_passed:
        await rollback_package(job.package)
        raise CodegenValidationError(validation.failures)

    return PackageResult(package=job.package, files=results, validation=validation)
```

**Dependency Resolution**:

```python
def resolve_dependencies() -> list[BatchJob]:
    """Resolve package dependencies and create processing order."""
    graph = build_dependency_graph(PACKAGE_ORDER)
    sorted_packages = topological_sort(graph)

    return [
        BatchJob(
            package=pkg,
            files=find_java_files(pkg),
            dependencies=graph[pkg].dependencies
        )
        for pkg in sorted_packages
    ]
```

---

## 3. Implementation Details

### 3.1 File Organization

**Output Structure**:

```
src/kgcl/yawl_ui/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── cases.py          # From CasesView.java
│   │   ├── participants.py   # From ParticipantsView.java
│   │   └── ...
│   └── dependencies.py
├── models/
│   ├── __init__.py
│   ├── announcement.py       # From Announcement.java
│   ├── task_privileges.py    # From TaskPrivilegesCache.java
│   └── ...
├── services/
│   ├── __init__.py
│   ├── case_service.py
│   ├── participant_service.py
│   └── ...
├── clients/
│   ├── __init__.py
│   ├── yawl_client.py
│   └── ...
└── utils/
    ├── __init__.py
    ├── ui_helpers.py         # From UiUtil.java
    └── ...

frontend/
├── src/
│   ├── components/
│   │   ├── announce/
│   │   │   ├── Announcement.tsx
│   │   │   └── ErrorMsg.tsx
│   │   ├── layout/
│   │   │   ├── VerticalScrollLayout.tsx
│   │   │   └── ...
│   │   ├── views/
│   │   │   ├── CasesView.tsx
│   │   │   ├── ParticipantsView.tsx
│   │   │   └── ...
│   │   └── dialogs/
│   │       └── ...
│   ├── hooks/
│   │   ├── useAuthentication.ts
│   │   ├── useCases.ts
│   │   └── ...
│   ├── api/
│   │   ├── casesClient.ts
│   │   ├── participantsClient.ts
│   │   └── ...
│   └── types/
│       ├── announcement.ts
│       ├── case.ts
│       └── ...
└── tests/
    └── components/
        └── *.test.tsx

tests/
├── yawl_ui/
│   ├── api/
│   │   ├── test_cases.py
│   │   └── ...
│   ├── services/
│   │   ├── test_case_service.py
│   │   └── ...
│   └── models/
│       ├── test_announcement.py
│       └── ...
└── conftest.py
```

### 3.2 Type Coverage Strategy

**Python** (100% mypy strict):

```python
# All functions must have full type hints
def convert_java_type(java_type: str, context: TypeContext) -> str:
    """Convert Java type to Python type annotation.

    Parameters
    ----------
    java_type : str
        Java type string (e.g., "List<String>", "Map<String, Integer>")
    context : TypeContext
        Type resolution context (imports, generic bounds)

    Returns
    -------
    str
        Python type annotation (e.g., "list[str]", "dict[str, int]")
    """
    # Implementation with full type safety
    ...

# Pydantic models ensure runtime type validation
class AnnouncementModel(BaseModel):
    """Announcement notification model."""
    message: str = Field(description="Notification message")
    variant: NotificationVariant = Field(description="Notification type")
    duration_ms: int = Field(default=5000, description="Display duration")
    position: NotificationPosition = Field(default=NotificationPosition.TOP_END)
```

**TypeScript** (strict mode):

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true
  }
}

// All interfaces fully typed
export interface AnnouncementProps {
  message: string;
  variant: NotificationVariant;
  duration?: number;
  position?: NotificationPosition;
  onClose?: () => void;
}

export const Announcement: React.FC<AnnouncementProps> = ({
  message,
  variant,
  duration = 5000,
  position = 'top-end',
  onClose
}) => {
  // Full type safety throughout
  ...
};
```

### 3.3 Test Generation Strategy

**Backend Tests** (pytest + Chicago School TDD):

```python
# tests/yawl_ui/api/test_cases.py
"""Test cases API endpoints.

Auto-generated from CasesView.java
"""

from fastapi.testclient import TestClient
from kgcl.yawl_ui.api.main import app
from kgcl.yawl_ui.models.case import CaseModel

client = TestClient(app)

def test_get_cases_returns_list():
    """Test GET /cases returns list of cases."""
    # Arrange
    # (No mocking - real endpoint, real response)

    # Act
    response = client.get("/api/cases")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Validate each item is a valid CaseModel
    for item in response.json():
        CaseModel.model_validate(item)

def test_get_case_by_id_returns_case():
    """Test GET /cases/{id} returns specific case."""
    # Arrange
    case_id = "test-case-001"

    # Act
    response = client.get(f"/api/cases/{case_id}")

    # Assert
    assert response.status_code == 200
    case = CaseModel.model_validate(response.json())
    assert case.id == case_id

def test_create_case_returns_created():
    """Test POST /cases creates new case."""
    # Arrange
    new_case = {
        "specification_id": "spec-001",
        "case_params": {"key": "value"}
    }

    # Act
    response = client.post("/api/cases", json=new_case)

    # Assert
    assert response.status_code == 201
    created = CaseModel.model_validate(response.json())
    assert created.specification_id == "spec-001"
```

**Frontend Tests** (Vitest + React Testing Library):

```typescript
// frontend/src/components/views/CasesView.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { CasesView } from './CasesView';
import * as casesClient from '../../api/casesClient';

describe('CasesView', () => {
  it('renders cases list', async () => {
    // Arrange
    const mockCases = [
      { id: 'case-001', specificationId: 'spec-001', status: 'active' },
      { id: 'case-002', specificationId: 'spec-002', status: 'completed' }
    ];
    vi.spyOn(casesClient, 'getCases').mockResolvedValue(mockCases);

    // Act
    render(<CasesView />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText('case-001')).toBeInTheDocument();
      expect(screen.getByText('case-002')).toBeInTheDocument();
    });
  });

  it('creates new case on button click', async () => {
    // Arrange
    const user = userEvent.setup();
    const createSpy = vi.spyOn(casesClient, 'createCase').mockResolvedValue({
      id: 'case-003',
      specificationId: 'spec-001',
      status: 'active'
    });

    render(<CasesView />);

    // Act
    await user.click(screen.getByRole('button', { name: /create case/i }));
    await user.selectOptions(screen.getByLabelText(/specification/i), 'spec-001');
    await user.click(screen.getByRole('button', { name: /submit/i }));

    // Assert
    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({ specificationId: 'spec-001' });
      expect(screen.getByText('case-003')).toBeInTheDocument();
    });
  });
});
```

**Coverage Requirements**:
- **Backend**: 80%+ line coverage (pytest-cov)
- **Frontend**: 80%+ branch coverage (vitest coverage)
- **Integration**: E2E tests for critical flows (Playwright)

### 3.4 Rollback Strategy

**Rollback Triggers**:
1. Type check failure (mypy/tsc errors)
2. Lint failure (ruff/eslint errors)
3. Test failure (any test fails or <80% coverage)
4. Lie detection (TODO/FIXME/stubs found)
5. Import error (missing dependency)

**Rollback Process**:

```python
@dataclass(frozen=True)
class RollbackContext:
    """Context for rolling back generated code."""
    package: str
    generated_files: list[Path]
    backup_path: Path
    timestamp: datetime

async def rollback_package(context: RollbackContext) -> None:
    """Rollback all generated files for a package.

    Parameters
    ----------
    context : RollbackContext
        Rollback context with file list and backup path
    """
    # 1. Delete all generated files
    for file in context.generated_files:
        if file.exists():
            file.unlink()

    # 2. Restore from backup if exists
    if context.backup_path.exists():
        shutil.copytree(context.backup_path, context.package_dir, dirs_exist_ok=True)

    # 3. Log rollback event
    log_rollback_event(
        package=context.package,
        reason="quality gate failure",
        timestamp=context.timestamp,
        files_rolled_back=len(context.generated_files)
    )

    # 4. Clean up backup
    shutil.rmtree(context.backup_path)
```

**Backup Strategy**:
- Before generating package: snapshot existing files
- Store in `/tmp/codegen_backup_{package}_{timestamp}/`
- Restore on failure, delete on success
- Keep last 3 backups for debugging

---

## 4. Quality Assurance

### 4.1 Pre-Generation Validation

**Java Source Validation**:
```python
def validate_java_source(file: Path) -> ValidationResult:
    """Validate Java source file before processing.

    Checks:
    - File exists and is readable
    - Valid Java syntax (parseable)
    - No compilation errors
    - Uses only supported patterns
    """
    ...
```

### 4.2 Post-Generation Validation

**Python Validation** (MANDATORY gates):

```bash
# 1. Format check
poe format
# Must exit 0 (no formatting needed)

# 2. Lint check
poe lint
# Must exit 0 (no errors)

# 3. Type check
poe type-check
# Must exit 0 (100% type coverage, strict mode)

# 4. Test execution
poe test
# Must exit 0 (all pass, 80%+ coverage)

# 5. Lie detection
poe detect-lies
# Must exit 0 (no TODO/FIXME/stubs)
```

**TypeScript Validation**:

```bash
# 1. Type check
npm run type-check
# Must exit 0 (tsc strict mode)

# 2. Lint
npm run lint
# Must exit 0 (eslint rules)

# 3. Test
npm run test
# Must exit 0 (vitest, 80%+ coverage)
```

### 4.3 Continuous Validation

**CI/CD Pipeline** (GitHub Actions):

```yaml
# .github/workflows/codegen-validation.yml
name: Codegen Validation

on:
  push:
    paths:
      - 'src/kgcl/yawl_ui/**'
      - 'frontend/src/**'

jobs:
  validate-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: uv sync
      - run: poe verify  # All gates

  validate-typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run verify  # Type check + lint + test
```

---

## 5. Execution Plan

### Phase 1: Infrastructure (Week 1)

**Deliverables**:
- [ ] Parser layer implementation (`JavaParser` with `javalang`)
- [ ] Semantic analyzer (pattern detection)
- [ ] Type mapper (Java → Python/TypeScript)
- [ ] Template infrastructure (Jinja2 setup)
- [ ] Validation framework (quality gates)
- [ ] Rollback mechanism

**Tests**:
- [ ] Parse all 122 Java files successfully
- [ ] Detect all 14 package patterns
- [ ] Map 100 sample types correctly
- [ ] Render 5 template examples
- [ ] Execute quality gates on test artifacts
- [ ] Rollback test generation successfully

### Phase 2: Tier 1 Packages (Week 2)

**Target**: 14 files (util, announce, layout)

**Process**:
1. Generate Python models/services
2. Generate React components
3. Generate tests (80%+ coverage)
4. Run quality gates
5. Rollback on failure, iterate
6. Commit on success

**Success Criteria**:
- [ ] All 14 files generate successfully
- [ ] 100% type coverage (Python + TypeScript)
- [ ] 80%+ test coverage
- [ ] All quality gates pass
- [ ] No TODO/FIXME/stubs

### Phase 3: Tier 2 Packages (Week 3)

**Target**: 12 files (listener, component)

**Dependencies**: Tier 1 complete

**Process**: Same as Phase 2

**Success Criteria**: Same as Phase 2

### Phase 4: Tier 3 Packages (Week 4-5)

**Target**: 52 files (dynform, dialog, service)

**Dependencies**: Tier 2 complete

**Process**: Same as Phase 2

**Success Criteria**: Same as Phase 2

### Phase 5: Tier 4 Packages (Week 6)

**Target**: 44 files (menu, view, dialog subpackages)

**Dependencies**: Tier 3 complete

**Process**: Same as Phase 2

**Success Criteria**: Same as Phase 2

### Phase 6: Integration & E2E (Week 7)

**Deliverables**:
- [ ] Full integration tests (backend ↔ frontend)
- [ ] E2E tests (Playwright)
- [ ] Performance benchmarks
- [ ] Documentation (API docs, component storybook)
- [ ] Deployment scripts

**Success Criteria**:
- [ ] All integration tests pass
- [ ] E2E tests cover critical flows
- [ ] Performance meets SLAs (<100ms p99)
- [ ] Documentation complete

---

## 6. Risk Mitigation

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Java parsing failures | Medium | High | Use battle-tested `javalang`, fallback to manual annotation |
| Type mapping errors | High | High | Comprehensive type mapper tests, manual review of edge cases |
| Template bugs | High | Medium | Template unit tests, dry-run before batch generation |
| Quality gate failures | High | High | Incremental validation, rollback mechanism |
| Missing dependencies | Medium | Medium | Dependency graph validation, topological sort |
| Coverage below 80% | Medium | High | Test template improvements, manual test writing |

### 6.2 Process Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | Medium | High | Strict focus on 122 files, defer enhancements to Phase 7 |
| Timeline delays | Medium | High | Weekly milestones, early warning system |
| Quality regression | Low | Critical | MANDATORY quality gates, no bypass allowed |
| Rollback data loss | Low | Critical | Backup mechanism, version control |

---

## 7. Success Metrics

### 7.1 Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Files generated | 122/122 (100%) | Count of output files |
| Type coverage | 100% | mypy + tsc reports |
| Test coverage | ≥80% | pytest-cov + vitest coverage |
| Quality gates pass rate | 100% | CI/CD pipeline status |
| Lines of code | ~18,000 LOC | Generated Python + TypeScript |
| Generation time | <2 hours | Total batch processing time |
| Rollback rate | <5% | Failed packages / total packages |

### 7.2 Qualitative Metrics

| Metric | Criteria |
|--------|----------|
| Code readability | Human-reviewable, follows PEP 8 / Airbnb style guide |
| Maintainability | Modular, DRY, SOLID principles |
| Documentation | NumPy-style docstrings, JSDoc comments |
| Semantic correctness | Preserves business logic from Java |
| Developer experience | Easy to understand, extend, debug |

---

## 8. Architecture Decision Records

### ADR-001: Use Jinja2 for Templates (Not AST Generation)

**Context**: Two approaches for code generation:
1. AST manipulation (using `ast` module for Python, TypeScript Compiler API)
2. Template rendering (using Jinja2)

**Decision**: Use Jinja2 templates

**Rationale**:
- **Maintainability**: Templates are human-readable, easy to modify
- **Separation of concerns**: Logic in Python, presentation in templates
- **Flexibility**: Can generate any text format (Python, TypeScript, tests, docs)
- **Proven**: Jinja2 is battle-tested, widely used

**Consequences**:
- ✅ Easy to customize output format
- ✅ Non-programmers can edit templates
- ❌ Less type safety than AST (mitigated by validation layer)

### ADR-002: Package-by-Package Processing (Not All-At-Once)

**Context**: Two batch processing strategies:
1. Generate all 122 files at once
2. Process package-by-package with dependency resolution

**Decision**: Package-by-package processing

**Rationale**:
- **Risk reduction**: Smaller rollback scope on failure
- **Incremental validation**: Quality gates per package
- **Dependency management**: Clear processing order
- **Debugging**: Easier to isolate failures

**Consequences**:
- ✅ Safer rollback (only failed package affected)
- ✅ Easier debugging
- ❌ Slightly longer total time (sequential packages)

### ADR-003: Semantic Migration (Not Line-by-Line Translation)

**Context**: Two migration approaches:
1. Line-by-line translation (transpiler)
2. Semantic extraction and re-implementation

**Decision**: Semantic migration

**Rationale**:
- **Better patterns**: Use FastAPI + React best practices, not Java patterns
- **Type safety**: Leverage Pydantic, TypeScript strict mode
- **Maintainability**: Idiomatic Python/TypeScript, not Java-isms
- **Quality**: Meet KGCL quality standards (100% types, 80% coverage)

**Consequences**:
- ✅ Production-quality output
- ✅ Idiomatic Python/TypeScript
- ❌ More complex translation logic

### ADR-004: 100% Type Coverage (No Gradual Typing)

**Context**: Python supports gradual typing (`# type: ignore`, `Any`)

**Decision**: 100% type coverage, mypy strict mode

**Rationale**:
- **KGCL standard**: Lean Six Sigma quality, zero defects
- **Runtime safety**: Pydantic validates at runtime
- **Developer experience**: Full IDE autocomplete
- **Maintainability**: Types as documentation

**Consequences**:
- ✅ Zero type-related runtime errors
- ✅ Excellent IDE support
- ❌ More upfront effort in type mapping

### ADR-005: No Test Skipping (Even for Generated Code)

**Context**: Generated code might have edge cases that are hard to test

**Decision**: NO test skipping allowed (`@pytest.mark.skip` forbidden)

**Rationale**:
- **KGCL policy**: "If you write a test, make it pass"
- **Quality**: Generated code must be production-ready
- **Confidence**: 80%+ coverage ensures robustness

**Consequences**:
- ✅ High confidence in generated code
- ✅ Catches template bugs early
- ❌ Requires comprehensive test templates

---

## 9. Future Enhancements (Phase 7+)

**Not in scope for initial 122-file migration, but potential future work:**

1. **Incremental Regeneration**: Only regenerate changed Java files
2. **Custom Annotations**: Support `@CodegenIgnore`, `@CodegenHint` in Java
3. **Multi-Language Support**: Extend to Java → Go, Java → Rust
4. **AI-Assisted Translation**: Use LLM for complex logic translation
5. **Interactive Mode**: Review/edit generated code before commit
6. **Metrics Dashboard**: Real-time generation progress, quality metrics
7. **Template Marketplace**: Share/reuse templates across projects

---

## 10. Appendix

### A. Technology Stack

**Python**:
- `javalang`: Java AST parsing
- `jinja2`: Template rendering
- `pydantic`: Runtime type validation
- `fastapi`: API framework
- `pytest`: Testing framework
- `mypy`: Static type checking
- `ruff`: Linting + formatting

**TypeScript/React**:
- `react`: UI framework
- `typescript`: Type system
- `vitest`: Testing framework
- `react-testing-library`: Component testing
- `axios`: HTTP client
- `react-hot-toast`: Notifications
- `eslint`: Linting

**Infrastructure**:
- `uv`: Python package manager
- `npm`: Node package manager
- `github-actions`: CI/CD
- `playwright`: E2E testing

### B. Glossary

| Term | Definition |
|------|------------|
| **Semantic Migration** | Extracting business logic/intent from source language and re-implementing in target language using idiomatic patterns |
| **Quality Gate** | Automated check that must pass before code is committed (type check, lint, test, etc.) |
| **Rollback** | Reverting generated code to previous state when quality gates fail |
| **Template** | Jinja2 template file that generates code from metadata |
| **Metadata** | Structured data extracted from Java source (classes, methods, types, etc.) |
| **Batch Job** | Processing unit for a single package (multiple files processed in parallel) |
| **Type Coverage** | Percentage of code with explicit type annotations (target: 100%) |
| **Test Coverage** | Percentage of code executed by tests (target: ≥80%) |

### C. References

- **KGCL Project Standards**: `/Users/sac/dev/kgcl/CLAUDE.md`
- **YAWL Source**: `vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/`
- **Java Parser Library**: https://github.com/c2nes/javalang
- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **Pydantic Documentation**: https://docs.pydantic.dev/
- **Vitest Documentation**: https://vitest.dev/

---

**Document Version**: 1.0
**Last Updated**: 2025-11-28
**Author**: System Architecture Designer
**Status**: Ready for Implementation
