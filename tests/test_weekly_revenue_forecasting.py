"""Synthetic forecasting and source-contract checks; no warehouse access."""

import csv
from datetime import date, timedelta
import math
from unittest.mock import Mock

import pytest

from forecasting import weekly_revenue as model


def rows(count=86):
    return [{'week_start': date(2017, 1, 2) + timedelta(weeks=i),
             'week_end': date(2017, 1, 8) + timedelta(weeks=i),
             'weekly_revenue': float(i + 1), 'missing_payment_orders': 0}
            for i in range(count)]


def test_forecasts_use_exact_trailing_windows():
    assert model.forecast_history(list(range(1, 11))) == {'naive': 10, 'ma4': 8.5, 'ma8': 6.5}


def test_chronological_backtest_and_evaluation_actuals():
    weeks = model.validate_weeks(rows(12), expected_count=12)
    result = model.backtest(weeks, initial_history=8, evaluation_weeks=4)
    assert [r['naive'] for r in result] == [8, 9, 10, 11]
    assert [r['ma4'] for r in result] == [6.5, 7.5, 8.5, 9.5]
    assert [r['ma8'] for r in result] == [4.5, 5.5, 6.5, 7.5]
    assert result[0]['actual_revenue'] == 9
    assert result[0]['week_start'] == weeks[8].week_start


def test_future_and_target_actuals_cannot_change_their_forecasts():
    original = rows(12)
    modified = rows(12)
    modified[9]['weekly_revenue'] = 10000
    modified[11]['weekly_revenue'] = 90000
    baseline = model.backtest(model.validate_weeks(original, 12), 8, 4)
    changed = model.backtest(model.validate_weeks(modified, 12), 8, 4)
    for index in (0, 1):
        assert {key: baseline[index][key] for key in model.METHODS} == {
            key: changed[index][key] for key in model.METHODS}
    assert changed[2]['naive'] == 10000  # now observed, available at the next origin


def test_metrics_definitions_and_bias_sign():
    result = model.calculate_metrics([10, 20], [12, 16])
    assert result == pytest.approx({'mae': 3, 'rmse': math.sqrt(10), 'wape_pct': 20, 'mean_bias': -1})
    assert model.calculate_metrics([10], [15])['mean_bias'] == 5
    assert model.calculate_metrics([0, 0], [0, 1])['wape_pct'] is None


@pytest.mark.parametrize('actual,predictions', [([], []), ([1], []), ([None], [1]), ([1], [math.nan])])
def test_invalid_metric_inputs(actual, predictions):
    with pytest.raises(ValueError):
        model.calculate_metrics(actual, predictions)


def test_insufficient_history_and_invalid_split():
    with pytest.raises(ValueError, match='eight'):
        model.forecast_history([1] * 7)
    weeks = model.validate_weeks(rows(12), 12)
    with pytest.raises(ValueError):
        model.backtest(weeks, 7, 5)
    with pytest.raises(ValueError):
        model.backtest(weeks, 8, 3)


@pytest.mark.parametrize('value', [None, -1, math.nan, math.inf, -math.inf, 'invalid', '12', True])
def test_reject_invalid_revenue(value):
    data = rows(2)
    data[0]['weekly_revenue'] = value
    with pytest.raises(ValueError, match='Revenue'):
        model.validate_weeks(data, 2)


@pytest.mark.parametrize('issue', ['missing', 'duplicate', 'reversed', 'boundary', 'null_date', 'payments'])
def test_reject_invalid_weekly_contract(issue):
    data = rows(3)
    if issue == 'missing':
        data.pop(1)
    elif issue == 'duplicate':
        data[1] = data[0].copy()
    elif issue == 'reversed':
        data.reverse()
    elif issue == 'boundary':
        data[0]['week_end'] += timedelta(days=1)
    elif issue == 'null_date':
        data[0]['week_start'] = None
    else:
        data[0]['missing_payment_orders'] = 1
    with pytest.raises(ValueError):
        model.validate_weeks(data, expected_count=len(data))


def test_expected_count_and_historical_boundaries():
    with pytest.raises(ValueError, match='86'):
        model.validate_weeks(rows(85))
    with pytest.raises(ValueError, match='first week'):
        model.validate_weeks(rows(), expected_start=date(2017, 1, 9))
    with pytest.raises(ValueError, match='last week'):
        model.validate_weeks(rows(), expected_end=date(2018, 8, 27))
    data = rows()
    data[0]['weekly_revenue'] = 0
    assert model.validate_weeks(data)[0].weekly_revenue == 0


def test_bigquery_extraction_is_ordered_read_only_and_explicitly_eu(monkeypatch):
    client = Mock()
    client.query.return_value.result.return_value = rows()
    factory = Mock(return_value=client)
    monkeypatch.setattr(model.bigquery, 'Client', factory)
    assert len(model.fetch_weeks()) == 86
    factory.assert_called_once_with(project=model.PROJECT, location='EU')
    client.query.assert_called_once_with(model.QUERY, location='EU')
    assert model.QUERY.startswith('SELECT week_start, week_end, weekly_revenue, missing_payment_orders')
    assert model.QUERY.endswith('ORDER BY week_start')
    assert '*' not in model.QUERY


def test_exports_and_snapshot_replay(tmp_path):
    weeks = model.validate_weeks(rows())
    metrics = model.export_results(weeks, tmp_path, 'synthetic offline fixture')
    assert len(metrics) == 3
    assert model.load_snapshot(tmp_path / 'source_snapshot.csv') == weeks
    with (tmp_path / 'predictions.csv').open(newline='') as stream:
        predictions = list(csv.DictReader(stream))
    assert len(predictions) == 12
    assert predictions[0]['week_start'] == '2018-06-04'
    assert float(predictions[0]['naive']) == 74
    assert (tmp_path / 'forecast_comparison.png').read_bytes().startswith(b'\x89PNG')
    assert 'Best baseline by MAE: **NAIVE**' in (tmp_path / 'report.md').read_text(encoding='utf-8')
