# Offline commerce lab

Phases 0–1 only. Run from repository root:

```powershell
python commerce_demo/serve.py
```

Open http://127.0.0.1:8765 in a modern browser. Keep the server bound to loopback. No build, packages, accounts or remote assets required. Node 18+ runs the contract tests; Node 24 was used here.

```powershell
node --test tests/commerce/contract.test.mjs
python commerce_demo/build_catalog.py
```

The generator requires the existing ignored Olist product/order-item CSVs in data/raw/olist. It sorts eligible product IDs and takes twelve, then creates a separate fictional display overlay. catalog.mjs is the committed reproducible snapshot; sourceChecksums record the input SHA256 digests. No source CSVs or historical models are changed. Names, descriptions, prices and placeholders are fictional. Original product_id/category remain in source objects. No actual photo URLs exist.

Use Allow local event recording, view an item, add it, open Cart, start checkout and complete a simulated purchase. The inspector shows validated events and the ordered session funnel, and downloads local evidence. Default recording is off. Denial/withdrawal removes local events/identity/attempts while preserving functional cart/orders. Reset entire demo clears everything. No PostHog/Google SDK or transport is installed; CSP prohibits network connections. Even when recording is allowed, all events remain local.

IndexedDB serializes read/write state transactions across tabs. Completion atomically stores order and its event, keyed by checkout ID. Refresh reads the existing order. Browser-profile/origin/storage lifetime bounds this guarantee: clearing storage or another device starts over. Cart edits invalidate checkout. Analytics timestamps and sequence permit deterministic ordering; sessions expire after thirty inactive minutes. Local event recording is consent-bound, not a legal consent management platform.

Replay latest event copies the exact payload into a separate local-delivery-attempt journal, preserving event and order IDs. It does not create an order or a canonical event. This verifies local replay invariants, not network-failure recovery, vendor deduplication or guaranteed delivery. No vendor outbox is implemented in these phases.

## Contract 1.0.0

Source: commerce_demo/contract.mjs. Strict allowlist validation rejects missing fields, unsupported versions/enums, malformed timestamps/event UUIDs, invalid integers, unknown products, wrong catalog values, empty/duplicate items and inconsistent totals. Events: product_viewed, product_added_to_cart, product_removed_from_cart, checkout_started, purchase_completed. Each has UTC timestamp, session sequence, pseudonymous identity, event UUID, schema/app/catalog versions, environment, consent, origin, simulation flag, items, integer BRL minor-unit total. Checkout/purchase carry checkout_id; purchase additionally requires demo_ order ID. Synthetic events require test_run_id/scenario_id; manual events forbid them. IDs are local pseudonymous identifiers, never historical customers/orders. No GA4 mapping is executed yet.

Product views fire on detail navigation, additions/removals after committed state change, checkout on new nonempty checkout and purchase on transactionally stored completion. Same-ID/different-content retries are conflicts. Logical events deduplicate by environment/event ID, with a separate purchase-order conflict check. The offline funnel anchors on first view, enforces thirty minutes and strict timestamp/sequence order, searches valid paths so an abandoned checkout cannot hide a later matching purchase, and compares checkout item snapshots.

## Reproduce browser evidence

The environment's Playwright tool executed tests/commerce/browser.mjs using actual clicks and isolated contexts, not injected events. With an existing local Playwright installation, import its default function and call it with a page whose browser supports newContext; first navigate the page to http://127.0.0.1:8765. No Playwright package/browser was added to this repository. The exported async function throws on failure and returns evidence on success. The test blocks and records all non-loopback requests. Test query parameters label actual browser journeys as synthetic; they do not inject events. Use a dedicated browser profile for manual replay.

Independent oracle: four view-only sessions, three ending after add, two after checkout and one purchase. Literal expected stage counts are 10/6/3/1, twenty core events, one order. Fixtures and browser tests specify expectations independently of production funnel code. Scripted traffic establishes correctness only.

## Evidence recorded 3 November 2026

- Offline contract: three Node tests passed initially; see subsequent verification record for final count.
- Actual browser: ten journeys produced 10/6/3/1 and twenty core events.
- Double click and refresh: one order and purchase.
- Two concurrently completing tabs: one order and purchase.
- Two local replay attempts: same original event ID and one order.
- Withdrawal: analytics cleared, order retained, denial survives refresh.
- Denied recording: purchase works with zero events/identity.
- Remove item: removal event and empty-checkout guard passed.
- Eighty-five loopback requests observed across suite, zero external requests attempted.
- Vendor receipt: NOT IMPLEMENTED. Warehouse reconciliation: NOT IMPLEMENTED.

## Learning and limits

Explain event versus order grain; local consent versus delivery; transaction serialization versus disabled buttons; why a retry keeps event_id; why raw attempts differ from logical events; app versus vendor session definitions; why scripts cannot establish behavior or uplift. Debug using the visible alert, inspector and browser console. A missing event after denied consent is expected; a second order for one checkout is an implementation defect.

