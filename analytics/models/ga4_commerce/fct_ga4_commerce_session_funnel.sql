with deliveries as (
    select * from {{ ref('stg_ga4_commerce_events') }}
), accepted_ids as (
    select environment, event_id
    from deliveries
    where event_id is not null
    group by environment, event_id
    having count(distinct payload_hash) = 1
       and sum(case when is_valid then 0 else 1 end) = 0
), ranked as (
    select d.*, row_number() over (
        partition by d.environment, d.event_id order by d.native_event_timestamp, d.source_shard
    ) as delivery_rank
    from deliveries d
    join accepted_ids a on d.environment = a.environment and d.event_id = a.event_id
), events as (
    select * from ranked where delivery_rank = 1
), sessions as (
    select session_key, environment, activity_origin, test_run_id, app_anonymous_id, app_session_id,
        min(scenario_id) as scenario_id, min(occurred_at) as session_started_at,
        count(*) as event_count,
        sum(case when event_name = 'product_removed_from_cart' then 1 else 0 end) as removal_events
    from events
    group by session_key, environment, activity_origin, test_run_id, app_anonymous_id, app_session_id
), views as (
    select *, row_number() over (
        partition by session_key order by occurred_at, session_sequence, event_id
    ) as view_rank
    from events where event_name = 'product_viewed'
), anchors as (
    select session_key, occurred_at_us from views where view_rank = 1
), additions as (
    select a.*
    from events a join anchors w on a.session_key = w.session_key
    where a.event_name = 'product_added_to_cart'
      and a.occurred_at_us <= w.occurred_at_us + 1800000000
      and exists (
          select 1 from views v
          where v.session_key = a.session_key and v.product_id = a.product_id
            and {{ commerce_after('a', 'v') }}
      )
), checkouts as (
    select c.*
    from events c join anchors w on c.session_key = w.session_key
    where c.event_name = 'checkout_started'
      and c.occurred_at_us <= w.occurred_at_us + 1800000000
      and exists (
          select 1 from additions a
          where a.session_key = c.session_key and {{ commerce_after('c', 'a') }}
            and strpos(c.product_tokens, concat('|', a.product_id, '|')) > 0
      )
), purchase_signatures as (
    select distinct environment, order_id, session_key, checkout_id, items_json
    from events where event_name = 'purchase_completed'
), accepted_orders as (
    select environment, order_id from purchase_signatures
    group by environment, order_id having count(*) = 1
), purchases as (
    select p.session_key, count(distinct p.order_id) as logical_purchases
    from events p
    join anchors w on p.session_key = w.session_key
    join accepted_orders o on p.environment = o.environment and p.order_id = o.order_id
    where p.event_name = 'purchase_completed'
      and p.occurred_at_us <= w.occurred_at_us + 1800000000
      and exists (
          select 1 from checkouts c
          where c.session_key = p.session_key and {{ commerce_after('p', 'c') }}
            and c.checkout_id = p.checkout_id and c.items_json = p.items_json
      )
    group by p.session_key
), flags as (
    select s.*,
        s.session_key in (select session_key from anchors) as viewed_product,
        s.session_key in (select session_key from additions) as added_to_cart,
        s.session_key in (select session_key from checkouts) as started_checkout,
        coalesce(p.logical_purchases, 0) > 0 as purchased,
        coalesce(p.logical_purchases, 0) as logical_purchases
    from sessions s left join purchases p on s.session_key = p.session_key
)
select *, case when purchased then 4 when started_checkout then 3
    when added_to_cart then 2 when viewed_product then 1 else 0 end as stage_reached
from flags
