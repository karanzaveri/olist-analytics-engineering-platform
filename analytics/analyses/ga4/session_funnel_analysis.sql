{{ config(enabled=target.name == 'ga4_dev') }}

-- Read-only report over the materialized mart; no public raw-table scan.
-- Compile under ga4_dev, then execute the compiled SELECT in BigQuery US.
-- Each session contributes once to each report type. Do not sum report types.
-- Device/channel conversion denominators are all sessions in that cohort,
-- including non-entrants. Transition denominators are the preceding stage.
with funnel as (

    select *
    from {{ ref('fct_ga4_session_funnel') }}

),

cohorts as (

    select 'Overall' as report_type, 'All sessions' as cohort, funnel.*
    from funnel

    union all

    select 'Device' as report_type, coalesce(device_category, 'Unknown') as cohort, funnel.*
    from funnel

    union all

    select 'Custom channel' as report_type,
        coalesce(attributed_channel, 'Unknown') as cohort, funnel.*
    from funnel

    union all

    -- Overlapping quality flags are separated into mutually exclusive combinations.
    select 'Attribution quality' as report_type,
        to_json_string(struct(
            attribution_status, has_internal_referral, has_conflicting_sources
        )) as cohort,
        funnel.*
    from funnel

),

counts as (

    select
        report_type,
        cohort,
        count(*) as total_sessions,
        countif(funnel_viewed_product) as viewed_sessions,
        countif(funnel_added_to_cart) as cart_sessions,
        countif(funnel_started_checkout) as checkout_sessions,
        countif(funnel_purchased) as purchasing_sessions,
        countif(has_internal_referral) as internal_referral_sessions,
        countif(has_conflicting_sources) as conflicting_sessions
    from cohorts
    group by report_type, cohort

)

select
    *,
    -- Rates are fractions (0-1), not percentages; zero denominators yield null.
    safe_divide(viewed_sessions, total_sessions) as funnel_entry_rate,
    safe_divide(purchasing_sessions, total_sessions) as session_purchase_rate,
    safe_divide(purchasing_sessions, viewed_sessions) as view_to_purchase_rate,
    safe_divide(cart_sessions, viewed_sessions) as view_to_cart_rate,
    safe_divide(checkout_sessions, cart_sessions) as cart_to_checkout_rate,
    safe_divide(purchasing_sessions, checkout_sessions) as checkout_to_purchase_rate,
    total_sessions - viewed_sessions as not_entered_sessions,
    viewed_sessions - cart_sessions as dropped_after_view_sessions,
    cart_sessions - checkout_sessions as dropped_after_cart_sessions,
    checkout_sessions - purchasing_sessions as dropped_after_checkout_sessions,
    safe_divide(total_sessions - viewed_sessions, total_sessions) as non_entry_rate,
    safe_divide(viewed_sessions - cart_sessions, viewed_sessions) as view_drop_off_rate,
    safe_divide(cart_sessions - checkout_sessions, cart_sessions) as cart_drop_off_rate,
    safe_divide(checkout_sessions - purchasing_sessions, checkout_sessions)
        as checkout_drop_off_rate,
    safe_divide(internal_referral_sessions, total_sessions) as internal_referral_rate,
    safe_divide(conflicting_sessions, total_sessions) as conflicting_pair_rate
from counts
order by report_type, cohort
