"""One-step-ahead weekly revenue baselines over the existing Olist mart."""

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math
from numbers import Real
import os
from pathlib import Path

from google.cloud import bigquery


PROJECT = 'mda-platform-2026'
SOURCE = f'{PROJECT}.analytics_dev.weekly_revenue_forecasting'
LOCATION = 'EU'
EXPECTED_WEEKS = 86
INITIAL_HISTORY = 74
EVALUATION_WEEKS = 12
METHODS = {'naive': 1, 'ma4': 4, 'ma8': 8}
DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'outputs' / 'weekly_revenue'
QUERY = f'''SELECT week_start, week_end, weekly_revenue, missing_payment_orders
FROM `{SOURCE}`
ORDER BY week_start'''


@dataclass(frozen=True)
class Week:
    week_start: date
    week_end: date
    weekly_revenue: float
    missing_payment_orders: int = 0


def _revenue(value):
    if (isinstance(value, bool) or not isinstance(value, (Real, Decimal))
            or not math.isfinite(value) or value < 0):
        raise ValueError('Revenue must be numeric, finite, nonnegative, and non-null.')
    return float(value)


def validate_weeks(rows, expected_count=EXPECTED_WEEKS, expected_start=None, expected_end=None):
    """Reject unsorted, duplicate, missing, incomplete, or invalid observations.

    Input order is validated, never silently sorted, reindexed, or zero-filled.
    Missing payments are rejected because their partial sums are not complete targets.
    """
    if len(rows) != expected_count or not rows:
        raise ValueError(f'Expected {expected_count} weekly observations, got {len(rows)}.')
    weeks = []
    for row in rows:
        start, end = row['week_start'], row['week_end']
        if type(start) is not date or type(end) is not date:
            raise ValueError('Week boundaries must be DATE values.')
        if start.weekday() != 0 or end != start + timedelta(days=6):
            raise ValueError('Weeks must run Monday through Sunday.')
        if weeks and start != weeks[-1].week_start + timedelta(days=7):
            raise ValueError('Weeks must be unique, chronological, and consecutive at seven-day intervals.')
        missing = row['missing_payment_orders']
        if isinstance(missing, bool) or not isinstance(missing, int) or missing != 0:
            raise ValueError('Missing-payment orders must be zero for complete forecasting targets.')
        weeks.append(Week(start, end, _revenue(row['weekly_revenue']), missing))
    if expected_start is not None and weeks[0].week_start != expected_start:
        raise ValueError(f'Expected first week {expected_start}.')
    if expected_end is not None and weeks[-1].week_start != expected_end:
        raise ValueError(f'Expected last week {expected_end}.')
    return weeks


def fetch_weeks(client=None):
    """Read only four ordered columns in EU using Application Default Credentials."""
    client = client if client is not None else bigquery.Client(project=PROJECT, location=LOCATION)
    rows = list(client.query(QUERY, location=LOCATION).result())
    return validate_weeks(rows, expected_start=date(2017, 1, 2), expected_end=date(2018, 8, 20))


def forecast_history(history):
    """Use trailing actuals only; callers supply history strictly before the target."""
    if len(history) < max(METHODS.values()):
        raise ValueError('At least eight historical observations are required for all baselines.')
    values = [_revenue(value) for value in history]
    return {name: math.fsum(values[-window:]) / window for name, window in METHODS.items()}


def backtest(weeks, initial_history=INITIAL_HISTORY, evaluation_weeks=EVALUATION_WEEKS):
    """Expanding history: previous evaluation actuals become known at the next origin."""
    if (type(initial_history) is not int or initial_history < 8
            or type(evaluation_weeks) is not int or evaluation_weeks < 1):
        raise ValueError('Initial history must be at least eight weeks and evaluation positive.')
    if len(weeks) != initial_history + evaluation_weeks:
        raise ValueError('Observation count must equal initial history plus evaluation weeks.')
    validate_weeks([vars(week) for week in weeks], expected_count=len(weeks))
    values = [week.weekly_revenue for week in weeks]
    return [
        {'week_start': weeks[index].week_start, 'actual_revenue': values[index],
         **forecast_history(values[:index])}
        for index in range(initial_history, len(weeks))
    ]


def calculate_metrics(actual, forecasts):
    """WAPE is a percentage; bias is forecast minus actual. All values are BRL."""
    if not actual or len(actual) != len(forecasts):
        raise ValueError('Actuals and forecasts must have equal, nonzero lengths.')
    actual = [_revenue(value) for value in actual]
    forecasts = [_revenue(value) for value in forecasts]
    errors = [prediction - observed for prediction, observed in zip(forecasts, actual)]
    absolute_error = math.fsum(abs(error) for error in errors)
    denominator = math.fsum(abs(value) for value in actual)
    return {
        'mae': absolute_error / len(actual),
        'rmse': math.sqrt(math.fsum(error * error for error in errors) / len(actual)),
        'wape_pct': 100 * absolute_error / denominator if denominator else None,
        'mean_bias': math.fsum(errors) / len(actual),
    }


