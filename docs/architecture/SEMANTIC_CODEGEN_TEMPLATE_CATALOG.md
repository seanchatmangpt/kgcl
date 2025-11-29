# Semantic Code Generator - Template Catalog

**System**: YAWL Java → Python/React Migration
**Version**: 1.0
**Date**: 2025-11-28

---

## Template Directory Structure

```
templates/
├── python/
│   ├── models/
│   │   ├── pydantic_model.py.j2
│   │   ├── enum_model.py.j2
│   │   └── base_model.py.j2
│   ├── api/
│   │   ├── router.py.j2
│   │   ├── endpoint.py.j2
│   │   └── dependencies.py.j2
│   ├── services/
│   │   ├── service_class.py.j2
│   │   ├── client_class.py.j2
│   │   └── base_service.py.j2
│   ├── utils/
│   │   ├── utility_module.py.j2
│   │   └── helper_functions.py.j2
│   └── tests/
│       ├── test_model.py.j2
│       ├── test_api.py.j2
│       ├── test_service.py.j2
│       └── conftest.py.j2
├── typescript/
│   ├── components/
│   │   ├── component.tsx.j2
│   │   ├── modal_component.tsx.j2
│   │   ├── form_component.tsx.j2
│   │   └── layout_component.tsx.j2
│   ├── hooks/
│   │   ├── use_api.ts.j2
│   │   ├── use_form.ts.j2
│   │   └── use_state.ts.j2
│   ├── api/
│   │   ├── api_client.ts.j2
│   │   └── types.ts.j2
│   ├── types/
│   │   ├── interface.ts.j2
│   │   ├── enum.ts.j2
│   │   └── type_alias.ts.j2
│   └── tests/
│       ├── component.test.tsx.j2
│       └── hook.test.ts.j2
└── shared/
    ├── __init__.py.j2
    ├── package.json.j2
    └── README.md.j2
```

---

## Python Templates

### 1. Pydantic Model Template

**File**: `templates/python/models/pydantic_model.py.j2`

**Usage**: Generate data models from Java classes (DTOs, entities)

**Template**:

```jinja2
"""{{ model.description }}

Auto-generated from Java class: {{ model.java_source }}
Generated on: {{ generation_timestamp }}
"""

from __future__ import annotations

from typing import {% if model.has_optional %}Optional, {% endif %}{% if model.has_list %}List, {% endif %}{% if model.has_dict %}Dict, {% endif %}Any
from pydantic import BaseModel, Field{% if model.has_validators %}, field_validator{% endif %}{% if model.has_root_validator %}, model_validator{% endif %}
{% for import_stmt in model.python_imports %}
{{ import_stmt }}
{% endfor %}


class {{ model.name }}(BaseModel):
    """{{ model.docstring }}

    Attributes
    ----------
    {% for field in model.fields %}
    {{ field.name }} : {{ field.type }}
        {{ field.description }}
    {% endfor %}

    Examples
    --------
    >>> {{ model.name.lower() }} = {{ model.name }}(
    ...     {% for field in model.fields[:2] %}{{ field.name }}={{ field.example_value }}{{ ', ' if not loop.last else '' }}
    ...     {% endfor %}
    ... )
    >>> {{ model.name.lower() }}.{{ model.fields[0].name }}
    {{ model.fields[0].example_value }}
    """

    {% for field in model.fields %}
    {{ field.name }}: {{ field.type }} = Field(
        {% if field.default is not none %}default={{ field.default }},
        {% endif %}{% if field.default_factory %}default_factory={{ field.default_factory }},
        {% endif %}description="{{ field.description }}",
        {% if field.min_length %}min_length={{ field.min_length }},
        {% endif %}{% if field.max_length %}max_length={{ field.max_length }},
        {% endif %}{% if field.ge is not none %}ge={{ field.ge }},
        {% endif %}{% if field.le is not none %}le={{ field.le }},
        {% endif %}{% if field.pattern %}pattern=r"{{ field.pattern }}",
        {% endif %}{% if field.examples %}examples={{ field.examples }},
        {% endif %}
    )
    {% endfor %}

    {% if model.has_validators %}
    {% for validator in model.validators %}
    @field_validator("{{ validator.field_name }}")
    @classmethod
    def {{ validator.name }}(cls, value: {{ validator.type }}) -> {{ validator.type }}:
        """{{ validator.description }}

        Parameters
        ----------
        value : {{ validator.type }}
            The value to validate

        Returns
        -------
        {{ validator.type }}
            The validated value

        Raises
        ------
        ValueError
            If validation fails
        """
        {{ validator.body | indent(8) }}
        return value
    {% endfor %}
    {% endif %}

    {% if model.has_root_validator %}
    @model_validator(mode="after")
    def {{ model.root_validator.name }}(self) -> {{ model.name }}:
        """{{ model.root_validator.description }}"""
        {{ model.root_validator.body | indent(8) }}
        return self
    {% endif %}

    {% if model.has_custom_methods %}
    {% for method in model.custom_methods %}
    def {{ method.name }}(self{% for param in method.parameters %}, {{ param.name }}: {{ param.type }}{% endfor %}) -> {{ method.return_type }}:
        """{{ method.description }}

        Parameters
        ----------
        {% for param in method.parameters %}
        {{ param.name }} : {{ param.type }}
            {{ param.description }}
        {% endfor %}

        Returns
        -------
        {{ method.return_type }}
            {{ method.return_description }}
        """
        {{ method.body | indent(8) }}
    {% endfor %}
    {% endif %}
```

