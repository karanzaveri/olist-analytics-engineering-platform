{{ config(enabled=target.name == 'commerce_dev') }}
with actual as (
    select * from {{ ref('int_commerce_events_deduped') }}
    where test_run_id = 'commerce-live-1793727480072'
), expected as (
    select * from {{ ref('commerce_expected_events') }}
)
select coalesce(a.event_id, e.event_id) as failed_id
from actual a full outer join expected e using(event_id)
where a.event_id is null or e.event_id is null
   or a.event_name != e.event_name or a.session_id != e.session_id
   or a.anonymous_id != e.anonymous_id or a.session_sequence != e.session_sequence
   or a.occurred_at != safe_cast(e.occurred_at as timestamp)
   or coalesce(a.checkout_id, '') != coalesce(e.checkout_id, '')
   or coalesce(a.order_id, '') != coalesce(e.order_id, '')
