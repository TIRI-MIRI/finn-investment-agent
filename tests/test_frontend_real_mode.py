from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import main


def test_real_mode_uses_verified_historical_filings_without_demo_prices(monkeypatch):
    monkeypatch.setattr(main.settings, 'demo_mode', False)
    client = TestClient(main.app)
    snapshot = client.get('/api/monitoring').json()
    assert snapshot['reference_date'] == '2025-01-16'
    assert len(snapshot['events']) == 1
    assert snapshot['signals'] == []
    assert not any(a['is_fixture'] for a in snapshot['events'])
    soup = BeautifulSoup(client.get('/today').text, 'html.parser')
    assert not soup.select('.holding-tile')
    assert '6,806.00' in soup.get_text()
    assert 'Not available' in soup.get_text()
    link = soup.select_one('.announcement-card a.filing-link')
    response = client.get(link['href'])
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')
    assert 'inline' in response.headers['content-disposition']
    assert client.get('/api/alerts').json()['alerts'] == []
    assert client.get('/api/digest?window=30d').json()['total_count'] == 1
    for route in ['/today', '/alerts', '/research', '/watch', '/portfolio', '/settings']:
        assert client.get(route, follow_redirects=False).status_code == 200
    watch = client.get('/watch').text
    assert 'Price unavailable' in watch
    assert 'Synthetic EOD</div>' not in watch


def test_thirty_day_filter_and_single_cards():
    client = TestClient(main.app)
    response = client.get('/today?window=30d')
    soup = BeautifulSoup(response.text, 'html.parser')
    assert soup.select_one('.window-btn.active').get_text() == '30d'
    assert len(soup.select('article.announcement-card')) == 10
    ids = [card['id'] for card in soup.select('article.announcement-card')]
    assert len(ids) == len(set(ids))


def test_real_mode_hides_events_if_archive_verification_fails(monkeypatch):
    monkeypatch.setattr(main.settings, 'demo_mode', False)
    monkeypatch.setattr(main.FilingArchive, 'usable_documents', lambda self: [])
    assert main.monitoring_snapshot(window='all')['events'] == []


def test_watchlist_limits_alerts_without_hiding_filings():
    client = TestClient(main.app)
    rules = client.get('/api/monitoring/settings').json()['rules']
    rules['monitored_tickers'] = ['INFY']
    assert client.put('/api/monitoring/settings', json=rules).status_code == 200
    snapshot = client.get('/api/monitoring?window=all').json()
    assert {a['ticker'] for a in snapshot['queue']} == {'INFY'}
    assert len(snapshot['events']) == 10
    assert client.get('/api/monitoring/settings').json()['rules']['monitored_tickers'] == ['INFY']


def test_watch_form_preserves_universe_and_verified_document_access(monkeypatch):
    monkeypatch.setattr(main.settings, 'demo_mode', False)
    client = TestClient(main.app)
    response = client.get('/watch')
    soup = BeautifulSoup(response.text, 'html.parser')
    assert len(soup.select('input[name="monitored_tickers"]')) == 19
    assert len(soup.select('.watch-metrics > div')) == 3
    assert '2025-01-16' in soup.select_one('.watch-status').get_text()
    link = soup.select_one('.watch-company a.watch-document')
    assert client.get(link['href']).content.startswith(b'%PDF')
    assert 'Real-data mode · Historical verified filings. Market prices unavailable.' not in client.get('/today').text


def test_saved_thresholds_change_actual_market_alerts_and_watch_form(monkeypatch):
    monkeypatch.setattr(main.settings, 'demo_mode', True)
    client = TestClient(main.app)
    rules = client.get('/api/monitoring/settings').json()['rules']
    rules.update(event_types=[], price_threshold_pct=3, volume_multiple_threshold=2)
    assert client.put('/api/monitoring/settings', json=rules).status_code == 200
    assert client.get('/api/alerts').json()['count'] > 0
    rules.update(price_threshold_pct=100, volume_multiple_threshold=50)
    assert client.put('/api/monitoring/settings', json=rules).status_code == 200
    assert client.get('/api/alerts').json()['count'] == 0
    assert client.get('/api/monitoring').json()['queue'] == []
    soup = BeautifulSoup(client.get('/watch').text, 'html.parser')
    assert float(soup.select_one('[name="price_threshold_pct"]')['value']) == 100
    assert float(soup.select_one('[name="volume_multiple_threshold"]')['value']) == 50
    assert 'No alerts in this window' in client.get('/alerts').text
