"""Synthetic rolling-origin alignment and endpoint-only exclusion checks."""

from dataclasses import replace
from datetime import date, timedelta
import pytest

from forecasting.backtesting import compare_scenarios, rolling_origin
from forecasting.weekly_revenue import Week, backtest


def weeks(count=86):
    return [Week(date(2017, 1, 2) + timedelta(weeks=i),
                 date(2017, 1, 8) + timedelta(weeks=i), float(i + 1)) for i in range(count)]


def test_52_week_warmup_and_exact_alignment():
    rows = rolling_origin(weeks())
    assert len(rows) == 34
    assert rows[0]['week_start'] == date(2018, 1, 1)
    assert rows[-1]['week_start'] == date(2018, 8, 20)
    assert rows[0]['actual_revenue'] == 53
    assert rows[0]['naive'] == 52
    assert rows[0]['ma4'] == 50.5
    assert rows[0]['ma8'] == 48.5


def test_actual_is_added_only_at_next_origin_without_future_leakage():
    original = weeks()
    modified = weeks()
    modified[55] = replace(modified[55], weekly_revenue=10000)
    modified[-1] = replace(modified[-1], weekly_revenue=20000)
    a, b = rolling_origin(original), rolling_origin(modified)
    for index in range(4):  # target index 55 included: its changed actual must not affect its prediction
        for name in ('naive', 'ma4', 'ma8'):
            assert a[index][name] == b[index][name]
    assert b[4]['naive'] == 10000
    assert b[4]['ma4'] == pytest.approx((53 + 54 + 55 + 10000) / 4)
    assert a[-1]['naive'] == b[-1]['naive']
    assert [row['naive'] for row in a] == list(range(52, 86))


def test_boundary_removes_only_final_target_and_original_holdout_is_unchanged():
    source = weeks()
    predictions, metrics = compare_scenarios(source)
    assert predictions['B_boundary'] == predictions['A_full'][:-1]
    assert len(predictions['B_boundary']) == 33
    assert predictions['B_boundary'][-1]['week_start'] == date(2018, 8, 13)
    assert predictions['C_original'] == backtest(source)
    assert predictions['C_original'] == predictions['A_full'][-12:]
    assert len(source) == 86  # input is not mutated
    assert len(metrics) == 9
    for row in metrics:
        assert row['forecast_count'] == {'A_full': 34, 'B_boundary': 33, 'C_original': 12}[row['scenario']]
        assert row['mae_rank'] == row['wape_pct_rank']


def test_insufficient_warmup_and_wrong_endpoint_are_rejected():
    with pytest.raises(ValueError):
        rolling_origin(weeks(52))
    with pytest.raises(ValueError):
        rolling_origin(weeks(), initial_history=7)
    shifted = [replace(week, week_start=week.week_start + timedelta(days=7),
                       week_end=week.week_end + timedelta(days=7)) for week in weeks()]
    with pytest.raises(ValueError, match='first week|last week'):
        compare_scenarios(shifted)


def test_tied_ranks_and_zero_total_wape():
    predictions, metrics = compare_scenarios([replace(week, weekly_revenue=0) for week in weeks()])
    assert all(row['mae_rank'] == 1 for row in metrics)
    assert all(row['wape_pct'] is None and row['wape_pct_rank'] is None for row in metrics)
