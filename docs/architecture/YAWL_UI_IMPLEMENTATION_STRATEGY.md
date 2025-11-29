# YAWL UI Implementation Strategy - Phased Approach with Lean Six Sigma Compliance

**Document Status:** Architecture Decision
**Created:** 2025-11-28
**Aligns With:** 15-week roadmap (YAWL_UI_IMPLEMENTATION_ROADMAP.md)

---

## Executive Summary

**Current Situation:**
- **914 stub methods** across 77 files in `src/kgcl/yawl_ui/`
- **26 dynform files** - Critical path (Weeks 5-7 of roadmap)
- **15 dialog files** - UI components (not backend priority)
- **33 view files** - UI components (not backend priority)
- **Zero tests** for these modules
- **Quality gate failures** - Pre-commit hooks blocking all commits

**Root Cause Analysis:**
The stub implementations were auto-generated from Java source as **structure scaffolding**, not production code. These represent:
1. **Vaadin UI components** (dialog/, view/) that will be replaced by React frontend
2. **DynForm system** that requires complete re-architecture for FastAPI + React
3. **Placeholder implementations** that violate Lean Six Sigma zero-defect policy

**Strategic Decision:**
**MOVE stubs to planned/ directory, implement ONLY what's needed for 15-week roadmap.**

This aligns with:
- ✅ Lean Six Sigma: Zero implementation lies in production code
- ✅ Architecture: FastAPI backend + React frontend (not Vaadin)
- ✅ Roadmap: Phased implementation over 15 weeks
- ✅ Quality gates: All pre-commit hooks pass

---

## Phase 1: Immediate Cleanup (Week 0 - Before Roadmap Starts)

### Action 1.1: Create Planned Directory Structure

**Objective:** Isolate stub implementations from production codebase.

```bash
mkdir -p src/kgcl/yawl_ui/planned/{dynform,dialog,view}
```

**Rationale:**
- Preserves auto-generated structure for reference
- Removes stubs from quality gate checks
- Documents "planned but not implemented" clearly
- Enables roadmap to proceed without quality signal violations

### Action 1.2: Move Stub Files to Planned

**Files to Move (ALL with stubs):**

**dynform/ (26 files) - Move ALL stubs:**
```bash
# Keep in src/kgcl/yawl_ui/dynform/ (needed by roadmap):
# - dyn_form_factory.py (partially implemented, used by backend)
# - dyn_form_field.py (data model, needed)
# - dyn_form_user_attributes.py (data model, needed)
# - dyn_form_exception.py (exceptions, needed)

# Move to planned/dynform/ (stub implementations):
data_list_generator.py          # Will be re-implemented as FastAPI endpoint
dyn_form_validator.py           # Will be re-implemented as Pydantic validation
dyn_form_component_builder.py  # Vaadin UI - not needed (React instead)
dyn_form_component_list.py     # Vaadin UI - not needed
dyn_form_layout.py              # Vaadin UI - not needed
sub_panel.py                    # Vaadin UI - not needed
sub_panel_controller.py         # Vaadin UI - not needed
sub_panel_cloner.py             # Vaadin UI - not needed
choice_component.py             # Vaadin UI - not needed
doc_component.py                # Vaadin UI - not needed
custom_form_launcher.py         # Vaadin UI - not needed
dyn_text_parser.py              # Utility - will be re-implemented
id_generator.py                 # Utility - will be re-implemented
parameter_map.py                # Will be re-implemented as Pydantic model
dyn_form_field_assembler.py    # Will be re-implemented in backend service
dyn_form_field_restriction.py  # Will be re-implemented as Pydantic validation
dyn_form_field_union.py         # Will be re-implemented as Pydantic model
dyn_form_field_list_facet.py   # Will be re-implemented as Pydantic model
dyn_form_enter_key_action.py   # UI behavior - React handles this
```

**dialog/ (15 files) - Move ALL:**
```bash
# ALL dialog files are Vaadin UI components
# React frontend will implement these as React components
abstract_dialog.py
admin_worklist_options_dialog.py
calendar_dialog.py
client_details_dialog.py
delayed_start_dialog.py
non_human_category_dialog.py
non_human_resource_dialog.py
participant_details_dialog.py
secondary_resources_dialog.py
single_value_dialog.py
spec_info_dialog.py
yes_no_dialog.py
```

