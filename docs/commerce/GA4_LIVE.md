# Dedicated GA4 / GTM Preview runbook

3 November 2026. User authorized draft configuration and explicitly consented synthetic Preview events only. No publishing, billing or unrelated-property changes.

## Current state

| Evidence | Result |
|---|---|
| Dedicated GTM identity | Browser verified Karan Analytics Lab / Commerce Demo Local / GTM-PHWDGH9B, account6402242168, container285052342, workspace2. Initially zero draft changes. |
| Consent template draft | Saved with four specific consent-write permissions and only commerce_google_consent data-layer read access; exported backup retained. No firing tag was created in the live workspace. |
| Importable configuration | Generated locally:7 tags,8 triggers,21 variables,1 cleaned consent template. Local structural tests pass. **Not yet accepted/validated by GTM import.** |
| Storefront adapter | Implemented; explicit ga4_gtm configuration, synthetic labels, separate tab grant and consent checks.14 Node tests and9 focused Python tests pass. |
| Actual live Preview journeys | Not executed. |
| Transport acceptance | Not observed. gtm_queued only means a local data-layer push. |
| GA4 vendor receipt | Not observed. |
| New GA4 warehouse arrival/reconciliation | Not implemented. |

Browser control ended during the file-upload fallback: Windows could not verify the active browser URL sufficiently for its guard. Chrome's upload helper separately required the ChatGPT extension's Allow access to file URLs setting. That permission was not enabled. No attempt was made to bypass the browser guard. Normal manual import is the next action; no broader extension permission is required for the user to select the file.

The only live workspace change completed was the unused consent-template draft. Its initial editor boilerplate remained in the exported draft; the generated import deliberately removes extra logging and a duplicate gtmOnSuccess callback. The import replaces this named template with the cleaned version. No event-tag import, Preview connection, live collection or publishing succeeded. The local storefront server was restored offline.

## Destinations

User supplied: GA4 property Commerce Demo Lab; stream Commerce Demo Local; stream ID16265125392; Measurement IDG-BSKG5RGN4Y; URL http://127.0.0.1:8765. GA4 account/property/stream configuration has not been independently inspected this turn; numeric property ID is still unknown and is not needed for browser collection. GTM identity was independently observed as above.

Repository configuration contains only public IDs. No private API key, OAuth token or Measurement Protocol secret was created or used.

## Import into the dedicated draft

The deliverable `gtm-container.json` is generated reproducibly by `python commerce_demo/build_gtm.py`. Its template and data structures come from the actual exported workspace schema; Google tag/event parameters follow the supported tag types. Successful local generation is not an import-success claim.

1. Open GTM-PHWDGH9B â†’ Admin â†’ Import Container.
2. Choose the provided gtm-container.json (also at commerce_demo/gtm-container.json in the repository).
3. Choose Existing â†’ Default Workspace (workspace2).
4. Choose **Merge â†’ Overwrite conflicting tags, triggers and variables**. Only the dedicated Commerce-prefixed items are intended to change. Do not choose whole-workspace Overwrite.
5. Review the detailed diff:7 Commerce tags,8 Commerce triggers,21 Commerce variables and1 Commerce consent template. There should be no unrelated changes or deletions. The existing same-named consent template should be replaced, not duplicated.
6. Confirm the draft import. If Google reports unknown tag fields, incompatible optimization or template validation errors, stop and retain the exact error for correction.
7. Do **not** click Submit or publish. Use Preview only.

Native tag types: googtag (supported alternate Google tag), gaawe (GA4 event), and the included container-qualified consent template. The bundle configures view_item, add_to_cart, remove_from_cart, begin_checkout and purchase separately. Google tag and ecommerce triggers also require GTM built-in Debug Mode=true (actual Preview), not merely GA4 debug_mode or a URL flag. Event triggers require hostname127.0.0.1, synthetic_test provenance, explicit commerce_google_consent=granted and test_run_id matching ^ga4-live-[0-9]+$. Google tag disables send_page_view, Google Signals and advertising personalization; automatic SDK session/engagement behavior still needs observation. No ads tags are included.

Consent Initialization uses setDefaultConsentState with four denied values and updateConsentState with analytics_storage granted only from the explicit local grant. Ads remain denied. Withdrawal triggers the same template with denied analytics; no Google tag is loaded at all before the separate grant (basic consent). Measurement tags additionally require analytics_storage.

Event tags explicitly pass canonical UUID, source timestamp and commerce metadata. Ecommerce items preserve Olist IDs and fictional display provenance; BRL minor units divide by100, transaction_id is the existing demo_ order ID. Canonical fields are not regenerated. Google event_timestamp/client_id/ga_session_id remain separate native values. The bundle sits at the standard event-parameter budget with ecommerce/custom/debug fields; inspect actual received parameters for omissions before claiming fidelity.

