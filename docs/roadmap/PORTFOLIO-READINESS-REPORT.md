# Portfolio readiness report

**READY WITH CAVEATS** · 6 November 2026

Release follow-up captured the seven Olist pages individually. See the [current evidence gallery](../powerbi/portfolio-evidence/README.md). The observations below record the earlier readiness pass.

The local portfolio is ready for a walkthrough using the offline replays and the new historical GA4 report export. A complete current Olist export and commit-linked hosted CI evidence remain open. This audit covers the local checkout.

## Fixed findings

- The README now lists all eight Olist report pages, labels legacy previews, links to current historical GA4 renders, and explains how the exploratory commerce branch differs from the historical US GA4 report.
- The initial hygiene inventory classified all 280 modified and untracked paths. Modified report definitions and semantic model metadata are existing project work. Untracked commerce application, model, ingestion and test files are source candidates. The generated GTM draft is an import fixture. Seeds and roadmap CSVs are reference or training data. Environment-specific profiles and vendor documentation should be reviewed for identifiers before sharing.
- The ignore rules now cover generated dbt user metadata, Power BI caches and the root pytest cache. Raw Olist and vendor exports, browser traces, generated AI output and forecast output already have ignore coverage. The path inventory and pattern results are local at the local audit output named `portfolio-hygiene-inventory.tsv`. The limited contents scan found zero private-key, Google API-key, GitHub-token or PostHog-token pattern flags across those 280 files. A full history scan and publication review remain separate tasks.
- The shared Docker/CI requirements now explicitly use pandas 3.0.6, matching the existing local requirements and the checked-in A/B fixture. The experiment logic and fixture remain as originally recorded.

## Clean-checkout and CI evidence

The initial clean checkout was a local clone of `2c0dbdc3dd318619ed1e74d4bb0b98818ada93b9`, with an empty Git status before setup. The checkout is at `%TEMP%\olist-readiness-d8e9550a`. It contains no working-tree commerce additions. The isolated rerun copied only the proposed dependency pin into that checkout.

```powershell
$repo = 'C:/Users/karan/modern-data-analytics-platform'
$clean = Join-Path $env:TEMP 'olist-readiness-d8e9550a'
git clone --no-local --quiet -- $repo $clean
Set-Location $clean
git rev-parse HEAD
git status --porcelain
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-docker.txt
./.venv/Scripts/python.exe -m pytest -q
```

The baseline install succeeded. The first suite run returned **456 passed, 1 failed**. A field-by-field comparison isolated the failure to the `pandas_version` value in `ab_summary.csv` (installed 3.1.1 versus recorded 3.0.6). The two other fixtures matched. With the proposed pin copied into the isolated checkout, `pip check` reported no broken requirements. The full isolated suite then passed **457 tests in 40.37 seconds**.

The following commands ran in the isolated checkout. The dbt profile was the workflow's temporary `ci` BigQuery OAuth placeholder, with `DBT_PROFILES_DIR` pointing to that directory and anonymous usage stats disabled.

```powershell
./.venv/Scripts/dbt.exe parse --project-dir analytics
./.venv/Scripts/python.exe analytics/ci/validate_ga4.py
./.venv/Scripts/python.exe -m forecasting.weekly_revenue --input-csv docs/forecasting/source-snapshot.csv --output-dir forecasting/outputs/replay
./.venv/Scripts/python.exe -m experimentation.simulate_experiment
./.venv/Scripts/python.exe -m experimentation.analyze_experiment
```

- Parse and isolation passed with dbt Core 1.12.5 and BigQuery adapter 1.12.1. The guard reported 24 Olist models, four historical GA4 models and 67 parsed GA4 test definitions. No warehouse data tests were executed.
- All 12 forecast rows matched the committed reference for target date, actuals, Naive, MA4 and MA8. Naive MAE was BRL 36,743.37 and WAPE was 15.13%. The local output is `forecasting/outputs/replay` in the isolated checkout.
- The seed-42 synthetic replay reproduced 4,433 users per arm, 527 A and 603 B conversions, +1.714415 percentage points, and p ≈ 0.015505. The synthetic CSV is under `experimentation/outputs` in the isolated checkout. The analyzer expects the simulation step to generate that CSV first.
- The separate working-tree suite returned **9 passed** for `tests/test_ga4_commerce_dashboard.py`, `tests/test_ga4_commerce_models.py` and `tests/test_commerce_configuration.py`.

The tracked [GitHub Actions workflow](../../.github/workflows/ci.yml) triggers on push and pull request, grants read-only contents access, installs the shared requirements, runs pytest, and parses with a placeholder profile before the historical target guard. The workflow contains no deploy job. A hosted run and commit pairing was not verified. These results are Windows local evidence. Newer commerce work and the proposed pin are uncommitted.

## Dashboard evidence and walkthrough

Power BI Desktop loaded both project files with saved local data. The historical GA4 PDF exported successfully and all three pages were visually inspected. The PNGs are rasterizations of the real Desktop PDF.

- Historical GA4 evidence. [Three-page PDF](../powerbi/portfolio-evidence/ga4-product-analytics-2026-11-06.pdf) · [Conversion](../powerbi/portfolio-evidence/ga4-product-analytics-1.png) · [Device and acquisition](../powerbi/portfolio-evidence/ga4-product-analytics-2.png) · [Attribution quality](../powerbi/portfolio-evidence/ga4-product-analytics-3.png)
- Olist Desktop observations. The eight-page project opened, and Desktop showed Exploratory GA4 Commerce, Product & Seller Performance, and A/B Quality & Decision during the export attempt. Export stopped with `PrintToPdfAsync failed`. Current full-page Olist screenshot files remain outstanding. The four-page export and README images are legacy. [Olist project](../../dashboard/Data%20Analytics.pbip) · [Legacy export](../powerbi/olist-analytics-dashboard.pdf)
- **90-second walkthrough.** Open Olist Executive Overview and describe delivered payment value by purchase month. Move to Delivery Performance to show where late-delivery risk concentrates, then point to the cohort matrix and explain observed zeros versus unobserved cells. On A/B Quality & Decision, explain why the synthetic uplift is insufficient for a rollout recommendation. Switch to historical GA4, show the loss from 6,192 product-view sessions to 1,090 sequential cart sessions, then open Attribution & Data Quality to explain the limits of the custom channel labels. Use cached data for the walkthrough.

## Remaining blockers and claims

- Capture Olist pages individually in Desktop if full-report PDF export continues to fail. Review current visual fit before replacing the legacy evidence. Static binding tests and the partial Desktop observation do not establish full-page usability.
- Review candidate files and run a history scan before publication. Obtain a hosted CI run tied to a specific reviewed commit before claiming hosted success.
- Historical GA4 is an obfuscated sample, the checkout experiment is simulated, and forecasting is retrospective. Exploratory GA4 commerce uses observed native export rows. Its source-to-warehouse reconciliation remains pending. PostHog has verified manual evidence, while native scheduled export remains unverified under the current billing restrictions. [GA4 warehouse evidence](../commerce/GA4_WAREHOUSE.md) · [PostHog warehouse evidence](../commerce/WAREHOUSE.md)