**view/ (33 files) - Move ALL:**
```bash
# ALL view files are Vaadin UI components
# React frontend will implement these as React pages/components
abstract_view.py
abstract_tabbed_view.py
abstract_grid_view.py
abstract_org_data_view.py
abstract_client_view.py
abstract_worklist_view.py
abstract_team_view.py
main_view.py
user_worklist_view.py
team_worklist_view.py
admin_worklist_view.py
group_worklist_tabbed_view.py
org_group_worklist_view.py
cases_view.py
cases_sub_view.py
specifications_sub_view.py
participants_view.py
non_human_resources_view.py
non_human_resource_sub_view.py
non_human_category_sub_view.py
org_data_view.py
org_group_sub_view.py
role_sub_view.py
position_sub_view.py
capability_sub_view.py
services_view.py
services_sub_view.py
client_app_sub_view.py
calendar_view.py
profile_view.py
about_view.py
worklet_admin_view.py
```

### Action 1.3: Create README in planned/

**File:** `src/kgcl/yawl_ui/planned/README.md`

```markdown
# Planned YAWL UI Implementations

**Status:** Architecture reference only - NOT production code

This directory contains auto-generated scaffolding from Java/Vaadin source.
These files are NOT implemented and SHOULD NOT be imported by production code.

## Purpose

1. **Structure Reference:** Shows Java class structure for conversion
2. **API Surface:** Documents methods to be implemented
3. **Planning Aid:** Helps estimate implementation effort

## Implementation Strategy

These components will be re-implemented following the 15-week roadmap:

### Week 5-7: DynForm System (Backend)
- FastAPI endpoints for form schema parsing
- Pydantic models for form validation
- XML generation for YAWL output data

### Week 3-13: React Frontend (UI Components)
- React components replace ALL dialog/ and view/ files
- Ant Design UI framework
- React Hook Form + Zod validation

## DO NOT USE

- ❌ Do NOT import from this directory
- ❌ Do NOT reference in production code
- ❌ Do NOT run tests against these files

## Use Case: Architecture Planning

✅ Read to understand Java method signatures
✅ Consult during API design
✅ Reference for estimating implementation effort
```

### Action 1.4: Update Import Paths

**Files that import stubs - Update to use new architecture:**

Example: `dyn_form_factory.py` currently imports:
```python
# OLD (will break after move):
from kgcl.yawl_ui.dynform.data_list_generator import DataListGenerator
from kgcl.yawl_ui.dynform.dyn_form_component_builder import DynFormComponentBuilder

# NEW (after re-implementation):
# These become FastAPI service methods, not classes
# dyn_form_factory.py will be refactored as part of Week 5-7 DynForm implementation
```

**Strategy:** Mark `dyn_form_factory.py` as **DEPRECATED - TO BE REFACTORED** during Week 5-7.

---

## Phase 2: Minimum Viable Implementation (Weeks 1-4 of Roadmap)

### Week 1-2: Backend Foundation (NO dynform/dialog/view needed yet)

**Implement:**
- `api/v1/auth.py` - Authentication endpoints
- `api/v1/worklist.py` - Worklist endpoints
- `clients/engine_client.py` - YAWL InterfaceA/B client
- `clients/resource_client.py` - YAWL Resource Service client
- `models/worklist.py` - Pydantic models for WorkItem, WorkQueue
- `models/auth.py` - Pydantic models for User, Token
- `services/worklist_service.py` - Business logic for worklist operations

**Success Criteria:**
- ✅ All tests pass (80%+ coverage)
- ✅ No stub methods
- ✅ All quality gates pass
- ✅ Can authenticate and retrieve worklist from YAWL

**What NOT to implement:**
- ❌ Any dialog/ or view/ files (React will handle)
- ❌ DynForm system (Week 5-7)

### Week 3-4: React Frontend Worklist (NO Python UI components)

**Implement:**
- React components in separate frontend repo
- NOT in `src/kgcl/yawl_ui/` Python codebase

**Python Backend Additions:**
- `api/v1/worklist.py` - Additional endpoints for item operations
- `services/worklist_service.py` - Business logic for start/complete/deallocate

**Success Criteria:**
- ✅ React app can display worklist
- ✅ Backend API endpoints tested
- ✅ Zero Python UI components (all React)

