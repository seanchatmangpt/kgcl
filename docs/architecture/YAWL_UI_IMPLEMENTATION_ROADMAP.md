# YAWL UI Python Implementation Roadmap

**Project:** Convert YAWL UI from Java/Vaadin to FastAPI + React
**Timeline:** 15 weeks (75 working days)
**Team Size:** 2-3 developers recommended

---

## Week 1: Backend Foundation

### Day 1-2: Project Setup

**Tasks:**
- [ ] Create FastAPI project structure in `src/kgcl/yawl_ui/`
- [ ] Setup `pyproject.toml` dependencies (FastAPI, httpx, Pydantic, Redis)
- [ ] Configure development environment (uvicorn, hot reload)
- [ ] Create base configuration system (`config.py`)
- [ ] Setup pytest structure with fixtures

**Deliverables:**
```python
# src/kgcl/yawl_ui/main.py
from fastapi import FastAPI
app = FastAPI(title="YAWL UI Backend", version="1.0.0")

# src/kgcl/yawl_ui/config.py
class Settings(BaseSettings):
    yawl_engine_host: str
    yawl_engine_port: str
    redis_url: str
    jwt_secret: str
```

**Success Criteria:**
- `uv run uvicorn kgcl.yawl_ui.main:app --reload` starts server
- GET `/docs` shows Swagger UI
- Tests run: `poe test`

---

### Day 3-5: YAWL Client Adapters

**Priority 1: EngineClient**

**Tasks:**
- [ ] Implement `YAWLClientBase` with auth/session handling
- [ ] Implement `EngineClient` for InterfaceA/B
- [ ] Methods: `connect()`, `get_running_cases()`, `launch_case()`, `upload_specification()`
- [ ] XML parsing utilities (`util/xml_parser.py`)
- [ ] Error handling & exceptions (`clients/exceptions.py`)
- [ ] Write tests with mocked YAWL responses

**Code:**
```python
# clients/engine_client.py
class EngineClient(YAWLClientBase):
    async def launch_case(
        self, spec_id: YSpecificationID, case_data: str
    ) -> str:
        """Launch case via InterfaceB."""
        # Implementation from Java EngineClient.launchCase()
```

**Priority 2: ResourceClient**

**Tasks:**
- [ ] Implement `ResourceClient` for Resource Service
- [ ] Methods: `get_participant()`, `get_work_queue()`, `start_workitem()`, `complete_workitem()`
- [ ] Parse WorkItemRecord from XML
- [ ] Write tests

**Success Criteria:**
- Connect to real YAWL instance (if available) or mocked
- Launch case successfully
- Retrieve worklist for participant

---

## Week 2: Authentication & Models

### Day 6-7: Authentication System

**Tasks:**
- [ ] Implement JWT token generation/validation
- [ ] Create auth endpoints (`api/v1/auth.py`)
- [ ] Implement `get_current_user()` dependency
- [ ] Create `AuthService` that wraps YAWL authentication
- [ ] Setup token refresh mechanism
- [ ] Write auth tests

**Code:**
```python
# api/v1/auth.py
@router.post("/login")
async def login(credentials: LoginRequest) -> TokenResponse:
    # Authenticate with YAWL Resource Service
    # Generate JWT tokens
    # Return tokens + user info
```

**Success Criteria:**
- POST `/api/v1/auth/login` returns JWT tokens
- Protected endpoints require valid token
- Token refresh works

---

### Day 8-10: Core Data Models

**Tasks:**
- [ ] Create Pydantic models in `models/`:
  - `common.py` - YSpecificationID, XNode
  - `auth.py` - User, Token, UserPrivileges
  - `worklist.py` - WorkItem, WorkQueue, PiledTask
  - `case.py` - Case, RunningCase
  - `specification.py` - SpecificationInfo, UploadResult
- [ ] Add validation rules (regex patterns, constraints)
- [ ] Write model validation tests
- [ ] Create conversion utilities (XML ↔ Pydantic)

**Success Criteria:**
- All models pass Pydantic validation
- Models serialize to/from JSON correctly
- Can convert YAWL XML to models

