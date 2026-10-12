"""Offline diagnostics of saved one-week-ahead baseline predictions."""

import argparse
import csv
from datetime import date, timedelta
import math
import os
from pathlib import Path

from forecasting.weekly_revenue import DEFAULT_OUTPUT, METHODS, load_snapshot


def percentage(numerator, denominator):
    """Percentage points; undefined denominators remain None, never zero-filled."""
    return 100 * numerator / denominator if denominator else None


def analyze_errors(predictions, history):
    """Return one diagnostic row per week/model; history supplies prior actuals.

    history is a date-to-actual mapping from the saved source snapshot. No model
    forecasts are recalculated. The target actual must match the same snapshot.
    """
    if not predictions:
        raise ValueError('Predictions must not be empty.')
    result = []
    previous_week = None
    for row in predictions:
        week = row['week_start']
        if type(week) is not date or week.weekday() != 0:
            raise ValueError('Evaluation dates must be Mondays.')
        if previous_week is not None and week != previous_week + timedelta(days=7):
            raise ValueError('Evaluation weeks must be unique, ordered, and consecutive.')
        previous_week = week
        actual = row['actual_revenue']
        prior = history.get(week - timedelta(days=7))
        snapshot_actual = history.get(week)
        for value in (actual, prior, snapshot_actual, *(row[name] for name in METHODS)):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError('Actuals, prior history, and forecasts must be finite nonnegative numbers.')
        if not math.isclose(actual, snapshot_actual, rel_tol=0, abs_tol=0.000001):
            raise ValueError('Prediction actuals do not match the saved source snapshot.')
        change = actual - prior
        direction = 'Increase' if change > 0 else 'Decrease' if change < 0 else 'Unchanged'
        for name in METHODS:
            forecast = row[name]
            error = forecast - actual
            result.append({
                'week_start': week, 'model': name, 'actual_revenue': actual,
                'predicted_revenue': forecast, 'signed_error': error,
                'absolute_error': abs(error), 'absolute_percentage_error': percentage(abs(error), abs(actual)),
                'previous_actual_revenue': prior, 'actual_wow_change': change,
                'actual_wow_change_pct': percentage(change, prior),
                'revenue_direction': direction, 'forecast_change_from_previous_actual': forecast - prior,
            })
    return result


def top_errors(rows, model, count=5):
    """Rank absolute magnitude descending, breaking ties by earliest week."""
    return sorted((row for row in rows if row['model'] == model),
                  key=lambda row: (-row['absolute_error'], row['week_start']))[:count]


def summarize(rows):
    if not rows:
        raise ValueError('Error rows must not be empty.')
    count = len(rows)
    return {
        'weeks': count,
        'overprediction_pct': percentage(sum(row['signed_error'] > 0 for row in rows), count),
        'underprediction_pct': percentage(sum(row['signed_error'] < 0 for row in rows), count),
        'exact_pct': percentage(sum(row['signed_error'] == 0 for row in rows), count),
        'mean_bias': math.fsum(row['signed_error'] for row in rows) / count,
        'mae': math.fsum(row['absolute_error'] for row in rows) / count,
    }


def load_predictions(path):
    with path.open(encoding='utf-8', newline='') as stream:
        rows = [{'week_start': date.fromisoformat(row['week_start']),
                 **{name: float(row[name]) for name in ['actual_revenue', *METHODS]}}
                for row in csv.DictReader(stream)]
    if (len(rows) != 12 or rows[0]['week_start'] != date(2018, 6, 4)
            or rows[-1]['week_start'] != date(2018, 8, 20)):
        raise ValueError('Expected the saved 12-week June 4-August 20, 2018 evaluation.')
    return rows


