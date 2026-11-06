# Native isolation and local GA4 preparation plan

User approved autonomous implementation; no account setup or live Google telemetry.
Use existing JavaScript/Python/dbt, no dependency addition. Reuse the current checkout and preserve unrelated dashboard edits.

- [x] Inspect Git, adapter/contract, actual warehouse schema and official docs.
- [x] Separate native destination events_native from manual events; retain JSON properties and APPEND.
- [x] Add optional native source union with explicit compatible columns/provenance; retain manual-only default and add source-specific reconciliation.
- [x] Add failing independent mapping/consent/retry tests, then local data-layer adapter.
- [x] Integrate only after committed canonical events; runtime opt-in COMMERCE_DATALAYER=local, existing local recording consent; no historical replay or Google loader.
- [x] Actual-browser checks of mapped checkout/removal, default-off, withdrawal, refresh and concurrent tabs; no external requests. Focused Node/Python/dbt checks.
- [x] Document five mappings, future basic consent, explicit Google account inputs, official export constraints and evidence states.

Native interval pending until 2026-11-04T00:00:00Z. Inspect once after that in a later continuation, backfill completed Nov3 interval if needed. Do not wait or poll now.

Review: added native raw/staging ID+UUID checks so manual-only models cannot satisfy native reconciliation. No new dependencies or commits.