---

## Week 3-4: Worklist Implementation

### Day 11-13: Worklist API Endpoints

**Tasks:**
- [ ] Implement `api/v1/worklist.py` with all endpoints
- [ ] Create `WorklistService` in `services/worklist_service.py`
- [ ] Implement Redis caching for worklists
- [ ] Handle work item state transitions (offered → allocated → started)
- [ ] Write API integration tests

**Endpoints:**
```python
GET  /api/v1/worklist/user/{user_id}
GET  /api/v1/worklist/team/{group_id}
GET  /api/v1/worklist/admin
POST /api/v1/worklist/item/{id}/start
POST /api/v1/worklist/item/{id}/deallocate
POST /api/v1/worklist/item/{id}/reallocate
POST /api/v1/worklist/item/{id}/complete
POST /api/v1/worklist/item/{id}/skip
POST /api/v1/worklist/item/{id}/pile
POST /api/v1/worklist/item/{id}/suspend
```

**Success Criteria:**
- Can retrieve worklist for any user
- Work item operations succeed
- Cache invalidation works

---

### Day 14-16: Frontend Worklist Views

**Tasks:**
- [ ] Setup React project with Vite + TypeScript
- [ ] Install dependencies (Ant Design, Zustand, React Query, Axios)
- [ ] Create API client (`src/api/client.ts`, `src/api/worklist.ts`)
- [ ] Implement login page (`pages/LoginPage.tsx`)
- [ ] Create app layout (`components/layout/AppLayout.tsx`)
- [ ] Implement user worklist view (`pages/worklist/UserWorklistPage.tsx`)
- [ ] Create worklist table component (`components/worklist/WorklistTable.tsx`)
- [ ] Setup auth store (`store/authStore.ts`)
- [ ] Implement `useUserWorklist` hook

**Success Criteria:**
- User can login and see JWT token stored
- Worklist displays in table
- Can click "Start" on work item (opens placeholder form)

---

## Week 5-7: Dynamic Form System (CRITICAL PATH)

### Day 17-20: Backend DynForm Parser & Factory

**Tasks:**
- [ ] Create `dynform/schema_parser.py` - Parse YAWL XML schemas
- [ ] Create `dynform/field_factory.py` - Field creation logic
- [ ] Create `dynform/layout_engine.py` - Layout generation
- [ ] Create `dynform/validator.py` - Validation rules
- [ ] Create `dynform/data_generator.py` - XML output generation
- [ ] Implement all field types:
  - Text, TextArea, Select, Radio, Checkbox
  - Date, Time, DateTime
  - Document (file upload)
  - SubPanel (repeating sections)
- [ ] Write comprehensive tests for each field type

**Code:**
```python
# dynform/schema_parser.py
class DynFormSchemaParser:
    def parse(self, schema_xml: str) -> DynFormSchemaDTO:
        """Parse YAWL form schema XML."""
        # Parse <formSchema> element
        # Extract field definitions
        # Build DynFormSchemaDTO
```

**Success Criteria:**
- Can parse real YAWL form schemas
- Field definitions match Java output
- Validation rules correctly extracted

---

### Day 21-23: Backend DynForm API

**Tasks:**
- [ ] Implement `DynFormService` in `services/dynform_service.py`
- [ ] Create API endpoints in `api/v1/dynform.py`
- [ ] Implement user attributes handling
- [ ] Implement subpanel cloning logic
- [ ] Write integration tests with real schemas

**Endpoints:**
```python
GET  /api/v1/dynform/schema/{item_id}
POST /api/v1/dynform/validate
POST /api/v1/dynform/generate-output
GET  /api/v1/dynform/user-attributes/{user_id}
POST /api/v1/dynform/subpanel/clone
```

**Success Criteria:**
- Schema endpoint returns parsed form definition
- Validation works correctly
- Output XML matches YAWL expectations

---

### Day 24-28: Frontend DynForm Renderer