def export_diagnostics(rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'error_analysis.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), layout='constrained')
    for name in METHODS:
        subset = [row for row in rows if row['model'] == name]
        axes[0].plot([row['week_start'] for row in subset],
                     [row['signed_error'] for row in subset], marker='o', label=name.upper())
        axes[1].scatter([row['actual_wow_change'] for row in subset],
                        [row['signed_error'] for row in subset], label=name.upper(), alpha=0.8)
    axes[0].set(title='Weekly forecast residuals: positive = overprediction',
                xlabel='Evaluation week starting Monday', ylabel='Forecast minus actual (BRL)')
    axes[0].tick_params(axis='x', rotation=25)
    axes[1].set(title='Residuals compared with actual week-over-week change',
                xlabel='Actual minus previous actual (BRL)', ylabel='Forecast minus actual (BRL)')
    axes[1].axvline(0, color='gray', linewidth=1)
    for axis in axes:
        axis.axhline(0, color='black', linewidth=1)
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:,.0f}'))
        axis.grid(alpha=0.2)
        axis.legend()
    axes[1].xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:,.0f}'))
    fig.savefig(output_dir / 'forecast_errors.png', dpi=160)
    plt.close(fig)

    lines = [
        '# Weekly revenue forecast error diagnostics', '',
        'Saved evaluation: June 4-August 20, 2018; 12 weeks per model, BRL.',
        'Inputs: predictions.csv and the matching 86-week source_snapshot.csv. No warehouse queries or forecast refits.',
        'Signed error = forecast - actual. APE = 100 * absolute error / abs(actual).',
        'APE is undefined (blank in CSV) for zero actual, including a zero/zero forecast.',
        'Actual WoW change = actual - previous actual; its percent is undefined for zero prior actual.',
        'The snapshot provides the May 28 actual for the June 4 comparison. Rates use all 12 evaluation weeks.', '',
        '## Observed direction and bias', '',
        '| Model | Overpredicted | Underpredicted | Exact | Mean bias (BRL) | Bias excluding last week (BRL) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for name in METHODS:
        subset = [row for row in rows if row['model'] == name]
        stats = summarize(subset)
        without_last = summarize(subset[:-1])
        lines.append(f"| {name.upper()} | {stats['overprediction_pct']:.2f}% | "
                     f"{stats['underprediction_pct']:.2f}% | {stats['exact_pct']:.2f}% | "
                     f"{stats['mean_bias']:,.2f} | {without_last['mean_bias']:,.2f} |")
    lines += ['', 'Excluding the last week is sensitivity analysis, not a replacement score or a reason to discard it.', '',
              '| Model | Revenue direction | Weeks | Overpredicted | Underpredicted | MAE (BRL) | Mean bias (BRL) |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for name in METHODS:
        for direction in ['Increase', 'Decrease', 'Unchanged']:
            subset = [row for row in rows if row['model'] == name and row['revenue_direction'] == direction]
            if subset:
                stats = summarize(subset)
                lines.append(f"| {name.upper()} | {direction} | {stats['weeks']} | "
                             f"{stats['overprediction_pct']:.2f}% | {stats['underprediction_pct']:.2f}% | "
                             f"{stats['mae']:,.2f} | {stats['mean_bias']:,.2f} |")
    for name in METHODS:
        lines += ['', f'## Five largest absolute errors: {name.upper()}', '',
                  '| Week | Actual | Forecast | Signed error | Absolute error | Actual WoW change |',
                  '| --- | ---: | ---: | ---: | ---: | ---: |']
        for row in top_errors(rows, name):
            lines.append(f"| {row['week_start']} | {row['actual_revenue']:,.2f} | {row['predicted_revenue']:,.2f} | "
                         f"{row['signed_error']:,.2f} | {row['absolute_error']:,.2f} | {row['actual_wow_change']:,.2f} |")
    lines += ['', '## Interpretation and investigations', '',
              'Naive residuals are exactly the negative of actual WoW changes because its forecast is the previous actual.',
              'That association is mathematical, not independent evidence of a business cause. Trailing averages can lag',
              'changes; inspect the conditional tables rather than assuming every increase or decrease has the same error sign.',
              'Mean bias and overprediction frequency answer different questions: large errors can dominate the mean.',
              'A 12-week sample cannot establish stable systematic bias; the last-week sensitivity exposes concentration.', '',
              'Possible explanations remain unverified. Do not attribute changes to promotions, holidays, campaigns,',
              'or customer behavior without corresponding data. Before adding advanced models, audit the late-window',
              'revenue drop, date coverage, payment completeness, delivered-status revisions, and order-count versus AOV changes.',
              'Check whether the end of the source history provides complete, mature delivered-order coverage.',
              'Then evaluate on more rolling origins, examine residual autocorrelation/seasonality and interval coverage,',
              'and introduce exogenous signals only when their historical as-of availability is established.',
              'These diagnostics reuse the same selection period; they are not a new holdout or proof of production reliability.', '']
    (output_dir / 'diagnostic_report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, default=DEFAULT_OUTPUT / 'predictions.csv')
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_OUTPUT / 'source_snapshot.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT / 'diagnostics')
    args = parser.parse_args()
    history = {week.week_start: week.weekly_revenue for week in load_snapshot(args.snapshot)}
    rows = analyze_errors(load_predictions(args.predictions), history)
    export_diagnostics(rows, args.output_dir)
    for name in METHODS:
        print(name, summarize([row for row in rows if row['model'] == name]))
    print('Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
