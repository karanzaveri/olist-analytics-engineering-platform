from pathlib import Path
import json
import pytest
from ingestion.commerce.load_file import prepare

def test_manual_import_rejects_local_fixture(tmp_path):
    path=tmp_path/'local.jsonl';path.write_text(json.dumps({'event_id':'local','event_name':'product_viewed'}))
    with pytest.raises(ValueError,match='vendor'):
        prepare(path)

def test_manual_import_preserves_vendor_line(tmp_path):
    # Test-only minimal envelope; never warehouse source evidence.
    line=json.dumps({'uuid':'vendor-id','event':'test','distinct_id':'visitor','timestamp':'2026-11-03T00:00:00Z','properties':{'event_id':'canonical'}})
    path=tmp_path/'vendor.jsonl';path.write_text(line)
    rows,digest=prepare(path)
    assert rows[0]['original_record']==line
    assert rows[0]['uuid']=='vendor-id'
    assert rows[0]['properties']=={'event_id':'canonical'}
    assert prepare(path)[1]==digest
