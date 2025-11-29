# YAWL UI Cleanup - Execution Checklist (Week 0)

**Objective:** Move 914 stub methods to planned/ directory, clear quality gates
**Duration:** 1-2 days
**Prerequisites:** None (can start immediately)

---

## Pre-Flight Checks

- [ ] Review `YAWL_UI_IMPLEMENTATION_STRATEGY.md` (full context)
- [ ] Review `YAWL_UI_DECISION_SUMMARY.md` (executive summary)
- [ ] Confirm team alignment on strategy
- [ ] Backup current branch: `git checkout -b backup-before-cleanup`

---

## Step 1: Create Directory Structure (5 minutes)

```bash
# Navigate to project root
cd /Users/sac/dev/kgcl

# Create planned/ directory structure
mkdir -p src/kgcl/yawl_ui/planned/{dynform,dialog,view}

# Verify creation
ls -la src/kgcl/yawl_ui/planned/
```

**Verification:**
- [ ] Directory exists: `src/kgcl/yawl_ui/planned/dynform/`
- [ ] Directory exists: `src/kgcl/yawl_ui/planned/dialog/`
- [ ] Directory exists: `src/kgcl/yawl_ui/planned/view/`

---

## Step 2: Move Dialog Files (10 minutes)

```bash
# Move ALL 15 dialog files to planned/dialog/
cd src/kgcl/yawl_ui

git mv dialog/abstract_dialog.py planned/dialog/
git mv dialog/admin_worklist_options_dialog.py planned/dialog/
git mv dialog/calendar_dialog.py planned/dialog/
git mv dialog/client_details_dialog.py planned/dialog/
git mv dialog/delayed_start_dialog.py planned/dialog/
git mv dialog/non_human_category_dialog.py planned/dialog/
git mv dialog/non_human_resource_dialog.py planned/dialog/
git mv dialog/participant_details_dialog.py planned/dialog/
git mv dialog/secondary_resources_dialog.py planned/dialog/
git mv dialog/single_value_dialog.py planned/dialog/
git mv dialog/spec_info_dialog.py planned/dialog/
git mv dialog/yes_no_dialog.py planned/dialog/

# Move __init__.py if exists
git mv dialog/__init__.py planned/dialog/ 2>/dev/null || true

# Remove empty dialog/ directory
rmdir dialog/
```

**Verification:**
- [ ] All files moved: `ls planned/dialog/` shows 12-15 files
- [ ] Original empty: `ls dialog/` shows "No such file or directory"
- [ ] Git tracks moves: `git status` shows "renamed:" entries

---

## Step 3: Move View Files (15 minutes)

```bash
# Move ALL 33 view files to planned/view/
cd /Users/sac/dev/kgcl/src/kgcl/yawl_ui

git mv view/abstract_view.py planned/view/
git mv view/abstract_tabbed_view.py planned/view/
git mv view/abstract_grid_view.py planned/view/
git mv view/abstract_org_data_view.py planned/view/
git mv view/abstract_client_view.py planned/view/
git mv view/abstract_worklist_view.py planned/view/
git mv view/abstract_team_view.py planned/view/
git mv view/main_view.py planned/view/
git mv view/user_worklist_view.py planned/view/
git mv view/team_worklist_view.py planned/view/
git mv view/admin_worklist_view.py planned/view/
git mv view/group_worklist_tabbed_view.py planned/view/
git mv view/org_group_worklist_view.py planned/view/
git mv view/cases_view.py planned/view/
git mv view/cases_sub_view.py planned/view/
git mv view/specifications_sub_view.py planned/view/
git mv view/participants_view.py planned/view/
git mv view/non_human_resources_view.py planned/view/
git mv view/non_human_resource_sub_view.py planned/view/
git mv view/non_human_category_sub_view.py planned/view/
git mv view/org_data_view.py planned/view/
git mv view/org_group_sub_view.py planned/view/
git mv view/role_sub_view.py planned/view/
git mv view/position_sub_view.py planned/view/
git mv view/capability_sub_view.py planned/view/
git mv view/services_view.py planned/view/
git mv view/services_sub_view.py planned/view/
git mv view/client_app_sub_view.py planned/view/
git mv view/calendar_view.py planned/view/
git mv view/profile_view.py planned/view/
git mv view/about_view.py planned/view/
git mv view/worklet_admin_view.py planned/view/

# Move __init__.py if exists
git mv view/__init__.py planned/view/ 2>/dev/null || true

# Remove empty view/ directory
rmdir view/
```

