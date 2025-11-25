# KGCL CLI Quick Start Guide

## Installation

```bash
# Clone the repository
cd /Users/sac/dev/kgcl

# Install with uv
uv sync --python 3.12

# Activate virtual environment
source .venv/bin/activate
```

## Available Commands

After installation, you have access to 5 CLI commands:

| Command | Purpose |
|---------|---------|
| `kgc-daily-brief` | Generate daily briefs from events |
| `kgc-weekly-retro` | Generate weekly retrospectives |
| `kgc-feature-list` | Browse and explore features |
| `kgc-query` | Execute SPARQL queries |
| `kgc-config` | Manage configuration |

## First Run

### 1. Initialize Configuration

```bash
kgc-config init
```

This creates `~/.config/kgcl/config.json` with sensible defaults.

### 2. Check Configuration

```bash
# View all settings
kgc-config show

# View specific setting
kgc-config get default_model
```

### 3. Generate Your First Brief

```bash
# Basic usage (uses today's date)
kgc-daily-brief

# With verbose output
kgc-daily-brief --verbose

# Save to file
kgc-daily-brief -o my-brief.md
```

### 4. Explore Features

```bash
# List all features
kgc-feature-list

# Filter by category
kgc-feature-list --category testing

# Search for specific features
kgc-feature-list --search "test" --verbose
```

### 5. Run Queries

```bash
# Show available templates
kgc-query --show-templates

# Run a template query
kgc-query -t all_features

# Custom query
kgc-query -q "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

## Common Workflows

### Daily Usage

```bash
# Morning routine - generate yesterday's brief
kgc-daily-brief --lookback 1 -o daily-$(date +%Y%m%d).md

# Check what features are available
kgc-feature-list --sort-by updated

# Query recent activity
kgc-query -t recent_events --limit 20
```

### Weekly Review

```bash
# Generate comprehensive retrospective
kgc-weekly-retro \
  --include-metrics \
  --verbose \
  -o weekly-retro-$(date +%Y%m%d).md

# Export feature catalog
kgc-feature-list \
  --format csv \
  -o feature-catalog.csv

# Query code changes
kgc-query -t code_changes --limit 50
```

### Custom Analysis

```bash
# Export all testing features
kgc-feature-list \
  --category testing \
  --format json \
  -o testing-features.json

# Run custom SPARQL
kgc-query -q "
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?feature (COUNT(?instance) as ?count)
WHERE {
  ?instance a kgcl:FeatureInstance ;
           kgcl:template ?feature .
}
GROUP BY ?feature
ORDER BY DESC(?count)
" -f table
```

## Configuration Tips

### Customize Default Model

```bash
kgc-config set default_model llama3.3
```

### Add File Exclusions

```bash
kgc-config exclude add --file "*.backup"
kgc-config exclude add --directory "build"
kgc-config exclude add --pattern "*.tmp"
```

### Enable/Disable Capabilities

```bash
# Enable telemetry
kgc-config capability enable telemetry

# Disable auto-updates
kgc-config capability disable auto_updates

# List all capabilities
kgc-config capability list
```

### Adjust Settings

```bash
# Increase event retention
kgc-config set event_retention_days 180

# Change SPARQL endpoint
kgc-config set sparql_endpoint http://localhost:3030/kgcl/sparql

# Set max feature instances
kgc-config set max_feature_instances 50000
```

## Output Formats

All commands support multiple output formats:

### Table (Default for lists)
```bash
kgc-feature-list --format table
```

### JSON (Structured data)
```bash
kgc-feature-list --format json
kgc-query -t all_features --format json
```

### CSV (Spreadsheet compatible)
```bash
kgc-feature-list --format csv -o features.csv
```

### TSV (Tab-separated)
```bash
kgc-query -t metrics_summary --format tsv -o metrics.tsv
```

### Markdown (Briefs and retros)
```bash
kgc-daily-brief --format markdown -o brief.md
kgc-weekly-retro --format markdown -o retro.md
```

## Clipboard Integration

Copy results directly to your clipboard:

```bash
# Copy brief to clipboard
kgc-daily-brief -c

# Copy query results (requires --format json or markdown)
kgc-query -t all_features -f json -c
```

**Platform Requirements:**
- macOS: Built-in `pbcopy` (no setup needed)
- Linux: Install `xclip` or `xsel`

```bash
# Ubuntu/Debian
sudo apt-get install xclip

# CentOS/RHEL
sudo yum install xclip
```

## Getting Help

Every command has comprehensive help:

```bash
kgc-daily-brief --help
kgc-weekly-retro --help
kgc-feature-list --help
kgc-query --help
kgc-config --help
```

For subcommands:

```bash
kgc-config exclude --help
kgc-config capability --help
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/cli/ -v

