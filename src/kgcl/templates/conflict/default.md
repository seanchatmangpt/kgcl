# Conflict Report

## 📅 Period
**{{ date_range.start.strftime('%B %d, %Y') }}** - **{{ date_range.end.strftime('%B %d, %Y') }}**

## Summary

**Total Conflicts Detected**: {{ total_conflicts }}

{% if total_conflicts == 0 %}
✅ **No conflicts found** - Your calendar is clear.
{% elif total_conflicts <= 2 %}
⚠️ **Minor conflicts** - {{ total_conflicts }} overlap(s) to resolve.
{% elif total_conflicts <= 5 %}
⚠️ **Moderate conflicts** - {{ total_conflicts }} overlaps require attention.
{% else %}
🔴 **Severe conflicts** - {{ total_conflicts }} overlaps need immediate action.
{% endif %}

---

## ⏰ Time Conflicts (Overlapping Events)

{% if time_conflicts %}
{% for conflict in time_conflicts %}

### Overlap {{ loop.index }}
- **Event 1**: {{ conflict.event1_title }}
  - Time: {{ conflict.event1_start.strftime('%a %H:%M') }} - {{ conflict.event1_end.strftime('%H:%M') }}
  - URI: `{{ conflict.event1_uri }}`

- **Event 2**: {{ conflict.event2_title }}
  - Time: {{ conflict.event2_start.strftime('%a %H:%M') }} - {{ conflict.event2_end.strftime('%H:%M') }}
  - URI: `{{ conflict.event2_uri }}`

- **Overlap Duration**: {{ conflict.overlap_minutes }} minutes

---

{% endfor %}
{% else %}
✅ No time conflicts detected.
{% endif %}

## 📦 Resource Conflicts

{% if resource_conflicts %}
{% for conflict in resource_conflicts %}

### {{ conflict.resource_name }}
- **Resource URI**: `{{ conflict.resource_uri }}`
- **Conflicting Events**: {{ conflict.event_count() }}
- **Events**:
{% for event in conflict.events %}
  - {{ event }}
{% endfor %}

---

{% endfor %}
{% else %}
✅ No resource conflicts detected.
{% endif %}

## 💡 Recommended Resolutions

{% if resolutions %}
{% for resolution in resolutions|sort(attribute='priority') %}

### {{ resolution.conflict_type|title }} Conflict Resolution
- **Suggestion**: {{ resolution.suggestion }}
- **Impact**: {{ resolution.estimated_impact|upper }}
- **Priority**:
  {% if resolution.priority == 1 %}
  🔴 HIGH
  {% elif resolution.priority == 2 %}
  🟡 MEDIUM
  {% else %}
  🟢 LOW
  {% endif %}

---

{% endfor %}
{% else %}
No resolutions needed - no conflicts to resolve.
{% endif %}

## 📋 Action Items

### Immediate (High Impact)
{% set high_impact = resolutions|selectattr('estimated_impact', 'equalto', 'high')|list %}
{% if high_impact %}
{% for res in high_impact[:5] %}
- [ ] {{ res.suggestion }}
{% endfor %}
{% else %}
None
{% endif %}

### Medium Priority
{% set medium_impact = resolutions|selectattr('estimated_impact', 'equalto', 'medium')|list %}
{% if medium_impact %}
{% for res in medium_impact[:5] %}
- [ ] {{ res.suggestion }}
{% endfor %}
{% else %}
None
{% endif %}

### Low Priority
{% set low_impact = resolutions|selectattr('estimated_impact', 'equalto', 'low')|list %}
{% if low_impact %}
{% for res in low_impact[:5] %}
- [ ] {{ res.suggestion }}
{% endfor %}
{% else %}
None
{% endif %}

---

## 🎓 Lean Principles

**PERFECTION**: Eliminate waste caused by scheduling conflicts.

Each resolved conflict:
- Reduces rework (re-scheduling meetings)
- Improves flow (clear calendar blocks)
- Increases value (fewer attendee no-shows)
- Enables single-piece flow (one meeting at a time)

---

*Conflict Report Generated*
*Lean Principle: VALUE_STREAM - Optimize the entire scheduling flow*
