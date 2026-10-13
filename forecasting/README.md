# Olist weekly revenue forecasting

This is a finalized **retrospective portfolio experiment**, not an operational forecasting deployment. Five existing models, chronological backtests, error diagnostics and historical 80%/90% intervals are implemented. Start with the [portfolio case study](../docs/forecasting/README.md) for results and business interpretation.

## Historical dataset and metric

The EU mart `mda-platform-2026.analytics_dev.weekly_revenue_forecasting` contains **86 consecutive purchase weeks**, January 2, 2017 through August 20, 2018; each week is Monday-Sunday and the last ends August 26. Total observed payment value is **R$15,363,879.91**.

The [dbt mart](../analytics/models/marts/weekly_revenue_forecasting.sql) selects orders whose **final-snapshot status is delivered**, sums their payment values, and assigns them to purchase weeks. Revenue is delivered-order payment value, not merchandise value, delivery-week revenue, profit or cash receipts. Empty weeks can be zero; missing-payment observations are rejected by the Python workflow rather than imputed.

The source snapshot was reconciled locally against `data/raw/olist/olist_orders_dataset.csv` and `olist_order_payments_dataset.csv`: payment rows were summed by order before joining unique order IDs, then delivered orders were aggregated by purchase week. All 86 revenue totals match within R$0.000001 and the snapshot has no missing-payment orders. This establishes agreement with the available local extract, not exhaustive source capture. Those raw CSVs remain ignored.

The mart's YAML and three singular tests define 14 checks. Historical logs show its 86-row build, 13 passes plus a calendar-test error, followed by a successful corrected calendar-test rerun. This is not a fresh all-14 warehouse run. See [mart definitions](../analytics/models/marts/weekly_revenue_forecasting.yml), [calendar](../analytics/tests/weekly_revenue_forecasting_calendar.sql), [reconciliation](../analytics/tests/weekly_revenue_forecasting_reconciliation.sql) and [missing-payment](../analytics/tests/weekly_revenue_forecasting_missing_payments.sql) tests.

## Final-week investigation

| Purchase week starting | Recorded orders | Eventually delivered | Payment value (BRL) |
| --- | ---: | ---: | ---: |
| August 13, 2018 | 1,875 | 1,839 | 285,766.68 |
| August 20, 2018 | 1,071 | 1,054 | 145,680.87 |

Revenue fell **49.02%**. Recorded orders fell 42.88%; eventually delivered counts fell 42.69%, and payment per delivered order fell 11.05%. These explain the arithmetic, not a business cause. Orders occur on all seven days of August 20-26 and delivered purchases continue through August 29, ruling out a simple file cutoff before the week ends.

Classification: **suspicious boundary observation, completeness unconfirmed**. There is no authoritative expected population, extraction manifest or status-history record proving exhaustive capture. Keep the observation in primary results and exclusion as sensitivity. Do not label it definitively incomplete or claim a proven cause. Additional SQL against the same finalized extract would not prove completeness.

## Forecasting methodology

| Model | One-week-ahead calculation |
| --- | --- |
| Naive | Last observed revenue |
| MA4 | Mean of the preceding four revenues |
| MA8 | Mean of the preceding eight revenues |
| Drift | `last + (last-first)/(n-1)` across expanding training history |
| SES | Simple exponential smoothing; alpha refit from training SSE at each origin |

SES uses statsmodels 0.14.6 with a known initial level equal to the first training value, training-max scaling, grid-start search and bounded L-BFGS-B (`maxiter=1000`, `ftol=1e-12`, `gtol=1e-8`). No trend, seasonality, Box-Cox or bias removal is added. Constant histories use alpha zero; invalid fits/nonconvergence raise errors. Drift is not silently clipped; negative forecasts on future declining data require an explicit policy under the current nonnegative scoring contract.

History expands after each target, while MA4/MA8 retain fixed trailing windows. Actuals are treated as available after their target week **within this retrospective experiment**; this is not an assertion about real-time availability. No random splits, centered windows or fixed-origin 12-step forecast are used.

| Scenario | Initial history | Targets | Target window |
| --- | ---: | ---: | --- |
| A_full | 52 weeks | 34 | January 1-August 20, 2018 |
| B_boundary | 52 weeks | 33 | January 1-August 13, 2018; endpoint excluded |
| C_original | 74 weeks | 12 | June 4-August 20, 2018 |

Metrics are MAE/RMSE in BRL, WAPE percent, and mean bias (`forecast - actual`). WAPE is undefined when total actual revenue is zero. Full precision is retained in calculations and CSVs. Overlapping evaluations share histories and are not independent experiments; model selection on these samples remains exploratory.

## Validated model comparison

