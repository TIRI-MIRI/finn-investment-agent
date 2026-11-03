"""Unit tests for ResearchStore: document, evidence, and research brief storage."""

import pytest

from app.core.models import CompanyResearch, RetrievedDocument, SourceEvidence
from app.services.research_store import ResearchStore


@pytest.fixture
def store():
    return ResearchStore()


class TestResearchStore:
    def test_save_and_get_document(self, store):
        doc = RetrievedDocument(
            id="doc-test-1",
            ticker="RELIANCE",
            title="Q3 FY25 Report",
            publisher="RIL",
            url="https://investors.ril.com/q3.html",
        )
        saved_id = store.save_document(doc)
        assert saved_id == "doc-test-1"

        retrieved = store.get_document("doc-test-1")
        assert retrieved is not None
        assert retrieved.ticker == "RELIANCE"
        assert retrieved.title == "Q3 FY25 Report"

    def test_get_nonexistent_document_returns_none(self, store):
        assert store.get_document("nonexistent-doc") is None

    def test_list_documents_filtering(self, store):
        doc1 = RetrievedDocument(id="d1", ticker="RELIANCE", title="R1", publisher="RIL", url="https://ril.com/1")
        doc2 = RetrievedDocument(id="d2", ticker="INFY", title="I1", publisher="Infosys", url="https://infosys.com/1")
        store.save_document(doc1)
        store.save_document(doc2)

        all_docs = store.list_documents()
        assert len(all_docs) == 2

        ril_docs = store.list_documents(ticker="RELIANCE")
        assert len(ril_docs) == 1
        assert ril_docs[0].ticker == "RELIANCE"

        infy_docs = store.list_documents(ticker="INFY")
        assert len(infy_docs) == 1
        assert infy_docs[0].ticker == "INFY"

    def test_save_and_get_evidence(self, store):
        ev1 = SourceEvidence(
            id="ev-1",
            title="AR 2024",
            publisher="Infosys",
            document_type="annual_report",
            ticker="INFY",
            document_id="d2",
            excerpt="Revenue was ₹1,53,670 Cr in FY24.",
        )
        ev2 = SourceEvidence(
            id="ev-2",
            title="Q3 Release",
            publisher="RIL",
            document_type="quarterly_results",
            ticker="RELIANCE",
            document_id="d1",
            excerpt="Digital services grew 15% YoY.",
        )
        store.save_evidence([ev1, ev2])

        assert store.get_evidence("ev-1") is not None
        assert store.get_evidence("ev-1").ticker == "INFY"
        assert store.get_evidence("ev-2") is not None
        assert store.get_evidence("missing-ev") is None

        # Filter by ticker
        infy_ev = store.list_evidence(ticker="INFY")
        assert len(infy_ev) == 1
        assert infy_ev[0].id == "ev-1"

        # Filter by document_id
        d1_ev = store.list_evidence(document_id="d1")
        assert len(d1_ev) == 1
        assert d1_ev[0].id == "ev-2"

    def test_save_and_get_research(self, store):
        research = CompanyResearch(
            id="res-001",
            ticker="INFY",
            company_name="Infosys Limited",
            generated_at="2025-02-05T12:00:00",
        )
        store.save_research(research)

        fetched = store.get_research("res-001")
        assert fetched is not None
        assert fetched.ticker == "INFY"

        latest = store.get_latest_research("INFY")
        assert latest is not None
        assert latest.id == "res-001"

        assert store.get_latest_research("NONEXISTENT") is None

    def test_clear_resets_store(self, store):
        doc = RetrievedDocument(id="d1", ticker="RELIANCE", title="R1", publisher="RIL", url="https://ril.com/1")
        store.save_document(doc)
        assert len(store.list_documents()) == 1

        store.clear()
        assert len(store.list_documents()) == 0
        assert store.get_document("d1") is None

