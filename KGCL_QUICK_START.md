# KGCL Quick Start Guide

**Read This First** for a 5-minute overview of the system.

---

## What is KGCL?

A **Lean-first, RDF-driven** personal productivity system for macOS/iOS that:

1. **Ingests** data from Calendar, Reminders, Mail, Files via PyObjC
2. **Stores** everything as RDF (Turtle/N3) in `.kgc/`
3. **Validates** quality with SHACL invariants (prevents 10 defect types)
4. **Automates** recurring work with knowledge hooks (eliminates 8 waste types)
5. **Generates** CLI, docs, diagrams from RDF (zero manual sync)

**Result:** One source of truth, everything else derived, all manual work automated.

---

## The `.kgc/` Directory (Your Brain)

Everything that matters for KGCL lives here:

```
.kgc/
├── manifest.ttl                    # Who you are in the KGC fabric
├── ontology.ttl                    # What things are (schema.org Event, Action, Message, CreativeWork)
├── types.ttl                       # Shape constraints (SHACL validation rules)
├── invariants.shacl.ttl            # Quality rules (prevent defects)
├── hooks.ttl                       # Automation rules (eliminate waste)
├── apple.ingest.ttl                # Data source specifications (Calendar, Reminders, Mail, Files)
├── projections/
│   └── cli.py.j2                  # Template for generating Typer CLI
└── context.md                      # Complete specification (read this for details)
```

**Key principle:** Never edit anything else. Everything is generated or derived from `.kgc/`.

---

## Standard RDF Ontologies (Not Custom)

KGCL uses **standard vocabularies** to stay Lean and interoperable:

| Concept | Standard Ontology | Properties |
|---------|------------------|------------|
| Calendar Event | `schema:Event` | name, startDate, endDate, attendee, location |
| Task/Reminder | `schema:Action` | name, dueDate, actionStatus |
| Email | `schema:Message` | name, author, recipient, dateReceived |
| File | `schema:CreativeWork` | name, url, dateModified, fileFormat |

**Custom properties:** Only 7 Apple-specific ones (sourceApp, sourceIdentifier, calendar, list, relatedFile, relatedAction, relatedEvent).

---

## The KGCT Console (Your Interface)

Once implementation is complete, you'll use:

```bash
# Ingest data from macOS/iOS
kgct scan-apple --all

# Generate daily briefing
kgct generate-agenda --day today

# Check data quality
kgct validate-data

# Find double-bookings
kgct detect-conflicts --day today

# Find stale tasks (> 90 days old)
kgct find-legacy --threshold-days 90
```

The CLI is **fully auto-generated** from `.kgc/ontology.ttl` — no manual code.

---

## Quality Invariants: Prevent Defects

10 SHACL rules automatically catch and prevent common problems:

| Problem | Solution | Invariant |
|---------|----------|-----------|
| Untitled meetings | Require title | `EventTitleNotEmptyInvariant` |
| Double-booked time | Prevent overlaps | `NoOverbookingInvariant` |
| Lost tasks | Require status | `ReminderStatusRequiredInvariant` |
| Task deadlock | No circular deps | `NoCircularDependenciesInvariant` |
| Lost context | Link task to focus block | `FocusSessionHasWorkItemInvariant` |
| Broken files | Validate paths | `FilePathValidInvariant` |
| Orphaned data | Require source | `DataHasSourceInvariant` |
| Stale tasks | Mark legacy items | `LegacyItemsMarkedInvariant` |

Example: Before storing any task, SHACL automatically checks:
```sparql
?task a schema:Action .
?task schema:name ?name .   # Title required
?task schema:actionStatus ?status .  # Status required
```

---

## Knowledge Hooks: Eliminate Waste

8 automation rules remove recurring manual work:

| Hook | Trigger | What It Does | Waste Removed |
|------|---------|--------------|---------------|
| **IngestHook** | Data imported | Regenerate agenda + CLI | Copy/paste work |
| **OntologyChangeHook** | .kgc modified | Regen all artifacts | Manual sync |
| **DailyReviewHook** | 6 AM daily | Generate morning briefing | Forgotten tasks |
| **WeeklyReviewHook** | Friday 5 PM | Generate retrospective | Lost learnings |
| **ConflictDetectionHook** | Calendar updated | Find overlaps | Missed meetings |
| **ValidationFailureHook** | Bad data | Generate quality report | Silent defects |
| **StaleItemHook** | Weekly review | Find legacy tasks | Task accumulation |
| **LensProjectionHook** | Data updated | Gen specialized views | Manual aggregation |

Example: Change the due date of one task → all projections (agenda, quality report, priority matrix) automatically regenerate.

---

## Lean Value Stream

The system is designed for **one-way flow** with **no rework**:

