# Phases 0–1 implementation plan
Approved design: chat deliverable commerce-product-analytics-design.md, 3 November 2026.
Execute inline. Preserve existing 15 modified dashboard files; do not commit unrelated work.
1. Write independent fixture expectations and contract/catalog checks; observe failure.
2. Implement deterministic catalog generator, strict versioned contract and session funnel.
3. Implement static storefront with transactional IndexedDB orders/events and consent-bound local inspection.
4. Verify real browser journeys, consent, refresh, double click, concurrent tabs and local retry; record evidence separately from unimplemented vendors/warehouse.
5. Run existing pytest suite and inspect diff. No telemetry, services or deployment.
Routine decisions: native ES modules and Node built-in test runner; Python stdlib catalog/server; no runtime dependencies. Retry means local inspection sink replay, not vendor transport. Browser automation uses environment tools; document repeatable script.
