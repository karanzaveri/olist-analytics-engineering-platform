# GTM container consent enum correction

3 November 2026. Local file correction only; no live container access, configuration change or publication.

## Root cause and evidence

The generator incorrectly reused the REST API value `needed` in a container export file. Its original test repeated that mistake. The user observed GTM reject it as an invalid ManualConsentOption before import preview.

These are distinct serializations:

| Meaning | Google REST API | GTM container export/import |
|---|---|---|
| Unspecified additional consent | notSet | NOT_SET |
| No additional consent requirement | notNeeded | NOT_NEEDED |
| Require the listed consent types | needed | NEEDED |

Google's [REST ConsentSetting / ManualConsentOption reference](https://developers.google.com/tag-platform/tag-manager/api/reference/rest/v2/accounts.containers.workspaces.tags#ManualConsentOption) documents the API spelling and requirement semantics. For file serialization, inspected primary published export artifacts: [DinnerBooking's own export](https://support.dinnerbooking.com/tracking-2/setup-google-ads/) contains exportFormatVersion2, NEEDED/NOT_SET and LIST of TEMPLATE string consent types; [the author's exported gtm_basic_front.json](https://gist.github.com/aristideriou/5b0466fc713f6faac4228ab13c234235) contains NOT_NEEDED/NOT_SET. These artifacts corroborate uppercase file literals; they are not a Google-published complete import JSON schema. GTM's actual error is the direct evidence that lowercase needed is rejected in this account.

## Exact change

Only these six generated JSON scalar values changed, each `needed` → `NEEDED`:

| JSON path | Tag ID | Tag |
|---|---|---|
| containerVersion.tag[1].consentSettings.consentStatus | 2 | Commerce - Google tag |
| containerVersion.tag[2].consentSettings.consentStatus | 10 | Commerce - view_item |
| containerVersion.tag[3].consentSettings.consentStatus | 11 | Commerce - add_to_cart |
| containerVersion.tag[4].consentSettings.consentStatus | 12 | Commerce - remove_from_cart |
| containerVersion.tag[5].consentSettings.consentStatus | 13 | Commerce - begin_checkout |
| containerVersion.tag[6].consentSettings.consentStatus | 14 | Commerce - purchase |

The generator's two consentStatus literals were corrected (one Google tag constructor, one five-event loop). No global case conversion or string replacement of unrelated values was applied.

`consentType` remains exactly `{"type":"LIST","list":[{"type":"TEMPLATE","value":"analytics_storage"}]}`. No NEEDED field was removed or downgraded to NOT_SET/NOT_NEEDED. The consent-initialization template has no additional-consent requirement and stays unchanged so it can establish the consent state. Consent API runtime states granted/denied remain lowercase.

## Verification

- Captured the failing input in local ignored evidence, then performed a recursive before/after JSON comparison. Exactly six differences, all paths and values listed above; every other JSON value/key/array position is unchanged.
- SHA256 checks confirm google-preview.mjs, ga4.mjs, serve.py, app.mjs and consent-template.tpl are byte-for-byte unchanged.
- Four GTM/config structure tests plus two runtime configuration tests passed (6 Python). Assertions cover exportFormatVersion2, export enum casing, exact analytics_storage requirement, source/generated-file parity, round trip, tag/trigger/setup references, the five mappings and actual Debug Mode guards.
- Fifteen Node tests passed, preserving the previous14 and adding execution of the unchanged sandboxed consent code with isolated consent-API stubs. Missing/denied consent stays denied; explicit granted changes only analytics_storage; all advertising types remain denied; completion is called once.
- These are focused local schema/behavior checks, not a full GTM importer emulator or proof of SDK/vendor behavior. Default offline mode and all explicit-consent guards remain intact.
- No browser, GTM workspace or GA4 property was accessed or modified.

Regenerated repository file: commerce_demo/gtm-container.json.
Corrected file SHA256: 8275e1102aaafffe296049a2e57b9dec4c5d1ce466d0b8d964716bf12187d35b.

Retry the manual draft Merge import using the newly named GTM-PHWDGH9B-consent-fixed.json deliverable. GTM acceptance, Preview and vendor receipt remain pending; do not publish.

