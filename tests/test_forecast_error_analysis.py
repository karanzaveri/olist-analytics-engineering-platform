"""Offline checks for diagnostic signs, denominators, and error ranking."""

from datetime import date, timedelta
import pytest

from forecasting.error_analysis import analyze_errors, percentage, summarize, top_errors


def example(actual=100, previous=80, forecasts=(110, 90, 100)):
    week = date(2018, 6, 4)
    rows = [{'week_start': week, 'actual_revenue': actual,
             'naive': forecasts[0], 'ma4': forecasts[1], 'ma8': forecasts[2]}]
    return analyze_errors(rows, {week: actual, week - timedelta(days=7): previous})


def test_sign_absolute_error_and_percentage_conventions():
    rows = example()
    assert [r['signed_error'] for r in rows] == [10, -10, 0]
    assert [r['absolute_error'] for r in rows] == [10, 10, 0]
    assert [r['absolute_percentage_error'] for r in rows] == [10, 10, 0]
    assert all(r['actual_wow_change'] == 20 and r['actual_wow_change_pct'] == 25 for r in rows)
    assert all(r['revenue_direction'] == 'Increase' for r in rows)


def test_zero_actual_and_prior_are_undefined_percentages():
    rows = example(actual=0, previous=0, forecasts=(10, 0, 5))
    assert all(r['absolute_percentage_error'] is None for r in rows)
    assert all(r['actual_wow_change_pct'] is None for r in rows)
    assert rows[0]['absolute_error'] == 10
    assert percentage(1, 0) is None


def test_over_under_and_exact_use_all_weeks_as_denominator():
    rows = example()
    stats = summarize(rows)
    assert stats['overprediction_pct'] == pytest.approx(100 / 3)
    assert stats['underprediction_pct'] == pytest.approx(100 / 3)
    assert stats['exact_pct'] == pytest.approx(100 / 3)
    assert stats['mean_bias'] == 0
    assert sum(stats[k] for k in ['overprediction_pct', 'underprediction_pct', 'exact_pct']) == pytest.approx(100)


def test_ranking_uses_absolute_magnitude_and_stable_date_ties():
    week = date(2018, 6, 4)
    rows = [{'model': 'naive', 'week_start': week + timedelta(weeks=i), 'absolute_error': value}
            for i, value in enumerate([2, 50, 10, 50, 1, 30])]
    rows.append({'model': 'ma4', 'week_start': week, 'absolute_error': 999})
    ranked = top_errors(list(reversed(rows)), 'naive')
    assert [r['absolute_error'] for r in ranked] == [50, 50, 30, 10, 2]
    assert ranked[0]['week_start'] < ranked[1]['week_start']


def test_decreases_and_snapshot_mismatch():
    assert example(actual=50)[0]['revenue_direction'] == 'Decrease'
    week = date(2018, 6, 4)
    prediction = {'week_start': week, 'actual_revenue': 50, 'naive': 60, 'ma4': 60, 'ma8': 60}
    with pytest.raises(ValueError, match='snapshot'):
        analyze_errors([prediction], {week: 100, week - timedelta(days=7): 60})
    with pytest.raises(ValueError, match='finite'):
        analyze_errors([prediction], {week: 50})


def test_invalid_evaluation_dates():
    week = date(2018, 6, 4)
    prediction = {'week_start': week, 'actual_revenue': 50, 'naive': 60, 'ma4': 60, 'ma8': 60}
    with pytest.raises(ValueError, match='consecutive'):
        analyze_errors([prediction, prediction], {week: 50, week - timedelta(days=7): 60})
