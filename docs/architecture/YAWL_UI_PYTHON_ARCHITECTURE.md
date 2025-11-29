# YAWL UI Python Architecture: FastAPI + React Conversion

**Document Status:** Architecture Design
**Target:** Convert 122 Java/Vaadin files (18,243 LOC) to FastAPI + React
**Priority:** High (DynForm system critical)

## Executive Summary

This document specifies the architecture for converting the YAWL UI from a Java/Vaadin monolith to a modern FastAPI (Python 3.13+) backend with React frontend. The conversion maintains full YAWL workflow engine integration while enabling incremental migration through API versioning.

**Key Metrics:**
- **Java Codebase:** 122 files, ~18,243 LOC
- **Packages:** 11 (announce, component, dialog+3, dynform+dynattributes, layout, listener, menu, service, util, view)
- **Critical Subsystem:** DynForm (26 files) - dynamic form generation from YAWL schemas
- **Service Clients:** 4 (Engine, Resource, DocStore, Worklet)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     YAWL UI Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              React Frontend (TypeScript)                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  Components:                                              │  │
│  │  • Worklist Views (User, Team, Admin, Calendar)          │  │
│  │  • Dynamic Form Renderer (DynForm → React)               │  │
│  │  • Organization Data Management                          │  │
│  │  • Specification & Case Management                       │  │
│  │  • Resource Management (Participants, Non-Human)         │  │
│  │  • Services & Client App Views                           │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  State Management: Zustand + React Query                 │  │
│  │  UI Framework: Ant Design / Material-UI                  │  │
│  │  Form Engine: React Hook Form + Zod validation          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            │ REST/WebSocket                      │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           FastAPI Backend (Python 3.13+)                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  API Layer (REST + WebSocket):                           │  │
│  │  • /api/v1/worklist/* - Worklist operations              │  │
│  │  • /api/v1/dynform/* - Dynamic form schemas              │  │
│  │  • /api/v1/cases/* - Case management                     │  │
│  │  • /api/v1/resources/* - Resource management             │  │
│  │  • /api/v1/orgdata/* - Organization data                 │  │
│  │  • /api/v1/specs/* - Specification management            │  │
│  │  • /ws/notifications - Real-time updates                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  Service Layer:                                           │  │
│  │  • WorklistService, DynFormService, CaseService          │  │
│  │  • ResourceService, OrgDataService, SpecService          │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  YAWL Client Adapters (Python):                          │  │
│  │  • EngineClient - InterfaceA/B HTTP wrapper              │  │
│  │  • ResourceClient - Resource service integration         │  │
│  │  • DocStoreClient - Document store integration           │  │
│  │  • WorkletClient - Worklet service integration           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            │ HTTP/REST                            │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              YAWL Engine (Java - existing)                │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  • InterfaceA - Admin & spec management                  │  │
│  │  • InterfaceB - Case & workitem operations               │  │
│  │  • Resource Service - Participant & resource management  │  │
│  │  • Document Store - Document management                  │  │
│  │  • Worklet Service - Dynamic process adaptation          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture: FastAPI

### Project Structure

```
src/kgcl/yawl_ui/
├── api/                          # API endpoints (REST + WebSocket)
│   ├── v1/                       # API version 1
│   │   ├── __init__.py
│   │   ├── worklist.py           # Worklist endpoints
│   │   ├── dynform.py            # Dynamic form endpoints
│   │   ├── cases.py              # Case management endpoints
│   │   ├── resources.py          # Resource management endpoints
│   │   ├── orgdata.py            # Organization data endpoints
│   │   ├── specifications.py     # Specification endpoints
│   │   ├── calendar.py           # Calendar endpoints
│   │   ├── auth.py               # Authentication endpoints
│   │   └── websocket.py          # WebSocket connections
│   └── dependencies.py           # Shared dependencies (auth, etc.)
│
├── services/                     # Business logic layer
│   ├── __init__.py
│   ├── worklist_service.py       # Worklist business logic
│   ├── dynform_service.py        # Dynamic form generation
│   ├── case_service.py           # Case management logic
│   ├── resource_service.py       # Resource management
│   ├── orgdata_service.py        # Organization data logic
│   ├── spec_service.py           # Specification management
│   └── notification_service.py   # Real-time notifications
│
├── clients/                      # YAWL engine clients (Python adapters)
│   ├── __init__.py
│   ├── base.py                   # Base client with auth & error handling
│   ├── engine_client.py          # EngineClient (InterfaceA/B)
│   ├── resource_client.py        # ResourceClient
│   ├── docstore_client.py        # DocStoreClient
│   ├── worklet_client.py         # WorkletClient
│   └── exceptions.py             # Client-specific exceptions
│
├── models/                       # Pydantic models (DTOs)
│   ├── __init__.py
│   ├── worklist.py               # WorkItem, WorkQueue models
│   ├── dynform.py                # DynForm field/schema models
│   ├── case.py                   # Case, CaseData models
│   ├── resource.py               # Participant, Resource models
│   ├── orgdata.py                # OrgGroup, Role, Position, Capability
│   ├── specification.py          # YSpecificationID, UploadResult
│   ├── auth.py                   # User, Token models
│   └── common.py                 # Shared models (XNode, etc.)
│
├── dynform/                      # Dynamic form system (CRITICAL)
│   ├── __init__.py
│   ├── schema_parser.py          # Parse YAWL form schemas
│   ├── field_factory.py          # Field type creation
│   ├── validator.py              # Form validation rules
│   ├── layout_engine.py          # Form layout generation
│   ├── data_generator.py         # Output data generation
│   ├── attributes/               # Dynamic attributes
│   │   ├── __init__.py
│   │   ├── base.py               # AbstractDynAttribute
│   │   ├── factory.py            # DynAttributeFactory
│   │   └── types.py              # Specific attribute types
│   └── components/               # Form component types
│       ├── __init__.py
│       ├── base.py               # Base field component
│       ├── text_field.py         # Text input components
│       ├── select_field.py       # Select/choice components
│       ├── date_field.py         # Date/time components
│       ├── document_field.py     # Document upload components
│       └── subpanel.py           # Nested/repeating panels
│
├── util/                         # Utilities
│   ├── __init__.py
│   ├── xml_parser.py             # XNode parser (from Java)
│   ├── settings.py               # Application settings
│   ├── cache.py                  # Caching utilities
│   └── privilege_checker.py      # User privilege validation
│
├── config.py                     # Application configuration
├── main.py                       # FastAPI application entry point
└── __init__.py
```

### API Endpoint Specification

#### 1. Authentication & Session Management

```python
POST   /api/v1/auth/login
    Request: {"username": str, "password": str}
    Response: {"access_token": str, "refresh_token": str, "user": UserDTO}

POST   /api/v1/auth/refresh
    Request: {"refresh_token": str}
    Response: {"access_token": str}

POST   /api/v1/auth/logout
    Request: {"refresh_token": str}
    Response: {"success": bool}

GET    /api/v1/auth/me
    Response: UserDTO (current authenticated user)
```

#### 2. Worklist Management

```python
GET    /api/v1/worklist/user/{user_id}
    Query Params: queue_type={offered|allocated|started|suspended}
    Response: {"items": List[WorkItemDTO], "count": int}

GET    /api/v1/worklist/team/{org_group_id}
    Response: {"items": List[WorkItemDTO], "count": int}

GET    /api/v1/worklist/admin
    Query Params: status={all|active|suspended}
    Response: {"items": List[WorkItemDTO], "count": int, "piled": List[PiledTaskDTO]}

POST   /api/v1/worklist/item/{item_id}/start
    Response: {"work_item": WorkItemDTO, "form_schema": str | None}

POST   /api/v1/worklist/item/{item_id}/deallocate
    Response: {"success": bool}

POST   /api/v1/worklist/item/{item_id}/reallocate
    Request: {"participant_id": str}
    Response: {"success": bool}

POST   /api/v1/worklist/item/{item_id}/skip
    Response: {"success": bool}

POST   /api/v1/worklist/item/{item_id}/pile
    Response: {"success": bool}

POST   /api/v1/worklist/item/{item_id}/suspend
    Response: {"success": bool}

POST   /api/v1/worklist/item/{item_id}/unsuspend
    Response: {"success": bool}
```

#### 3. Dynamic Form System (CRITICAL)

```python
GET    /api/v1/dynform/schema/{item_id}
    Response: {
        "schema": str,                    # Original YAWL schema (XML)
        "parsed_schema": DynFormSchemaDTO,  # Parsed form definition
        "layout": DynFormLayoutDTO         # Layout configuration
    }

POST   /api/v1/dynform/validate
    Request: {
        "schema_id": str,
        "field_values": Dict[str, Any]
    }
    Response: {
        "valid": bool,
        "errors": List[ValidationErrorDTO]
    }

POST   /api/v1/dynform/generate-output
    Request: {
        "schema_id": str,
        "field_values": Dict[str, Any]
    }
    Response: {
        "output_xml": str,  # YAWL-compatible output data
        "success": bool
    }

GET    /api/v1/dynform/user-attributes/{user_id}
    Response: {
        "attributes": Dict[str, Any]  # User-defined form attributes
    }

# Subpanel operations (for repeating sections)
POST   /api/v1/dynform/subpanel/clone
    Request: {"panel_id": str, "instance_data": Dict[str, Any]}
    Response: {"new_panel_id": str, "panel_data": Dict[str, Any]}
```

#### 4. Case Management

```python
GET    /api/v1/cases
    Query Params: status={running|completed|suspended|cancelled}
    Response: {"cases": List[CaseDTO], "count": int}

GET    /api/v1/cases/{case_id}
    Response: CaseDTO

POST   /api/v1/cases/launch
    Request: {
        "spec_id": YSpecificationIDDTO,
        "case_data": Dict[str, Any],
        "delay_ms": int | None
    }
    Response: {"case_id": str}

POST   /api/v1/cases/{case_id}/cancel
    Response: {"success": bool}

GET    /api/v1/cases/{case_id}/workitems
    Response: {"items": List[WorkItemDTO]}
```

#### 5. Specification Management

```python
GET    /api/v1/specs
    Response: {"specifications": List[SpecificationDTO]}

POST   /api/v1/specs/upload
    Request: multipart/form-data (file: .yawl specification)
    Response: {
        "spec_id": YSpecificationIDDTO,
        "upload_result": UploadResultDTO
    }

POST   /api/v1/specs/{spec_id}/unload
    Response: {"success": bool}

GET    /api/v1/specs/{spec_id}/info
    Response: SpecificationInfoDTO

GET    /api/v1/specs/{spec_id}/case-params
    Response: {"parameters": List[YParameterDTO]}
```

#### 6. Resource Management

```python
GET    /api/v1/resources/participants
    Response: {"participants": List[ParticipantDTO]}

GET    /api/v1/resources/participants/{participant_id}
    Response: ParticipantDTO

POST   /api/v1/resources/participants
    Request: ParticipantCreateDTO
    Response: ParticipantDTO

PUT    /api/v1/resources/participants/{participant_id}
    Request: ParticipantUpdateDTO
    Response: ParticipantDTO

DELETE /api/v1/resources/participants/{participant_id}
    Response: {"success": bool}

# Non-human resources
GET    /api/v1/resources/nonhuman
    Response: {"resources": List[NonHumanResourceDTO]}

GET    /api/v1/resources/categories
    Response: {"categories": List[NonHumanCategoryDTO]}
```

#### 7. Organization Data

```python
GET    /api/v1/orgdata/roles
    Response: {"roles": List[RoleDTO]}

GET    /api/v1/orgdata/positions
    Response: {"positions": List[PositionDTO]}

GET    /api/v1/orgdata/capabilities
    Response: {"capabilities": List[CapabilityDTO]}

GET    /api/v1/orgdata/orggroups
    Response: {"groups": List[OrgGroupDTO]}

# CRUD operations for each entity type
POST   /api/v1/orgdata/{entity_type}
PUT    /api/v1/orgdata/{entity_type}/{id}
DELETE /api/v1/orgdata/{entity_type}/{id}
```

#### 8. Calendar & Scheduling

```python
GET    /api/v1/calendar/{user_id}/events
    Query Params: start_date, end_date
    Response: {"events": List[CalendarEventDTO]}

POST   /api/v1/calendar/delayed-start
    Request: {
        "spec_id": YSpecificationIDDTO,
        "case_data": Dict[str, Any],
        "start_time": datetime
    }
    Response: {"scheduled_case_id": str}
```

#### 9. WebSocket Notifications (Real-time Updates)

```python
WS     /ws/notifications?token={jwt_token}
    Messages:
    - case_launched: {"case_id": str, "spec_id": YSpecificationIDDTO}
    - workitem_offered: {"item_id": str, "participant_id": str}
    - workitem_started: {"item_id": str}
    - workitem_completed: {"item_id": str}
    - case_completed: {"case_id": str}
    - spec_uploaded: {"spec_id": YSpecificationIDDTO}
    - spec_unloaded: {"spec_id": YSpecificationIDDTO}
```

### Pydantic Models (Key DTOs)

```python
# models/worklist.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any

class WorkItemDTO(BaseModel):
    """Work item representation."""
    id: str = Field(..., description="Work item ID")
    case_id: str
    task_id: str
    task_name: str
    spec_id: YSpecificationIDDTO
    status: str = Field(..., pattern="^(offered|allocated|started|suspended)$")
    enabled_time: datetime
    fired_time: datetime | None = None
    started_time: datetime | None = None
    data: Dict[str, Any] = Field(default_factory=dict)
    resource_status: str | None = None
    allow_dynamic_creation: bool = False
    requires_resourcing_decisions: bool = False

class WorkQueueDTO(BaseModel):
    """Work queue for a participant."""
    participant_id: str
    offered: list[WorkItemDTO] = Field(default_factory=list)
    allocated: list[WorkItemDTO] = Field(default_factory=list)
    started: list[WorkItemDTO] = Field(default_factory=list)
    suspended: list[WorkItemDTO] = Field(default_factory=list)

class PiledTaskDTO(BaseModel):
    """Piled task information."""
    task_id: str
    spec_id: YSpecificationIDDTO
    count: int

# models/dynform.py
class DynFormFieldDTO(BaseModel):
    """Dynamic form field definition."""
    name: str
    label: str
    field_type: str = Field(..., pattern="^(text|textarea|select|date|time|datetime|checkbox|radio|document|subpanel)$")
    required: bool = False
    read_only: bool = False
    default_value: Any | None = None
    restrictions: Dict[str, Any] = Field(default_factory=dict)  # min, max, pattern, etc.
    attributes: Dict[str, Any] = Field(default_factory=dict)    # Dynamic attributes
    choices: list[ChoiceDTO] | None = None  # For select/radio fields
    subfields: list["DynFormFieldDTO"] | None = None  # For subpanel fields

class DynFormSchemaDTO(BaseModel):
    """Parsed dynamic form schema."""
    schema_id: str
    title: str | None = None
    fields: list[DynFormFieldDTO]
    layout: DynFormLayoutDTO
    validation_rules: list[ValidationRuleDTO] = Field(default_factory=list)

class DynFormLayoutDTO(BaseModel):
    """Form layout configuration."""
    width: str = "800px"  # "auto", "600px", "100%"
    height: str = "auto"
    columns: int = 1
    field_spacing: str = "medium"
    custom_styles: Dict[str, str] = Field(default_factory=dict)

# models/case.py
class CaseDTO(BaseModel):
    """Running case representation."""
    case_id: str
    spec_id: YSpecificationIDDTO
    status: str = Field(..., pattern="^(running|completed|suspended|cancelled)$")
    start_time: datetime
    completion_time: datetime | None = None
    data: Dict[str, Any] = Field(default_factory=dict)

# models/specification.py
class YSpecificationIDDTO(BaseModel):
    """YAWL specification identifier."""
    id: str = Field(..., description="Specification URI/identifier")
    version: str = Field(..., pattern=r"^\d+\.\d+$")
    uri: str

class UploadResultDTO(BaseModel):
    """Specification upload result."""
    spec_id: YSpecificationIDDTO
    success: bool
    message: str | None = None

# models/resource.py
class ParticipantDTO(BaseModel):
    """Participant (user) representation."""
    id: str
    userid: str
    firstname: str
    lastname: str
    fullname: str
    email: str | None = None
    description: str | None = None
    notes: str | None = None
    is_administrator: bool = False
    is_available: bool = True
    privileges: UserPrivilegesDTO
    roles: list[str] = Field(default_factory=list)
    positions: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)

class UserPrivilegesDTO(BaseModel):
    """User privilege flags."""
    can_choose_item_to_start: bool = False
    can_start_concurrent_items: bool = False
    can_reorder_items: bool = False
    can_view_team_items: bool = False
    can_view_org_group_items: bool = False
    can_chain_execution: bool = False
    can_manage_cases: bool = False

# models/orgdata.py
class RoleDTO(BaseModel):
    """Organizational role."""
    id: str
    name: str
    description: str | None = None
    belongs_to: str | None = None  # Parent role ID

class PositionDTO(BaseModel):
    """Organizational position."""
    id: str
    title: str
    description: str | None = None
    reports_to: str | None = None  # Manager position ID
    org_group: str | None = None

class CapabilityDTO(BaseModel):
    """Capability/skill."""
    id: str
    name: str
    description: str | None = None

class OrgGroupDTO(BaseModel):
    """Organizational group/team."""
    id: str
    group_name: str
    group_type: str = Field(..., pattern="^(team|department|division)$")
    belongs_to: str | None = None  # Parent group ID
```

### YAWL Client Adapters

```python
# clients/base.py
from abc import ABC
from typing import Any
import httpx
from pydantic import BaseModel

class YAWLClientBase(ABC):
    """Base class for YAWL service clients."""

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._handle: str | None = None
        self._client = httpx.AsyncClient(timeout=timeout)

    async def connect(self, username: str, password: str) -> str:
        """Establish session with YAWL service."""
        # Implement YAWL authentication protocol
        # Returns session handle
        ...

    async def disconnect(self) -> None:
        """Terminate session."""
        ...

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Execute GET request with handle."""
        params = params or {}
        params["sessionHandle"] = self._handle
        response = await self._client.get(f"{self.base_url}/{endpoint}", params=params)
        return self._process_response(response)

    async def _post(self, endpoint: str, data: dict[str, Any] | None = None) -> str:
        """Execute POST request with handle."""
        data = data or {}
        data["sessionHandle"] = self._handle
        response = await self._client.post(f"{self.base_url}/{endpoint}", data=data)
        return self._process_response(response)

    def _process_response(self, response: httpx.Response) -> str:
        """Process YAWL response, checking for success/failure tags."""
        response.raise_for_status()
        content = response.text

        # YAWL wraps responses in <success>...</success> or <failure>...</failure>
        if "<failure>" in content:
            raise YAWLClientException(self._unwrap_xml(content))

        return self._unwrap_xml(content)

    def _unwrap_xml(self, xml: str) -> str:
        """Remove <success> or <failure> wrapper tags."""
        # Implementation from Java StringUtil.unwrap()
        ...

# clients/engine_client.py
class EngineClient(YAWLClientBase):
    """Client for YAWL Engine InterfaceA/B."""

    def __init__(self, host: str, port: str) -> None:
        ia_url = f"http://{host}:{port}/yawl/ia"
        ib_url = f"http://{host}:{port}/yawl/ib"
        self._ia_client = YAWLClientBase(ia_url)
        self._ib_client = YAWLClientBase(ib_url)
        super().__init__(ia_url)

    async def get_running_cases(self) -> list[RunningCase]:
        """Get all running cases (InterfaceB)."""
        xml = await self._ib_client._get("getAllRunningCases")
        return self._parse_running_cases(xml)

    async def launch_case(
        self,
        spec_id: YSpecificationID,
        case_data: str,
        delay_ms: int | None = None
    ) -> str:
        """Launch a new case instance."""
        endpoint = "launchCase"
        data = {
            "specID": spec_id.to_xml(),
            "caseParams": case_data,
        }
        if delay_ms:
            data["delay"] = delay_ms

        case_id = await self._ib_client._post(endpoint, data)
        # Emit event
        await self._announce_event(ClientEvent.Action.LAUNCH_CASE, case_id)
        return case_id

    async def upload_specification(self, spec_xml: str) -> UploadResult:
        """Upload YAWL specification (InterfaceA)."""
        xml = await self._ia_client._post("uploadSpecification", {"content": spec_xml})
        return UploadResult.from_xml(xml)

    async def unload_specification(self, spec_id: YSpecificationID) -> bool:
        """Unload specification from engine."""
        await self._ia_client._post("unloadSpecification", {"specID": spec_id.to_xml()})
        await self._announce_event(ClientEvent.Action.SPEC_UNLOAD, spec_id)
        return True

    async def get_task_information(
        self,
        spec_id: YSpecificationID,
        task_id: str
    ) -> TaskInformation:
        """Get task definition for generating dynamic forms."""
        xml = await self._ib_client._get("getTaskInformation", {
            "specID": spec_id.to_xml(),
            "taskID": task_id
        })
        return TaskInformation.from_xml(xml)

# clients/resource_client.py
class ResourceClient(YAWLClientBase):
    """Client for YAWL Resource Service."""

    async def get_all_participants(self) -> list[Participant]:
        """Retrieve all participants."""
        xml = await self._get("getAllParticipants")
        return [Participant.from_xml(node) for node in XNode.parse_list(xml)]

    async def get_participant(self, participant_id: str) -> Participant:
        """Get single participant by ID."""
        xml = await self._get("getParticipant", {"participantID": participant_id})
        return Participant.from_xml(xml)

    async def get_work_queue(self, participant_id: str) -> WorkQueue:
        """Get work queue for participant."""
        xml = await self._get("getWorkQueue", {"participantID": participant_id})
        return WorkQueue.from_xml(xml)

    async def start_workitem(self, item_id: str, participant_id: str) -> WorkItemRecord:
        """Start (allocate and begin) a work item."""
        xml = await self._post("startWorkItem", {
            "itemID": item_id,
            "participantID": participant_id
        })
        return WorkItemRecord.from_xml(xml)

    async def complete_workitem(self, item_id: str, data: str) -> bool:
        """Complete work item with output data."""
        await self._post("completeWorkItem", {"itemID": item_id, "data": data})
        return True

    # Additional resource service methods...
    # deallocateWorkItem, reallocateWorkItem, skipWorkItem, pileWorkItem,
    # suspendWorkItem, unsuspendWorkItem, createParticipant, updateParticipant, etc.
```

### Service Layer Architecture

```python
# services/worklist_service.py
from typing import Protocol
from dataclasses import dataclass

class WorklistService:
    """Business logic for worklist operations."""

    def __init__(
        self,
        resource_client: ResourceClient,
        engine_client: EngineClient,
        cache: Cache
    ) -> None:
        self.resource_client = resource_client
        self.engine_client = engine_client
        self.cache = cache

    async def get_user_worklist(
        self,
        user_id: str,
        queue_type: str = "all"
    ) -> WorkQueueDTO:
        """Get worklist for specific user."""
        # Check cache first
        cache_key = f"worklist:{user_id}:{queue_type}"
        cached = await self.cache.get(cache_key)
        if cached:
            return WorkQueueDTO(**cached)

        # Fetch from resource service
        work_queue = await self.resource_client.get_work_queue(user_id)

        # Filter by queue type if specified
        result = self._filter_queue(work_queue, queue_type)

        # Cache for 30 seconds
        await self.cache.set(cache_key, result.model_dump(), ttl=30)
        return result

    async def start_workitem(
        self,
        item_id: str,
        participant_id: str
    ) -> tuple[WorkItemDTO, str | None]:
        """Start work item and retrieve form schema if available."""
        # Start the work item
        wir = await self.resource_client.start_workitem(item_id, participant_id)

        # Get task information for dynamic form
        task_info = await self.engine_client.get_task_information(
            YSpecificationID.from_wir(wir),
            wir.task_id
        )

        # Extract form schema (if custom form exists)
        form_schema = task_info.decomposition_attributes.get("formSchema")

        # Invalidate cache
        await self.cache.invalidate(f"worklist:{participant_id}:*")

        return WorkItemDTO.from_wir(wir), form_schema

    # Additional methods: deallocate, reallocate, skip, pile, suspend, etc.

# services/dynform_service.py
class DynFormService:
    """Business logic for dynamic form generation."""

    def __init__(
        self,
        schema_parser: DynFormSchemaParser,
        field_factory: DynFormFieldFactory,
        layout_engine: DynFormLayoutEngine,
        validator: DynFormValidator
    ) -> None:
        self.schema_parser = schema_parser
        self.field_factory = field_factory
        self.layout_engine = layout_engine
        self.validator = validator

    async def get_form_schema(
        self,
        work_item_id: str,
        user_id: str
    ) -> DynFormSchemaDTO:
        """Generate dynamic form schema from work item."""
        # This is the CRITICAL PATH - must replicate Java DynFormFactory logic

        # 1. Parse YAWL schema XML
        raw_schema = await self._get_raw_schema(work_item_id)
        parsed_fields = self.schema_parser.parse(raw_schema)

        # 2. Apply user-defined attributes
        user_attrs = await self._get_user_attributes(user_id)
        enriched_fields = self._apply_user_attributes(parsed_fields, user_attrs)

        # 3. Generate layout
        layout = self.layout_engine.generate_layout(enriched_fields)

        # 4. Build validation rules
        validation_rules = self.validator.build_rules(enriched_fields)

        return DynFormSchemaDTO(
            schema_id=work_item_id,
            fields=enriched_fields,
            layout=layout,
            validation_rules=validation_rules
        )

    async def validate_form_data(
        self,
        schema_id: str,
        field_values: dict[str, Any]
    ) -> tuple[bool, list[ValidationError]]:
        """Validate form data against schema."""
        schema = await self.get_form_schema(schema_id, "system")
        return self.validator.validate(schema, field_values)

    async def generate_output_xml(
        self,
        schema_id: str,
        field_values: dict[str, Any]
    ) -> str:
        """Generate YAWL-compatible output XML from form data."""
        # This replicates DataListGenerator logic
        schema = await self.get_form_schema(schema_id, "system")
        return self._build_output_xml(schema, field_values)

# services/case_service.py
class CaseService:
    """Case management business logic."""

    def __init__(self, engine_client: EngineClient) -> None:
        self.engine_client = engine_client

    async def launch_case(
        self,
        spec_id: YSpecificationID,
        case_data: dict[str, Any],
        delay_ms: int | None = None
    ) -> str:
        """Launch new case instance."""
        # Convert case_data dict to YAWL XML format
        case_xml = self._build_case_data_xml(case_data)

        # Launch through engine client
        case_id = await self.engine_client.launch_case(spec_id, case_xml, delay_ms)

        # Notify via WebSocket
        await notification_service.broadcast({
            "event": "case_launched",
            "case_id": case_id,
            "spec_id": spec_id.model_dump()
        })

        return case_id
```

---

## Frontend Architecture: React + TypeScript

### Project Structure

```
frontend/
├── public/
│   └── icons/
│       └── favicon.png
├── src/
│   ├── api/                      # API client layer
│   │   ├── client.ts             # Axios instance with auth
│   │   ├── worklist.ts           # Worklist API calls
│   │   ├── dynform.ts            # DynForm API calls
│   │   ├── cases.ts              # Case management API
│   │   ├── resources.ts          # Resource API
│   │   ├── orgdata.ts            # OrgData API
│   │   ├── specifications.ts     # Spec API
│   │   └── websocket.ts          # WebSocket client
│   │
│   ├── components/               # Reusable components
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx     # Main app layout (Vaadin AppLayout → Ant Layout)
│   │   │   ├── DrawerMenu.tsx    # Navigation drawer
│   │   │   ├── Header.tsx        # App header
│   │   │   └── Footer.tsx        # App footer
│   │   │
│   │   ├── worklist/
│   │   │   ├── WorklistTable.tsx # Work item table (Vaadin Grid → Ant Table)
│   │   │   ├── WorkItemCard.tsx  # Individual work item card
│   │   │   └── QueueTabs.tsx     # Offered/Allocated/Started tabs
│   │   │
│   │   ├── dynform/              # CRITICAL: Dynamic form renderer
│   │   │   ├── DynFormRenderer.tsx     # Main form renderer
│   │   │   ├── DynFormField.tsx        # Single field component
│   │   │   ├── fields/
│   │   │   │   ├── TextField.tsx       # Text input
│   │   │   │   ├── TextAreaField.tsx   # Textarea
│   │   │   │   ├── SelectField.tsx     # Select/dropdown
│   │   │   │   ├── RadioField.tsx      # Radio buttons
│   │   │   │   ├── CheckboxField.tsx   # Checkbox
│   │   │   │   ├── DateField.tsx       # Date picker
│   │   │   │   ├── TimeField.tsx       # Time picker
│   │   │   │   ├── DateTimeField.tsx   # DateTime picker
│   │   │   │   ├── DocumentField.tsx   # File upload
│   │   │   │   └── SubPanelField.tsx   # Nested/repeating panel
│   │   │   ├── DynFormLayout.tsx       # Form layout wrapper
│   │   │   ├── DynFormValidator.tsx    # Client-side validation
│   │   │   └── useDynForm.ts           # Form state hook
│   │   │
│   │   ├── dialogs/
│   │   │   ├── AbstractDialog.tsx      # Base dialog
│   │   │   ├── ParticipantDialog.tsx   # Participant CRUD
│   │   │   ├── OrgDataDialog.tsx       # OrgData CRUD
│   │   │   ├── SpecUploadDialog.tsx    # Spec upload
│   │   │   └── ConfirmDialog.tsx       # Yes/No confirmation
│   │   │
│   │   ├── resource/
│   │   │   ├── ParticipantList.tsx     # Participant listing
│   │   │   ├── ResourceSelector.tsx    # Resource picker
│   │   │   └── ParticipantDetails.tsx  # Participant info card
│   │   │
│   │   └── common/
│   │       ├── Badge.tsx               # Status badges
│   │       ├── Icon.tsx                # Icon wrapper
│   │       ├── Announcement.tsx        # Toast notifications
│   │       └── LoadingSpinner.tsx      # Loading indicator
│   │
│   ├── pages/                    # Page-level components (views)
│   │   ├── LoginPage.tsx         # Login form
│   │   ├── worklist/
│   │   │   ├── UserWorklistPage.tsx    # User worklist view
│   │   │   ├── TeamWorklistPage.tsx    # Team worklist view
│   │   │   └── AdminWorklistPage.tsx   # Admin worklist view
│   │   ├── cases/
│   │   │   ├── CasesPage.tsx           # Case management
│   │   │   └── CaseDetailsPage.tsx     # Case details
│   │   ├── specifications/
│   │   │   └── SpecificationsPage.tsx  # Spec management
│   │   ├── resources/
│   │   │   ├── ParticipantsPage.tsx    # Participants management
│   │   │   └── NonHumanResourcesPage.tsx
│   │   ├── orgdata/
│   │   │   └── OrgDataPage.tsx         # Org data management
│   │   ├── profile/
│   │   │   └── ProfilePage.tsx         # User profile
│   │   ├── calendar/
│   │   │   └── CalendarPage.tsx        # Calendar view
│   │   └── about/
│   │       └── AboutPage.tsx           # About/version info
│   │
│   ├── store/                    # Zustand state management
│   │   ├── authStore.ts          # Auth state (user, token)
│   │   ├── worklistStore.ts      # Worklist state
│   │   ├── caseStore.ts          # Cases state
│   │   ├── resourceStore.ts      # Resources state
│   │   └── notificationStore.ts  # WebSocket notifications
│   │
│   ├── hooks/                    # Custom React hooks
│   │   ├── useAuth.ts            # Auth hook
│   │   ├── useWorklist.ts        # Worklist data (React Query)
│   │   ├── useCases.ts           # Cases data
│   │   ├── useResources.ts       # Resources data
│   │   ├── useWebSocket.ts       # WebSocket connection
│   │   └── usePermissions.ts     # User permissions check
│   │
│   ├── utils/                    # Utilities
│   │   ├── api.ts                # API helpers
│   │   ├── xml.ts                # XML parsing/generation
│   │   ├── datetime.ts           # Date/time formatting
│   │   └── validation.ts         # Validation helpers
│   │
│   ├── types/                    # TypeScript types
│   │   ├── api.ts                # API response types
│   │   ├── models.ts             # Domain models (mirrors backend DTOs)
│   │   └── common.ts             # Shared types
│   │
│   ├── App.tsx                   # Root component
│   ├── router.tsx                # React Router config
│   └── main.tsx                  # Entry point
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### Component Hierarchy & Vaadin Mapping

```
MainView (AppLayout)
├── Header
│   ├── Logo
│   ├── DrawerToggle (hamburger menu)
│   └── UserMenu (profile, logout)
├── DrawerMenu (Tabs)
│   ├── WorklistMenu
│   │   ├── "My Worklist" → UserWorklistPage
│   │   ├── "My Team's Worklist" → TeamWorklistPage
│   │   └── "Admin Worklist" → AdminWorklistPage (if admin)
│   ├── ProfileMenu
│   │   ├── "My Profile" → ProfilePage
│   │   └── "Calendar" → CalendarPage
│   ├── ManagementMenu (if admin)
│   │   ├── "Case Mgt" → CasesPage
│   │   ├── "Participants" → ParticipantsPage
│   │   ├── "Org Data" → OrgDataPage
│   │   ├── "Non-Human Resources" → NonHumanResourcesPage
│   │   └── "Services / Clients" → ServicesPage
│   └── AboutMenu
│       └── "About" → AboutPage
└── Content (outlet for page components)

Vaadin Component → React Component Mapping:
┌───────────────────────────────────┬─────────────────────────────┐
│ Vaadin (Java)                     │ React (TypeScript)          │
├───────────────────────────────────┼─────────────────────────────┤
│ AppLayout                         │ Layout (Ant Design)         │
│ Tabs / Tab                        │ Menu / Menu.Item (Ant)      │
│ Grid                              │ Table (Ant Design)          │
│ FormLayout                        │ Form (Ant Design)           │
│ TextField                         │ Input                       │
│ TextArea                          │ Input.TextArea              │
│ Select / ComboBox                 │ Select                      │
│ DatePicker                        │ DatePicker                  │
│ TimePicker                        │ TimePicker                  │
│ Button                            │ Button                      │
│ Dialog                            │ Modal                       │
│ Notification                      │ message/notification (Ant)  │
│ VerticalLayout / HorizontalLayout │ Space / Flex (Ant)          │
│ Scroller                          │ <div style={{overflow}}>    │
│ Upload                            │ Upload (Ant Design)         │
│ Label / H5                        │ Typography.Title/Text       │
└───────────────────────────────────┴─────────────────────────────┘
```

### State Management: Zustand + React Query

**Pattern:** Use Zustand for global UI state (auth, notifications), React Query for server state (worklist, cases, resources).

```typescript
// store/authStore.ts
import create from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  userid: string;
  fullname: string;
  isAdministrator: boolean;
  privileges: UserPrivileges;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  isAuthenticated: boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken }),
      clearAuth: () => set({ user: null, accessToken: null, refreshToken: null }),
      isAuthenticated: !!get().accessToken,
    }),
    { name: 'yawl-auth' }
  )
);

// hooks/useWorklist.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { worklistApi } from '../api/worklist';

export function useUserWorklist(userId: string, queueType: string = 'all') {
  return useQuery({
    queryKey: ['worklist', userId, queueType],
    queryFn: () => worklistApi.getUserWorklist(userId, queueType),
    refetchInterval: 30000, // Auto-refresh every 30s
  });
}

export function useStartWorkItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, participantId }: { itemId: string; participantId: string }) =>
      worklistApi.startWorkItem(itemId, participantId),
    onSuccess: (data, variables) => {
      // Invalidate worklist queries to trigger refresh
      queryClient.invalidateQueries({ queryKey: ['worklist', variables.participantId] });
    },
  });
}

// hooks/useWebSocket.ts
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { websocketClient } from '../api/websocket';
import { useNotificationStore } from '../store/notificationStore';

export function useWebSocket() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore(state => state.addNotification);

  useEffect(() => {
    const ws = websocketClient.connect();

    ws.on('workitem_offered', (data) => {
      // Invalidate worklist cache
      queryClient.invalidateQueries({ queryKey: ['worklist', data.participant_id] });
      // Show notification
      addNotification({
        type: 'info',
        message: `New work item offered: ${data.task_name}`,
      });
    });

    ws.on('case_launched', (data) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      addNotification({
        type: 'success',
        message: `Case launched: ${data.case_id}`,
      });
    });

    // More event handlers...

    return () => ws.disconnect();
  }, [queryClient, addNotification]);
}
```

### Dynamic Form Renderer (CRITICAL Component)

```typescript
// components/dynform/DynFormRenderer.tsx
import React, { useState } from 'react';
import { Form, Button, Space } from 'antd';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { DynFormField } from './DynFormField';
import { buildZodSchema } from './DynFormValidator';
import type { DynFormSchemaDTO } from '../../types/models';

interface DynFormRendererProps {
  schema: DynFormSchemaDTO;
  initialValues?: Record<string, any>;
  onSubmit: (data: Record<string, any>) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  showSave?: boolean;
}

export const DynFormRenderer: React.FC<DynFormRendererProps> = ({
  schema,
  initialValues = {},
  onSubmit,
  onCancel,
  submitLabel = 'Complete',
  showSave = false,
}) => {
  const [loading, setLoading] = useState(false);

  // Build Zod validation schema from YAWL schema
  const zodSchema = buildZodSchema(schema);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(zodSchema),
    defaultValues: initialValues,
  });

  const onSubmitForm = async (data: Record<string, any>) => {
    setLoading(true);
    try {
      await onSubmit(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      layout="vertical"
      style={{
        width: schema.layout.width,
        maxHeight: schema.layout.height === 'auto' ? undefined : schema.layout.height,
      }}
    >
      {/* Render fields based on schema */}
      {schema.fields.map((field) => (
        <DynFormField
          key={field.name}
          field={field}
          control={control}
          errors={errors}
        />
      ))}

      {/* Actions */}
      <Space style={{ marginTop: 24 }}>
        <Button type="primary" onClick={handleSubmit(onSubmitForm)} loading={loading}>
          {submitLabel}
        </Button>
        {showSave && (
          <Button onClick={handleSubmit(onSubmitForm)}>Save</Button>
        )}
        {onCancel && (
          <Button onClick={onCancel}>Cancel</Button>
        )}
      </Space>
    </Form>
  );
};

