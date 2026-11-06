{{ config(enabled=target.name == 'ga4_commerce_dev') }}

select session_key
from {{ ref('fct_ga4_commerce_session_funnel') }}
where (purchased and not started_checkout)
   or (started_checkout and not added_to_cart)
   or (added_to_cart and not viewed_product)
   or purchased != (logical_purchases > 0)
