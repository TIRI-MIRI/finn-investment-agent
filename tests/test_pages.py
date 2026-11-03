"""Tests for FINN UI pages and server-rendered routes."""

import pytest
from fastapi.testclient import TestClient

from app.data.companies import PORTDATA, RESEARCH_DATA
from main import app

client = TestClient(app)


class TestPageRoutes:
    """Verify HTTP status codes for all page routes."""

    def test_root_redirects_to_today(self):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/today"

    def test_today_page_status_200(self):
        response = client.get("/today")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_portfolio_page_status_200(self):
        response = client.get("/portfolio")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_research_page_status_200(self):
        response = client.get("/research")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_settings_page_status_200(self):
        response = client.get("/settings")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_static_css_reachable(self):
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        assert "--bg-primary" in response.text


class TestNavigation:
    """Verify navigation links exist on all screens."""

    PAGES = ["/today", "/portfolio", "/research", "/settings"]

    @pytest.mark.parametrize("page", PAGES)
    def test_navigation_links_present(self, page):
        html = client.get(page).text
        assert 'href="/today"' in html
        assert 'href="/research"' in html
        assert 'href="/portfolio"' in html
        assert 'href="/settings"' in html

    @pytest.mark.parametrize("page,tab", [
        ("/today", "today"),
        ("/portfolio", "portfolio"),
        ("/research", "research"),
        ("/settings", "settings"),
    ])
    def test_active_nav_tab_highlighted(self, page, tab):
        html = client.get(page).text
        # Both desktop and mobile nav items for the active tab should have class "active"
        assert f'class="nav-link-desktop active"' in html or f'class="nav-item-mobile active"' in html


class TestTodayPageContent:
    """Verify Today screen elements, priority cards, and routine collapsible section."""

    def test_today_page_has_header_and_disclaimer(self):
        html = client.get("/today").text
        assert "Today&#39;s Digest" in html or "Today's Digest" in html
        assert "Demo Fixture Environment" in html
        assert "synthetic" in html.lower()

    def test_today_page_has_pulse_stats(self):
        html = client.get("/today").text
        assert "Portfolio Universe" in html
        assert "High Priority" in html
        assert "Medium Priority" in html
        assert "Routine Filings" in html

    def test_today_page_has_priority_cards(self):
        html = client.get("/today").text
        assert "Triggered Alerts" in html
        assert "Corporate Events &amp; Filings" in html
        assert "RELIANCE" in html
        assert "Why it matters" in html
        assert "synthetic announcements, results &amp; prices" in html

    def test_today_page_has_collapsible_routine_section(self):
        html = client.get("/today").text
        assert "<details" in html
        assert "Routine &amp; Compliance Filings" in html or "Routine & Compliance Filings" in html
        assert "SBIN" in html  # AGM notice is low priority routine


class TestPortfolioPageContent:
    """Verify Portfolio screen displays all 19 companies."""

    def test_portfolio_page_displays_all_companies(self):
        import html
        response_text = client.get("/portfolio").text
        unescaped_text = html.unescape(response_text)
        for company in PORTDATA:
            assert company.ticker in unescaped_text, f"Ticker {company.ticker} missing from portfolio page"
            assert company.name in unescaped_text, f"Name {company.name} missing from portfolio page"

    def test_portfolio_page_has_search_input(self):
        html = client.get("/portfolio").text
        assert 'id="portfolioSearch"' in html
        assert 'filterPortfolio' in html

    def test_portfolio_page_has_synthetic_disclaimer(self):
        html = client.get("/portfolio").text
        assert "Mock Portfolio" in html
        assert "synthetic" in html.lower()


class TestResearchPageContent:
    """Verify Research screen brief rendering, sections, and universe navigation."""

    def test_research_page_renders_brief(self):
        html = client.get("/research").text
        assert "Company Research" in html
        assert "Pull Workflow" in html
        assert "Primary Sources Only" in html
        assert "INFY" in html
        assert "Company Overview" in html
        assert "Financial Trajectory" in html
        assert "Cash &amp; Balance Sheet" in html or "Cash & Balance Sheet" in html
        assert "Management Outlook" in html
        assert "Risks &amp; Data Limitations" in html or "Risks & Data Limitations" in html

    def test_research_page_shows_research_universe(self):
        html = client.get("/research").text
        for company in RESEARCH_DATA:
            assert company.ticker in html, f"Research ticker {company.ticker} missing"

    def test_research_page_ticker_param(self):
        response = client.get("/research?ticker=RELIANCE")
        assert response.status_code == 200
        assert "Reliance Industries" in response.text
        assert "RELIANCE" in response.text

    def test_research_page_evidence_inspector_modal(self):
        response = client.get("/research?ticker=INFY")
        assert response.status_code == 200
        html = response.text
        assert "inspectorModalBackdrop" in html
        assert "Primary Evidence Inspector" in html
        assert "openEvidenceModal" in html
        assert "modalExcerpt" in html
        assert "modalProvenance" in html

    def test_research_page_loading_and_coverage_elements(self):
        response = client.get("/research?ticker=INFY")
        assert response.status_code == 200
        html = response.text
        assert "research-loading" in html
        assert "Grounding Research Brief" in html
        assert "evidence-inspector" in html

    def test_research_page_error_state_on_unknown_ticker(self):
        response = client.get("/research?ticker=UNKNOWNXYZ")
        assert response.status_code == 200
        html = response.text
        assert "error-state-card" in html
        assert "Ticker Not In Authorized Research Universe" in html


class TestSettingsPageContent:
    """Verify Settings screen configuration and threshold values."""

    def test_settings_page_shows_thresholds(self):
        html = client.get("/settings").text
        assert "Settings &amp; Environment" in html or "Settings & Environment" in html
        assert "2.0" in html  # volume anomaly threshold
        assert "3.0%" in html  # price anomaly threshold
        assert "24 Hours" in html  # digest window

    def test_settings_page_shows_demo_mode_status(self):
        html = client.get("/settings").text
        assert "DEMO" in html
        assert "VERIFIED" in html
        assert "NONE (SAFE)" in html

    def test_settings_page_shows_data_counts(self):
        html = client.get("/settings").text
        assert f"{len(PORTDATA)} Stocks" in html
        assert f"{len(RESEARCH_DATA)} Stocks" in html
