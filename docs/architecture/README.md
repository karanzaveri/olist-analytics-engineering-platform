# Platform architecture diagram

[Editable Mermaid source](analytics-platform.mmd) · [SVG used by the root README](../images/analytics-platform-overview.svg) · [Platform overview](../../README.md#architecture)

The source is authoritative. The SVG is a Mermaid CLI export, with no manual changes to labels, geometry or dependency arrows. Theme, typography, spacing and accessible title/description are defined in the source. Plain SVG text avoids HTML labels and external font or image dependencies.

## Reading the diagram

- **Olist EU:** CSVs are loaded manually by Python into RAW; dbt builds staging, intermediate and mart models. The mart branch supplies Power BI and monthly KPI commentary, plus customer analytics and historical forecasting inputs.
- **Customer lineage:** the core chain summarizes ingestion and order modelling rather than every `ref()`. Specifically, `fct_orders` feeds `int_customer_monthly_activity`, which feeds `int_customer_cohorts`; these feed retention and repeat-behaviour marts. The customer branch includes this return to intermediate models. The weekly revenue mart also consumes `fct_orders`.
- **AI:** `monthly_revenue_reporting` supplies Python KPI retrieval and Gemini generation, followed by Pydantic/numeric validation and JSON/Markdown output. Power BI does not feed the AI workflow. Numeric validation is narrower than semantic correctness.
- **FX:** Frankfurter responses have a separate Python/RAW path. There is no FX dependency in Olist metrics.
- **GA4 US:** public historical events feed a separate staging/session/attribution/funnel branch under `ga4_dev`, then a separate three-page Power BI report. No EU/US join is implied. The intermediate box summarizes model lineage: attribution reads staged events and sessions; the funnel mart also reads staged events directly.
- **Experimentation:** generated user outcomes feed statistical evaluation and disconnected CSV fixtures for Olist report pages 6–7. These pages share a report shell with Olist analytics; synthetic outcomes do not feed warehouse KPIs or come from observed Olist transactions.
- **Airflow:** thick arrows in the top band mean task order, not data lineage: FX ingestion, dbt run, dbt test, AI generation. Both dbt commands exclude `fct_orders_incremental`. The DAG does not load Olist CSVs, refresh Power BI, select GA4 or run Python forecasting. Airflow is an external/local installation, not part of Compose.
- **Engineering support:** Docker/Compose, pytest and GitHub Actions are runtime/testing infrastructure. CI performs Python tests, parsing and target-isolation checks, without executing BigQuery SQL.

Solid arrows inside data bands show flow; thick arrows inside the Airflow band show orchestration. Invisible Mermaid links only place the independent bands and engineering boxes. Their source comments identify them explicitly; they carry no dependency meaning. The diagram claims implemented structure, not a fresh execution, a production deployment or operational forecasting validity.

## Export

Run from the repository root with Node.js and a Chromium-compatible browser available. This export uses **Mermaid CLI 11.12.0**; retain the pinned version when reproducing it. npm may download renderer dependencies and its browser on first use. They are tooling dependencies, not project runtime dependencies.

```bash
npx --yes --package @mermaid-js/mermaid-cli@11.12.0 mmdc -i docs/architecture/analytics-platform.mmd -o docs/images/analytics-platform-overview.svg -b white -w 1600 -H 1600
```

To use an existing Chrome/Chromium installation instead of a downloaded browser, set `PUPPETEER_EXECUTABLE_PATH` to that installation or pass `-p` with an external Puppeteer JSON configuration. Keep machine-specific browser paths and profiles outside the repository. Renderer settings live in the Mermaid source; no repository package manifest or lockfile is needed.

For the refresh, the pinned CLI was installed in a temporary directory, run with local headless Chrome, and exported directly from the source. A second export to a temporary SVG was compared byte-for-byte with the repository SVG. Temporary previews and tooling are not repository assets.

## Review after edits

1. Edit the Mermaid source and regenerate the SVG with the same command/settings. Do not hand-edit the export.
2. Inspect the SVG as an embedded image at README width. Check typography, text bounds, arrow routing, independent bands and the EU/US distinction. Confirm it contains no HTML `foreignObject`, scripts or external resource references.
3. Re-export to a temporary SVG and compare it with the repository SVG to establish source/export consistency.
4. Verify Markdown links relative to each document, source/output labels against implementation, and `git diff --check`. Inspect new documentation files for trailing whitespace too, since ordinary `git diff` omits untracked files.

The [previous PNG](../images/analytics-platform-overview.png) remains preserved as a historical asset; the root README uses the new SVG.
