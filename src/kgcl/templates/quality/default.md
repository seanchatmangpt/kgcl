# Quality Report

## Executive Summary

**Total Violations**: {{ total_violations }}

### By Severity
- 🔴 **High**: {{ violations_by_severity.high }}
- 🟡 **Medium**: {{ violations_by_severity.medium }}
- 🟢 **Low**: {{ violations_by_severity.low }}

{% if total_violations == 0 %}
✅ **All systems nominal** - No quality issues detected.
{% elif violations_by_severity.high == 0 %}
✅ **No critical issues** - System quality is acceptable. Address medium/low priority items during maintenance windows.
{% elif violations_by_severity.high <= 3 %}
⚠️ **Few critical issues** - Prioritize fixes for {{ violations_by_severity.high }} high-severity items.
{% else %}
❌ **Quality alert** - {{ violations_by_severity.high }} high-severity issues require immediate attention.
{% endif %}

---

## 🔍 Violations by Category

{% for category in categories %}

### {{ category.name }}

**{{ category.description }}**

{% set severity_counts = category.count_by_severity() %}
- High: {{ severity_counts.high }} | Medium: {{ severity_counts.medium }} | Low: {{ severity_counts.low }}

{% if category.recommendation %}
**Recommended Fix**: {{ category.recommendation }}
{% endif %}

#### Issues
{% for violation in category.violations %}
- **{{ violation.message }}**
  - Node: `{{ violation.focus_node }}`
  {% if violation.result_path %}
  - Path: `{{ violation.result_path }}`
  {% endif %}
  - Constraint: `{{ violation.source_constraint }}`
  {% if violation.value %}
  - Value: `{{ violation.value }}`
  {% endif %}

{% endfor %}

---

{% endfor %}

## 📈 Quality Trends

{% if trends %}
| Date | Total | High | Medium | Low |
|------|-------|------|--------|-----|
{% for trend in trends %}
| {{ trend.date }} | {{ trend.total_violations }} | {{ trend.high_severity }} | {{ trend.medium_severity }} | {{ trend.low_severity }} |
{% endfor %}

{% if trends[-1].total_violations < trends[0].total_violations %}
✅ **Trend**: Quality improving - violation count decreased
{% elif trends[-1].total_violations > trends[0].total_violations %}
⚠️ **Trend**: Quality degrading - violation count increased
{% else %}
→ **Trend**: Quality stable - no recent change
{% endif %}

{% else %}
No historical trend data available yet.
{% endif %}

---

## 🔗 Ontology Reference

Reference: [{{ ontology_link }}]({{ ontology_link }})

For each violation, consult the ontology to understand:
- Shape constraints that were violated
- Cardinality and range restrictions
- Required properties and their formats
- Relationship invariants

---

## 📋 Action Plan

### Immediate (High Severity)
{% set high = violations|selectattr('severity', 'equalto', 'high')|list %}
{% if high %}
{% for v in high[:10] %}
1. Fix: {{ v.message }}
   - Node: {{ v.focus_node }}
   - Constraint: {{ v.source_constraint }}
{% endfor %}
{% if high|length > 10 %}
... and {{ high|length - 10 }} more high-severity issues
{% endif %}
{% else %}
No high-severity issues to address.
{% endif %}

### Soon (Medium Severity)
{% set medium = violations|selectattr('severity', 'equalto', 'medium')|list %}
{% if medium %}
- [ ] Review {{ medium|length }} medium-severity violations
{% else %}
None
{% endif %}

### Later (Low Severity)
{% set low = violations|selectattr('severity', 'equalto', 'low')|list %}
{% if low %}
- [ ] Plan fixes for {{ low|length }} low-severity issues
{% else %}
None
{% endif %}

---

## 🎓 Lean Principles

**PERFECTION**: Drift between ontology (O) and actual data (A) is a defect.

Each violation represents a gap that should be:
1. **Fixed** (correct the data to match the ontology)
2. **Prevented** (add invariants to catch similar issues)
3. **Measured** (track fix velocity and quality trends)

---

*Quality Report Generated*
*Lean Principle: PERFECTION - Continuous improvement toward zero-defect quality*
