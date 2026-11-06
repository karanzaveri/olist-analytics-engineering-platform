# Commerce warehouse runbook

Verified 3 November 2026, project `mda-platform-2026`, PostHog EU project `333258`. Run `commerce-live-1793727480072` is synthetic correctness evidence.

## Evidence states

| State | Observed result |
|---|---|
| Vendor receipt | Independently queried in PostHog: 20 expected event IDs and properties; see RECEIPT.md. |
| Native export configuration | Created and enabled daily at 00:00 UTC. All five connection/ownership/project/dataset/table tests passed. No native delivery observed yet. |
| Raw warehouse arrival | Supported PostHog file-download export imported into BigQuery: 21 vendor records, including the 20 controlled events and one earlier diagnostic. |
| Model execution | 4 commerce models and 2 reference seeds succeeded; 16 dbt data tests passed. |
| Final reconciliation | All 20 expected IDs, every canonical property and original vendor timestamp matched; zero mismatches. Ten sessions, ordered 10 / 6 / 3 / 1, one logical purchase. |
| Duplicate-delivery replay | The identical vendor file was appended again: raw 21 â†’ 42, controlled deliveries 20 â†’ 40, unique vendor UUIDs 21. Clean events remained 21 overall / 20 controlled; sessions and funnel unchanged. |

Warehouse results currently demonstrate the **manual vendor-file fallback**, not successful native delivery. No local generated fixture was imported as warehouse evidence. Independent expected-ID and catalogue seeds are reference/test data only; production event models never reference the expectation seed.

## Account and permissions

Read-only checks found billing disabled, no linked billing account, existing Olist raw/analytics datasets in EU and historical GA4 in US. The PostHog account had no paid subscription and included 1M analytics events and 1M batch-export rows. Export rows are a separate allowance; repeated exports count again.

The user explicitly approved native export setup. Enabled the free Cloud Resource Manager API and created:
- `commerce-posthog-export@mda-platform-2026.iam.gserviceaccount.com`.
- Project-level `roles/bigquery.jobUser` for that account.
- Data Editor-equivalent dataset WRITER only on new EU `commerce_posthog_raw`.
- On that service account only, PostHog's documented external batch-export principal received `roles/iam.serviceAccountTokenCreator` and `roles/iam.serviceAccountViewer`.
- New EU model dataset `analytics_commerce_dev`. Both new datasets retain the sandbox's 60-day table expiry.

Final read-back confirmed billing remains disabled, only Job User at project scope, and no export-account grants on existing `raw`, `analytics_dev` or `analytics_ga4_dev`. No service-account key was generated. PostHog uses supported impersonation, never a browser-embedded secret. Existing user OAuth runs local dbt/load jobs.

