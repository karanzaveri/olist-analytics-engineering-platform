{% set shard = var('ga4_commerce_daily_suffix', '20261103') | string %}
{% if not modules.re.fullmatch('[0-9]{8}', shard) %}
    {{ exceptions.raise_compiler_error('ga4_commerce_daily_suffix must be YYYYMMDD') }}
{% endif %}
{% set string_keys = [
    'event_id', 'occurred_at', 'canonical_event_name', 'app_session_id', 'app_anonymous_id',
    'test_run_id', 'scenario_id', 'checkout_id', 'order_id', 'transaction_id', 'currency',
    'consent_state', 'environment', 'activity_origin', 'simulation', 'schema_version',
    'app_version', 'catalog_version', 'catalog_origin', 'display_provenance', 'device_class'
] %}
{% set canonical_keys = string_keys + ['session_sequence', 'value'] %}
with native as (
    select
        '{{ shard }}' as source_shard,
        event_name as ga4_event_name,
        event_timestamp as native_event_timestamp,
        event_date as native_event_date,
        stream_id, user_pseudo_id, event_params, items as native_items, privacy_info, ecommerce,
        (
            select as struct
                {% for key in string_keys %}
                max(if(p.key = '{{ key }}', p.value.string_value, null)) as {{ 'source_occurred_at' if key == 'occurred_at' else key }},
                {% endfor %}
                max(if(p.key = 'session_sequence', p.value.int_value, null)) as session_sequence,
                max(if(p.key = 'value', coalesce(
                    safe_cast(p.value.int_value as numeric), safe_cast(p.value.double_value as numeric)
                ), null)) as value_brl,
                max(if(p.key = 'ga_session_id', p.value.int_value, null)) as ga_session_id
            from unnest(event_params) p
        ) as params,
        not exists (
            select 1 from unnest(event_params) p
            where p.key in ({% for key in canonical_keys %}'{{ key }}'{% if not loop.last %}, {% endif %}{% endfor %})
            group by p.key having count(*) > 1
        ) as unique_params,
        array(
            select as struct i.item_id as product_id, i.item_name as demo_title,
                i.item_category as category, i.quantity,
                safe_cast(i.price as numeric) * 100 as price_minor
            from unnest(items) i
            order by product_id, demo_title, category, quantity, price_minor
        ) as normalized_items
    from {{ source('ga4_commerce_raw', 'daily_events') }}
    where stream_id = '16265125392'
      and event_name in ('view_item', 'add_to_cart', 'remove_from_cart', 'begin_checkout', 'purchase')
), normalized as (
    select native.* except(params), params.*,
        safe_cast(params.source_occurred_at as timestamp) as occurred_at,
        to_json_string(struct(params.environment, params.activity_origin, params.test_run_id,
            params.app_anonymous_id, params.app_session_id)) as session_key,
        params.canonical_event_name as event_name,
        params.value_brl * 100 as value_minor,
        normalized_items[safe_offset(0)].product_id as product_id,
        concat('|', array_to_string(array(select i.product_id from unnest(normalized_items) i), '|'), '|') as product_tokens,
        to_json_string(normalized_items) as items_json
    from native
)
select *,
    unix_micros(occurred_at) as occurred_at_us,
    to_hex(sha256(to_json_string(struct(
        ga4_event_name, event_name, source_occurred_at, session_sequence, environment, activity_origin,
        test_run_id, scenario_id, app_anonymous_id, app_session_id, schema_version, app_version,
        catalog_version, catalog_origin, display_provenance, device_class, simulation, consent_state,
        currency, value_minor, normalized_items, checkout_id, order_id, transaction_id,
        nullif(ecommerce.transaction_id, '(not set)') as native_transaction_id
    )))) as payload_hash,
    coalesce(
        unique_params
        and regexp_contains(event_id, r'(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
        and occurred_at is not null
        and regexp_contains(source_occurred_at, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        and session_sequence between 1 and 9007199254740991
        and environment = 'local_demo' and activity_origin = 'synthetic_test'
        and regexp_contains(test_run_id, r'^ga4-live-[0-9]+$') and scenario_id != ''
        and app_anonymous_id != '' and app_session_id != ''
        and schema_version = '1.0.0' and app_version = '1.0.0' and catalog_version = '1.0.0'
        and catalog_origin = 'olist_historical' and display_provenance = 'manual_demo'
        and device_class in ('desktop', 'tablet', 'mobile', 'unknown')
        and simulation = 'true' and consent_state = 'granted' and currency = 'BRL'
        and event_name = case ga4_event_name
            when 'view_item' then 'product_viewed'
            when 'add_to_cart' then 'product_added_to_cart'
            when 'remove_from_cart' then 'product_removed_from_cart'
            when 'begin_checkout' then 'checkout_started'
            when 'purchase' then 'purchase_completed'
        end
        and array_length(normalized_items) > 0
        and (ga4_event_name in ('begin_checkout', 'purchase') or array_length(normalized_items) = 1)
        and not exists (
            select 1 from unnest(normalized_items) i
            where not coalesce(regexp_contains(i.product_id, r'^[0-9a-f]{32}$') and i.demo_title != ''
                and i.category != '' and i.quantity = 1 and i.price_minor >= 0
                and i.price_minor = trunc(i.price_minor), false)
        )
        and array_length(normalized_items) = (select count(distinct i.product_id) from unnest(normalized_items) i)
        and (ga4_event_name = 'purchase' or nullif(ecommerce.transaction_id, '(not set)') is null)
        and value_minor = (select sum(i.price_minor * i.quantity) from unnest(normalized_items) i)
        and case ga4_event_name
            when 'purchase' then checkout_id != '' and starts_with(order_id, 'demo_')
                and transaction_id = order_id and ecommerce.transaction_id = order_id
            when 'begin_checkout' then checkout_id != '' and order_id is null and transaction_id is null
            else checkout_id is null and order_id is null and transaction_id is null
        end,
        false
    ) as is_valid
from normalized
