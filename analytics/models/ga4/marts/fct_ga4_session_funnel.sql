with events as (

    select user_pseudo_id, ga_session_id, event_name, event_timestamp
    from {{ ref('stg_ga4_events') }}
    where event_name in ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')

),

product_views as (

    select
        user_pseudo_id,
        ga_session_id,
        min(event_timestamp) as funnel_view_item_timestamp
    from events
    where event_name = 'view_item'
    group by user_pseudo_id, ga_session_id

),

carts as (

    select
        product_views.*,
        min(events.event_timestamp) as funnel_add_to_cart_timestamp
    from product_views
    left join events
        on product_views.user_pseudo_id = events.user_pseudo_id
        and product_views.ga_session_id = events.ga_session_id
        and events.event_name = 'add_to_cart'
        and events.event_timestamp >= product_views.funnel_view_item_timestamp
    group by product_views.user_pseudo_id, product_views.ga_session_id,
        product_views.funnel_view_item_timestamp

),

checkouts as (

    select
        carts.*,
        min(events.event_timestamp) as funnel_begin_checkout_timestamp
    from carts
    left join events
        on carts.user_pseudo_id = events.user_pseudo_id
        and carts.ga_session_id = events.ga_session_id
        and events.event_name = 'begin_checkout'
        and events.event_timestamp >= carts.funnel_add_to_cart_timestamp
    group by carts.user_pseudo_id, carts.ga_session_id,
        carts.funnel_view_item_timestamp, carts.funnel_add_to_cart_timestamp

),

purchases as (

    select
        checkouts.*,
        min(events.event_timestamp) as funnel_purchase_timestamp
    from checkouts
    left join events
        on checkouts.user_pseudo_id = events.user_pseudo_id
        and checkouts.ga_session_id = events.ga_session_id
        and events.event_name = 'purchase'
        and events.event_timestamp >= checkouts.funnel_begin_checkout_timestamp
    group by checkouts.user_pseudo_id, checkouts.ga_session_id,
        checkouts.funnel_view_item_timestamp, checkouts.funnel_add_to_cart_timestamp,
        checkouts.funnel_begin_checkout_timestamp

),

session_funnel as (

    select
        sessions.user_pseudo_id,
        sessions.ga_session_id,
        sessions.session_start_timestamp,
        sessions.session_end_timestamp,
        sessions.session_duration_seconds,
        sessions.total_events,
        sessions.device_category,
        -- Independent event-presence flags do not imply sequential progression.
        sessions.has_product_view,
        sessions.has_add_to_cart,
        sessions.has_begin_checkout,
        sessions.has_purchase,
        attribution.attributed_source,
        attribution.attributed_medium,
        attribution.attributed_channel,
        attribution.attribution_status,
        attribution.has_internal_referral,
        attribution.has_conflicting_sources,
        attribution.distinct_source_medium_pairs,
        purchases.funnel_view_item_timestamp,
        purchases.funnel_add_to_cart_timestamp,
        purchases.funnel_begin_checkout_timestamp,
        purchases.funnel_purchase_timestamp,
        purchases.funnel_view_item_timestamp is not null as funnel_viewed_product,
        purchases.funnel_add_to_cart_timestamp is not null as funnel_added_to_cart,
        purchases.funnel_begin_checkout_timestamp is not null as funnel_started_checkout,
        purchases.funnel_purchase_timestamp is not null as funnel_purchased,
        case
            when purchases.funnel_purchase_timestamp is not null then 4
            when purchases.funnel_begin_checkout_timestamp is not null then 3
            when purchases.funnel_add_to_cart_timestamp is not null then 2
            when purchases.funnel_view_item_timestamp is not null then 1
            else 0
        end as funnel_stage_reached
    from {{ ref('int_ga4_sessions') }} as sessions
    left join purchases
        on sessions.user_pseudo_id = purchases.user_pseudo_id
        and sessions.ga_session_id = purchases.ga_session_id
    left join {{ ref('int_ga4_session_attribution') }} as attribution
        on sessions.user_pseudo_id = attribution.user_pseudo_id
        and sessions.ga_session_id = attribution.ga_session_id

)

select
    *,
    case funnel_stage_reached
        when 0 then 'Not Entered'
        when 1 then 'After Product View'
        when 2 then 'After Add to Cart'
        when 3 then 'After Begin Checkout'
        when 4 then 'Completed'
    end as funnel_drop_off_stage
from session_funnel
