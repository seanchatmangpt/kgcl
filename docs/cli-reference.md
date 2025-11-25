# KGCL CLI Reference

Command-line tools for the Knowledge Graph Capture & Learning system.

## Installation

```bash
pip install kgcl
```

After installation, the following commands are available:

- `kgc-daily-brief` - Generate daily briefs
- `kgc-weekly-retro` - Generate weekly retrospectives
- `kgc-feature-list` - List and explore features
- `kgc-query` - Execute SPARQL queries
- `kgc-config` - Manage configuration

## Commands

### kgc-daily-brief

Generate a daily brief from recent events.

**Usage:**
```bash
kgc-daily-brief [OPTIONS]
```

**Options:**
- `--date DATE` - Target date for the brief (format: YYYY-MM-DD, defaults to today)
- `--lookback N` - Number of days to look back (default: 1)
- `--output, -o FILE` - Output file path
- `--clipboard, -c` - Copy result to clipboard
- `--format, -f FORMAT` - Output format (markdown, json)
- `--model MODEL` - Ollama model to use (default: llama3.2)
- `--verbose, -v` - Verbose output

**Examples:**
```bash
# Generate today's brief
kgc-daily-brief

# Generate brief for specific date with 2-day lookback
kgc-daily-brief --date 2024-01-15 --lookback 2

# Save to file and copy to clipboard
kgc-daily-brief -o brief.md -c

# Use different model
kgc-daily-brief --model llama3.3
```

---

### kgc-weekly-retro

Generate a weekly retrospective from aggregated features.

**Usage:**
```bash
kgc-weekly-retro [OPTIONS]
```

**Options:**
- `--end-date DATE` - End date for the retrospective (defaults to today)
- `--days N` - Number of days to include (default: 7)
- `--output, -o FILE` - Output file path
- `--clipboard, -c` - Copy result to clipboard
- `--format, -f FORMAT` - Output format (markdown, json)
- `--model MODEL` - Ollama model to use (default: llama3.2)
- `--include-metrics` - Include detailed metrics in output
- `--verbose, -v` - Verbose output

**Examples:**
```bash
# Generate retrospective for last 7 days
kgc-weekly-retro

# Custom time range with metrics
kgc-weekly-retro --days 14 --include-metrics

# Save to file
kgc-weekly-retro -o retro.md

# Use different model
kgc-weekly-retro --model llama3.3
```

---

### kgc-feature-list

List and explore features from the knowledge graph.

**Usage:**
```bash
kgc-feature-list [OPTIONS]
```

**Options:**
- `--category CATEGORY` - Filter by category
- `--source SOURCE` - Filter by source
- `--search TERM` - Search term for feature name
- `--templates-only` - Show only feature templates
- `--instances-only` - Show only feature instances
- `--output, -o FILE` - Output file path
- `--format, -f FORMAT` - Output format (table, json, csv, tsv)
- `--sort-by FIELD` - Sort by field (name, updated, category, source)
- `--verbose, -v` - Verbose output with full details

**Examples:**
```bash
# List all features
kgc-feature-list

# Filter by category
kgc-feature-list --category metrics

# Search for specific features
kgc-feature-list --search "test"

# Show only templates in JSON format
kgc-feature-list --templates-only -f json

# Export to CSV
kgc-feature-list -f csv -o features.csv
```

---

### kgc-query

Execute SPARQL queries against the knowledge graph.

**Usage:**
```bash
kgc-query [OPTIONS]
```