**Example Output** (from `Announcement.java`):

```python
"""Announcement notification model.

Auto-generated from Java class: org.yawlfoundation.yawl.ui.announce.Announcement
Generated on: 2025-11-28T10:00:00Z
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class NotificationVariant(str, Enum):
    """Notification type variants."""
    SUCCESS = "success"
    PRIMARY = "primary"
    ERROR = "error"


class NotificationPosition(str, Enum):
    """Notification position on screen."""
    TOP_START = "top-start"
    TOP_CENTER = "top-center"
    TOP_END = "top-end"
    MIDDLE = "middle"
    BOTTOM_START = "bottom-start"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_END = "bottom-end"


class Announcement(BaseModel):
    """Notification announcement model.

    Attributes
    ----------
    message : str
        The notification message
    variant : NotificationVariant
        The notification type (success, primary, error)
    duration_ms : int
        Display duration in milliseconds
    position : NotificationPosition
        Position on screen

    Examples
    --------
    >>> announcement = Announcement(
    ...     message="Operation successful",
    ...     variant=NotificationVariant.SUCCESS
    ... )
    >>> announcement.message
    'Operation successful'
    """

    message: str = Field(
        description="The notification message",
        min_length=1,
        max_length=500,
    )
    variant: NotificationVariant = Field(
        default=NotificationVariant.SUCCESS,
        description="The notification type",
    )
    duration_ms: int = Field(
        default=5000,
        description="Display duration in milliseconds",
        ge=1000,
        le=30000,
    )
    position: NotificationPosition = Field(
        default=NotificationPosition.TOP_END,
        description="Position on screen",
    )

    def strip_xml_tags(self) -> Announcement:
        """Strip XML tags from message.

        Returns
        -------
        Announcement
            New announcement with stripped message
        """
        import re
        stripped = re.sub(r"</*\w+>", "", self.message)
        return self.model_copy(update={"message": stripped})
```

### 2. FastAPI Router Template

**File**: `templates/python/api/router.py.j2`

**Usage**: Generate API route handlers from Java view/controller classes

**Template**:

