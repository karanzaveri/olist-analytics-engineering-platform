"""Run the actual funnel SQL on normalized, synthetic staging rows."""
from pathlib import Path
import sqlite3

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1] / 'analytics'
MODELS = ROOT / 'models' / 'ga4_commerce'


def run(rows):
    env = Environment()
    macro = env.from_string((ROOT / 'macros' / 'commerce_after.sql').read_text()).module
    query = env.from_string((MODELS / 'fct_ga4_commerce_session_funnel.sql').read_text()).render(
        ref=lambda name: name, commerce_after=macro.commerce_after)
    with sqlite3.connect(':memory:') as db:
        db.create_function('strpos', 2, lambda text, part: text.find(part) + 1)
        db.execute('''create table stg_ga4_commerce_events (
            event_id, environment, activity_origin, test_run_id, app_anonymous_id,
            app_session_id, scenario_id, session_key, event_name, occurred_at integer,
            occurred_at_us integer, session_sequence integer, product_id, product_tokens,
            items_json, checkout_id, order_id, payload_hash, is_valid integer,
            native_event_timestamp integer, source_shard)''')
        db.executemany('insert into stg_ga4_commerce_events values (' + ','.join('?' * 21) + ')', rows)
        db.row_factory = sqlite3.Row
        return {row['session_key']: dict(row) for row in db.execute(query)}


def event(session, seq, name, *, time=0, product='a', checkout=None, order=None,
          event_id=None, payload=None, valid=1):
    key = event_id or f'{session}-{seq}'
    return (key, 'local_demo', 'synthetic_test', 'offline-oracle', f'user-{session}', session,
            session, session, name, time, time, seq, product, f'|{product}|',
            f'items-{product}', checkout, order, payload or key, valid, time, '20261103')


def chain(session, length, **options):
    return [event(session, i, name, checkout='checkout' if i >= 3 else None,
                  order=options.get('order', 'order') if i == 4 else None)
            for i, name in enumerate(('product_viewed', 'product_added_to_cart',
                                      'checkout_started', 'purchase_completed')[:length], 1)]


def test_independent_offline_oracle_and_exact_replay():
    lengths = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
    rows = [row for i, length in enumerate(lengths) for row in chain(str(i), length)]
    results = run(rows)
    assert len(rows) == 20 and len(results) == 10
    assert [sum(r[k] for r in results.values()) for k in
            ('viewed_product', 'added_to_cart', 'started_checkout', 'purchased', 'logical_purchases')] == [10, 6, 3, 1, 1]
    assert run(rows + rows) == results


def test_strict_order_window_continuity_and_removal():
    rows = chain('tie', 1) + [event('tie', 1, 'product_added_to_cart', event_id='tie-add')]
    rows += chain('late', 1) + [event('late', 2, 'product_added_to_cart', time=1_800_000_001)]
    rows += chain('edge', 1) + [event('edge', 2, 'product_added_to_cart', time=1_800_000_000)]
    rows += chain('wrong-product', 1) + [event('wrong-product', 2, 'product_added_to_cart', product='b')]
    rows += chain('checkout-product', 2) + [
        event('checkout-product', 3, 'checkout_started', product='b', checkout='checkout')]
    rows += chain('late-second-view', 1) + [
        event('late-second-view', 2, 'product_viewed', time=1_800_000_001),
        event('late-second-view', 3, 'product_added_to_cart', time=1_800_000_002)]
    rows += chain('remove', 2) + [event('remove', 3, 'product_removed_from_cart')]
    rows += chain('wrong-checkout', 3) + [event('wrong-checkout', 4, 'purchase_completed', checkout='other', order='different')]
    rows += chain('wrong-items', 3) + [event('wrong-items', 4, 'purchase_completed', product='b', checkout='checkout', order='items')]
    actual = run(rows)
    assert {k: v['stage_reached'] for k, v in actual.items()} == {
        'tie': 1, 'late': 1, 'edge': 2, 'wrong-product': 1, 'remove': 2,
        'wrong-checkout': 3, 'wrong-items': 3, 'checkout-product': 2, 'late-second-view': 1}
    assert actual['remove']['removal_events'] == 1


def test_event_conflicts_and_purchase_uniqueness():
    original = chain('main', 4)
    retry = event('main', 5, 'purchase_completed', checkout='checkout', order='order')
    assert run(original + [retry])['main']['logical_purchases'] == 1
    conflicting = chain('other', 4)
    actual = run(original + conflicting)
    assert actual['main']['logical_purchases'] == actual['other']['logical_purchases'] == 0
    conflict = event('main', 2, 'product_added_to_cart', payload='different')
    assert run(original + [conflict])['main']['stage_reached'] == 1
    invalid = event('main', 2, 'product_added_to_cart', valid=0)
    assert run(original + [invalid])['main']['stage_reached'] == 1
