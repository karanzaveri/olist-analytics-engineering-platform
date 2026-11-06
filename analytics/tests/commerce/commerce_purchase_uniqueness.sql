{{ config(enabled=target.name == 'commerce_dev') }}
select environment, order_id
from {{ ref('int_commerce_events_deduped') }}
where event_name = 'purchase_completed'
group by 1, 2 having count(*) > 1