Native destination: [Commerce BigQuery export](https://eu.posthog.com/project/333258/pipeline/batch-exports/01a1a289-4afb-0001-3ea0-eb8708ff4226), export ID `01a1a289-4afb-0001-3ea0-eb8708ff4226`, events-only, JSON properties, daily UTC, `commerce_posthog_raw.events_native` (separated from manual evidence during the compatibility follow-up). Do not select mutable person exports: their MERGE operations require DML, which BigQuery sandbox does not support. Immutable events use batch load jobs; sandbox excludes streaming and DML. A native configuration test does not prove its eventual load job will succeed.

No paid resources, billing activation, account switch, public deployment or broader Olist access. Sandbox quotas may reject jobs instead of charging. Current volumes are tiny; queries cap bytes at 100 MB, tables expire after 60 days. BigQuery's `bytes_billed` job accounting field can show a 10 MB minimum while project billing remains disabled; it is not evidence of a monetary charge. Adding billing, mutable exports, higher volume or retention would require a new cost decision.

Sources checked: [PostHog BigQuery export](https://posthog.com/docs/data-pipelines/batch-exports/bigquery), [supported file-download exports](https://posthog.com/docs/data-pipelines/file-download-exports), [BigQuery sandbox limits](https://cloud.google.com/bigquery/docs/sandbox), [BigQuery pricing](https://cloud.google.com/bigquery/pricing).

## Export and lineage

The native backfill UI accepts calendar dates. On 3 November it rejected both a same-day zero-length interval and an interval ending 4 November in the future. No native failed-load conclusion follows: that full daily window has not completed. Check the next run and its BigQuery load job before declaring native delivery verified.

For same-day evidence, used PostHog's supported file-download batch export:
- Export ID `01a1a28b-95e1-0002-c6df-267bb42c95de`; completed, 21 records.
- File ID `01a1a28b-b67e-0000-8605-fbacc2d276ee`; uncompressed JSONLines; interval 2026-11-03 17:30â€“17:45 UTC; four core commerce event names.
- Original local file: `data/raw/commerce/posthog-export-01a1a28b-95e1.jsonl` (ignored).
- SHA256 `44bc539e8f14c454ad353c39819f715344ffb1cd82375508f6f806368b9bdddb`.
- Corrected baseline load job `40a42e88-591c-49cb-a7c5-5360d5ea8a2b`; append replay job `607320d3-f1c2-4a93-a137-faf087de8a48`.
- Original file lines are retained verbatim in `original_record`, with file digest/import method, original UUID, timestamp, created/inserted times and JSON properties. Canonical event ID and vendor UUID remain separate.

An initial importer encoded JSON objects as strings; inspection caught it. Corrected the loader and replaced only this newly created commerce raw table from the unchanged original vendor file before baseline verification. An inferred seed timestamp and two SQL compilation issues were also corrected before the successful final build. No existing dataset was replaced.

## Reproduce

Use the existing virtual environment, authenticated user OAuth and repository root. Telemetry remains default-offline; these commands do not recapture browser events.

```powershell
.\.venv\Scripts\python.exe ingestion/commerce/load_file.py data/raw/commerce/posthog-export-01a1a28b-95e1.jsonl
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
.\.venv\Scripts\dbt.exe build --project-dir analytics --profiles-dir analytics/profiles/commerce --target commerce_dev --no-partial-parse
.\.venv\Scripts\python.exe ingestion/commerce/reconcile.py --output docs/commerce/warehouse-after-replay.json
.\.venv\Scripts\python.exe analytics/ci/validate_commerce.py
.\.venv\Scripts\python.exe -m pytest -q
```

The load command appends, so repeating it increases raw delivery count intentionally. Do not run it on arbitrary JSON/browser manifests: its vendor envelope check prevents accidental fixture import, but is not cryptographic proof of origin. The signed-in export, unchanged original file and recorded digest establish lineage here.

Dedicated nonsensitive profile: `analytics/profiles/commerce/profiles.yml`; existing external profile remains unchanged. All commerce sources/models/seeds/tests are target-gated. Offline parse verification confirms mutually exclusive model sets: dev 24 Olist / ga4_dev 4 historical / commerce_dev 4 commerce. Existing 15 Power BI edits, Olist models, GA4 target and orchestration were preserved. No new dependency was added.

Raw staging is bounded by `commerce_start` / `commerce_end` (defaults 2026-11-03 through exclusive 2026-11-04). Widen explicitly for later runs. It validates contract/provenance/catalogue, retains invalid deliveries with a flag, and deduplicates non-conflicting valid records by environment/event ID. Conflicting payloads fail a data test and are excluded. Session grain includes environment, origin, run, anonymous ID and app session ID.

Exact funnel SQL is retained in `analytics/models/commerce/fct_commerce_session_funnel.sql` with strict timestamp/sequence ordering in `analytics/macros/commerce_after.sql`: earliest-view anchor, 30 minutes, any qualifying path, added product in checkout, matching checkout ID and item snapshot on purchase. Exact-ID checks are in `analytics/tests/commerce/commerce_expected_reconciliation.sql`; all canonical properties on every controlled raw delivery are checked by `ingestion/commerce/reconcile.py`. The literal 10 / 6 / 3 / 1 oracle is specified independently in `commerce_funnel_oracle.sql`.

Local before/after JSON reports retain query job IDs and byte counts (ignored from Git). Baseline and replay clean/funnel objects are equal. Latest replay reconciliation jobs: `a59da8cd-e841-450a-a4d4-46baf45deb42`, `27ee1b6e-4da2-4415-97b5-4e5c6da6ceb2`, `ce614ac1-33ae-44dd-aa9b-3aa73d647e0a`.

## PostHog insight and limits

[Saved native funnel comparison](https://eu.posthog.com/project/333258/insights/NE2EbL5c) was created and reopened: 10 / 6 / 3 / 1 persons, 10% total conversion. It filters the controlled test_run_id and uses an ordered 30-minute person funnel.

This is a **comparison**, not the canonical app-session definition. These events carry `session_id`, not PostHog `$session_id`; the available native session aggregation requires the latter. One person has one session in this run, so counts agree. Native person aggregation does not enforce our sequence tie-breaker, earliest-view rule or checkout/item continuity. Keep the exact dbt SQL and reconciliation as authoritative for this contract.

Final automated evidence: 459 pytest passed (two Google Python-version warnings), four model successes, two seed successes and 16 dbt tests passed; three-target parse isolation passed. Local duplicate replay proves warehouse idempotence for exact duplicate deliveries. It does not prove SDK retries, vendor deduplication, native replay behavior or durable transport.

Remaining limitation: observe a completed native scheduled/backfill export and reconcile its records. No account action is currently required. GA4/GTM, public deployment and further technologies remain deferred.

## Native compatibility follow-up — 3 November 2026

Read-back caught a prior reporting error: the API returned paused=true despite the earlier enabled status report. Corrected paused=false and read back the active state. The native export now targets commerce_posthog_raw.events_native, uses JSON properties and APPEND, and keeps its existing integration, schedule and exclusion. Manual importer remains fixed to commerce_posthog_raw.events. Native writes no longer target the verified manual table. This is destination separation; the previously approved dataset-level service-account grant is unchanged, not a new table-level IAM boundary.

Actual manual schema matches the 14 documented native nullable event fields/types, JSON properties, and DAY partition on timestamp. Its five extra nullable fields (original_record, import_id, import_method, vendor_created_at, vendor_inserted_at) belong only to manual lineage. No casts of original properties or UUID substitutions are required. Native table does not exist yet, and API latest_runs is empty. At inspection the November3 UTC daily interval remained open until 4 November00:00 UTC / 01:00 Europe/Berlin. No repeated polling or premature backfill was performed.

Staging now explicitly projects compatible event columns with delivery_source/source_table/import_id. Default remains manual-only; commerce_include_native defaults false. No native fixture table was created. After actual native table arrival, verify its schema first, then run:

```powershell
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
.\.venv\Scripts\dbt.exe build --project-dir analytics --profiles-dir analytics/profiles/commerce --target commerce_dev --vars '{commerce_include_native: true}' --select path:models/commerce path:seeds/commerce path:tests/commerce --no-partial-parse
.\.venv\Scripts\python.exe ingestion/commerce/reconcile.py --source native --output docs/commerce/warehouse-native.json
.\.venv\Scripts\python.exe ingestion/commerce/reconcile.py --source combined --output docs/commerce/warehouse-combined.json
```

Inspect a completed native export's actual interval and load-job status once eligible. If it excludes the original run, use the supported UI backfill for the completed interval 2026-11-03T00:00:00Z through exclusive2026-11-04T00:00:00Z. Do not change frequency or billing to bypass eligibility. Retain the export-run/load-job IDs before declaring delivery.

Native/combined reconciliation independently requires all20 IDs/properties from native raw, plus matching native UUID/ID pairs in valid staging. It cannot pass against a manual-only model build. Deduplication still keys canonical environment/event ID across delivery channels; raw records remain separate. Native-only raw counts and combined clean counts are distinct evidence.

Rebuilt current manual models and reconciled again: raw42 (40 controlled),21 clean overall/20 controlled, zero canonical-property mismatches, ten controlled sessions,10/6/3/1, one logical purchase.4 models+2 seeds succeeded,16 tests passed;24/4/4 target isolation passed. Billing remains disabled. Native delivery remains PENDING, not verified.

GA4 local preparation and account requirements: GA4_GTM.md. Latest evidence folder: docs/commerce/evidence/2026-11-03-native-ga4-prep (local/ignored). A deliverable copy is saved under the chat outputs/evidence folder.
