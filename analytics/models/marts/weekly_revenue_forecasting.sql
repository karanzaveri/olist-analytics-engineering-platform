with calendar as (

    select week_start
    from unnest(generate_date_array(
        date('2017-01-02'), date('2018-08-20'), interval 7 day
    )) as week_start

),

weekly_orders as (

    select
        date_trunc(order_purchase_date, week(monday)) as week_start,
        count(*) as delivered_orders,
        sum(total_payment_value) as weekly_revenue,
        countif(total_payment_value is null) as missing_payment_orders
    from {{ ref('fct_orders') }}
    where order_status = 'delivered'
      and order_purchase_date >= date('2017-01-02')
      and order_purchase_date < date('2018-08-27')
    group by week_start

),

weekly_metrics as (

    select
        calendar.week_start,
        date_add(calendar.week_start, interval 6 day) as week_end,
        coalesce(weekly_orders.delivered_orders, 0) as delivered_orders,
        -- Only genuinely empty calendar weeks become zero revenue.
        -- Preserve NULL when delivered orders exist but every payment is missing.
        case
            when weekly_orders.delivered_orders is null then 0
            else weekly_orders.weekly_revenue
        end as weekly_revenue,
        coalesce(weekly_orders.missing_payment_orders, 0) as missing_payment_orders
    from calendar
    left join weekly_orders
        on calendar.week_start = weekly_orders.week_start

)

select
    week_start,
    week_end,
    delivered_orders,
    weekly_revenue,
    safe_divide(weekly_revenue, delivered_orders) as average_order_value,
    missing_payment_orders
from weekly_metrics