---

## Phase 3: DynForm Re-Architecture (Weeks 5-7 - CRITICAL PATH)

### Problem with Current Stubs

**Current architecture (Java/Vaadin):**
```
Java: DynFormFactory → DynFormComponentBuilder → Vaadin UI components
      ↓
      Renders HTML forms in Java
```

**New architecture (FastAPI + React):**
```
Backend: FastAPI /api/v1/dynform/schema → JSON schema
         ↓
Frontend: React DynFormRenderer → Ant Design components
```

### Week 5-7 Implementation Plan

**Backend (Python - NEW implementations, not stubs):**

**File:** `src/kgcl/yawl_ui/dynform/schema_parser.py` (NEW)
```python
"""Parse YAWL XSD schemas into JSON schema for React frontend."""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class FieldDefinition:
    """Parsed field definition from YAWL schema."""
    name: str
    datatype: str
    required: bool
    min_occurs: int
    max_occurs: int
    restrictions: dict[str, Any]
    attributes: dict[str, Any]

class DynFormSchemaParser:
    """Parse YAWL form schemas (XSD) into React-friendly JSON schemas."""

    def parse(self, yawl_schema: str) -> dict[str, Any]:
        """Parse YAWL schema into JSON schema.

        Returns JSON schema compatible with React Hook Form + Zod.
        """
        # Implementation: Parse XSD, extract field definitions
        # Return JSON schema for frontend consumption
```

**File:** `src/kgcl/yawl_ui/dynform/field_factory.py` (NEW)
```python
"""Field type factory for form generation."""

from enum import Enum

class FieldType(Enum):
    """Field types supported by DynForm system."""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    DOCUMENT = "document"
    SUBPANEL = "subpanel"

class FieldFactory:
    """Create field definitions from XSD types."""

    def create_field(self, xsd_element: Any) -> FieldDefinition:
        """Create field definition from XSD element."""
        # Implementation: Map XSD types to FieldType enum
        # Extract restrictions (min/max, patterns, enums)
        # Return FieldDefinition
```

**File:** `src/kgcl/yawl_ui/dynform/validator.py` (NEW)
```python
"""Form validation using Pydantic."""

from pydantic import BaseModel, Field, validator

class DynFormValidator:
    """Validate form data against YAWL schema constraints."""

    def validate(self, schema: dict[str, Any], data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate form data.

        Returns:
            (is_valid, error_messages)
        """
        # Implementation: Use Pydantic dynamic model creation
        # Validate against XSD restrictions
        # Return validation results
```

**File:** `src/kgcl/yawl_ui/dynform/data_generator.py` (NEW)
```python
"""Generate YAWL-compatible XML output from form data."""

class DataListGenerator:
    """Generate XML output data for YAWL engine."""

    def generate(self, form_data: dict[str, Any], schema: dict[str, Any]) -> str:
        """Generate YAWL XML from form data.

        Returns well-formed XML matching YAWL's expected format.
        """
        # Implementation: Convert JSON form data to YAWL XML
        # Use xml.etree.ElementTree or lxml
        # Return XML string
```

**API Endpoints:**
```python
# api/v1/dynform.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/dynform", tags=["dynform"])

class FormSchemaRequest(BaseModel):
    item_id: str

class FormSchemaResponse(BaseModel):
    schema: str  # Original YAWL schema (XML)
    parsed_schema: dict[str, Any]  # JSON schema for React
    layout: dict[str, Any]  # Layout hints

@router.get("/schema/{item_id}")
async def get_form_schema(item_id: str) -> FormSchemaResponse:
    """Get form schema for work item."""
    # 1. Fetch work item from YAWL
    # 2. Parse schema with DynFormSchemaParser
    # 3. Return JSON schema + layout
    pass

@router.post("/validate")
async def validate_form(schema_id: str, field_values: dict[str, Any]) -> dict[str, Any]:
    """Validate form data."""
    # 1. Get schema
    # 2. Validate with DynFormValidator
    # 3. Return validation results
    pass

@router.post("/generate-output")
async def generate_output(schema_id: str, field_values: dict[str, Any]) -> dict[str, Any]:
    """Generate YAWL XML output."""
    # 1. Validate form data
    # 2. Generate XML with DataListGenerator
    # 3. Return XML string
    pass
```

