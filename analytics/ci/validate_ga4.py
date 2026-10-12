"""Offline dbt parsing and target-isolation checks.

Uses a temporary placeholder profile, never the developer's profiles.yml.
No authentication, warehouse models, data tests, or schema inspection is needed.
Parsing checks Jinja/dependencies, not warehouse SQL validity or test outcomes.
Run from any directory with the repository's dbt dependencies installed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT = Path(__file__).resolve().parents[1]
GA4_MODELS = {
    'stg_ga4_events',
    'int_ga4_sessions',
    'int_ga4_session_attribution',
    'fct_ga4_session_funnel',
}


def main():
    os.environ['DBT_SEND_ANONYMOUS_USAGE_STATS'] = 'false'
    with TemporaryDirectory(prefix='ga4-dbt-ci-') as temporary:
        workspace = Path(temporary)
        (workspace / 'profiles.yml').write_text(
            'analytics:\n'
            '  target: dev\n'
            '  outputs:\n'
            + ''.join(
                f'    {target}:\n'
                '      type: bigquery\n'
                '      method: oauth\n'
                '      project: ci-placeholder-project\n'
                f'      dataset: ci_{target}\n'
                f'      location: {location}\n'
                '      threads: 1\n'
                for target, location in [('dev', 'EU'), ('ga4_dev', 'US')]
            ),
            encoding='utf-8',
        )

        def invoke(command, target, *options):
            arguments = [
                command, '--project-dir', str(PROJECT),
                '--profiles-dir', str(workspace), '--target', target,
                '--target-path', str(workspace / target),
                '--log-path', str(workspace / 'logs'),
                '--no-partial-parse', *options,
            ]
            # Child processes close dbt's log handlers before temporary cleanup.
            subprocess.run(
                [sys.executable, '-c', 'from dbt.cli.main import cli; cli()', *arguments],
                check=True,
            )

        manifests = {}
        for target in ['dev', 'ga4_dev']:
            invoke('parse', target)
            manifests[target] = json.loads(
                (workspace / target / 'manifest.json').read_text(encoding='utf-8')
            )

        enabled = {
            target: {
                node['name'] for node in manifest['nodes'].values()
                if node['resource_type'] == 'model' and node['config']['enabled']
            }
            for target, manifest in manifests.items()
        }
        if len(enabled['dev']) != 23 or enabled['dev'] & GA4_MODELS:
            raise AssertionError(f'Unexpected dev selection: {enabled["dev"]}')
        if enabled['ga4_dev'] != GA4_MODELS:
            raise AssertionError(f'Unexpected ga4_dev selection: {enabled["ga4_dev"]}')
        for target, other in [('dev', 'ga4_dev'), ('ga4_dev', 'dev')]:
            disabled = {
                node['name'] for nodes in manifests[target]['disabled'].values()
                for node in nodes if node['resource_type'] == 'model'
            }
            if not enabled[other] <= disabled:
                raise AssertionError(f'Model isolation failed for {target}')

        for node in manifests['dev']['nodes'].values():
            if node['resource_type'] == 'test' and node['config']['enabled']:
                if any(f'model.analytics.{name}' in node['depends_on']['nodes']
                       for name in GA4_MODELS):
                    raise AssertionError(f'GA4 test enabled under dev: {node["name"]}')
        tests = [node for node in manifests['ga4_dev']['nodes'].values()
                 if node['resource_type'] == 'test' and node['config']['enabled']]
        if len(tests) != 67:
            raise AssertionError(f'Expected 67 GA4 test definitions, got {len(tests)}')

        analysis_id = 'analysis.analytics.session_funnel_analysis'
        if analysis_id in manifests['dev']['nodes']:
            raise AssertionError('GA4 analysis must be disabled under dev')
        analysis = manifests['ga4_dev']['nodes'][analysis_id]
        if analysis['depends_on']['nodes'] != ['model.analytics.fct_ga4_session_funnel']:
            raise AssertionError('Read-only analysis must depend only on the funnel mart')

        print('Offline checks passed: dev=23 Olist, ga4_dev=4 GA4; 67 test definitions parsed.')
        print('No warehouse SQL or data tests executed; warehouse validity is not checked here.')


if __name__ == '__main__':
    main()
