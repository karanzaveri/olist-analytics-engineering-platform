# PostHog receipt verification — 3 November 2026

Project: 333258, EU. Read-only signed-in PostHog WebMCP project-get, execute-sql and billing-overview-get used. No personal/secret API key, paid subscription, account setting change or warehouse jobs.

Controlled run: commerce-live-1793727480072. Browser action timestamps 17:38:00.527–17:38:07.103 UTC (18:38 Berlin). Fresh isolated browser contexts, explicit cloud consent, actual UI actions. Twenty HTTP-accepted requests. Initial read exposed only one event; re-read after ingestion settled exposed twenty. HTTP acceptance and final receipt were recorded separately. Earlier diagnostic/failed run IDs are excluded, not combined into this oracle.

Independent vendor read: 20 rows; all 20 expected event IDs matched, zero missing, unexpected or duplicate IDs. Canonical names 10 product_viewed, 6 product_added_to_cart, 3 checkout_started, 1 purchase_completed. Grouping received anonymous_id/session_id and ordering timestamp/session_sequence yields 10 sessions and ordered funnel 10/6/3/1, one unique demo order. Checkout and purchase checkout_id match. This is a controlled session-path verification, not a saved PostHog UI funnel or behavioral finding.

Property checks on received rows: distinct_id equals canonical anonymous_id; event timestamp equals occurred_at; schema/app/catalog versions 1.0.0; local_demo, synthetic_test, olist_historical, manual_demo; simulation true, consent granted; BRL minor-unit total 2500; Olist product 00066f42aeeb9f3007548bb9d3f33c38, perfumaria, quantity1, fictional title/price retained. PostHog renders timestamps with six fractional digits; canonical millisecond instants preserved. No claim that its generated UUID equals canonical event_id.

Read-only receipt query: receipt-verification.sql. Full local expectations are in live-expectations.json (ignored runtime evidence); rerun live-browser.mjs with explicit configuration/authorization to generate fresh expected IDs. Current source contains no actual public capture token. Test scripts use fake public tokens for interception only.

Account compatibility observed: billing_plan=free, subscription_level=free, has_active_subscription=false, no customer ID/trial. Analytics free allocation/limit 1,000,000 events. Batch-export feature present (data_pipelines_batch_exports) and rows_exported free allocation/limit 1,000,000. Realtime destinations separate 10,000 trigger-event allowance. Billing usage summary still showed zero shortly after receipt; it is not a substitute for receipt records and may lag. BigQuery export is feasible at PostHog entitlement level; GCP IAM, region and cost/job compatibility remain for next milestone, not tested here.

Checks: 7 Node tests passed; existing pytest suite457 passed with2 Google Python-version FutureWarnings. Offline actual-browser eight groups passed with0 external attempts. Intercepted cloud gating passed. Review found/fixed delayed-import withdrawal race and repeated-grant transport replacement; delayed-import browser regression passed with0 events/requests. SDK retries, durable delivery and vendor deduplication unproven; adapter is direct Capture API with bounded explicit retries and page-memory pending set.

Server returned to default offline mode after live run. Warehouse/dbt/GA4/GTM remain deferred. Existing15 dashboard modifications preserved; changes uncommitted.

Expected IDs independently matched in vendor rows:
8658cee3-e885-4c28-b122-76d0ca5894a6
50281596-c3ba-4de8-a8c4-a9a3221efc61
0ce6034f-fc99-4824-9840-c20346bdf949
fea5ee0c-87d4-4bfb-ada9-bae2be208baf
82cc3bcf-57ac-4b42-b789-3104a050cb4b
e3725a89-30c2-4841-a2b0-2658034d08e4
b72eb93f-2c7d-48a9-b5db-9c0269737910
e990d85b-0f27-4b3f-9563-8cb2c7d4a39b
410d0767-760d-42b4-8188-c060d9cc1894
4fa9bae1-d810-4237-ac37-d089f8d5c370
d53db808-fde1-4682-a783-8633b7b382c7
242e55cb-c4e1-47b1-85d5-ff05a195292e
8873f94b-31d2-4c9a-bfa1-0d2edabe0f48
9a14e5a2-ad3a-44f8-a088-b29b8c153653
0ab328bf-26fb-4da6-839a-d80cef678dd1
3ffec618-fa25-4d7e-a3b7-ea47b6c074b7
6d9f65cc-767a-48b0-a96e-ae78ea8396ec
50b10eb9-471a-448f-9a54-927922b0ade0
fe0a882a-ad5c-4688-b133-31c9d8dfafc2
ef5d40fa-c3dc-437a-843f-4b4342c0e806