| Model | MAE (BRL) | RMSE (BRL) | WAPE |
| --- | ---: | ---: | ---: |
| NAIVE | 34,070.94 | 48,653.16 | 13.72% |
| MA4 | 39,167.37 | 54,475.96 | 15.78% |
| MA8 | 35,221.09 | 46,454.66 | 14.19% |
| DRIFT | 34,245.81 | 49,005.50 | 13.79% |
| SES | 34,281.65 | 49,798.26 | 13.81% |

Naive leads full-sample MAE/WAPE (**R$34,070.94 / 13.72%**). MA8 leads full-sample RMSE (**R$46,454.66**). In B, SES's MAE is R$30,842.09 versus Naive's R$30,858.37: only **R$16.27/week (0.053%)** improvement, with worse RMSE (R$43,510.52 versus R$42,944.07). Naive wins the original holdout at MAE R$36,743.37 and WAPE 15.13%. No model is established as universally superior.

[All A/B/C model scores](../docs/forecasting/model-comparison.csv) include sample sizes/dates. [Endpoint deltas](../docs/forecasting/endpoint-sensitivity.csv) describe the original three baselines only; their ranks should not be mistaken for five-model ranks.

## Historical prediction intervals

Nominal **80% and 90% Naive intervals are implemented** in `prediction_intervals.py`. Calibration expands using only prior rolling-origin absolute errors, not fitted training residuals or complete-period quantiles. Radius is the `ceil((n+1)*coverage)`-th smallest prior error without interpolation. Skip when fewer than **20 errors** exist or the rank exceeds n. The current target's error is appended after both intervals are calibrated.

| Sample | Nominal | Evaluated | Observed coverage | Mean width (BRL) |
| --- | ---: | ---: | ---: | ---: |
| Full | 80% | 14 | 78.57% | 111,006.03 |
| Full | 90% | 14 | 85.71% | 168,156.26 |
| Endpoint excluded | 80% | 13 | 84.62% | 111,022.60 |
| Endpoint excluded | 90% | 13 | 92.31% | 169,136.55 |

The first 20 origins are calibration-only; usable targets start May 21, 2018. A evaluates 14 and B 13 targets. All shared intervals are identical. August 20 falls below both intervals, so exclusion removes one miss without improving calibration.

Nominal coverage is a chosen calibration level; observed coverage counts inclusive endpoint hits among usable forecasts only. Lower bounds are clipped to zero; this reduces width without changing inclusion for nonnegative targets. None of the saved evaluated intervals required clipping. Mean full widths are 45.38%/68.74% of the mean point forecast.

These wide ranges can illustrate downside/upside scenarios but are not guaranteed floors, cash budgets, or staffing forecasts. Translation into business decisions needs margin, cash-timing, order-volume and capacity assumptions. Only 14/13 targets are evaluated; dependency, stationarity and as-of availability are unverified, so no future coverage guarantee is claimed. Do not tune calibration settings on these same outcomes.

See [coverage and width metrics](../docs/forecasting/prediction-interval-metrics.csv) and the [existing uncertainty visual](../docs/forecasting/prediction-intervals.png). The older generated baseline report's "no prediction intervals" statement describes that original baseline run; the later interval experiment is separate and already implemented.

## Information availability

**1,595 of the preceding week's 1,839 eventually delivered orders were delivered on or after August 20 (86.73%).** At a Monday-start forecast origin, their eventual delivered status was not observable. Payment rows have no availability timestamps to reconstruct what was known then.

Chronological target ordering prevents direct future-row leakage, but prior rows contain retrospectively finalized outcomes. This affects model history and when calibration errors would become available. Results are **retrospective forecasting experiments, not operationally valid historical forecasts**. Operational validation would require point-in-time status/payment histories, a reporting-lag policy and genuinely available targets. The existing metric definition is unchanged.

Only 86 weeks are available, fewer than two annual cycles. Trend/ACF diagnostics are descriptive and do not establish annual seasonality or causation.

## Offline reproduction from a fresh clone

Activate Python 3.11 and install the existing pinned environment with `python -m pip install -r requirements-docker.txt`. It already includes BigQuery client, statsmodels, SciPy, patsy, matplotlib and pytest. No new dependency is needed.