No cloud, billing, public deployment, target/model or orchestration changes. Existing 15 modified GA4/Power BI files were present before work and are preserved. Runtime dependencies: Python/Node standard libraries and browser APIs only. Browser automation is an environment verification facility, not a bundled production dependency. Storage is intentionally small-demo scale, not production or a payment ledger. New tests are invoked separately from the existing Python suite.

Final verification: node --test tests/commerce/contract.test.mjs: 4 passed. Existing Python suite: 457 passed, 2 Google Python-version FutureWarnings, no failures (57.61 seconds). No cloud validation performed.

Optional standalone browser command: `node tests/commerce/run-browser.mjs` while local server runs. This requires an already installed Playwright package and Chromium. Set PLAYWRIGHT_MODULE to an absolute Playwright module entry if it is installed outside module search paths. No such dependency was installed here; the available environment browser tool ran the same exported verification function. Adding Playwright as a development dependency later is justified only for portable automated browser verification, never required to run the storefront.

Review follow-up: fixed tab-local test provenance (manual visits no longer inherit synthetic labels) and cross-tab withdrawal via BroadcastChannel plus fresh export reads. Added real-browser regressions; final complete browser suite passed all eight scenario groups with 95 loopback requests and zero external requests. Desktop 1280×800 and mobile 390×844 have no horizontal overflow. Initial async UI assertion was corrected to wait for committed render. Existing git diff --check reports pre-existing trailing blank lines in dashboard semantic model files; those files were not changed by this work.

## PostHog milestone

Phases 0–1 evidence above is historical. Current continuation state and blockers are maintained in PROGRESS.md; configuration, compatibility, costs and transport limitations are in POSTHOG.md. The default server remains offline. Optional PostHog Capture API integration and independently verified live vendor receipt are complete; see RECEIPT.md. No SDK retry/deduplication claim is made.

## Warehouse milestone

The isolated EU commerce dbt target and vendor-file warehouse reconciliation are verified. Native export is configured with successful connection tests; native delivery remains pending. See WAREHOUSE.md for reproducible commands, exact SQL locations, replay results, permissions and costs. PROGRESS.md is the current evidence-state summary.

## Local GA4/GTM preparation

GA4_GTM.md documents the optional local data layer, five ecommerce mappings, consent controls, actual-browser evidence and future account requirements. No Google tag or live telemetry is enabled. Native PostHog export now targets events_native separately from accepted manual records; see WAREHOUSE.md and PROGRESS.md for pending interval status.

## Live Google Preview continuation

Optional ga4_gtm mode, public destination IDs, separate explicit consent and an importable draft are implemented. GTM import, actual Preview and GA4 vendor receipt remain pending a browser-access blocker. See GA4_LIVE.md. Default launch remains offline.

## Approved standalone browser checks on Windows

From the repository root, point the launcher at the existing standalone worker directory:

```powershell
$worker = 'C:\path\to\browser-agent'
.\.venv\Scripts\python.exe tests/commerce/run-olist-browser.py inspector --worker-root $worker
.\.venv\Scripts\python.exe tests/commerce/run-olist-browser.py journey --worker-root $worker
```

The inspector is read-only and runs in agentic mode after authenticated FreeLLMAPI model readiness passes. The journey uses deterministic mode and requires no gateway or credential. It stops at simulated checkout review. Both commands start and stop their own offline storefront on port 8765 and refuse an occupied port. Each run writes a concise JSON summary under the standalone worker's reports/olist-launcher directory with links to its detailed evidence. Run the checks sequentially.

The launcher accepts only the two reviewed task files and verifies their hashes. Keep scope changes, new browser tasks and vendor interactions behind the manual ChatGPT review checkpoint.

## Offline GA4 source-manifest rehearsal

Use an existing local Chromium and Python Playwright installation. The runner starts and stops its own loopback-only server on an ephemeral port. It exercises the reviewed synthetic matrix with local recording only and blocks requests outside that exact origin.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& $browserPython tests/commerce/manifest-rehearsal.py --chromium $chromium
```

The inspector exposes **Download source manifest** only in explicit offline mode with `source_manifest=1`, a `ga4-rehearsal-` run ID followed by 25 digits, and a valid scenario label. Local recording must be enabled to download. The app atomically adds source records in IndexedDB alongside canonical event updates and releases delivery eligibility after commit. A journal failure rolls back the transaction and stops further capture in that page. Withdrawal or reset removes the origin's source journals and pending local tracking state. Use disposable browser contexts and close them after exporting evidence.

The runner writes sealed evidence under the Git-ignored `docs/commerce/evidence/<run-id>/` directory. Keep only synthetic evidence, restrict it to the local reviewer, and delete the run directory after review or within **seven calendar days of capture**, whichever comes first. Apply the same limit to incomplete runs and copied downloads. Remove local copies promptly if withdrawal applies to their contents. The browser cannot retract already exported files.

This evidence proves source capture and offline behavior. Live Preview arming, consent and transmission require separate approval and a separate validation step.
