"""Read-only warehouse reconciliation against browser expectations, never source generation."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from google.cloud import bigquery
PROJECT='mda-platform-2026'
RUN='commerce-live-1793727480072'

def verify_deliveries(selected, expected):
    actual={r['properties']['event_id']:r for r in selected}
    assert set(actual)=={e['event_id'] for e in expected},'event ID gap'
    expected_map={e['event_id']:e for e in expected}
    for r in selected:
        e=expected_map[r['properties']['event_id']]
        assert r['event']==e['event_name']
        assert r['timestamp']==datetime.fromisoformat(e['occurred_at'].replace('Z','+00:00'))
        for k,v in e.items():assert r['properties'][k]==v,(e['event_id'],k)
        assert r['uuid'], 'missing vendor UUID'
        if r['delivery_source']=='manual_vendor_file_export':
            assert r.get('original_record'), 'missing manual original record'
            original=json.loads(r['original_record'])
            assert original['uuid']==r['uuid'] and original['properties']==r['properties']
        else:
            assert r['delivery_source']=='native_batch_export', 'unknown delivery provenance'
    return len(actual)

def verify_source_deliveries(selected, expected, required_sources):
    for source in required_sources:
        verify_deliveries([r for r in selected if r['delivery_source']==source],expected)
    return len({r['properties']['event_id'] for r in selected})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--source',choices=['manual','native','combined'],default='manual');args=parser.parse_args()
    c=bigquery.Client(project=PROJECT)
    jobs=[]
    def query(sql):
        config=bigquery.QueryJobConfig(maximum_bytes_billed=100000000)
        dry=c.query(sql,location='EU',job_config=bigquery.QueryJobConfig(dry_run=True,use_query_cache=False))
        if dry.total_bytes_processed>100000000:raise ValueError('Query exceeds100MB cap')
        j=c.query(sql,location='EU',job_config=config);rows=[dict(r) for r in j.result()];jobs.append({'id':j.job_id,'bytes_processed':j.total_bytes_processed,'bytes_billed':j.total_bytes_billed});return rows
    expected=json.loads(Path('docs/commerce/live-expectations.json').read_text(encoding='utf-8-sig'))['events']
    sources={'manual':('events','manual_vendor_file_export'),'native':('events_native','native_batch_export')}
    raw=[]
    for name in (sources if args.source=='combined' else [args.source]):
        table,method=sources[name]
        original='original_record' if name=='manual' else 'cast(null as string) as original_record'
        raw.extend(query(f"SELECT uuid, event, timestamp, properties, {original}, '{method}' AS delivery_source FROM `{PROJECT}.commerce_posthog_raw.{table}` WHERE timestamp >= '2026-11-03' AND timestamp < '2026-11-04'"))
    selected=[r for r in raw if r['properties'].get('test_run_id')==RUN]
    required_sources=[sources[n][1] for n in (sources if args.source=='combined' else [args.source])]
    matched=verify_source_deliveries(selected,expected,required_sources)
    native_model_verified=False
    if args.source in ('native','combined'):
        staged=query(f"SELECT vendor_uuid AS uuid,event_name AS event,vendor_timestamp AS timestamp,properties,delivery_source FROM `{PROJECT}.analytics_commerce_dev.stg_commerce_events` WHERE delivery_source='native_batch_export' AND test_run_id='{RUN}' AND is_valid")
        verify_deliveries(staged,expected)
        key=lambda r:(r['uuid'],r['properties']['event_id'])
        assert {key(r) for r in selected if r['delivery_source']=='native_batch_export'}=={key(r) for r in staged},'native staging UUID/ID gap; build with commerce_include_native=true'
        native_model_verified=True
    clean=query(f"SELECT count(*) AS events, countif(test_run_id='{RUN}') AS controlled FROM `{PROJECT}.analytics_commerce_dev.int_commerce_events_deduped`")[0]
    f=query(f"SELECT count(*) AS sessions,countif(viewed_product) AS viewed,countif(added_to_cart) AS added,countif(started_checkout) AS checkout,countif(purchased) AS purchased,sum(logical_purchases) AS logical_purchases FROM `{PROJECT}.analytics_commerce_dev.fct_commerce_session_funnel` WHERE test_run_id='{RUN}'")[0]
    assert [f[k] for k in ['sessions','viewed','added','checkout','purchased','logical_purchases']]==[10,10,6,3,1,1]
    assert clean['controlled']==20
    report={'method':args.source,'native_staging_verified':native_model_verified,'delivery_sources':sorted({r['delivery_source'] for r in raw}),'run':RUN,'raw_rows':len(raw),'raw_controlled_deliveries':len(selected),'distinct_vendor_uuids':len({r['uuid'] for r in raw}),'matched_event_ids':matched,'canonical_property_mismatches':0,'clean':clean,'funnel':f,'jobs':jobs}
    Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
