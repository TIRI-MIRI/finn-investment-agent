"""Tests for FINN Pull Research Workflow API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.data.companies import RESEARCH_DATA
from main import app

client = TestClient(app)


class TestResearchCompaniesEndpoint:
    """Verify GET /api/research/companies."""

    def test_get_research_companies_status_200(self):
        response = client.get("/api/research/companies")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(RESEARCH_DATA)
        assert data["is_fixture"] is True
        tickers = [c["ticker"] for c in data["companies"]]
        for target in ["RELIANCE", "INFY", "TCS", "HDFCBANK", "TATAMOTORS"]:
            assert target in tickers


class TestResearchGenerateBriefEndpoint:
    """Verify POST /api/research/{ticker}."""

    @pytest.mark.parametrize("ticker", ["INFY", "RELIANCE", "TCS", "HDFCBANK", "TATAMOTORS"])
    def test_generate_brief_valid_tickers(self, ticker):
        response = client.post(f"/api/research/{ticker}")
        assert response.status_code == 200
        data = response.json()

        # Contract validation
        assert data["ticker"] == ticker
        assert "company_name" in data
        assert "generated_at" in data
        assert data["source_mode"] in ("demo", "live")
        assert "coverage" in data
        assert data["coverage"]["documents_found"] >= 1
        assert isinstance(data["coverage"]["periods"], list)

        # 5 Sections validation
        sections = data["sections"]
        assert len(sections) == 5
        sec_ids = [s["id"] for s in sections]
        assert sec_ids == [
            "company_overview",
            "financial_trajectory",
            "cash_and_balance_sheet",
            "management_outlook",
            "risks_and_limitations",
        ]

        # Evidence validation
        evidence = data["evidence"]
        assert len(evidence) > 0
        ev_ids_in_store = {e["id"] for e in evidence}

        # Check citation groundings
        for sec in sections:
            for claim in sec["claims"]:
                assert "text" in claim
                assert "confidence" in claim
                # Citations must only point to evidence in the brief
                for cid in claim["evidence_ids"]:
                    assert cid in ev_ids_in_store, f"Uncited evidence ID '{cid}' in claim"

    def test_generate_brief_invalid_ticker_returns_404(self):
        response = client.post("/api/research/NONEXISTENT_TICKER")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_generate_brief_force_refresh(self):
        response = client.post("/api/research/INFY?force_refresh=true")
        assert response.status_code == 200
        assert response.json()["ticker"] == "INFY"


class TestGetResearchBriefEndpoint:
    """Verify GET /api/research/{ticker}."""

    def test_get_research_brief_success(self):
        # Generate first
        post_res = client.post("/api/research/TCS")
        assert post_res.status_code == 200
        brief_id = post_res.json()["id"]

        # Retrieve by ticker
        get_res = client.get("/api/research/TCS")
        assert get_res.status_code == 200
        assert get_res.json()["ticker"] == "TCS"
        assert get_res.json()["id"] == brief_id

        # Retrieve by research ID
        id_res = client.get(f"/api/research/{brief_id}")
        assert id_res.status_code == 200
        assert id_res.json()["ticker"] == "TCS"

    def test_get_research_brief_invalid_ticker_returns_404(self):
        response = client.get("/api/research/UNKNOWN_TICKER")
        assert response.status_code == 404


class TestGetResearchEvidenceEndpoint:
    """Verify GET /api/research/{ticker}/evidence."""

    def test_get_research_evidence_success(self):
        response = client.get("/api/research/RELIANCE/evidence")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "RELIANCE"
        assert data["count"] > 0
        assert len(data["evidence"]) == data["count"]

        # Verify evidence properties
        first_ev = data["evidence"][0]
        assert "id" in first_ev
        assert "title" in first_ev
        assert "publisher" in first_ev
        assert "excerpt" in first_ev
        assert first_ev["ticker"] == "RELIANCE"

    def test_get_research_evidence_invalid_ticker_returns_404(self):
        response = client.get("/api/research/INVALID_TICKER/evidence")
        assert response.status_code == 404

