"""Descriptive trend and ACF diagnostics of the saved weekly revenue snapshot."""

import argparse
import csv
import math
import os
from pathlib import Path

import numpy as np
from statsmodels.tsa.stattools import acf

from forecasting.backtesting import FLAGGED_WEEK, rolling_origin
from forecasting.weekly_revenue import DEFAULT_OUTPUT, load_snapshot, validate_weeks


def first_differences(values):
    """The ith output belongs to input week i+1; never pad with an artificial zero."""
    return [current - previous for previous, current in zip(values, values[1:])]


def wow_percentages(values):
    return [100 * (current - previous) / previous if previous else None
            for previous, current in zip(values, values[1:])]


def acf_rows(values, max_lag):
    """Demeaned, unadjusted sample ACF; lag zero included, with overlapping pair counts.

    r[k] = sum((x[t]-mean)*(x[t-k]-mean)) / sum((x[t]-mean)**2).
    No confidence bands or significance tests. Constant series have undefined ACF.
    """
    data = np.asarray(values, dtype=float)
    if data.ndim != 1 or len(data) < 2 or not np.isfinite(data).all():
        raise ValueError('ACF requires at least two finite observations.')
    if type(max_lag) is not int or max_lag < 0:
        raise ValueError('max_lag must be a nonnegative integer.')
    max_lag = min(max_lag, len(data) - 1)
    correlations = ([None] * (max_lag + 1) if np.ptp(data) == 0 else
                    acf(data, nlags=max_lag, adjusted=False, fft=False, missing='raise'))
    return [{'lag': lag, 'acf': None if value is None else float(value),
             'observations': len(data), 'overlapping_pairs': len(data) - lag}
            for lag, value in enumerate(correlations)]


def boundary_cases(weeks):
    validate_weeks([vars(week) for week in weeks], expected_count=86, expected_end=FLAGGED_WEEK)
    return {'Full 86 weeks': weeks, 'Boundary sensitivity: first 85 weeks': weeks[:-1]}


def trailing_means(values, window):
    return [None if index + 1 < window else math.fsum(values[index + 1 - window:index + 1]) / window
            for index in range(len(values))]


def diagnose(weeks):
    summaries, correlations, weekly = [], [], []
    for scenario, source in boundary_cases(weeks).items():
        values = [week.weekly_revenue for week in source]
        changes, percentages = first_differences(values), wow_percentages(values)
        rolling = rolling_origin(source)
        errors = [row['naive'] - row['actual_revenue'] for row in rolling]
        x = np.arange(len(values), dtype=float)
        centered = np.asarray(values) - np.mean(values)
        slope = float(np.dot(x - x.mean(), centered) / np.dot(x - x.mean(), x - x.mean()))
        fitted_centered = slope * (x - x.mean())
        denominator = float(np.dot(centered, centered))
        summaries.append({
            'scenario': scenario, 'observations': len(values), 'start': source[0].week_start,
            'end': source[-1].week_start, 'mean_revenue': math.fsum(values) / len(values),
            'first_13_week_mean': math.fsum(values[:13]) / 13,
            'last_13_week_mean': math.fsum(values[-13:]) / 13,
            'descriptive_linear_slope_brl_per_week': slope,
            'descriptive_linear_r_squared': 1 - float(np.sum((centered - fitted_centered)**2)) / denominator
                if denominator else None,
            'mean_wow_change': math.fsum(changes) / len(changes),
            'increases': sum(value > 0 for value in changes),
            'decreases': sum(value < 0 for value in changes),
            'rolling_naive_error_count': len(errors), 'rolling_naive_error_start': rolling[0]['week_start'],
            'rolling_naive_error_end': rolling[-1]['week_start'],
        })
        for series_name, data, max_lag in [
            ('Raw revenue', values, 52), ('First-differenced revenue', changes, 52),
            ('Rolling Naive errors (52-week warm-up)', errors, 12),
        ]:
            correlations.extend({'scenario': scenario, 'series': series_name, **row}
                                for row in acf_rows(data, max_lag))
        ma4, ma8 = trailing_means(values, 4), trailing_means(values, 8)
        weekly.extend({'scenario': scenario, 'week_start': week.week_start, 'revenue': values[index],
                       'trailing_ma4': ma4[index], 'trailing_ma8': ma8[index],
                       'wow_change_brl': None if index == 0 else changes[index - 1],
                       'wow_change_pct': None if index == 0 else percentages[index - 1]}
                      for index, week in enumerate(source))
    return summaries, correlations, weekly


