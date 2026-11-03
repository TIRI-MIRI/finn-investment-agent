from datetime import date, timedelta

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from pydantic import ValidationError

import main
from app.core.models import AnnouncementCategory, PriceBar
from app.data.announcements import ANNOUNCEMENTS
from app.data.prices import PRICE_BARS_BY_TICKER
from app.services.announcements import AnnouncementService
from app.services.anomalies import AnomalyDetector
from app.services.monitoring import build_monitoring, intelligence
from app.services.monitoring_store import MonitoringRules, MonitoringStore

client = TestClient(main.app)


def bars(close=103, volume=200):
    return [PriceBar(ticker="INFY", date=(date(2025, 1, 1) + timedelta(days=i)).isoformat(), close=100 if i < 20 else close, volume=100 if i < 20 else volume) for i in range(21)]


@pytest.mark.parametrize('close,volume,mode,expected', [
    (103,100,'OR',True), (97,100,'OR',True), (100,200,'OR',True),
    (103,100,'AND',False), (100,200,'AND',False), (103,200,'AND',True),
    (102.999,199,'OR',False), (100,100,'OR',False),
])
def test_threshold_boundaries_and_modes(close, volume, mode, expected):
    signal = AnomalyDetector(trigger_mode=mode).detect_ticker_anomaly('INFY', bars(close,volume))
    assert signal.triggered is expected
    assert signal.baseline_volume_mean == 100  # excludes latest spike
    assert signal.baseline_sessions == 20


def test_short_and_empty_baselines_are_honest():
    history = bars()[-3:]
    signal = AnomalyDetector().detect_ticker_anomaly('INFY', history)
    assert signal.baseline_sessions == 2
    for bar in history[:-1]:
        bar.volume = 0
    signal = AnomalyDetector(volume_multiple_threshold=.5).detect_ticker_anomaly('INFY', history)
    assert signal.baseline_sessions == 0
    assert signal.is_volume_anomaly is False


@pytest.mark.parametrize('payload', [
    {'price_threshold_pct':0}, {'price_threshold_pct':float('inf')},
    {'volume_multiple_threshold':.4}, {'trigger_mode':'XOR'},
    {'event_types':['invented']}, {'unknown':True},
])
def test_invalid_rules_rejected(payload):
    with pytest.raises(ValidationError):
        MonitoringRules(**payload)


def test_settings_persist_and_preserve_acknowledgement(tmp_path):
    path = tmp_path / 'settings.json'
    store = MonitoringStore(path)
    store.acknowledge('alert-test', True)
    store.save_rules(MonitoringRules(price_threshold_pct=7, event_types=[]))
    state, warning = MonitoringStore(path).load()
    assert not warning
    assert state.rules.price_threshold_pct == 7
    assert state.rules.event_types == []
    assert state.acknowledged == {'alert-test': True}


