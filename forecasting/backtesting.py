"""Offline rolling-origin and flagged-endpoint sensitivity comparisons."""

import argparse
import csv
from datetime import date
import os
from pathlib import Path

from forecasting.error_analysis import load_predictions
from forecasting.weekly_revenue import (
    DEFAULT_OUTPUT, METHODS, backtest, calculate_metrics, load_snapshot, validate_weeks,
)


SCENARIOS = {
    'A_full': 'Full 86-week series; 52-week warm-up',
    'B_boundary': 'First 85 weeks; exclude flagged August 20 endpoint',
    'C_original': 'Original 12-week holdout; 74-week warm-up',
}
FLAGGED_WEEK = date(2018, 8, 20)


def rolling_origin(weeks, initial_history=52):
    """Reuse the original leakage-free evaluator at every subsequent origin."""
    return backtest(weeks, initial_history=initial_history,
                    evaluation_weeks=len(weeks) - initial_history)


def compare_scenarios(weeks):
    """Remove only the predeclared final observation; keep the original holdout."""
    validate_weeks([vars(week) for week in weeks], expected_count=86,
                   expected_start=date(2017, 1, 2), expected_end=FLAGGED_WEEK)
    predictions = {
        'A_full': rolling_origin(weeks),
        'B_boundary': rolling_origin(weeks[:-1]),
        'C_original': backtest(weeks),
    }
    metrics = []
    for scenario, rows in predictions.items():
        actual = [row['actual_revenue'] for row in rows]
        scenario_metrics = [
            {'scenario': scenario, 'model': name,
             'initial_history_weeks': 74 if scenario == 'C_original' else 52,
             'source_weeks': 85 if scenario == 'B_boundary' else 86,
             'forecast_count': len(rows), 'forecast_start': rows[0]['week_start'],
             'forecast_end': rows[-1]['week_start'],
             **calculate_metrics(actual, [row[name] for row in rows])}
            for name in METHODS
        ]
        for row in scenario_metrics:
            # Competition ranks preserve ties. WAPE is undefined for all-zero actuals.
            for metric in ('mae', 'wape_pct'):
                row[f'{metric}_rank'] = (None if row[metric] is None else
                    1 + sum(other[metric] is not None and other[metric] < row[metric]
                            for other in scenario_metrics))
        metrics.extend(scenario_metrics)
    return predictions, metrics


def boundary_deltas(metrics):
    """B minus A; changes are sensitivity to one endpoint, not a new experiment."""
    result = []
    for name in METHODS:
        full = next(row for row in metrics if row['scenario'] == 'A_full' and row['model'] == name)
        boundary = next(row for row in metrics if row['scenario'] == 'B_boundary' and row['model'] == name)
        result.append({'model': name,
                       **{f'{metric}_change': boundary[metric] - full[metric]
                          if boundary[metric] is not None and full[metric] is not None else None
                          for metric in ('mae', 'rmse', 'wape_pct', 'mean_bias')},
                       'full_mae_rank': full['mae_rank'], 'boundary_mae_rank': boundary['mae_rank'],
                       'full_wape_rank': full['wape_pct_rank'], 'boundary_wape_rank': boundary['wape_pct_rank']})
    return result


def _csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _format(value):
    return 'undefined' if value is None else f'{value:,.2f}'


