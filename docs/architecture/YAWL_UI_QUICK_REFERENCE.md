# YAWL UI Python Conversion - Quick Reference

## Overview

**Goal:** Convert 122 Java/Vaadin files (18,243 LOC) to FastAPI + React
**Timeline:** 15 weeks (3-4 months)
**Priority:** DynForm system (26 files) is CRITICAL PATH

---

## Architecture At-a-Glance

```
React Frontend (TypeScript)
        ↓ REST/WebSocket
FastAPI Backend (Python 3.13+)
        ↓ HTTP
YAWL Engine (Java - existing)
```

---

## Technology Decisions

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | FastAPI + Pydantic | Async, type-safe, auto-docs |
| **Frontend** | React 18 + TypeScript | Modern, hooks, type-safe |
| **UI Components** | Ant Design 5 | Comprehensive (like Vaadin) |
| **State (UI)** | Zustand | Lightweight, simple |
| **State (Server)** | React Query | Caching, auto-refresh |
| **Forms** | React Hook Form + Zod | Performant, validation |
| **HTTP** | httpx (backend), Axios (frontend) | Async support |
| **Caching** | Redis | Fast TTL-based cache |

---

## Project Structure (Quick)

```
Backend (src/kgcl/yawl_ui/):
├── api/v1/          # REST endpoints
├── services/        # Business logic
├── clients/         # YAWL adapters
├── models/          # Pydantic DTOs
├── dynform/         # Dynamic forms (CRITICAL)
└── util/            # Helpers

Frontend (frontend/src/):
├── api/             # API clients
├── components/      # Reusable components
├── pages/           # Views
├── store/           # Zustand stores
├── hooks/           # React hooks
└── types/           # TypeScript types
```

---

## Critical Path: DynForm System

**Most complex component - allocate 3 weeks**

**Java (26 files) → Python + React:**

| Java Component | Python Module | React Component |
|----------------|---------------|-----------------|
| DynFormFactory | dynform_service.py | DynFormRenderer.tsx |
| DynFormField | models/dynform.py | DynFormField.tsx |
| DynFormValidator | validator.py | DynFormValidator.tsx |
| DynTextParser | schema_parser.py | - |
| DataListGenerator | data_generator.py | - |
| SubPanel | components/subpanel.py | SubPanelField.tsx |
| DynAttributeFactory | attributes/factory.py | - |

**Key Features:**
- Parse YAWL XML schemas → JSON schema
- Generate form fields dynamically
- Support 10+ field types (text, select, date, subpanel, etc.)
- Client + server-side validation
- Generate YAWL XML output from form data

---

## API Endpoint Quick Reference

```
Authentication:
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  GET  /api/v1/auth/me

Worklist:
  GET  /api/v1/worklist/user/{user_id}
  GET  /api/v1/worklist/team/{group_id}
  POST /api/v1/worklist/item/{id}/start
  POST /api/v1/worklist/item/{id}/complete

DynForm (CRITICAL):
  GET  /api/v1/dynform/schema/{item_id}
  POST /api/v1/dynform/validate
  POST /api/v1/dynform/generate-output

Cases:
  GET  /api/v1/cases
  POST /api/v1/cases/launch
  POST /api/v1/cases/{id}/cancel

Specifications:
  GET  /api/v1/specs
  POST /api/v1/specs/upload
  POST /api/v1/specs/{id}/unload

Resources:
  GET  /api/v1/resources/participants
  POST /api/v1/resources/participants

OrgData:
  GET  /api/v1/orgdata/roles
  GET  /api/v1/orgdata/positions
  GET  /api/v1/orgdata/capabilities

WebSocket:
  WS   /ws/notifications
```

---

## Migration Phases

**Phase 1: Core Infrastructure (Weeks 1-2)**
- FastAPI skeleton
- YAWL clients (Engine, Resource)
- Authentication
- React app scaffold

**Phase 2: Worklist (Weeks 3-4)**
- User/Team/Admin worklist views
- Work item operations

**Phase 3: DynForm (Weeks 5-7) - CRITICAL**
- Schema parser
- Field factory
- Layout engine
- React form renderer
- All field types

**Phase 4: Resources (Weeks 8-9)**
- Participant management
- Org data
- Non-human resources

