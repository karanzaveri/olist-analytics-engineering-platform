"""Training-only Drift and statsmodels SES compared with unchanged baselines."""

import argparse
from dataclasses import dataclass
import math
from numbers import Real
import os
from pathlib import Path
import warnings

import numpy as np
import statsmodels
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from forecasting.backtesting import SCENARIOS, _csv, compare_scenarios
from forecasting.error_analysis import load_predictions
from forecasting.weekly_revenue import DEFAULT_OUTPUT, METHODS, _revenue, calculate_metrics, load_snapshot


ALL_MODELS = (*METHODS, 'drift', 'ses')


@dataclass(frozen=True)
class SESResult:
    forecast: float
    alpha: float
    training_sse: float
    initial_level: float
    scale: float


def _history(history):
    if len(history) < 2:
        raise ValueError('At least two training observations are required.')
    return [_revenue(value) for value in history]


def drift_forecast(history):
    values = _history(history)
    return values[-1] + (values[-1] - values[0]) / (len(values) - 1)


def ses_forecast(history, smoothing_level=None):
    """Fit alpha from training SSE only; optional fixed alpha supports verification.

    Predeclared optimizer: statsmodels grid-start search then L-BFGS-B, known
    initial level=first training actual, no bias removal/Box-Cox/trend/seasonality.
    Divide by training max (at least 1) for numeric stability; restore BRL units.
    Alpha endpoints 0/1 are valid fixed parameters. Optimized bounds are the
    library's internal epsilon bounds. Constant history uses alpha=0 deterministically.
    """
    values = _history(history)
    if smoothing_level is not None and (
        isinstance(smoothing_level, bool) or not isinstance(smoothing_level, Real)
        or not math.isfinite(smoothing_level) or not 0 <= smoothing_level <= 1
    ):
        raise ValueError('Smoothing alpha must be finite and in [0, 1].')
    scale = max(max(values), 1.0)
    if min(values) == max(values):
        return SESResult(values[-1], 0.0 if smoothing_level is None else float(smoothing_level),
                         0.0, values[0], scale)
    scaled = np.asarray(values) / scale
    model = SimpleExpSmoothing(scaled, initialization_method='known', initial_level=scaled[0])
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        try:
            fitted = model.fit(
                smoothing_level=smoothing_level, optimized=smoothing_level is None,
                method='L-BFGS-B', use_brute=True, remove_bias=False,
                minimize_kwargs={'options': {'maxiter': 1000, 'ftol': 1e-12, 'gtol': 1e-8}},
            )
        except ConvergenceWarning as exc:
            raise RuntimeError('SES optimization failed to converge on training history.') from exc
    if smoothing_level is None and not fitted.mle_retvals['success']:
        raise RuntimeError(f'SES optimizer failed: {fitted.mle_retvals}')
    alpha = float(fitted.params['smoothing_level'])
    prediction = float(fitted.forecast(1)[0]) * scale
    sse = float(fitted.sse) * scale**2
    if not 0 <= alpha <= 1 or not all(math.isfinite(value) for value in (alpha, prediction, sse)):
        raise RuntimeError('SES produced invalid parameters or forecasts.')
    return SESResult(prediction, alpha, sse, values[0], scale)