```jinja2
"""{{ router.description }}

Auto-generated from Java class: {{ router.java_source }}
Generated on: {{ generation_timestamp }}
"""

from __future__ import annotations

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from pydantic import Field

{% for import_stmt in router.python_imports %}
{{ import_stmt }}
{% endfor %}

router = APIRouter(
    prefix="{{ router.prefix }}",
    tags={{ router.tags }},
)


{% for endpoint in router.endpoints %}
@router.{{ endpoint.method }}(
    "{{ endpoint.path }}",
    response_model={{ endpoint.response_model }},
    status_code=status.HTTP_{{ endpoint.status_code }},
    summary="{{ endpoint.summary }}",
    description="{{ endpoint.description }}",
    {% if endpoint.deprecated %}deprecated=True,
    {% endif %}
)
async def {{ endpoint.name }}(
    {% for param in endpoint.path_params %}
    {{ param.name }}: {{ param.type }} = Path(..., description="{{ param.description }}"),
    {% endfor %}
    {% for param in endpoint.query_params %}
    {{ param.name }}: {{ param.type }} = Query({{ param.default }}, description="{{ param.description }}"),
    {% endfor %}
    {% for param in endpoint.body_params %}
    {{ param.name }}: {{ param.type }} = Body(..., description="{{ param.description }}"),
    {% endfor %}
    {% for param in endpoint.dependencies %}
    {{ param.name }}: {{ param.type }} = Depends({{ param.dependency }}),
    {% endfor %}
) -> {{ endpoint.response_model }}:
    """{{ endpoint.docstring }}

    Parameters
    ----------
    {% for param in endpoint.all_params %}
    {{ param.name }} : {{ param.type }}
        {{ param.description }}
    {% endfor %}

    Returns
    -------
    {{ endpoint.response_model }}
        {{ endpoint.return_description }}

    Raises
    ------
    HTTPException
        {% for error in endpoint.possible_errors %}
        - {{ error.status_code }}: {{ error.description }}
        {% endfor %}

    Examples
    --------
    >>> # {{ endpoint.example.description }}
    >>> response = client.{{ endpoint.method }}("{{ endpoint.example.path }}"{% if endpoint.example.body %}, json={{ endpoint.example.body }}{% endif %})
    >>> response.status_code
    {{ endpoint.example.expected_status }}
    """
    {{ endpoint.body | indent(4) }}
{% endfor %}
```

**Example Output** (from `CasesView.java`):

```python
"""Cases management API endpoints.

Auto-generated from Java class: org.yawlfoundation.yawl.ui.view.CasesView
Generated on: 2025-11-28T10:00:00Z
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status

from kgcl.yawl_ui.models.case import CaseModel, CaseCreateRequest, CaseStatus
from kgcl.yawl_ui.services.case_service import CaseService, get_case_service
from kgcl.yawl_ui.api.dependencies import get_current_user

router = APIRouter(
    prefix="/api/cases",
    tags=["cases"],
)


@router.get(
    "",
    response_model=List[CaseModel],
    status_code=status.HTTP_200_OK,
    summary="List all cases",
    description="Retrieve a list of all workflow cases with optional filtering",
)
async def list_cases(
    specification_id: Optional[str] = Query(None, description="Filter by specification ID"),
    status_filter: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of cases to return"),
    offset: int = Query(0, ge=0, description="Number of cases to skip"),
    case_service: CaseService = Depends(get_case_service),
    current_user: str = Depends(get_current_user),
) -> List[CaseModel]:
    """List all workflow cases with optional filtering.

    Parameters
    ----------
    specification_id : Optional[str]
        Filter by specification ID
    status_filter : Optional[CaseStatus]
        Filter by case status (active, completed, suspended, cancelled)
    limit : int
        Maximum number of cases to return (1-1000)
    offset : int
        Number of cases to skip for pagination
    case_service : CaseService
        Injected case service
    current_user : str
        Authenticated user ID

    Returns
    -------
    List[CaseModel]
        List of cases matching the filters

    Raises
    ------
    HTTPException
        - 401: User not authenticated
        - 403: User does not have permission to view cases

    Examples
    --------
    >>> # Get first 10 active cases
    >>> response = client.get("/api/cases?status_filter=active&limit=10")
    >>> response.status_code
    200
    """
    try:
        cases = await case_service.list_cases(
            specification_id=specification_id,
            status=status_filter,
            limit=limit,
            offset=offset,
            user_id=current_user
        )
        return cases
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {e}"
        )


@router.post(
    "",
    response_model=CaseModel,
    status_code=status.HTTP_201_CREATED,
    summary="Create new case",
    description="Launch a new workflow case from a specification",
)
async def create_case(
    request: CaseCreateRequest,
    case_service: CaseService = Depends(get_case_service),
    current_user: str = Depends(get_current_user),
) -> CaseModel:
    """Launch a new workflow case.

    Parameters
    ----------
    request : CaseCreateRequest
        Case creation request with specification ID and parameters
    case_service : CaseService
        Injected case service
    current_user : str
        Authenticated user ID

    Returns
    -------
    CaseModel
        The newly created case

    Raises
    ------
    HTTPException
        - 400: Invalid case parameters
        - 401: User not authenticated
        - 404: Specification not found

    Examples
    --------
    >>> # Create case from specification
    >>> response = client.post("/api/cases", json={"specification_id": "spec-001"})
    >>> response.status_code
    201
    """
    try:
        case = await case_service.create_case(
            specification_id=request.specification_id,
            case_params=request.case_params,
            user_id=current_user
        )
        return case
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {e}"
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification not found: {e}"
        )
```