def export_comparison(predictions, metrics, output_dir, snapshot):
    output_dir.mkdir(parents=True, exist_ok=True)
    _csv(output_dir / 'predictions.csv',
         [{'scenario': scenario, **row} for scenario, rows in predictions.items() for row in rows])
    _csv(output_dir / 'metrics.csv', metrics)
    deltas = boundary_deltas(metrics)
    _csv(output_dir / 'boundary_deltas.csv', deltas)

    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
    labels = ['A: Full\n34 forecasts', 'B: Exclude endpoint\n33 forecasts', 'C: Original holdout\n12 forecasts']
    for axis, metric, title in zip(axes, ('mae', 'wape_pct'), ('MAE (BRL)', 'WAPE (%)')):
        for index, name in enumerate(METHODS):
            values = [next(row[metric] for row in metrics
                           if row['scenario'] == scenario and row['model'] == name)
                      for scenario in SCENARIOS]
            axis.bar([position + (index - 1) * 0.24 for position in range(3)],
                     [float('nan') if value is None else value for value in values],
                     width=0.24, label=name.upper())
        axis.set_xticks(range(3), labels)
        axis.set(title=title, ylabel=title)
        axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}' if metric == 'mae' else '{x:.1f}'))
        axis.grid(axis='y', alpha=0.2)
        axis.set_axisbelow(True)
        axis.legend()
    fig.suptitle('One-week-ahead revenue forecasts: rolling origins and endpoint sensitivity')
    fig.savefig(output_dir / 'backtesting_comparison.png', dpi=160)
    plt.close(fig)

    lines = ['# Rolling-origin backtesting and boundary sensitivity', '',
             f'Input: `{snapshot}`; saved EU mart snapshot only. No warehouse queries or rebuilds.',
             'All predictions reuse the existing Naive, MA4, MA8 and metric functions without formula changes.',
             'Each target uses strictly earlier actuals. After each forecast the observed actual enters the next origin.',
             'The history expands, although moving-average formulas always retain their fixed trailing windows.', '',
             '| Scenario | Source weeks | Initial history | Forecasts | First target | Last target |',
             '| --- | ---: | ---: | ---: | --- | --- |']
    for scenario in SCENARIOS:
        row = next(row for row in metrics if row['scenario'] == scenario)
        lines.append(f"| {scenario}: {SCENARIOS[scenario]} | {row['source_weeks']} | "
                     f"{row['initial_history_weeks']} | {row['forecast_count']} | "
                     f"{row['forecast_start']} | {row['forecast_end']} |")
    lines += ['', '| Scenario | Model | MAE (BRL) | RMSE (BRL) | WAPE (%) | Signed bias (BRL) | MAE rank | WAPE rank |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in metrics:
        lines.append(f"| {row['scenario']} | {row['model'].upper()} | {_format(row['mae'])} | "
                     f"{_format(row['rmse'])} | {_format(row['wape_pct'])} | {_format(row['mean_bias'])} | "
                     f"{row['mae_rank']} | {row['wape_pct_rank']} |")
    lines += ['', '## Rankings and boundary effect', '']
    for scenario in SCENARIOS:
        subset = [row for row in metrics if row['scenario'] == scenario]
        for metric in ('mae', 'wape_pct'):
            ranked = sorted((row for row in subset if row[metric] is not None), key=lambda row: row[metric])
            ranking = ', '.join(f"{row['model'].upper()} (rank {row[f'{metric}_rank']})" for row in ranked)
            lines.append(f'- {scenario} {metric}: {ranking or "undefined"}.')
    lines += ['', 'Changes below are B minus A; WAPE changes are percentage points.', '',
              '| Model | MAE change (BRL) | RMSE change (BRL) | WAPE change (pp) | Bias change (BRL) |',
              '| --- | ---: | ---: | ---: | ---: |']
    for row in deltas:
        lines.append(f"| {row['model'].upper()} | {_format(row['mae_change'])} | "
                     f"{_format(row['rmse_change'])} | {_format(row['wape_pct_change'])} | "
                     f"{_format(row['mean_bias_change'])} |")
    lines += ['', '## Interpretation and unresolved issues', '',
              'A and B have identical forecasts at all shared origins; B removes only the August 20 target and its error.',
              'C preserves the original predictions exactly and overlaps the last 12 origins of A.',
              'Within a scenario, MAE and WAPE rank identically because all models share the same actual-revenue denominator.',
              'Bias is forecast minus actual; positive means overprediction. WAPE is undefined if all actuals are zero.',
              'CSV values retain precision; report and chart formatting round only for presentation.', '',
              'Rolling forecasts share history and overlapping trailing windows; they are not independent experiments.',
              'Scenario C covers a different period and cannot be compared with A as an independent method experiment.',
              'Excluding the flagged endpoint is sensitivity analysis, not proof of data corruption, and does not establish',
              'a business cause for the raw-order decline. Keep both full and excluded-endpoint scores visible.',
              'The exact cause remains unresolved. Audit source-end coverage, status maturity, and purchase/payment',
              'revisions before choosing the operational training cutoff. These are retrospective current-status data,',
              'not historical as-of snapshots. Confirm point-in-time availability before making production claims.',
              'Before advanced models, inspect residual autocorrelation and seasonality, use more rolling origins or',
              'a separate untouched holdout, and assess uncertainty and robustness across periods. Model selection on',
              'these same observations remains exploratory; only 86 weekly observations are available.', '']
    (output_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_OUTPUT / 'source_snapshot.csv')
    parser.add_argument('--original-predictions', type=Path, default=DEFAULT_OUTPUT / 'predictions.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT / 'backtesting')
    args = parser.parse_args()
    predictions, metrics = compare_scenarios(load_snapshot(args.snapshot))
    if predictions['C_original'] != load_predictions(args.original_predictions):
        raise ValueError('Recomputed original holdout differs from saved predictions; investigate input provenance.')
    export_comparison(predictions, metrics, args.output_dir, args.snapshot)
    for row in metrics:
        print(row)
    print('Original holdout predictions match saved CSV exactly. Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
