from copy import deepcopy
import json
import pytest
from ingestion.commerce.reconcile import verify_deliveries

EXPECTED={'event_id':'canonical','event_name':'product_viewed','occurred_at':'2026-11-03T17:38:00.000Z','test_run_id':'commerce-live-1793727480072'}
def row(source):
    from datetime import datetime, timezone
    result={'uuid':'vendor-uuid','event':'product_viewed','timestamp':datetime(2026,11,3,17,38,tzinfo=timezone.utc),'properties':deepcopy(EXPECTED),'delivery_source':source}
    if source=='manual_vendor_file_export':
        result['original_record']=json.dumps({'uuid':'vendor-uuid','properties':EXPECTED})
    return result

def test_manual_and_native_keep_distinct_lineage():
    assert verify_deliveries([row('manual_vendor_file_export'),row('native_batch_export')],[EXPECTED])==1
    missing=row('manual_vendor_file_export');missing['original_record']=None
    with pytest.raises(AssertionError):verify_deliveries([missing],[EXPECTED])

def test_conflicting_earlier_duplicate_cannot_hide():
    bad=row('native_batch_export');bad['properties']['event_name']='purchase_completed'
    with pytest.raises(AssertionError):verify_deliveries([bad,row('native_batch_export')],[EXPECTED])


def test_native_cannot_be_satisfied_by_manual_only_evidence():
    from ingestion.commerce.reconcile import verify_source_deliveries
    with pytest.raises(AssertionError,match='event ID gap'):
        verify_source_deliveries([row('manual_vendor_file_export')],[EXPECTED],['manual_vendor_file_export','native_batch_export'])
    assert verify_source_deliveries([row('manual_vendor_file_export'),row('native_batch_export')],[EXPECTED],['manual_vendor_file_export','native_batch_export'])==1
