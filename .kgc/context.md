# KGCL Context: Personal macOS/iOS Productivity Fabric

**Version:** 1.0
**Last Updated:** 2025-11-24
**Specification:** KGC Lean Context (Python/KGCT/RDF)

---

## Overview

KGCL is a **Lean-first, RDF-driven personal productivity system** that unifies macOS/iOS data (Calendar, Reminders, Mail, Files) into a single knowledge graph. It eliminates manual work, synchronization waste, and information drift using:

- **RDF/Turtle** as the canonical data model (O, Σ, Q planes)
- **SHACL invariants** to prevent quality defects
- **Knowledge hooks** to automate recurring tasks
- **Jinja projections** to generate CLI, docs, and diagrams from RDF
- **PyObjC** to ingest macOS/iOS data locally (no cloud SaaS)

---

## Core Design Principles

### 1. Lean First
**Value:** Reduce human touch points and rework.
**Eliminate Waste:**
- No manual copy/paste between apps
- No synchronization of docs, CLI, diagrams
- No ambiguous task state
- No forgotten reminders or double-booked time

### 2. Ontology-Driven (O-plane)
Everything is defined in RDF. Changes to `.kgc/ontology.ttl` automatically flow to:
- KGCT CLI (via Jinja template)
- Documentation (via projection)
- Diagrams (via projection)
- Validation rules (via SHACL)

### 3. Quality Enforced (Q-plane)
Invariants prevent known defect patterns:
- Untitled events → EventTitleNotEmptyInvariant
- Double-bookings → NoOverbookingInvariant
- Lost tasks → ReminderStatusRequiredInvariant
- Circular dependencies → NoCircularDependenciesInvariant

### 4. Pull, Not Push
Artifacts are generated *when needed*, not accumulated in advance:
- `kgct generate-cli` → regenerate KGCT from RDF
- `kgct generate-agenda --day today` → pull today's briefing from calendar/reminders
- `kgct generate-quality-report` → on-demand validation audit

---

## Directory Structure

```
.kgc/
├── manifest.ttl              # Project identity and metadata
├── ontology.ttl              # Domain entities & workflows (O-plane)
├── types.ttl                 # SHACL shapes and type rules (Σ-plane)
├── invariants.shacl.ttl      # Quality constraints (Q-plane)
├── hooks.ttl                 # Automation rules and triggers
├── apple.ingest.ttl          # macOS/iOS data mapping specification
├── projections/
│   ├── cli.py.j2             # Typer KGCT CLI template
│   ├── agenda.md.j2          # Daily/weekly agenda template
│   └── diagrams.njk          # Architecture diagrams template
└── context.md                # This file

data/
├── apple-ingest.ttl          # Ingested RDF (Calendar, Reminders, Mail, Files)
├── cache.json                # Ingest cache (for idempotency)
└── receipts.json             # SHA256 receipts (for drift detection)

src/kgcl/
├── generators/
│   └── cli_generator.py      # Standard generator script
├── ingest/
│   ├── apple_calendar.py     # EventKit calendar ingest
│   ├── apple_reminders.py    # EventKit reminders ingest
│   ├── apple_mail.py         # Mail.app metadata ingest
│   └── apple_files.py        # Finder/Spotlight file ingest
├── handlers/
│   ├── commands.py           # KGCT command handlers
│   └── projections.py        # Projection rendering
└── validators/
    └── shacl_validator.py    # SHACL validation runner

personal_kgct_cli.py          # Generated KGCT console (auto-generated)

docs/
├── agenda.md                 # Auto-generated daily/weekly agenda
├── quality-report.md         # Auto-generated quality audit
├── briefings/
│   └── daily-{DATE}.md       # Morning briefing (auto-generated)
├── reviews/
│   └── weekly-{WEEK}.md      # Weekly retrospective (auto-generated)
└── lenses/
    └── commitments-{WEEK}.md # Specialized views (auto-generated)
```

---

## Quick Start: Standard Work for KGC Technician

### Loop 1: Discover (Import data)
```bash
python personal_kgct_cli.py scan-apple --all
```
This reads:
- Calendar events (EventKit)
- Reminders (EventKit)
- Mail metadata (Mail.app)
- File artifacts (Finder/Spotlight)

And writes RDF to `data/apple-ingest.ttl`.

### Loop 2: Align (Update ontology if needed)
Edit `.kgc/ontology.ttl` ONLY if new concepts appear:
- New workflow type?
- New entity type?
- New relationship pattern?

**Most of the time, ontology is stable.** Only change it when you discover something genuinely new.

### Loop 3: Regenerate (Projections)
```bash
# CLI
python -m kgcl.generators.cli_generator

# Daily agenda
python personal_kgct_cli.py generate-agenda --day today

# Quality report
python personal_kgct_cli.py generate-quality-report

# Weekly diagrams
python personal_kgct_cli.py generate-diagrams
```