# Specific test file
pytest tests/cli/test_daily_brief.py -v

# With coverage
pytest tests/cli/ --cov=kgcl.cli --cov-report=html
```

## Troubleshooting

### Command not found

```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Verify installation
which kgc-daily-brief
```

### Import errors

```bash
# Reinstall dependencies
uv sync --python 3.12
```

### Configuration issues

```bash
# Reset to defaults
kgc-config reset

# Reinitialize
kgc-config init
```

### SPARQL endpoint errors

```bash
# Check endpoint configuration
kgc-config get sparql_endpoint

# Update if needed
kgc-config set sparql_endpoint http://localhost:3030/kgcl/sparql
```

## Examples

### Generate Monthly Report

```bash
#!/bin/bash
# monthly-report.sh

DATE=$(date +%Y%m%d)
OUTPUT_DIR="reports/$DATE"
mkdir -p "$OUTPUT_DIR"

# Generate 30-day retrospective
kgc-weekly-retro \
  --days 30 \
  --include-metrics \
  -o "$OUTPUT_DIR/monthly-retro.md"

# Export feature catalog
kgc-feature-list \
  --format csv \
  -o "$OUTPUT_DIR/features.csv"

# Export all queries
for template in all_features recent_events metrics_summary code_changes; do
  kgc-query \
    -t "$template" \
    -f json \
    -o "$OUTPUT_DIR/$template.json"
done

echo "Reports generated in $OUTPUT_DIR"
```

### Daily Automation

```bash
#!/bin/bash
# daily-automation.sh

# Add to cron: 0 9 * * * /path/to/daily-automation.sh

DATE=$(date +%Y-%m-%d)
OUTPUT="daily-briefs/brief-$DATE.md"

kgc-daily-brief \
  --lookback 1 \
  --verbose \
  -o "$OUTPUT"

# Optional: Send to email, Slack, etc.
```

### Feature Analysis

```bash
#!/bin/bash
# analyze-features.sh

# Get all testing features
kgc-feature-list \
  --category testing \
  --format json \
  > testing-features.json

# Get all quality features
kgc-feature-list \
  --category quality \
  --format json \
  > quality-features.json

# Run custom analysis query
kgc-query -q "
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?category (COUNT(?feature) as ?count)
WHERE {
  ?feature a kgcl:Feature ;
          kgcl:category ?category .
}
GROUP BY ?category
ORDER BY DESC(?count)
" -f json > feature-distribution.json

echo "Analysis complete"
```

## Advanced Usage

### Piping and Filtering

```bash
# Get feature names only
kgc-feature-list -f json | jq '.[] | .name'

# Count features by category
kgc-feature-list -f json | jq 'group_by(.category) | map({category: .[0].category, count: length})'

# Filter recent events
kgc-query -t recent_events -f json | jq '.[] | select(.timestamp > "2024-01-01")'
```

### Batch Operations

```bash
# Generate briefs for last 7 days
for i in {1..7}; do
  DATE=$(date -d "$i days ago" +%Y-%m-%d)
  kgc-daily-brief \
    --date "$DATE" \
    -o "briefs/brief-$DATE.md"
done
```

### Configuration Profiles

```bash
# Create development profile
kgc-config set sparql_endpoint http://localhost:3030/dev/sparql
kgc-config set default_model llama3.2
kgc-config capability disable telemetry

# Save configuration
cp ~/.config/kgcl/config.json ~/.config/kgcl/config-dev.json

# Create production profile
kgc-config set sparql_endpoint http://prod-server:3030/kgcl/sparql
kgc-config set default_model llama3.3
kgc-config capability enable telemetry

cp ~/.config/kgcl/config.json ~/.config/kgcl/config-prod.json

# Swap profiles
# cp ~/.config/kgcl/config-dev.json ~/.config/kgcl/config.json
```

## Next Steps

1. Explore the full [CLI Reference](cli-reference.md)
2. Read the [Implementation Summary](CLI_IMPLEMENTATION_SUMMARY.md)
3. Check out example workflows in the main documentation
4. Contribute improvements via pull requests

## Resources

- **User Guide**: `docs/cli-reference.md`
- **Implementation Details**: `docs/CLI_IMPLEMENTATION_SUMMARY.md`
- **Source Code**: `src/kgcl/cli/`
- **Tests**: `tests/cli/`
- **Issues**: Report bugs and feature requests on GitHub

Happy querying! 🚀