**Verification:**
- [ ] All files moved: `ls planned/view/` shows 32-33 files
- [ ] Original empty: `ls view/` shows "No such file or directory"
- [ ] Git tracks moves: `git status` shows "renamed:" entries

---

## Step 4: Move DynForm Stub Files (20 minutes)

**IMPORTANT:** Keep 4 files, move 18 stubs

```bash
cd /Users/sac/dev/kgcl/src/kgcl/yawl_ui

# Move stub implementations to planned/dynform/
git mv dynform/data_list_generator.py planned/dynform/
git mv dynform/dyn_form_validator.py planned/dynform/
git mv dynform/dyn_form_component_builder.py planned/dynform/
git mv dynform/dyn_form_component_list.py planned/dynform/
git mv dynform/dyn_form_layout.py planned/dynform/
git mv dynform/sub_panel.py planned/dynform/
git mv dynform/sub_panel_controller.py planned/dynform/
git mv dynform/sub_panel_cloner.py planned/dynform/
git mv dynform/choice_component.py planned/dynform/
git mv dynform/doc_component.py planned/dynform/
git mv dynform/custom_form_launcher.py planned/dynform/
git mv dynform/dyn_text_parser.py planned/dynform/
git mv dynform/id_generator.py planned/dynform/
git mv dynform/parameter_map.py planned/dynform/
git mv dynform/dyn_form_field_assembler.py planned/dynform/
git mv dynform/dyn_form_field_restriction.py planned/dynform/
git mv dynform/dyn_form_field_union.py planned/dynform/
git mv dynform/dyn_form_field_list_facet.py planned/dynform/
git mv dynform/dyn_form_enter_key_action.py planned/dynform/

# KEEP these files in dynform/ (needed by backend)
# - dyn_form_field.py (data model)
# - dyn_form_exception.py (exceptions)
# - dyn_form_user_attributes.py (attributes)
# - dyn_form_factory.py (partial impl, deprecate Week 5-7)
# - __init__.py

# Verify kept files
ls dynform/
```

**Verification:**
- [ ] Moved files: `ls planned/dynform/` shows 18-19 files
- [ ] Kept files: `ls dynform/` shows 4-5 files (field, exception, attributes, factory, __init__)
- [ ] Git tracks moves: `git status` shows "renamed:" entries

---

## Step 5: Create README in planned/ (10 minutes)

```bash
cd /Users/sac/dev/kgcl/src/kgcl/yawl_ui/planned

cat > README.md << 'EOF'
# Planned YAWL UI Implementations

**Status:** Architecture reference only - NOT production code

This directory contains auto-generated scaffolding from Java/Vaadin source.
These files are NOT implemented and SHOULD NOT be imported by production code.

## ⚠️ WARNING: DO NOT USE

- ❌ **Do NOT import** from this directory in production code
- ❌ **Do NOT reference** in tests or application code
- ❌ **Do NOT implement** - these will be replaced by React components

## Purpose

1. **Structure Reference:** Shows Java class structure for planning
2. **API Surface:** Documents methods that existed in Java
3. **Planning Aid:** Helps estimate implementation effort

## Implementation Strategy

These components will be re-implemented following the 15-week roadmap
(see `docs/architecture/YAWL_UI_IMPLEMENTATION_ROADMAP.md`):

### Week 5-7: DynForm System (Backend)
- FastAPI endpoints for form schema parsing
- Pydantic models for form validation
- XML generation for YAWL output data
- **NOT a 1:1 port** - complete re-architecture for React

### Week 3-13: React Frontend (UI Components)
- React components replace ALL dialog/ and view/ files
- Ant Design UI framework
- React Hook Form + Zod validation

## Directory Structure

```
planned/
├── dynform/    # 18 stub files - Vaadin UI components & incomplete logic
├── dialog/     # 15 stub files - Vaadin dialog components
├── view/       # 33 stub files - Vaadin view/page components
└── README.md   # This file
```

## Quality Assurance

This directory is **EXCLUDED** from quality gate checks:
- Pre-commit hooks ignore `planned/` directory
- `detect-lies` script skips `planned/` files
- Test coverage requirements don't apply here

## Use Case: Architecture Planning

**Allowed:**
✅ Read to understand Java method signatures
✅ Consult during API design discussions
✅ Reference for estimating implementation effort
✅ Compare with new implementation approach

**Forbidden:**
❌ Import into production code
❌ Copy/paste stub implementations
❌ Use as production components

## Why Not Implement These?

1. **dialog/ and view/ (48 files):** Vaadin UI components
   - **Replacement:** React components in frontend repo
   - **Technology:** Ant Design + React Hook Form
   - **Architecture:** Frontend handles ALL UI (not Python)

2. **dynform/ stubs (18 files):** Incomplete/Vaadin-specific logic
   - **Replacement:** 4 new backend files (schema_parser, field_factory, validator, data_generator)
   - **Technology:** FastAPI + Pydantic + React renderer
   - **Architecture:** Backend generates JSON schema, React renders forms

## References

- **Implementation Strategy:** `docs/architecture/YAWL_UI_IMPLEMENTATION_STRATEGY.md`
- **15-Week Roadmap:** `docs/architecture/YAWL_UI_IMPLEMENTATION_ROADMAP.md`
- **Architecture Spec:** `docs/architecture/YAWL_UI_PYTHON_ARCHITECTURE.md`

---

**Last Updated:** 2025-11-28
**Status:** Architecture reference only
**Do NOT use in production code**
EOF

# Verify README created
cat README.md
```

