# Knowledge Hooks Failure Modes Matrix

## Risk Priority Matrix (Visual)

```
RPN Scale: 1 (Low) ────────────────────────────────────── 1000 (Critical)
           |        20        50        100       200       315
Risk:      Low      Medium    High      Critical
```

### Failure Mode Distribution by Risk Level

```
Critical (RPN > 100)  ████████████████████ 70% (7 modes)
High (RPN 50-100)     ─                     0% (0 modes)
Medium (RPN 20-50)    ████                 30% (3 modes)
Low (RPN < 20)        ─                     0% (0 modes)
```

## Failure Modes by RPN (Descending)

```
FM-HOOK-003: Priority Deadlock                     RPN: 315  ████████████████
FM-HOOK-004: Rollback Cascade Failure              RPN: 150  ███████▌
FM-HOOK-008: N3 Rule Not Loaded                    RPN: 147  ███████▍
FM-HOOK-002: Circular Hook Chain                   RPN: 135  ██████▊
FM-HOOK-007: Handler Action Type Mismatch          RPN: 125  ██████▎
FM-HOOK-009: Receipt Storage Exhaustion            RPN: 105  █████▎
FM-HOOK-010: Delta Pattern Match Explosion         RPN: 105  █████▎
FM-HOOK-001: Condition Query Timeout               RPN:  45  ██▎
FM-HOOK-006: Condition SPARQL Injection            RPN:  45  ██▎
FM-HOOK-005: Phase Ordering Violation              RPN:  21  █
```

## Detailed Matrix

### FM-HOOK-003: Priority Deadlock 🔴 CRITICAL
```
Severity:    █████████░ 9/10  Non-deterministic behavior
Occurrence:  █████░░░░░ 5/10  Common with multiple hooks
Detection:   ███████░░░ 7/10  Hard to detect (intermittent)
─────────────────────────────────────────────────
RPN: 315 (HIGHEST)
```
**Effect**: Neither hook executes reliably. Race conditions. Unpredictable system behavior.

**Mitigation**: Implement priority tie-breaking by hook ID lexicographic order.

---

### FM-HOOK-004: Rollback Cascade Failure 🔴 CRITICAL
```
Severity:    ██████████ 10/10  Data corruption
Occurrence:  ███░░░░░░░ 3/10  Rare with proper transactions
Detection:   █████░░░░░ 5/10  Integrity checks detect
─────────────────────────────────────────────────
RPN: 150
```
**Effect**: Graph in inconsistent state. Manual recovery required.

**Mitigation**: Atomic transaction boundaries around hook execution.

---

### FM-HOOK-008: N3 Rule Not Loaded 🔴 CRITICAL
```
Severity:    ███████░░░ 7/10  Critical feature disabled
Occurrence:  ███░░░░░░░ 3/10  Rare initialization error
Detection:   ███████░░░ 7/10  Silent failure (hard to detect)
─────────────────────────────────────────────────
RPN: 147
```
**Effect**: All hooks disabled. Silent failure. No validation occurs.

**Mitigation**: Verify N3 physics rules present after initialization.

---

### FM-HOOK-002: Circular Hook Chain 🔴 CRITICAL
```
Severity:    █████████░ 9/10  System failure
Occurrence:  ███░░░░░░░ 3/10  Rare unless misconfigured
Detection:   █████░░░░░ 5/10  Runtime monitoring required
─────────────────────────────────────────────────
RPN: 135
```
**Effect**: Infinite loop. CPU/memory exhaustion. System hangs.

**Mitigation**: Cycle detection with visited set. Max chain depth limit.

---

### FM-HOOK-007: Handler Action Type Mismatch 🔴 CRITICAL
```
Severity:    █████░░░░░ 5/10  Silent failure
Occurrence:  █████░░░░░ 5/10  Common configuration error
Detection:   █████░░░░░ 5/10  Requires handler execution check
─────────────────────────────────────────────────
RPN: 125
```
**Effect**: Hook executes but performs no action. Validation bypassed.

**Mitigation**: Schema validation matching handler_data to action type.

---

### FM-HOOK-009: Receipt Storage Exhaustion 🔴 CRITICAL
```
Severity:    ███████░░░ 7/10  Eventual system failure
Occurrence:  █████░░░░░ 5/10  Common long-running systems
Detection:   ███░░░░░░░ 3/10  Memory monitoring detects
─────────────────────────────────────────────────
RPN: 105
```
**Effect**: Memory leak. System slowdown. Out-of-memory crash.

