with populated_events as (

    select
        user_pseudo_id,
        ga_session_id,
        event_timestamp,
        trim(event_source) as source,
        trim(event_medium) as medium
    from {{ ref('stg_ga4_events') }}
    where nullif(trim(event_source), '') is not null
      and nullif(trim(event_medium), '') is not null

),

classified_events as (

    select
        *,
        lower(source) in (
            'shop.googlemerchandisestore.com',
            'googlemerchandisestore.com'
        ) and lower(medium) = 'referral' as is_internal_referral
    from populated_events

),

pair_summary as (

    select
        user_pseudo_id,
        ga_session_id,
        logical_or(is_internal_referral) as has_internal_referral,
        -- Serialize the pair to avoid collisions from concatenated strings.
        count(distinct to_json_string(struct(source, medium)))
            as distinct_source_medium_pairs
    from classified_events
    group by user_pseudo_id, ga_session_id

),

first_non_internal as (

    select
        user_pseudo_id,
        ga_session_id,
        source,
        medium
    from classified_events
    where not is_internal_referral
    -- Equal timestamp/pair rows yield identical attribution values.
    qualify row_number() over (
        partition by user_pseudo_id, ga_session_id
        order by event_timestamp asc, source asc, medium asc
    ) = 1

),

session_attribution as (

    select
        sessions.user_pseudo_id,
        sessions.ga_session_id,
        first_non_internal.source as attributed_source,
        first_non_internal.medium as attributed_medium,
        case
            when first_non_internal.source is not null then 'Attributed'
            when pair_summary.has_internal_referral then 'Internal Referral Only'
            else 'Unknown'
        end as attribution_status,
        coalesce(pair_summary.has_internal_referral, false) as has_internal_referral,
        coalesce(pair_summary.distinct_source_medium_pairs, 0)
            as distinct_source_medium_pairs
    from {{ ref('int_ga4_sessions') }} as sessions
    left join first_non_internal
        on sessions.user_pseudo_id is not distinct from first_non_internal.user_pseudo_id
        and sessions.ga_session_id is not distinct from first_non_internal.ga_session_id
    left join pair_summary
        on sessions.user_pseudo_id is not distinct from pair_summary.user_pseudo_id
        and sessions.ga_session_id is not distinct from pair_summary.ga_session_id

)

select
    user_pseudo_id,
    ga_session_id,
    attributed_source,
    attributed_medium,
    -- Custom channel rules, not GA4's official default channel grouping.
    case
        when attribution_status != 'Attributed' then attribution_status
        when lower(attributed_source) = '(direct)'
            and lower(attributed_medium) in ('(none)', 'none') then 'Direct'
        when lower(attributed_medium) = 'organic' then 'Organic Search'
        when lower(attributed_medium) in ('cpc', 'ppc', 'paidsearch') then 'Paid Search'
        when lower(attributed_medium) = 'email' then 'Email'
        when lower(attributed_medium) = 'referral' then 'Referral'
        else 'Other'
    end as attributed_channel,
    attribution_status,
    has_internal_referral,
    distinct_source_medium_pairs > 1 as has_conflicting_sources,
    distinct_source_medium_pairs
from session_attribution