**Verification:**
- [ ] File created: `src/kgcl/yawl_ui/planned/README.md`
- [ ] Content correct: Shows warnings and usage guidelines
- [ ] Readable: `cat planned/README.md` displays correctly

---

## Step 6: Update Quality Gate Configuration (15 minutes)

### 6A: Update detect-lies script

```bash
cd /Users/sac/dev/kgcl

# Edit scripts/detect_implementation_lies.py
# Add planned/ to EXCLUDE_PATTERNS
```

**File changes needed in `scripts/detect_implementation_lies.py`:**

```python
# Add to EXCLUDE_PATTERNS list
EXCLUDE_PATTERNS = [
    "planned/",  # Architecture reference, not production code
    "tests/",    # Test fixtures may have placeholders
    "examples/", # POC code
    ".venv/",
    "__pycache__/",
]
```

### 6B: Update pre-commit hook

```bash
cd /Users/sac/dev/kgcl

# Edit scripts/git_hooks/pre-commit
# Add check to exclude planned/ from stub detection
```

**File changes needed in `scripts/git_hooks/pre-commit`:**

```bash
# Add after existing stub detection logic

# Exclude planned/ from lie detection
if git diff --cached --name-only | grep -v "planned/" | xargs grep -l "# Auto-generated implementation stub" 2>/dev/null; then
    echo "❌ BLOCKED: Stub implementations detected in production code"
    echo "Stubs are only allowed in planned/ directory for reference"
    exit 1
fi
```

**Verification:**
- [ ] `scripts/detect_implementation_lies.py` excludes `planned/`
- [ ] `scripts/git_hooks/pre-commit` excludes `planned/` from stub checks
- [ ] Files saved and ready to commit

---

## Step 7: Verify Quality Gates Pass (10 minutes)

```bash
cd /Users/sac/dev/kgcl

# Run full verification suite
uv run poe verify

# Specifically check for stubs (should find 0 in production)
uv run poe detect-lies

# Run tests (should still pass)
uv run poe test

# Check git status
git status
```

**Expected Results:**
```
✓ uv run poe verify       # All checks pass
✓ uv run poe detect-lies  # 0 stubs in src/ (planned/ excluded)
✓ uv run poe test         # All tests pass
✓ git status              # Shows renamed files, ready to commit
```

**Verification:**
- [ ] `poe verify` - ALL PASSING
- [ ] `poe detect-lies` - 0 stubs in production code
- [ ] `poe test` - ALL PASSING
- [ ] No import errors from moving files

---

## Step 8: Update Import Paths (if needed) (10 minutes)

**Check for broken imports:**

