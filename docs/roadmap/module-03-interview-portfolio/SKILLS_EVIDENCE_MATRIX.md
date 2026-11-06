# Skills evidence matrix

Strength describes the artifact available in this checkout. **Strong** means inspectable implementation with tests or saved analytical results. **Moderate** means implementation with environment, rendering, or verification limits. **Partial** means adjacent evidence or a documented exercise. None of these ratings establishes employment experience or personal proficiency.

| Skill | Artifact | Strength | Interview talking point | Remaining gap |
|---|---|---|---|---|
| SQL and BigQuery | [Order fact](../../../analytics/models/marts/fct_orders.sql) | Strong | Preserve order grain and reconcile monetary measures | Timed SQL on unfamiliar tables, scan budgeting |
| Python and Pandas | [Experiment analysis](../../../experimentation/analyze_experiment.py) | Strong | Validate assignment and outcome data before inference | Debug a malformed extract independently |
| Ingestion | [Olist loader](../../../ingestion/olist/load_olist_bigquery.py) | Strong | Explicit schemas and replace semantics | Demonstrate failure recovery and idempotency trade-offs |
| dbt and dimensional modeling | [Model guide](../../../analytics/README.md) | Strong | Separate item and payment aggregation before the order join | Design a new fact and explain slowly changing dimensions |
| Airflow | [DAG and local behavior](../../../orchestration/airflow/README.md) | Moderate | Logical dates, dependencies, retries and independent FX | Diagnose a real failed run or backfill from logs |
| GA4 and product analytics | [Historical session definitions](../../../analytics/models/ga4/README.md) | Strong | Session grain, ordered events and attribution quality | Defend measurement design on unfamiliar event schemas |
| Local commerce measurement | [Commerce progress](../../commerce/PROGRESS.md) · [Warehouse guide](../../commerce/GA4_WAREHOUSE.md) | Moderate, local | Trace consent, event identity and separate evidence states | Produce dated native source-to-warehouse reconciliation |
| Power BI and DAX | [Olist report](../../../dashboard/Data%20Analytics.pbip) · [Cohort measures](../../powerbi/customer-retention-page.md) | Strong for implementation, moderate for current render | Diagnose context versus formatting | Verify redesigned pages and debug a context error live |
| A/B, power and SRM | [Synthetic case](../../../experimentation/CASE_STUDY.md) | Strong for synthetic work | Separate detectable effect, profitability and guardrails | Real assignment and operational guardrail evidence |
| Cohort retention and conversion | [Cohort mart](../../../analytics/models/marts/customer_cohort_retention.sql) · [Sequential funnel](../../../analytics/models/ga4/README.md) | Strong | Explain censoring, weighted denominators and stage entry | Build and defend a different eligibility window |
| Forecasting | [Saved forecast evaluation](../../forecasting/README.md) | Strong for retrospective work | Different losses select different models, as-of validity matters | Prospective evidence with mature targets |
| Testing and CI | [Workflow](../../../.github/workflows/ci.yml) · [GA4 target test](../../../tests/test_ga4_ci_selection.py) | Strong for configuration, moderate for execution evidence | Explain offline parse versus warehouse and deployment evidence | Capture a commit-linked passing run and a failure trace |
| AI output validation | [Validation logic](../../../ai/validate_insights.py) | Moderate | Check generated commentary against deterministic KPI rules | Show a sanitized rejection and recovery example |
| Excel and Power Query | [Module 1](../module-01-excel-power-query/README.md) | Partial | Explain the intended clean-and-join exercise | A completed learner workbook and refresh walkthrough |
| Communication and business judgment | [Experiment case](../../../experimentation/CASE_STUDY.md) · [Forecast case](../../forecasting/README.md) | Strong for written examples, unverified for delivery | Lead with the decision and its evidence boundary | Timed presentation and stakeholder challenge practice |

Use wording such as “In this portfolio project, the model…” and state your own contribution accurately. Present saved results as saved results. Describe synthetic outcomes and retrospective validation using those labels.
