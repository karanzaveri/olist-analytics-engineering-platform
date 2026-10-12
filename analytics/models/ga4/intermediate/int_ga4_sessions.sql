with events as (

    select *
    from {{ ref('stg_ga4_events') }}

),

sessions as (

    select
        user_pseudo_id,
        ga_session_id,
        min(event_timestamp) as session_start_timestamp,
        max(event_timestamp) as session_end_timestamp,
        count(*) as total_events,
        -- Order timestamp ties by stable event contents, not input row order.
        -- A struct preserves a null device on the earliest event.
        array_agg(
            struct(device_category as device_category)
            order by event_timestamp asc, to_json_string(events) asc
            limit 1
        )[offset(0)].device_category as device_category,
        countif(event_name = 'view_item') > 0 as has_product_view,
        countif(event_name = 'add_to_cart') > 0 as has_add_to_cart,
        countif(event_name = 'begin_checkout') > 0 as has_begin_checkout,
        countif(event_name = 'purchase') > 0 as has_purchase
    from events
    group by user_pseudo_id, ga_session_id

)

select
    user_pseudo_id,
    ga_session_id,
    session_start_timestamp,
    session_end_timestamp,
    -- These bounds cover only events observed in the staging date window.
    greatest(
        timestamp_diff(session_end_timestamp, session_start_timestamp, second),
        0
    ) as session_duration_seconds,
    total_events,
    device_category,
    has_product_view,
    has_add_to_cart,
    has_begin_checkout,
    has_purchase
from sessions
