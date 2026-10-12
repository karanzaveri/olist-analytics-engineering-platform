# Weekly revenue forecasting baselines

This independent Python module reads the existing EU mart
`mda-platform-2026.analytics_dev.weekly_revenue_forecasting`. It never writes to
BigQuery, builds dbt models, or connects to GA4. Uses existing dependencies:
google-cloud-bigquery, matplotlib, and pytest; no additional packages required.

Run from the repository root with Application Default Credentials configured
outside the repository, following the existing Python BigQuery client convention:

```powershell
.\.venv\Scripts\python.exe -m forecasting.weekly_revenue
.\.venv\Scripts\python.exe -m pytest tests/test_weekly_revenue_forecasting.py tests/test_ga4_ci_selection.py -q
.\.venv\Scripts\python.exe analytics/ci/validate_ga4.py
```

The extraction selects only week_start, week_end, weekly_revenue, and
missing_payment_orders, ordered by week_start, with EU explicitly set. It
requires 86 unique consecutive Monday-Sunday weeks, January 2, 2017 through
August 20, 2018, finite nonnegative revenue, and no missing-payment orders.
No sorting, filling, or imputation conceals source problems. Genuine zero
revenue is valid; a zero-total evaluation has undefined WAPE.

First 74 weeks form initial history. The final 12 are chronological evaluation
origins. Each forecast uses strictly earlier actuals: Naive takes the prior week,
MA4 the prior four, MA8 the prior eight. Once an evaluation week ends its actual
is available to later forecasts. This evaluates repeated one-week-ahead forecasts,
not a fixed-origin 12-week prediction; no centered windows or random splits.

Metrics are MAE, RMSE, WAPE percent, and mean bias (forecast minus actual).
The best baseline is selected by MAE. Selection on this short evaluation period
is exploratory; validate on further rolling origins or another holdout. The
report also discusses changing delivered status, source revisions, limited
history, absent seasonality/intervals, and retrospective rather than as-of data.

Generated artifacts live under ignored `forecasting/outputs/weekly_revenue/`:
`predictions.csv` (12 origins, actuals and all forecasts), `metrics.csv`,
`forecast_comparison.png`, `report.md`, and `source_snapshot.csv` (86 input weeks).
No rounding is applied to forecasts or metric calculations; presentation rounds
currency only. Replay the snapshot without a warehouse connection:

```powershell
.\.venv\Scripts\python.exe -m forecasting.weekly_revenue --input-csv forecasting/outputs/weekly_revenue/source_snapshot.csv --output-dir forecasting/outputs/replay
```

The offline CI guard now expects 24 Olist models under dev, including this mart,
and exactly four GA4 models under ga4_dev. Existing isolation, disabled-model,
test-definition, and analysis-dependency checks remain in place.

## Saved-prediction error diagnostics

```powershell
.\.venv\Scripts\python.exe -m forecasting.error_analysis
.\.venv\Scripts\python.exe -m pytest tests/test_forecast_error_analysis.py -q
```

This offline extension reads `predictions.csv` and its matching source snapshot,
without a BigQuery query or changes to model formulas. It writes ignored files
under `forecasting/outputs/weekly_revenue/diagnostics/`: `error_analysis.csv`
(36 week/model rows), `forecast_errors.png`, and `diagnostic_report.md`.
The report includes five largest absolute errors per model, over/under/exact
frequencies, conditional errors for revenue increases/decreases, and last-week
bias sensitivity. Signed error is forecast minus actual. APE and actual WoW
change percentages are undefined for zero denominators, represented as blank
CSV fields. May 28 snapshot revenue supplies June 4's previous actual.
Observed associations and arithmetic identities are distinguished from untested
business explanations. No external causes or stable systematic bias are inferred
from this short evaluation alone.

## Rolling-origin and boundary sensitivity

```powershell
.\.venv\Scripts\python.exe -m forecasting.backtesting
.\.venv\Scripts\python.exe -m pytest tests/test_forecasting_backtesting.py -q
```

The extension reads the existing offline source snapshot and reuses `backtest`
and `calculate_metrics`. A uses all 86 observations with 52 initial history weeks:
34 one-step-ahead forecasts, January 1-August 20, 2018. B uses the first 85 weeks
with the same warm-up: 33 forecasts through August 13, excluding only the flagged
August 20 endpoint. C retains the 74-week initial history and original June 4-
August 20 holdout, with 12 forecasts. The CLI verifies C matches saved predictions
exactly. No formulas, snapshots, or original reports are overwritten.

History expands after each observed actual; MA4 and MA8 still use only their fixed
trailing windows. Outputs in ignored `forecasting/outputs/weekly_revenue/backtesting/`
include combined predictions, metrics with counts/dates and ranks, B-minus-A
metric deltas, `backtesting_comparison.png`, and `report.md`.