**Tasks:**
- [ ] Create `components/dynform/DynFormRenderer.tsx`
- [ ] Create `components/dynform/DynFormField.tsx`
- [ ] Create `components/dynform/DynFormValidator.tsx`
- [ ] Implement field components in `components/dynform/fields/`:
  - `TextField.tsx`
  - `TextAreaField.tsx`
  - `SelectField.tsx`
  - `RadioField.tsx`
  - `CheckboxField.tsx`
  - `DateField.tsx`
  - `TimeField.tsx`
  - `DateTimeField.tsx`
  - `DocumentField.tsx`
  - `SubPanelField.tsx` (with add/remove rows)
- [ ] Setup React Hook Form integration
- [ ] Setup Zod validation schema builder
- [ ] Implement form submission flow
- [ ] Write component tests

**Code:**
```typescript
// components/dynform/DynFormRenderer.tsx
export const DynFormRenderer: React.FC<{
  schema: DynFormSchemaDTO;
  onSubmit: (data: Record<string, any>) => Promise<void>;
}> = ({ schema, onSubmit }) => {
  // Build Zod schema
  // Setup React Hook Form
  // Render fields
  // Handle submission
};
```

**Success Criteria:**
- Can render forms from backend schema
- All field types display correctly
- Validation works (client + server)
- Subpanels can add/remove rows
- Form submission generates correct XML

---

### Day 29-30: DynForm Integration Testing

**Tasks:**
- [ ] End-to-end test: Start work item → Show form → Complete
- [ ] Test with multiple real YAWL form schemas
- [ ] Test all field types in isolation
- [ ] Test complex nested subpanels
- [ ] Performance testing (large forms)
- [ ] Fix any issues found

**Success Criteria:**
- Complete work item with form data successfully
- YAWL engine accepts generated XML
- No console errors in browser
- Form loads in <500ms

---

## Week 8-9: Resource Management

### Day 31-34: Participant & OrgData Backend

**Tasks:**
- [ ] Create `ResourceClient` methods for all resource operations
- [ ] Implement `ResourceService` in `services/resource_service.py`
- [ ] Implement `OrgDataService` in `services/orgdata_service.py`
- [ ] Create models in `models/resource.py` and `models/orgdata.py`
- [ ] Create API endpoints in `api/v1/resources.py` and `api/v1/orgdata.py`
- [ ] Write tests

**Success Criteria:**
- Can CRUD participants
- Can CRUD org data (roles, positions, capabilities, groups)
- Data syncs with YAWL Resource Service

---

### Day 35-38: Resource Management Frontend

**Tasks:**
- [ ] Create `pages/resources/ParticipantsPage.tsx`
- [ ] Create `pages/orgdata/OrgDataPage.tsx`
- [ ] Create `components/resource/ParticipantList.tsx`
- [ ] Create `components/dialogs/ParticipantDialog.tsx` (CRUD)
- [ ] Create `components/dialogs/OrgDataDialog.tsx` (CRUD)
- [ ] Implement org data views (roles, positions, capabilities, groups)
- [ ] Write component tests

**Success Criteria:**
- Can view all participants
- Can create/edit/delete participants
- Can manage org data entities
- UI updates in real-time

---

## Week 10-11: Case & Specification Management

### Day 39-42: Cases & Specs Backend

**Tasks:**
- [ ] Implement `CaseService` in `services/case_service.py`
- [ ] Implement `SpecService` in `services/spec_service.py`
- [ ] Create models in `models/case.py` and `models/specification.py`
- [ ] Create API endpoints in `api/v1/cases.py` and `api/v1/specifications.py`
- [ ] Implement file upload handling for specs
- [ ] Implement delayed case launching
- [ ] Write tests

**Endpoints:**
```python
# Cases
GET  /api/v1/cases
POST /api/v1/cases/launch
POST /api/v1/cases/{id}/cancel

# Specifications
GET  /api/v1/specs
POST /api/v1/specs/upload
POST /api/v1/specs/{id}/unload
```

**Success Criteria:**
- Can upload YAWL specifications
- Can launch cases with parameters
- Can cancel running cases
- Can schedule delayed case launches

---

### Day 43-46: Cases & Specs Frontend

