"""Credential-free parse checks for all four mutually exclusive model branches."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import yaml
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'dev':24,'ga4_dev':4,'commerce_dev':4,'ga4_commerce_dev':2}
def main():
    with TemporaryDirectory(prefix='commerce-isolation-') as tmp:
        p=Path(tmp)
        outputs={name:{'type':'bigquery','method':'oauth','project':'ci-placeholder-project','dataset':'ci_'+name,'location':'US' if name=='ga4_dev' else 'EU','threads':1} for name in EXPECTED}
        (p/'profiles.yml').write_text(yaml.safe_dump({'analytics':{'target':'dev','outputs':outputs}}))
        selections={}
        for target,count in EXPECTED.items():
            subprocess.run([sys.executable,'-c','from dbt.cli.main import cli; cli()','parse','--project-dir',str(ROOT),'--profiles-dir',str(p),'--target',target,'--target-path',str(p/target),'--log-path',str(p/'logs'),'--no-partial-parse','--quiet'],check=True,env={**os.environ,'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'})
            manifest=json.loads((p/target/'manifest.json').read_text())
            nodes=[n for n in manifest['nodes'].values() if n['resource_type']=='model' and n['config']['enabled']]
            assert len(nodes)==count,(target,len(nodes))
            for n in nodes:
                path=n['original_file_path'].replace(chr(92),'/')
                assert ('/commerce/' in path)==(target=='commerce_dev'),(target,path)
                assert ('/ga4/' in path)==(target=='ga4_dev'),(target,path)
                assert ('/ga4_commerce/' in path)==(target=='ga4_commerce_dev'),(target,path)
            sources={s['source_name'] for s in manifest['sources'].values()}
            assert ('ga4_commerce_raw' in sources)==(target=='ga4_commerce_dev'),(target,sources)
            if target=='ga4_commerce_dev':
                # The existing Olist source is always declared. Check actual model lineage.
                source=next(s for s in manifest['sources'].values() if s['source_name']=='ga4_commerce_raw')
                lineage={dependency for node in nodes for dependency in node['depends_on']['nodes']}
                assert lineage=={source['unique_id'],'model.analytics.stg_ga4_commerce_events'},lineage
                assert (source['database'],source['schema'],source['identifier'])==(
                    'mda-platform-2026','analytics_562157149','events_20261103'),source
            selections[target]=sorted(n['name'] for n in nodes)
        print(json.dumps({'model_counts':EXPECTED,'selections':selections}))
if __name__=='__main__':main()