// components/dynform/DynFormField.tsx
import React from 'react';
import { Controller } from 'react-hook-form';
import { TextField } from './fields/TextField';
import { TextAreaField } from './fields/TextAreaField';
import { SelectField } from './fields/SelectField';
import { DateField } from './fields/DateField';
import { SubPanelField } from './fields/SubPanelField';
// ... other field imports

import type { DynFormFieldDTO } from '../../types/models';

interface DynFormFieldProps {
  field: DynFormFieldDTO;
  control: any;
  errors: any;
}

export const DynFormField: React.FC<DynFormFieldProps> = ({ field, control, errors }) => {
  const renderField = () => {
    switch (field.field_type) {
      case 'text':
        return <TextField field={field} control={control} errors={errors} />;
      case 'textarea':
        return <TextAreaField field={field} control={control} errors={errors} />;
      case 'select':
      case 'radio':
        return <SelectField field={field} control={control} errors={errors} />;
      case 'date':
        return <DateField field={field} control={control} errors={errors} />;
      case 'subpanel':
        return <SubPanelField field={field} control={control} errors={errors} />;
      // ... other field types
      default:
        return <div>Unsupported field type: {field.field_type}</div>;
    }
  };

  return (
    <Controller
      name={field.name}
      control={control}
      render={({ field: { onChange, value } }) => (
        <div>
          {renderField()}
          {errors[field.name] && (
            <div style={{ color: 'red' }}>{errors[field.name].message}</div>
          )}
        </div>
      )}
    />
  );
};
```

---

## Integration Design

### Authentication Flow

```
1. User enters credentials in LoginPage
2. Frontend sends POST /api/v1/auth/login
3. Backend:
   a. Connect to YAWL Resource Service
   b. Validate credentials
   c. Generate JWT tokens (access + refresh)
   d. Return tokens + user info
