import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('run_browser', Path(__file__).with_name('run-olist-browser.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_only_approved_tasks_and_distinct_modes(self):
        agent = Path('external-worker')
        inspector = launcher.worker_command(agent, 'inspector')
        journey = launcher.worker_command(agent, 'journey')
        self.assertIn('-CheckReadiness', inspector)
        self.assertNotIn('--deterministic', inspector)
        self.assertIn('--deterministic', journey)
        self.assertNotIn('-CheckReadiness', journey)
        with self.assertRaises(KeyError):
            launcher.worker_command(agent, 'purchase')

    def test_offline_environment_overrides_inherited_tracking(self):
        with patch.dict(os.environ, {'COMMERCE_MODE': 'ga4_gtm', 'COMMERCE_DATALAYER': 'local'}):
            env = launcher.offline_environment()
        self.assertEqual(env['COMMERCE_MODE'], 'offline')
        self.assertNotIn('COMMERCE_DATALAYER', env)

    def test_report_separates_browser_status_and_model_counts(self):
        report = {'status': 'passed', 'execution_mode': 'deterministic',
                  'requests': [], 'isolation_verified': None, 'evidence': ['page_snapshot.json']}
        result = launcher.summarize(report, 'deterministic', Path('report.json'), 0)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['model_requests'], 0)
        report['requests'].append({'status': 200})
        with self.assertRaises(ValueError):
            launcher.summarize(report, 'deterministic', Path('report.json'), 0)

    def test_passed_agentic_ui_cannot_substitute_for_model_route(self):
        report = {'status': 'passed', 'execution_mode': 'agentic',
                  'requests': [], 'isolation_verified': False, 'evidence': []}
        result = launcher.summarize(report, 'agentic', Path('report.json'), 0)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['worker_status'], 'passed')
