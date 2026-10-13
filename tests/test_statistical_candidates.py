"""Synthetic candidate arithmetic, train-only fitting and shared-origin checks."""

from dataclasses import replace
from datetime import date, timedelta
from unittest.mock import Mock
import pytest
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from forecasting import statistical_candidates as model
from forecasting.weekly_revenue import Week


def weeks():
    return [Week(date(2017, 1, 2) + timedelta(weeks=i),
                 date(2017, 1, 8) + timedelta(weeks=i), float(i + 1)) for i in range(86)]


def test_drift_arithmetic_includes_all_historical_intervals():
    assert model.drift_forecast([10, 20, 30]) == 40
    assert model.drift_forecast([10, 99, 20]) == 25
    assert model.drift_forecast([10, 10]) == 10
    assert model.drift_forecast([100, 0]) == -100  # no silent clipping
    with pytest.raises(ValueError):
        model.drift_forecast([1])


@pytest.mark.parametrize('alpha,expected', [(0, 10), (0.5, 22.5), (1, 30)])
def test_ses_known_initial_level_and_fixed_alpha(alpha, expected):
    result = model.ses_forecast([10, 20, 30], smoothing_level=alpha)
    assert result.forecast == pytest.approx(expected)
    assert result.alpha == alpha
    assert result.initial_level == 10


@pytest.mark.parametrize('alpha', [-0.1, 1.1, float('nan'), float('inf'), True, '0.5'])
def test_invalid_alpha_rejected(alpha):
    with pytest.raises(ValueError, match='alpha'):
        model.ses_forecast([10, 20, 30], smoothing_level=alpha)


def test_optimized_ses_reproducible_bounded_and_scale_equivariant():
    history = [10, 20, 15, 24, 19, 28, 25, 30]
    a, b = model.ses_forecast(history), model.ses_forecast(history)
    assert a == b
    assert 0 <= a.alpha <= 1
    c = model.ses_forecast([value * 100 for value in history])
    assert c.alpha == pytest.approx(a.alpha, abs=1e-6)
    assert c.forecast == pytest.approx(a.forecast * 100, rel=1e-6)
    assert model.ses_forecast([5, 5, 5]).forecast == 5
    assert model.ses_forecast([0, 0]).alpha == 0


def test_each_fit_receives_only_prior_history_and_identical_target_alignment(monkeypatch):
    histories = []

    def fitted(history):
        histories.append(history.copy())
        return model.SESResult(history[-1], 0.5, 0, history[0], max(history))

    monkeypatch.setattr(model, 'ses_forecast', fitted)
    predictions, metrics = model.evaluate_candidates(weeks())
    assert len(histories) == 34 + 33 + 12
    assert histories[0] == list(range(1, 53))
    assert histories[1] == list(range(1, 54))
    assert histories[34] == list(range(1, 53))
    assert histories[67] == list(range(1, 75))
    assert predictions['A_full'][:-1] == predictions['B_boundary']
    assert len(metrics) == 15
    for scenario, rows in predictions.items():
        assert len(rows) == {'A_full': 34, 'B_boundary': 33, 'C_original': 12}[scenario]
        assert all(row['training_end'] < row['week_start'] for row in rows)
        assert all(row['ses'] == row['naive'] for row in rows)


def test_future_target_cannot_affect_candidate_fit_or_prediction():
    source = weeks()
    modified = source.copy()
    modified[52] = replace(modified[52], weekly_revenue=100)
    a, _ = model.evaluate_candidates(source)
    b, _ = model.evaluate_candidates(modified)
    for key in ('drift', 'ses', 'ses_alpha', 'ses_training_sse'):
        assert a['A_full'][0][key] == b['A_full'][0][key]
    assert a['A_full'][1]['drift'] != b['A_full'][1]['drift']


def test_nonconvergence_is_an_error_not_a_naive_fallback(monkeypatch):
    library_model = Mock()
    library_model.fit.side_effect = ConvergenceWarning('Synthetic optimizer failure')
    monkeypatch.setattr(model, 'SimpleExpSmoothing', Mock(return_value=library_model))
    with pytest.raises(RuntimeError, match='converge'):
        model.ses_forecast([10, 20, 30])


def test_cli_checks_explicit_original_predictions_path(monkeypatch, tmp_path):
    import sys

    snapshot = tmp_path / 'input.csv'
    saved_predictions = tmp_path / 'original.csv'
    output = tmp_path / 'results'
    source = weeks()
    baseline, _ = model.compare_scenarios(source)
    loaded = Mock(return_value=baseline['C_original'])
    exported = Mock()
    monkeypatch.setattr(sys, 'argv', [
        'statistical_candidates', '--snapshot', str(snapshot),
        '--original-predictions', str(saved_predictions), '--output-dir', str(output),
    ])
    monkeypatch.setattr(model, 'load_snapshot', Mock(return_value=source))
    monkeypatch.setattr(model, 'load_predictions', loaded)
    monkeypatch.setattr(model, 'evaluate_candidates', Mock(return_value=(baseline, [])))
    monkeypatch.setattr(model, 'export_results', exported)

    model.main()

    loaded.assert_called_once_with(saved_predictions)
    exported.assert_called_once_with(baseline, [], output)
