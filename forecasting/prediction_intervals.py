"""Historical, sequential empirical Naive intervals; no future calibration errors."""

import argparse
from datetime import date, timedelta
import math
from numbers import Real
import os
from pathlib import Path

from forecasting.backtesting import _csv, compare_scenarios
from forecasting.weekly_revenue import DEFAULT_OUTPUT, _revenue, load_snapshot


NOMINAL_LEVELS = (0.8, 0.9)
MIN_CALIBRATION = 20


def empirical_radius(errors, coverage, minimum=MIN_CALIBRATION):
    """Finite-sample-style absolute-error order statistic, without a guarantee.

    k=ceil((n+1)*coverage). No interpolation or clamping k to n. Return None
    when calibration is insufficient or k exceeds n (no finite radius).
    """
    if (isinstance(coverage, bool) or not isinstance(coverage, Real)
            or not math.isfinite(coverage) or not 0 < coverage < 1):
        raise ValueError('Nominal coverage must be finite and between zero and one.')
    if type(minimum) is not int or minimum < 1:
        raise ValueError('Minimum calibration size must be a positive integer.')
    values = sorted(_revenue(error) for error in errors)
    rank = math.ceil((len(values) + 1) * coverage)
    if len(values) < minimum or rank > len(values):
        return None
    return values[rank - 1]


def sequential_intervals(predictions, levels=NOMINAL_LEVELS, minimum=MIN_CALIBRATION):
    """Calibrate before evaluating the current actual; append its error last.

    Only errors from these prior evaluation origins are admitted. No fitted
    training residuals, complete-period quantiles, or target-based tuning.
    """
    if not predictions or not levels or len(set(levels)) != len(levels):
        raise ValueError('Predictions and distinct nominal levels are required.')
    errors, rows = [], []
    previous_date = None
    for prediction in predictions:
        week = prediction['week_start']
        if type(week) is not date or week.weekday() != 0 or (
            previous_date is not None and week != previous_date + timedelta(days=7)
        ):
            raise ValueError('Origins must be unique consecutive Mondays in chronological order.')
        forecast = _revenue(prediction['naive'])
        actual = _revenue(prediction['actual_revenue'])
        for coverage in levels:
            radius = empirical_radius(errors, coverage, minimum)
            raw_lower = None if radius is None else forecast - radius
            lower = None if radius is None else max(0.0, raw_lower)
            upper = None if radius is None else forecast + radius
            rows.append({
                'week_start': week, 'nominal_coverage_pct': coverage * 100,
                'point_forecast': forecast, 'actual_revenue': actual,
                'calibration_count': len(errors), 'calibration_end': previous_date,
                'quantile_rank': math.ceil((len(errors) + 1) * coverage),
                'radius': radius, 'raw_lower': raw_lower, 'lower': lower, 'upper': upper,
                'lower_clipped': None if radius is None else raw_lower < 0,
                'interval_width': None if radius is None else upper - lower,
                'covered': None if radius is None else lower <= actual <= upper,
                'outside_side': None if radius is None else (
                    'Below' if actual < lower else 'Above' if actual > upper else 'Inside'),
                'status': 'Skipped: insufficient calibration' if radius is None else 'Evaluated',
            })
        # This actual is observed after both nominal intervals have been calibrated.
        errors.append(abs(forecast - actual))
        previous_date = week
    return rows


def interval_summary(rows):
    summaries = []
    for nominal in sorted({row['nominal_coverage_pct'] for row in rows}):
        all_rows = [row for row in rows if row['nominal_coverage_pct'] == nominal]
        usable = [row for row in all_rows if row['status'] == 'Evaluated']
        outside = [row for row in usable if not row['covered']]
        summaries.append({
            'nominal_coverage_pct': nominal, 'forecast_origins': len(all_rows),
            'evaluated_forecasts': len(usable), 'skipped_forecasts': len(all_rows) - len(usable),
            'first_evaluated_week': usable[0]['week_start'] if usable else None,
            'last_evaluated_week': usable[-1]['week_start'] if usable else None,
            'observed_coverage_pct': 100 * sum(row['covered'] for row in usable) / len(usable) if usable else None,
            'average_width_brl': math.fsum(row['interval_width'] for row in usable) / len(usable) if usable else None,
            'average_width_pct_of_point': 100 * math.fsum(row['interval_width'] for row in usable)
                / math.fsum(row['point_forecast'] for row in usable)
                if usable and math.fsum(row['point_forecast'] for row in usable) else None,
            'outside_count': len(outside),
            'outside_weeks': ';'.join(row['week_start'].isoformat() for row in outside),
            'clipped_lower_count': sum(row['lower_clipped'] for row in usable),
        })
    return summaries


def compare_intervals(weeks):
    predictions, _ = compare_scenarios(weeks)
    rows, summaries = [], []
    for scenario in ('A_full', 'B_boundary'):
        intervals = sequential_intervals(predictions[scenario])
        rows.extend({'scenario': scenario, **row} for row in intervals)
        summaries.extend({'scenario': scenario, **row} for row in interval_summary(intervals))
    return rows, summaries


