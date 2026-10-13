# GA4 Product Analytics - Power BI Dashboard

## Overview

A three-page product-analytics report over the public, historical, obfuscated GA4 e-commerce sample for **January 25-31, 2021**. It connects conversion performance with attribution quality so analysts can investigate funnel losses and interpret device/channel comparisons responsibly. This is a separate report from the Olist dashboard.

The reviewed exports show **26,355 sessions**, **21,596 pseudonymous users**, **6,192 sequential product-view sessions**, **1,090 add-to-cart sessions**, **407 checkout sessions**, and **226 purchasing sessions**. The sequential session purchase rate is **0.86%**. Attributed and unknown session shares are **55.88%** and **28.77%**; internal-referral and conflicting-source shares are **30.51%** and **15.94%**.

## Report structure and portfolio assets

| Page | Business purpose |
| --- | --- |
| Product Conversion Overview | Locate observed losses between product view, cart, checkout and purchase; review daily session trends. |
| Device & Acquisition Performance | Compare session-level conversion by device and custom channel alongside segment volumes. |
| Attribution & Data Quality | Assess attribution coverage, overlapping quality flags and channel-quality limitations before marketing decisions. |

### Product Conversion Overview

![GA4 Product Conversion Overview](../../docs/images/ga4/ga4-product-conversion.jpg)

### Device & Acquisition Performance

![GA4 Device and Acquisition Performance](../../docs/images/ga4/ga4-device-acquisition.jpg)

### Attribution & Data Quality

![GA4 Attribution and Data Quality](../../docs/images/ga4/ga4-attribution-quality.jpg)

[Full three-page PDF](../../docs/powerbi/GA4%20Product%20Analytics.pdf) | [Editable PBIP project](GA4%20Product%20Analytics.pbip) | [GA4 dbt documentation](../../analytics/models/ga4/README.md)

The supplied JPEGs and PDF are static snapshots. Scrollable channel tables show their visible rows; open the editable project to explore the remaining rows and slicer selections. Unknown and Internal Referral Only are retained in the report.

## Project and BigQuery source

Open `dashboard/ga4/GA4 Product Analytics.pbip` in Power BI Desktop. Keep the adjacent `GA4 Product Analytics.Report` and `GA4 Product Analytics.SemanticModel` folders together with the PBIP entry point.

- **Imported table:** `mda-platform-2026.analytics_ga4_dev.fct_ga4_session_funnel`.
- **Location:** BigQuery **US**. The GA4 dbt target is `ga4_dev`; the separate Olist target `dev` remains in EU.
- **Upstream public source:** `bigquery-public-data.ga4_obfuscated_sample_ecommerce`, limited by dbt to the seven daily event tables for January 25-31, 2021.
- **Mode:** Import, using the Google BigQuery Power Query connector and a native `SELECT *` from the existing funnel mart.

All three pages use the same imported `Sessions` table. The model's funnel-stage and quality-flag tables contain presentation labels, not additional session/event data. The [saved Sessions definition](GA4%20Product%20Analytics.SemanticModel/definition/tables/Sessions.tmdl) contains the connection and DAX measures.

## Connect and refresh

