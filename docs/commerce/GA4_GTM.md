# GA4 / GTM preparation â€” local only

Updated 3 November 2026. This milestone implements and tests a local data layer. No Google tracking script, GTM container, consent-mode command, account configuration, export link or telemetry was activated. Existing historical GA4 models are unchanged.

## Five ecommerce mappings

| Canonical event | GA4 event | Trigger |
|---|---|---|
| product_viewed | view_item | Committed product-detail navigation |
| product_added_to_cart | add_to_cart | Committed cart addition |
| product_removed_from_cart | remove_from_cart | Committed removal |
| checkout_started | begin_checkout | First creation of a nonempty checkout |
| purchase_completed | purchase | Atomic creation of the simulated order |

`commerce_demo/ga4.mjs` validates the existing 1.0.0 canonical contract before mapping. `ecommerce.items` maps original Olist product_id â†’ item_id, fictional demo_title â†’ item_name, original category â†’ item_category, price_minor / 100 â†’ price, and quantity unchanged. currency is BRL; value_minor / 100 becomes value. Purchase uses the original demo_ order_id as transaction_id. No tax, shipping, discount, promotion, customer or payment data is invented.

Every queued ecommerce message is preceded by `{ecommerce:null,commerce:null}`, preventing a prior checkout, transaction or provenance field from leaking into the next event.

Top-level `event` is the GA4 name, `event_id` is the canonical UUID, and `commerce` holds canonical_event_name, occurred_at, session_sequence, schema_version, app_version, catalog_version, environment, activity_origin, catalog_origin, display_provenance, simulation, consent_state, device_class, app_session_id, app_anonymous_id, test_run_id, scenario_id, checkout_id and order_id. Optional identifiers are explicitly null when absent. Original canonical events remain unchanged in IndexedDB.

`occurred_at` is a custom source timestamp; this local mapping does not override Google's future collection timestamp. app_session_id/app_anonymous_id remain custom properties and must not overwrite native ga_session_id/client_id/user_pseudo_id. Original IDs, timestamps and provenance support later exact reconciliation. These custom IDs are high-cardinality diagnostics; do not register them as reporting dimensions.