def _csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def strongest(rows, limit=3, max_lag=12):
    return sorted((row for row in rows if 1 <= row['lag'] <= max_lag and row['acf'] is not None),
                  key=lambda row: (-abs(row['acf']), row['lag']))[:limit]


def export_diagnostics(summaries, correlations, weekly, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    _csv(output_dir / 'trend_summary.csv', summaries)
    _csv(output_dir / 'acf_summary.csv', correlations)
    _csv(output_dir / 'weekly_diagnostics.csv', weekly)
    os.environ.setdefault('MPLCONFIGDIR', str(output_dir.resolve() / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    full = [row for row in weekly if row['scenario'] == summaries[0]['scenario']]
    dates = [row['week_start'] for row in full]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), layout='constrained', sharex=True)
    axes[0].plot(dates, [row['revenue'] for row in full], color='gray', alpha=0.7, label='Full 86-week revenue')
    axes[0].plot(dates[:-1], [row['revenue'] for row in full[:-1]], color='steelblue', label='First 85 weeks')
    for field, label, color in [('trailing_ma4', 'Trailing 4-week mean', 'seagreen'),
                                ('trailing_ma8', 'Trailing 8-week mean', 'darkorange')]:
        axes[0].plot(dates, [row[field] for row in full], label=label, color=color)
    axes[0].scatter([dates[-1]], [full[-1]['revenue']], color='red', zorder=5, label='Flagged August 20 endpoint')
    axes[0].set(title='Weekly revenue and trailing means (descriptive, includes current actual)', ylabel='Revenue (BRL)')
    for axis, field, label in [(axes[1], 'wow_change_brl', 'WoW change (BRL)'),
                               (axes[2], 'wow_change_pct', 'WoW change (%)')]:
        axis.plot(dates[1:], [row[field] for row in full[1:]], color='gray', label='Full 86 weeks')
        axis.plot(dates[1:-1], [row[field] for row in full[1:-1]], color='steelblue', label='First 85 weeks')
        axis.scatter([dates[-1]], [full[-1][field]], color='red', zorder=5)
        axis.axhline(0, color='black', linewidth=0.8)
        axis.set(ylabel=label)
    for axis in axes:
        axis.axvline(FLAGGED_WEEK, color='red', linestyle=':', alpha=0.5)
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
        axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    axes[-1].set_xlabel('Week starting Monday; full and excluded-endpoint paths coincide before August 20')
    fig.savefig(output_dir / 'revenue_trend_changes.png', dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), layout='constrained')
    for axis, series_name in zip(axes, dict.fromkeys(row['series'] for row in correlations)):
        for summary in summaries:
            subset = [row for row in correlations if row['scenario'] == summary['scenario'] and row['series'] == series_name]
            axis.plot([row['lag'] for row in subset], [float('nan') if row['acf'] is None else row['acf'] for row in subset],
                      marker='.', label=summary['scenario'])
        axis.axhline(0, color='black', linewidth=0.8)
        axis.set(title=series_name, xlabel='Lag in weeks (lag 0 = self-correlation)', ylabel='Sample ACF', ylim=(-1, 1.05))
        axis.legend(fontsize=8)
        axis.grid(alpha=0.2)
    fig.suptitle('Exploratory ACF: no confidence bands or significance claims')
    fig.savefig(output_dir / 'acf_comparison.png', dpi=160)
    plt.close(fig)

    lines = ['# Exploratory weekly revenue trend and dependence', '',
             'Offline snapshot: 86 Monday-Sunday weeks, January 2, 2017-August 20, 2018.',
             'Boundary sensitivity excludes only flagged August 20; it is not proof of corruption or its cause.', '',
             '| Scenario | Mean revenue (BRL) | First 13 mean | Last 13 mean | Linear slope (BRL/week) | Linear R² |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in summaries:
        r2 = 'undefined' if row['descriptive_linear_r_squared'] is None else f"{row['descriptive_linear_r_squared']:.3f}"
        lines.append(f"| {row['scenario']} | {row['mean_revenue']:,.2f} | {row['first_13_week_mean']:,.2f} | "
                     f"{row['last_13_week_mean']:,.2f} | {row['descriptive_linear_slope_brl_per_week']:,.2f} | {r2} |")
    def coefficient(scenario, series_name, lag):
        return next(row['acf'] for row in correlations if row['scenario'] == scenario
                    and row['series'] == series_name and row['lag'] == lag)

    full_scenario, boundary_scenario = [row['scenario'] for row in summaries]
    lines += ['',
              f"Observed slope changes from {summaries[0]['descriptive_linear_slope_brl_per_week']:,.2f} to "
              f"{summaries[1]['descriptive_linear_slope_brl_per_week']:,.2f} BRL/week when the endpoint is excluded.",
              f"Raw lag-1 ACF changes from {coefficient(full_scenario, 'Raw revenue', 1):.3f} to "
              f"{coefficient(boundary_scenario, 'Raw revenue', 1):.3f}; the strong level dependence persists.",
              f"After differencing, lag-1 ACF is {coefficient(full_scenario, 'First-differenced revenue', 1):.3f} "
              f"(full) and {coefficient(boundary_scenario, 'First-differenced revenue', 1):.3f} (boundary case).",
              f"Rolling Naive-error lag-2 ACF changes from {coefficient(full_scenario, 'Rolling Naive errors (52-week warm-up)', 2):.3f} "
              f"to {coefficient(boundary_scenario, 'Rolling Naive errors (52-week warm-up)', 2):.3f}; error diagnostics are more endpoint-sensitive.",
              'These are measured differences, without a statistical significance claim.', '',
              'Linear slope is a descriptive whole-sample fit, not a forecast, causal explanation, or significance test.',
              'The last 13-week blocks differ by one week between scenarios. Trailing plotted means include current actuals',
              'and are descriptive smoothers, not the existing one-step-ahead forecasts.', '',
              '| Scenario | Series | Lag | Sample ACF | Overlapping pairs |',
              '| --- | --- | ---: | ---: | ---: |']
    for summary in summaries:
        for series_name in dict.fromkeys(row['series'] for row in correlations):
            subset = [row for row in correlations if row['scenario'] == summary['scenario'] and row['series'] == series_name]
            selected = {row['lag']: row for row in strongest(subset)}
            selected.update({row['lag']: row for row in subset if row['lag'] in (1, 4, 8, 13, 26, 52)})
            for row in sorted(selected.values(), key=lambda row: row['lag']):
                value = 'undefined' if row['acf'] is None else f"{row['acf']:.3f}"
                lines.append(f"| {summary['scenario']} | {series_name} | {row['lag']} | {value} | {row['overlapping_pairs']} |")
    lines += ['', 'ACF uses demeaned, unadjusted sample covariance divided by lag-zero covariance, with no confidence bands.',
              'The table includes the three largest absolute ACFs at lags 1-12 plus selected calendar/short-term lags.',
              'Searching many lags is exploratory: isolated peaks are not evidence of seasonality.',
              'Raw-revenue correlation can reflect changing levels/trend, rather than a repeatable seasonal process.',
              'Differencing removes level changes but does not automatically establish stationarity.', '',
              'Naive errors use the existing 52-week-warm-up rolling backtest: 34 targets January 1-August 20, 2018',
              '(33 through August 13 without the endpoint). Error = previous actual - current actual = negative first difference.',
              'Their ACF is therefore the ACF of differences over that target subset, not independent evidence of model failure.',
              'Short-lag nonzero error correlations motivate testing potential predictive structure, but do not guarantee a gain.', '',
              '## Seasonality and next investigations', '',
              'Annual weekly seasonality would use roughly lag 52. With only 86 (85) observations there are fewer than',
              'two complete annual cycles; lag 52 has only 34 (33) overlapping raw pairs, and even fewer differenced pairs.',
              'Annual seasonality is not statistically established here. More complete annual cycles and stable coverage',
              'are needed before treating a seasonal pattern as dependable. No annual seasonal decomposition is fitted.', '',
              'Trend or short-lag autoregressive candidates deserve controlled rolling-origin comparisons against Naive,',
              'not immediate adoption. First audit boundary coverage and as-of delivered status/payment revisions.',
              'Estimate any transforms/trends inside each training origin; whole-sample diagnostics must not leak into predictions.',
              'Evaluate robustness across windows, intervals and remaining residual dependence. Overlapping rolling forecasts',
              'are not independent experiments. No ARIMA, Prophet or machine-learning model is introduced.', '']
    (output_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_OUTPUT / 'source_snapshot.csv')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT / 'time_series_diagnostics')
    args = parser.parse_args()
    summaries, correlations, weekly = diagnose(load_snapshot(args.snapshot))
    export_diagnostics(summaries, correlations, weekly, args.output_dir)
    for row in summaries:
        print(row)
    for scenario in (row['scenario'] for row in summaries):
        for series_name in dict.fromkeys(row['series'] for row in correlations):
            print(scenario, series_name, strongest([row for row in correlations
                  if row['scenario'] == scenario and row['series'] == series_name]))
    print('Outputs:', args.output_dir.resolve())


if __name__ == '__main__':
    main()