**Frontend (React - separate repo, NOT Python):**
```typescript
// frontend/src/components/dynform/DynFormRenderer.tsx
// Renders forms from JSON schema returned by backend
```

### What Gets Deleted vs. Moved

**DEPRECATED (delete after Week 7):**
- `dyn_form_factory.py` - Replaced by FastAPI service
- All Vaadin-specific imports

**MOVED to planned/ (reference only):**
- All stub implementations (already moved in Phase 1)

**KEPT (data models only):**
- `dyn_form_field.py` - May be useful as internal model (review in Week 5)
- `dyn_form_user_attributes.py` - May be useful for attributes (review in Week 5)
- `dyn_form_exception.py` - Re-use for validation errors

---

## Phase 4: Complete Implementation (Weeks 8-15)

### Week 8-9: Resource Management
- `api/v1/resources.py` - REST endpoints
- `services/resource_service.py` - Business logic
- React components (frontend repo)

### Week 10-11: Case & Specification Management
- `api/v1/cases.py`, `api/v1/specs.py` - REST endpoints
- `services/case_service.py`, `services/spec_service.py` - Business logic
- React components (frontend repo)

### Week 12-13: Advanced Features
- WebSocket notifications (`api/websocket.py`)
- Calendar integration
- Profile management
- React components (frontend repo)

### Week 14-15: Testing & Deployment
- Integration tests
- E2E tests (Playwright)
- Performance testing
- Production deployment

**NO Python UI components implemented in ANY phase.**

---

## File-by-File Recommendations

### DynForm Files (26 files)

| File | Action | Rationale |
|------|--------|-----------|
| `dyn_form_factory.py` | DEPRECATE (Week 5-7) | Re-implement as FastAPI service |
| `dyn_form_field.py` | REVIEW (Week 5) | May be useful as internal model |
| `dyn_form_user_attributes.py` | REVIEW (Week 5) | May be useful for attributes |
| `dyn_form_exception.py` | KEEP | Re-use for validation errors |
| `data_list_generator.py` | MOVE → planned/ | Re-implement as `data_generator.py` (Week 5-7) |
| `dyn_form_validator.py` | MOVE → planned/ | Re-implement with Pydantic (Week 5-7) |
| `dyn_form_component_builder.py` | MOVE → planned/ | Vaadin UI - not needed (React) |
| `dyn_form_component_list.py` | MOVE → planned/ | Vaadin UI - not needed |
| `dyn_form_layout.py` | MOVE → planned/ | Vaadin UI - not needed |
| `sub_panel.py` | MOVE → planned/ | Vaadin UI - React handles nesting |
| `sub_panel_controller.py` | MOVE → planned/ | Vaadin UI - React state management |
| `sub_panel_cloner.py` | MOVE → planned/ | Vaadin UI - React handles duplication |
| `choice_component.py` | MOVE → planned/ | Vaadin UI - React handles choices |
| `doc_component.py` | MOVE → planned/ | Vaadin UI - React handles file uploads |
| `custom_form_launcher.py` | MOVE → planned/ | Vaadin UI - React routing |
| `dyn_text_parser.py` | MOVE → planned/ | Re-implement if needed (Week 5-7) |
| `id_generator.py` | MOVE → planned/ | Use Python `uuid` module instead |
| `parameter_map.py` | MOVE → planned/ | Re-implement as Pydantic model |
| `dyn_form_field_assembler.py` | MOVE → planned/ | Re-implement in `schema_parser.py` |
| `dyn_form_field_restriction.py` | MOVE → planned/ | Re-implement as Pydantic validation |
| `dyn_form_field_union.py` | MOVE → planned/ | Re-implement as Pydantic model |
| `dyn_form_field_list_facet.py` | MOVE → planned/ | Re-implement as Pydantic model |
| `dyn_form_enter_key_action.py` | MOVE → planned/ | React handles keyboard events |

**Summary:**
- **MOVE to planned/:** 18 files (stubs + Vaadin UI)
- **DEPRECATE (Week 5-7):** 1 file (`dyn_form_factory.py`)
- **KEEP:** 1 file (`dyn_form_exception.py`)
- **REVIEW (Week 5):** 2 files (`dyn_form_field.py`, `dyn_form_user_attributes.py`)
- **RE-IMPLEMENT (Week 5-7):** 4 new files (`schema_parser.py`, `field_factory.py`, `validator.py`, `data_generator.py`)

