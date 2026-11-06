{{ config(enabled=target.name == 'commerce_dev') }}
select * from {{ ref('fct_commerce_session_funnel') }}
where (purchased and not started_checkout) or (started_checkout and not added_to_cart)
   or (added_to_cart and not viewed_product) or session_end < session_start
