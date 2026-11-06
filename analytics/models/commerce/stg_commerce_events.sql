with raw as (
    select uuid, event, distinct_id, timestamp, bq_ingested_timestamp, properties,
        'manual_vendor_file_export' as delivery_source, 'commerce_posthog_raw.events' as source_table, import_id
    from {{ source('commerce_posthog_raw', 'events') }}
    where timestamp >= timestamp('{{ var("commerce_start", "2026-11-03") }}')
      and timestamp < timestamp('{{ var("commerce_end", "2026-11-04") }}')
    {% if var('commerce_include_native', false) %}
    union all
    select uuid, event, distinct_id, timestamp, bq_ingested_timestamp, properties,
        'native_batch_export' as delivery_source, 'commerce_posthog_raw.events_native' as source_table, cast(null as string) as import_id
    from {{ source('commerce_posthog_raw', 'events_native') }}
    where timestamp >= timestamp('{{ var("commerce_start", "2026-11-03") }}')
      and timestamp < timestamp('{{ var("commerce_end", "2026-11-04") }}')
    {% endif %}
), typed as (
    select uuid as vendor_uuid, event as event_name, distinct_id, timestamp as vendor_timestamp,
        bq_ingested_timestamp, properties, delivery_source, source_table, import_id,
        json_value(properties, '$.event_id') as event_id,
        safe_cast(json_value(properties, '$.occurred_at') as timestamp) as occurred_at,
        json_value(properties, '$.anonymous_id') as anonymous_id,
        json_value(properties, '$.session_id') as session_id,
        safe_cast(json_value(properties, '$.session_sequence') as int64) as session_sequence,
        json_value(properties, '$.schema_version') as schema_version,
        json_value(properties, '$.environment') as environment,
        json_value(properties, '$.activity_origin') as activity_origin,
        json_value(properties, '$.test_run_id') as test_run_id,
        json_value(properties, '$.scenario_id') as scenario_id,
        json_value(properties, '$.catalog_origin') as catalog_origin,
        json_value(properties, '$.display_provenance') as display_provenance,
        json_value(properties, '$.checkout_id') as checkout_id,
        json_value(properties, '$.order_id') as order_id,
        json_value(properties, '$.currency') as currency,
        json_value(properties, '$.consent_state') as consent_state,
        safe_cast(json_value(properties, '$.simulation') as bool) as simulation,
        safe_cast(json_value(properties, '$.value_minor') as int64) as value_minor,
        to_json_string(json_query(properties, '$.items')) as items_json,
        json_query_array(properties, '$.items') as items
    from raw
), item_quality as (
    select t.vendor_uuid, t.bq_ingested_timestamp, t.delivery_source,
        countif(c.product_id is null or safe_cast(json_value(i, '$.quantity') as int64) is distinct from 1) as item_invalid_count
    from typed t cross join unnest(t.items) i
    left join {{ ref('commerce_catalog') }} c
      on c.product_id = json_value(i, '$.product_id')
     and c.category = json_value(i, '$.category')
     and c.demo_title = json_value(i, '$.demo_title')
     and c.price_minor = safe_cast(json_value(i, '$.price_minor') as int64)
    group by 1, 2, 3
)
select *,
    to_hex(sha256(to_json_string(struct(environment, activity_origin, test_run_id, anonymous_id, session_id)))) as session_key,
    to_hex(sha256(to_json_string(struct(event_name, distinct_id, to_json_string(properties) as event_properties)))) as payload_hash,
    coalesce(
        vendor_uuid is not null and regexp_contains(event_id, r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$') and occurred_at is not null
        and occurred_at = vendor_timestamp and anonymous_id = distinct_id and session_id is not null
        and anonymous_id != '' and session_id != '' and event_name = json_value(properties, '$.event_name')
        and json_value(properties, '$.app_version') = '1.0.0' and json_value(properties, '$.catalog_version') = '1.0.0'
        and session_sequence > 0 and schema_version = '1.0.0' and environment = 'local_demo'
        and activity_origin in ('manual_demo', 'synthetic_test')
        and ((activity_origin = 'synthetic_test' and nullif(test_run_id, '') is not null and nullif(scenario_id, '') is not null) or (activity_origin = 'manual_demo' and test_run_id is null and scenario_id is null))
        and catalog_origin = 'olist_historical' and display_provenance = 'manual_demo'
        and consent_state = 'granted' and simulation and currency = 'BRL'
        and value_minor >= 0 and array_length(items) > 0
        and (not starts_with(event_name, 'product_') or array_length(items) = 1)
        and array_length(items) = (select count(distinct json_value(i, '$.product_id')) from unnest(items) i)
        and item_invalid_count = 0
        and value_minor = (select sum(safe_cast(json_value(i, '$.price_minor') as int64) * safe_cast(json_value(i, '$.quantity') as int64)) from unnest(items) i)
        and not exists(select 1 from unnest(items) i where safe_cast(json_value(i, '$.quantity') as int64) is distinct from 1 or safe_cast(json_value(i, '$.price_minor') as int64) < 0 or json_value(i, '$.product_id') is null)
        and event_name in ('product_viewed', 'product_added_to_cart', 'product_removed_from_cart', 'checkout_started', 'purchase_completed')
        and (event_name not in ('checkout_started', 'purchase_completed') or checkout_id is not null)
        and (event_name != 'purchase_completed' or starts_with(order_id, 'demo_')),
        false
    ) as is_valid
from typed left join item_quality using(vendor_uuid, bq_ingested_timestamp, delivery_source)
