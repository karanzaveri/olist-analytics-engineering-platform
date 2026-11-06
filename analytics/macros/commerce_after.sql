{% macro commerce_after(later, earlier) %}
({{ later }}.occurred_at > {{ earlier }}.occurred_at or ({{ later }}.occurred_at = {{ earlier }}.occurred_at and {{ later }}.session_sequence > {{ earlier }}.session_sequence))
{% endmacro %}
