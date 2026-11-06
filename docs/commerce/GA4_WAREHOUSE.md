# Native GA4 commerce dbt branch

The EU target `ga4_commerce_dev` points to the isolated output dataset `analytics_ga4_commerce_dev`. The source resolves to one completed native daily table in `mda-platform-2026.analytics_562157149`. The default suffix is `20261103`; set `ga4_commerce_daily_suffix` explicitly for another completed date. This keeps intraday tables out and bounds each build to one shard. Sessions and conflicts spanning shards require a separately designed multi-shard check.

- `stg_ga4_commerce_events` retains the native parameter, item, ecommerce and privacy records and emits typed canonical fields, the native timestamp, an item snapshot, a canonical payload hash, and a validity flag. Duplicate canonical parameter keys fail validity. The exported value can occupy the integer or double slot. Amounts normalize to BRL minor units. Item validation checks structural and monetary consistency; exact membership and fidelity require the independent browser manifest.
- `fct_ga4_commerce_session_funnel` groups by environment, origin, run, app anonymous ID and app session ID. GA4 session identifiers are diagnostic only. Invalid or conflicting deliveries disqualify their canonical ID; exact canonical replays count once. The earliest view anchors an inclusive 30-minute window. A qualifying add follows a view of the same product, checkout follows an add and contains its product, and purchase follows checkout with the same checkout ID and normalized item multiset. Source timestamp and sequence determine strict order. Removal is counted separately. Each environment/order ID counts once, and conflicting app session, checkout or item signatures disqualify the order.

The November 3 export has 37 exploratory ecommerce rows from **one app session and four distinct purchases**. The ten-session **10 → 6 → 3 → 1** benchmark is an independent offline fixture of 20 events. Native completeness and source-to-warehouse reconciliation remain pending. The existing PostHog benchmark is a separate population.

From repository root, run the offline checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_ga4_commerce_models.py
.\.venv\Scripts\python.exe analytics/ci/validate_commerce.py
```

The fixture suite executes the actual funnel SQL against normalized rows in SQLite. It covers replay, event and order conflicts, sequence ties, time-window edges, product and checkout continuity, and removal. The isolation check uses credential-free dbt parse. BigQuery execution of staging and warehouse data tests remains pending.

For the next review, retain the controlled run's sealed source manifest and wait for its completed daily export. Compare exact IDs and canonical fields, including duplicates and conflicting payloads. After separate approval, confirm the isolated EU output dataset is available and run only this branch for the reviewed shard:

```powershell
.\.venv\Scripts\dbt.exe build --project-dir analytics --profiles-dir analytics/profiles/ga4_commerce --target ga4_commerce_dev --select path:models/ga4_commerce path:tests/ga4_commerce --vars '{ga4_commerce_daily_suffix: "YYYYMMDD"}'
```

Validate the ten benchmark sessions independently and report the removal scenario separately. A successful build alone does not establish source completeness.
