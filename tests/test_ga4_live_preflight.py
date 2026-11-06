import pytest

from commerce_demo.serve import configuration, reserve_preview_run, PreviewClaims


RUN = 'ga4-live-1793890387648262484762878'


@pytest.fixture
def live(monkeypatch):
    for key, value in {
        'COMMERCE_MODE': 'ga4_gtm',
        'GTM_CONTAINER_ID': 'GTM-PHWDGH9B',
        'GA4_MEASUREMENT_ID': 'G-BSKG5RGN4Y',
        'GA4_STREAM_ID': '16265125392',
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('COMMERCE_DATALAYER', raising=False)


def test_authorization_must_be_explicit_and_synthetic(live):
    for value in (None, 'ga4-live-2026110302', 'ga4-rehearsal-1793890387648262484762878'):
        with pytest.raises(ValueError, match='authorization'):
            configuration(value)
    assert configuration(RUN)['liveRunId'] == RUN


@pytest.mark.parametrize('field', ['GTM_CONTAINER_ID', 'GA4_MEASUREMENT_ID', 'GA4_STREAM_ID'])
def test_wrong_destination_rejected(live, monkeypatch, field):
    monkeypatch.setenv(field, 'wrong')
    with pytest.raises(ValueError, match='dedicated'):
        configuration(RUN)


def test_run_reservation_cannot_be_reused(tmp_path):
    reserve_preview_run(tmp_path, RUN)
    with pytest.raises(FileExistsError):
        reserve_preview_run(tmp_path, RUN)
    with pytest.raises(ValueError):
        reserve_preview_run(tmp_path, '../wrong')


def test_scenario_claims_are_one_use():
    claims = PreviewClaims(RUN)
    assert not claims.claim('another-run', 'journey-00')
    assert not claims.claim(RUN, 'journey-10')
    assert claims.claim(RUN, 'journey-00')
    assert not claims.claim(RUN, 'journey-00')
    assert claims.claim(RUN, 'remove-00')