def evaluate_candidates(weeks):
    # Original evaluator validates the series, establishes shared dates, and
    # generates Naive/MA4/MA8 without any changes to their formulas.
    baseline_predictions, _ = compare_scenarios(weeks)
    predictions, metrics = {}, []
    for scenario, baseline in baseline_predictions.items():
        warmup = 74 if scenario == 'C_original' else 52
        source = weeks[:-1] if scenario == 'B_boundary' else weeks
        rows = []
        for index, row in enumerate(baseline, start=warmup):
            history = [week.weekly_revenue for week in source[:index]]
            ses = ses_forecast(history)
            rows.append({**row, 'drift': drift_forecast(history), 'ses': ses.forecast,
                         'training_count': index, 'training_end': source[index - 1].week_start,
                         'ses_alpha': ses.alpha, 'ses_training_sse': ses.training_sse,
                         'ses_initial_level': ses.initial_level, 'ses_training_scale': ses.scale})
        predictions[scenario] = rows
        actual = [row['actual_revenue'] for row in rows]
        scored = [
            {'scenario': scenario, 'model': name, 'forecast_count': len(rows),
             'forecast_start': rows[0]['week_start'], 'forecast_end': rows[-1]['week_start'],
             **calculate_metrics(actual, [row[name] for row in rows])}
            for name in ALL_MODELS
        ]
        for row in scored:
            for metric in ('mae', 'rmse', 'wape_pct'):
                row[f'{metric}_rank'] = None if row[metric] is None else 1 + sum(
                    other[metric] is not None and other[metric] < row[metric] for other in scored)
        metrics.extend(scored)
    return predictions, metrics