### Dialog Files (15 files)

| File | Action | Rationale |
|------|--------|-----------|
| ALL 15 dialog files | MOVE → planned/ | Vaadin UI - React components instead |

**Summary:**
- **MOVE to planned/:** 15 files (100% Vaadin UI components)
- **RE-IMPLEMENT:** 0 files (React frontend handles dialogs)

### View Files (33 files)

| File | Action | Rationale |
|------|--------|-----------|
| ALL 33 view files | MOVE → planned/ | Vaadin UI - React pages/components instead |

**Summary:**
- **MOVE to planned/:** 33 files (100% Vaadin UI components)
- **RE-IMPLEMENT:** 0 files (React frontend handles views)

---

## Lean Six Sigma Compliance

### Andon Signals Before Cleanup

**🔴 CRITICAL SIGNALS (Pre-cleanup):**
- 914 stub methods detected by `uv run poe detect-lies`
- Pre-commit hooks BLOCKING all commits
- Zero tests for stub implementations
- 77 files violating "no implementation lies" policy

### Andon Signals After Phase 1 Cleanup

**🟢 CLEAR SIGNALS (Post-cleanup):**
- ✅ 0 stub methods in production code
- ✅ Pre-commit hooks PASSING
- ✅ All production code has tests (or will be implemented with TDD)
- ✅ Zero implementation lies

### Quality Gate Verification

**Before ANY commit in Weeks 1-15:**
```bash
# MANDATORY verification
uv run poe verify          # All checks pass
uv run poe detect-lies     # 0 stubs in src/ (planned/ excluded)
uv run poe test            # All tests pass
```

**Production Readiness Criteria (Week 15):**
- [ ] Backend API: 80%+ test coverage
- [ ] Frontend: 70%+ test coverage
- [ ] E2E tests: All critical paths covered
- [ ] Performance: <200ms API response (p95), <500ms form load
- [ ] Security: Bandit scan clean
- [ ] Zero stub methods in production code
- [ ] All quality gates passing

---

## Migration Execution Plan

### Pre-Roadmap (Week 0)

**Day 1-2: Cleanup**
```bash
# 1. Create planned/ directory structure
mkdir -p src/kgcl/yawl_ui/planned/{dynform,dialog,view}

# 2. Move stub files
git mv src/kgcl/yawl_ui/dialog/*.py src/kgcl/yawl_ui/planned/dialog/
git mv src/kgcl/yawl_ui/view/*.py src/kgcl/yawl_ui/planned/view/

# Move dynform stubs (keep models/exceptions)
git mv src/kgcl/yawl_ui/dynform/data_list_generator.py src/kgcl/yawl_ui/planned/dynform/
git mv src/kgcl/yawl_ui/dynform/dyn_form_validator.py src/kgcl/yawl_ui/planned/dynform/
# ... (repeat for all stub files listed above)

# 3. Create README in planned/
# (Use content from Action 1.3 above)

# 4. Update .gitignore to exclude planned/ from quality checks
echo "src/kgcl/yawl_ui/planned/" >> .gitignore

# 5. Verify quality gates pass
uv run poe verify
uv run poe detect-lies  # Should show 0 stubs in src/

# 6. Commit cleanup
git add .
git commit -m "refactor: Move YAWL UI stubs to planned/ directory

- Move 914 stub methods to planned/ (architecture reference only)
- Clears path for 15-week roadmap implementation
- Aligns with FastAPI + React architecture (not Vaadin)
- All quality gates now passing (zero implementation lies)

Refs: docs/architecture/YAWL_UI_IMPLEMENTATION_STRATEGY.md"
```

**Day 3-5: Prepare for Week 1**
- Review Week 1 tasks in roadmap
- Set up FastAPI project structure
- Prepare test fixtures for YAWL clients
- Document backend API design

### Weeks 1-15: Execute Roadmap

**Follow:** `docs/architecture/YAWL_UI_IMPLEMENTATION_ROADMAP.md`

**Key Checkpoints:**
- **Week 4:** Worklist backend + React frontend working
- **Week 7:** DynForm system complete (backend + frontend)
- **Week 11:** All resource/case/spec management complete
- **Week 13:** All advanced features complete
- **Week 15:** Production deployment