def export_results(rows, summaries, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    _csv(output_dir / 'interval_predictions.csv', rows)
    _csv(output_dir / 'interval_metrics.csv', summaries)
    # Keep explicit columns even when no misses are observed.
    outside = [row for row in rows if row['status'] == 'Evaluated' and not row['covered']]
    import csv
    with (output_dir / 'outside_intervals.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(outside)
    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout='constrained')
    for axis, scenario in zip(axes, ('A_full', 'B_boundary')):
        base = [row for row in rows if row['scenario'] == scenario and row['nominal_coverage_pct'] == 80]
        dates = [row['week_start'] for row in base]
        axis.plot(dates, [row['actual_revenue'] for row in base], color='black', marker='.', label='Actual')
        axis.plot(dates, [row['point_forecast'] for row in base], color='steelblue', label='Naive point forecast')
        for nominal, color in [(90, 'orange'), (80, 'steelblue')]:
            subset = [row for row in rows if row['scenario'] == scenario and row['nominal_coverage_pct'] == nominal]
            axis.fill_between([row['week_start'] for row in subset],
                              [float('nan') if row['lower'] is None else row['lower'] for row in subset],
                              [float('nan') if row['upper'] is None else row['upper'] for row in subset],
                              alpha=0.2, color=color, label=f'Nominal {nominal}% historical interval')
        usable = [row for row in base if row['status'] == 'Evaluated']
        axis.axvspan(dates[0], usable[0]['week_start'], color='gray', alpha=0.1, label='20 calibration-only origins')
        axis.set(title=f'{scenario}: sequential calibration; lower bounds clipped at zero',
                 ylabel='Weekly delivered payment value (BRL)', xlabel='Target week starting Monday')
        axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8, loc='upper left')
    fig.suptitle('Historical prediction-interval experiment: no future errors in calibration')
    fig.savefig(output_dir / 'prediction_intervals.png', dpi=160)
    plt.close(fig)

    lines = ['# Historical Naive prediction-interval experiment', '',
             'Offline source snapshot only; unchanged Naive points and shared rolling-origin evaluation.',
             'Initial forecasting history is 52 weeks. Only prior errors from subsequent one-step forecast origins',
             'calibrate intervals. First 20 origins are calibration-only: usable targets start May 21, 2018.',
             'Calibration is expanding and uses absolute errors. Radius = kth smallest past absolute error,',
             'k = ceil((n+1) * nominal coverage). No interpolation; skip if n < 20 or k > n.',
             'The current actual/error is appended only after calibrating both levels. No whole-period quantiles.', '',
             '| Scenario | Nominal | Evaluated | Skipped | Observed coverage | Mean width (BRL) | Outside weeks |',
             '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for row in summaries:
        lines.append(f"| {row['scenario']} | {row['nominal_coverage_pct']:.0f}% | {row['evaluated_forecasts']} | "
                     f"{row['skipped_forecasts']} | {row['observed_coverage_pct']:.2f}% | {row['average_width_brl']:,.2f} | "
                     f"{row['outside_weeks'] or 'None'} |")
    lines += ['', 'Coverage counts endpoints inclusively and divides by usable intervals only, not skipped origins.',
              'Intervals start symmetric around a nonnegative point; lower=max(0, point-radius), upper=point+radius.',
              'Clipping makes them asymmetric and reduces width when applied. For nonnegative targets it cannot',
              'change inclusion relative to the raw symmetric interval; it is not an adjustment calibrated to targets.',
              'Clipping counts and average width relative to mean point forecast are recorded in the metrics CSV.', '',
              '## Historical, illustrative planning example', '']
    example = [row for row in rows if row['scenario'] == 'A_full' and row['status'] == 'Evaluated'][:2]
    point = example[0]['point_forecast']
    lines.append(f"At the historical {example[0]['week_start']} origin, the Naive point was R${point:,.2f}.")
    for row in example:
        lines.append(f"- Nominal {row['nominal_coverage_pct']:.0f}% range: R${row['lower']:,.2f}-R${row['upper']:,.2f}.")
    lines += ['A finance team could use the point for a base revenue scenario and the lower/upper values for',
              'downside/upside stress scenarios. The lower bound is not a guaranteed floor; the upper bound is not',
              'committed revenue or permission to spend. Revenue is not cash receipts or profit. Operations would',
              'need separate order-volume, margin and capacity assumptions to translate this range into staffing.',
              'This is historical and illustrative, not a validated future prediction or budget recommendation.', '',
              '## Interpretation and limitations', '',
              'The quantile rule is conformal-style, but exchangeability/stationarity and point-in-time data availability',
              'are unverified. No statistical coverage guarantee is claimed. Ordered revenue errors may be dependent',
              'and change scale; observed coverage from 14/13 weeks is uncertain and coarse, not a future probability.',
              'Full versus excluded-endpoint comparisons share identical earlier intervals; exclusion is sensitivity',
              'analysis, not proof of corruption or its cause. Inspect the explicit missed weeks, not just average coverage.',
              'Wide ranges may support risk scenarios but may be too broad for precise spending/capacity decisions.',
              'Before operational use, audit endpoint completeness and as-of delivered-status leakage; evaluate longer',
              'rolling samples, width/coverage trade-offs and downside costs using genuinely available historical data.',
              'Do not choose calibration windows or nominal levels by optimizing these same evaluation outcomes.', '']
    (output_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_OUTPUT / 'source_snapshot.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT / 'prediction_intervals')
    args = parser.parse_args()
    rows, summaries = compare_intervals(load_snapshot(args.snapshot))
    export_results(rows, summaries, args.output_dir)
    for row in summaries:
        print(row)
    print('Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
