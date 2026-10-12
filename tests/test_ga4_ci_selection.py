"""Offline target-selection guard tests; no dbt or BigQuery execution."""

import pytest

from analytics.ci.validate_ga4 import GA4_MODELS, validate_model_selection


def selection():
    return {'dev': {f'olist_{i}' for i in range(23)} | {'weekly_revenue_forecasting'},
            'ga4_dev': GA4_MODELS.copy()}


def test_updated_olist_inventory_passes():
    validate_model_selection(selection())


@pytest.mark.parametrize('issue', ['old_count', 'extra_dev', 'ga4_under_dev', 'olist_under_ga4', 'missing_ga4', 'missing_weekly'])
def test_isolation_and_inventory_failures_remain_rejected(issue):
    enabled = selection()
    if issue == 'old_count':
        enabled['dev'].remove('olist_0')
    elif issue == 'extra_dev':
        enabled['dev'].add('extra')
    elif issue == 'ga4_under_dev':
        enabled['dev'].remove('olist_0')
        enabled['dev'].add('stg_ga4_events')
    elif issue == 'olist_under_ga4':
        enabled['ga4_dev'].add('olist_0')
    elif issue == 'missing_ga4':
        enabled['ga4_dev'].remove('stg_ga4_events')
    else:
        enabled['dev'].remove('weekly_revenue_forecasting')
        enabled['dev'].add('replacement')
    with pytest.raises(AssertionError):
        validate_model_selection(enabled)