### 3. Service Class Template

**File**: `templates/python/services/service_class.py.j2`

**Usage**: Generate business logic service classes from Java service classes

```jinja2
"""{{ service.description }}

Auto-generated from Java class: {{ service.java_source }}
Generated on: {{ generation_timestamp }}
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
{% for import_stmt in service.python_imports %}
{{ import_stmt }}
{% endfor %}


class {{ service.name }}:
    """{{ service.docstring }}

    This service handles {{ service.responsibility }}.

    Attributes
    ----------
    {% for attr in service.attributes %}
    {{ attr.name }} : {{ attr.type }}
        {{ attr.description }}
    {% endfor %}
    """

    def __init__(
        self,
        {% for param in service.constructor_params %}
        {{ param.name }}: {{ param.type }}{% if param.default is not none %} = {{ param.default }}{% endif %},
        {% endfor %}
    ) -> None:
        """Initialize {{ service.name }}.

        Parameters
        ----------
        {% for param in service.constructor_params %}
        {{ param.name }} : {{ param.type }}
            {{ param.description }}
        {% endfor %}
        """
        {% for attr in service.attributes %}
        self.{{ attr.name }} = {{ attr.initialization }}
        {% endfor %}

    {% for method in service.methods %}
    {% if method.is_async %}async {% endif %}def {{ method.name }}(
        self,
        {% for param in method.parameters %}
        {{ param.name }}: {{ param.type }}{% if param.default is not none %} = {{ param.default }}{% endif %},
        {% endfor %}
    ) -> {{ method.return_type }}:
        """{{ method.description }}

        Parameters
        ----------
        {% for param in method.parameters %}
        {{ param.name }} : {{ param.type }}
            {{ param.description }}
        {% endfor %}

        Returns
        -------
        {{ method.return_type }}
            {{ method.return_description }}

        Raises
        ------
        {% for exception in method.raises %}
        {{ exception.type }}
            {{ exception.description }}
        {% endfor %}

        Examples
        --------
        {% for example in method.examples %}
        >>> # {{ example.description }}
        {{ example.code | indent(8) }}
        {% endfor %}
        """
        {{ method.body | indent(8) }}
    {% endfor %}


# Dependency injection helper
_{{ service.name.lower() }}_instance: Optional[{{ service.name }}] = None


def get_{{ service.name.lower() }}() -> {{ service.name }}:
    """Get singleton instance of {{ service.name }}.

    Returns
    -------
    {{ service.name }}
        Singleton service instance
    """
    global _{{ service.name.lower() }}_instance
    if _{{ service.name.lower() }}_instance is None:
        _{{ service.name.lower() }}_instance = {{ service.name }}(
            {% for param in service.constructor_params %}
            {{ param.name }}={{ param.default_value }},
            {% endfor %}
        )
    return _{{ service.name.lower() }}_instance
```

---

## TypeScript Templates

### 4. React Component Template