def export_results(predictions, metrics, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    _csv(output_dir / 'predictions.csv', [{'scenario': scenario, **row}
         for scenario, rows in predictions.items() for row in rows])
    _csv(output_dir / 'metrics.csv', metrics)
    improvements = []
    for scenario in SCENARIOS:
        naive = next(row for row in metrics if row['scenario'] == scenario and row['model'] == 'naive')
        for row in (r for r in metrics if r['scenario'] == scenario and r['model'] in ('drift', 'ses')):
            improvements.append({'scenario': scenario, 'model': row['model'],
                **{f'{metric}_reduction_pct': 100 * (naive[metric] - row[metric]) / naive[metric]
                   if naive[metric] else None for metric in ('mae', 'rmse')},
                'wape_reduction_pp': naive['wape_pct'] - row['wape_pct']
                    if naive['wape_pct'] is not None else None})
    _csv(output_dir / 'improvements_vs_naive.csv', improvements)
    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
    for axis, metric, label in zip(axes, ('mae', 'rmse', 'wape_pct'), ('MAE (BRL)', 'RMSE (BRL)', 'WAPE (%)')):
        for index, name in enumerate(ALL_MODELS):
            values = [next(row[metric] for row in metrics if row['scenario'] == scenario and row['model'] == name)
                      for scenario in SCENARIOS]
            axis.bar([position + (index - 2) * 0.15 for position in range(3)],
                     [float('nan') if value is None else value for value in values], width=0.15, label=name.upper())
        axis.set_xticks(range(3), ['A: Full\n34 targets', 'B: Boundary\n33 targets', 'C: Holdout\n12 targets'])
        axis.set(title=label, ylabel=label)
        axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}' if metric != 'wape_pct' else '{x:.1f}'))
        axis.grid(axis='y', alpha=0.2)
        axis.set_axisbelow(True)
        axis.legend(fontsize=8)
    fig.suptitle('Five models on identical one-week-ahead targets within each scenario')
    fig.savefig(output_dir / 'candidate_comparison.png', dpi=160)
    plt.close(fig)

    lines = ['# Drift and SES statistical candidates', '',
             f'Offline saved EU mart snapshot; statsmodels {statsmodels.__version__}. No warehouse access.',
             'A: 52-week warm-up, 34 targets January 1-August 20, 2018.',
             'B: 52-week warm-up, 33 targets January 1-August 13, 2018.',
             'C: 74-week warm-up, 12 targets June 4-August 20, 2018.',
             'All five methods use identical actuals and strictly prior information within each scenario.', '',
             'Drift = last + (last - first)/(training count - 1); no clipping or formula changes.',
             'SES uses statsmodels SimpleExpSmoothing, known initial level=first training value, no bias adjustment.',
             'Alpha is re-estimated at every origin from training SSE only: grid-start search plus L-BFGS-B,',
             'maxiter=1000, ftol=1e-12, gtol=1e-8, on training-max-scaled revenue. No target-based tuning.',
             'No trend, seasonality or Box-Cox component is used. Library optimized alpha bounds are epsilon-interior;',
             'fixed alpha 0/1 are supported. Constant history has tied alpha fits and uses alpha=0 deterministically.',
             'Fits must converge and produce valid finite parameters. Predictions CSV records alpha, training-end/count,',
             'initial level, scaling factor and training SSE. CSV precision is retained; report rounding is presentation only.', '',
             '| Scenario | Model | MAE | RMSE | WAPE (%) | Bias | MAE rank | WAPE rank | RMSE rank |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in metrics:
        wape = 'undefined' if row['wape_pct'] is None else f"{row['wape_pct']:.2f}"
        lines.append(f"| {row['scenario']} | {row['model'].upper()} | {row['mae']:,.2f} | {row['rmse']:,.2f} | "
                     f"{wape} | {row['mean_bias']:,.2f} | {row['mae_rank']} | {row['wape_pct_rank']} | {row['rmse_rank']} |")
    lines += ['', 'Currency metrics are BRL; bias = forecast minus actual. Rankings use full precision, so tiny numerical',
              'differences may create different ranks even when presentation values look tied.', '', '## Metric trade-offs', '']
    for scenario in SCENARIOS:
        for metric in ('mae', 'wape_pct', 'rmse'):
            subset = [row for row in metrics if row['scenario'] == scenario and row[metric] is not None]
            best = min((row[metric] for row in subset), default=None)
            winners = ', '.join(row['model'].upper() for row in subset if row[metric] == best)
            lines.append(f'- {scenario} best {metric}: {winners or "undefined"}.')
    lines += ['', '| Scenario | Candidate | MAE reduction vs Naive (%) | RMSE reduction (%) | WAPE reduction (pp) |',
              '| --- | --- | ---: | ---: | ---: |']
    for row in improvements:
        formatted = [('undefined' if row[key] is None else f'{row[key]:.4f}')
                     for key in ('mae_reduction_pct', 'rmse_reduction_pct', 'wape_reduction_pp')]
        lines.append(f"| {row['scenario']} | {row['model'].upper()} | {' | '.join(formatted)} |")
    lines += ['', 'Positive reductions indicate lower error; negative means worse. No model is universally best merely',
              'because it wins one criterion. RMSE emphasizes large errors more strongly than MAE; WAPE and MAE rankings',
              'agree within a scenario because their denominators are shared. Consider the absolute reductions and',
              'ranking sensitivity, not just a numerical winner. No statistical significance of improvement is claimed.', '',
              '## Limitations and next steps', '',
              'Only 86 historical weeks and overlapping forecast origins are available; scenarios are not independent experiments.',
              'Boundary exclusion is sensitivity analysis, not proof of corruption; the cause of the raw-order drop is unresolved.',
              'Data use current delivered status, not historical as-of status. Source maturity, revision risk and cutoff choice',
              'need auditing. No annual seasonality is established or introduced. Check longer rolling windows, untouched',
              'holdouts, residual structure, uncertainty and business loss before adoption. Do not tune models on these targets.',
              'Drift can be negative for declining nonnegative histories; it is never silently clipped. The current shared',
              'metric contract rejects negative predictions, so future such cases require an explicit evaluation-policy decision.', '']
    (output_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_OUTPUT / 'source_snapshot.csv')
    parser.add_argument('--original-predictions', type=Path, default=DEFAULT_OUTPUT / 'predictions.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT / 'statistical_candidates')
    args = parser.parse_args()
    predictions, metrics = evaluate_candidates(load_snapshot(args.snapshot))
    saved = load_predictions(args.original_predictions)
    original = [{key: row[key] for key in ('week_start', 'actual_revenue', *METHODS)}
                for row in predictions['C_original']]
    if original != saved:
        raise ValueError('Original baseline holdout changed; investigate snapshot provenance.')
    export_results(predictions, metrics, args.output_dir)
    for row in metrics:
        print(row)
    print('Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
