from commerce_demo.serve import configuration

def test_data_layer_is_opt_in_and_does_not_enable_cloud(monkeypatch):
    monkeypatch.delenv('COMMERCE_MODE',raising=False)
    monkeypatch.delenv('COMMERCE_DATALAYER',raising=False)
    assert configuration()=={'mode':'offline'}
    monkeypatch.setenv('COMMERCE_DATALAYER','local')
    assert configuration()=={'mode':'offline','dataLayer':'local'}

def test_google_preview_mode_requires_exact_public_destination(monkeypatch):
    import pytest
    monkeypatch.setenv('COMMERCE_MODE','ga4_gtm')
    monkeypatch.delenv('GTM_CONTAINER_ID',raising=False)
    monkeypatch.delenv('GA4_MEASUREMENT_ID',raising=False)
    with pytest.raises(ValueError,match='dedicated'):
        configuration()
    monkeypatch.setenv('GTM_CONTAINER_ID','GTM-PHWDGH9B')
    monkeypatch.setenv('GA4_MEASUREMENT_ID','G-BSKG5RGN4Y')
    monkeypatch.setenv('GA4_STREAM_ID','16265125392')
    with pytest.raises(ValueError,match='authorization'):
        configuration()
    run='ga4-live-1793890387648262484762878'
    assert configuration(run)=={'mode':'ga4_gtm','containerId':'GTM-PHWDGH9B',
                                'measurementId':'G-BSKG5RGN4Y','streamId':'16265125392','liveRunId':run}