**File**: `templates/typescript/components/component.tsx.j2`

**Usage**: Generate React components from Java Vaadin components

```jinja2
/**
 * {{ component.description }}
 *
 * Auto-generated from Java class: {{ component.java_source }}
 * Generated on: {{ generation_timestamp }}
 */

import React from 'react';
{% for import_stmt in component.typescript_imports %}
{{ import_stmt }}
{% endfor %}

/**
 * Props for {{ component.name }} component
 */
export interface {{ component.name }}Props {
  {% for prop in component.props %}
  /**
   * {{ prop.description }}
   */
  {{ prop.name }}{{ '?' if prop.optional else '' }}: {{ prop.type }};
  {% endfor %}
}

/**
 * {{ component.docstring }}
 *
 * @example
 * ```tsx
 * {{ component.usage_example }}
 * ```
 */
export const {{ component.name }}: React.FC<{{ component.name }}Props> = ({
  {% for prop in component.props %}
  {{ prop.name }}{{ ' = ' + prop.default if prop.default else '' }},
  {% endfor %}
}) => {
  {% for state in component.state %}
  const [{{ state.name }}, set{{ state.name | capitalize }}] = React.useState<{{ state.type }}>({{ state.default }});
  {% endfor %}

  {% for ref in component.refs %}
  const {{ ref.name }} = React.useRef<{{ ref.type }}>({{ ref.default }});
  {% endfor %}

  {% for effect in component.effects %}
  React.useEffect(() => {
    {{ effect.body | indent(4) }}
  }, [{{ effect.dependencies | join(', ') }}]);
  {% endfor %}

  {% for handler in component.handlers %}
  const {{ handler.name }} = React.useCallback(
    ({% for param in handler.parameters %}{{ param.name }}: {{ param.type }}{{ ', ' if not loop.last else '' }}{% endfor %}) => {
      {{ handler.body | indent(6) }}
    },
    [{{ handler.dependencies | join(', ') }}]
  );
  {% endfor %}

  return (
    {{ component.jsx | indent(4) }}
  );
};
```

**Example Output** (from `Announcement.java`):

```typescript
/**
 * Announcement notification component
 *
 * Auto-generated from Java class: org.yawlfoundation.yawl.ui.announce.Announcement
 * Generated on: 2025-11-28T10:00:00Z
 */

import React from 'react';
import toast from 'react-hot-toast';

/**
 * Notification variant types
 */
export type NotificationVariant = 'success' | 'primary' | 'error';

/**
 * Notification position on screen
 */
export type NotificationPosition =
  | 'top-start'
  | 'top-center'
  | 'top-end'
  | 'middle'
  | 'bottom-start'
  | 'bottom-center'
  | 'bottom-end';

/**
 * Props for Announcement component
 */
export interface AnnouncementProps {
  /**
   * The notification message
   */
  message: string;

  /**
   * The notification type
   */
  variant?: NotificationVariant;

  /**
   * Display duration in milliseconds
   */
  durationMs?: number;

  /**
   * Position on screen
   */
  position?: NotificationPosition;

  /**
   * Callback when notification is closed
   */
  onClose?: () => void;
}

/**
 * Display a notification announcement
 *
 * @example
 * ```tsx
 * <Announcement
 *   message="Operation successful"
 *   variant="success"
 *   durationMs={5000}
 * />
 * ```
 */
export const Announcement: React.FC<AnnouncementProps> = ({
  message,
  variant = 'success',
  durationMs = 5000,
  position = 'top-end',
  onClose,
}) => {
  React.useEffect(() => {
    // Strip XML tags from message
    const strippedMessage = message.replace(/<\/*\w+>/g, '');

    // Show toast based on variant
    const toastOptions = {
      duration: durationMs,
      position,
    };

    switch (variant) {
      case 'success':
        toast.success(strippedMessage, toastOptions);
        break;
      case 'error':
        toast.error(strippedMessage, toastOptions);
        break;
      case 'primary':
      default:
        toast(strippedMessage, toastOptions);
        break;
    }

    // Call onClose when duration expires
    const timer = setTimeout(() => {
      onClose?.();
    }, durationMs);

    return () => clearTimeout(timer);
  }, [message, variant, durationMs, position, onClose]);

  // This component only triggers side effects, no rendering
  return null;
};
```

