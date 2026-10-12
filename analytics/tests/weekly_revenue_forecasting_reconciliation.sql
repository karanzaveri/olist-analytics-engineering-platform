{{ config(enabled=target.name == 'dev') }}

with source_totals as (

    select
        date_trunc(order_purchase_date, week(monday)) as week_start,
        count(*) as expected_orders,
        sum(total_payment_value) as expected_revenue,
        countif(total_payment_value is null) as expected_missing_payments
    from {{ ref('fct_orders') }}
    where order_status = 'delivered'
      and order_purchase_date >= date('2017-01-02')
      and order_purchase_date < date('2018-08-27')
    group by week_start

),

comparison as (

    select
        weekly.*,
        coalesce(source_totals.expected_orders, 0) as expected_orders,
        case when source_totals.expected_orders is null then 0
            else source_totals.expected_revenue end as expected_revenue,
        coalesce(source_totals.expected_missing_payments, 0) as expected_missing_payments
    from {{ ref('weekly_revenue_forecasting') }} as weekly
    left join source_totals
        on weekly.week_start = source_totals.week_start

)

select *
from comparison
where delivered_orders is distinct from expected_orders
   or missing_payment_orders is distinct from expected_missing_payments
   or missing_payment_orders > delivered_orders
   or (weekly_revenue is null) != (expected_revenue is null)
   -- FLOAT64 sums can differ slightly with parallel aggregation; no model rounding.
   or abs(weekly_revenue - expected_revenue) > 0.000001
   or (average_order_value is null) != (safe_divide(expected_revenue, expected_orders) is null)
   or abs(average_order_value - safe_divide(expected_revenue, expected_orders)) > 0.000001