**Tasks:**
- [ ] Create `pages/cases/CasesPage.tsx`
- [ ] Create `pages/specifications/SpecificationsPage.tsx`
- [ ] Create `components/dialogs/SpecUploadDialog.tsx`
- [ ] Create `components/dialogs/CaseLaunchDialog.tsx` (with DynForm for params)
- [ ] Implement case details view
- [ ] Write component tests

**Success Criteria:**
- Can upload specifications via UI
- Can launch cases with form inputs
- Can view running cases
- Can cancel cases

---

## Week 12-13: Advanced Features

### Day 47-50: WebSocket & Real-time Updates

**Tasks:**
- [ ] Implement WebSocket endpoint in `api/v1/websocket.py`
- [ ] Create `NotificationService` in `services/notification_service.py`
- [ ] Implement event broadcasting (case launched, workitem offered, etc.)
- [ ] Setup Redis Pub/Sub for multi-instance support
- [ ] Create `useWebSocket` hook in frontend
- [ ] Integrate WebSocket events with React Query cache invalidation
- [ ] Implement toast notifications for events
- [ ] Write integration tests

**Success Criteria:**
- WebSocket connects on app load
- Events trigger cache invalidation
- UI updates automatically on events
- Toast notifications appear for user-relevant events

---

### Day 51-54: Calendar, Profile, Services Views

**Tasks:**
- [ ] Create `api/v1/calendar.py` with calendar endpoints
- [ ] Create `pages/calendar/CalendarPage.tsx`
- [ ] Implement delayed case scheduling UI
- [ ] Create `pages/profile/ProfilePage.tsx`
- [ ] Create `pages/services/ServicesPage.tsx` (view installed services)
- [ ] Write tests

**Success Criteria:**
- Calendar view shows upcoming events
- Can schedule delayed case launches
- Profile page shows user info & settings
- Services page lists YAWL custom services

---

### Day 55-58: Polishing & UX Improvements

**Tasks:**
- [ ] Implement loading states for all async operations
- [ ] Add error boundaries in React
- [ ] Improve error messages (user-friendly)
- [ ] Add tooltips and help text
- [ ] Implement keyboard shortcuts
- [ ] Add accessibility features (ARIA labels, keyboard navigation)
- [ ] Optimize bundle size (code splitting)
- [ ] Performance profiling and optimization

**Success Criteria:**
- No blank screens during loading
- Errors display helpful messages
- App is accessible (keyboard navigation, screen readers)
- Bundle size <500KB (main chunk)

---

## Week 14-15: Testing & Deployment

### Day 59-63: Comprehensive Testing

**Tasks:**
- [ ] Write integration tests for all API endpoints
- [ ] Write E2E tests with Playwright/Cypress
- [ ] Test with multiple YAWL specifications
- [ ] Load testing (simulate 100+ concurrent users)
- [ ] Security testing (OWASP Top 10)
- [ ] Browser compatibility testing
- [ ] Fix all bugs found

**Test Scenarios:**
- User login → Worklist → Start item → Fill form → Complete
- Admin upload spec → Launch case → Monitor → Cancel
- Multiple users working on same cases (concurrency)
- Network failures (offline, reconnect)
- Invalid form inputs (XSS, SQL injection attempts)

**Success Criteria:**
- 80%+ backend test coverage
- 70%+ frontend test coverage
- All E2E scenarios pass
- No critical security vulnerabilities

---

### Day 64-67: Documentation

**Tasks:**
- [ ] Write API documentation (beyond auto-generated Swagger)
- [ ] Write deployment guide (Docker, Nginx, Redis setup)
- [ ] Write developer guide (how to add new features)
- [ ] Write user guide (screenshots, workflows)
- [ ] Create architecture diagrams (update as needed)
- [ ] Document configuration options
- [ ] Create troubleshooting guide

**Deliverables:**
- `docs/api/README.md` - API usage guide
- `docs/deployment/README.md` - Deployment guide
- `docs/development/README.md` - Developer guide
- `docs/user/README.md` - User manual

---

### Day 68-71: Deployment Preparation

