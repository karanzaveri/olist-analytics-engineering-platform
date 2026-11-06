# PostHog capture compatibility and setup

Checked official docs 3 November 2026 using Context7 and public vendor docs. No existing PostHog environment-variable names or configuration files were found. No credentials printed. No PostHog connector is installed; browser inspection is the available receipt-verification route.

## Free-plan feasibility

https://posthog.com/pricing lists a no-card Free plan: one project, one-year retention, 1M analytics events/month. Destinations have a separate 10K events + 1M rows allowance; allowances are organization-wide and not interchangeable. Free usage stops at its limit; do not enable paid usage. Public docs establish supported BigQuery export and a free destinations allowance, not entitlement or quota remaining for a particular account. Verify the destination is available in this new project's UI before a later warehouse milestone.

https://posthog.com/docs/data-pipelines/batch-exports/bigquery documents events export to BigQuery. Prefer service-account impersonation; needs project bigquery.jobs.create and dataset/table permissions (datasets.get; tables.create/get/getData/list/updateData/delete). Built-in alternatives: project Job User and dataset Data Editor, scoped only to a new dataset. Impersonation needs Token Creator and service-account read access for PostHog's documented service principal plus organization ID in account description. A destination-managing user and GCP IAM authority are needed later. No roles/datasets/accounts changed here.

BigQuery jobs/storage may incur charges separately. Sandbox limitations can prevent connector operations; do not promise compatibility without checking actual jobs. Events-only export avoids persons MERGE complexity. Native export may duplicate rows, works by arrival intervals, and backfills require downstream deduplication. https://posthog.com/docs/data-pipelines/batch-exports . Recurring extraction through /query is unsupported: https://posthog.com/docs/api/queries . No export or warehouse pipeline built here.

## Adapter choice and configuration

Direct POST to documented /i/v0/e/ rather than adding SDK/dependencies: https://posthog.com/docs/api/capture . This demonstrates PostHog API integration, not SDK installation/retry expertise. Browser sends only validated canonical events with top-level distinct_id=anonymous_id, original timestamp and canonical properties. process_person_profile=false and geoip_disable=true; no IP enrichment requested, though vendor still sees network connection metadata. event_id remains a canonical correlation property: no vendor UUID/dedup guarantee is assumed.

Default command remains python commerce_demo/serve.py (offline). For configured EU capture, set these in the server process only:

    $env:COMMERCE_MODE = 'posthog'
    $env:POSTHOG_CAPTURE_HOST = 'https://eu.i.posthog.com'
    $env:POSTHOG_CAPTURE_TOKEN = '<public phc_ token>'
    python commerce_demo/serve.py

The server exposes only this PUBLIC capture token through runtime.mjs, never personal/secret API keys. Keep values out of Git. Invalid cloud configuration fails closed. Offline CSP permits same-origin only; cloud CSP permits only the selected ingest host. No external script/CDN is loaded. Local server stays loopback-only.

Each tab starts cloud sending disabled, even if earlier local recording consent persists. Click Allow new events to PostHog in this tab before the test journey. Old offline events are never replayed. Withdrawal aborts in-flight requests best-effort and clears pending memory; delivered requests cannot be recalled. Refresh loses pending memory and requires fresh cloud consent: this minimal adapter is not a durable delivery service. At most three explicit send attempts per event; non-429 client errors stop retries. HTTP success is transport_accepted only. Network/CORS/blockers/timeouts are failures, not receipts. Inspector shows canonical events, local replay attempts, cloud pending IDs/count and transport records separately. Local replay button never sends to cloud; Retry pending cloud events is separate.

## Verification

node --test tests/commerce/contract.test.mjs tests/commerce/posthog.test.mjs

Existing browser.mjs verifies offline regression. cloud-browser.mjs intercepts all PostHog traffic to verify configuration/consent behavior without network delivery. Both export async functions compatible with the existing Playwright tool/optional runner pattern. Live verification must use a fresh unique test_run_id, exact twenty canonical events and ten isolated sessions (4 view-only, 3 cart, 2 checkout, 1 purchase), save expected event IDs, then inspect received PostHog properties and reconcile by event_id. Use saved SQL insight if native funnel cannot enforce app-session semantics; never call HTTP acceptance receipt or equate native user sessions with app sessions.

No personal API key is necessary if signed-in browser UI is accessible. Needed now: EU project ID, public capture token, and access to that project in an accessible signed-in browser. No BigQuery account changes needed for capture. Next user action at onboarding: skip automated wizard, open Project settings for ID/token; keep billing disabled.

## Completed live verification

The signed-in PostHog browser exposed read-only WebMCP tools, so no secret API credential was needed. Actual free-plan and batch-export entitlement were confirmed. RECEIPT.md records the completed live test and independent receipt reconciliation. PROGRESS.md is the continuation entry point. The server has been returned to offline mode.