1. Ensure the existing GA4 mart is available in BigQuery US. An authorized Google account needs access to the table and permission to run BigQuery jobs in its billing project.
2. Open the PBIP project. In Power BI Desktop's data source settings, configure credentials for the existing Google BigQuery connection. Do not commit credentials or authentication files.
3. Inspect the existing `Sessions` Power Query source if your project or billing configuration differs. The saved source uses the table above and leaves `BillingProject` unset. Changing only the dbt profile does not redirect this Power BI query.
4. Use **Home > Refresh** to import the current contents of the existing mart, then verify the report totals with slicers cleared. Import mode does not query BigQuery for each slicer interaction; another refresh is needed to load warehouse changes.
5. Save the project after a successful refresh. Refresh reads the mart; it does not rebuild dbt models. Follow the [GA4 dbt reproduction guide](../../analytics/models/ga4/README.md#reproduce-locally-and-validate-offline-in-ci) for an intentional upstream rebuild.

See Microsoft's [Google BigQuery connector documentation](https://learn.microsoft.com/en-us/power-query/connectors/google-bigquery) for authentication and billing-project configuration. Power BI Service deployment and scheduled refresh are not configured by this repository. No warehouse rebuild or refresh was performed during documentation packaging.

## Session-grain definitions

A session is one reconstructed `(user_pseudo_id, ga_session_id)` pair. `ga_session_id` alone is not globally unique. Total sessions include non-entrants; pseudonymous users are distinct identifiers, not necessarily people.

The sequential funnel requires a product view followed by cart, checkout, and purchase with nondecreasing timestamps. Measures use the `funnel_*` flags, not the independent event-presence `has_*` flags. Counts represent sessions reaching each stage, not numbers of events or orders.

- **Stage conversion:** qualifying sessions at the next stage / qualifying sessions at the preceding stage.
- **Session purchase rate:** sequential purchasing sessions / all sessions in the current filter context, including non-entrants. Device and channel rows use their own sessions as the denominator.
- **Attribution coverage:** the mutually exclusive `Attributed`, `Internal Referral Only`, and `Unknown` statuses partition the selected sessions. Status-row shares use selected sessions across statuses.
- **Quality rates:** sessions with `has_internal_referral` or `has_conflicting_sources` / all sessions in the current context. Channel-quality rates use all sessions in that channel. The flags can overlap.
- **UTC session-start date:** derived from the observed session-start timestamp; it can differ from GA4's property-local event date.

Device, custom-channel, and UTC date slicers filter the analytical visuals on Pages 2 and 3. Rate denominators follow those selections.

## Key DAX metrics

These are existing model measures, not new calculations introduced by this documentation:

```dax
Total Sessions = COUNTROWS('Sessions')

Pseudonymous Users = DISTINCTCOUNT('Sessions'[user_pseudo_id])

Viewed Product Sessions =
    COALESCE(CALCULATE([Total Sessions],
        KEEPFILTERS('Sessions'[funnel_viewed_product] = TRUE())), 0)

Sequential Purchasing Sessions =
    COALESCE(CALCULATE([Total Sessions],
        KEEPFILTERS('Sessions'[funnel_purchased] = TRUE())), 0)

Overall Sequential Session Purchase Rate =
    DIVIDE([Sequential Purchasing Sessions], [Total Sessions])

View-to-Cart Rate =
    DIVIDE([Added to Cart Sessions], [Viewed Product Sessions])

Internal Referral Session Share =
    DIVIDE([Internal Referral Sessions], [Total Sessions])

Conflicting Source Session Share =
    DIVIDE([Conflicting Source Sessions], [Total Sessions])
```

Added-to-cart and checkout measures use `funnel_added_to_cart` and `funnel_started_checkout`. Attribution counts filter `attribution_status`; quality counts filter the existing Boolean flags with `KEEPFILTERS`. `DIVIDE` handles zero denominators safely; the model formats rates to two decimal places.

## Attribution methodology and limitations

The earliest complete non-internal source/medium pair within the observed session supplies a **custom session-level attribution proxy**. It is not official GA4 attribution or GA4 default channel grouping. Internal pairs are referrals from `shop.googlemerchandisestore.com` or `googlemerchandisestore.com`; conflicting sources mean more than one complete source/medium pair, including internal pairs.

The seven-day sample is historical and obfuscated. Sessions crossing the window boundary may be incomplete. Equal timestamps can qualify together, product continuity across stages is not enforced, and identities are not stitched across devices. Small segments can produce unstable rates.

Observed device/channel differences are not causal explanations or randomized A/B test outcomes. Internal referrals and conflicting pairs motivate investigation of tagging and referral handling; they do not prove a tracking defect. The dashboard contains no simulated A/B outcomes or revenue metrics.

The existing [GA4 dbt documentation](../../analytics/models/ga4/README.md) records the warehouse reconciliation and 67 passing GA4 tests. The dashboard has been reviewed and reconciled in Desktop as reported by the project owner. Packaging verified the supplied assets and links without rerunning BigQuery or Desktop interactions.