Sources: [Google ecommerce guide](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce), [event parameter reference](https://developers.google.com/analytics/devguides/collection/ga4/reference/events), [data-layer processing](https://developers.google.com/tag-platform/tag-manager/datalayer).

## Offline consent and queue behavior

Run from repository root:

```powershell
$env:COMMERCE_MODE = 'offline'
$env:COMMERCE_DATALAYER = 'local'
python commerce_demo/serve.py
```

Then open http://127.0.0.1:8765 and choose Allow local event recording. Inspect `localDataLayer` in the existing Event inspector. Omit COMMERCE_DATALAYER for the normal default with no data layer. PostHog sending is a separate tab-local opt-in and is unaffected.

The local adapter owns a plain array and rejects an existing or externally instrumented dataLayer. It is intentionally unsuitable for connection to a loaded GTM runtime without a separate live adapter review. No request/SDK/cookie code exists in this module; CSP still permits only self for scripts and connections. Loading this local module is not loading Google tracking.

Only events emitted by this tab and committed to IndexedDB enter its local queue. Existing history is never exported on consent, refresh or tab creation. Same-ID retry is a no-op, conflicting content throws. The winning checkout transaction produces one event across tabs; the local sink adds no separate purchase. The queue is page-memory only, and refresh loses it. Revocation/reset clears local messages, IDs and pending entries in that tab; BroadcastChannel clears other tabs. No receipt or durable-delivery guarantee follows from a local queue.

Local recording consent is **not consent to send to Google**. Future live Google mode must have its own explicit configuration and consent action. Use basic consent: no Google/GTM loader before that grant; no cookieless pings on denial. Default analytics_storage, ad_storage, ad_user_data and ad_personalization to denied. For this analytics-only demo grant analytics_storage only; advertising stays denied. A GTM consent template must use setDefaultConsentState/updateConsentState before measurement. Revocation must stop further sends and clear pending local data. These future tag/consent changes are specified, not implemented here. [Official consent setup](https://developers.google.com/tag-platform/security/guides/consent).

## Required live account inputs and actions

Repository inspection found no configured Google demo IDs. No signed-in Google Analytics/GTM account was inspected or changed. The historical public-data dbt target does not imply ownership of a live GA4 property.

For later live verification, identify or create these isolated test resources:

| Resource | Required identifier / configuration |
|---|---|
| Standard GA4 demo property | Numeric property ID; proposed name Commerce Demo Lab; timezone Europe/Berlin, currency BRL |
| Web stream belonging to that property | Numeric stream ID and public Measurement ID G-â€¦; confirm its configured website URL and local verification origin |
| GTM Web container | GTM-â€¦ ID, account/container identity and draft workspace; dedicated demo container |
| Google access | Property Editor for setup/BigQuery linking; GTM workspace Edit access for draft/preview. Publishing is separately deferred. |

No private API secret is required for browser collection or signed-in receipt inspection. Never paste credentials. Account creation/terms, property/stream/container creation, Google tag configuration, Google Signals/advertising settings, enhanced-measurement choices and BigQuery linking are user account actions, not performed now. Use the free Standard property and Web container; no 360, server-side container, hosting or billing setup.

In the future draft workspace, configure a Google tag for the chosen G-â€¦ ID with unnecessary automatic page measurement disabled; disable enhanced measurement for this synthetic demo, no Google Signals or ads tags. Use only five exact ecommerce triggers (view_item/add_to_cart/remove_from_cart/begin_checkout/purchase), GA4 event names from the event key, and ecommerce values from the message. Explicitly allowlist the listed commerce fields as event parameters; do not forward the whole browser/global object or use wildcard triggers for arbitrary events. Check current parameter limits before implementing the live tag; do not silently drop canonical fields. Preview requires explicit authorization to load/send; do not publish a container.

Official setup checked 3 November 2026: [Analytics property and stream setup](https://support.google.com/analytics/answer/9304153?hl=en), [GTM account and Web container](https://support.google.com/tagmanager/answer/14842164?hl=en). A configured website URL is not authorization to deploy publicly; if the stream setup rejects loopback, stop and resolve that field with the user.

## Export feasibility, permissions and costs

Google documents a free BigQuery sandbox route. Standard daily export is limited to 1M events/day; use daily only and select EU storage at link creation. Sandbox has no streaming and expiring tables. Later linking requires GA4 Editor and project IAM-policy/service-enable permissions; the setup page lists Owner as a superset. Linking creates analytics_<property_id> separately from historical analytics_ga4_dev and PostHog datasets. Inspect proposed exporter grants before approving them; do not broaden existing Olist access.

Google's setup page discusses both paid-project payment requirements and the sandbox exception. Stay on the sandbox route; if the actual UI requires payment/billing, stop rather than upgrade. Paid storage/query/streaming costs are outside this approval. Daily data arrives later, not as a live receipt signal; old pre-link data is not assumed available for backfill. No export integration was built. [Official export setup, limits and billing](https://support.google.com/analytics/answer/9823238?hl=en).

## Controlled verification and evidence states

Tests reuse `tests/commerce/fixtures.mjs` and the existing catalogue. Unit assertions independently specify all five mappings and literal 10 / 6 / 3 / 1 counts. `tests/commerce/ga4-browser.mjs` uses actual storefront clicks through the supported tab API, reads the existing inspector and accepts a same-profile createTab(url) callback. It was executed against an offline loopback server on port 8766, keeping the ordinary server configuration unchanged.

Observed: ten real journeys, twenty mapped core events, ten distinct app sessions; removal mapping; refresh without historical replay; concurrent completion in two tabs produces one mapped purchase total; local retry does not requeue; withdrawal clears both tabs. Script-resource inspection found only local app.mjs, with self-only script/connect CSP. No live Google tag was loaded. One exploratory dblclick call lost its second target after the first click removed the button; the persisted purchase was single. The saved reusable regression uses normal completion and the separate two-tab contention check.

Focused checks: 10 Node tests pass; 6 Python configuration/import/reconciliation tests pass. Existing Google Python-version warnings persist. Full Python suite was not repeated; its last milestone result was 459 passed. Commerce dbt build remains 4 models + 2 seeds successful, 16 data tests passed; target isolation 24 / 4 / 4 passed.

| Evidence state | Current status |
|---|---|
| Local canonical validation | Verified |
| Local data-layer queue and actual browser interactions | Verified |
| GTM preview / Google transport acceptance | Not attempted |
| GA4 received-event inspection | Not attempted |
| New GA4 raw warehouse arrival / reconciliation | Not implemented |

For live verification later: use a new synthetic run, execute ten actual browser journeys plus a separate removal case, retain independently expected IDs and properties, then inspect GA4 receipt by those identifiers. Keep Tag Assistant firing, HTTP acceptance, DebugView receipt, daily BigQuery arrival and final SQL reconciliation separate. Verify ecommerce numbers/transaction IDs, consent denial/withdrawal, refresh, double click, concurrent tabs and retries without assuming vendor deduplication. No generated fixture can replace received-event evidence.

PostHog's saved chart is a **person-based comparison**. The canonical funnel groups app sessions and enforces earliest view, strict timestamp/sequence order, 30 minutes, and matching checkout/item snapshot. GA4 native sessions/funnels also need separate comparison; neither vendor's native aggregation automatically implements this definition.

Smallest next user action: open Analytics Admin and tell us whether a dedicated demo GA4 property already exists. Then identify its stream and the dedicated GTM container, or guide their creation one step at a time. No publishing, billing or account edits were authorized by this preparation.

## Live continuation

The user supplied the dedicated resources and authorized draft/Preview only. See GA4_LIVE.md and PROGRESS.md for the implemented adapter, importable configuration, current browser-upload blocker and pending receipt. The earlier local-only evidence above remains historical; it does not verify the new live controls.
