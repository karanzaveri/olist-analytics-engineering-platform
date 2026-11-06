select session_key, environment, activity_origin, test_run_id, anonymous_id, session_id,
    min(occurred_at) as session_start, max(occurred_at) as session_end,
    count(*) as event_count,
    countif(event_name = 'purchase_completed') as purchase_events
from {{ ref('int_commerce_events_deduped') }}
group by 1, 2, 3, 4, 5, 6
