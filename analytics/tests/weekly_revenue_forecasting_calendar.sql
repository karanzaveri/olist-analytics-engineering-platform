{{ config(enabled=target.name == 'dev') }}

with calendar as (

    select week_start, 1 as expected_rows, 0 as actual_rows
    from unnest(generate_date_array(
        date('2017-01-02'), date('2018-08-20'), interval 7 day
    )) as week_start

    union all

    select week_start, 0 as expected_rows, 1 as actual_rows
    from {{ ref('weekly_revenue_forecasting') }}

),

coverage as (

    select week_start,
        sum(expected_rows) as expected_count,
        sum(actual_rows) as actual_count
    from calendar
    group by week_start

),

row_count as (

    select count(*) as weekly_records
    from {{ ref('weekly_revenue_forecasting') }}

)

select week_start, 'missing_extra_or_duplicate_week' as violation
from coverage
where expected_count != 1 or actual_count != 1

union all

select week_start, 'invalid_calendar_boundary' as violation
from {{ ref('weekly_revenue_forecasting') }}
where week_end is distinct from date_add(week_start, interval 6 day)
   or extract(dayofweek from week_start) != 2
   or extract(dayofweek from week_end) != 1

union all

select cast(null as date) as week_start, 'expected_86_records' as violation
from row_count
where weekly_records != 86
