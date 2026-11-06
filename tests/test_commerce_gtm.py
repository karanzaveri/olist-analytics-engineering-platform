from commerce_demo.build_gtm import build_container

def test_container_is_scoped_and_contains_only_approved_events():
    c=build_container()['containerVersion']
    assert c['container']['publicId']=='GTM-PHWDGH9B'
    event_tags=[t for t in c['tag'] if t['type']=='gaawe']
    assert {next(p['value'] for p in t['parameter'] if p['key']=='eventName') for t in event_tags}=={'view_item','add_to_cart','remove_from_cart','begin_checkout','purchase'}
    for tag in event_tags:
        assert next(p['value'] for p in tag['parameter'] if p['key']=='measurementIdOverride')=='G-BSKG5RGN4Y'
        assert tag['consentSettings']['consentStatus']=='NEEDED'
    assert 'analytics_storage' in c['customTemplate'][0]['templateData']
    assert 'logToConsole' not in c['customTemplate'][0]['templateData']


def test_google_tags_require_actual_gtm_preview_debug_mode():
    c=build_container()['containerVersion']
    assert any(v['type']=='DEBUG_MODE' for v in c['builtInVariable'])
    trigger_map={t['triggerId']:t for t in c['trigger']}
    for tag in c['tag']:
        if tag['type'] not in ('googtag','gaawe'):continue
        for trigger_id in tag['firingTriggerId']:
            filters=trigger_map[trigger_id]['filter']
            assert any(f['type']=='EQUALS' and {p['key']:p['value'] for p in f['parameter']}=={'arg0':'{{Debug Mode}}','arg1':'true'} for f in filters)


def test_consent_settings_use_container_export_schema():
    # Export-file literals independently observed in primary published exports;
    # REST discovery uses different casing. See docs/commerce/GTM_ENUM_FIX.md.
    c=build_container()['containerVersion']
    measured=[t for t in c['tag'] if t['type'] in ('googtag','gaawe')]
    assert len(measured)==6
    for tag in measured:
        settings=tag['consentSettings']
        assert settings['consentStatus'] in {'NOT_SET','NOT_NEEDED','NEEDED'}
        assert settings['consentStatus']=='NEEDED'
        assert settings['consentType']=={'type':'LIST','list':[{'type':'TEMPLATE','value':'analytics_storage'}]}
    assert 'consentSettings' not in next(t for t in c['tag'] if t['name']=='Commerce - analytics-only consent')
    trigger_ids={t['triggerId'] for t in c['trigger']}
    tag_names={t['name'] for t in c['tag']}
    assert all(set(t['firingTriggerId'])<=trigger_ids for t in c['tag'])
    assert all(s['tagName'] in tag_names for t in c['tag'] for s in t.get('setupTag',[]))


def test_generated_export_matches_builder_and_roundtrips():
    import json
    from pathlib import Path
    generated=json.loads((Path(__file__).resolve().parents[1]/'commerce_demo'/'gtm-container.json').read_text(encoding='utf-8'))
    assert generated==build_container()
    assert generated['exportFormatVersion']==2
    assert json.loads(json.dumps(generated))==generated
