# CLI Reference

Command-line interface for KGCL Hybrid Engine.

## Overview

The CLI uses a noun-verb pattern:

```bash
kgcl <noun> <verb> [options]
```

## Commands

### Engine Commands

#### `kgcl engine run`

Run workflow to completion.

```bash
kgcl engine run --topology workflow.ttl --max-ticks 100
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--topology`, `-t` | PATH | Required | Turtle file with workflow topology |
| `--max-ticks`, `-m` | INT | 100 | Maximum ticks before timeout |
| `--output`, `-o` | PATH | stdout | Output file for results |
| `--format`, `-f` | TEXT | json | Output format (json, turtle, table) |

#### `kgcl engine tick`

Execute single physics tick.

```bash
kgcl engine tick --topology workflow.ttl
```

#### `kgcl engine status`

Show engine status.

```bash
kgcl engine status
```

---

### Store Commands

#### `kgcl store load`

Load RDF data into store.

```bash
kgcl store load --file data.ttl --format turtle
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--file`, `-f` | PATH | Required | RDF file to load |
| `--format` | TEXT | turtle | Input format (turtle, n3, trig) |
| `--store`, `-s` | PATH | memory | Store path (or "memory") |

#### `kgcl store dump`

Dump store contents.

```bash
kgcl store dump --output state.ttl --format turtle
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output`, `-o` | PATH | stdout | Output file |
| `--format`, `-f` | TEXT | turtle | Output format |
| `--store`, `-s` | PATH | memory | Store path |

#### `kgcl store query`

Execute SPARQL query.

```bash
kgcl store query "SELECT ?s ?status WHERE { ?s kgc:status ?status }"
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--store`, `-s` | PATH | memory | Store path |
| `--format`, `-f` | TEXT | table | Output format (table, json, csv) |

#### `kgcl store clear`

Clear all triples from store.

```bash
kgcl store clear --store /data/workflow
```

---

### Task Commands

#### `kgcl task list`

List all tasks and statuses.

```bash
kgcl task list --topology workflow.ttl
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--topology`, `-t` | PATH | Required | Topology file |
| `--format`, `-f` | TEXT | table | Output format |

#### `kgcl task status`

Get status of specific task.

```bash
kgcl task status urn:task:A --topology workflow.ttl
```

#### `kgcl task activate`

Manually activate a task.

```bash
kgcl task activate urn:task:A --topology workflow.ttl
```

#### `kgcl task complete`

Mark task as completed.

```bash
kgcl task complete urn:task:A --topology workflow.ttl
```

---

### Physics Commands

#### `kgcl physics list`

List available WCP patterns.

```bash
kgcl physics list
kgcl physics list --category "Basic Control Flow"
kgcl physics list --verb Transmute
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--category`, `-c` | TEXT | all | Filter by category |
| `--verb`, `-v` | TEXT | all | Filter by KGC verb |

#### `kgcl physics show`

Show details of specific pattern.

```bash
kgcl physics show 1
kgcl physics show --name Sequence
```

#### `kgcl physics rules`

Output N3 rules.

```bash
kgcl physics rules --patterns 1,2,3 --output rules.n3
kgcl physics rules --all --output complete.n3
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--patterns`, `-p` | TEXT | all | Comma-separated pattern numbers |
| `--all` | FLAG | false | Include all 43 patterns |
| `--output`, `-o` | PATH | stdout | Output file |

---

### System Commands

#### `kgcl version`

Show version information.

```bash
kgcl version
```

#### `kgcl check`

Check system dependencies.

```bash
kgcl check
```

Output:
```
✓ Python 3.12.0
✓ PyOxigraph 0.3.22
✓ EYE Reasoner 23.0.1
✗ Ollama (not found)
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KGCL_STORE_PATH` | Default store path |
| `KGCL_LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) |
| `KGCL_EYE_TIMEOUT` | EYE reasoner timeout in seconds |

## Examples

### Basic Workflow Execution

```bash
# Create topology file
cat > workflow.ttl << 'EOF'
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:A> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:task:B> a yawl:Task ; kgc:status "Pending" .
EOF

# Run to completion
kgcl engine run -t workflow.ttl

# Check task statuses
kgcl task list -t workflow.ttl
```

### Interactive Debugging

```bash
# Load topology
kgcl store load -f workflow.ttl

# Execute single tick
kgcl engine tick

# Query state
kgcl store query "SELECT ?task ?status WHERE { ?task kgc:status ?status }"

# Execute another tick
kgcl engine tick

# Dump final state
kgcl store dump -o final.ttl
```

### Pattern Exploration

```bash
# List all cancellation patterns
kgcl physics list --verb Void

# Show WCP-19 details
kgcl physics show 19

# Export sequence and parallel split rules
kgcl physics rules -p 1,2 -o basic.n3
```
