# Platform architecture diagram

[Editable HTML source](analytics-platform.html) Â· [SVG used by the root README](../images/olist-platform-architecture.svg) Â· [Platform overview](../../README.md#architecture)

Designed with Diagram Design using the repository README hero’s deep green (#101b1b), mint (#86d8ba), and pale green (#f1f6ef) palette. A flat layout emphasizes the primary Olist pipeline and uses open typography for supporting paths. HTML is authoritative; the SVG is exported from its inline figure. System fonts keep the GitHub image portable.

## Reading the diagram

- **Olist EU:** CSVs are loaded manually by Python into RAW; dbt builds staging, intermediate and mart models. The mart branch supplies Power BI and monthly KPI commentary, plus customer analytics and historical forecasting inputs.
- **Customer lineage:** the core chain summarizes ingestion and order modelling rather than every `ref()`. Specifically, `fct_orders` feeds `int_customer_monthly_activity`, which feeds `int_customer_cohorts`; these feed retention and repeat-behaviour marts. The customer branch includes this return to intermediate models. The weekly revenue mart also consumes `fct_orders`.
- **AI:** `monthly_revenue_reporting` supplies Python KPI retrieval and Gemini generation, followed by Pydantic/numeric validation and JSON/Markdown output. Power BI does not feed the AI workflow. Numeric validation is narrower than semantic correctness.
- **FX:** Frankfurter responses have a separate Python/RAW path. There is no FX dependency in Olist metrics.
- **GA4 US:** public historical events feed a separate staging/session/attribution/funnel branch under `ga4_dev`, then a separate three-page Power BI report. No EU/US join is implied. The intermediate box summarizes model lineage: attribution reads staged events and sessions; the funnel mart also reads staged events directly.
- **Commerce EU:** the storefront is offline by default. Consent and explicit configuration gate PostHog or GTM Preview. The verified PostHog warehouse path is a manual import. Native PostHog export is unverified under current billing restrictions. The separate native GA4 export feeds the exploratory commerce page. Source-to-warehouse reconciliation remains pending.
- **Experimentation:** generated user outcomes feed statistical evaluation and disconnected CSV fixtures for Olist report pages 6â€“7. These pages share a report shell with Olist analytics; synthetic outcomes do not feed warehouse KPIs or come from observed Olist transactions.
- **Airflow:** the sequence in the bottom band mean task order, not data lineage: FX ingestion, dbt run, dbt test, AI generation. Both dbt commands exclude `fct_orders_incremental`. The DAG does not load Olist CSVs, refresh Power BI, select GA4 or run Python forecasting. Airflow is an external/local installation, not part of Compose.
- **Engineering support:** Docker/Compose, pytest and GitHub Actions are runtime/testing infrastructure. CI performs Python and JavaScript tests, parsing and four-target isolation checks, without executing BigQuery SQL.

## Design and fidelity

The six original lanes remain independent. Olist output branches appear below its main chain. The commerce inspector and opt-in GA4 branch are described as parallel storefront paths; no connection between the inspector and GA4 is implied. The PostHog endpoint summarizes commerce marts and retains the native-export limitation. Airflow is a textual task-order sequence, distinct from data lineage. Model-level dependencies remain in the reading notes above.

## Editing and export

Edit `analytics-platform.html`, then use the installed Diagram Design `scripts/export_svg.py` helper with the HTML input and `docs/images/olist-platform-architecture.svg` output, passing `--system-fonts`. Run its `self_check.py` and `verify_geometry.py` helpers against the HTML, then inspect the rendered figure and run `git diff --check`.

The former Mermaid source is retained only as a historical reference. It is no longer authoritative and is not used to generate the architecture image. Future architecture updates use designed HTML/SVG, never Mermaid.

Automated source and geometry checks passed. The exported SVG was rendered with headless Chrome and visually inspected; commerce-note spacing was corrected after that review.