The small [portfolio evidence directory](../docs/forecasting/README.md#evidence-and-reproduction) includes byte-preserving copies of the 86-row aggregate snapshot, 12-row baseline reference, selected metrics and one existing PNG. No credentials or raw customer/order identifiers are included. All other generated files stay ignored under `forecasting/outputs/`.

Run from the repository root; explicit inputs avoid dependence on pre-existing ignored files:

```powershell
python -m forecasting.weekly_revenue --input-csv docs/forecasting/source-snapshot.csv --output-dir forecasting/outputs/replay
python -m forecasting.error_analysis --snapshot docs/forecasting/source-snapshot.csv --predictions docs/forecasting/original-predictions.csv --output-dir forecasting/outputs/replay/diagnostics
python -m forecasting.backtesting --snapshot docs/forecasting/source-snapshot.csv --original-predictions docs/forecasting/original-predictions.csv --output-dir forecasting/outputs/replay/backtesting
python -m forecasting.time_series_diagnostics --snapshot docs/forecasting/source-snapshot.csv --output-dir forecasting/outputs/replay/time_series_diagnostics
python -m forecasting.statistical_candidates --snapshot docs/forecasting/source-snapshot.csv --original-predictions docs/forecasting/original-predictions.csv --output-dir forecasting/outputs/replay/statistical_candidates
python -m forecasting.prediction_intervals --snapshot docs/forecasting/source-snapshot.csv --output-dir forecasting/outputs/replay/prediction_intervals
```

The statistical-candidate CLI now accepts `--original-predictions`, matching the backtesting CLI. Previously it always read the ignored default path even when a custom snapshot was supplied. This fixes input routing only; default behavior, algorithms and verified numerical results remain unchanged.

## Docker and local validation

The Dockerfile includes `forecasting/` and selected portfolio inputs; `.dockerignore` excludes local forecasting outputs/caches. Existing ingestion, experimentation, AI, orchestration, analytics and tests remain packaged. Offline commands require no ADC or warehouse access:

```powershell
docker build -t olist-forecasting-portfolio .
docker run --rm olist-forecasting-portfolio python -m pytest tests/test_weekly_revenue_forecasting.py tests/test_forecast_error_analysis.py tests/test_forecasting_backtesting.py tests/test_time_series_diagnostics.py tests/test_statistical_candidates.py tests/test_prediction_intervals.py tests/test_ga4_ci_selection.py -q
docker run --rm olist-forecasting-portfolio python -m forecasting.statistical_candidates --snapshot docs/forecasting/source-snapshot.csv --original-predictions docs/forecasting/original-predictions.csv --output-dir /tmp/forecasting/statistical_candidates
docker run --rm olist-forecasting-portfolio python -m forecasting.prediction_intervals --snapshot docs/forecasting/source-snapshot.csv --output-dir /tmp/forecasting/prediction_intervals
```

Equivalent local checks:

```powershell
python -m pytest tests/test_weekly_revenue_forecasting.py tests/test_forecast_error_analysis.py tests/test_forecasting_backtesting.py tests/test_time_series_diagnostics.py tests/test_statistical_candidates.py tests/test_prediction_intervals.py tests/test_ga4_ci_selection.py -q
python -m pytest -q
python analytics/ci/validate_ga4.py
```

The CI guard parses with a temporary placeholder profile and checks 24 Olist / 4 GA4 model isolation plus 67 GA4 test definitions; it does not query BigQuery. The GitHub Actions parse step is also credential-free. Warehouse extraction (`python -m forecasting.weekly_revenue` without `--input-csv`) is optional, needs ADC and incurs BigQuery work; it was not run during finalization. Do not run it for offline reproduction.

Validation outcomes and any environment limitations are recorded in the finalization report; source completeness and operational validity remain unconfirmed regardless of passing tests.

## Finalization validation - October 13, 2026

| Check | Observed result |
| --- | --- |
| Local forecasting and isolation tests | 70 passed |
| Full available local suite | 457 passed |
| Docker build | Passed |
| Container forecasting and isolation tests | 70 passed |
| Full available container suite | 457 passed |
| Six offline forecasting CLIs in Docker | Passed without credentials or pre-existing ignored outputs |
| Numerical replay | Original 12 predictions, 15 model-score rows, 3 endpoint-delta rows and 4 interval-summary rows match selected saved results |
| CI-equivalent placeholder dbt parse | Passed; no warehouse execution |
| Offline target-isolation guard | Passed: 24 Olist models, 4 GA4 models and 67 GA4 test definitions |

The initial full-suite runs exposed a CRLF-versus-LF mismatch in `tests/test_ab_reporting_fixtures.py::test_dashboard_fixtures_match_deterministic_exporter`. All fixture columns, rows, ordering and exact cell strings were confirmed equal. The test now compares strict parsed CSV rows, retaining those assertions while ignoring record line-ending conventions. Both full suites were rerun: 457 passed locally and 457 passed in Docker. No fixture values or Power BI definitions changed. No passing remote CI run is claimed here.

The Docker image also includes the existing read-only A/B fixtures and semantic definitions needed by repository tests. No new dependencies were added; the existing requirement pins already cover forecasting. All original generated outputs and model formulas remain unchanged; the sole Python implementation edit is the explicit baseline-reference CLI argument.