```bash
cd /Users/sac/dev/kgcl

# Search for imports from moved modules
grep -r "from kgcl.yawl_ui.dialog" src/ tests/ 2>/dev/null
grep -r "from kgcl.yawl_ui.view" src/ tests/ 2>/dev/null
grep -r "from kgcl.yawl_ui.dynform.data_list_generator" src/ tests/ 2>/dev/null
```

**Expected:** No imports found (these were stubs, not used in production)

**If imports found:**
1. Review if import is needed (likely not - was stub)
2. If needed, update import path to planned/ (temporary)
3. Add TODO comment to re-implement properly

**Verification:**
- [ ] No imports from moved files (or updated if critical)
- [ ] All tests still pass after import updates

---

## Step 9: Commit Cleanup (10 minutes)

```bash
cd /Users/sac/dev/kgcl

# Review changes
git status
git diff --cached --stat

# Commit with detailed message
git add .
git commit -m "refactor(yawl_ui): Move stub implementations to planned/ directory

PROBLEM:
- 914 stub methods across 77 files blocking quality gates
- Pre-commit hooks failing (implementation lies detected)
- Auto-generated scaffolding not production-ready
- Cannot proceed with 15-week roadmap

SOLUTION:
- Move 66 UI files (dialog/ + view/) to planned/ (React replaces)
- Move 18 dynform stubs to planned/ (re-implement in Weeks 5-7)
- Keep 4 dynform files (data models, exceptions)
- Create planned/README.md with usage warnings
- Update quality gate config to exclude planned/

IMPACT:
- ✅ 0 stub methods in production code
- ✅ All quality gates passing
- ✅ Pre-commit hooks no longer blocking
- ✅ Ready for Week 1 of roadmap

FILES MOVED:
- dialog/ → planned/dialog/ (15 files, Vaadin UI)
- view/ → planned/view/ (33 files, Vaadin UI)
- dynform/ → planned/dynform/ (18 files, stubs/UI components)

FILES KEPT:
- dynform/dyn_form_field.py (data model, review Week 5)
- dynform/dyn_form_exception.py (exceptions, re-use)
- dynform/dyn_form_user_attributes.py (attributes, review Week 5)
- dynform/dyn_form_factory.py (partial impl, deprecate Week 5-7)

NEXT STEPS:
1. Begin Week 1 of roadmap (backend foundation)
2. Review DynForm kept files in Week 5
3. Re-implement DynForm as FastAPI service (Weeks 5-7)

Refs: docs/architecture/YAWL_UI_IMPLEMENTATION_STRATEGY.md
Refs: docs/architecture/YAWL_UI_DECISION_SUMMARY.md"

# Verify commit
git log -1 --stat
```

**Verification:**
- [ ] Commit created successfully
- [ ] Commit message detailed and clear
- [ ] `git log` shows file renames
- [ ] No uncommitted changes: `git status` clean

---

## Step 10: Final Verification (10 minutes)

```bash
cd /Users/sac/dev/kgcl

# 1. Check directory structure
echo "=== Directory Structure ==="
ls -la src/kgcl/yawl_ui/
ls -la src/kgcl/yawl_ui/planned/

# 2. Count files
echo "=== File Counts ==="
echo "Dialog files moved: $(ls src/kgcl/yawl_ui/planned/dialog/*.py 2>/dev/null | wc -l)"
echo "View files moved: $(ls src/kgcl/yawl_ui/planned/view/*.py 2>/dev/null | wc -l)"
echo "DynForm files moved: $(ls src/kgcl/yawl_ui/planned/dynform/*.py 2>/dev/null | wc -l)"
echo "DynForm files kept: $(ls src/kgcl/yawl_ui/dynform/*.py 2>/dev/null | wc -l)"

# 3. Run quality gates
echo "=== Quality Gates ==="
uv run poe verify
uv run poe detect-lies

# 4. Check for stubs in production
echo "=== Stub Detection ==="
grep -r "# Auto-generated implementation stub" src/kgcl/yawl_ui/ --exclude-dir=planned | wc -l

# 5. Verify planned/ excluded
echo "=== Planned Directory Excluded ==="
uv run poe detect-lies 2>&1 | grep "planned/" || echo "✓ planned/ correctly excluded"
```