**Options:**
- `--query, -q SPARQL` - SPARQL query to execute
- `--file FILE` - File containing SPARQL query
- `--template, -t NAME` - Use a predefined query template
- `--output, -o FILE` - Output file path
- `--format, -f FORMAT` - Output format (table, json, csv, tsv)
- `--limit N` - Limit number of results
- `--endpoint URL` - SPARQL endpoint URL (default: http://localhost:3030/kgcl/sparql)
- `--show-templates` - Show available query templates and exit
- `--verbose, -v` - Verbose output

**Available Templates:**
- `all_features` - List all features with types and categories
- `recent_events` - Recent events from the knowledge graph
- `feature_dependencies` - Feature dependency relationships
- `metrics_summary` - Aggregated metrics summary
- `code_changes` - Recent code changes

**Examples:**
```bash
# Show available templates
kgc-query --show-templates

# Use a template query
kgc-query -t all_features

# Execute custom query
kgc-query -q "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

# Query from file and export to JSON
kgc-query --file query.sparql -f json -o results.json

# Query with result limit
kgc-query -t recent_events --limit 50
```

---

### kgc-config

Manage KGCL configuration settings.

**Usage:**
```bash
kgc-config COMMAND [OPTIONS]
```

**Commands:**

#### show
Show current configuration.

```bash
kgc-config show [--format FORMAT]
```

#### init
Initialize configuration with defaults.

```bash
kgc-config init
```

#### set
Set a configuration value.

```bash
kgc-config set KEY VALUE
```

**Example:**
```bash
kgc-config set default_model llama3.3
kgc-config set event_retention_days 30
```

#### get
Get a configuration value.

```bash
kgc-config get KEY
```

#### reset
Reset configuration to defaults.

```bash
kgc-config reset
```

#### exclude
Manage exclusion lists.

**Subcommands:**
- `add` - Add exclusion pattern
- `remove` - Remove exclusion pattern
- `list` - List all exclusions

**Examples:**
```bash
# Add file exclusion
kgc-config exclude add --file "*.backup"

# Add directory exclusion
kgc-config exclude add --directory "build"

# List exclusions
kgc-config exclude list

# Remove exclusion
kgc-config exclude remove --file "*.backup"
```

#### capability
Manage capability toggles.

**Subcommands:**
- `enable` - Enable a capability
- `disable` - Disable a capability
- `list` - List all capabilities

**Available Capabilities:**
- `auto_feature_discovery` - Automatic feature discovery
- `continuous_learning` - Continuous learning mode
- `telemetry` - Telemetry reporting
- `auto_updates` - Automatic updates

**Examples:**
```bash
# Enable telemetry
kgc-config capability enable telemetry

# Disable auto-updates
kgc-config capability disable auto_updates

# List all capabilities
kgc-config capability list
```

## Configuration

Configuration is stored in `~/.config/kgcl/config.json`.

**Default Configuration:**
```json
{
  "exclusions": {
    "files": [".git", "__pycache__", "node_modules", ".venv", "*.pyc"],
    "directories": [".git", "__pycache__", "node_modules", ".venv"],
    "patterns": ["*.log", "*.tmp", "*.swp"]
  },
  "capabilities": {
    "auto_feature_discovery": true,
    "continuous_learning": true,
    "telemetry": false,
    "auto_updates": false
  },
  "settings": {
    "default_model": "llama3.2",
    "sparql_endpoint": "http://localhost:3030/kgcl/sparql",
    "event_retention_days": 90,
    "max_feature_instances": 10000
  }
}
```

## Output Formats

All CLI commands support multiple output formats:

- `table` - Rich formatted table (terminal only)
- `json` - JSON format
- `csv` - Comma-separated values (requires --output)
- `tsv` - Tab-separated values (requires --output)
- `markdown` - Markdown format (for briefs and retros)

## Environment Variables

- `KGCL_CONFIG_DIR` - Override default config directory
- `KGCL_SPARQL_ENDPOINT` - Override default SPARQL endpoint
- `KGCL_MODEL` - Override default Ollama model

## Getting Help

For detailed help on any command:

```bash
kgc-daily-brief --help
kgc-weekly-retro --help
kgc-feature-list --help
kgc-query --help
kgc-config --help
```

## Examples

### Daily Workflow

```bash
# Morning: Generate yesterday's brief
kgc-daily-brief --lookback 1 -o daily-$(date +%Y%m%d).md

# During day: Check specific features
kgc-feature-list --category testing --verbose

# Query recent activity
kgc-query -t recent_events --limit 20

# End of week: Generate retrospective
kgc-weekly-retro --include-metrics -o weekly-retro.md
```

### Advanced Usage

```bash
# Complex query with custom SPARQL
kgc-query -q "
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?feature (COUNT(?instance) as ?count)
WHERE {
  ?instance a kgcl:FeatureInstance ;
           kgcl:template ?feature .
  FILTER (?timestamp > '2024-01-01'^^xsd:dateTime)
}
GROUP BY ?feature
ORDER BY DESC(?count)
" -f json -o feature-usage.json

# Export feature catalog for analysis
kgc-feature-list --format csv -o catalog.csv

# Generate comprehensive weekly report
kgc-weekly-retro --days 7 --include-metrics --verbose -o report.md
```

## Troubleshooting

### Command not found

Ensure the package is installed:
```bash
pip install kgcl
```

### SPARQL endpoint connection issues

Check the endpoint configuration:
```bash
kgc-config get sparql_endpoint
```

Update if necessary:
```bash
kgc-config set sparql_endpoint http://localhost:3030/kgcl/sparql
```

### Clipboard not working

Clipboard functionality requires system tools:
- macOS: `pbcopy` (built-in)
- Linux: `xclip` or `xsel`

Install on Linux:
```bash
sudo apt-get install xclip  # Ubuntu/Debian
sudo yum install xclip      # CentOS/RHEL
```

## Contributing

See the main project documentation for contribution guidelines.
