"""Validate bindings and scope of the existing Power BI report extension."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'dashboard'
PAGES = ROOT / 'Data Analytics.Report/definition/pages'
PAGE = PAGES / 'c057a430000000000001'
MODEL = ROOT / 'Data Analytics.SemanticModel/definition'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_commerce_page_visual_bindings():
    index = read(PAGES / 'pages.json')
    assert index['pageOrder'].count(PAGE.name) == 1
    assert read(PAGE / 'page.json')['displayName'] == 'Exploratory GA4 Commerce'
    types = []
    for file in (PAGE / 'visuals').glob('*/visual.json'):
        visual = read(file)
        assert visual['name'] == file.parent.name
        pos = visual['position']
        assert pos['x'] + pos['width'] <= 1920 and pos['y'] + pos['height'] <= 1080
        types.append(visual['visual']['visualType'])
        query = visual['visual'].get('query', {})
        for role in query.get('queryState', {}).values():
            for projection in role['projections']:
                kind, binding = next(iter(projection['field'].items()))
                entity = binding['Expression']['SourceRef']['Entity']
                assert entity.startswith('GA4 Commerce ')
                tmdl = (MODEL / 'tables' / f'{entity}.tmdl').read_text()
                assert f"ref table '{entity}'" in (MODEL / 'model.tmdl').read_text()
                prop = binding['Property']
                assert (f"measure '{prop}' =" if kind == 'Measure' else f'column {prop}\n') in tmdl
    assert sorted(types) == sorted(['cardVisual'] * 5 + ['tableEx'] * 2 + ['barChart'] + ['textbox'] * 2)


def test_imports_are_scoped_and_detail_is_bounded():
    tables = list((MODEL / 'tables').glob('GA4 Commerce *.tmdl'))
    assert len(tables) == 3
    for table in tables:
        content = table.read_text()
        assert 'mode: import' in content and 'Value.NativeQuery' in content
        relations = re.findall(r'\x60([^\x60]+)\x60', content)
        assert relations == [
            'mda-platform-2026.analytics_ga4_commerce_dev.' + (
                'stg_ga4_commerce_events' if table.stem.endswith('Events') else 'fct_ga4_commerce_session_funnel')]
    assert 'LIMIT 500' in (MODEL / 'tables/GA4 Commerce Sessions.tmdl').read_text()
    funnel = (MODEL / 'tables/GA4 Commerce Funnel.tmdl').read_text()
    assert 'SAFE_DIVIDE(s.reached,s.previous)' in funnel
    assert 'SAFE_DIVIDE(s.previous-s.reached,s.previous)' in funnel



def test_commerce_layout_and_integer_kpis():
    page = read(PAGE / 'page.json')
    visuals = [read(file) for file in (PAGE / 'visuals').glob('*/visual.json')]
    positions = []
    for entry in visuals:
        bounds = entry['position']
        x, y, width, height = (bounds[key] for key in ('x', 'y', 'width', 'height'))
        assert width > 0 and height > 0
        assert 0 <= x < x + width <= page['width']
        assert 0 <= y < y + height <= page['height']
        for left, top, right, bottom in positions:
            assert x + width <= left or right <= x or y + height <= top or bottom <= y
        positions.append((x, y, x + width, y + height))

        visual = entry['visual']
        if visual['visualType'] == 'cardVisual':
            values = visual['objects']['value']
            assert len(values) == 1
            properties = values[0]['properties']
            assert properties['labelDisplayUnits']['expr']['Literal']['Value'] == '1D'
            assert properties['labelPrecision']['expr']['Literal']['Value'] == '0D'

def test_portfolio_layout_and_native_navigation():
    from itertools import combinations

    historical = ROOT / 'ga4/GA4 Product Analytics.Report/definition/pages'
    for directory, count, navigator_count in ((PAGES, 8, 7), (historical, 3, 3)):
        order = read(directory / 'pages.json')['pageOrder']
        assert len(order) == len(set(order)) == count
        navigators = 0
        for page_id in order:
            page_dir = directory / page_id
            page = read(page_dir / 'page.json')
            assert page['name'] == page_id
            rectangles = []
            for path in (page_dir / 'visuals').glob('*/visual.json'):
                visual = read(path)
                assert visual['name'] == path.parent.name
                x, y, width, height = (
                    visual['position'][key] for key in ('x', 'y', 'width', 'height')
                )
                assert 0 <= x < x + width <= page['width']
                assert 0 <= y < y + height <= page['height']
                rectangles.append((x, y, x + width, y + height))
                if visual['visual']['visualType'] == 'pageNavigator':
                    navigators += 1
                    fills = visual['visual']['objects']['fill']
                    assert any(fill.get('selector', {}).get('id') == 'selected' for fill in fills)
            for (left, top, right, bottom), (x1, y1, x2, y2) in combinations(rectangles, 2):
                assert right <= x1 or x2 <= left or bottom <= y1 or y2 <= top
        assert navigators == navigator_count