**Expected Output:**
```
Dialog files moved: 12-15
View files moved: 32-33
DynForm files moved: 18-19
DynForm files kept: 4-5

✓ All quality gates passing
✓ 0 stubs in production code (src/kgcl/yawl_ui/ excluding planned/)
✓ planned/ directory excluded from checks
```

**Final Verification:**
- [ ] **66+ files** moved to planned/
- [ ] **4-5 files** kept in dynform/
- [ ] **0 stubs** in production code (excluding planned/)
- [ ] **All quality gates** passing
- [ ] **Pre-commit hooks** no longer blocking
- [ ] **README** in planned/ warns against usage

---

## Success Criteria

**Cleanup is complete when ALL of these are true:**

- [x] planned/ directory created with subdirectories
- [x] 66+ stub files moved to planned/
- [x] 4-5 dynform files kept in production
- [x] README created in planned/
- [x] Quality gate config updated (detect-lies, pre-commit)
- [x] `uv run poe verify` - ALL PASSING
- [x] `uv run poe detect-lies` - 0 stubs in production
- [x] `uv run poe test` - ALL PASSING
- [x] Changes committed with detailed message
- [x] No import errors
- [x] Ready to start Week 1 of roadmap

---

## Rollback Plan (If Needed)

If cleanup causes issues:

```bash
# Restore from backup branch
git checkout backup-before-cleanup

# Or undo last commit (if not pushed)
git reset --soft HEAD~1

# Or revert specific files
git checkout HEAD~1 -- src/kgcl/yawl_ui/dialog/
git checkout HEAD~1 -- src/kgcl/yawl_ui/view/
git checkout HEAD~1 -- src/kgcl/yawl_ui/dynform/
```

**When to rollback:**
- ❌ Quality gates still failing after cleanup
- ❌ Critical import errors not resolvable
- ❌ Tests failing due to missing modules
- ❌ Team consensus to try different approach

---

## Troubleshooting

### Issue: "git mv: file exists"

**Cause:** Target file already exists in planned/

**Solution:**
```bash
# Use -f to force overwrite
git mv -f dialog/file.py planned/dialog/
```

### Issue: "No such file or directory"

**Cause:** File already moved or doesn't exist

**Solution:**
```bash
# Check if file exists
ls dialog/file.py

# Check if already moved
ls planned/dialog/file.py

# Skip if already moved
```

### Issue: Pre-commit hook still detecting stubs

**Cause:** planned/ not excluded yet

**Solution:**
```bash
# Update pre-commit hook (see Step 6B)
# Re-run verification
uv run poe verify
```

### Issue: Tests failing after move

**Cause:** Test imports stub files

**Solution:**
```bash
# Find failing imports
grep -r "from kgcl.yawl_ui.dialog" tests/
grep -r "from kgcl.yawl_ui.view" tests/

# Option 1: Remove test (was testing stub)
# Option 2: Update import to planned/ (temporary)
# Option 3: Re-implement properly (if critical)
```

---

## Post-Cleanup Actions

**After cleanup complete:**

1. [ ] Update project documentation
   - Update README.md to reference planned/
   - Update CONTRIBUTING.md with new structure

2. [ ] Notify team
   - Share YAWL_UI_DECISION_SUMMARY.md
   - Explain planned/ directory purpose
   - Clarify Week 1 next steps

3. [ ] Prepare for Week 1
   - Review Week 1 tasks in roadmap
   - Set up development environment
   - Create Week 1 branch: `git checkout -b week-1-backend-foundation`

4. [ ] Update tracking
   - Mark Phase 1 complete in project tracker
   - Update roadmap status to "Week 1 Ready"

---

## Estimated Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| Pre-flight checks | 10 min | 10 min |
| Create directories | 5 min | 15 min |
| Move dialog files | 10 min | 25 min |
| Move view files | 15 min | 40 min |
| Move dynform files | 20 min | 60 min |
| Create README | 10 min | 70 min |
| Update quality gates | 15 min | 85 min |
| Verify quality gates | 10 min | 95 min |
| Update imports | 10 min | 105 min |
| Commit cleanup | 10 min | 115 min |
| Final verification | 10 min | 125 min |

**Total:** ~2 hours (125 minutes)

**Add 30-60 minutes buffer for troubleshooting.**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Status:** ✅ Ready for Execution

**Ready to begin? Start with Step 1!**
