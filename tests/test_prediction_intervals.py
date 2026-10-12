"""Synthetic interval chronology, empirical order-statistic and coverage checks."""

from datetime import date, timedelta
import pytest

from forecasting.prediction_intervals import compare_intervals, empirical_radius, interval_summary, sequential_intervals
from forecasting.weekly_revenue import Week


def predictions():
    return [{'week_start': date(2018, 1, 1) + timedelta(weeks=i),
             'naive': 100, 'actual_revenue': 100 + i + 1} for i in range(24)]


def test_finite_sample_order_statistic_and_insufficient_history():
    assert empirical_radius(list(range(1, 21)), 0.8) == 17
    assert empirical_radius(list(range(1, 21)), 0.9) == 19
    assert empirical_radius([1] * 19, 0.8) is None
    assert empirical_radius([1] * 20, 0.99) is None  # k>n, do not silently clamp
    with pytest.raises(ValueError):
        empirical_radius([1] * 20, 1)


def test_calibration_precedes_current_target_and_future_errors():
    original = predictions()
    changed = [row.copy() for row in original]
    changed[20]['actual_revenue'] = 100000
    a, b = sequential_intervals(original), sequential_intervals(changed)
    for index in range(42):  # first 21 origins, both nominal levels
        for key in ('radius', 'lower', 'upper', 'calibration_count', 'calibration_end'):
            assert a[index][key] == b[index][key]
    assert a[40]['radius'] == 17  # uses prior errors 1..20, excludes current error 21
    assert a[40]['calibration_end'] < a[40]['week_start']
    assert a[-1]['radius'] != b[-1]['radius']  # changed error admitted only at later origins


def test_clipping_and_inclusive_coverage():
    data = [{'week_start': date(2018, 1, 1), 'naive': 1, 'actual_revenue': 11},
            {'week_start': date(2018, 1, 8), 'naive': 2, 'actual_revenue': 0}]
    rows = sequential_intervals(data, levels=(0.5,), minimum=1)
    assert rows[0]['covered'] is None
    assert rows[1]['radius'] == 10
    assert rows[1]['raw_lower'] == -8
    assert rows[1]['lower'] == 0 and rows[1]['upper'] == 12
    assert rows[1]['interval_width'] == 12 and rows[1]['covered'] is True
    summary = interval_summary(rows)[0]
    assert summary['evaluated_forecasts'] == 1
    assert summary['skipped_forecasts'] == 1
    assert summary['observed_coverage_pct'] == 100
    assert summary['average_width_brl'] == 12


def test_skipped_origins_do_not_enter_coverage_denominator():
    rows = sequential_intervals(predictions()[:20])
    assert all(row['status'].startswith('Skipped') for row in rows)
    assert all(row['evaluated_forecasts'] == 0 and row['observed_coverage_pct'] is None
               for row in interval_summary(rows))
    summaries = interval_summary(sequential_intervals(predictions()))
    assert all(row['evaluated_forecasts'] == 4 and row['skipped_forecasts'] == 20 for row in summaries)
    assert summaries[0]['outside_count'] == 4


def test_boundary_removes_only_final_origin_preserving_all_shared_intervals():
    weeks = [Week(date(2017, 1, 2) + timedelta(weeks=i),
                  date(2017, 1, 8) + timedelta(weeks=i), float(i + 1)) for i in range(86)]
    rows, summaries = compare_intervals(weeks)
    a = [{key: value for key, value in row.items() if key != 'scenario'} for row in rows if row['scenario'] == 'A_full']
    b = [{key: value for key, value in row.items() if key != 'scenario'} for row in rows if row['scenario'] == 'B_boundary']
    assert a[:-2] == b
    assert [row['evaluated_forecasts'] for row in summaries] == [14, 14, 13, 13]
    assert all(row['first_evaluated_week'] == date(2018, 5, 21) for row in summaries)
