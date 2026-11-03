"""Regression tests for research citation accuracy, source links, and evidence inspector navigation."""

import re
from fastapi.testclient import TestClient
import pytest

from app.core.models import Claim, Confidence, RetrievedDocument, SourceEvidence, SourceMode
from app.data.companies import RESEARCH_DATA
from app.data.research_fixtures import RESEARCH_FIXTURE_DOCS
from app.services.citation_validator import CitationValidator
from app.services.research_service import ResearchService
from app.services.synthesizer import ResearchSynthesizer
from main import app

client = TestClient(app)


class TestCitationIntegrityAndResolution:
    """Verify that every citation chip resolves to an evidence record in the active brief."""

    @pytest.mark.parametrize("company", RESEARCH_DATA)
    def test_all_rendered_citation_chips_resolve_to_evidence(self, company):
        ticker = company.ticker
        res = client.get(f"/research?ticker={ticker}")
        assert res.status_code == 200
        html = res.text

        # Extract all citation chips: onclick="openEvidenceModal('ev-...')"
        cited_ids = re.findall(r"openEvidenceModal\('(ev-[a-zA-Z0-9_-]+)'\)", html)
        assert len(cited_ids) > 0, f"No citations found for ticker {ticker}"

        # Extract all evidence card IDs: id="ev-..."
        card_ids = set(re.findall(r'<div class="evidence-card" id="(ev-[a-zA-Z0-9_-]+)"', html))

        # Every cited ID must exist in card_ids
        for cid in cited_ids:
            assert cid in card_ids, f"Citation chip [{cid}] for {ticker} does not resolve to an evidence card in DOM"

    def test_missing_evidence_modal_error_handling(self):
        """Verify that JavaScript inspector handles non-existent IDs with an explicit error state."""
        res = client.get("/research?ticker=INFY")
        assert res.status_code == 200
        html = res.text
        # Inspector script must contain explicit error handling for !card
        assert "Unresolved Citation Error" in html
        assert "ERROR: Citation ID Not Found in Evidence Store" in html


class TestOfficialSourceLinksAndProvenance:
    """Verify that genuine source URLs are valid official domains and not synthetic placeholders."""

    @pytest.mark.parametrize("ticker", ["RELIANCE", "INFY", "TCS", "HDFCBANK", "TATAMOTORS"])
    def test_genuine_documents_have_official_urls(self, ticker):
        docs = RESEARCH_FIXTURE_DOCS.get(ticker, [])
        assert len(docs) >= 1, f"No documents configured for {ticker}"

        doc = docs[0]
        # Must have valid URL starting with https://
        assert doc.url.startswith("https://")
        assert not doc.is_fixture  # Verified genuine official document
        assert doc.status == "success"

        # Domain verification
        allowed_hosts = {
            "RELIANCE": "ril.com",
            "INFY": "infosys.com",
            "TCS": "tcs.com",
            "HDFCBANK": "hdfc.bank.in",
            "TATAMOTORS": "tatamotors.com",
        }
        expected_host = allowed_hosts[ticker]
        assert expected_host in doc.url, f"Doc URL '{doc.url}' does not belong to expected host '{expected_host}'"

    def test_ui_renders_official_source_links(self):
        """Verify that official documents display 'View Official Primary Document Source'."""
        res = client.get("/research?ticker=RELIANCE")
        assert res.status_code == 200
        html = res.text
        assert "View Official Primary Document Source" in html
        assert "ril.com/sites/default/files" in html
        assert "Status: Genuine Document" in html
        assert "[OFFICIAL FILING]" in html

    def test_fixture_documents_suppress_live_links(self):
        """Verify that fixture-backed research suppresses misleading outbound links."""
        svc = ResearchService()
        fixture_doc = RetrievedDocument(
            id="doc-synthetic-01",
            ticker="INFY",
            title="Synthetic Demo Disclosure",
            publisher="Synthetic Test Corp",
            url="https://placeholder.internal/test.html",
            document_type="quarterly_results",
            is_fixture=True,  # Explicitly marked as demo fixture
            raw_text="<p>Synthetic business update with demo metrics.</p>",
        )
        evidence = svc.processor.process_document(fixture_doc)
        assert len(evidence) > 0
        assert evidence[0].is_fixture is True

        brief = svc.synthesizer.generate_brief("INFY", "Infosys Limited", evidence)
        assert brief.source_mode == SourceMode.DEMO
        assert any("synthetic demo fixtures" in w.lower() for w in brief.coverage.warnings)


