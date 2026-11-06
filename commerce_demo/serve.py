"""Loopback-only demo server. Default offline; explicit public capture config only."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from functools import partial
import argparse
import json
import os
import re
from threading import Lock

PREVIEW_DESTINATION = {
    'GTM_CONTAINER_ID': ('containerId', 'GTM-PHWDGH9B'),
    'GA4_MEASUREMENT_ID': ('measurementId', 'G-BSKG5RGN4Y'),
    'GA4_STREAM_ID': ('streamId', '16265125392'),
}
PREVIEW_RUN = re.compile(r'ga4-live-[0-9]{25}')
PREVIEW_SCENARIOS = frozenset([*(f'journey-{i:02}' for i in range(10)), 'remove-00'])


def reserve_preview_run(directory, run_id):
    if not PREVIEW_RUN.fullmatch(run_id):
        raise ValueError('Invalid Preview authorization run ID')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / run_id).mkdir()  # Exclusive and persistent across server restarts.


class PreviewClaims:
    def __init__(self, run_id):
        self.run_id = run_id
        self.used = set()
        self.lock = Lock()

    def claim(self, run_id, scenario):
        if run_id != self.run_id or not isinstance(scenario, str) or scenario not in PREVIEW_SCENARIOS:
            return False
        with self.lock:
            if scenario in self.used:
                return False
            self.used.add(scenario)
            return True


def configuration(authorized_run=None):
    if os.environ.get('COMMERCE_MODE') == 'ga4_gtm':
        if any(os.environ.get(env) != value for env, (_, value) in PREVIEW_DESTINATION.items()):
            raise ValueError('Google Preview requires the dedicated approved container and stream')
        if not isinstance(authorized_run, str) or not PREVIEW_RUN.fullmatch(authorized_run):
            raise ValueError('Google Preview requires explicit execution authorization for a new run ID')
        if os.environ.get('COMMERCE_DATALAYER'):
            raise ValueError('Use either local data-layer inspection or live Google Preview, not both')
        return {'mode': 'ga4_gtm', 'liveRunId': authorized_run,
                **{field: value for field, value in PREVIEW_DESTINATION.values()}}
    if authorized_run is not None:
        raise ValueError('Google Preview authorization requires explicit ga4_gtm mode')
    if os.environ.get('COMMERCE_MODE', 'offline') != 'posthog':
        return {'mode': 'offline', **({'dataLayer': 'local'} if os.environ.get('COMMERCE_DATALAYER') == 'local' else {})}
    host = os.environ.get('POSTHOG_CAPTURE_HOST', '')
    token = os.environ.get('POSTHOG_CAPTURE_TOKEN', '')
    if host not in ('https://eu.i.posthog.com', 'https://us.i.posthog.com') or not re.fullmatch(r'phc_[A-Za-z0-9_]+', token):
        raise ValueError('Cloud mode requires an approved capture host and public phc_ token; never a secret key')
    return {'mode': 'posthog', 'host': host, 'token': token, **({'dataLayer': 'local'} if os.environ.get('COMMERCE_DATALAYER') == 'local' else {})}

class Handler(SimpleHTTPRequestHandler):
    runtime = {'mode': 'offline'}
    preview_claims = None

    def do_POST(self):
        if self.path != '/preview-claim' or self.runtime['mode'] != 'ga4_gtm' or not self.preview_claims:
            self.send_error(404)
            return
        origin = f'http://127.0.0.1:{self.server.server_port}'
        if (self.headers.get('Origin') != origin or self.headers.get('Host') != origin.removeprefix('http://')
                or self.headers.get_content_type() != 'application/json'):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 512:
                raise ValueError
            self.connection.settimeout(3)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, TimeoutError):
            self.send_error(400)
            return
        if not self.preview_claims.claim(payload.get('run_id'), payload.get('scenario_id')):
            self.send_error(409)
            return
        self.send_response(204)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/runtime.mjs':
            body = ('export const runtime=' + json.dumps(self.runtime) + ';').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        elif path in ('/', '/index.html'):
            body = (Path(self.directory) / 'index.html').read_text(encoding='utf-8')
            if self.runtime['mode'] == 'posthog':
                body = body.replace("connect-src 'self'", "connect-src 'self' " + self.runtime['host'])
            if self.runtime['mode'] == 'ga4_gtm':
                body = body.replace("script-src 'self'", "script-src 'self' https://www.googletagmanager.com https://tagassistant.google.com")
                body = body.replace("connect-src 'self'", "connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://tagassistant.google.com")
                body = body.replace("img-src 'self' data:", "img-src 'self' data: https://*.google-analytics.com https://www.googletagmanager.com")
                body = body.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
                body = body.replace("form-action 'none'", "form-action 'none'; frame-src https://www.googletagmanager.com https://tagassistant.google.com")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            super().do_GET()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-ga4-preview', metavar='NEW_RUN_ID')
    args = parser.parse_args()
    Handler.runtime = configuration(args.authorize_ga4_preview)
    root = Path(__file__).resolve().parent
    with ThreadingHTTPServer(('127.0.0.1', 8765), partial(Handler, directory=str(root))) as server:
        if args.authorize_ga4_preview:
            reserve_preview_run(root.parent / 'docs' / 'commerce' / 'evidence' / 'ga4-preview-reservations',
                                args.authorize_ga4_preview)
            Handler.preview_claims = PreviewClaims(args.authorize_ga4_preview)
        print('Commerce demo: http://127.0.0.1:8765 — ' + Handler.runtime['mode'], flush=True)
        server.serve_forever()
