"""Offline regressions: official-looking URLs never establish provenance."""
import hashlib
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from main import app
from app.data.research_fixtures import RESEARCH_FIXTURE_DOCS

client = TestClient(app)


def test_reviewed_research_records_have_not_silently_changed():
    # Update only after rechecking title, date AND every summary against the PDF.
    expected = json.loads(Path(__file__).with_name('reviewed_filings.json').read_text())
    actual = {
        d.id: hashlib.sha256(json.dumps(d.model_dump(), sort_keys=True).encode()).hexdigest()
        for docs in RESEARCH_FIXTURE_DOCS.values() for d in docs
    }
    assert actual == expected
    assert all(d.has_verified_filing for docs in RESEARCH_FIXTURE_DOCS.values() for d in docs)


@pytest.mark.parametrize('fixture,reviewed,linked', [(True, False, False), (True, True, False), (False, False, False), (False, True, True)])
def test_today_material_and_routine_links_require_review(fixture, reviewed, linked):
    response = client.get('/today?window=all')
    context = dict(response.context)
    url = 'https://www.ril.com/unverified-test-document'
    for key in ('material_announcements', 'routine_announcements'):
        context[key] = [a.model_copy(update={
            'is_fixture': fixture, 'source_url': url,
            'verification_note': 'Test review' if reviewed else None,
        }) for a in context[key]]
    soup = BeautifulSoup(response.template.render(context), 'html.parser')
    cards = soup.select('.announcement-card')
    assert cards
    for card in cards:
        assert bool(card.select_one(f'a[href="{url}"]')) == linked
        if fixture:
            assert 'Synthetic demo announcement — no external filing.' in card.get_text()


@pytest.mark.parametrize('fixture,reviewed,linked', [(True, False, False), (True, True, False), (False, False, False), (False, True, True)])
def test_research_cards_and_inspector_require_review(fixture, reviewed, linked):
    response = client.get('/research?ticker=INFY')
    context = dict(response.context)
    brief = context['brief'].model_copy(deep=True)
    for ev in brief.evidence:
        ev.is_fixture = fixture
        ev.verification_note = 'Test review' if reviewed else None
    context['brief'] = brief
    soup = BeautifulSoup(response.template.render(context), 'html.parser')
    cards = soup.select('.evidence-card')
    assert cards
    for card in cards:
        assert bool(card.select_one('a.evidence-link')) == linked
        assert bool(card['data-url']) == linked
        assert card['data-verified'] == str(linked).lower()
        assert ('[OFFICIAL FILING]' in card.get_text()) == linked


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'http://www.ril.com/file', 'https://user@www.ril.com/file'])
def test_unsafe_urls_cannot_be_verified(url):
    doc = RESEARCH_FIXTURE_DOCS['RELIANCE'][0].model_copy(update={'url': url})
    assert not doc.has_verified_filing