### Loop 4: Review (Inspect projections)
- Read `docs/agenda.md` for today's context
- Read `docs/quality-report.md` for violations
- Check `docs/briefings/daily-*.md` for automated briefings

### Loop 5: Remove Waste (Update hooks & O/Q)
If you see a repeated manual step:
1. Add a hook trigger to `hooks.ttl` to automate it
2. Update invariants if it's a quality defect
3. Update ontology if it needs new concepts

Repeat.

---

## RDF Planes Explained

### O-Plane (Ontology)
**File:** `.kgc/ontology.ttl`

Defines **what things are** and **how they relate**:
- Entities: `apple:CalendarEvent`, `apple:Reminder`, `apple:MailMessage`, `apple:FileArtifact`
- Properties: `apple:hasStartTime`, `apple:hasStatus`, `apple:linksToFile`
- Workflows: `apple:DailyReview`, `apple:WeeklyReview`

Example query:
```sparql
SELECT ?event ?title ?start
WHERE {
  ?event a apple:CalendarEvent ;
         schema:name ?title ;
         apple:hasStartTime ?start .
  FILTER(?start > NOW())
}
```

### Σ-Plane (Types)
**File:** `.kgc/types.ttl`

Defines **shape constraints** (SHACL):
- Every `CalendarEvent` must have a non-empty title ✓
- Every `CalendarEvent` must have start < end ✓
- Every `Reminder` must have a status ✓

SHACL reports violations; violations trigger `ValidationFailureHook`.

### Q-Plane (Invariants)
**File:** `.kgc/invariants.shacl.ttl`

Defines **quality rules** that prevent defects:
- No overlapping calendar events (defect: double-booking)
- No circular task dependencies (defect: deadlock)
- All data has traceable source (defect: orphaned data)

Each invariant links to an observed failure mode.

### Δ-Plane (Hooks)
**File:** `.kgc/hooks.ttl`

Defines **automation triggers**:
- When `DataIngested` → regenerate agenda + CLI
- When `OntologyModified` → regenerate diagrams
- When `ValidationFailed` → generate quality report
- On Friday 5 PM → generate weekly review

Hooks remove recurring waste.

### τ-Plane (Projections)
**Files:** `.kgc/projections/*.j2`

Defines **derived artifacts** (one-way reads from RDF):
- KGCT CLI (Jinja template)
- Documentation (Markdown templates)
- Diagrams (Nunjucks templates)

No edits to projections; all changes happen in `.kgc/` files.

---

## Invariant Map: Defects → Prevention

| Defect | Cause | Preventive Invariant |
|--------|-------|----------------------|
| Untitled meetings | Poor habit | `EventTitleNotEmptyInvariant` |
| Double-booked time | Missing overlap detection | `NoOverbookingInvariant` |
| Missed tasks | No status field | `ReminderStatusRequiredInvariant` |
| Task deadlock | Circular dependencies | `NoCircularDependenciesInvariant` |
| Context loss | Focus block with no link | `FocusSessionHasWorkItemInvariant` |
| Orphaned mail | Incomplete metadata | `MailMetadataValidInvariant` |
| Lost file links | Broken paths | `FilePathValidInvariant` |
| Accumulation of waste | No decommissioning | `LegacyItemsMarkedInvariant` |
| Invalid time ranges | Data entry error | `EventTimeRangeValidInvariant` |
| Missing commitments | Today-tagged tasks, no due date | `ReminderDueTodayValidInvariant` |

---

## Hook Map: Waste Removed

| Hook | Trigger | Action | Waste Removed |
|------|---------|--------|---------------|
| `IngestHook` | Apple data ingested | Regenerate agenda, CLI | Copy/paste, manual updates |
| `OntologyChangeHook` | ontology.ttl modified | Regen CLI, docs, diagrams | Desync between O and artifacts |
| `ValidationFailureHook` | SHACL violation | Gen quality report | Silent data quality issues |
| `StaleItemHook` | Weekly review | Find legacy items | Accumulation of waste |
| `ConflictDetectionHook` | Calendar updated | Detect overlaps | Missed meetings, last-minute scramble |
| `DailyReviewHook` | 6 AM (cron) | Gen daily briefing | Forgotten tasks, unclear priorities |
| `WeeklyReviewHook` | Friday 5 PM (cron) | Gen retrospective | Lost learnings, no pattern ID |
| `LensProjectionHook` | Data ingested | Gen specialized views | Tab surfing, manual aggregation |

---

## KGCT CLI Commands (Auto-Generated)

The `personal_kgct_cli.py` is generated from `.kgc/ontology.ttl`.

Core commands:

```bash
# Ingest
kgct scan-apple --all                    # Ingest Calendar, Reminders, Mail, Files
kgct scan-apple --calendars              # Calendar only
kgct scan-apple --reminders              # Reminders only

# Generate
kgct generate-cli                        # Regenerate this CLI from RDF
kgct generate-agenda --day today         # Today's agenda
kgct generate-agenda --day this-week     # Week's agenda
kgct generate-diagrams                   # Architecture diagrams
kgct generate-quality-report             # Validation audit
kgct generate-daily-briefing             # Morning briefing
kgct generate-weekly-summary --week 1    # Weekly retrospective

# Analysis
kgct detect-conflicts --day today        # Find double-bookings
kgct find-legacy --threshold-days 90     # Find stale tasks
kgct find-unused-lists --threshold-days 60  # Find inactive lists
kgct analyze-week-patterns --metrics time-usage,interruptions

# Validation
kgct validate-data                       # Run SHACL validation
kgct validate-invariants                 # Check quality rules
kgct check-receipts                      # Verify data integrity
```

---

## Metrics: Lean Control Points

We measure **four key metrics** to detect waste and flow issues:

1. **Lead Time for Change**
   From creating/changing event → updated projections.
   Target: minutes to hours.

2. **Rework Rate**
   Fraction of changes requiring correction due to stale O/Q.
   Target: trending down toward zero.

3. **Artifact Drift**
   Cases where CLI/docs/diagrams disagree with reality.
   Target: zero (each incident is a defect).

4. **Hands-On Time**
   Technician time per significant change.
   Target: decreasing (automation removes manual steps).

All metrics project into `docs/metrics.md` from `.kgc/` + receipts.

---

## Apple Ingest: PyObjC Integration

Data flows from macOS/iOS → RDF via PyObjC bridges (no cloud):

### Calendar → apple:CalendarEvent
- **Framework:** EventKit (macOS/iOS)
- **Access:** Request user permission
- **Maps:** `EKEvent` → RDF with properties (title, start, end, attendees, source)
- **Idempotency:** Cache by `eventIdentifier`

### Reminders → apple:Reminder
- **Framework:** EventKit (macOS) or Reminders.app
- **Access:** Request user permission
- **Maps:** `EKReminder` → RDF with status, due date, list
- **Idempotency:** Cache by `calendarItemIdentifier`

### Mail → apple:MailMessage
- **Framework:** Mail.app scripting / Cocoa APIs
- **Access:** Request user permission
- **Maps:** Message metadata (subject, from, date, flags) → RDF
- **Note:** Body text NOT ingested (privacy, storage)
- **Idempotency:** Cache by `messageID`

### Files → apple:FileArtifact
- **Framework:** NSFileManager, NSMetadataQuery (Spotlight)
- **Discovery:** Spotlight queries, designated folders, Finder tags
- **Maps:** File metadata (name, path, modified date, tags) → RDF
- **Idempotency:** Cache by path

All ingest validates against SHACL before storing RDF.

---

## Implementation Checklist

- [x] Create `.kgc/` directory with manifest, ontology, types, invariants, hooks, apple.ingest specs
- [x] Define CLI commands in ontology.ttl
- [x] Create Jinja template for KGCT CLI
- [x] Create generator script for CLI
- [ ] Implement Apple ingest engines (PyObjC calendar, reminders, mail, files)
- [ ] Implement handlers (command logic for scan-apple, generate-*, validate-*, etc.)
- [ ] Implement projection rendering (agenda, diagrams, quality reports)
- [ ] Setup SHACL validator
- [ ] Create daily/weekly hook executors (cron-triggered)
- [ ] Wire up `personal_kgct_cli.py` as entrypoint
- [ ] Run first scan: `kgct scan-apple --all`
- [ ] Generate first artifacts: `kgct generate-agenda --day today`
- [ ] Validate: `kgct validate-data`
- [ ] Start Lean improvement loop

---

## Key References

- **Manifest:** `.kgc/manifest.ttl` — Project identity and planes
- **Ontology:** `.kgc/ontology.ttl` — Domain model
- **Types:** `.kgc/types.ttl` — SHACL shapes
- **Invariants:** `.kgc/invariants.shacl.ttl` — Quality rules
- **Hooks:** `.kgc/hooks.ttl` — Automation triggers
- **Ingest:** `.kgc/apple.ingest.ttl` — Data source specs
- **CLI Generator:** `src/kgcl/generators/cli_generator.py`
- **Ingest Engines:** `src/kgcl/ingest/apple_*.py`

---

## Next Steps

1. **Run Apple ingest:** `kgct scan-apple --all` → generates `data/apple-ingest.ttl`
2. **Inspect results:** Check SHACL violations in `docs/quality-report.md`
3. **Generate agenda:** `kgct generate-agenda --day today` → see what's mapped
4. **Review ontology:** Are all entities mapped correctly? Update `.kgc/ontology.ttl` if needed
5. **Setup hooks:** Decide which automated workflows to enable first (daily briefing, weekly review, conflict detection)
6. **Iterate:** Apply Lean improvement: remove waste, reduce rework, automate manual steps

---

**Last Generated:** 2025-11-24 | **KGC Specification Version:** 1.0