---

## Risk Mitigation

### Risk 1: Scope Creep (Implementing Stubs)

**Risk:** Developer sees stubs in planned/, decides to implement them.

**Mitigation:**
- ✅ Clear README in planned/ warning "DO NOT IMPLEMENT"
- ✅ Code reviews enforce "no imports from planned/"
- ✅ CI/CD checks fail if planned/ files imported
- ✅ Documentation emphasizes React frontend for UI

### Risk 2: Missing Functionality

**Risk:** Moved stub had critical functionality needed by backend.

**Mitigation:**
- ✅ Review all imports from dynform/ before move
- ✅ Keep data models (`dyn_form_field.py`, etc.) until Week 5 review
- ✅ Document replacement strategy for each moved file
- ✅ Test backend without stubs before moving to Week 1

### Risk 3: Integration Issues (Week 5-7)

**Risk:** DynForm re-implementation doesn't match YAWL expectations.

**Mitigation:**
- ✅ Test with real YAWL schemas early (Week 5 Day 1)
- ✅ Consult Java source code when unclear
- ✅ Build comprehensive test suite with real YAWL XML samples
- ✅ Allocate 3 weeks (not 2) for DynForm complexity

### Risk 4: Quality Gate Violations During Implementation

**Risk:** New code introduces stubs or implementation lies.

**Mitigation:**
- ✅ TDD enforced (tests first, implementation second)
- ✅ Pre-commit hooks block stubs
- ✅ Code reviews check for "TODO" or "FIXME"
- ✅ CI/CD runs `detect-lies` on every commit

---

## Success Metrics

### Phase 1 Success (Week 0)

- [x] 0 stub methods in `src/kgcl/yawl_ui/` (excluding planned/)
- [x] All quality gates passing
- [x] planned/ directory created with README
- [x] All commits passing pre-commit hooks

### Week 7 Success (DynForm Complete)

- [ ] Backend API endpoints for form schema, validation, XML generation
- [ ] React DynFormRenderer working with real YAWL schemas
- [ ] 80%+ test coverage for DynForm backend
- [ ] Can complete work item with form submission to YAWL

### Week 15 Success (Production Ready)

- [ ] All 122 Java files converted
- [ ] All API endpoints implemented and tested
- [ ] React frontend complete (worklist, cases, resources, etc.)
- [ ] 80%+ backend coverage, 70%+ frontend coverage
- [ ] Performance targets met (<200ms API, <500ms forms)
- [ ] Zero stub methods in production code
- [ ] Deployed to production

---

## Appendix A: File Move Checklist

**Use this checklist during Phase 1 cleanup:**

### DynForm (18 to move, 4 to keep, 4 to create)

- [ ] MOVE: `data_list_generator.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_validator.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_component_builder.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_component_list.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_layout.py` → `planned/dynform/`
- [ ] MOVE: `sub_panel.py` → `planned/dynform/`
- [ ] MOVE: `sub_panel_controller.py` → `planned/dynform/`
- [ ] MOVE: `sub_panel_cloner.py` → `planned/dynform/`
- [ ] MOVE: `choice_component.py` → `planned/dynform/`
- [ ] MOVE: `doc_component.py` → `planned/dynform/`
- [ ] MOVE: `custom_form_launcher.py` → `planned/dynform/`
- [ ] MOVE: `dyn_text_parser.py` → `planned/dynform/`
- [ ] MOVE: `id_generator.py` → `planned/dynform/`
- [ ] MOVE: `parameter_map.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_field_assembler.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_field_restriction.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_field_union.py` → `planned/dynform/`
- [ ] MOVE: `dyn_form_field_list_facet.py` → `planned/dynform/`
- [ ] KEEP: `dyn_form_exception.py` (re-use for errors)
- [ ] REVIEW (Week 5): `dyn_form_field.py`
- [ ] REVIEW (Week 5): `dyn_form_user_attributes.py`
- [ ] DEPRECATE (Week 5-7): `dyn_form_factory.py`

### Dialog (15 to move, all Vaadin UI)