Sources checked: [Google tag setup including alternate method](https://support.google.com/tagmanager/answer/9442095?hl=en), [container import/export](https://support.google.com/tagmanager/answer/6106997?hl=en), [consent APIs](https://developers.google.com/tag-platform/tag-manager/templates/consent-apis).

## Launch Preview explicitly

Stop the ordinary offline server before starting this alternative process on the same port. Never run both. From repository root, with the existing virtual environment:

```powershell
$env:COMMERCE_MODE = 'ga4_gtm'
$env:GTM_CONTAINER_ID = 'GTM-PHWDGH9B'
$env:GA4_MEASUREMENT_ID = 'G-BSKG5RGN4Y'
Remove-Item Env:COMMERCE_DATALAYER -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe commerce_demo/serve.py
```

In the dedicated draft choose Preview. Use a new numeric run ID, for example a current timestamp:
`http://127.0.0.1:8765/?ga4_preview=1&test_run_id=ga4-live-<timestamp>&scenario_id=journey-0`.

On the storefront click **Allow new synthetic events to GA4 Preview in this tab**. Local recording alone never grants Google sending. The ga4_preview query flag is an application safeguard; it does **not prove** Tag Assistant is connected or that the draft was served. Confirm those separately in Tag Assistant before executing the oracle journeys. Without a Preview connection, the ordinary GTM loader may serve the existing published empty container and no GA4 event tags. Even if this configuration were accidentally published later, the Debug Mode trigger guards block Google measurement outside Preview.

Only newly emitted, committed events enter the Google pending set. Loading a tab or granting consent never replays prior history. Retries preserve canonical IDs; exact same-ID pushes are locally suppressed. Loaded-GTM/SDK retries, network durability, native vendor deduplication and purchase deduplication are unverified.

Withdrawal immediately sets the dedicated ga-disable flag, clears pending/journal entries and same-origin _ga cookie names, commits analytics withdrawal, then reloads to remove the loaded Google runtime. Already-sent requests cannot be recalled. Reload resets Google grant; cross-tab withdrawal reloads any other tab that loaded the runtime. Browser proof of these new live controls remains pending.

The CSP allows Google/Tag Assistant scripts, collection endpoints and preview frames only in this explicit runtime mode. Offline CSP retains self-only scripts and connections. No cloud loader is embedded statically in index.html. No no-script tracking pixel exists.

Restore offline after testing:

```powershell
$env:COMMERCE_MODE = 'offline'
Remove-Item Env:COMMERCE_DATALAYER -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe commerce_demo/serve.py
```

## Controlled verification still required

Use actual UI interactions, reusing the approved four view-only, three add-ending, two checkout-ending and one purchase journey. Literal expectations are20 core events,10 app sessions,10 â†’6 â†’3 â†’1 and one logical purchase. Save each journey's original canonical IDs/properties before resetting its browser state. Run a separately labelled remove-from-cart case. Do not substitute generated fixtures for received Google events.

Keep separate artifacts for:
- GTM draft import/Preview configuration and consent state.
- Browser canonical events and data-layer queue IDs.
- Tag Assistant fired/blocked tags and actual network outcomes.
- Independently observed GA4 DebugView/received-event IDs and ecommerce properties.
- Any later daily BigQuery arrival and exact SQL reconciliation.

After draft import, inspect this dedicated GA4 stream's enhanced-measurement and automatic settings; change only what is necessary to disable unnecessary collection. No such GA4 setting change was made in this turn. Verify all five received event types, source timestamp, event ID, app-session ID/sequence, run/scenario, item IDs, prices, currency/value and purchase transaction/checkout continuity. Verify denial causes no loader or collection, withdrawal stops further measurement, refresh does not replay, and double-click/concurrent tabs/retry yield one logical purchase without assuming Google's behavior.

PostHog's saved native funnel is person-based; our canonical definition is app-session based, earliest-view anchored, strict timestamp/sequence order,30-minute window and matching checkout/item snapshot. Neither PostHog nor GA4 native funnels are assumed identical.

Next user action: manually select gtm-container.json in the dedicated import screen and complete the Merge draft import above, then report whether Google accepted it. Leave the container unpublished. Once browser access resumes, continue Preview and independent GA4 receipt verification.

## Import enum correction

The first manual import rejected lowercase consentStatus=needed. See GTM_ENUM_FIX.md: regenerated file uses export literal NEEDED for the Google tag and five ecommerce tags. All other generated JSON fields are unchanged. Retry the newly named corrected file; import acceptance remains pending. No workspace was accessed during this correction.
