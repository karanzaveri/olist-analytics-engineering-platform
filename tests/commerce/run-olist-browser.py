"""Launch an approved offline Olist task with an existing standalone worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from uuid import uuid4


REPO = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:8765'
READY = 'FreeLLMAPI readiness: HTTP 200, configured alias ready'
TASKS = {
    'inspector': ('olist-storefront-offline-inspector', 'agentic',
                  'a0ac3edd4b70ef0d10b7a16862391eb9080af47cc9342d6f59d6b3135a7e1172'),
    'journey': ('olist-storefront-journey', 'deterministic',
                '7bd085ef2a2d60c8266fe365b9f1c5fe2427095068ee6ff28df5e8d2b31b81ea'),
}


def worker_command(agent, check):
    task_id, mode, _ = TASKS[check]
    task = agent / 'tasks' / f'{task_id}.json'
    if mode == 'agentic':
        return ['pwsh', '-NoProfile', '-File', str(agent / 'run.ps1'),
                '-Task', str(task), '-Headless', '-CheckReadiness']
    return [str(agent / '.venv' / 'Scripts' / 'python.exe'), str(agent / 'worker.py'),
            '--task', str(task), '--headless', '--deterministic']


def offline_environment():
    env = {**os.environ, 'COMMERCE_MODE': 'offline', 'PYTHONDONTWRITEBYTECODE': '1'}
    env.pop('COMMERCE_DATALAYER', None)
    return env


def check_port():
    with socket.socket() as listener:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', 8765))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def verify_offline(server):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + 5
    while server.poll() is None:
        try:
            with opener.open(BASE + '/runtime.mjs', timeout=1) as response:
                runtime = response.read().decode()
            break
        except URLError:
            if time.monotonic() >= deadline:
                raise RuntimeError('Offline server startup timed out') from None
            time.sleep(0.1)
    else:
        raise RuntimeError('Offline server exited during startup')
    if runtime != 'export const runtime={"mode": "offline"};':
        raise RuntimeError('Storefront runtime is not explicitly offline')
    with opener.open(BASE + '/', timeout=2) as response:
        html = response.read()
    with opener.open(BASE + '/app.mjs', timeout=2) as response:
        app = response.read()
    if (server.poll() is not None or b"connect-src 'self';" not in html or b"script-src 'self';" not in html
            or app != (REPO / 'commerce_demo' / 'app.mjs').read_bytes()):
        raise RuntimeError('Offline storefront identity or policy check failed')


def report_path(output, report_root, task_id):
    for line in reversed(output.splitlines()):
        if line.lstrip().startswith('"report":'):
            path = Path(json.loads('{' + line.strip().rstrip(',') + '}')['report']).resolve()
            if (path.parent.parent != report_root.resolve() or path.name != 'report.json'
                    or not path.parent.name.startswith(task_id + '-')):
                raise ValueError('Worker returned an unexpected evidence path')
            return path
    return None


def summarize(report, mode, path, exit_code):
    if report['execution_mode'] != mode:
        raise ValueError('Worker returned an unexpected execution mode')
    requests = report['requests']
    if mode == 'deterministic' and requests:
        raise ValueError('Deterministic execution attempted a model request')
    status = report['status']
    if status == 'passed' and mode == 'agentic' and not report['isolation_verified']:
        status = 'partial'
    if status == 'passed' and exit_code:
        status = 'failed'
    return {
        'status': status, 'worker_status': report['status'], 'worker_exit_code': exit_code,
        'execution_mode': mode, 'model_requests': len(requests),
        'successful_model_requests': sum(r.get('status') == 200 for r in requests),
        'successful_model_routes': sorted({r['routed_via'] for r in requests
                                           if r.get('status') == 200 and r.get('routed_via')}),
        'isolation_verified': report['isolation_verified'], 'assertions': report.get('final_report'),
        'worker_report': str(path), 'evidence': [str(path.parent / name) for name in report['evidence']],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=TASKS)
    parser.add_argument('--worker-root', required=True, type=Path)
    args = parser.parse_args()
    agent = args.worker_root.resolve()
    task_id, mode, expected_hash = TASKS[args.check]
    command = worker_command(agent, args.check)
    task = agent / 'tasks' / f'{task_id}.json'
    executable = agent / '.venv' / 'Scripts' / 'python.exe'
    if not executable.is_file() or not (agent / 'worker.py').is_file() or not task.is_file():
        parser.error('Supply the existing standalone worker directory and installed runtime')
    if hashlib.sha256(task.read_bytes()).hexdigest() != expected_hash:
        parser.error('Approved task changed. Review its scope before updating the launcher')
    if mode == 'agentic' and (not (agent / 'run.ps1').is_file() or not shutil.which('pwsh')):
        parser.error('The agentic inspector requires PowerShell and the standalone launcher')

    summary = {'check': args.check, 'execution_mode': mode, 'status': 'failed',
               'model_requests': None, 'gateway_readiness': 'not_run' if mode == 'agentic' else 'not_applicable'}
    server = None
    try:
        check_port()
        server = subprocess.Popen([sys.executable, '-u', 'commerce_demo/serve.py'], cwd=REPO,
                                  env=offline_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        verify_offline(server)
        summary['offline_verified'] = True
        result = subprocess.run(command, cwd=agent, env=offline_environment(),
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        path = report_path(result.stdout, agent / 'reports', task_id)
        if mode == 'agentic':
            summary['gateway_readiness'] = 'ready' if READY in result.stdout.splitlines() else 'unconfirmed'
        if path:
            summary.update(summarize(json.loads(path.read_text(encoding='utf-8')), mode, path, result.returncode))
            if mode == 'agentic' and summary['gateway_readiness'] != 'ready':
                summary['status'] = 'failed'
        elif 'FreeLLMAPI readiness failed. Worker launch skipped.' in result.stderr:
            summary.update(status='blocked', gateway_readiness='failed', model_requests=0,
                           successful_model_requests=0, error='Gateway readiness failed before worker launch')
        else:
            summary['error'] = 'Standalone worker did not produce an evidence report'
    except (OSError, RuntimeError, ValueError) as exc:
        summary.update(status='failed', error=str(exc))
    finally:
        if server is not None:
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=5)
            summary['pilot_server_stopped'] = server.poll() is not None

    output_dir = agent / 'reports' / 'olist-launcher'
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f'{args.check}-{uuid4().hex[:8]}.json'
    path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**summary, 'summary': str(path)}, indent=2))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
