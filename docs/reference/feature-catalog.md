# KGCL Feature Catalog

## Table of Contents

- [Overview](#overview)
- [Feature Organization](#feature-organization)
- [Productivity Features](#productivity-features)
- [Browsing Features](#browsing-features)
- [Calendar Features](#calendar-features)
- [Communication Features](#communication-features)
- [Development Features](#development-features)
- [Custom Feature Templates](#custom-feature-templates)
- [Aggregation Functions](#aggregation-functions)
- [Time Windows](#time-windows)
- [Feature Examples](#feature-examples)
- [Adding New Features](#adding-new-features)

## Overview

Features are structured representations of user activities derived from raw events. They provide meaningful aggregations and transformations that enable LLM reasoning about productivity, focus, and work patterns.

### Feature Lifecycle

```
Raw Events → Feature Template → SPARQL Query → Aggregation → Feature Instance
```

### Feature Components

1. **Template Definition**: SHACL shape defining input properties and output structure
2. **Materialization Logic**: SPARQL query or aggregation function
3. **Time Window**: Temporal scope (hourly, daily, weekly)
4. **Storage**: RDF triples in UNRDF engine
5. **Consumption**: Used by DSPy signatures for reasoning

## Feature Organization

### By Category

| Category | Count | Description |
|----------|-------|-------------|
| Productivity | 12 | App usage, focus, context switching |
| Browsing | 8 | Web activity, domains, search patterns |
| Calendar | 6 | Meetings, scheduling, time blocking |
| Communication | 5 | Email, Slack, messaging patterns |
| Development | 9 | Code commits, PR reviews, build times |
| Custom | ∞ | User-defined templates |

### By Data Source

| Source | Features | Collection Method |
|--------|----------|-------------------|
| AppKit | app_usage_time, frontmost_app_history, context_switches | PyObjC polling |
| WebKit | browser_domains, url_visits, search_queries | Browser history API |
| EventKit | meeting_count, calendar_time, scheduling_patterns | Calendar API |
| Git | commit_count, code_changes, pr_activity | File system monitoring |

### By Temporal Granularity

| Window | Features | Use Case |
|--------|----------|----------|
| Real-time | current_app, active_window | Live monitoring |
| Hourly | app_usage_hourly, context_switches_hourly | Intraday patterns |
| Daily | daily_app_usage, daily_meeting_count | Daily briefs |
| Weekly | weekly_productivity, weekly_focus_score | Weekly retrospectives |
| Monthly | monthly_trends, habit_analysis | Long-term insights |

## Productivity Features

### app_usage_time

**Description**: Total time spent in each application

**SHACL Definition**:
```turtle
@prefix kgcl: <http://kgcl.io/ontology#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

kgcl:AppUsageTimeShape
  a sh:NodeShape ;
  rdfs:comment "Total time spent per application in a time window" ;
  sh:targetClass kgcl:AppUsageTimeFeature ;
  sh:property [
    sh:path kgcl:appName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
    rdfs:comment "Application name (e.g., 'Chrome', 'VSCode')" ;
  ] ;
  sh:property [
    sh:path kgcl:bundleId ;
    sh:datatype xsd:string ;
    rdfs:comment "macOS bundle identifier" ;
  ] ;
  sh:property [
    sh:path kgcl:totalSeconds ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
    rdfs:comment "Total seconds the app was active" ;
  ] ;
  sh:property [
    sh:path kgcl:windowStart ;
    sh:datatype xsd:dateTime ;
    rdfs:comment "Start of time window" ;
  ] ;
  sh:property [
    sh:path kgcl:windowEnd ;
    sh:datatype xsd:dateTime ;
    rdfs:comment "End of time window" ;
  ] ;
  sh:property [
    sh:path kgcl:category ;
    sh:datatype xsd:string ;
    rdfs:comment "App category (productivity, communication, entertainment)" ;
  ] .
```

**Example Values**:
```json
{
  "appName": "Visual Studio Code",
  "bundleId": "com.microsoft.VSCode",
  "totalSeconds": 12600,
  "windowStart": "2024-01-15T00:00:00Z",
  "windowEnd": "2024-01-15T23:59:59Z",
  "category": "productivity"
}
```

**Interpretation**: User spent 3.5 hours in VS Code on 2024-01-15

### context_switches

**Description**: Number of app switches within a time window

**SHACL Definition**:
```turtle
kgcl:ContextSwitchShape
  a sh:NodeShape ;
  rdfs:comment "Context switch frequency indicating multitasking level" ;
  sh:targetClass kgcl:ContextSwitchFeature ;
  sh:property [
    sh:path kgcl:switchCount ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
    rdfs:comment "Number of app switches" ;
  ] ;
  sh:property [
    sh:path kgcl:avgDurationBetweenSwitches ;
    sh:datatype xsd:float ;
    rdfs:comment "Average seconds between switches" ;
  ] ;
  sh:property [
    sh:path kgcl:mostFrequentTransition ;
    sh:datatype xsd:string ;
    rdfs:comment "Most common app-to-app transition (e.g., 'VSCode → Chrome')" ;
  ] .
```

**Example Values**:
```json
{
  "switchCount": 45,
  "avgDurationBetweenSwitches": 180.0,
  "mostFrequentTransition": "VSCode → Chrome"
}
```

**Interpretation**: 45 context switches with average 3-minute focus per app. Primary workflow: coding in VSCode, then researching in Chrome.

### focus_time

**Description**: Periods of uninterrupted work in a single application

**SHACL Definition**:
```turtle
kgcl:FocusTimeShape
  a sh:NodeShape ;
  rdfs:comment "Continuous focus periods without app switching" ;
  sh:targetClass kgcl:FocusTimeFeature ;
  sh:property [
    sh:path kgcl:appName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:focusDurationSeconds ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
    rdfs:comment "Duration of continuous focus" ;
  ] ;
  sh:property [
    sh:path kgcl:startTime ;
    sh:datatype xsd:dateTime ;
  ] ;
  sh:property [
    sh:path kgcl:endTime ;
    sh:datatype xsd:dateTime ;
  ] ;
  sh:property [
    sh:path kgcl:qualityScore ;
    sh:datatype xsd:integer ;
    sh:minInclusive 1 ;
    sh:maxInclusive 10 ;
    rdfs:comment "Focus quality score based on duration and consistency" ;
  ] .
```

**Example Values**:
```json
{
  "appName": "VSCode",
  "focusDurationSeconds": 5400,
  "startTime": "2024-01-15T10:00:00Z",
  "endTime": "2024-01-15T11:30:00Z",
  "qualityScore": 9
}
```

**Interpretation**: High-quality 90-minute focus session in VSCode from 10:00-11:30 AM.

### productivity_score

**Description**: Overall productivity score derived from multiple signals

**SHACL Definition**:
```turtle
kgcl:ProductivityScoreShape
  a sh:NodeShape ;
  rdfs:comment "Composite productivity score (1-10)" ;
  sh:targetClass kgcl:ProductivityScoreFeature ;
  sh:property [
    sh:path kgcl:score ;
    sh:datatype xsd:integer ;
    sh:minInclusive 1 ;
    sh:maxInclusive 10 ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:focusComponent ;
    sh:datatype xsd:float ;
    rdfs:comment "Contribution from focus time (0.0-1.0)" ;
  ] ;
  sh:property [
    sh:path kgcl:outputComponent ;
    sh:datatype xsd:float ;
    rdfs:comment "Contribution from measurable output (commits, PRs)" ;
  ] ;
  sh:property [
    sh:path kgcl:contextComponent ;
    sh:datatype xsd:float ;
    rdfs:comment "Inverse contribution from context switches" ;
  ] .
```

**Example Values**:
```json
{
  "score": 8,
  "focusComponent": 0.85,
  "outputComponent": 0.75,
  "contextComponent": 0.80
}
```

**Interpretation**: Strong productivity day (score 8/10) driven by good focus (0.85), solid output (0.75), and low context switching (0.80).

### idle_time

**Description**: Periods with no user activity

**Example Values**:
```json
{
  "totalIdleSeconds": 3600,
  "longestIdlePeriodSeconds": 1800,
  "idlePeriodsCount": 3
}
```

**Interpretation**: 1 hour total idle time with longest break being 30 minutes.

### active_hours

**Description**: Hours of the day with user activity

**Example Values**:
```json
{
  "startHour": 9,
  "endHour": 18,
  "totalActiveHours": 9,
  "peakHour": 10
}
```

**Interpretation**: Active from 9 AM to 6 PM (9 hours), most productive at 10 AM.

## Browsing Features

### browser_domain_visits

**Description**: Count of visits to each web domain

**SHACL Definition**:
```turtle
kgcl:BrowserDomainVisitsShape
  a sh:NodeShape ;
  rdfs:comment "Frequency of visits to web domains" ;
  sh:targetClass kgcl:BrowserDomainVisitsFeature ;
  sh:property [
    sh:path kgcl:domain ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
    rdfs:comment "Domain name (e.g., 'github.com')" ;
  ] ;
  sh:property [
    sh:path kgcl:visitCount ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:totalDurationSeconds ;
    sh:datatype xsd:integer ;
  ] ;
  sh:property [
    sh:path kgcl:uniqueUrls ;
    sh:datatype xsd:integer ;
    rdfs:comment "Number of unique URLs visited on domain" ;
  ] .
```

**Example Values**:
```json
{
  "domain": "github.com",
  "visitCount": 45,
  "totalDurationSeconds": 4320,
  "uniqueUrls": 12
}
```

**Interpretation**: 45 visits to GitHub, 1.2 hours total, across 12 different pages/repos.

### search_queries

**Description**: Search queries performed

**Example Values**:
```json
{
  "query": "python asyncio best practices",
  "engine": "google",
  "timestamp": "2024-01-15T14:30:00Z",
  "resultsClicked": 3
}
```

**Interpretation**: Searched for Python asyncio information, clicked 3 results.

### url_visit_patterns

**Description**: Temporal patterns in URL visits

**Example Values**:
```json
{
  "url": "https://github.com/user/repo",
  "visitsByHour": {
    "10": 5,
    "14": 8,
    "16": 3
  },
  "avgVisitDuration": 180,
  "returnVisitor": true
}
```

**Interpretation**: Frequently returns to this repo, primarily in early afternoon (14:00 peak).

### top_websites_by_category

**Description**: Top domains grouped by category

**Example Values**:
```json
{
  "development": ["github.com", "stackoverflow.com", "docs.python.org"],
  "news": ["news.ycombinator.com", "reddit.com"],
  "social": ["twitter.com", "linkedin.com"]
}
```

**Interpretation**: Primary categories are development tools, with some news and social.

## Calendar Features

### meeting_count

**Description**: Number of calendar meetings

**SHACL Definition**:
```turtle
kgcl:MeetingCountShape
  a sh:NodeShape ;
  rdfs:comment "Count and duration of calendar meetings" ;
  sh:targetClass kgcl:MeetingCountFeature ;
  sh:property [
    sh:path kgcl:meetingCount ;
    sh:datatype xsd:integer ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:totalMeetingMinutes ;
    sh:datatype xsd:integer ;
  ] ;
  sh:property [
    sh:path kgcl:avgMeetingDuration ;
    sh:datatype xsd:integer ;
  ] ;
  sh:property [
    sh:path kgcl:longestMeetingMinutes ;
    sh:datatype xsd:integer ;
  ] .
```

**Example Values**:
```json
{
  "meetingCount": 5,
  "totalMeetingMinutes": 240,
  "avgMeetingDuration": 48,
  "longestMeetingMinutes": 90
}
```

**Interpretation**: 5 meetings totaling 4 hours, average 48 minutes each, longest was 90 minutes.

### meeting_patterns

**Description**: Patterns in meeting scheduling

**Example Values**:
```json
{
  "preferredDayOfWeek": "Tuesday",
  "preferredTimeSlot": "10:00-11:00",
  "backToBackMeetings": 2,
  "meetingFreeBlocks": ["09:00-10:00", "14:00-16:00"]
}
```

**Interpretation**: Prefers Tuesday mornings for meetings, has focus blocks 9-10 AM and 2-4 PM.

### calendar_density

**Description**: Percentage of day blocked by meetings

**Example Values**:
```json
{
  "densityPercent": 45.0,
  "busyHours": ["10", "11", "14", "15"],
  "freeHours": ["09", "12", "13", "16", "17"]
}
```

**Interpretation**: 45% of work day in meetings, concentrated in mornings and mid-afternoon.

## Communication Features

### email_volume

**Description**: Email sent and received counts

**Example Values**:
```json
{
  "received": 87,
  "sent": 23,
  "avgResponseTime": 120,
  "peakEmailHour": 10
}
```

**Interpretation**: Received 87 emails, sent 23, average 2-hour response time, peak at 10 AM.

### slack_activity

**Description**: Slack message and channel activity

**Example Values**:
```json
{
  "messagesSent": 145,
  "messagesReceived": 234,
  "activeChannels": ["#engineering", "#general", "#random"],
  "avgResponseTime": 15
}
```

**Interpretation**: Active Slack user (145 sent, 234 received), quick 15-minute avg response time.

## Development Features

### commit_count

**Description**: Git commits by repository

**Example Values**:
```json
{
  "repository": "kgcl",
  "commitCount": 12,
  "filesChanged": 35,
  "linesAdded": 450,
  "linesDeleted": 120
}
```

**Interpretation**: 12 commits to kgcl repo, added 450 lines, deleted 120, touched 35 files.

### pr_activity

**Description**: Pull request reviews and creation

**Example Values**:
```json
{
  "prsCreated": 3,
  "prsReviewed": 7,
  "avgReviewTime": 3600,
  "commentsMade": 45
}
```

**Interpretation**: Created 3 PRs, reviewed 7, average 1-hour review time, 45 comments.

### build_times

**Description**: CI/CD build duration and success rate

**Example Values**:
```json
{
  "totalBuilds": 25,
  "successfulBuilds": 23,
  "avgBuildTime": 420,
  "longestBuildTime": 720
}
```

**Interpretation**: 25 builds, 92% success rate, average 7-minute build, longest 12 minutes.

## Custom Feature Templates

### Creating a Template

1. **Define SHACL Shape**:

```turtle
@prefix kgcl: <http://kgcl.io/ontology#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

kgcl:CodeReviewQualityShape
  a sh:NodeShape ;
  rdfs:comment "Quality metrics for code reviews" ;
  sh:targetClass kgcl:CodeReviewQualityFeature ;
  sh:property [
    sh:path kgcl:reviewId ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path kgcl:commentsCount ;
    sh:datatype xsd:integer ;
  ] ;
  sh:property [
    sh:path kgcl:qualityScore ;
    sh:datatype xsd:integer ;
    sh:minInclusive 1 ;
    sh:maxInclusive 10 ;
  ] ;
  sh:property [
    sh:path kgcl:thoroughnessScore ;
    sh:datatype xsd:float ;
  ] .
```

2. **Implement Materialization Logic**:

```python
from kgcl.ingestion import FeatureMaterializer

class CodeReviewQualityMaterializer(FeatureMaterializer):
    def materialize(self, window_start, window_end):
        # Query raw events
        query = """
        PREFIX kgcl: <http://kgcl.io/ontology#>
        SELECT ?review ?comments
        WHERE {
          ?review a kgcl:CodeReviewEvent ;
                  kgcl:timestamp ?ts ;
                  kgcl:commentCount ?comments .
          FILTER(?ts >= ?start && ?ts <= ?end)
        }
        """

        # Compute quality scores
        features = []
        for review, comments in results:
            quality_score = self.compute_quality(review, comments)
            thoroughness = self.compute_thoroughness(review)

            feature = {
                "reviewId": review,
                "commentsCount": comments,
                "qualityScore": quality_score,
                "thoroughnessScore": thoroughness
            }
            features.append(feature)

        return features
```

3. **Register Template**:

```python
from kgcl.ingestion import register_feature_template

register_feature_template(
    name="code_review_quality",
    shape_path="ontology/code_review_quality.ttl",
    materializer=CodeReviewQualityMaterializer(),
    enabled=True
)
```

## Aggregation Functions

### Built-in Aggregations

| Function | Description | Example |
|----------|-------------|---------|
| `SUM` | Sum values | Total app usage time |
| `COUNT` | Count occurrences | Number of meetings |
| `AVG` | Average value | Average focus duration |
| `MAX` | Maximum value | Longest meeting |
| `MIN` | Minimum value | Shortest context switch |
| `GROUP_CONCAT` | Concatenate strings | List of visited domains |

### Custom Aggregations

```python
from kgcl.ingestion import AggregationFunction

class ProductivityScoreAggregation(AggregationFunction):
    def aggregate(self, events):
        focus_score = self.compute_focus_score(events)
        output_score = self.compute_output_score(events)
        context_score = self.compute_context_score(events)

        return {
            "score": int((focus_score + output_score + context_score) / 3 * 10),
            "focusComponent": focus_score,
            "outputComponent": output_score,
            "contextComponent": context_score
        }
```

## Time Windows

### Window Definitions

| Window | Duration | Use Case | Example |
|--------|----------|----------|---------|
| Instant | 0s | Current state | `current_app` |
| Minute | 60s | Real-time metrics | `recent_activity` |
| Hourly | 3600s | Intraday patterns | `app_usage_hourly` |
| Daily | 86400s | Daily summaries | `daily_productivity` |
| Weekly | 604800s | Week reviews | `weekly_focus` |
| Monthly | 2592000s | Trend analysis | `monthly_patterns` |

### Sliding Windows

```python
from kgcl.ingestion import SlidingWindow

# 1-hour window sliding every 15 minutes
window = SlidingWindow(
    size=3600,  # 1 hour
    slide=900   # 15 minutes
)

features = materializer.materialize_sliding(window)
```

### Tumbling Windows

```python
from kgcl.ingestion import TumblingWindow

# Non-overlapping daily windows
window = TumblingWindow(size=86400)  # 24 hours

features = materializer.materialize_tumbling(window)
```

## Feature Examples

### Complete Example: Daily Productivity Analysis

**Features Used**:
- `app_usage_time`
- `context_switches`
- `focus_time`
- `meeting_count`
- `productivity_score`

**Sample Data**:
```json
{
  "date": "2024-01-15",
  "app_usage": {
    "VSCode": 12600,
    "Chrome": 8100,
    "Slack": 3600
  },
  "context_switches": 45,
  "focus_sessions": [
    {"app": "VSCode", "duration": 5400, "quality": 9},
    {"app": "VSCode", "duration": 3600, "quality": 7}
  ],
  "meetings": {
    "count": 3,
    "total_minutes": 120
  },
  "productivity_score": {
    "score": 8,
    "components": {
      "focus": 0.85,
      "output": 0.75,
      "context": 0.80
    }
  }
}
```

**LLM Interpretation** (via DSPy):
```
Your January 15th was highly productive (score: 8/10). You spent 3.5 hours in
deep work with VSCode, demonstrating strong focus. Context switching was
manageable (45 switches), and meeting time was well-balanced at 2 hours total.

Key Insight: Your morning focus session (90 minutes, quality 9/10) was
exceptional. Consider protecting this time slot in the future.
```

## Adding New Features

### Step-by-Step Guide

1. **Identify Data Source**:
   - Existing events? Query UNRDF
   - New source? Implement collector first

2. **Design Feature Structure**:
   - What properties are needed?
   - What time window makes sense?
   - How will it be aggregated?

3. **Create SHACL Shape**:
   ```bash
   # Edit ontology file
   vim ontology/custom_features.ttl
   ```

4. **Implement Materializer**:
   ```bash
   # Create materializer
   vim src/kgcl/ingestion/materializers/custom.py
   ```

5. **Test Feature**:
   ```bash
   pytest tests/ingestion/test_custom_feature.py -v
   ```

6. **Generate DSPy Signature**:
   ```bash
   python -m kgcl.ttl2dspy generate \
     ontology/custom_features.ttl \
     src/generated/
   ```

7. **Use in Reasoning**:
   ```python
   from generated.signatures import CustomFeatureSignature
   import dspy

   predictor = dspy.Predict(CustomFeatureSignature)
   result = predictor(feature_data=...)
   ```

### Best Practices

1. **Property Naming**: Use camelCase for consistency
2. **Data Types**: Use appropriate XSD types (string, integer, float, dateTime)
3. **Required Fields**: Mark essential properties with `sh:minCount 1`
4. **Documentation**: Add `rdfs:comment` to all properties
5. **Validation**: Define constraints with `sh:minInclusive`, `sh:pattern`, etc.
6. **Categories**: Group related features in same namespace
7. **Versioning**: Include schema version in shape URIs

### Feature Quality Checklist

- [ ] SHACL shape validates correctly
- [ ] Materializer produces expected output
- [ ] Feature values are interpretable
- [ ] Time window is appropriate
- [ ] Aggregation logic is correct
- [ ] Unit tests pass
- [ ] DSPy signature generates correctly
- [ ] LLM can reason about the feature
- [ ] Documentation is complete
- [ ] Performance is acceptable

## Feature Discovery

### List All Features

```bash
# List all available features
kgc-feature-list

# List by category
kgc-feature-list --category productivity

# Search features
kgc-feature-list --search "focus"

# Show detailed info
kgc-feature-list --verbose
```

### Query Feature Instances

```bash
# Query all instances
kgc-query --query "
PREFIX kgcl: <http://kgcl.io/ontology#>
SELECT ?feature ?timestamp
WHERE {
  ?feature a kgcl:FeatureInstance ;
           kgcl:timestamp ?timestamp .
}
ORDER BY DESC(?timestamp)
LIMIT 100
"

# Query specific feature type
kgc-query --template feature_instances --type app_usage_time
```

### Feature Lineage

```bash
# Trace feature provenance
kgc-query --query "
PREFIX kgcl: <http://kgcl.io/ontology#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?feature ?source ?agent ?timestamp
WHERE {
  ?feature a kgcl:FeatureInstance ;
           prov:wasDerivedFrom ?source ;
           prov:wasGeneratedBy ?agent ;
           prov:generatedAtTime ?timestamp .
}
"
```

## Further Reading

- [System Architecture](./SYSTEM_ARCHITECTURE.md) - How features fit in the system
- [API Reference](./API_REFERENCE.md#feature-api) - Feature API documentation
- [Extensibility Guide](./EXTENSIBILITY.md) - Creating custom features
- [Reasoning Pipeline](./REASONING_PIPELINE.md) - How features are used in LLM reasoning
