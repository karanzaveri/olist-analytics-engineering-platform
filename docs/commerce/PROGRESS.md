# Commerce extension progress

Latest update — GTM consent enum import fix (3 November 2026): user reported ManualConsentOption rejecting needed before preview. Verified REST-versus-export spelling against Google's API reference and primary export artifacts. Corrected only six consentSettings.consentStatus scalars to NEEDED; analytics_storage LIST/TEMPLATE, all five mappings, Debug Mode/consent/run guards and runtime/template bytes remain unchanged. Regenerated the import file and proved exactly six JSON differences.6 focused Python and15 Node tests pass. No live container/browser access or publication. User will retry manual import; GTM acceptance and GA4 receipt remain pending. Detailed paths, sources and checksum: GTM_ENUM_FIX.md.


Updated 3 November 2026. Live GA4/GTM implementation prepared; browser setup blocked during import. **GA4 vendor receipt remains unverified.**

Current dedicated resources (user supplied): Commerce Demo Lab / Commerce Demo Local, stream16265125392, G-BSKG5RGN4Y, http://127.0.0.1:8765. GTM Karan Analytics Lab / Commerce Demo Local / GTM-PHWDGH9B was independently observed in Chrome (account6402242168/container285052342/workspace2).

- Repository Git state checked before editing; reused existing checkout. Existing15 dashboard modifications preserved;76 dashboard/ga4 files match recorded SHA256. No historical dbt model or orchestration edits in this turn.
- Created and saved one unused consent-template draft in the dedicated workspace; exported actual draft backup. No Google measurement firing tag was configured in the workspace, no container publish or unrelated-property edit.
- Implemented a separate lazy-loaded Google Preview adapter. Requires explicit ga4_gtm mode, exact dedicated public IDs, synthetic labels, application Preview flag and a separate tab consent grant. Default remains offline. New committed events only; canonical IDs/properties preserved, local duplicate pushes suppressed. Withdrawal disables the dedicated measurement, clears local pending/journal and reloads after committing withdrawal. Current live controls still require actual-browser proof.
- Generated commerce_demo/gtm-container.json:7 tags,8 triggers,21 variables,1 cleaned consent template. All Google measurement triggers require GTM built-in Debug Mode=true plus loopback/consent/provenance/run guards. Local structural tests pass; **GTM import acceptance is pending**, not implied by JSON generation.
- Upload API required the Chrome extension's Allow access to file URLs setting; not enabled. The supported normal-picker fallback was then stopped by the Windows browser-URL guard. Browser work ended without attempting to bypass the guard. No Preview connection, synthetic live journey, HTTP acceptance or GA4 receipt was observed.
- Focused local checks passed:14 Node tests,9 Python tests (two existing Google Python-version warnings). Full suite not repeated. Current app syntax checked. No new dependencies, billing changes, account changes outside the dedicated draft, public deployment, commit or push.
- Restored http://127.0.0.1:8765 server to offline. Preview code remains explicitly opt-in.

Fallback import/Preview runbook: GA4_LIVE.md. Generated public configuration and consent template are available as chat output deliverables. Latest evidence: docs/commerce/evidence/2026-11-03-ga4-live (actual pre-import draft export + local verification summary).

Smallest next user action: in dedicated GTM-PHWDGH9B Admin → Import Container, select the generated gtm-container.json, choose Existing → Default Workspace, Merge → overwrite conflicting Commerce items, review no unrelated changes/deletions, then confirm only the draft import. Do not Submit/publish. Tell us whether Google accepts the import; resume actual Preview and independent GA4 receipt verification afterward. The detailed runbook covers startup and consent; no secret API key needed.

Evidence states: prior PostHog receipt VERIFIED; accepted manual warehouse reconciliation VERIFIED; native PostHog delivery PENDING (not checked in this Google milestone); previous offline data-layer/browser milestone VERIFIED; current live adapter unit/config checks VERIFIED; GTM import/Preview/transport/GA4 receipt PENDING; new GA4 warehouse integration DEFERRED.

Prior accepted evidence remains: manual raw42 deliveries (40 controlled),21 clean overall/20 controlled, all20 expected IDs/properties, ten controlled app sessions,10 →6 →3 →1 and one logical purchase. Last dbt build4 models+2 seeds and16 tests passed; last target-isolation check24 Olist/4 historical GA4/4 commerce. No warehouse changes in this turn.

PostHog saved chart remains a person-based comparison. Canonical app-session SQL uses earliest view, strict timestamp/sequence order,30 minutes and matching checkout/items. GA4 native sessions/funnels are not assumed equivalent.


Latest: user reports GTM import accepted (37 added,1 modified,0 deleted). Preview timeout diagnosed locally: server was offline, log showed bare root plus gtm_debug only, and app Preview/synthetic labels and separate consent were absent. Started the approved opt-in Preview process without granting consent; HTTP/CSP checks pass,2 Python and4 Node focused tests pass. No code changes or browser/GA4 receipt verification. Default code stays offline. See TAG_ASSISTANT_DIAGNOSIS.md for exact retry steps.