**Phase 5: Cases & Specs (Weeks 10-11)**
- Case management
- Spec upload/unload

**Phase 6: Advanced (Weeks 12-13)**
- Calendar
- Profile
- Services view

**Phase 7: Testing (Weeks 14-15)**
- Integration tests
- Performance tuning
- Documentation

---

## Key Patterns

### 1. YAWL Client Pattern

```python
class EngineClient(YAWLClientBase):
    async def launch_case(self, spec_id, case_data):
        # Connect with session handle
        xml = await self._ib_client._post("launchCase", data)
        # Parse response
        # Emit event via WebSocket
        return case_id
```

### 2. Service Layer Pattern

```python
class WorklistService:
    def __init__(self, resource_client, cache):
        self.resource_client = resource_client
        self.cache = cache

    async def get_user_worklist(self, user_id):
        # Check cache
        # Call YAWL if cache miss
        # Cache result
        return WorkQueueDTO(...)
```

### 3. React Query Pattern

```typescript
function useUserWorklist(userId: string) {
  return useQuery({
    queryKey: ['worklist', userId],
    queryFn: () => worklistApi.getUserWorklist(userId),
    refetchInterval: 30000, // Auto-refresh
  });
}
```

### 4. DynForm Rendering Pattern

```typescript
<DynFormRenderer
  schema={schema}  // From backend
  onSubmit={async (data) => {
    // Validate
    // Generate XML
    // Complete work item
  }}
/>
```

---

## Vaadin → React Component Mapping

| Vaadin | React (Ant Design) |
|--------|-------------------|
| AppLayout | Layout |
| Tabs / Tab | Menu / Menu.Item |
| Grid | Table |
| FormLayout | Form |
| TextField | Input |
| Select | Select |
| DatePicker | DatePicker |
| Button | Button |
| Dialog | Modal |
| Notification | message/notification |

---

## State Management Strategy

**Zustand (Global UI State):**
- Auth (user, tokens)
- Notifications
- UI settings (theme, sidebar)

**React Query (Server State):**
- Worklists (auto-refresh every 30s)
- Cases
- Resources
- Specifications

**WebSocket (Real-time):**
- Invalidate React Query cache on events
- Show toast notifications

---

## Security Checklist

- [x] JWT authentication (access + refresh tokens)
- [x] YAWL session handle server-side
- [x] Permission checking at API + UI
- [x] Pydantic validation on all inputs
- [x] Zod validation on client
- [x] CORS whitelisting
- [x] No XXE in XML parsing

---

## Performance Targets

**Backend:**
- Redis cache for worklists (30s TTL)
- Async I/O for all YAWL calls
- Connection pooling

**Frontend:**
- React Query caching
- Route-based code splitting
- Virtual scrolling for large lists

---

## Testing Strategy

**Backend:**
- pytest + httpx
- Chicago School TDD
- 80%+ coverage
- Mock YAWL clients

**Frontend:**
- React Testing Library
- Jest
- Component tests
- Integration tests

---

## First Steps (Day 1-3)

**Backend:**
```bash
mkdir -p src/kgcl/yawl_ui/{api/v1,services,clients,models,dynform}
# Create base models
# Implement EngineClient
# Test connection to YAWL
```

**Frontend:**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install antd zustand @tanstack/react-query axios
# Create layout scaffold
# Implement login page
```

**Integration:**
```bash
# Test login → worklist → work item
# Prove end-to-end flow
```

---

## Open Questions

1. **Custom Forms:** Support iframe embedding? (Security risk)
2. **WebSocket Scale:** Redis Pub/Sub for multi-instance?
3. **XML Handling:** XSD → Pydantic models? (Recommended)

---

## Success Criteria

- [x] All 122 Java files converted
- [x] Full worklist functionality (user/team/admin)
- [x] DynForm system working (26 files converted)
- [x] Case management operational
- [x] Resource/org data management
- [x] Real-time WebSocket updates
- [x] 80%+ test coverage
- [x] <200ms API response time (p95)
- [x] Production deployment ready

---

## References

- Full Architecture: `YAWL_UI_PYTHON_ARCHITECTURE.md`
- Diagrams: `yawl_ui_diagrams.md`
- Java Source: `vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/`
