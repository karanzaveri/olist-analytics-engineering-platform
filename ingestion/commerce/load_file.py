"""Manual supported PostHog file-export import; never accepts browser fixtures."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery
PROJECT = 'mda-platform-2026'
TABLE = PROJECT + '.commerce_posthog_raw.events'

def prepare(path):
    payload = Path(path).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for line in payload.decode('utf-8-sig').splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        for key in ['uuid', 'event', 'distinct_id', 'timestamp', 'properties']:
            if key not in e:
                raise ValueError('Not a vendor events export: missing ' + key)
        if not isinstance(e['properties'], dict):
            raise ValueError('Expected original JSON object properties')
        row = {k: e.get(k) for k in ['uuid', 'event', 'distinct_id', 'timestamp', 'person_id']}
        row.update(properties=e['properties'], person_properties=e.get('person_properties', {}), bq_ingested_timestamp=now, original_record=line, import_id=digest, import_method='posthog_file_download', vendor_created_at=e.get('created_at'), vendor_inserted_at=e.get('_inserted_at'))
        rows.append(row)
    if not rows:
        raise ValueError('Empty vendor export')
    return rows, digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('file');args=parser.parse_args()
    rows,digest=prepare(args.file)
    c=bigquery.Client(project=PROJECT)
    if c.get_dataset(PROJECT+'.commerce_posthog_raw').location!='EU':
        raise ValueError('EU raw dataset required')
    schema=[bigquery.SchemaField(k,t) for k,t in [('uuid','STRING'),('event','STRING'),('distinct_id','STRING'),('timestamp','TIMESTAMP'),('person_id','STRING'),('properties','JSON'),('person_properties','JSON'),('bq_ingested_timestamp','TIMESTAMP'),('original_record','STRING'),('import_id','STRING'),('import_method','STRING'),('vendor_created_at','TIMESTAMP'),('vendor_inserted_at','TIMESTAMP'),('elements','STRING'),('set','JSON'),('set_once','JSON'),('team_id','INT64'),('ip','STRING'),('site_url','STRING')]]
    job=c.load_table_from_json(rows,TABLE,location='EU',job_config=bigquery.LoadJobConfig(schema=schema,write_disposition='WRITE_APPEND',time_partitioning=bigquery.TimePartitioning(field='timestamp')))
    job.result()
    print(json.dumps({'method':'manual_posthog_file_export','file_sha256':digest,'rows_loaded':len(rows),'job_id':job.job_id,'table':TABLE}))
if __name__=='__main__':
    main()