```
macOS/iOS Data
    ↓
PyObjC Ingest (EventKit, Mail, Spotlight)
    ↓
RDF/Turtle Store (.kgc/ + data/)
    ↓
SHACL Validation (catch defects early)
    ↓
Knowledge Hooks (trigger automation)
    ↓
Generate Projections (CLI, agenda, diagrams)
    ↓
Human Review
```

Each step is **idempotent** (safe to re-run) and produces **receipts** (SHA256 hashes) for verification.

---

## How to Use This System

### Loop 1: Discover (Every morning)
```bash
kgct scan-apple --all              # Ingest latest data
kgct generate-agenda --day today   # Get today's briefing
```

### Loop 2: Align (When needed)
Edit `.kgc/ontology.ttl` ONLY if:
- New entity type appears (e.g., "meeting series")
- New relationship emerges (e.g., "depends on X team")
- New workflow required

**Most of the time, ontology is stable.** You only change it when you discover something genuinely new.

### Loop 3: Review (Daily + Weekly)
```bash
# Daily (6 AM): Auto-generated briefing
kgct generate-daily-briefing

# Weekly (Friday 5 PM): Auto-generated review
kgct generate-weekly-summary --week current
```

### Loop 4: Improve (Continuous)
If you notice **repeated manual work**, that's a design defect:

1. Add a **hook** to `.kgc/hooks.ttl` to automate it
2. Add an **invariant** to `.kgc/invariants.shacl.ttl` if it's a quality issue
3. Update **ontology** if it needs new concepts
4. Re-run: `kgct generate-cli` (CLI auto-updates)

---

## Key Files to Read

**In Order:**

1. **`KGCL_IMPLEMENTATION_SUMMARY.md`** (this directory)
   - Architecture overview
   - Standard ontologies used
   - Quality invariants explained
   - Knowledge hooks explained

2. **`.kgc/context.md`** (in `.kgc/`)
   - Complete specification (reference manual)
   - RDF planes explained (O, Σ, Q, Δ, τ)
   - All commands listed
   - Metrics and control points
   - Implementation checklist

3. **`.kgc/ontology.ttl`** (source of truth)
   - Domain model definition
   - What properties exist and why
   - Mapping to standard vocabularies

4. **`.kgc/invariants.shacl.ttl`** (quality rules)
   - 10 SHACL rules
   - Links to defect prevention

5. **`.kgc/hooks.ttl`** (automation rules)
   - 8 automation triggers
   - Links to waste elimination

---

## System Metrics

The system tracks **4 key Lean metrics**:

| Metric | Target | What It Measures |
|--------|--------|-----------------|
| **Lead Time** | Minutes to hours | From change → updated projections |
| **Rework Rate** | Trending down | Defects caught by invariants |
| **Artifact Drift** | Zero | CLI/docs disagreement with reality |
| **Hands-On Time** | Decreasing | Human effort per change |

All metrics are **automatically tracked** and reported in `docs/metrics.md`.

---

## What's Implemented vs. What's Needed

### ✅ DONE (Specification)
- RDF ontology (schema.org + custom extensions)
- SHACL validation rules (10 invariants)
- Knowledge hooks (8 automation triggers)
- Apple ingest mapping (PyObjC data sources)
- KGCT CLI generator (RDF → Typer)
- Documentation (user guide + reference)

### ⏳ NEEDED (Implementation)
- Apple ingest engines (PyObjC calendar, reminders, mail, files)
- Command handlers (scan-apple, generate-*, validate-*)
- Projection renderers (agenda, quality reports, diagrams)
- SHACL validator (validation runner)
- Cron hooks (daily/weekly triggers)

**Total implementation effort:** 1-2 weeks for experienced Python developer.

---

## Next Steps

### If you're the USER:
1. Read `.kgc/context.md` for complete guide
2. Decide which hooks to enable first
3. Plan first data ingest (calendars? reminders? all?)
4. Wait for implementation team to deliver

### If you're the IMPLEMENTATION TEAM:
1. Implement `src/kgcl/ingest/apple_*.py` (4 modules)
2. Implement `src/kgcl/handlers/*.py` (command logic)
3. Implement `src/kgcl/validators/shacl_validator.py`
4. Run: `kgct scan-apple --all` (first ingest)
5. Run: `kgct validate-data` (first validation)
6. Enable: DailyReviewHook (6 AM briefing)

---

## Questions?

Refer to:
- **Architecture:** `.kgc/manifest.ttl`
- **What data where:** `.kgc/ontology.ttl`
- **Quality rules:** `.kgc/invariants.shacl.ttl`
- **Automation:** `.kgc/hooks.ttl`
- **Data mapping:** `.kgc/apple.ingest.ttl`
- **Complete guide:** `.kgc/context.md`
- **Implementation notes:** `src/kgcl/generators/cli_generator.py`

---

**Status:** ✅ Ready for implementation
**Next:** Implement PyObjC ingest engines + command handlers
**Time to first data:** ~1 week

Go forward! 🚀
