with raw as (
    select * from {{ ref('stg_commerce_events') }}
), keys as (
    select environment, event_id, count(distinct payload_hash) as payload_versions
    from raw group by 1, 2
), ranked as (
    select r.*, k.payload_versions,
        row_number() over(partition by r.environment, r.event_id order by r.bq_ingested_timestamp, r.vendor_uuid) as delivery_rank
    from raw r join keys k using(environment, event_id)
)
select * except(delivery_rank)
from ranked
where delivery_rank = 1 and is_valid and payload_versions = 1