4. Frontend stores tokens in Zustand (persisted to localStorage)
5. All subsequent API calls include Authorization: Bearer <token>
6. WebSocket connection established with token in query param
```

### Real-time Updates via WebSocket

```
Backend (FastAPI WebSocket):
- Maintain ConnectionManager with user_id → WebSocket mapping
- When YAWL events occur (case launched, workitem offered, etc.):
  1. Emit event to relevant connected clients
  2. Clients receive message and update local state

Frontend (React):
- useWebSocket hook establishes connection on app load
- Event handlers invalidate React Query caches
- UI auto-refreshes with fresh data
- Toast notifications inform user of events
```

### Dynamic Form Integration

```
Flow: User clicks "Start" on work item
┌────────────────────────────────────────────────────────────┐
│ 1. Frontend: POST /api/v1/worklist/item/{id}/start        │
│    → Backend starts item via ResourceClient                │
│    → Returns work_item + form_schema (if exists)           │
│                                                             │
│ 2. If form_schema exists:                                  │
│    Frontend: GET /api/v1/dynform/schema/{item_id}          │
│    → Backend:                                               │
│      a. DynFormService.get_form_schema()                   │
│      b. Parse schema XML (DynFormSchemaParser)             │
│      c. Build field definitions (DynFormFieldFactory)      │
│      d. Generate layout (DynFormLayoutEngine)              │
│      e. Create validation rules (DynFormValidator)         │
│    → Returns DynFormSchemaDTO                              │
│                                                             │
│ 3. Frontend renders DynFormRenderer                        │
│    → User fills form                                        │
│    → User clicks "Complete"                                 │
│                                                             │
│ 4. Frontend: POST /api/v1/dynform/validate                 │
│    → Backend validates field values                        │
│    → Returns validation errors (if any)                    │
│                                                             │
│ 5. If valid:                                                │
│    Frontend: POST /api/v1/dynform/generate-output          │
│    → Backend generates YAWL XML from field values          │
│    → Returns output_xml                                    │
│                                                             │
│ 6. Frontend: POST /api/v1/worklist/item/{id}/complete      │
│    → Backend completes work item with output_xml           │
│    → Broadcasts workitem_completed via WebSocket           │
└────────────────────────────────────────────────────────────┘
```

---

## Migration Strategy

### Incremental Conversion Approach

**Phase 1: Core Infrastructure (Weeks 1-2)**
- ✓ FastAPI project setup
- ✓ YAWL client adapters (EngineClient, ResourceClient)
- ✓ Authentication system
- ✓ React app scaffold with routing
- ✓ WebSocket infrastructure

**Phase 2: Worklist Views (Weeks 3-4)**
- ✓ User worklist (UserWorklistView → UserWorklistPage)
- ✓ Team worklist (TeamWorklistView → TeamWorklistPage)
- ✓ Admin worklist (AdminWorklistView → AdminWorklistPage)
- ✓ Basic work item operations (start, deallocate, reallocate)

**Phase 3: Dynamic Form System (Weeks 5-7) - CRITICAL**
- ✓ DynFormService backend
- ✓ Schema parser (XML → DynFormSchemaDTO)
- ✓ Field factory (all field types)
- ✓ Layout engine
- ✓ Validator
- ✓ DynFormRenderer React component
- ✓ All field type components (text, select, date, subpanel, etc.)
- ✓ Form submission → output XML generation

**Phase 4: Resource Management (Weeks 8-9)**
- ✓ Participant management (ParticipantsView → ParticipantsPage)
- ✓ Organization data (OrgDataView → OrgDataPage)
- ✓ Non-human resources (NonHumanResourcesView → NonHumanResourcesPage)

**Phase 5: Case & Specification Management (Weeks 10-11)**
- ✓ Case management (CasesView → CasesPage)
- ✓ Specification upload/unload (SpecificationsSubView)
- ✓ Delayed case launching

**Phase 6: Advanced Features (Weeks 12-13)**
- ✓ Calendar view (CalendarView → CalendarPage)
- ✓ Profile management (ProfileView → ProfilePage)
- ✓ Services/clients view (ServicesView → ServicesPage)
- ✓ Worklet admin (WorkletAdminView)

**Phase 7: Testing & Optimization (Weeks 14-15)**
- ✓ Integration testing
- ✓ Performance optimization
- ✓ UI/UX refinement
- ✓ Documentation

### Coexistence Pattern (During Migration)

**Option A: Proxy-Based (Recommended)**
- Run Java Vaadin UI on :8080
- Run React UI on :3000
- Nginx proxy routes by path:
  - `/` → React (new UI)
  - `/legacy` → Java Vaadin (old UI)
  - `/api/v1` → FastAPI backend
  - `/yawl` → YAWL engine

**Option B: Feature Flag**
- Single backend serves both UIs
- User setting: "Use legacy UI" checkbox
- Gradual migration of users from old → new

---

## Technology Stack

### Backend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Web Framework | FastAPI 0.100+ | Async, auto-docs, Pydantic validation |
| Python Version | 3.13+ | Latest features, performance |
| HTTP Client | httpx | Async HTTP for YAWL clients |
| Validation | Pydantic v2 | Type-safe DTOs, JSON schema |
| WebSocket | FastAPI WebSocket | Built-in, auto-reconnect support |
| Caching | Redis | Fast TTL-based cache for worklists |
| Task Queue | Celery (optional) | Background jobs (delayed cases) |
| Testing | pytest + httpx | Chicago School TDD |

### Frontend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | React 18 + TypeScript | Type safety, hooks, modern |
| Build Tool | Vite | Fast dev server, HMR |
| UI Library | Ant Design 5 | Comprehensive, Vaadin-like |
| State (UI) | Zustand | Lightweight, simple API |
| State (Server) | React Query v4 | Caching, auto-refresh, mutations |
| Forms | React Hook Form + Zod | Performant, validation |
| Routing | React Router v6 | Standard routing |
| HTTP Client | Axios | Interceptors for auth |
| WebSocket | Socket.IO Client | Auto-reconnect, event-based |
| Styling | Tailwind CSS + Ant | Utility-first + components |

---

## Data Flow Diagrams

### Worklist Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Worklist Data Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User navigates to "My Worklist"                            │
│           │                                                  │
│           ▼                                                  │
│  React: useUserWorklist(userId) hook                        │
│           │                                                  │
│           ▼                                                  │
│  React Query checks cache                                   │
│           │                                                  │
│           ├─ Cache HIT → Return cached data                 │
│           │                                                  │
│           └─ Cache MISS:                                     │
│                   │                                          │
│                   ▼                                          │
│           GET /api/v1/worklist/user/{userId}                │
│                   │                                          │
│                   ▼                                          │
│           FastAPI: WorklistService.get_user_worklist()      │
│                   │                                          │
│                   ├─ Check Redis cache                      │
│                   │   │                                      │
│                   │   ├─ HIT → Return from Redis            │
│                   │   │                                      │
│                   │   └─ MISS:                               │
│                   │           │                              │
│                   │           ▼                              │
│                   │   ResourceClient.get_work_queue()       │
│                   │           │                              │
│                   │           ▼                              │
│                   │   HTTP GET → YAWL Resource Service      │
│                   │           │                              │
│                   │           ▼                              │
│                   │   Parse XML response → WorkQueue        │
│                   │           │                              │
│                   │           ▼                              │
│                   │   Store in Redis (TTL 30s)              │
│                   │           │                              │
│                   │           ▼                              │
│                   └───────── Return WorkQueueDTO            │
│                               │                              │
│                               ▼                              │
│                   React Query caches result                 │
│                               │                              │
│                               ▼                              │
│                   React: Render WorklistTable               │
│                                                              │
│  WebSocket event: "workitem_offered"                        │
│           │                                                  │
│           ▼                                                  │
│  React Query invalidates cache → Auto-refetch               │
│           │                                                  │
│           ▼                                                  │
│  UI updates with new work item                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dynamic Form Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Dynamic Form Data Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User clicks "Start" on work item                           │
│           │                                                  │
│           ▼                                                  │
│  POST /api/v1/worklist/item/{id}/start                      │
│           │                                                  │
│           ▼                                                  │
│  Backend: WorklistService.start_workitem()                  │
│           │                                                  │
│           ├─ ResourceClient.start_workitem(id, user_id)     │
│           │       │                                          │
│           │       ▼                                          │
│           │   YAWL Resource Service allocates + starts item │
│           │       │                                          │
│           │       ▼                                          │
│           │   Returns WorkItemRecord (with data)            │
│           │                                                  │
│           ├─ EngineClient.get_task_information(spec, task)  │
│           │       │                                          │
│           │       ▼                                          │
│           │   YAWL Engine returns TaskInformation           │
│           │       │                                          │
│           │       ▼                                          │
│           │   Extract formSchema attribute (if exists)      │
│           │                                                  │
│           ▼                                                  │
│  Return: {work_item, form_schema}                           │
│           │                                                  │
│           ▼                                                  │
│  React: If form_schema exists:                              │
│           │                                                  │
│           ▼                                                  │
│  GET /api/v1/dynform/schema/{item_id}                       │
│           │                                                  │
│           ▼                                                  │
│  Backend: DynFormService.get_form_schema()                  │
│           │                                                  │
│           ├─ DynFormSchemaParser.parse(schema_xml)          │
│           │       │                                          │
│           │       ├─ Parse XML → Extract field definitions  │
│           │       ├─ Identify field types, restrictions     │
│           │       └─ Handle subpanels, choices              │
│           │                                                  │
│           ├─ DynFormFieldFactory.create_fields()            │
│           │       │                                          │
│           │       ├─ For each field:                        │
│           │       │   ├─ Determine component type           │
│           │       │   ├─ Apply restrictions (min/max/etc)   │
│           │       │   └─ Build DynFormFieldDTO              │
│           │       │                                          │
│           │       └─ Apply user attributes                  │
│           │                                                  │
│           ├─ DynFormLayoutEngine.generate_layout()          │
│           │       │                                          │
│           │       └─ Calculate width, columns, spacing      │
│           │                                                  │
│           ├─ DynFormValidator.build_rules()                 │
│           │       │                                          │
│           │       └─ Create validation rules from schema    │
│           │                                                  │
│           ▼                                                  │
│  Return: DynFormSchemaDTO                                   │
│           │                                                  │
│           ▼                                                  │
│  React: Render DynFormRenderer                              │
│           │                                                  │
│           ├─ Build Zod schema from validation rules         │
│           ├─ Render fields using DynFormField components    │
│           └─ Setup React Hook Form with validation          │
│                                                              │
│  User fills form and clicks "Complete"                      │
│           │                                                  │
│           ▼                                                  │
│  Client-side validation (Zod + React Hook Form)             │
│           │                                                  │
│           ├─ FAIL → Show errors, block submit               │
│           │                                                  │
│           └─ PASS:                                           │
│                   │                                          │
│                   ▼                                          │
│           POST /api/v1/dynform/generate-output              │
│                   │                                          │
│                   ▼                                          │
│           Backend: DynFormService.generate_output_xml()     │
│                   │                                          │
│                   ├─ Map field_values to YAWL parameters    │
│                   ├─ Build XML structure                    │
│                   └─ Validate output against schema         │
│                   │                                          │
│                   ▼                                          │
│           Return: {output_xml}                              │
│                   │                                          │
│                   ▼                                          │
│           POST /api/v1/worklist/item/{id}/complete          │
│                   │                                          │
│                   ▼                                          │
│           ResourceClient.complete_workitem(id, output_xml)  │
│                   │                                          │
│                   ▼                                          │
│           YAWL Resource Service completes item              │
│                   │                                          │
│                   ▼                                          │
│           Broadcast WebSocket: "workitem_completed"         │
│                   │                                          │
│                   ▼                                          │
│           React: Close form, refresh worklist               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Authentication & Authorization

1. **JWT-based authentication**
   - Access token (short-lived, 15 min)
   - Refresh token (long-lived, 7 days)
   - Token rotation on refresh

2. **Session management**
   - YAWL session handle stored server-side
   - Mapped to JWT user_id
   - Auto-reconnect on handle expiry

3. **Permission checking**
   - User privileges fetched from YAWL Resource Service
   - Cached with user session
   - Checked at API endpoints and React components

4. **CORS configuration**
   - Whitelist frontend origin
   - Credentials allowed for cookies (if used)

### Input Validation

1. **Backend (FastAPI)**
   - Pydantic models validate all inputs
   - Custom validators for YAWL-specific formats
   - XML parsing with security (no XXE)

2. **Frontend (React)**
   - Zod schema validation
   - React Hook Form client-side validation
   - Sanitize user inputs before display

---

## Performance Considerations

### Backend Optimization

1. **Caching strategy**
   - Redis for worklists (TTL 30s)
   - In-memory cache for org data (TTL 5 min)
   - Cache invalidation on write operations

2. **Async I/O**
   - All YAWL client calls async (httpx)
   - FastAPI async endpoints
   - WebSocket async handlers

3. **Connection pooling**
   - httpx client reuse
   - Database connection pooling (if added)

### Frontend Optimization

1. **React Query caching**
   - Automatic cache management
   - Stale-while-revalidate pattern
   - Background refetch

2. **Code splitting**
   - Route-based splitting
   - Lazy load dialog components
   - Dynamic imports for large dependencies

3. **Virtual scrolling**
   - Ant Table virtualization for large worklists
   - Pagination for case/spec lists

---

## Testing Strategy

### Backend Tests

```python
# tests/api/test_worklist.py
from fastapi.testclient import TestClient
from kgcl.yawl_ui.main import app