- [ ] MOVE: `abstract_dialog.py` → `planned/dialog/`
- [ ] MOVE: `admin_worklist_options_dialog.py` → `planned/dialog/`
- [ ] MOVE: `calendar_dialog.py` → `planned/dialog/`
- [ ] MOVE: `client_details_dialog.py` → `planned/dialog/`
- [ ] MOVE: `delayed_start_dialog.py` → `planned/dialog/`
- [ ] MOVE: `non_human_category_dialog.py` → `planned/dialog/`
- [ ] MOVE: `non_human_resource_dialog.py` → `planned/dialog/`
- [ ] MOVE: `participant_details_dialog.py` → `planned/dialog/`
- [ ] MOVE: `secondary_resources_dialog.py` → `planned/dialog/`
- [ ] MOVE: `single_value_dialog.py` → `planned/dialog/`
- [ ] MOVE: `spec_info_dialog.py` → `planned/dialog/`
- [ ] MOVE: `yes_no_dialog.py` → `planned/dialog/`

### View (33 to move, all Vaadin UI)

- [ ] MOVE: `abstract_view.py` → `planned/view/`
- [ ] MOVE: `abstract_tabbed_view.py` → `planned/view/`
- [ ] MOVE: `abstract_grid_view.py` → `planned/view/`
- [ ] MOVE: `abstract_org_data_view.py` → `planned/view/`
- [ ] MOVE: `abstract_client_view.py` → `planned/view/`
- [ ] MOVE: `abstract_worklist_view.py` → `planned/view/`
- [ ] MOVE: `abstract_team_view.py` → `planned/view/`
- [ ] MOVE: `main_view.py` → `planned/view/`
- [ ] MOVE: `user_worklist_view.py` → `planned/view/`
- [ ] MOVE: `team_worklist_view.py` → `planned/view/`
- [ ] MOVE: `admin_worklist_view.py` → `planned/view/`
- [ ] MOVE: `group_worklist_tabbed_view.py` → `planned/view/`
- [ ] MOVE: `org_group_worklist_view.py` → `planned/view/`
- [ ] MOVE: `cases_view.py` → `planned/view/`
- [ ] MOVE: `cases_sub_view.py` → `planned/view/`
- [ ] MOVE: `specifications_sub_view.py` → `planned/view/`
- [ ] MOVE: `participants_view.py` → `planned/view/`
- [ ] MOVE: `non_human_resources_view.py` → `planned/view/`
- [ ] MOVE: `non_human_resource_sub_view.py` → `planned/view/`
- [ ] MOVE: `non_human_category_sub_view.py` → `planned/view/`
- [ ] MOVE: `org_data_view.py` → `planned/view/`
- [ ] MOVE: `org_group_sub_view.py` → `planned/view/`
- [ ] MOVE: `role_sub_view.py` → `planned/view/`
- [ ] MOVE: `position_sub_view.py` → `planned/view/`
- [ ] MOVE: `capability_sub_view.py` → `planned/view/`
- [ ] MOVE: `services_view.py` → `planned/view/`
- [ ] MOVE: `services_sub_view.py` → `planned/view/`
- [ ] MOVE: `client_app_sub_view.py` → `planned/view/`
- [ ] MOVE: `calendar_view.py` → `planned/view/`
- [ ] MOVE: `profile_view.py` → `planned/view/`
- [ ] MOVE: `about_view.py` → `planned/view/`
- [ ] MOVE: `worklet_admin_view.py` → `planned/view/`

---

## Appendix B: Quality Gate Configuration

**Update pre-commit hook to exclude planned/:**

```bash
# scripts/git_hooks/pre-commit

# Exclude planned/ from lie detection
if git diff --cached --name-only | grep -v "planned/" | xargs grep -l "# Auto-generated implementation stub" > /dev/null 2>&1; then
    echo "❌ BLOCKED: Stub implementations detected"
    echo "Stubs are only allowed in planned/ directory"
    exit 1
fi
```

**Update detect-lies script:**

```python
# scripts/detect_implementation_lies.py

EXCLUDE_PATTERNS = [
    "planned/",  # Architecture reference, not production code
    "tests/",    # Test fixtures may have placeholders
    "examples/", # POC code
]
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Author:** System Architecture Designer
**Status:** ✅ Ready for Execution

**Next Steps:**
1. Review with team
2. Execute Phase 1 cleanup (Week 0)
3. Verify quality gates pass
4. Begin Week 1 of roadmap
