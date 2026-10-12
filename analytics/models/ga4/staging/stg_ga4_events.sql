with source as (

    select *
    from {{ source('ga4_raw', 'events') }}
    -- Constant suffix bounds restrict the scan to the seven daily shards.
    where _table_suffix between '20210125' and '20210131'

),

renamed as (

    select
        parse_date('%Y%m%d', event_date) as event_date,
        timestamp_micros(event_timestamp) as event_timestamp,
        event_name,
        user_pseudo_id,
        -- Scalar lookups preserve raw event grain, including missing parameters.
        -- If a key repeats, use its first occurrence in the original array.
        (
            select param.value.int_value
            from unnest(event_params) as param with offset as param_offset
            where param.key = 'ga_session_id'
            order by param_offset
            limit 1
        ) as ga_session_id,
        device.category as device_category,
        traffic_source.source as first_user_source,
        traffic_source.medium as first_user_medium,
        (
            select param.value.string_value
            from unnest(event_params) as param with offset as param_offset
            where param.key = 'source'
            order by param_offset
            limit 1
        ) as event_source,
        (
            select param.value.string_value
            from unnest(event_params) as param with offset as param_offset
            where param.key = 'medium'
            order by param_offset
            limit 1
        ) as event_medium,
        (
            select param.value.string_value
            from unnest(event_params) as param with offset as param_offset
            where param.key = 'campaign'
            order by param_offset
            limit 1
        ) as event_campaign,
        (
            select param.value.string_value
            from unnest(event_params) as param with offset as param_offset
            where param.key = 'page_location'
            order by param_offset
            limit 1
        ) as page_location,
        ecommerce.transaction_id as ecommerce_transaction_id,
        ecommerce.purchase_revenue_in_usd as purchase_revenue_usd
    from source

)

select *
from renamed