def _write_csv(path, rows, columns):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def load_snapshot(path):
    """Replay the exported full history without any BigQuery connection."""
    with path.open(encoding='utf-8', newline='') as stream:
        rows = [
            {'week_start': date.fromisoformat(row['week_start']),
             'week_end': date.fromisoformat(row['week_end']),
             'weekly_revenue': float(row['weekly_revenue']),
             'missing_payment_orders': int(row['missing_payment_orders'])}
            for row in csv.DictReader(stream)
        ]
    return validate_weeks(rows, expected_start=date(2017, 1, 2), expected_end=date(2018, 8, 20))


def export_results(weeks, output_dir, provenance):
    """Export full-precision CSVs, a plot, and a report; rounding is presentation only."""
    predictions = backtest(weeks)
    actual = [row['actual_revenue'] for row in predictions]
    metrics = [{'model': name, **calculate_metrics(actual, [row[name] for row in predictions])}
               for name in METHODS]
    best = min(metrics, key=lambda row: row['mae'])
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / 'source_snapshot.csv', [vars(week) for week in weeks],
               ['week_start', 'week_end', 'weekly_revenue', 'missing_payment_orders'])
    _write_csv(output_dir / 'predictions.csv', predictions, ['week_start', 'actual_revenue', *METHODS])
    _write_csv(output_dir / 'metrics.csv', metrics, ['model', 'mae', 'rmse', 'wape_pct', 'mean_bias'])

    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, axis = plt.subplots(figsize=(11, 5.5))
    dates = [row['week_start'] for row in predictions]
    axis.plot(dates, actual, color='black', marker='o', linewidth=2.3, label='Actual')
    for name in METHODS:
        axis.plot(dates, [row[name] for row in predictions], marker='.', label=name.upper())
    axis.set(title='Weekly delivered revenue: one-week-ahead baselines',
             xlabel='Purchase week starting Monday', ylabel='Revenue (BRL)')
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'R${value:,.0f}'))
    axis.grid(alpha=0.25)
    axis.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / 'forecast_comparison.png', dpi=160)
    plt.close(fig)

    table = '\n'.join(
        f"| {row['model'].upper()} | {row['mae']:,.2f} | {row['rmse']:,.2f} | "
        f"{row['wape_pct']:.2f}% | {row['mean_bias']:,.2f} |"
        if row['wape_pct'] is not None else
        f"| {row['model'].upper()} | {row['mae']:,.2f} | {row['rmse']:,.2f} | undefined | {row['mean_bias']:,.2f} |"
        for row in metrics
    )
    report = f'''# Weekly revenue forecasting baseline

Source: `{SOURCE}` (EU). Input provenance: {provenance}.
Report generated: {datetime.now(timezone.utc).isoformat()}.
Validated history: {len(weeks)} weeks, {weeks[0].week_start} through {weeks[-1].week_start}.
Initial history: 74 weeks through {weeks[73].week_start}.
Evaluation: 12 one-week-ahead origins, {dates[0]} through {dates[-1]} (last Sunday {weeks[-1].week_end}).

Each forecast uses only actuals before its target week. Prior evaluation actuals
become available for later forecasts; this is not a 12-step forecast from one origin.
Naive uses the last actual; MA4/MA8 use exactly four/eight trailing actual weeks.

| Model | MAE (BRL) | RMSE (BRL) | WAPE | Mean bias (BRL) |
| --- | ---: | ---: | ---: | ---: |
{table}

Best baseline by MAE: **{best['model'].upper()}**, MAE **R${best['mae']:,.2f}**.
WAPE = 100 × sum(abs(forecast − actual)) / sum(abs(actual)); undefined at zero denominator.
Mean bias = mean(forecast − actual); positive means overprediction.
CSV values retain precision; the table and chart formatting are presentation only.

Limitations: a single 12-week historical evaluation, 86 weeks total, no modeled
seasonality or exogenous signals, and no prediction intervals. Revenue is delivered
payment value by purchase week, not profit, delivery-week revenue, or demand for all
orders. Current delivered status may reflect information unavailable at the original
forecast origin; this is a retrospective evaluation, not an as-of data backtest.
The source snapshot supports replay, but upstream status/payment revisions may change
future extracts. Missing payments, null values, and missing weeks are rejected rather
than imputed. Results do not establish production reliability or causal effects.
Baseline selection uses this evaluation period; assess it on further rolling origins
or a separate holdout before treating the selected method as a reliable winner.
'''
    (output_dir / 'report.md').write_text(report, encoding='utf-8')
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--input-csv', type=Path, help='Replay source_snapshot.csv without BigQuery.')
    args = parser.parse_args()
    weeks = load_snapshot(args.input_csv) if args.input_csv else fetch_weeks()
    metrics = export_results(weeks, args.output_dir,
                             str(args.input_csv) if args.input_csv else 'read-only BigQuery extraction')
    for row in metrics:
        print(row)
    print('Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
