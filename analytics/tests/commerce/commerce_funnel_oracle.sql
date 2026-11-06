{{ config(enabled=target.name == 'commerce_dev') }}
select count(*) as observed_sessions
from {{ ref('fct_commerce_session_funnel') }}
where test_run_id = 'commerce-live-1793727480072'
having count(*) != 10 or countif(viewed_product) != 10 or countif(added_to_cart) != 6
    or countif(started_checkout) != 3 or countif(purchased) != 1 or sum(logical_purchases) != 1
