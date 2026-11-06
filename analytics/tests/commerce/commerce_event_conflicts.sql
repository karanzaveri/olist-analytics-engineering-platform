{{ config(enabled=target.name == 'commerce_dev') }}
select environment, event_id
from {{ ref('stg_commerce_events') }}
group by 1, 2 having count(distinct payload_hash) > 1
