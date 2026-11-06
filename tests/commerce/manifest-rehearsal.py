"""Offline-only source manifest rehearsal using the existing local Chromium."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
from threading import Thread
from uuid import UUID

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = '00066f42aeeb9f3007548bb9d3f33c38'
VIEW, ADD, CHECKOUT, PURCHASE, REMOVE = (
    'product_viewed', 'product_added_to_cart', 'checkout_started',
    'purchase_completed', 'product_removed_from_cart',
)
MATRIX = {
    **{f'journey-{i:02}': [VIEW] for i in range(4)},
    **{f'journey-{i:02}': [VIEW, ADD] for i in range(4, 7)},
    **{f'journey-{i:02}': [VIEW, ADD, CHECKOUT] for i in range(7, 9)},
    'journey-09': [VIEW, ADD, CHECKOUT, PURCHASE],
    'remove-00': [VIEW, ADD, REMOVE],
}


def digest(data):
    return sha256(data).hexdigest()


def lines(data):
    return [json.loads(line) for line in data.splitlines()]


def inspect(page, expected_count, orders=0):
    page.get_by_role('link', name='Event inspector', exact=True).click()
    expect(page.locator('#counts')).to_have_text(
        f'{expected_count} recorded events; {orders} simulated orders.')
    return json.loads(page.locator('#events').inner_text())


def download(page):
    with page.expect_download() as result:
        page.get_by_role('button', name='Download source manifest', exact=True).click()
    return result.value.path().read_bytes()


def start(page, url):
    page.goto(url)
    expect(page.locator('#products')).to_be_visible()
    expect(page.locator('#google-grant')).to_be_hidden()
    expect(page.locator('#cloud-grant')).to_be_hidden()
    page.locator('#grant').click()
    expect(page.locator('#consent-status')).to_contain_text('Local recording allowed')


def view(page):
    page.locator(f'a[href="#product/{PRODUCT}"]').click()
    expect(page.locator('#add')).to_be_enabled()


def exercise(page, expected):
    view(page)
    if ADD in expected:
        page.locator('#add').click()
        expect(page.locator('#add')).to_be_disabled()
        page.get_by_role('link', name='Cart', exact=True).click()
        expect(page.locator(f'[data-remove="{PRODUCT}"]')).to_have_count(1)
    if CHECKOUT in expected:
        page.locator('#checkout').click()
        expect(page.get_by_role('heading', name='Review simulated purchase')).to_be_visible()
    if PURCHASE in expected:
        page.locator('#complete').click()
        expect(page.get_by_role('heading', name='Simulated purchase complete')).to_be_visible()
    if REMOVE in expected:
        page.locator(f'[data-remove="{PRODUCT}"]').click()
        expect(page.get_by_text('Your cart is empty.')).to_be_visible()


def verify_records(records, source, run_id, scenario, expected):
    events = [record['event'] for record in records]
    assert events == source['events'], scenario
    assert [event['event_name'] for event in events] == expected, scenario
    for sequence, record in enumerate(records, 1):
        event = record['event']
        assert record['manifest_version'] == 1
        assert record['capture_stage'] == 'source_committed_before_dispatch'
        assert UUID(event['event_id']).version == 4
        assert datetime.fromisoformat(event['occurred_at']).utcoffset() == timezone.utc.utcoffset(None)
        assert event['test_run_id'] == run_id and event['scenario_id'] == scenario
        assert event['session_sequence'] == sequence
        assert event['simulation'] is True and event['consent_state'] == 'granted'
        assert event['activity_origin'] == 'synthetic_test' and event['environment'] == 'local_demo'
        assert event['currency'] == 'BRL' and event['value_minor'] == 2500
        assert event['items'] == [dict(product_id=PRODUCT, category='perfumaria',
                                     demo_title='Perfumaria / 00066f', price_minor=2500, quantity=1)]
        assert record['expected_transaction_id'] == event.get('order_id')
        assert ('checkout_id' in event) == (event['event_name'] in (CHECKOUT, PURCHASE))
        assert ('order_id' in event) == (event['event_name'] == PURCHASE)
    assert len({event['session_id'] for event in events}) == 1
    assert len({event['anonymous_id'] for event in events}) == 1
    assert [row['event_id'] for row in source['localDataLayer'] if row.get('event')] == [
        event['event_id'] for event in events]
    assert not source['cloudTransport'] and not source['googlePreview'] and source['cloudPending'] == 0
    if PURCHASE in expected:
        assert events[-2]['checkout_id'] == events[-1]['checkout_id']
        assert events[-2]['items'] == events[-1]['items'] and events[-1]['order_id'].startswith('demo_')
    return events


def rehearsal(browser, base, run_id):
    requests, blocked = Counter(), []
    combined, sealed, scenario_hashes = [], [], {}

    def context():
        ctx = browser.new_context(accept_downloads=True, service_workers='block')
        ctx.set_default_timeout(5000)
        ctx.set_default_navigation_timeout(5000)

        def route(request_route):
            url = request_route.request.url
            if url.startswith(base + '/'):
                requests[url.split('?', 1)[0].removeprefix(base)] += 1
                request_route.continue_()
            else:
                blocked.append(url)
                request_route.abort()

        ctx.route('**/*', route)
        return ctx

    def url(scenario):
        return f'{base}/?source_manifest=1&test_run_id={run_id}&scenario_id={scenario}#catalog'

    for scenario, expected in MATRIX.items():
        with context() as ctx:
            page = ctx.new_page()
            start(page, url(scenario))
            exercise(page, expected)
            source = inspect(page, len(expected), int(PURCHASE in expected))
            data = download(page)
            assert data == download(page), scenario
            records = lines(data)
            combined.extend(verify_records(records, source, run_id, scenario, expected))
            sealed.append(data)
            scenario_hashes[scenario] = digest(data)
            if scenario == 'journey-09':
                page.locator('#retry').click()
                expect(page.locator('#events')).to_contain_text('localDeliveryAttempts')
                page.wait_for_function("JSON.parse(document.querySelector('#events').textContent).localDeliveryAttempts.length === 1")
                assert download(page) == data
            if scenario == 'remove-00':
                # Withdraw from an unarmed tab sharing the same origin and database.
                other = ctx.new_page()
                other.goto(base + '/#inspect')
                expect(other.locator('#counts')).to_contain_text('3 recorded events')
                other.locator('#deny').click()
                expect(page.locator('#counts')).to_have_text('0 recorded events; 0 simulated orders.')
                cleared = json.loads(page.locator('#events').inner_text())
                assert all(not cleared[key] for key in ('events', 'localDeliveryAttempts', 'localDataLayer',
                                                        'cloudPending', 'cloudTransport', 'googlePreview'))
                expect(page.get_by_role('button', name='Download source manifest')).to_be_disabled()
                # Regrant only local recording to verify purge independently of the disabled control.
                page.locator('#grant').click()
                expect(page.get_by_role('button', name='Download source manifest')).to_be_enabled()
                assert download(page) == b''

    with context() as ctx:
        page = ctx.new_page()
        start(page, url('failure-00'))
        view(page)
        original = page.evaluate('''() => new Promise((resolve, reject) => {
            const request = indexedDB.open('olist-commerce-offline', 1);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                const db = request.result;
                const t = db.transaction('state', 'readonly');
                const r = t.objectStore('state').get('demo');
                t.oncomplete = () => { db.close(); resolve(r.result.events[0]); };
                t.onabort = () => { db.close(); reject(t.error); };
            };
        })''')
        # Inject only a UUID collision; exercise the actual Add button and IndexedDB transaction.
        page.evaluate('(id) => { crypto.randomUUID = () => id; }', original['event_id'])
        page.locator('#add').click()
        expect(page.locator('#error')).to_contain_text('Source manifest transaction failed')
        page.locator('#add').click()
        expect(page.locator('#error')).to_contain_text('Source manifest transaction failed')
        page.get_by_role('link', name='Cart', exact=True).click()
        expect(page.get_by_text('Your cart is empty.')).to_be_visible()
        after = inspect(page, 1)
        assert after['events'] == [original]
        assert [row['event_id'] for row in after['localDataLayer'] if row.get('event')] == [original['event_id']]
        assert [row['event'] for row in lines(download(page))] == [original]

    with context() as ctx:
        page = ctx.new_page()
        start(page, base + '/?source_manifest=1#catalog')
        view(page)
        inspect(page, 1)
        expect(page.get_by_role('button', name='Download source manifest')).to_have_count(0)

    counts = Counter(event['event_name'] for event in combined)
    benchmark = [event for event in combined if event['scenario_id'].startswith('journey-')]
    stages = [len({event['session_id'] for event in benchmark if event['event_name'] == name})
              for name in (VIEW, ADD, CHECKOUT, PURCHASE)]
    assert stages == [10, 6, 3, 1]
    assert counts == {VIEW: 11, ADD: 7, REMOVE: 1, CHECKOUT: 3, PURCHASE: 1}
    assert len(combined) == len({event['event_id'] for event in combined}) == 23
    assert len({event['session_id'] for event in combined}) == 11
    assert len({event['anonymous_id'] for event in combined}) == 11
    assert not blocked, blocked
    assert not {'/google-preview.mjs', '/posthog.mjs'} & requests.keys()
    return combined, b''.join(sealed), dict(stages=stages, counts=dict(counts), scenario_sha256=scenario_hashes,
                          localhost_requests=dict(requests), blocked_external_attempts=blocked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('commerce_server', ROOT / 'commerce_demo' / 'serve.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.Handler.runtime = {'mode': 'offline', 'dataLayer': 'local'}
    handler = partial(module.Handler, directory=str(ROOT / 'commerce_demo'))
    stamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    run_id = f'ga4-rehearsal-{stamp}{secrets.randbelow(10**12):012d}'
    evidence = ROOT / 'docs' / 'commerce' / 'evidence' / run_id
    evidence.mkdir()
    plan = dict(run_id=run_id, mode='offline', scenarios=MATRIX, product_id=PRODUCT,
                value_minor=2500, currency='BRL', expected_funnel=[10, 6, 3, 1],
                expected_benchmark_events=20, expected_total_events=23, expected_sessions=11,
                started_at=datetime.now(timezone.utc).isoformat(),
                repository_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256={name: digest((ROOT / name).read_bytes()) for name in (
                    'commerce_demo/app.mjs', 'commerce_demo/contract.mjs',
                    'commerce_demo/catalog.mjs', 'commerce_demo/ga4.mjs')})
    (evidence / 'run-plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=str(args.chromium), headless=True)
                try:
                    events, payload, checks = rehearsal(browser, f'http://127.0.0.1:{server.server_port}', run_id)
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join()
    (evidence / 'source-events.ndjson').write_bytes(payload)
    index = dict(checks, source_sha256=digest(payload), records=len(events), sessions=11,
                 run_plan_sha256=digest((evidence / 'run-plan.json').read_bytes()),
                 completed_at=datetime.now(timezone.utc).isoformat(), vendor_dispatch='not_attempted',
                 warehouse='not_checked', local_retry_preserved_manifest=True,
                 withdrawal_cleared_journal=True, journal_collision_rolled_back=True)
    (evidence / 'evidence-index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(evidence=str(evidence), **index), indent=2))


if __name__ == '__main__':
    main()
