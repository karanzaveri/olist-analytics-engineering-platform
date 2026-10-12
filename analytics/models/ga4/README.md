# GA4 analytics

## Problem and business objectives

Raw ecommerce events show activity but do not directly answer how many sessions
progress from product discovery to purchase. This feature reconstructs sessions,
measures sequential funnel progression, supports device and acquisition
comparisons, and investigates self-referrals and ambiguous attribution before
those labels are used for business decisions. It provides a reproducible
analytical foundation, not a production attribution system or a causal study.

The source is the public historical **obfuscated GA4 ecommerce sample**,
`bigquery-public-data.ga4_obfuscated_sample_ecommerce`, limited to daily tables
for **January 25-31, 2021**. The observations below are verified warehouse
measurements supplied for this feature; rates are calculated from those counts.
They describe this sample and window, not current store performance.

## Architecture, lineage, and grain

The destination project is `mda-platform-2026`. The external `analytics` profile
keeps `dev` as its default. Olist remains in BigQuery **EU** under `dev`; GA4 is
in BigQuery **US** under `ga4_dev`. The public GA4 source and GA4 destinations
must be queried in US. The branches do not join across locations and do not
alter the existing Olist, Airflow, or Power BI workflows.

| Target | Enabled models | Location |
| --- | --- | --- |
| `dev` | 23 Olist, 0 GA4 | EU |
| `ga4_dev` | 4 GA4, 0 Olist | US |

| Model | Inputs | Grain | Materialization |
| --- | --- | --- | --- |
| `stg_ga4_events` | Public daily event shards | One row per raw event, including duplicates | View |
| `int_ga4_sessions` | Staged events | One row per `(user_pseudo_id, ga_session_id)` | View |
| `int_ga4_session_attribution` | Staged events and sessions | One row per session pair | View |
| `fct_ga4_session_funnel` | All three preceding models | One row per session pair, including non-entrants | Table |

`stg_ga4_events` is a view enabled only for `ga4_dev` (BigQuery US). The default
`dev` target remains the Olist project in BigQuery EU. `int_ga4_sessions` is an
intermediate view with the same target restriction. `int_ga4_session_attribution`
adds a custom attribution proxy. `fct_ga4_session_funnel` is the final session
funnel table, also enabled only under `ga4_dev`.

