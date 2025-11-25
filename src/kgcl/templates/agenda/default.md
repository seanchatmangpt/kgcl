# Daily Agenda - {{ date.strftime('%A, %B %d, %Y') }}

## Summary
- **Total Scheduled Hours**: {{ "%.1f"|format(total_event_hours) }}h
- **Focus Time Available**: {{ "%.1f"|format(total_focus_hours) }}h
- **Events**: {{ events|length }}
- **Reminders**: {{ reminders|length }}
- **Focus Blocks**: {{ focus_blocks|length }}

---

## 📅 Calendar Events

{% if events %}
{% set last_date = None %}
{% for event in events %}
{% set current_date = event.start.strftime('%A, %B %d') %}
{% if current_date != last_date %}

### {{ current_date }}
{% set last_date = current_date %}
{% endif %}

- **{{ event.start.strftime('%H:%M') }}{% if event.end %} - {{ event.end.strftime('%H:%M') }}{% endif %}** ({{ "%.1f"|format(event.duration_hours()) }}h) - *{{ event.title }}*{% if event.location %} @ {{ event.location }}{% endif %}
  {% if event.description %}
  > {{ event.description }}
  {% endif %}
  {% if event.priority == 1 %}
  🔴 **HIGH PRIORITY**
  {% elif event.priority == 2 %}
  🟡 **MEDIUM PRIORITY**
  {% endif %}

{% endfor %}
{% else %}
No calendar events scheduled.
{% endif %}

---

## ✓ Reminders & Tasks

{% if reminders %}
{% for reminder in reminders %}
- {% if reminder.completed %}✓{% else %}○{% endif %} **{{ reminder.title }}**
  - Due: {{ reminder.due_date.strftime('%a, %b %d at %H:%M') }}
  {% if reminder.tags %}
  - Tags: {{ reminder.tags|join(', ') }}
  {% endif %}
  {% if reminder.priority == 1 %}
  - 🔴 **HIGH PRIORITY**
  {% elif reminder.priority == 2 %}
  - 🟡 **MEDIUM PRIORITY**
  {% endif %}

{% endfor %}
{% else %}
No reminders or tasks for this period.
{% endif %}

---

## 💡 Focus Time Blocks

{% if focus_blocks %}
### Available for Deep Work
{% for block in focus_blocks %}
- **{{ block.start.strftime('%H:%M') }} - {{ block.end.strftime('%H:%M') }}** ({{ "%.1f"|format(block.duration_hours()) }}h)
  - {{ block.purpose }}

{% endfor %}

**💡 Tip**: Use these uninterrupted blocks for focused work and meetings.
{% else %}
No significant focus blocks identified (< 2 hours) in this period.
Consider consolidating or reducing meeting load.
{% endif %}

---

## 📋 Action Items

### High Priority (Do Today)
{% set high_priority = reminders|selectattr('priority', 'equalto', 1)|list + events|selectattr('priority', 'equalto', 1)|list %}
{% if high_priority %}
{% for item in high_priority[:5] %}
- [ ] {{ item.title }}
{% endfor %}
{% else %}
No high-priority items.
{% endif %}

### Medium Priority (This Week)
{% set medium_priority = reminders|selectattr('priority', 'equalto', 2)|list + events|selectattr('priority', 'equalto', 2)|list %}
{% if medium_priority %}
{% for item in medium_priority[:5] %}
- [ ] {{ item.title }}
{% endfor %}
{% else %}
No medium-priority items.
{% endif %}

---

## 📊 Time Distribution

- **Meeting Time**: {{ "%.1f"|format(total_event_hours) }}h ({{ "%.0f"|format((total_event_hours / (8))|default(0) * 100) }}% of 8h workday)
- **Focus Time**: {{ "%.1f"|format(total_focus_hours) }}h ({{ "%.0f"|format((total_focus_hours / (8))|default(0) * 100) }}% of 8h workday)
- **Unscheduled**: {{ "%.1f"|format(8 - total_event_hours - total_focus_hours) }}h

**💡 Lean Principle**: Single-piece flow works best with at least 60% focus time.

---

*Generated at {{ date.strftime('%Y-%m-%d %H:%M:%S') }}*
*Lean Principle: VALUE - Maximize time spent on high-value activities*
