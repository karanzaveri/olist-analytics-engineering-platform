{{ config(enabled=target.name == 'ga4_dev') }}

select *
from {{ ref('fct_ga4_session_funnel') }}
where (funnel_added_to_cart and not funnel_viewed_product)
   or (funnel_started_checkout and not funnel_added_to_cart)
   or (funnel_purchased and not funnel_started_checkout)
   or funnel_viewed_product is distinct from (funnel_view_item_timestamp is not null)
   or funnel_added_to_cart is distinct from (funnel_add_to_cart_timestamp is not null)
   or funnel_started_checkout is distinct from (funnel_begin_checkout_timestamp is not null)
   or funnel_purchased is distinct from (funnel_purchase_timestamp is not null)
   or funnel_add_to_cart_timestamp < funnel_view_item_timestamp
   or funnel_begin_checkout_timestamp < funnel_add_to_cart_timestamp
   or funnel_purchase_timestamp < funnel_begin_checkout_timestamp
   or session_end_timestamp < session_start_timestamp
   or session_duration_seconds is distinct from
       timestamp_diff(session_end_timestamp, session_start_timestamp, second)
   or funnel_view_item_timestamp < session_start_timestamp
   or funnel_view_item_timestamp > session_end_timestamp
   or funnel_add_to_cart_timestamp > session_end_timestamp
   or funnel_begin_checkout_timestamp > session_end_timestamp
   or funnel_purchase_timestamp > session_end_timestamp
   or (funnel_viewed_product and not has_product_view)
   or (funnel_added_to_cart and not has_add_to_cart)
   or (funnel_started_checkout and not has_begin_checkout)
   or (funnel_purchased and not has_purchase)
   or funnel_stage_reached is distinct from case
       when funnel_purchased then 4
       when funnel_started_checkout then 3
       when funnel_added_to_cart then 2
       when funnel_viewed_product then 1
       else 0
   end
   or funnel_drop_off_stage is distinct from case funnel_stage_reached
       when 0 then 'Not Entered'
       when 1 then 'After Product View'
       when 2 then 'After Add to Cart'
       when 3 then 'After Begin Checkout'
       when 4 then 'Completed'
   end