The `ga4_raw.events` source uses `identifier: "events_*"` in
`bigquery-public-data.ga4_obfuscated_sample_ecommerce`. This is the documented
[dbt BigQuery sharded-source configuration](https://docs.getdbt.com/reference/resource-properties/identifier#reference-sharded-tables-as-a-source-in-bigquery),
verified with the installed dbt-bigquery 1.12.1 relation renderer and compiled SQL.
The adapter quotes the wildcard identifier. BigQuery's
[constant _TABLE_SUFFIX filter](https://docs.cloud.google.com/bigquery/docs/querying-wildcard-tables#filtering_selected_tables_using_table_suffix)
limits reads to `events_20210125` through `events_20210131`, inclusive, excluding
intraday tables. The source itself is unbounded; retain the filter in consumers.

The model preserves every raw event row, including duplicates. Scalar correlated
parameter lookups return null for missing keys and the first array occurrence
for repeated keys, without expanding rows. `event_date` is a reporting-timezone
DATE; `event_timestamp` is a UTC TIMESTAMP converted with `TIMESTAMP_MICROS`.
First user source/medium come from `traffic_source`; event source/medium/campaign
come only from event parameters and are not inferred session attribution.
User, session, page, campaign, and ecommerce fields can be null. No uniqueness
is assumed. Schema tests require event date, timestamp, and name and check the
seven permitted dates. The staging model's four tests have passed in the warehouse
as reported by the user; the session model's 14 tests have also passed as reported
by the user. The complete GA4 warehouse suite passed **67 tests, 0 warnings,
0 errors** (4 staging, 14 sessions, 14 attribution, 35 mart). This finalization
does not rerun that suite. Static compilation is reported separately from
warehouse validation.

`event_params` is an array of key/value structs; its value struct holds typed
fields such as `int_value` and `string_value`. `UNNEST` exposes its elements for
lookup. Correlated scalar subqueries extract `ga_session_id`, source, medium,
campaign, and page location without a top-level cross join multiplying event
rows. Missing keys remain null; repeated keys use the first array offset.

## Observed sessions

`int_ga4_sessions` references only `stg_ga4_events` and groups by
`(user_pseudo_id, ga_session_id)`. Neither identifier is individually unique.
All sessions are retained, including those without purchases. Counts include
duplicate raw events, and the four funnel flags report presence of `view_item`,
`add_to_cart`, `begin_checkout`, and `purchase`; they do not imply funnel order.

Start/end are the minimum/maximum UTC timestamps observed in the January 25-31,
2021 daily-table window. Sessions crossing its boundaries may be incomplete.
Duration is nonnegative whole seconds using `TIMESTAMP_DIFF`, not engagement
time. Device selection follows the earliest timestamp, then lexical ordering of
the full staging row's `TO_JSON_STRING` as a stable tie-breaker. This uses
[BigQuery's ordered ARRAY_AGG](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/aggregate_functions#array_agg)
with a struct to preserve null device values. Exact duplicate rows yield the
same device; ties do not establish the actual collection order.

Session tests check the composite grain, non-null identifiers/timestamps/counts/
duration/flags, nonnegative counts/duration, and desktop/mobile/tablet device
categories when non-null. The validated staging sample has no null user or
session IDs, as reported by the user. Future null IDs would remain grouped and
fail identifier tests; they cannot reliably identify a real session.

The verified sample contains **273,507 raw/staged event rows**, **21,596 distinct
pseudonymous users**, and **26,355 reconstructed sessions**. Both user and session
IDs are populated in this window. `ga_session_id` alone is not globally unique;
the pair is the session key. A pseudonymous user is not necessarily a person,
and this model does not stitch identities across devices or reset session IDs.

Device conversion should use all sessions of each `device_category` as the
denominator, including non-entrants. Device is selected from the earliest
observed event with the documented deterministic tie-breaker. First-user
acquisition fields (`first_user_source`, `first_user_medium`) remain available
in staging and describe first acquisition, not session attribution. They are
not carried into the mart or substituted for missing event source/medium.
Future first-user analysis should select one deterministic user or session
record before joining to session outcomes, avoiding multiplication by events.
No device or first-user segment results are claimed here without measurement.

## Custom session attribution proxy

`int_ga4_session_attribution` left joins event attribution summaries to every
`int_ga4_sessions` row. It preserves one row per user/session pair, including
sessions with no complete source/medium pair. This is **not official GA4 session
attribution** and its channel rules are **not GA4 default channel grouping**.
It uses only events observed within the staging window, with no first-user
fallback, cross-session carryover, or inference of direct traffic from missing
parameters.

Both source and medium must be populated after trimming whitespace. The earliest
non-internal pair wins, ordered by event timestamp then source and medium
lexically. Duplicate events with equal timestamp and pair yield identical
attribution. Source and medium always come from the same event. Internal pairs
are `shop.googlemerchandisestore.com / referral` and
`googlemerchandisestore.com / referral`, matched case-insensitively.

Statuses are `Attributed`, `Internal Referral Only`, and `Unknown`. The latter
two retain null attributed source/medium and use the status as the channel.
Channels for attributed sessions use explicit direct/(none) or none, organic,
cpc/ppc/paidsearch, email, and referral rules; other pairs map to `Other`.
Distinct-pair counts include internal pairs, preserve case, and exclude
incomplete pairs; conflicts mean more than one such pair. An internal referral
followed by one external pair therefore counts as conflicting.

Schema tests reuse composite uniqueness and nonnegative checks, require session
IDs/status/channel/flags/counts, validate labels, and require source/medium for
Attributed rows. A singular test checks complete session coverage and status/
count/flag consistency. No expected fixture counts are hardcoded into tests.

Warehouse reconciliation supplied by the user: 26,355 sessions; 14,728 Attributed;
4,045 Internal Referral Only; 7,582 Unknown; 4,200 with conflicting pairs;
8,041 sessions with internal referrals.

The internal-referral flag and conflict flag overlap and must not be added as
mutually exclusive totals. Internal-only sessions are a subset of the 8,041
sessions with an internal referral. Investigate navigation across store domains,
cross-domain measurement, referral exclusions, parameter coverage, and repeated
source/medium changes as possible explanations. These are **hypotheses**, not
proven causes; self-referral observations alone do not establish a tracking bug.

## Sequential session funnel mart

`fct_ga4_session_funnel` references all three upstream GA4 models. Its grain is
one row per `(user_pseudo_id, ga_session_id)`, retaining all observed sessions,
including those without product views or purchases. Session metrics, device,
independent `has_*` flags, and all attribution fields are carried through without
changing their business rules. Required non-null session keys are used for joins.

The funnel selects the earliest `view_item`, then the earliest `add_to_cart`
whose timestamp is **>=** that view, the earliest `begin_checkout` **>=** that
cart, and the earliest `purchase` **>=** that checkout. Aggregation before the
next stage prevents repeated events from expanding the final session grain.
`funnel_*` flags require this sequence; independent `has_*` flags do not. Four
qualifying timestamps are null when their stage is not reached.

`funnel_stage_reached` is 0-4. `funnel_drop_off_stage` maps these to `Not Entered`,
`After Product View`, `After Add to Cart`, `After Begin Checkout`, and `Completed`.
The labels describe observed progression, not reasons for abandonment.

This is a historical, obfuscated GA4 sample observed only January 25-31, 2021.
Boundary sessions can be incomplete. Same-timestamp events may qualify together
under the inclusive ordering used by the validated exploratory SQL; their actual
collection order is not established. No product-level continuity is enforced:
successive stages may involve different products. Attribution remains a custom
proxy, not official GA4 session attribution.

Verified mart reconciliation (not hardcoded into outputs or tests): **26,355
total sessions**, **6,192 product viewed**, **1,090 added to cart**, **407 checkout
started**, **226 purchased**, across all devices.

| Sequential stage | Sessions | Share of all sessions | Conversion from preceding stage | Preceding-stage drop-off |
| --- | ---: | ---: | ---: | ---: |
| Product viewed | 6,192 | 23.49% | 23.49% of all sessions | 76.51% did not enter |
| Added to cart | 1,090 | 4.14% | 17.60% of viewers | 82.40% of viewers |
| Checkout started | 407 | 1.54% | 37.34% of cart sessions | 62.66% of cart sessions |
| Purchased | 226 | 0.86% | 55.53% of checkout sessions | 44.47% of checkout sessions |

View-to-purchase conversion is **3.65%** (226 / 6,192). Drop-off counts are
**20,163 not entered**, **5,102 after product view**, **683 after cart**, and
**181 after checkout**, plus **226 completed**. These categories partition the
26,355 sessions. Rates use session counts, not event counts or distinct users,
and are rounded to two decimal places. Non-entry is distinguished from drop-off
after entering; missing or out-of-order earlier stages prevent sequential
completion even when an independent purchase event exists.

Schema tests cover composite uniqueness, required dimensions and flags, accepted
stage/status/channel/device/drop-off values, and nonnegative session durations
and counts. Singular tests require exact session coverage, funnel monotonicity,
flag/timestamp consistency, inclusive timestamp ordering within session bounds,
duration consistency, and agreement between stage/drop-off labels and flags.

## Read-only analysis and further investigations

[session_funnel_analysis.sql](../../analyses/ga4/session_funnel_analysis.sql)
compiles to one read-only report over the existing mart. It returns overall,
device, custom channel, and attribution-quality cohorts with stage counts,
conversion/drop-off rates, and internal/conflicting-pair shares. Each report type
contains all sessions once; do not sum across report types. Rates are fractions
and use `SAFE_DIVIDE`, returning null for zero denominators. Segment purchase
rates divide sequential purchasing sessions by **all sessions in that segment**;
stage transition rates divide by the preceding qualifying stage in that segment.

No new segment results are invented or executed during PR preparation. Compare
segment volumes alongside rates and investigate tracking coverage before drawing
business conclusions. Observational differences by device or channel can reflect
audience mix, traffic intent, attribution quality, and measurement artifacts;
they do not prove causation. The largest measured within-funnel loss is between
view and cart, which motivates investigation, not a claim about its cause.

Recommended follow-ups: inspect first-user acquisition separately from session
attribution; audit cross-domain/referral instrumentation; quantify incomplete
boundary sessions and timestamp ties; consider product/item continuity and
purchase/revenue reconciliation; examine segment uncertainty and longer windows.
Use controlled experiments to test proposed UX changes. Obfuscation, limited
history, incomplete boundaries, no identity stitching, and simplified channel
rules constrain generalization.

## Reproduce locally and validate offline in CI

Validate from `analytics/` with the configured external profile:

```powershell
..\.venv\Scripts\dbt.exe parse --target dev
..\.venv\Scripts\dbt.exe ls --target dev --resource-type model
..\.venv\Scripts\dbt.exe compile --target dev --exclude fct_orders_incremental --no-introspect --no-populate-cache
..\.venv\Scripts\dbt.exe parse --target ga4_dev
..\.venv\Scripts\dbt.exe ls --target ga4_dev --resource-type model
..\.venv\Scripts\dbt.exe compile --target ga4_dev --no-introspect --no-populate-cache
..\.venv\Scripts\dbt.exe compile --target ga4_dev --select session_funnel_analysis --no-introspect --no-populate-cache
```

Use `dbt` in place of the Windows virtualenv path on other platforms. Keep
`profiles.yml` and authentication outside the repository. Configure `dev` with
EU and `ga4_dev` with US, project `mda-platform-2026`, and a suitable GA4 output
dataset (the validated profile uses `analytics_ga4_dev`). Never change the
default target to run GA4 implicitly.

The following warehouse commands are provided for future authorized reproduction;
they incur BigQuery work and **were not executed during PR finalization**:

```powershell
..\.venv\Scripts\dbt.exe run --target ga4_dev --select path:models/ga4
..\.venv\Scripts\dbt.exe test --target ga4_dev --select path:models/ga4 path:tests/ga4
```

After compilation, execute `target/compiled/analytics/analyses/ga4/session_funnel_analysis.sql`
as a SELECT in BigQuery US to reproduce the analysis without rebuilding models.
Use the compiled path corresponding to any custom `--target-path`. The analysis
is enabled only under `ga4_dev`; dbt compilation does not execute it.

CI preserves its existing pytest and parse steps, then runs
`python analytics/ci/validate_ga4.py` from the repository root. The added check
creates an isolated temporary placeholder profile (default `dev`), parses both
targets, verifies 23/4 model isolation and 67 GA4 test definitions, and parses
GA4 model/test/analysis definitions. It needs no
Google credentials and never runs models or data tests. It checks dbt structure
and Jinja parsing, not warehouse SQL validity, data quality, or the observed
reconciliation figures. Temporary profiles, manifests, and logs are cleaned up.
Compilation is kept local: the installed adapter can attempt authentication
even with introspection disabled, so CI does not advertise credential-free
compilation.

The parse/list/compile commands do not build models or run data tests.
Compilation is local with introspection and relation-cache population disabled;
it can initialize authentication and does not establish
warehouse schema compatibility or data-test outcomes.

The existing `fct_orders_incremental` demonstration is excluded only from local
compilation: its `is_incremental()` lookup requires adapter relation introspection
and fails with `connection never acquired for thread` when introspection is
disabled. It remains enabled and listed under `dev`. On restricted Windows
environments, compilation may also need permission to create a thread-pool pipe.
