# Stale Items Report

## 📊 Summary

**Cutoff Date**: {{ cutoff_date.strftime('%B %d, %Y') }} (items not modified in the past 30+ days)

### Item Counts
- **Stale Items**: {{ stale_items|length }}
- **Completed (Unarchived)**: {{ completed_items|length }}
- **Total Items for Cleanup**: {{ stale_items|length + completed_items|length }}

### Cleanup Impact
- **Estimated Triples to Remove**: {{ cleanup_estimate.estimated_triples_saved|default(0) }}
- **Storage Reduction**: {{ "%.2f"|format(cleanup_estimate.storage_reduction_mb|default(0)) }} MB
- **Query Performance Gain**: {{ cleanup_estimate.query_performance_gain|default('unknown') }}

{% if stale_items|length + completed_items|length == 0 %}
✅ **No stale items found** - Your knowledge base is clean.
{% elif stale_items|length + completed_items|length <= 5 %}
✅ **Minimal cleanup needed** - {{ stale_items|length + completed_items|length }} items to review.
{% elif stale_items|length + completed_items|length <= 20 %}
⚠️ **Maintenance required** - {{ stale_items|length + completed_items|length }} items accumulating.
{% else %}
🔴 **Cleanup urgent** - {{ stale_items|length + completed_items|length }} items need immediate attention.
{% endif %}

---

## 🗑️ Stale Items (Not Modified > 30 Days)

{% if stale_items %}
### By Staleness Level

#### Ancient (180+ days)
{% set ancient = stale_items|selectattr('staleness_level', 'equalto', 'ancient')|list %}
{% if ancient %}
{% for item in ancient %}
- **{{ item.label }}** ({{ item.item_type }})
  - Last Modified: {{ item.last_modified.strftime('%B %d, %Y') }} ({{ item.days_stale }} days ago)
  - URI: `{{ item.uri }}`
  - Size: {{ item.size_estimate }} triples
  - **Action**: Consider deletion - likely outdated

{% endfor %}
{% else %}
None
{% endif %}

#### Very Stale (90-180 days)
{% set very_stale = stale_items|selectattr('staleness_level', 'equalto', 'very_stale')|list %}
{% if very_stale %}
{% for item in very_stale %}
- **{{ item.label }}** ({{ item.item_type }})
  - Last Modified: {{ item.last_modified.strftime('%B %d, %Y') }} ({{ item.days_stale }} days ago)
  - URI: `{{ item.uri }}`
  - Size: {{ item.size_estimate }} triples
  - **Action**: Review for relevance

{% endfor %}
{% else %}
None
{% endif %}

#### Stale (30-90 days)
{% set stale = stale_items|selectattr('staleness_level', 'equalto', 'stale')|list %}
{% if stale %}
{% for item in stale[:10] %}
- **{{ item.label }}** ({{ item.item_type }})
  - Last Modified: {{ item.last_modified.strftime('%B %d, %Y') }} ({{ item.days_stale }} days ago)
  - URI: `{{ item.uri }}`
  - Size: {{ item.size_estimate }} triples

{% endfor %}
{% if stale|length > 10 %}
... and {{ stale|length - 10 }} more stale items
{% endif %}
{% else %}
None
{% endif %}

{% else %}
✅ No stale items found.
{% endif %}

---

## ✓ Completed But Unarchived Items

{% if completed_items %}
{% for item in completed_items %}

- **{{ item.label }}** ({{ item.item_type }})
  - Completed: {{ item.completed_date.strftime('%B %d, %Y') }} ({{ item.days_unarchived }} days ago)
  - URI: `{{ item.uri }}`
  - **Action**: Archive or delete

{% endfor %}
{% else %}
✅ All completed items are properly archived.
{% endif %}

---

## 📋 Cleanup Action Plan

### Phase 1: Quick Wins (Execute This Week)
{% set delete_candidates = stale_items|selectattr('staleness_level', 'equalto', 'ancient')|list %}
{% if delete_candidates %}
Delete {{ delete_candidates|length }} ancient items (180+ days old):
{% for item in delete_candidates[:5] %}
- [ ] Delete: {{ item.label }} ({{ item.days_stale }} days stale)
{% endfor %}
{% if delete_candidates|length > 5 %}
- [ ] ... and {{ delete_candidates|length - 5 }} more ancient items
{% endif %}
{% else %}
None
{% endif %}

### Phase 2: Review (This Month)
- [ ] Review {{ completed_items|length }} completed unarchived items for archival
- [ ] Review {{ very_stale|length }} very stale items (90-180 days) for continued relevance
- [ ] Consolidate duplicate entries if found

### Phase 3: Optimize (Next Quarter)
- [ ] Implement data retention policies
- [ ] Set up automatic archival workflows
- [ ] Monitor staleness metrics in future reports

---

## 💰 Cleanup Benefits

### Storage Optimization
- **Before**: {{ cleanup_estimate.estimated_triples_saved|default(0) }} triples
- **After**: {{ (cleanup_estimate.estimated_triples_saved * 0.8)|int }} triples
- **Savings**: {{ cleanup_estimate.storage_reduction_mb|default(0) }} MB

### Performance Improvement
- **Query Speed**: +{{ (cleanup_estimate.estimated_triples_saved / 1000 * 5)|int }}% faster SPARQL queries
- **Graph Traversal**: Reduced density and cycle detection
- **Inference**: Fewer rules to evaluate

### Maintainability
- **Clarity**: Easier to understand knowledge base structure
- **Consistency**: Less debt to track
- **Focus**: More attention on valuable items

---

## 🎓 Lean Principles

**PERFECTION**: Stale items represent **waste** (muda).

Cleanup delivers value through:
1. **Reduced Inventory**: Remove non-value items from graph
2. **Improved Flow**: Faster queries, clearer data
3. **Visible Waste**: Quantified in storage and performance metrics
4. **Continuous Improvement**: Regular cleanup cadence

---

*Stale Items Report Generated*
*Lean Principle: PULL - Keep only items needed for current value delivery*