### 5. React Hook Template

**File**: `templates/typescript/hooks/use_api.ts.j2`

**Usage**: Generate custom React hooks for API calls

```jinja2
/**
 * {{ hook.description }}
 *
 * Auto-generated from Java class: {{ hook.java_source }}
 * Generated on: {{ generation_timestamp }}
 */

import { useState, useEffect, useCallback } from 'react';
{% for import_stmt in hook.typescript_imports %}
{{ import_stmt }}
{% endfor %}

/**
 * {{ hook.docstring }}
 *
 * @example
 * ```tsx
 * {{ hook.usage_example }}
 * ```
 */
export function {{ hook.name }}<TData = any, TError = Error>(
  {% for param in hook.parameters %}
  {{ param.name }}{{ '?' if param.optional else '' }}: {{ param.type }},
  {% endfor %}
): {{ hook.return_type }} {
  const [data, setData] = useState<TData | null>(null);
  const [error, setError] = useState<TError | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  {% for helper in hook.helpers %}
  const {{ helper.name }} = useCallback(
    ({% for param in helper.parameters %}{{ param.name }}: {{ param.type }}{{ ', ' if not loop.last else '' }}{% endfor %}) => {
      {{ helper.body | indent(6) }}
    },
    [{{ helper.dependencies | join(', ') }}]
  );
  {% endfor %}

  useEffect(() => {
    {{ hook.effect_body | indent(4) }}
  }, [{{ hook.dependencies | join(', ') }}]);

  return {
    data,
    error,
    loading,
    {% for method in hook.returned_methods %}
    {{ method.name }},
    {% endfor %}
  };
}
```

---

## Test Templates

### 6. Python Test Template

**File**: `templates/python/tests/test_api.py.j2`

**Usage**: Generate pytest test suites from API endpoints

```jinja2
"""Test {{ test.module_name }}.

Auto-generated from Java class: {{ test.java_source }}
Generated on: {{ generation_timestamp }}
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
{% for import_stmt in test.python_imports %}
{{ import_stmt }}
{% endfor %}


@pytest.fixture
def client() -> TestClient:
    """Create test client.

    Returns
    -------
    TestClient
        FastAPI test client
    """
    from {{ test.app_module }} import app
    return TestClient(app)


{% for test_case in test.test_cases %}
def {{ test_case.name }}(client: TestClient{% for fixture in test_case.fixtures %}, {{ fixture.name }}: {{ fixture.type }}{% endfor %}) -> None:
    """{{ test_case.description }}

    Parameters
    ----------
    client : TestClient
        FastAPI test client
    {% for fixture in test_case.fixtures %}
    {{ fixture.name }} : {{ fixture.type }}
        {{ fixture.description }}
    {% endfor %}
    """
    # Arrange
    {{ test_case.arrange | indent(4) }}

    # Act
    {{ test_case.act | indent(4) }}

    # Assert
    {{ test_case.assert_section | indent(4) }}
{% endfor %}
```

**Example Output**:

