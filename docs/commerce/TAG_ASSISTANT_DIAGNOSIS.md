# Tag Assistant connection diagnosis

3 November 2026. No live container accessed or changed. No consent granted, Google script loaded or live event sent by this diagnosis.

Confirmed root cause: the running localhost server served runtime mode offline. The user opened the bare root URL. Offline mode hides the Google grant and uses self-only CSP; the Preview adapter additionally requires ga4_preview=1 plus synthetic test_run_id/scenario_id labels and a separate explicit Google grant. Thus no GTM initialization is expected, and Tag Assistant cannot detect it before consent. This was a runtime/setup mismatch, not a verified source-code defect; no application code changed.

Evidence: localhost runtime request succeeded; initial response was export const runtime={"mode":"offline"}. The existing offline server log included the Preview visit /?gtm_debug=1793733526367, which had no application Preview or synthetic labels. Local HTTP reachability works. Offline CSP blocking Google is intentional. Extensions, browser-specific loopback access and post-consent CSP execution have not been tested or ruled out; there is no evidence to blame them yet.

Stopped only the assistant-owned offline server and started the already approved explicit ga4_gtm process on127.0.0.1:8765. Read-back now reports the dedicated GTM-PHWDGH9B and G-BSKG5RGN4Y. Returned HTML allows GTM in Preview CSP and contains no static external GTM snippet. Default source configuration remains offline. No consent was granted in any browser.

Focused checks:2 Python runtime configuration tests and4 Node Preview consent/loader tests passed. This is local evidence, not proof of a successful Tag Assistant handshake or GA4 receipt.

Retry steps:
1. Disconnect/close the previous timed-out Tag Assistant session and stale storefront tab.
2. In dedicated GTM-PHWDGH9B draft choose Preview.
3. Enter http://127.0.0.1:8765/?ga4_preview=1&test_run_id=ga4-live-2026110302&scenario_id=journey-0 and Connect. Use127.0.0.1 consistently, not localhost. Use a new numeric run suffix for a fresh verification run.
4. When the storefront opens, click Allow new synthetic events to GA4 Preview in this tab only if you explicitly consent to loading Google and sending the labelled synthetic demo events. Allow local event recording alone does not authorize Google. Do this while Tag Assistant is waiting, before its timeout.
5. Return to Tag Assistant and check Connected, GTM-PHWDGH9B, analytics_storage granted and advertising types denied. If it timed out before the grant, retry connection while this explicitly consented tab remains open. Do not publish.
6. Only then perform controlled shopping interactions. Tag firing, transport and GA4 received IDs remain separate checks. Do not claim receipt from connection alone.

If connection still fails AFTER the explicit grant: check the storefront alert and browser Network for https://www.googletagmanager.com/gtm.js?id=GTM-PHWDGH9B, its status, blocked-by-client or CSP console errors. Share only the relevant status/error, not cookies or credentials. Check both tabs use the same Chrome profile and allow the Preview popup. Do not disable security features or consent checks to force detection. No browser extension setting was changed by this diagnosis.

The Preview-configured local server is currently running, but Google remains disabled in each tab until its separate grant. Restart with COMMERCE_MODE=offline after testing to restore the ordinary process; defaults were never changed.