Overlapping rolling forecasts share data and are not independent experiments.
Endpoint exclusion is sensitivity analysis, not proof of corruption; the exact
raw-order decline cause remains unresolved. MAE and WAPE rankings match within
each scenario because all methods share its actual denominator. Do not interpret
the different evaluation periods as independent causal comparisons.

## Exploratory trend and dependence

```powershell
.\.venv\Scripts\python.exe -m forecasting.time_series_diagnostics
.\.venv\Scripts\python.exe -m pytest tests/test_time_series_diagnostics.py -q
```

Uses only the saved snapshot. Ignored outputs under
`forecasting/outputs/weekly_revenue/time_series_diagnostics/` contain revenue/
trailing-mean/WoW charts, raw/differenced/rolling-Naive-error ACF charts,
weekly diagnostics, trend and ACF CSVs, and `report.md`. Full 86-week and first
85-week boundary cases are labeled explicitly. Rolling-error ACF uses the
existing 52-week warm-up, yielding 34/33 one-step targets, rather than treating
training-period residuals as evaluation forecasts.

ACF is demeaned and unadjusted, with lag zero and overlapping-pair counts
included; confidence bands and significance claims are omitted. Constant-series
ACF and zero-prior-revenue WoW percentages remain undefined. Descriptive trailing
means include the current actual and are not prediction formulas. Whole-sample
linear trend slopes are descriptive, not causal or out-of-sample estimates.
Only 86 weeks are available, fewer than two annual cycles: isolated lag-52
correlations cannot establish annual seasonality. Candidate models must later
be tested within rolling training windows against the unchanged Naive baseline.

## Drift and Simple Exponential Smoothing candidates

```powershell
.\.venv\Scripts\python.exe -m forecasting.statistical_candidates
.\.venv\Scripts\python.exe -m pytest tests/test_statistical_candidates.py -q
```

All five models use the same A/B/C dates and shared metrics. Existing Naive/MA4/
MA8 predictions are reused unchanged; C is checked against its saved original
CSV. Ignored `forecasting/outputs/weekly_revenue/statistical_candidates/` contains
prediction/fitting metadata, metrics and ranks (MAE, WAPE, RMSE), reductions
versus Naive, a three-panel chart, and a report. No baseline reports are overwritten.

Drift uses `last + (last-first)/(n-1)` on each expanding training history.
SES uses installed statsmodels 0.14.6
[SimpleExpSmoothing](https://www.statsmodels.org/v0.14.4/generated/statsmodels.tsa.holtwinters.SimpleExpSmoothing.html)
with known initial level equal to the first training value. Alpha is fit anew
using training SSE only: grid-start initialization followed by bounded L-BFGS-B
(maxiter 1000, ftol 1e-12, gtol 1e-8). Revenue is scaled by the training maximum
(at least 1) for stability, then forecasts/SSE are restored to BRL units.
No Box-Cox, bias removal, trend, or seasonality is added to SES. Optimized alpha
uses library epsilon-interior bounds; fixed alpha in [0,1] is supported for
verification. Constant histories have tied fits and deterministically use alpha
zero. Nonconvergence/invalid parameters are errors, not silent fallback forecasts.
No evaluation actual enters its own parameter fit.

Ranks use full precision; near-ties may have different numerical ranks without
practically meaningful improvement. MAE/WAPE and RMSE can select different models.
Boundary sensitivity is not proof of corruption, and overlapping evaluations are
not independent experiments. Drift is not clipped: if it produces negative
predictions on future declining data, the shared nonnegative metric contract
fails explicitly and requires a deliberate evaluation-policy decision.

## Historical Naive prediction intervals

```powershell
.\.venv\Scripts\python.exe -m forecasting.prediction_intervals
.\.venv\Scripts\python.exe -m pytest tests/test_prediction_intervals.py -q
```

Uses the offline snapshot and unchanged 52-week-warm-up Naive forecasts.
Expanding calibration admits only previously observed errors at these forecast
origins, not fitted training residuals. The minimum is 20 errors: the first 20
forecast weeks are calibration-only, leaving 14 full-series and 13 boundary-case
usable targets, starting May 21, 2018. Both nominal 80%/90% intervals use the
same history, calibrated before appending the current actual's error.

Radius is the `ceil((n+1)*coverage)`-th smallest past absolute error, without
interpolation. Insufficient samples or ranks above n are skipped, not fabricated.
Raw intervals are symmetric around the nonnegative Naive point. Lower bounds
are clipped at zero, reducing width and making the ranges asymmetric without changing inclusion for
nonnegative targets. No coverage guarantee is claimed: exchangeability,
stationarity and as-of status availability are unverified.

Ignored outputs under `forecasting/outputs/weekly_revenue/prediction_intervals/`
contain interval predictions (including skipped origins), coverage/width metrics,
missed weeks, a visualization and a report with a historical illustrative finance/
operations example. Rates divide by usable forecasts only. No prior forecasting
results or formulas are modified. Endpoint exclusion is a sensitivity experiment,
not proof of corruption, and the short coverage sample is not a future guarantee.