```python
"""Test cases API endpoints.

Auto-generated from Java class: org.yawlfoundation.yawl.ui.view.CasesView
Generated on: 2025-11-28T10:00:00Z
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from kgcl.yawl_ui.models.case import CaseModel, CaseStatus


@pytest.fixture
def client() -> TestClient:
    """Create test client.

    Returns
    -------
    TestClient
        FastAPI test client
    """
    from kgcl.yawl_ui.api.main import app
    return TestClient(app)


def test_list_cases_returns_list(client: TestClient) -> None:
    """Test GET /api/cases returns list of cases.

    Parameters
    ----------
    client : TestClient
        FastAPI test client
    """
    # Arrange
    # (No setup needed - endpoint returns current cases)

    # Act
    response = client.get("/api/cases")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Validate each item is a valid CaseModel
    for item in response.json():
        CaseModel.model_validate(item)


def test_list_cases_filters_by_status(client: TestClient) -> None:
    """Test GET /api/cases filters by status parameter.

    Parameters
    ----------
    client : TestClient
        FastAPI test client
    """
    # Arrange
    status_filter = CaseStatus.ACTIVE

    # Act
    response = client.get(f"/api/cases?status_filter={status_filter.value}")

    # Assert
    assert response.status_code == 200
    cases = [CaseModel.model_validate(item) for item in response.json()]
    # All returned cases should match the filter
    assert all(case.status == status_filter for case in cases)


def test_create_case_returns_created(client: TestClient) -> None:
    """Test POST /api/cases creates new case.

    Parameters
    ----------
    client : TestClient
        FastAPI test client
    """
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
    assert created.status == CaseStatus.ACTIVE
```

### 7. TypeScript Test Template

**File**: `templates/typescript/tests/component.test.tsx.j2`

**Usage**: Generate Vitest component tests

```jinja2
/**
 * Test {{ test.component_name }}
 *
 * Auto-generated from Java class: {{ test.java_source }}
 * Generated on: {{ generation_timestamp }}
 */

import { describe, it, expect, vi{% if test.has_before_each %}, beforeEach{% endif %} } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
{% for import_stmt in test.typescript_imports %}
{{ import_stmt }}
{% endfor %}

describe('{{ test.component_name }}', () => {
  {% if test.has_before_each %}
  beforeEach(() => {
    {{ test.before_each | indent(4) }}
  });
  {% endif %}

  {% for test_case in test.test_cases %}
  it('{{ test_case.description }}', async () => {
    // Arrange
    {{ test_case.arrange | indent(4) }}

    // Act
    {{ test_case.act | indent(4) }}

    // Assert
    {{ test_case.assert_section | indent(4) }}
  });
  {% endfor %}
});
```

---

## Template Metadata Schema

**File**: `templates/metadata_schema.json`

This defines the structure of metadata passed to templates:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Template Metadata Schema",
  "type": "object",
  "properties": {
    "model": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "java_source": {"type": "string"},
        "docstring": {"type": "string"},
        "python_imports": {"type": "array", "items": {"type": "string"}},
        "fields": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "type": {"type": "string"},
              "description": {"type": "string"},
              "default": {},
              "example_value": {}
            }
          }
        },
        "validators": {"type": "array"},
        "custom_methods": {"type": "array"}
      }
    }
  }
}
```

---

## Template Testing Strategy

**All templates MUST be tested before use:**

```python
# tests/templates/test_templates.py

def test_pydantic_model_template_renders() -> None:
    """Test Pydantic model template renders correctly."""
    # Arrange
    metadata = {
        "model": {
            "name": "TestModel",
            "description": "Test model",
            "java_source": "com.example.Test",
            "fields": [
                {
                    "name": "id",
                    "type": "str",
                    "description": "Unique ID"
                }
            ]
        }
    }

    # Act
    output = render_template("python/models/pydantic_model.py.j2", metadata)

    # Assert
    assert "class TestModel(BaseModel):" in output
    assert "id: str" in output
    assert output.count("def ") == 0  # No validators in simple case
```

---

## Summary

This catalog defines **13 core templates**:

**Python** (7 templates):
1. Pydantic model
2. Enum model
3. FastAPI router
4. Service class
5. Client class
6. Utility module
7. Pytest test

**TypeScript** (6 templates):
8. React component
9. Modal component
10. React hook
11. TypeScript interface
12. API client
13. Vitest test

**Success Criteria**:
- ✅ All templates generate syntactically valid code
- ✅ All templates pass quality gates (format, lint, type-check)
- ✅ Generated code achieves 80%+ test coverage
- ✅ Templates are reusable across all 122 Java files
- ✅ Templates follow KGCL standards (NumPy docstrings, 100% types)

**Next Steps**:
1. Implement template rendering engine
2. Test each template with sample metadata
3. Validate generated code passes quality gates
4. Integrate into orchestrator pipeline