**Tasks:**
- [ ] Create Dockerfile for FastAPI backend
- [ ] Create Dockerfile for React frontend
- [ ] Create docker-compose.yml (backend + frontend + Redis)
- [ ] Create Nginx configuration (reverse proxy)
- [ ] Setup environment variable management
- [ ] Create deployment scripts
- [ ] Test deployment locally with Docker
- [ ] Create CI/CD pipeline (GitHub Actions / GitLab CI)
- [ ] Setup staging environment

**Success Criteria:**
- `docker-compose up` starts full stack
- Nginx routes requests correctly
- CI/CD pipeline runs tests and builds images
- Staging environment accessible

---

### Day 72-75: Production Deployment & Handoff

**Tasks:**
- [ ] Deploy to production environment
- [ ] Monitor logs and metrics
- [ ] Performance tuning (cache TTLs, connection pools)
- [ ] Setup monitoring (APM, error tracking)
- [ ] Create runbook for operations team
- [ ] Conduct training session for users
- [ ] Handoff to maintenance team

**Success Criteria:**
- Production deployment successful
- No critical errors in logs
- Response times meet SLAs (<200ms p95)
- Users can perform all workflows
- Operations team trained

---

## Risk Mitigation

### High-Risk Items

**1. DynForm Complexity (Weeks 5-7)**
- **Risk:** 26 Java files, complex logic, critical path
- **Mitigation:**
  - Allocate 3 weeks (not 2)
  - Start with simple field types, add complexity incrementally
  - Test with real YAWL schemas early
  - Get user feedback on form rendering

**2. YAWL Integration Issues**
- **Risk:** YAWL engine behavior differs from documentation
- **Mitigation:**
  - Access to running YAWL instance for testing
  - Consult YAWL source code when unclear
  - Build comprehensive mocks for testing

**3. WebSocket Scalability**
- **Risk:** Performance degrades with many concurrent users
- **Mitigation:**
  - Use Redis Pub/Sub from day 1
  - Load test early (Week 14)
  - Have fallback to polling if needed

**4. XML Parsing Edge Cases**
- **Risk:** YAWL XML has undocumented edge cases
- **Mitigation:**
  - Collect diverse real-world YAWL specs for testing
  - Implement comprehensive error handling
  - Log parsing failures for investigation

---

## Success Metrics

**Technical:**
- 80%+ backend test coverage
- 70%+ frontend test coverage
- <200ms API response time (p95)
- <500ms form load time
- <500KB frontend bundle size
- Zero critical security vulnerabilities

**Functional:**
- 100% of Java features ported
- All 122 Java files converted
- All YAWL integration points working
- Real-time updates functioning

**User Experience:**
- <3 clicks to complete work item
- <5 second login to worklist
- Zero blank screens during loading
- Keyboard navigation supported

---

## Contingency Plans

**If Behind Schedule:**
1. **Week 10:** Drop calendar view (low priority)
2. **Week 12:** Drop services view (can use YAWL admin)
3. **Week 14:** Deploy with known minor bugs, fix post-launch

**If Team Member Leaves:**
- All code reviewed and documented
- Each week's work self-contained
- Can onboard replacement with documentation

**If YAWL Engine Unavailable:**
- Develop against mocked YAWL responses
- Use recorded XML responses from real YAWL
- Deploy to test environment when YAWL available

---

## Daily Standup Questions

1. What did I complete yesterday?
2. What will I work on today?
3. Any blockers? (e.g., waiting on YAWL instance, unclear requirements)
4. Is the current week's milestone at risk?

---

## Weekly Review Checklist

**Every Friday:**
- [ ] All planned tasks completed?
- [ ] Tests passing?
- [ ] Code reviewed?
- [ ] Documentation updated?
- [ ] Demo prepared for stakeholders?
- [ ] Next week's tasks prioritized?

---

## Contact & Escalation

**Technical Questions:**
- Review Java source in `vendors/yawlui-v5.2/`
- Consult YAWL documentation: http://www.yawlfoundation.org/

**Blockers:**
- Escalate to project lead
- Consider consulting YAWL community if stuck

---

**END OF ROADMAP**
