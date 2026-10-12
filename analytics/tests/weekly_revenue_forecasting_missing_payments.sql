{{ config(enabled=target.name == 'dev', severity='warn') }}

-- Surface genuine source payment gaps without imputing or rejecting their weeks.
-- Exact missing-payment counts are independently checked by the reconciliation test.
select week_start, delivered_orders, weekly_revenue, missing_payment_orders
from {{ ref('weekly_revenue_forecasting') }}
where missing_payment_orders > 0
