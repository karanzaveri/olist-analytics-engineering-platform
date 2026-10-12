{{ config(enabled=target.name == 'ga4_dev') }}

-- Check complete session coverage and consistency without fixing fixture counts.
with sessions as (

    select user_pseudo_id, ga_session_id
    from {{ ref('int_ga4_sessions') }}

),

attribution as (

    select *
    from {{ ref('int_ga4_session_attribution') }}

),

session_alignment as (

    -- Grouping matches null keys without an unsupported null-safe full join.
    -- Require exactly one row on each side, including duplicate-key detection.
    select
        user_pseudo_id,
        ga_session_id,
        sum(session_rows) as session_rows,
        sum(attribution_rows) as attribution_rows
    from (
        select user_pseudo_id, ga_session_id, 1 as session_rows, 0 as attribution_rows
        from sessions

        union all

        select user_pseudo_id, ga_session_id, 0 as session_rows, 1 as attribution_rows
        from attribution
    ) as session_keys
    group by user_pseudo_id, ga_session_id

)

select
    user_pseudo_id,
    ga_session_id,
    'session_alignment' as violation
from session_alignment
where session_rows != 1
   or attribution_rows != 1

union all

select
    user_pseudo_id,
    ga_session_id,
    'attribution_consistency' as violation
from attribution
where attribution_status is null
   or attribution_status not in ('Attributed', 'Internal Referral Only', 'Unknown')
   or attributed_channel is null
   or has_internal_referral is null
   or has_conflicting_sources is null
   or distinct_source_medium_pairs is null
   or distinct_source_medium_pairs < 0
   or has_conflicting_sources != (distinct_source_medium_pairs > 1)
   or (attribution_status = 'Unknown' and (
       distinct_source_medium_pairs != 0
       or has_internal_referral
       or attributed_source is not null
       or attributed_medium is not null
       or attributed_channel != 'Unknown'
   ))
   or (attribution_status = 'Internal Referral Only' and (
       distinct_source_medium_pairs < 1
       or not has_internal_referral
       or attributed_source is not null
       or attributed_medium is not null
       or attributed_channel != 'Internal Referral Only'
   ))
   or (attribution_status = 'Attributed' and (
       distinct_source_medium_pairs < 1
       or nullif(trim(attributed_source), '') is null
       or nullif(trim(attributed_medium), '') is null
       or attributed_channel in ('Unknown', 'Internal Referral Only')
       or (lower(attributed_source) in (
           'shop.googlemerchandisestore.com', 'googlemerchandisestore.com'
       ) and lower(attributed_medium) = 'referral')
   ))