def test_get_user_worklist(auth_client: TestClient, mock_resource_client):
    """Test worklist retrieval."""
    mock_resource_client.get_work_queue.return_value = WorkQueue(...)

    response = auth_client.get("/api/v1/worklist/user/user123")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["count"] >= 0

# tests/services/test_dynform_service.py
def test_parse_dynform_schema():
    """Test dynamic form schema parsing."""
    schema_xml = """
    <formSchema>
        <field name="orderID" type="text" required="true" />
        <field name="quantity" type="number" min="1" max="100" />
    </formSchema>
    """

    service = DynFormService(...)
    result = service.schema_parser.parse(schema_xml)

    assert len(result.fields) == 2
    assert result.fields[0].name == "orderID"
    assert result.fields[0].required is True
    assert result.fields[1].restrictions["min"] == 1
```

### Frontend Tests

```typescript
// components/dynform/DynFormRenderer.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DynFormRenderer } from './DynFormRenderer';

describe('DynFormRenderer', () => {
  it('renders fields from schema', () => {
    const schema: DynFormSchemaDTO = {
      schema_id: 'test',
      fields: [
        { name: 'username', label: 'Username', field_type: 'text', required: true },
        { name: 'age', label: 'Age', field_type: 'text', required: false },
      ],
      layout: { width: '600px', height: 'auto', columns: 1, field_spacing: 'medium' },
      validation_rules: [],
    };

    render(<DynFormRenderer schema={schema} onSubmit={jest.fn()} />);

    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Age')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    const onSubmit = jest.fn();
    const schema = { /* schema with required field */ };

    render(<DynFormRenderer schema={schema} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByText('Complete'));

    // Should show validation error
    expect(await screen.findByText(/required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
```

---

## Open Questions & Decisions

### 1. Custom Form Rendering

**Question:** YAWL supports custom HTML forms (CustomFormLauncher). How to handle?

**Options:**
- A) Support only DynForm schema-based forms (simpler)
- B) Allow iframe embedding of custom HTML forms (security risk)
- C) Create custom form builder UI in React (complex)

**Recommendation:** Start with A, add C later if needed.

### 2. WebSocket Scalability

**Question:** How to scale WebSocket connections for many users?

**Options:**
- A) Redis Pub/Sub for multi-instance coordination
- B) Dedicated WebSocket server (Socket.IO with adapter)
- C) Server-Sent Events (SSE) instead of WebSocket

**Recommendation:** A (Redis Pub/Sub) for production.

### 3. XML Handling

**Question:** Should we parse/generate XML in Python or preserve Java approach?

**Options:**
- A) Use Python lxml for XML parsing/generation
- B) Use dictionaries + manual XML building (fragile)
- C) Generate Pydantic models from YAWL XSD schemas

**Recommendation:** C (XSD → Pydantic) for type safety, fall back to A.

---

## Appendix: File Mapping Table

| Java Package/File | Python Module | React Component |
|-------------------|---------------|-----------------|
| `view/MainView.java` | `api/v1/auth.py` | `App.tsx`, `layout/AppLayout.tsx` |
| `view/UserWorklistView.java` | `api/v1/worklist.py` | `pages/worklist/UserWorklistPage.tsx` |
| `view/AdminWorklistView.java` | `api/v1/worklist.py` | `pages/worklist/AdminWorklistPage.tsx` |
| `dynform/DynForm.java` | `dynform/schema_parser.py` | `components/dynform/DynFormRenderer.tsx` |
| `dynform/DynFormFactory.java` | `services/dynform_service.py` | - |
| `dynform/DynFormField.java` | `models/dynform.py` | `components/dynform/DynFormField.tsx` |
| `dynform/SubPanel.java` | `dynform/components/subpanel.py` | `components/dynform/fields/SubPanelField.tsx` |
| `service/EngineClient.java` | `clients/engine_client.py` | - |
| `service/ResourceClient.java` | `clients/resource_client.py` | - |
| `dialog/ParticipantDetailsDialog.java` | `api/v1/resources.py` | `components/dialogs/ParticipantDialog.tsx` |
| `view/CasesSubView.java` | `api/v1/cases.py` | `pages/cases/CasesPage.tsx` |
| `util/TaskPrivilegesCache.java` | `util/privilege_checker.py` | `hooks/usePermissions.ts` |

---

## Next Steps

1. **Backend skeleton:**
   ```bash
   mkdir -p src/kgcl/yawl_ui/{api/v1,services,clients,models,dynform,util}
   uv run poe format
   ```

2. **Create base models:**
   - `models/common.py` (YSpecificationID, XNode)
   - `models/worklist.py` (WorkItem, WorkQueue)
   - `models/auth.py` (User, Token)

3. **Implement EngineClient:**
   - Connect to YAWL InterfaceA/B
   - Test with real YAWL instance

4. **React scaffold:**
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend && npm install antd zustand @tanstack/react-query
   ```

5. **First vertical slice:**
   - Login → UserWorklist → WorkItemTable
   - Prove end-to-end connectivity

---

**End of Architecture Document**
