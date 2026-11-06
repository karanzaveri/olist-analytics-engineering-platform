{{ config(enabled=target.name == 'ga4_commerce_dev') }}

select environment, event_id
from {{ ref('stg_ga4_commerce_events') }}
group by environment, event_id
having count(distinct payload_hash) > 1
    or sum(case when is_valid then 0 else 1 end) > 0