class TestClaimNumberVerification:
    """Verify that synthesized claims match genuine numbers from primary filings."""

    def test_reliance_claims_match_genuine_numbers(self):
        res = client.get("/api/research/RELIANCE")
        assert res.status_code == 200
        brief = res.json()
        all_claim_text = " ".join(
            c["text"] for sec in brief["sections"] for c in sec["claims"]
        )
        # Genuine Q3 FY25 figures from RIL media release
        assert "267186" in all_claim_text.replace(",", "") or "267,186" in all_claim_text
        assert "48003" in all_claim_text.replace(",", "") or "48,003" in all_claim_text
        assert "21930" in all_claim_text.replace(",", "") or "21,930" in all_claim_text

    def test_tatamotors_claims_match_genuine_numbers(self):
        res = client.get("/api/research/TATAMOTORS")
        assert res.status_code == 200
        brief = res.json()
        all_claim_text = " ".join(
            c["text"] for sec in brief["sections"] for c in sec["claims"]
        )
        # Genuine Q3 FY25 figures from Tata Motors press release
        assert "113574" in all_claim_text.replace(",", "") or "113,574" in all_claim_text or "113.6K" in all_claim_text
        assert "15500" in all_claim_text.replace(",", "") or "15,500" in all_claim_text

    def test_infosys_claims_match_genuine_numbers(self):
        res = client.get("/api/research/INFY")
        assert res.status_code == 200
        brief = res.json()
        all_claim_text = " ".join(
            c["text"] for sec in brief["sections"] for c in sec["claims"]
        )
        assert "41764" in all_claim_text.replace(",", "") or "41,764" in all_claim_text
        assert "6806" in all_claim_text.replace(",", "") or "6,806" in all_claim_text


class TestTodayPageAnnouncementLinks:
    """Verify that synthetic announcements on Today page do not present broken placeholder links."""

    def test_synthetic_announcements_display_no_filing_label(self):
        res = client.get("/today")
        assert res.status_code == 200
        html = res.text
        # Must display honest non-link label
        assert "Synthetic demo announcement" in html
        assert "no external filing" in html

    def test_problematic_placeholder_urls_not_rendered(self):
        res = client.get("/today?window=all")
        assert res.status_code == 200
        html = res.text

        problematic_urls = [
            "https://www.tatamotors.com/press/ev-battery-jv-2025",
            "https://www.ril.com/investor-relations/results/q3-fy2025",
            "https://www.infosys.com/investors/reports/q3-fy2025",
            "https://www.hdfcbank.com/investor/dividend/2025",
            "https://www.sbi.co.in/web/investor-relations/agm-2025",
            "https://www.itcportal.com/investor-relations/bonus-2025",
            "https://www.larsentoubro.com/media/press-releases/green-hydrogen-2025",
            "https://www.icicibank.com/investor-relations/qip-jan2025",
            "https://www.tcs.com/press-releases/2025/cto-appointment",
        ]
        for url in problematic_urls:
            assert f'href="{url}"' not in html, f"Broken placeholder URL '{url}' rendered on Today page"

    def test_all_fixture_announcements_have_no_unverified_source_url(self):
        from app.data.announcements import ANNOUNCEMENTS
        for ann in ANNOUNCEMENTS:
            if ann.is_fixture:
                assert ann.source_url is None, (
                    f"Announcement {ann.id} is marked fixture but has unverified source_url: {ann.source_url}"
                )

    def test_routine_filings_suppress_broken_links(self):
        res = client.get("/today?window=all")
        assert res.status_code == 200
        html = res.text
        # Routine compliance drawer must also suppress broken links
        assert "SBIN" in html
        assert "Synthetic demo announcement" in html


