# Getting Started with KGCL

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [First-Time User Flow](#first-time-user-flow)
- [Basic Workflows](#basic-workflows)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Configuration Reference](#configuration-reference)
- [Next Steps](#next-steps)

## Prerequisites

### System Requirements

- **Operating System**: macOS 11.0 (Big Sur) or later
- **Python**: 3.12 or later
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk Space**: 1 GB minimum, 5 GB recommended for extended usage

### Required Software

1. **Python 3.12+**

   Check your Python version:
   ```bash
   python3 --version
   ```

   If needed, install via Homebrew:
   ```bash
   brew install python@3.12
   ```

2. **uv** (Python package manager)

   Install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Or via pip:
   ```bash
   pip install uv
   ```

3. **Ollama** (for LLM reasoning)

   Download from https://ollama.ai or install via Homebrew:
   ```bash
   brew install ollama
   ```

   Pull the default model:
   ```bash
   ollama pull llama3.3
   ```

   Start Ollama server:
   ```bash
   ollama serve
   ```

### Optional Software

1. **OpenTelemetry Collector** (for observability)

   ```bash
   brew install opentelemetry-collector
   ```

2. **Jaeger** (for trace visualization)

   ```bash
   docker run -d --name jaeger \
     -p 16686:16686 \
     -p 4317:4317 \
     -p 4318:4318 \
     jaegertracing/all-in-one:latest
   ```

   Access Jaeger UI at http://localhost:16686

## Installation

### Option 1: Install from Source (Recommended for Development)

1. **Clone the repository**

   ```bash
   cd ~/dev
   git clone https://github.com/user/kgcl.git
   cd kgcl
   ```

2. **Create virtual environment and install dependencies**

   ```bash
   uv sync --python 3.12
   ```

   This creates a virtual environment at `.venv` and installs all dependencies.

3. **Activate the virtual environment**

   ```bash
   source .venv/bin/activate
   ```

4. **Verify installation**

   ```bash
   kgc-config --version
   kgc-health check
   ```

### Option 2: Install from PyPI (When Available)

```bash
pip install kgcl

# Verify installation
kgc-config --version
```

### Option 3: Dev Container

If using VS Code Dev Containers:

1. Open folder in VS Code
2. Press `Cmd+Shift+P` → "Dev Containers: Reopen in Container"
3. Wait for container to build

All dependencies are pre-installed in the container.

## Initial Configuration

### 1. Initialize Configuration

Run the configuration wizard:

```bash
kgc-config init
```

This creates `~/.config/kgcl/config.json` with default settings:

```json
{
  "default_model": "llama3.3",
  "event_retention_days": 90,
  "sparql_endpoint": "local",
  "data_directory": "~/.kgcl/data",
  "log_directory": "~/.kgcl/logs",
  "enable_telemetry": false,
  "ollama_endpoint": "http://localhost:11434",
  "excluded_apps": [
    "com.apple.Spotlight",
    "com.apple.loginwindow"
  ],
  "excluded_domains": [
    "localhost",
    "127.0.0.1"
  ]
}
```

### 2. Verify Configuration

View your configuration:

```bash
kgc-config show
```

Check specific settings:

```bash
kgc-config get default_model
kgc-config get data_directory
```

### 3. Configure Ollama (Required for Reasoning)

Test Ollama connection:

```bash
kgc-health check ollama
```

If Ollama is not running:

```bash
# Start Ollama server
ollama serve &

# Pull a model if needed
ollama pull llama3.3
```

Update Ollama endpoint if needed:

```bash
kgc-config set ollama_endpoint http://localhost:11434
```

### 4. Configure Data Directories

By default, KGCL stores data in `~/.kgcl/`:

```
~/.kgcl/
├── data/              # RDF graphs and events
├── logs/              # Application logs
├── cache/             # TTL2DSPy cache
└── config.json        # Configuration file
```

To use a custom location:

```bash
kgc-config set data_directory /path/to/data
kgc-config set log_directory /path/to/logs
```

### 5. Set Up Privacy Filters (Recommended)

Exclude sensitive applications:

```bash
kgc-config exclude add --app "com.company.private"
kgc-config exclude add --app "com.banking.app"
```

Exclude domains:

```bash
kgc-config exclude add --domain "private-site.com"
kgc-config exclude add --domain "banking.com"
```

Exclude file patterns:

```bash
kgc-config exclude add --pattern "*.secret"
kgc-config exclude add --pattern "/private/*"
```

View exclusions:

```bash
kgc-config exclude list
```

## First-Time User Flow

### Step 1: Discover System Capabilities

Explore what KGCL can collect:

```bash
# Start the PyObjC agent to discover capabilities
python -m kgcl.pyobjc_agent discover

# This will:
# - Load available PyObjC frameworks
# - Enumerate observable methods
# - Generate capability JSON-LD
# - Save to ~/.kgcl/data/capabilities.jsonld
```

Expected output:

```
=== Capability Discovery Summary ===
Frameworks loaded: 3
  - AppKit: 25 classes, 150 methods
  - WebKit: 12 classes, 80 methods
  - EventKit: 8 classes, 45 methods
Total capabilities: 275
Output: ~/.kgcl/data/capabilities.jsonld
```

### Step 2: Start Collecting Events

Start the PyObjC agent to collect events:

```bash
# Start agent in background
python -m kgcl.pyobjc_agent start --config config/pyobjc_agent.yaml

# Or run in foreground for debugging
python -m kgcl.pyobjc_agent run --verbose
```

The agent will:
- Poll frontmost application every 1 second
- Check browser history every 5 minutes
- Check calendar events every 5 minutes
- Write events to `~/.kgcl/data/events/`

To stop the agent:

```bash
python -m kgcl.pyobjc_agent stop
```

### Step 3: Ingest Events into UNRDF

After collecting events for a while (10+ minutes recommended), ingest them into the RDF graph:

```bash
# Ingest all events from the data directory
unrdf ingest --source ~/.kgcl/data/events/ \
             --output ~/.kgcl/data/knowledge.ttl \
             --validate

# Check ingestion results
unrdf stats ~/.kgcl/data/knowledge.ttl
```

Expected output:

```
Ingestion complete
  Events processed: 1,250
  Triples created: 8,750
  Validation: PASSED
  Duration: 2.3s
  Output: ~/.kgcl/data/knowledge.ttl

Graph statistics:
  Total triples: 8,750
  Unique subjects: 1,250
  Unique predicates: 15
  Provenance records: 8,750
```

### Step 4: Explore Features

List available features:

```bash
kgc-feature-list
```

This shows feature templates that can be materialized from your events:

```
┌────────────────────────────┬──────────────┬─────────────────────────┐
│ Feature                    │ Category     │ Description             │
├────────────────────────────┼──────────────┼─────────────────────────┤
│ app_usage_time             │ productivity │ Time spent per app      │
│ browser_domain_visits      │ browsing     │ Domains visited         │
│ meeting_count              │ calendar     │ Meetings attended       │
│ context_switches           │ productivity │ App switches per hour   │
│ focus_time                 │ productivity │ Uninterrupted work time │
└────────────────────────────┴──────────────┴─────────────────────────┘

Total: 5 features available
```

View details for a specific feature:

```bash
kgc-feature-list --search "app_usage" --verbose
```

### Step 5: Generate Your First Daily Brief

Generate a daily brief from today's collected events:

```bash
kgc-daily-brief
```

If you haven't collected enough data yet, use a past date:

```bash
kgc-daily-brief --date 2024-01-15
```

Example output:

```markdown
# Daily Brief for 2024-01-15

## Overview
Your day focused primarily on software development, with significant time
spent in VS Code and Chrome. You had 3 scheduled meetings and demonstrated
good focus with low context switching.

## Key Activities
- **Development**: 4.5 hours in VS Code
- **Research**: 2.3 hours in Chrome (GitHub, StackOverflow)
- **Communication**: 1.2 hours in Slack
- **Meetings**: 3 scheduled (2 hours total)

## Productivity Insights
- **Focus Score**: 8/10
- **Context Switches**: 32 (below average, good!)
- **Peak Productivity**: 10:00 AM - 12:30 PM

## Top Websites
1. github.com (45 visits, 1.2 hours)
2. stackoverflow.com (18 visits, 0.8 hours)
3. docs.python.org (12 visits, 0.4 hours)

## Recommendations for Tomorrow
- Continue morning focus block (worked well today)
- Schedule meetings after 2 PM to protect deep work time
- Consider batching similar tasks to reduce switching
```

Save the brief to a file:

```bash
kgc-daily-brief --date 2024-01-15 --output daily-brief.md
```

Copy to clipboard:

```bash
kgc-daily-brief --clipboard
```

### Step 6: Run Custom Queries

Explore your data with SPARQL:

```bash
# Show available query templates
kgc-query --show-templates

# Run a template query
kgc-query --template all_features

# Run a custom query
kgc-query --query "
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?app (SUM(?duration) as ?total)
WHERE {
  ?event a kgcl:AppUsageEvent ;
         kgcl:appName ?app ;
         kgcl:duration ?duration .
}
GROUP BY ?app
ORDER BY DESC(?total)
LIMIT 10
"
```

Save query results:

```bash
kgc-query --template all_features --format json --output features.json
```

## Basic Workflows

### Daily Workflow

```bash
# Morning: Start the agent
python -m kgcl.pyobjc_agent start

# Evening: Generate brief for today
kgc-daily-brief --output ~/Documents/briefs/$(date +%Y-%m-%d).md

# Optional: Stop agent if not running continuously
python -m kgcl.pyobjc_agent stop
```

### Weekly Workflow

```bash
# Generate weekly retrospective
kgc-weekly-retro --days 7 --output weekly-retro.md

# Export feature catalog
kgc-feature-list --format csv --output features.csv

# Archive old data
unrdf archive --older-than 30d --output archive/
```

### Continuous Monitoring

Set up as a launch agent on macOS:

1. Create `~/Library/LaunchAgents/com.kgcl.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kgcl.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/.kgcl/.venv/bin/python</string>
        <string>-m</string>
        <string>kgcl.pyobjc_agent</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/.kgcl/logs/agent.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/.kgcl/logs/agent-error.log</string>
</dict>
</plist>
```

2. Load the agent:

```bash
launchctl load ~/Library/LaunchAgents/com.kgcl.agent.plist
```

3. Verify it's running:

```bash
launchctl list | grep kgcl
```

## Troubleshooting Common Issues

### Issue: Command not found

**Symptom**: `kgc-daily-brief: command not found`

**Solution**:

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Verify installation
which kgc-daily-brief

# Reinstall if needed
uv sync --python 3.12
```

### Issue: Ollama connection failed

**Symptom**: `Failed to connect to Ollama at http://localhost:11434`

**Solution**:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve &

# Verify model is available
ollama list
ollama pull llama3.3
```

### Issue: No events collected

**Symptom**: PyObjC agent runs but no events are saved

**Solution**:

```bash
# Check agent logs
tail -f ~/.kgcl/logs/pyobjc_agent.log

# Verify configuration
cat config/pyobjc_agent.yaml

# Check permissions (grant accessibility access)
System Settings → Privacy & Security → Accessibility → Add your terminal

# Run in verbose mode to debug
python -m kgcl.pyobjc_agent run --verbose
```

### Issue: UNRDF ingestion fails

**Symptom**: `ValidationError: SHACL validation failed`

**Solution**:

```bash
# Check event format
head ~/.kgcl/data/events/events_*.jsonl

# Skip validation temporarily
unrdf ingest --source ~/.kgcl/data/events/ \
             --output ~/.kgcl/data/knowledge.ttl \
             --no-validate

# Check SHACL shapes
ls ontology/*.ttl
```

### Issue: Daily brief generation fails

**Symptom**: `No features found for date 2024-01-15`

**Solution**:

```bash
# Check if events are ingested
unrdf stats ~/.kgcl/data/knowledge.ttl

# Query for events manually
kgc-query --query "SELECT * WHERE { ?s a ?type } LIMIT 10"

# Try different date
kgc-daily-brief --date $(date -v-1d +%Y-%m-%d)

# Run with verbose output
kgc-daily-brief --verbose
```

### Issue: Slow query performance

**Symptom**: Queries take > 10 seconds

**Solution**:

```bash
# Check graph size
unrdf stats ~/.kgcl/data/knowledge.ttl

# Archive old data
unrdf archive --older-than 30d --output archive/

# Consider external triple store for large datasets
# See SYSTEM_ARCHITECTURE.md for Fuseki integration
```

## Configuration Reference

### Core Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `default_model` | `llama3.3` | LLM model for reasoning |
| `event_retention_days` | `90` | Days to retain events |
| `sparql_endpoint` | `local` | SPARQL endpoint URL or 'local' |
| `data_directory` | `~/.kgcl/data` | Data storage location |
| `log_directory` | `~/.kgcl/logs` | Log file location |

### Ollama Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ollama_endpoint` | `http://localhost:11434` | Ollama API endpoint |
| `ollama_timeout` | `30` | Request timeout (seconds) |
| `ollama_temperature` | `0.7` | LLM temperature |

### Collection Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `collect_app_usage` | `true` | Collect app usage events |
| `collect_browser_history` | `true` | Collect browser history |
| `collect_calendar` | `true` | Collect calendar events |
| `collection_interval` | `1` | Frontmost app poll interval (seconds) |

### Privacy Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `privacy_mode` | `false` | Redact sensitive data |
| `excluded_apps` | `[...]` | Apps to exclude from collection |
| `excluded_domains` | `[...]` | Domains to exclude |
| `excluded_patterns` | `[]` | File patterns to exclude |

### Observability Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enable_telemetry` | `false` | Send telemetry data |
| `enable_tracing` | `true` | OpenTelemetry tracing |
| `otlp_endpoint` | `http://localhost:4317` | OTLP exporter endpoint |
| `trace_sampling_rate` | `1.0` | Trace sampling rate (0.0-1.0) |

### Modify Settings

```bash
# Set a value
kgc-config set default_model llama3.2

# Get a value
kgc-config get default_model

# Reset to defaults
kgc-config reset

# Show all settings
kgc-config show
```

## Next Steps

### Learn More

- [System Architecture](./SYSTEM_ARCHITECTURE.md) - Understand how components work together
- [API Reference](./API_REFERENCE.md) - Detailed API documentation
- [Feature Catalog](./FEATURE_CATALOG.md) - All available features
- [Reasoning Pipeline](./REASONING_PIPELINE.md) - How DSPy signatures work
- [Observability Guide](./OBSERVABILITY_GUIDE.md) - Monitoring and debugging

### Extend KGCL

- [Add Custom Collectors](./EXTENSIBILITY.md#custom-collectors) - Collect new event types
- [Create Feature Templates](./EXTENSIBILITY.md#feature-templates) - Define new features
- [Write DSPy Signatures](./EXTENSIBILITY.md#dspy-signatures) - Custom reasoning tasks
- [Implement Hooks](./EXTENSIBILITY.md#hooks) - Extend core behavior

### Get Help

- [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common issues and solutions
- [Data Privacy Guide](./DATA_PRIVACY.md) - Privacy and data management
- [Contributing Guide](./CONTRIBUTING.md) - Contribute to KGCL
- [GitHub Issues](https://github.com/user/kgcl/issues) - Report bugs or request features

### Examples

Explore example workflows in the repository:

```bash
# Example: Custom feature extraction
examples/custom_features/

# Example: DSPy signature development
examples/dspy_signatures/

# Example: Integration with external tools
examples/integrations/
```

## Quick Command Reference

```bash
# Agent management
python -m kgcl.pyobjc_agent start          # Start agent
python -m kgcl.pyobjc_agent stop           # Stop agent
python -m kgcl.pyobjc_agent status         # Check status

# Data ingestion
unrdf ingest --source events/ --output graph.ttl
unrdf stats graph.ttl
unrdf query graph.ttl "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

# Daily workflows
kgc-daily-brief                            # Today's brief
kgc-weekly-retro --days 7                  # Weekly retrospective
kgc-feature-list                           # List features
kgc-query --template all_features          # Query data

# Configuration
kgc-config show                            # Show all settings
kgc-config set key value                   # Set a value
kgc-config exclude add --app "com.app.id"  # Add exclusion

# Health checks
kgc-health check                           # Overall health
kgc-health check ollama                    # Ollama status
kgc-health check unrdf                     # UNRDF status
```

Happy knowledge graphing! 🚀
