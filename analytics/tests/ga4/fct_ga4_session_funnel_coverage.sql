{{ config(enabled=target.name == 'ga4_dev') }}

-- Exactly one row in each model per composite key; detect missing/extra/duplicate sessions.
with session_keys as (

    select user_pseudo_id, ga_session_id, 1 as session_rows, 0 as funnel_rows
    from {{ ref('int_ga4_sessions') }}

    union all

    select user_pseudo_id, ga_session_id, 0 as session_rows, 1 as funnel_rows
    from {{ ref('fct_ga4_session_funnel') }}

),

session_counts as (

    -- Keep aggregate aliases distinct from inputs and filter in the next scope.
    -- GROUP BY also aligns null keys without relying on join equality.
    select
        user_pseudo_id,
        ga_session_id,
        sum(session_rows) as session_row_count,
        sum(funnel_rows) as funnel_row_count
    from session_keys
    group by user_pseudo_id, ga_session_id

)

select
    user_pseudo_id,
    ga_session_id,
    session_row_count,
    funnel_row_count
from session_counts
where session_row_count != 1 or funnel_row_count != 1
