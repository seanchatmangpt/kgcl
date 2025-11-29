# Chapter 2: The Failure of Piecemeal Porting—Empirical Evidence

[← Previous: Chapter 1](./chapter-1-introduction.md) | [Back to Contents](./README.md) | [Next: Chapter 3 →](./chapter-3-challenges.md)

---

## 2.1 The Manual Porting Process

Our initial approach followed software engineering best practices:

1. **Package Selection**: Choose cohesive Java packages (e.g., `org.yawlfoundation.yawl.elements`)
2. **Class Translation**: Manually translate classes to Python
3. **Method Implementation**: Port method bodies with equivalent logic
4. **Test Verification**: Run Python tests against expected behavior
5. **Integration**: Merge to main branch, move to next package

This approach succeeded for simple data transfer objects (DTOs) and utility classes. It catastrophically failed for complex stateful classes with deep inheritance hierarchies.

## 2.2 Quantitative Failure Metrics

Six months of effort produced:

| Metric | Target | Achieved | Gap |
|--------|--------|----------|-----|
| **Classes Ported** | 858 | 130 | 728 (85% missing) |
| **Methods Implemented** | ~2,500 | ~600 | ~1,900 (76% missing) |
| **Core Functionality** | 100% | 12% | 88% incomplete |
| **Critical Classes Complete** | 7 | 0 | 7 (100% partial) |

**Critical Class Gaps** (from lies detector analysis):
- **YTask**: 240/242 methods missing (98.8% gap)
- **YWorkItem**: 229/234 methods missing (98.3% gap)
- **YNetRunner**: 173/182 methods missing (95.1% gap)
- **YCondition**: 21/22 methods missing (95.5% gap)
- **YDecomposition**: 65/74 methods missing (87.8% gap)
- **YEngine**: 148/172 methods missing (86.0% gap)
- **YVariable**: 50/50 methods missing (100% gap, naming mismatch)

## 2.3 Qualitative Failure Patterns

### 2.3.1 Implementation Lies

Lean Six Sigma quality gates detected **54 implementation lies**:

**Deferred Work** (11 instances):
```python
# TODO: Replace with xml.jdom_util.encode_escapes when available
escaped = html.escape(core)

# Stub - would need XML serialization
return Document()
```

**Temporal Deferral** (11 instances):
```python
# For now, return -1 to indicate not found
# Note: Would need persistence manager - using None for now
```

**Speculative Scaffolding** (29 empty exception classes):
```python
class EYENotFoundError(Exception):
    pass  # No docstring, no message handling
```

These "lies" indicate developers **knew** the implementation was incomplete but shipped it anyway—a symptom of overwhelming complexity.

### 2.3.2 Architectural Misalignment

Java's inheritance-heavy design clashed with Pythonic composition:

**Java Pattern**:
```java
class YTask extends YExternalNetElement
              implements YWorkItemProvider, Cancellable {
    private YNet _net;
    private YDecomposition _decomposition;
    // 242 methods coordinating state across hierarchy
}
```

**Python Attempt**:
```python
class YTask(YExternalNetElement):  # Lost YWorkItemProvider, Cancellable
    _net: YNet | None = None
    _decomposition: YDecomposition | None = None
    # Only 2 methods implemented; 240 missing
```

The Python version lost multiple interfaces, dropped state coordination, and failed to implement lifecycle methods. The gap wasn't just **quantity** (240 missing methods) but **semantics** (lost behavioral contracts).

### 2.3.3 Naming Convention Hell

Java's camelCase vs. Python's snake_case created systematic false negatives:

```python
# Java: getDefaultValue()
# Python: get_default_value()
# Gap Analyzer: Reports as "missing" (string mismatch)
```

The gap analyzer reported **YVariable as 100% incomplete** despite having 40+ methods implemented with correct behavior but snake_case naming. This false negative masked real progress and demoralized developers.

## 2.4 Root Cause Analysis

Why did piecemeal porting fail? Five factors emerged:

**1. Cognitive Overload**: Developers couldn't maintain mental models of 240-method classes
**2. Dependency Hell**: Methods depended on other not-yet-ported methods
**3. Test Insufficiency**: Java tests didn't translate directly to Python test factories
**4. Behavioral Opacity**: Reading Java code doesn't reveal runtime behavior
**5. No Progress Visibility**: Gap detection was too coarse (class-level, not method-level)

## 2.5 The Breaking Point

After detecting the 54th implementation lie, we held a project retrospective. The consensus: **"We are building a house of cards. Each new class depends on incomplete foundations. We need systematic guarantees, not heroic effort."**

This realization prompted a fundamental pivot from manual translation to ontology-driven automation.

### The Graph Problem Insight

The critical insight was recognizing that cross-language migration is a **graph problem**, not a linear sequence. Dependencies form a directed acyclic graph (DAG), and manual porting attempts a topological sort without visibility into the full graph structure.

**Formal Model**:
```
Let G = (V, E) be the code dependency graph:
  V = set of all classes/methods
  E = set of dependencies (method calls, inheritance, composition)

Manual porting attempts to process vertices in arbitrary order.
Expected failures: F(n) = O(n²) where n = |V|

Why? Each unported dependency creates a potential failure point.
With 858 classes averaging 15 dependencies each:
  Expected failures ≈ 858 × 15 × 0.1 = 1,287 integration failures

Observed: 54 documented lies + ~200 silent failures = ~254 actual failures
(Lower than expected due to developers working around missing dependencies)
```

This mathematical framing made clear why manual approaches were doomed at this scale.

---

[← Previous: Chapter 1](./chapter-1-introduction.md) | [Back to Contents](./README.md) | [Next: Chapter 3 →](./chapter-3-challenges.md)
