{% test unique_ga4_session(model) %}

select
    user_pseudo_id,
    ga_session_id,
    count(*) as record_count
from {{ model }}
group by user_pseudo_id, ga_session_id
having count(*) > 1

{% endtest %}
