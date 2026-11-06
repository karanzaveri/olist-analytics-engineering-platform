with events as (
    select * from {{ ref('int_commerce_events_deduped') }}
), anchors as (
    select session_key, array_agg(struct(occurred_at, session_sequence) order by occurred_at, session_sequence limit 1)[offset(0)] as anchor
    from events where event_name = 'product_viewed' group by 1
), views as (
    select session_key, anchor.occurred_at as occurred_at, anchor.session_sequence as session_sequence
    from anchors
), additions as (
    select a.* from events a join views v using(session_key)
    where a.event_name = 'product_added_to_cart' and {{ commerce_after('a', 'v') }}
      and a.occurred_at <= timestamp_add(v.occurred_at, interval 30 minute)
), checkouts as (
    select distinct c.* except(properties, items), c.items_json as checkout_items_json
    from events c join additions a using(session_key) join views v using(session_key)
    where c.event_name = 'checkout_started' and {{ commerce_after('c', 'a') }}
      and c.occurred_at <= timestamp_add(v.occurred_at, interval 30 minute)
      and exists(select 1 from unnest(c.items) ci, unnest(a.items) ai where json_value(ci, '$.product_id') = json_value(ai, '$.product_id'))
), purchases as (
    select distinct p.session_key, p.order_id
    from events p join checkouts c using(session_key) join views v using(session_key)
    where p.event_name = 'purchase_completed' and {{ commerce_after('p', 'c') }}
      and p.checkout_id = c.checkout_id and p.items_json = c.checkout_items_json
      and p.occurred_at <= timestamp_add(v.occurred_at, interval 30 minute)
), flags as (
    select s.*,
        s.session_key in (select session_key from views) as viewed_product,
        s.session_key in (select session_key from additions) as added_to_cart,
        s.session_key in (select session_key from checkouts) as started_checkout,
        s.session_key in (select session_key from purchases) as purchased,
        (select count(distinct p.order_id) from purchases p where p.session_key = s.session_key) as logical_purchases
    from {{ ref('int_commerce_sessions') }} s
)
select *, case when purchased then 4 when started_checkout then 3 when added_to_cart then 2 when viewed_product then 1 else 0 end as stage_reached
from flags