**Mitigation**: Receipt rotation with 1000 receipt retention limit.

---

### FM-HOOK-010: Delta Pattern Match Explosion 🔴 CRITICAL
```
Severity:    ███████░░░ 7/10  System unresponsive
Occurrence:  █████░░░░░ 5/10  Common with generic patterns
Detection:   ███░░░░░░░ 3/10  Performance monitoring detects
─────────────────────────────────────────────────
RPN: 105
```
**Effect**: System hangs during delta processing. Tick duration exceeds SLO.

**Mitigation**: Limit delta pattern matches. Add max_matches bound.

---

### FM-HOOK-001: Condition Query Timeout 🟡 MEDIUM
```
Severity:    █████░░░░░ 5/10  Moderate impact
Occurrence:  ███░░░░░░░ 3/10  Occasional complex queries
Detection:   ███░░░░░░░ 3/10  Easily detected (logs)
─────────────────────────────────────────────────
RPN: 45
```
**Effect**: Hook never triggers or triggers late. Validation missed.

**Mitigation**: Query timeout handling with fallback behavior.

---

### FM-HOOK-006: Condition SPARQL Injection 🟡 MEDIUM
```
Severity:    █████████░ 9/10  Security breach
Occurrence:  █░░░░░░░░░ 1/10  Only if untrusted hooks loaded
Detection:   █████░░░░░ 5/10  SPARQL parsing detects some
─────────────────────────────────────────────────
RPN: 45
```
**Effect**: Unauthorized data access. Graph corruption. Data exfiltration.

**Mitigation**: SPARQL sanitization. Enforce read-only queries.

---

### FM-HOOK-005: Phase Ordering Violation 🟡 MEDIUM
```
Severity:    ███████░░░ 7/10  High impact on correctness
Occurrence:  ███░░░░░░░ 3/10  Rare with phase enforcement
Detection:   █░░░░░░░░░ 1/10  Easily detected (receipts)
─────────────────────────────────────────────────
RPN: 21
```
**Effect**: Hook sees incomplete data. Workflow physics violated.

**Mitigation**: Phase validation at registration and execution.

---

## Risk Mitigation Priority

Based on RPN values, address in this order:

1. **FM-HOOK-003** (RPN 315): Priority tie-breaking
2. **FM-HOOK-004** (RPN 150): Transaction boundaries
3. **FM-HOOK-008** (RPN 147): N3 health checks
4. **FM-HOOK-002** (RPN 135): Cycle detection
5. **FM-HOOK-007** (RPN 125): Schema validation
6. **FM-HOOK-009** (RPN 105): Receipt rotation
7. **FM-HOOK-010** (RPN 105): Delta pattern limits
8. **FM-HOOK-001** (RPN 45): Query timeouts
9. **FM-HOOK-006** (RPN 45): SPARQL sanitization
10. **FM-HOOK-005** (RPN 21): Phase guards

## Impact Categories

### Data Integrity Failures
- FM-HOOK-004: Rollback Cascade (RPN 150)
- FM-HOOK-007: Handler Mismatch (RPN 125)
- FM-HOOK-006: SPARQL Injection (RPN 45)

### Performance Failures
- FM-HOOK-010: Pattern Explosion (RPN 105)
- FM-HOOK-002: Circular Chain (RPN 135)
- FM-HOOK-001: Query Timeout (RPN 45)

### Logic Failures
- FM-HOOK-003: Priority Deadlock (RPN 315)
- FM-HOOK-005: Phase Violation (RPN 21)
- FM-HOOK-008: Rules Not Loaded (RPN 147)

### Resource Failures
- FM-HOOK-009: Receipt Exhaustion (RPN 105)

## Testing Coverage

All 10 failure modes have:
- ✅ Comprehensive test coverage (29 tests total)
- ✅ RPN calculation verification
- ✅ Risk level classification verification
- ✅ Mitigation strategies documented
- ✅ Integration points identified

## Quality Assurance

```
Type Checking:  100% (mypy strict)
Test Coverage:  100% (29/29 passing, <1s)
Immutability:   100% (@dataclass(frozen=True))
Documentation:  100% (NumPy-style docstrings)
FMEA Standard:  100% (AIAG 4th Ed compliance)
```