def test_corrupt_settings_fall_back_visibly(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{broken')
    store = MonitoringStore(path)
    state, warning = store.load()
    assert state.rules == MonitoringRules()
    assert warning
    with pytest.raises(OSError):
        store.acknowledge('alert-test', True)
    assert path.read_text() == '{broken'


def test_atomic_write_failure_keeps_saved_settings(isolated_monitoring_store, monkeypatch):
    store = isolated_monitoring_store
    store.save_rules(MonitoringRules(price_threshold_pct=6))
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr('app.services.monitoring_store.os.replace', fail)
    assert client.put('/api/monitoring/settings', json=MonitoringRules().model_dump(mode='json')).status_code == 503
    assert store.load()[0].rules.price_threshold_pct == 6


def test_preview_does_not_save_and_saved_rules_drive_both_apis(isolated_monitoring_store):
    rules = MonitoringRules(price_threshold_pct=100, volume_multiple_threshold=50, event_types=[]).model_dump(mode='json')
    preview = client.post('/api/monitoring/preview', json=rules).json()
    assert preview['alert_count'] == 0
    assert not isolated_monitoring_store.path.exists()
    assert client.put('/api/monitoring/settings', json=rules).status_code == 200
    assert client.get('/api/monitoring').json()['queue'] == []
    assert client.get('/api/alerts').json()['count'] == 0
    assert 'No rules triggered' in client.get('/today').text
    assert len(client.get('/api/digest?window=all').json()['material_announcements']) > 0


def test_subscriptions_only_affect_alerts_not_event_feed():
    result = build_monitoring(ANNOUNCEMENTS, {}, MonitoringRules(event_types=['dividend']), {}, '2025-02-05', 'all')
    assert len(result['events']) == 10
    assert len(result['queue']) == 1
    assert result['queue'][0]['ticker'] == 'HDFCBANK'


def test_acknowledgement_persists_and_can_be_reversed():
    before = client.get('/api/monitoring').json()
    alert_id = before['queue'][0]['id']
    assert client.put(f'/api/monitoring/alerts/{alert_id}', json={'acknowledged':True}).status_code == 200
    after = client.get('/api/monitoring').json()
    assert after['unread_count'] == before['unread_count'] - 1
    assert after['queue'][0]['acknowledged'] is True
    assert client.put(f'/api/monitoring/alerts/{alert_id}', json={'acknowledged':False}).status_code == 200
    assert client.get('/api/monitoring').json()['unread_count'] == before['unread_count']
    assert client.put('/api/monitoring/alerts/missing', json={'acknowledged':True}).status_code == 404


def test_historical_views_do_not_use_future_prices():
    response = client.get('/api/monitoring?reference_date=2025-01-22&window=all').json()
    assert all(s['date'] <= '2025-01-22' for s in response['signals'])
    assert response['events'] == []
    assert client.get('/today?ref_date=bad').status_code == 422


def test_dedup_normalized_title_url_and_source_id():
    original = ANNOUNCEMENTS[0]
    variants = [original, original.model_copy(update={'id':'duplicate','title':'  ' + original.title.upper().replace(' ', '  ') + '!!!'})]
    assert len(AnnouncementService.deduplicate(variants)) == 1
    assert AnnouncementService.canonical_id(variants[0]) == AnnouncementService.canonical_id(variants[1])
    original = original.model_copy(update={'source_url':'https://www.ril.com/report.pdf'})
    other = original.model_copy(update={'title':'Different wrapper title', 'source_url':'https://WWW.RIL.COM/report.pdf?utm_source=demo#page=2'})
    assert len(AnnouncementService.deduplicate([original,other])) == 1
    other.source_url = None
    other.source_document_id = 'filing-123'
    original.source_document_id = 'filing-123'
    assert len(AnnouncementService.deduplicate([original,other])) == 1


def test_generated_ids_distinguish_same_day_different_events():
    svc = AnnouncementService()
    raw = ANNOUNCEMENTS[0].model_dump()
    raw.pop('id')
    first = svc.normalize_record(raw)
    second = svc.normalize_record({**raw, 'title':'Another filing'})
    assert first.id != second.id


def test_queue_and_feed_do_not_duplicate_full_cards():
    response = client.get('/today?window=all')
    soup = BeautifulSoup(response.text, 'html.parser')
    assert len(soup.select('article.announcement-card')) == 10
    assert not soup.select('.routine-details[open]')
    for link in soup.select('.event-reference a, .signal-table a'):
        assert soup.select_one(link['href']) is not None
    for card in soup.select('.inbox-alert'):
        assert len(card.select('.review-details > summary')) == 1
    assert not soup.select('.announcement-card a[href^="http"]')


def test_management_and_ma_do_not_invent_missing_facts():
    management = next(a for a in ANNOUNCEMENTS if a.category == AnnouncementCategory.MANAGEMENT_CHANGE)
    info = intelligence(management)
    assert info['fields']['Incoming executive'] == 'Not disclosed'
    assert info['fields']['Effective date'] == 'Not disclosed'
    assert info['fields']['Verified background'] == 'Not verified from an official source'
    deal = next(a for a in ANNOUNCEMENTS if a.category == AnnouncementCategory.M_AND_A)
    assert intelligence(deal)['fields']['Approvals'] == 'Not disclosed'


def test_related_alerts_do_not_assert_causality_or_attach_wrong_results():
    result = build_monitoring(ANNOUNCEMENTS, PRICE_BARS_BY_TICKER, MonitoringRules(), {}, '2025-02-05', 'all')
    tata = next(a for a in result['queue'] if a['ticker'] == 'TATAMOTORS' and a['ann'])
    assert len(tata['related']) == 1
    tcs = next(a for a in result['events'] if a.ticker == 'TCS')
    assert result['event_info'][AnnouncementService.canonical_id(tcs)]['results'] is None
    assert 'no causal relationship established' in client.get('/today').text


def test_results_show_comparison_values_and_pbt():
    soup = BeautifulSoup(client.get('/today').text, 'html.parser')
    tables = soup.select('.results-table')
    assert len(tables) == 2
    for table in tables:
        text = table.get_text()
        assert all(label in text for label in ('Q3 FY2025','Q2 FY2025','Q3 FY2024','Revenue','EBITDA','PBT','PAT'))
        assert len(table.select('tbody tr')) == 4


def test_results_missing_and_zero_values_are_not_fabricated():
    from app.core.models import QuarterlyMetric, QuarterlyResultSummary
    template = main.templates.env.get_template('monitoring_macros.html')
    ann = ANNOUNCEMENTS[0]
    info = intelligence(ann)
    info['results'] = QuarterlyResultSummary(ticker=ann.ticker, company_name=ann.company_name,
        period='Q3 FY2025', revenue=QuarterlyMetric(metric_name='Revenue', current=0, qoq_prev=10, yoy_prev=None))
    rendered = template.module.event_detail(ann, info)
    soup = BeautifulSoup(rendered, 'html.parser')
    rows = soup.select('tbody tr')
    assert '0.00' in rows[0].get_text()
    assert '-100.00%' in rows[0].get_text()
    assert 'Not available' in rows[0].get_text()
    assert rows[2].get_text().count('Not available') == 5  # missing PBT, all periods and growth


@pytest.mark.parametrize('url', ['/api/monitoring/settings', '/api/monitoring/preview'])
def test_invalid_settings_api_returns_422_without_saving(url, isolated_monitoring_store):
    method = client.put if url.endswith('settings') else client.post
    assert method(url, json={'price_threshold_pct':-3}).status_code == 422
    assert not isolated_monitoring_store.path.exists()


def test_market_rule_revision_requires_fresh_review():
    first = build_monitoring([], PRICE_BARS_BY_TICKER, MonitoringRules(), {}, '2025-02-05')
    seen = {a['id']:True for a in first['queue']}
    revised = build_monitoring([], PRICE_BARS_BY_TICKER, MonitoringRules(price_threshold_pct=2), seen, '2025-02-05')
    assert revised['unread_count'] == len(revised['queue'])


def test_source_document_id_participates_in_canonical_identity():
    ann = ANNOUNCEMENTS[0]
    reviewed = ann.model_copy(update={'source_document_id':'official-123'})
    assert AnnouncementService.canonical_id(ann) != AnnouncementService.canonical_id(reviewed)
    # Alternate wrappers remain deduplicated by normalized content or source ID.
    assert len(AnnouncementService.deduplicate([ann, reviewed])) == 1
